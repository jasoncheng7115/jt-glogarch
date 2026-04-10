"""CLI interface using Click + Rich."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from glogarch.core.config import Settings, load_settings, get_settings
from glogarch.core.database import ArchiveDB
from glogarch.utils.logging import setup_logging

console = Console()


def _get_db() -> ArchiveDB:
    settings = get_settings()
    db = ArchiveDB(settings.database_path)
    db.connect()
    return db


def _parse_dt(s: str) -> datetime:
    """Parse datetime string, supports multiple formats."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise click.BadParameter(f"Cannot parse datetime: {s}")


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Path to config.yaml")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(config_path: str | None, verbose: bool):
    """jt-glogarch — Graylog Open Archive tool."""
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level)
    load_settings(config_path)


@cli.command()
@click.option("--from", "time_from", default=None, help="Start time (ISO format or YYYY-MM-DD)")
@click.option("--to", "time_to", default=None, help="End time (default: now)")
@click.option("--days", "-d", default=None, type=int, help="Export the last N days (e.g. --days 180)")
@click.option("--mode", "-m", default=None, type=click.Choice(["api", "opensearch"]),
              help="Export mode (default: from config export_mode)")
@click.option("--server", "-s", default=None, help="Server name from config")
@click.option("--stream", default=None, multiple=True, help="Stream ID(s) to export (api mode)")
@click.option("--index-set", default=None, multiple=True, help="Index set ID(s)")
@click.option("--resume/--no-resume", default=True, help="Auto-resume from last exported point (default: enabled)")
def export(time_from: str | None, time_to: str | None, days: int | None,
           mode: str | None, server: str | None, stream: tuple[str, ...],
           index_set: tuple[str, ...], resume: bool):
    """Export logs from Graylog to archive files.

    Supports two modes:

      api         — Export via Graylog REST API (default)

      opensearch  — Export directly from OpenSearch (faster, no pagination limits)

    Examples:

      glogarch export --days 180                        Last 180 days via API

      glogarch export --days 180 --mode opensearch      Last 180 days via OpenSearch

      glogarch export --from 2026-03-01 --to 2026-03-15
    """
    if not time_from and not days:
        raise click.UsageError("Must specify either --from or --days")

    settings = get_settings()
    server_config = settings.get_server(server)
    db = _get_db()
    export_mode = mode or settings.export_mode

    dt_to = _parse_dt(time_to) if time_to else datetime.utcnow()
    dt_from = (dt_to - timedelta(days=days)) if days else _parse_dt(time_from)

    console.print(f"[bold]Export mode:[/bold] {export_mode}")

    if export_mode == "opensearch":
        _export_opensearch(settings, server_config, db, dt_from, dt_to,
                           index_set, resume)
    else:
        _export_api(settings, server_config, db, dt_from, dt_to,
                    stream, index_set, resume)

    db.close()


def _export_api(settings, server_config, db, dt_from, dt_to, stream, index_set, resume):
    """Export via Graylog REST API."""
    from glogarch.export.exporter import Exporter, _ensure_naive

    exporter = Exporter(server_config, settings.export, settings.rate_limit, db)

    if resume:
        rp = exporter.get_resume_point(stream[0] if stream else None)
        if rp:
            rp = _ensure_naive(rp)
            if rp > dt_from:
                dt_from = rp
                console.print(f"[yellow]Resuming from {dt_from.isoformat()}[/yellow]")

    streams = list(stream) if stream else None
    stream_names: dict[str, str] = {}

    if index_set or settings.export.index_sets:
        index_set_ids = list(index_set) if index_set else settings.export.index_sets
        console.print(f"[cyan]Resolving streams for {len(index_set_ids)} index set(s)...[/cyan]")

        async def _resolve():
            from glogarch.graylog.client import GraylogClient
            from glogarch.ratelimit.limiter import RateLimiter
            rl = RateLimiter(settings.rate_limit)
            async with GraylogClient(server_config, rl) as client:
                resolved = []
                for isid in index_set_ids:
                    ss = await client.get_streams_for_index_set(isid)
                    for s in ss:
                        resolved.append(s["id"])
                        stream_names[s["id"]] = s.get("title", "")
                        console.print(f"  Stream: {s['id']} — {s.get('title', '?')}")
                return resolved

        resolved_streams = asyncio.run(_resolve())
        streams = (streams or []) + resolved_streams

    console.print(f"[bold]Exporting (API)[/bold] {server_config.name}: "
                  f"{dt_from.isoformat()} → {dt_to.isoformat()}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.fields[messages]} records)"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting...", total=100, messages=0)

        def _progress(info: dict):
            progress.update(task, completed=info.get("pct", 0),
                            description=f"Chunk {info.get('chunk_index', 0)}/{info.get('total_chunks', 0)} [{info.get('phase', '')}]",
                            messages=info.get("messages_done", 0))

        result = asyncio.run(exporter.export(
            time_from=dt_from, time_to=dt_to, streams=streams,
            stream_names=stream_names if stream_names else None,
            progress_callback=_progress,
        ))

    _print_export_result(result)


def _export_opensearch(settings, server_config, db, dt_from, dt_to, index_set, resume):
    """Export directly from OpenSearch."""
    from glogarch.opensearch.exporter import OpenSearchExporter
    from glogarch.export.exporter import _ensure_naive

    if not settings.opensearch.hosts:
        console.print("[red]Error: opensearch.hosts not configured in config.yaml[/red]")
        console.print("Please add opensearch connection settings:")
        console.print("  opensearch:")
        console.print("    hosts: [\"http://192.168.1.127:9200\"]")
        console.print("    username: admin")
        console.print("    password: your-password")
        return

    exporter = OpenSearchExporter(
        server_config, settings.opensearch, settings.export,
        settings.rate_limit, db,
    )

    if resume:
        rp = exporter.get_resume_point()
        if rp:
            rp = _ensure_naive(rp)
            if rp > dt_from:
                dt_from = rp
                console.print(f"[yellow]Resuming from {dt_from.isoformat()}[/yellow]")

    index_set_ids = list(index_set) if index_set else (settings.export.index_sets or None)

    console.print(f"[bold]Exporting (OpenSearch)[/bold] {server_config.name}: "
                  f"{dt_from.isoformat()} → {dt_to.isoformat()}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.fields[messages]} records)"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting...", total=100, messages=0)

        def _progress(info: dict):
            idx = info.get("index", "")
            progress.update(task, completed=info.get("pct", 0),
                            description=f"Index {info.get('chunk_index', 0)}/{info.get('total_chunks', 0)} {idx} [{info.get('phase', '')}]",
                            messages=info.get("messages_done", 0))

        result = asyncio.run(exporter.export(
            time_from=dt_from, time_to=dt_to,
            index_set_ids=index_set_ids,
            progress_callback=_progress,
        ))

    _print_export_result(result)


def _print_export_result(result):
    console.print()
    console.print(f"[green]Done![/green] Exported: {result.chunks_exported} chunks, "
                  f"Skipped: {result.chunks_skipped}, "
                  f"Records: {result.messages_total:,}")
    if result.files_written:
        console.print(f"  Files: {len(result.files_written)}")
    if result.errors:
        for err in result.errors:
            console.print(f"[red]Error:[/red] {err}")


@cli.command("test-opensearch")
def test_opensearch():
    """Test OpenSearch connection."""
    from glogarch.opensearch.client import OpenSearchClient

    settings = get_settings()

    if not settings.opensearch.hosts:
        console.print("[red]Error: opensearch.hosts not configured in config.yaml[/red]")
        return

    console.print(f"Testing OpenSearch: {', '.join(settings.opensearch.hosts)}")

    async def _test():
        async with OpenSearchClient(settings.opensearch) as client:
            return await client.test_connection()

    result = asyncio.run(_test())

    if result.get("connected"):
        console.print(f"[green]Connected![/green]")
        table = Table(title="OpenSearch Cluster Info")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        table.add_row("Cluster", result.get("cluster_name", ""))
        table.add_row("Version", result.get("version", ""))
        table.add_row("Status", result.get("status", ""))
        table.add_row("Nodes", str(result.get("nodes", "")))
        table.add_row("Active Shards", str(result.get("indices", "")))
        console.print(table)
    else:
        console.print(f"[red]Connection failed:[/red] {result.get('error', 'Unknown error')}")


@cli.command("index-sets")
@click.option("--server", "-s", default=None, help="Server name from config")
def index_sets(server: str | None):
    """List available index sets from Graylog."""
    settings = get_settings()
    server_config = settings.get_server(server)

    async def _list():
        from glogarch.graylog.client import GraylogClient
        from glogarch.ratelimit.limiter import RateLimiter
        rl = RateLimiter(settings.rate_limit)
        async with GraylogClient(server_config, rl) as client:
            return await client.get_index_sets()

    index_sets_data = asyncio.run(_list())

    table = Table(title=f"Index Sets ({server_config.name})")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Description")
    table.add_column("Index Prefix")
    table.add_column("Default", justify="center")

    for iset in index_sets_data:
        table.add_row(
            iset.get("id", ""),
            iset.get("title", ""),
            (iset.get("description", "") or "")[:40],
            iset.get("index_prefix", ""),
            "Yes" if iset.get("default", False) else "",
        )

    console.print(table)
    console.print(f"\nUse --index-set <ID> with export command to export all streams in an index set.")


@cli.command("streams")
@click.option("--server", "-s", default=None, help="Server name from config")
def streams(server: str | None):
    """List available streams from Graylog."""
    settings = get_settings()
    server_config = settings.get_server(server)

    async def _list():
        from glogarch.graylog.client import GraylogClient
        from glogarch.ratelimit.limiter import RateLimiter
        rl = RateLimiter(settings.rate_limit)
        async with GraylogClient(server_config, rl) as client:
            return await client.get_streams()

    streams_data = asyncio.run(_list())

    table = Table(title=f"Streams ({server_config.name})")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Index Set")
    table.add_column("Description")

    for s in streams_data:
        table.add_row(
            s.get("id", ""),
            s.get("title", ""),
            s.get("index_set_id", ""),
            (s.get("description", "") or "")[:40],
        )

    console.print(table)


@cli.command("import")
@click.option("--archive-id", "-a", multiple=True, type=int, help="Archive ID(s) to import")
@click.option("--from", "time_from", default=None, help="Import archives from this time")
@click.option("--to", "time_to", default=None, help="Import archives to this time")
@click.option("--server", "-s", default=None, help="Filter archives by source server")
@click.option("--target", "-t", default=None, help="Target server name (for tracking)")
@click.option("--mode", type=click.Choice(["gelf", "bulk"]), default="gelf",
              help="Import mode: 'gelf' (default, goes through Graylog pipeline) "
                   "or 'bulk' (direct OpenSearch _bulk write, 5-10x faster, "
                   "skips Graylog processing rules)")
@click.option("--target-api-url", default=None,
              help="Target Graylog API URL (e.g. http://192.168.1.83:9000) — REQUIRED for compliance pipeline")
@click.option("--target-api-token", default=None, help="Target Graylog API token")
@click.option("--target-api-username", default=None, help="Target Graylog username (alternative to token)")
@click.option("--target-api-password", default=None, help="Target Graylog password")
@click.option("--target-os-url", default=None,
              help="[bulk mode] OpenSearch URL. Auto-detected from Graylog API URL if omitted.")
@click.option("--target-os-username", default=None, help="[bulk mode] OpenSearch username (defaults to Graylog username)")
@click.option("--target-os-password", default=None, help="[bulk mode] OpenSearch password (defaults to Graylog password)")
@click.option("--target-index-pattern", default="jt_restored",
              help="[bulk mode] Target index name prefix. Documents go to <prefix>_YYYY_MM_DD")
@click.option("--dedup-strategy", type=click.Choice(["id", "none", "fail"]), default="id",
              help="[bulk mode] How to handle duplicate gl2_message_id: "
                   "'id' (use as _id, overwrite on re-import), 'none' (always create new), 'fail' (abort on duplicate)")
@click.option("--batch-docs", type=int, default=10000,
              help="[bulk mode] Documents per _bulk request (default 5000)")
@click.option("--no-preflight", is_flag=True, default=False,
              help="DANGEROUS: skip preflight check (no compliance guarantees, no zero-loss promise)")
def import_cmd(archive_id: tuple[int, ...], time_from: str | None, time_to: str | None,
               server: str | None, target: str | None,
               mode: str,
               target_api_url: str | None, target_api_token: str | None,
               target_api_username: str | None, target_api_password: str | None,
               target_os_url: str | None, target_os_username: str | None,
               target_os_password: str | None, target_index_pattern: str,
               dedup_strategy: str, batch_docs: int,
               no_preflight: bool):
    """Import archived logs back into Graylog via GELF.

    Compliance: by default, runs the same pre-flight check as the Web UI:
        1. Verifies target Graylog API credentials
        2. Cluster health + GELF input check
        3. Capacity check (rotation/retention)
        4. Field mapping conflict detection + auto-fix
        5. OpenSearch field-limit override
        6. Index rotation
        7. GELF send (TCP backpressure + journal monitoring)
        8. Post-import indexer-failure reconciliation

    Pass --target-api-url plus either --target-api-token or
    --target-api-username/--target-api-password to enable preflight.
    """
    from glogarch.import_.importer import Importer
    from glogarch.import_.journal_monitor import JournalMonitor
    from glogarch.import_.preflight import PreflightChecker
    from glogarch.import_.bulk import BulkImporter

    settings = get_settings()
    db = _get_db()

    # --- Compliance: validate target API credentials unless explicitly skipped ---
    preflight = None
    journal_monitor = None
    bulk_importer = None
    if no_preflight:
        console.print("[bold red]WARNING:[/bold red] --no-preflight set. "
                      "Import will run WITHOUT compliance checks. "
                      "Indexer failures may go undetected.")
    else:
        if not target_api_url:
            console.print("[bold red]ERROR:[/bold red] --target-api-url is required "
                          "for compliance preflight. Use --no-preflight to bypass "
                          "(not recommended).")
            db.close()
            return
        if not target_api_token and not (target_api_username and target_api_password):
            console.print("[bold red]ERROR:[/bold red] provide either "
                          "--target-api-token or --target-api-username + "
                          "--target-api-password")
            db.close()
            return

        preflight = PreflightChecker(
            api_url=target_api_url,
            api_token=target_api_token or "",
            api_username=target_api_username or "",
            api_password=target_api_password or "",
            gelf_port=settings.import_config.gelf_port,
        )
        journal_monitor = JournalMonitor(
            mode="api",
            api_url=target_api_url,
            api_token=target_api_token or "",
            api_username=target_api_username or "",
            api_password=target_api_password or "",
        )

        # Bulk mode: build BulkImporter
        if mode == "bulk":
            os_url = target_os_url
            if not os_url:
                # Auto-detect from Graylog API URL
                os_url = asyncio.run(preflight.auto_detect_opensearch_url())
                if not os_url:
                    console.print("[bold red]ERROR:[/bold red] Could not auto-detect "
                                  "OpenSearch URL. Use --target-os-url to specify.")
                    db.close()
                    return
                console.print(f"[dim]Auto-detected OpenSearch: {os_url}[/dim]")
            os_user = target_os_username or target_api_username or ""
            os_pass = target_os_password or target_api_password or ""
            bulk_importer = BulkImporter(
                opensearch_url=os_url,
                os_username=os_user,
                os_password=os_pass,
                target_index_pattern=target_index_pattern,
                dedup_strategy=dedup_strategy,
                batch_docs=batch_docs,
            )
            ok, err = asyncio.run(bulk_importer.verify_opensearch())
            if not ok:
                console.print(f"[bold red]ERROR:[/bold red] OpenSearch verification failed: {err}")
                db.close()
                return
            console.print(f"[green]Bulk mode:[/green] writing to {os_url} "
                          f"pattern={target_index_pattern}_*  dedup={dedup_strategy}")

    importer = Importer(
        settings.import_config, settings.export, db,
        journal_monitor=journal_monitor,
        preflight=preflight,
        mode=mode,
        bulk_importer=bulk_importer,
    )

    dt_from = _parse_dt(time_from) if time_from else None
    dt_to = _parse_dt(time_to) if time_to else None
    ids = list(archive_id) if archive_id else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.fields[messages]} msgs)"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing...", total=100, messages=0)

        def _progress(info: dict):
            phase = info.get("phase", "")
            desc = (
                "Pre-flight..."
                if phase == "preflight"
                else f"Archive {info.get('archive_index', 0)}/{info.get('total_archives', 0)}"
            )
            progress.update(task,
                            completed=info.get("pct", 0),
                            description=desc,
                            messages=info.get("messages_done", 0))

        result = asyncio.run(importer.import_archives(
            archive_ids=ids,
            time_from=dt_from,
            time_to=dt_to,
            server_name=server,
            target_server=target,
            progress_callback=_progress,
        ))

    console.print()
    console.print(f"[green]Done![/green] Archives: {result.archives_processed}, "
                  f"Messages sent: {result.messages_sent}")
    for notice in getattr(result, 'notices', []):
        console.print(f"[bold cyan]ⓘ[/bold cyan] {notice}")
    if result.errors:
        for err in result.errors:
            if "Compliance violation" in err:
                console.print(f"[bold yellow]Compliance:[/bold yellow] {err}")
            else:
                console.print(f"[red]Error:[/red] {err}")

    db.close()


@cli.command("list")
@click.option("--server", "-s", default=None, help="Filter by server")
@click.option("--stream", default=None, help="Filter by stream")
@click.option("--from", "time_from", default=None, help="Filter from time")
@click.option("--to", "time_to", default=None, help="Filter to time")
@click.option("--limit", "-n", default=50, help="Max results")
def list_cmd(server: str | None, stream: str | None, time_from: str | None,
             time_to: str | None, limit: int):
    """List archived log files."""
    db = _get_db()

    dt_from = _parse_dt(time_from) if time_from else None
    dt_to = _parse_dt(time_to) if time_to else None

    archives = db.list_archives(server=server, stream=stream,
                                time_from=dt_from, time_to=dt_to)

    if not archives:
        console.print("[yellow]No archives found.[/yellow]")
        db.close()
        return

    table = Table(title="Archives", show_lines=True)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Server", style="green")
    table.add_column("Stream")
    table.add_column("From")
    table.add_column("To")
    table.add_column("Messages", justify="right")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Status")
    table.add_column("Parts", justify="right")

    for a in archives[:limit]:
        size_mb = f"{a.file_size_bytes / 1024 / 1024:.2f}"
        status_style = "green" if a.status.value == "completed" else "red"
        table.add_row(
            str(a.id),
            a.server_name,
            a.stream_name or a.stream_id or "all",
            a.time_from.strftime("%Y-%m-%d %H:%M") if a.time_from else "",
            a.time_to.strftime("%Y-%m-%d %H:%M") if a.time_to else "",
            str(a.message_count),
            size_mb,
            f"[{status_style}]{a.status.value}[/{status_style}]",
            f"{a.part_number}/{a.total_parts}",
        )

    console.print(table)
    console.print(f"Showing {min(len(archives), limit)} of {len(archives)} archives")
    db.close()


@cli.command()
@click.option("--server", "-s", default=None, help="Verify only archives from this server")
@click.option("--workers", "-w", default=1, type=int,
              help="Number of parallel SHA256 workers (default: 1)")
def verify(server: str | None, workers: int):
    """Verify archive file integrity."""
    from glogarch.verify.verifier import Verifier

    settings = get_settings()
    db = _get_db()
    verifier = Verifier(settings.export, db)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Verifying...", total=100)

        def _progress(info: dict):
            total = info.get("total", 1)
            current = info.get("current", 0)
            pct = (current / total) * 100 if total else 100
            progress.update(task, completed=pct,
                            description=f"Checking {current}/{total}")

        result = verifier.verify_all(server=server, progress_callback=_progress,
                                     workers=workers)

    console.print()
    console.print(f"[bold]Verification Report[/bold]")
    console.print(f"  Total checked: {result.total_checked}")
    console.print(f"  [green]Valid:[/green] {result.valid}")
    if result.corrupted:
        console.print(f"  [red]Corrupted:[/red] {len(result.corrupted)}")
        for f in result.corrupted:
            console.print(f"    - {f}")
    if result.missing_files:
        console.print(f"  [yellow]Missing files:[/yellow] {len(result.missing_files)}")
        for f in result.missing_files:
            console.print(f"    - {f}")
    if result.orphan_files:
        console.print(f"  [yellow]Orphan files:[/yellow] {len(result.orphan_files)}")
        for f in result.orphan_files:
            console.print(f"    - {f}")

    db.close()


@cli.command()
@click.option("--days", "-d", default=None, type=int, help="Override retention days")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
def cleanup(days: int | None, dry_run: bool):
    """Clean up expired archives based on retention policy."""
    from glogarch.cleanup.cleaner import Cleaner

    settings = get_settings()
    db = _get_db()
    cleaner = Cleaner(settings.retention, settings.export, db)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Cleaning up...", total=100)

        def _progress(info: dict):
            total = info.get("total", 1)
            current = info.get("current", 0)
            pct = (current / total) * 100 if total else 100
            progress.update(task, completed=pct,
                            description=f"{'[DRY RUN] ' if dry_run else ''}Deleting {current}/{total}")

        result = cleaner.cleanup(retention_days=days, dry_run=dry_run,
                                 progress_callback=_progress)

    prefix = "[DRY RUN] " if dry_run else ""
    console.print()
    console.print(f"[green]{prefix}Cleanup completed[/green]")
    console.print(f"  Files deleted: {result.files_deleted}")
    console.print(f"  Space freed: {result.bytes_freed / 1024 / 1024:.2f} MB")
    if result.errors:
        for err in result.errors:
            console.print(f"  [red]Error:[/red] {err}")

    db.close()


@cli.command()
def status():
    """Show system status and archive statistics."""
    from glogarch.archive.storage import ArchiveStorage

    settings = get_settings()
    db = _get_db()
    storage = ArchiveStorage(settings.export)

    # DB stats
    stats = db.get_archive_stats()
    storage_stats = storage.get_storage_stats()

    console.print("[bold]Glogarch System Status[/bold]")
    console.print()

    table = Table(title="Archive Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total archives", str(stats.get("total", 0)))
    table.add_row("Total messages", f"{stats.get('total_messages', 0):,}")
    total_bytes = stats.get("total_bytes", 0)
    table.add_row("Total size", f"{total_bytes / 1024 / 1024:.2f} MB")
    table.add_row("Earliest archive", str(stats.get("earliest", "N/A")))
    table.add_row("Latest archive", str(stats.get("latest", "N/A")))
    table.add_row("Disk available", f"{storage_stats.get('available_mb', 0):.0f} MB")
    table.add_row("Archive path", str(settings.export.base_path))

    console.print(table)

    # Server configs
    console.print()
    srv_table = Table(title="Configured Servers")
    srv_table.add_column("Name", style="cyan")
    srv_table.add_column("URL")
    srv_table.add_column("Auth")

    for srv in settings.servers:
        auth_type = "token" if srv.auth_token else ("basic" if srv.username else "none")
        srv_table.add_row(srv.name, srv.url, auth_type)

    console.print(srv_table)

    # Recent jobs
    jobs = db.list_jobs(limit=5)
    if jobs:
        console.print()
        job_table = Table(title="Recent Jobs")
        job_table.add_column("ID", style="cyan", max_width=8)
        job_table.add_column("Type")
        job_table.add_column("Status")
        job_table.add_column("Progress")
        job_table.add_column("Messages")
        job_table.add_column("Started")

        for j in jobs:
            status_style = {"completed": "green", "failed": "red", "running": "yellow"}.get(j.status.value, "")
            job_table.add_row(
                j.id[:8],
                j.job_type.value if hasattr(j.job_type, 'value') else j.job_type,
                f"[{status_style}]{j.status.value}[/{status_style}]",
                f"{j.progress_pct:.0f}%",
                f"{j.messages_done:,}" + (f"/{j.messages_total:,}" if j.messages_total else ""),
                j.started_at.strftime("%Y-%m-%d %H:%M") if j.started_at else "",
            )

        console.print(job_table)

    db.close()


@cli.command()
@click.argument("action", type=click.Choice(["list", "enable", "disable"]))
@click.option("--name", "-n", default=None, help="Schedule name")
def schedule(action: str, name: str | None):
    """Manage export/cleanup schedules."""
    db = _get_db()
    settings = get_settings()

    if action == "list":
        schedules = db.list_schedules()
        if not schedules:
            console.print("[yellow]No schedules configured.[/yellow]")
        else:
            table = Table(title="Schedules")
            table.add_column("Name", style="cyan")
            table.add_column("Type")
            table.add_column("Cron")
            table.add_column("Enabled")
            table.add_column("Last Run")
            table.add_column("Next Run")
            for s in schedules:
                table.add_row(
                    s.name, s.job_type, s.cron_expr,
                    "[green]Yes[/green]" if s.enabled else "[red]No[/red]",
                    s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "Never",
                    s.next_run_at.strftime("%Y-%m-%d %H:%M") if s.next_run_at else "",
                )
            console.print(table)

    elif action in ("enable", "disable"):
        if not name:
            console.print("[red]--name is required for enable/disable[/red]")
            return
        schedules = db.list_schedules()
        found = [s for s in schedules if s.name == name]
        if not found:
            console.print(f"[red]Schedule '{name}' not found[/red]")
            return
        s = found[0]
        s.enabled = action == "enable"
        db.save_schedule(s)
        console.print(f"Schedule '{name}' {'enabled' if s.enabled else 'disabled'}")

    db.close()


@cli.command()
def server():
    """Start the Web UI server (HTTPS)."""
    from glogarch.web.app import create_app
    import uvicorn
    from pathlib import Path

    settings = get_settings()
    app = create_app()

    ssl_opts = {}
    certfile = Path(settings.web.ssl_certfile)
    keyfile = Path(settings.web.ssl_keyfile)
    if certfile.exists() and keyfile.exists():
        ssl_opts["ssl_certfile"] = str(certfile)
        ssl_opts["ssl_keyfile"] = str(keyfile)
        console.print(f"[bold]Starting jt-glogarch web server on "
                      f"https://{settings.web.host}:{settings.web.port}[/bold]")
    else:
        console.print(f"[yellow]SSL certificate not found at {certfile}, running without HTTPS[/yellow]")
        console.print(f"[bold]Starting jt-glogarch web server on "
                      f"http://{settings.web.host}:{settings.web.port}[/bold]")

    uvicorn.run(app, host=settings.web.host, port=settings.web.port,
                log_level="info", **ssl_opts)


@cli.command()
@click.option("--output", "-o", default="config.yaml", help="Output path")
def config(output: str):
    """Generate example config.yaml."""
    example = """\
# jt-glogarch Configuration
servers:
  - name: graylog-main
    url: "http://192.168.1.132:9000"
    # Use either auth_token or username/password
    # auth_token: "your-api-token-here"
    username: admin
    password: admin
    verify_ssl: false

default_server: graylog-main

export:
  base_path: /data/graylog-archives
  chunk_duration_minutes: 60
  max_file_size_mb: 100
  query: "*"
  streams: []
  fields: []
  batch_size: 1000
  min_disk_space_mb: 500

import:
  gelf_host: localhost
  gelf_port: 32202
  gelf_protocol: tcp     # tcp (recommended, has backpressure) or udp
  batch_size: 500
  delay_between_batches_ms: 100

retention:
  enabled: true
  retention_days: 180

rate_limit:
  requests_per_second: 5.0
  adaptive: true
  max_cpu_percent: 80.0
  backoff_seconds: 10.0

schedule:
  export_cron: "0 * * * *"
  export_days: 180
  cleanup_cron: "0 3 * * *"

web:
  host: "0.0.0.0"
  port: 8990

database_path: /opt/jt-glogarch/jt-glogarch.db
log_level: INFO
"""
    from pathlib import Path
    Path(output).write_text(example)
    console.print(f"[green]Example config written to {output}[/green]")


@cli.command("streams-cleanup")
@click.option("--server", "-s", default=None, help="Server name from config")
@click.option("--prefix", default="jt_restored",
              help="Stream/index-set name prefix to scan (default: jt_restored)")
@click.option("--dry-run", is_flag=True, help="List only, do not delete")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def streams_cleanup(server: str | None, prefix: str, dry_run: bool, yes: bool):
    """List/delete restored Streams + Index Sets created by jt-glogarch.

    Repeated bulk imports leave behind one Stream + Index Set per target
    pattern. Use this to clean up after testing or when retiring an
    archive set. Both the Graylog Stream and the underlying Index Set are
    removed (Graylog also drops the OpenSearch indices).
    """
    import asyncio
    import httpx
    settings = get_settings()
    sc = settings.get_server(server)

    async def _run():
        auth = None
        headers = {"Accept": "application/json", "X-Requested-By": "jt-glogarch-cli"}
        if sc.auth_token:
            auth = (sc.auth_token, "token")
        elif sc.username:
            auth = (sc.username, sc.password or "")

        async with httpx.AsyncClient(verify=False, timeout=30, auth=auth, headers=headers) as c:
            # Streams
            r = await c.get(f"{sc.url}/api/streams")
            r.raise_for_status()
            streams = [s for s in r.json().get("streams", [])
                       if (s.get("title") or "").startswith(prefix)]
            r = await c.get(f"{sc.url}/api/system/indices/index_sets")
            r.raise_for_status()
            isets = [s for s in r.json().get("index_sets", [])
                     if (s.get("index_prefix") or "").startswith(prefix)]

            console.print(f"[bold]Streams matching '{prefix}*':[/bold] {len(streams)}")
            for s in streams:
                console.print(f"  - {s.get('title')} ({s.get('id')})")
            console.print(f"[bold]Index sets matching '{prefix}*':[/bold] {len(isets)}")
            for s in isets:
                console.print(f"  - {s.get('title')} (prefix={s.get('index_prefix')}, id={s.get('id')})")

            if dry_run or (not streams and not isets):
                return

            if not yes:
                if not click.confirm(
                    f"Delete {len(streams)} stream(s) and {len(isets)} index set(s)? "
                    "This cannot be undone."
                ):
                    return

            for s in streams:
                rr = await c.delete(f"{sc.url}/api/streams/{s['id']}")
                if rr.status_code in (200, 204):
                    console.print(f"[green]Deleted stream:[/green] {s.get('title')}")
                else:
                    console.print(f"[red]Failed to delete stream {s.get('title')}: HTTP {rr.status_code}[/red]")
            for s in isets:
                rr = await c.delete(f"{sc.url}/api/system/indices/index_sets/{s['id']}?delete_indices=true")
                if rr.status_code in (200, 204):
                    console.print(f"[green]Deleted index set:[/green] {s.get('title')}")
                else:
                    console.print(f"[red]Failed to delete index set {s.get('title')}: HTTP {rr.status_code}[/red]")

    asyncio.run(_run())


@cli.command("db-backup")
@click.option("--dest", "-d", default="/var/backups/jt-glogarch",
              help="Backup directory")
@click.option("--keep", default=14, type=int,
              help="Number of backups to keep (older are pruned)")
def db_backup(dest: str, keep: int):
    """Snapshot the SQLite metadata DB to a backup directory.

    Uses SQLite's online .backup API — safe to run while jt-glogarch is
    actively writing. Recommended cron entry::

        0 4 * * * /usr/bin/python3 -m glogarch db-backup
    """
    from pathlib import Path
    from glogarch.maintenance.db_rebuild import backup_db, prune_backups
    settings = get_settings()
    src = Path(settings.database_path)
    dest_p = Path(dest)
    try:
        out = backup_db(src, dest_p)
    except Exception as e:
        console.print(f"[red]Backup failed:[/red] {e}")
        sys.exit(1)
    pruned = prune_backups(dest_p, keep=keep)
    size_mb = out.stat().st_size / 1024 / 1024
    console.print(f"[green]Backup written:[/green] {out} ({size_mb:.2f} MB)")
    if pruned:
        console.print(f"[dim]Pruned {pruned} old backup(s)[/dim]")


@cli.command("db-rebuild")
@click.option("--archive-root", "-r", default=None,
              help="Override archive base path (default: from config)")
@click.option("--dry-run", is_flag=True,
              help="Show what would be inserted without writing")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def db_rebuild(archive_root: str | None, dry_run: bool, yes: bool):
    """Rebuild SQLite metadata DB by scanning the archive directory.

    Use this after disaster recovery: if the SQLite DB is lost or corrupted,
    this command walks the archive root, reads each .json.gz metadata block
    + its .sha256 sidecar, and inserts a row per file. Existing rows are
    preserved (no duplicates).
    """
    from pathlib import Path
    from glogarch.maintenance.db_rebuild import rebuild
    settings = get_settings()
    root = Path(archive_root) if archive_root else Path(settings.export.base_path)

    if not yes and not dry_run:
        console.print(f"[yellow]About to scan {root} and insert any missing "
                      f"archives into {settings.database_path}[/yellow]")
        if not click.confirm("Continue?"):
            return

    db = _get_db()
    try:
        summary = rebuild(db, root, dry_run=dry_run)
    except Exception as e:
        console.print(f"[red]Rebuild failed:[/red] {e}")
        sys.exit(1)

    table = Table(title="DB Rebuild Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    for k, v in summary.items():
        table.add_row(k, str(v))
    console.print(table)
    if dry_run:
        console.print("[dim]Dry run — no changes written[/dim]")

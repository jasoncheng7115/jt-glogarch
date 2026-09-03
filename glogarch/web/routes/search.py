# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Record search across archives — HTTP surface.

A search is a background job, not a request: scanning even a day of one index
takes tens of seconds, and a wide range takes minutes. So `POST /api/search`
starts a worker and returns immediately; the page polls for progress and for
the hits found so far, exactly as it does for an export.

`POST /api/search/{id}/more` continues from the engine's cursor rather than
re-running the query — archives already scanned are never opened again.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from glogarch.search.engine import SearchQuery, iter_all_hits, run_search
from glogarch.utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter()

# Live searches, newest last. Bounded: each retains at most MAX_RETAINED_HITS
# results (~1.8 KB per message), and old searches are pruned, because this is
# in-process memory on a box that is already tight enough to OOM on import.
_searches: dict[str, dict] = {}
_searches_lock = threading.Lock()

MAX_LIVE_SEARCHES = 5
MAX_RETAINED_HITS = 5000        # a browser cannot usefully render more anyway
DEFAULT_PAGE = 500
MAX_PAGE = 5000

# Measured on real archives: a non-matching archive costs ~1.6 s (chunked byte
# prefilter), one that matches also pays ~8.5 s to parse. Most archives in a
# range do not match, so the prefilter cost dominates the estimate.
_SEC_PER_ARCHIVE = 1.7


def _prune_locked() -> None:
    while len(_searches) > MAX_LIVE_SEARCHES:
        oldest = min(_searches, key=lambda k: _searches[k]["started_at"])
        _searches.pop(oldest, None)


def _parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _err(code: str, message: str, value: str = "") -> dict:
    """A refusal the UI can translate.

    The English text is kept as a fallback for API clients and logs, but the
    UI must not show it verbatim: a Chinese interface answering "Enter a
    keyword or a field filter" is our own message leaking untranslated.
    """
    out = {"code": code, "error": message}
    if value:
        out["value"] = value
    return out


def _parse_field_filters(raw: str) -> tuple[dict, dict | None]:
    """`source=fw01 level=4` -> {source: fw01, level: 4}."""
    out = {}
    for part in (raw or "").split():
        k, _, v = part.partition("=")
        k, v = k.strip(), v.strip()
        if not _ or not k or not v:
            return {}, _err("filter_format",
                            f"Field filter must look like field=value: {part!r}",
                            part)
        out[k] = v
    return out, None


def _parse_terms(raw: str) -> list[str]:
    """Split keywords on whitespace, but keep a quoted phrase together.

    Without this there is no way to search for a phrase that contains a space:
    `connection refused` would become two independent terms and match any
    message holding both words anywhere, which is not what was asked for.
    `"connection refused"` is one term.

    shlex handles the quoting rules; an unbalanced quote is a typo mid-edit,
    not an error worth refusing, so fall back to a plain split rather than
    rejecting what the user is still typing.
    """
    import shlex
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    return [p for p in (t.strip() for t in parts) if p]


def _build_query(body: dict) -> tuple[SearchQuery | None, dict | None]:
    time_from = _parse_dt(body.get("time_from"))
    time_to = _parse_dt(body.get("time_to"))
    if time_from is None or time_to is None:
        # The time range is the ONLY index this search has. Without it the
        # scan is the whole corpus, so it is required rather than defaulted.
        return None, _err("range_required", "time_from and time_to are required")
    if time_to <= time_from:
        return None, _err("range_order", "time_to must be after time_from")

    filters, err = _parse_field_filters(body.get("field_filters") or "")
    if err:
        return None, err

    terms = _parse_terms(body.get("q") or "")
    if not terms and not filters:
        return None, _err("need_query", "Enter a keyword or a field filter")

    try:
        page = int(body.get("limit") or DEFAULT_PAGE)
    except (TypeError, ValueError):
        return None, _err("limit_nan", "limit must be a number")
    page = max(1, min(page, MAX_PAGE))

    return SearchQuery(
        terms=terms, field_filters=filters,
        time_from=time_from, time_to=time_to,
        server=(body.get("server") or "").strip() or None,
        stream_id=(body.get("stream_id") or "").strip() or None,
        max_results=page,
    ), None


@router.post("/search/plan")
async def plan_search(request: Request):
    """How much work would this search be? Pure SQL — opens no archive.

    Shown before the user commits, because on this data set the difference
    between a one-hour and a one-month range is seconds versus tens of
    minutes, and that must not be a surprise discovered halfway through.
    """
    body = await request.json()
    q, err = _build_query(body)
    if err:
        return JSONResponse(err, status_code=400)

    db = request.app.state.db
    records = db.list_archives_for_search(
        server=q.server, stream_id=q.stream_id,
        time_from=q.time_from, time_to=q.time_to)
    messages = sum(int(getattr(r, "message_count", 0) or 0) for r in records)
    return {
        "archives": len(records),
        "messages": messages,
        "estimated_seconds": round(len(records) * _SEC_PER_ARCHIVE),
    }


def _yield_to_archiving() -> None:
    """Search gives way to archiving: same disk, and archiving is the product.

    A short sleep per archive is enough — it hands the disk back between files
    without stalling the search outright.
    """
    try:
        from glogarch.export.exporter import _export_lock
        from glogarch.opensearch.exporter import _os_export_lock
        if _export_lock or _os_export_lock:
            time.sleep(0.25)
    except Exception as e:
        log.warning("Could not check archiving state while searching", error=str(e))


def _run(search_id: str, db, q: SearchQuery) -> None:
    st = _searches.get(search_id)
    if st is None:
        return

    def _cancel():
        return bool(_searches.get(search_id, {}).get("cancel"))

    # Hits are published as each archive finishes, not held until the whole
    # page is scanned. A wide range takes minutes; showing the first results
    # after two seconds rather than after four minutes is the difference
    # between "working" and "stuck", and costs nothing — they are already in
    # memory. `copied` tracks how much of out.hits has been handed over so the
    # final flush cannot duplicate them.
    copied = 0

    def _publish(out):
        nonlocal copied
        s = _searches.get(search_id)
        if s is None:
            return
        fresh = out.hits[copied:]
        if fresh:
            s["hits"].extend(_hit_to_dict(h) for h in fresh)
            copied = len(out.hits)
            del s["hits"][MAX_RETAINED_HITS:]
        s["archives_scanned"] = out.archives_scanned
        s["archives_total"] = out.archives_total
        s["messages_examined"] = out.messages_examined
        s["hit_count"] = len(s["hits"])

    try:
        res = run_search(db, q, progress_cb=_publish, cancel_check=_cancel,
                         yield_cb=_yield_to_archiving)
        _publish(res)                      # flush whatever the last archive found
        del st["hits"][MAX_RETAINED_HITS:]
        st.update(
            archives_total=res.archives_total,
            archives_scanned=res.archives_scanned,
            archives_parsed=st.get("archives_parsed", 0) + res.archives_parsed,
            messages_examined=st.get("messages_examined", 0) + res.messages_examined,
            hit_count=len(st["hits"]),
            truncated=res.truncated,
            cancelled=res.cancelled,
            next_start_archive=res.next_start_archive,
            next_skip_in_archive=res.next_skip_in_archive,
            errors=res.errors[:10],
            duration_seconds=st.get("duration_seconds", 0.0) + res.duration_seconds,
            status="cancelled" if res.cancelled else "done",
        )
    except Exception as e:
        log.error("Archive search failed", search=search_id, error=str(e))
        st.update(status="failed", error=str(e))


def _hit_to_dict(h) -> dict:
    return {
        "timestamp": h.timestamp, "source": h.source, "level": h.level,
        "message": h.message, "doc": h.doc,
        "archive_id": h.archive_id, "archive_file": h.archive_file,
    }


def _start_worker(search_id: str, db, q: SearchQuery) -> None:
    threading.Thread(target=_run, args=(search_id, db, q), daemon=True,
                     name=f"archive-search-{search_id[:8]}").start()


@router.post("/search")
async def start_search(request: Request):
    body = await request.json()
    q, err = _build_query(body)
    if err:
        return JSONResponse(err, status_code=400)

    # Count the archives BEFORE returning, with the same cheap SQL /plan uses.
    # Otherwise the first poll arrives before the worker has started and the
    # page shows "0 / 0" with an empty bar — indistinguishable from a search
    # that is not running at all.
    try:
        _total = len(request.app.state.db.list_archives_for_search(
            server=q.server, stream_id=q.stream_id,
            time_from=q.time_from, time_to=q.time_to))
    except Exception as e:
        log.warning("Could not pre-count archives for the search", error=str(e))
        _total = 0

    search_id = str(uuid.uuid4())
    with _searches_lock:
        _searches[search_id] = {
            "id": search_id, "status": "running", "started_at": time.time(),
            "hits": [], "hit_count": 0, "archives_total": _total,
            "archives_scanned": 0, "archives_parsed": 0,
            "messages_examined": 0, "duration_seconds": 0.0,
            "truncated": False, "cancelled": False, "cancel": False,
            "next_start_archive": None, "next_skip_in_archive": 0,
            "errors": [], "query": {
                "q": body.get("q") or "", "field_filters": body.get("field_filters") or "",
                "time_from": str(q.time_from), "time_to": str(q.time_to),
                "server": q.server or "", "stream_id": q.stream_id or "",
                "limit": q.max_results,
            },
        }
        _prune_locked()

    _start_worker(search_id, request.app.state.db, q)
    try:
        db = request.app.state.db
        db.audit("search_started", f"q={body.get('q','')!r} range={q.time_from}..{q.time_to}",
                 request.session.get("username", ""),
                 request.client.host if request.client else "")
    except Exception as e:
        log.warning("Could not audit the search", error=str(e))
    return {"search_id": search_id, "status": "running"}


# --- Download the whole result set -----------------------------------------
#
# Deliberately NOT "download what is on screen". The page holds one capped
# page of hits; the answer to "export this search" is every record in the
# range that matches, which is what an evidence request or a hand-off to
# another tool needs.
#
# Three constraints shaped this:
#   - Memory. `iter_all_hits` yields one record at a time and retains none,
#     so peak footprint is a single row whether the export is 500 rows or
#     five million. It also reads each archive ONCE: the paged resume that
#     serves the screen re-parses the archive it stopped inside, which is
#     quadratic over a whole download (three 1,000-row pages on staging
#     examined 220K, 531K then 464K messages for the same work).
#   - The event loop. The generator below is SYNCHRONOUS, so Starlette runs it
#     in a threadpool; gzip and JSON parsing never block the loop and the rest
#     of the UI keeps responding while a long download streams.
#   - Honesty about limits. A cap that silently drops rows would turn a
#     partial export into what looks like a complete one, so the cap is
#     generous, stated in the UI, and MARKED IN THE FILE when it is reached.
MAX_EXPORT_ROWS = 1_000_000
CSV_COLUMNS = ["timestamp", "source", "level", "message", "archive_file"]


def _csv_row(values: list) -> str:
    import csv
    import io as _io
    buf = _io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()


def _export_rows(db, q: SearchQuery, fmt: str):
    """Yield the export row by row. Sync on purpose — see above."""
    import json

    rows = 0
    truncated = False

    if fmt == "csv":
        # BOM first: Excel reads a UTF-8 CSV without one as Latin-1 and turns
        # every Chinese field into mojibake, which is most of the audience.
        yield "﻿" + _csv_row(CSV_COLUMNS)

    for h in iter_all_hits(db, q, yield_cb=_yield_to_archiving):
        if rows >= MAX_EXPORT_ROWS:
            truncated = True
            break
        if fmt == "csv":
            yield _csv_row([h.timestamp, h.source, h.level, h.message,
                            h.archive_file])
        else:
            # The record exactly as archived, plus its provenance under a
            # namespaced key that cannot collide with a Graylog field.
            yield json.dumps({**h.doc, "_jt_source_archive": h.archive_file},
                             ensure_ascii=False, default=str) + "\n"
        rows += 1

    if truncated:
        note = (f"TRUNCATED at {MAX_EXPORT_ROWS:,} rows — narrow the time "
                f"range and export again to get the rest")
        log.warning("Search export hit the row ceiling", rows=rows)
        if fmt == "csv":
            yield _csv_row(["", "", "", note, ""])
        else:
            yield json.dumps({"_jt_note": note}) + "\n"
    log.info("Search export finished", rows=rows, fmt=fmt, truncated=truncated)


@router.get("/search/export")
async def export_search(request: Request):
    """Stream every matching record as CSV or JSON Lines.

    A GET taking query parameters, not a POST taking JSON, so the browser can
    do the download itself: `location.href = ...` hands the stream straight to
    the disk writer. `fetch()` + `blob()` would hold the ENTIRE export in the
    tab's memory before the save dialog appears — the one thing this must not
    do — and a form POST cannot carry a JSON body. Nothing here changes state.
    """
    from fastapi.responses import StreamingResponse

    body = dict(request.query_params)
    q, err = _build_query(body)
    if err:
        return JSONResponse(err, status_code=400)

    fmt = (body.get("format") or "csv").strip().lower()
    if fmt not in ("csv", "jsonl"):
        return JSONResponse(_err("bad_format", "format must be csv or jsonl", fmt),
                            status_code=400)

    stamp = q.time_from.strftime("%Y%m%dT%H%M") + "_" + q.time_to.strftime("%Y%m%dT%H%M")
    name = f"jt-glogarch-search_{stamp}.{'csv' if fmt == 'csv' else 'jsonl'}"
    media = "text/csv; charset=utf-8" if fmt == "csv" else "application/x-ndjson"

    # Taking records OUT of the archive is data egress, so it is audited like
    # any other state-changing operation — who exported what, and over which
    # range.
    try:
        request.app.state.db.audit(
            "search_exported",
            f"format={fmt} q={body.get('q','')!r} range={q.time_from}..{q.time_to}",
            request.session.get("username", ""),
            request.client.host if request.client else "")
    except Exception as e:
        log.warning("Could not audit the search export", error=str(e))

    return StreamingResponse(
        _export_rows(request.app.state.db, q, fmt),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"',
                 # The length is unknown until the scan ends, so the browser
                 # shows an indeterminate download. Say so rather than letting
                 # it look stalled.
                 "X-Accel-Buffering": "no"},
    )


@router.get("/search/{search_id}")
async def get_search(search_id: str, offset: int = 0):
    st = _searches.get(search_id)
    if st is None:
        return JSONResponse(_err("gone", "unknown or expired search"),
                            status_code=404)
    offset = max(0, int(offset or 0))
    return {
        **{k: v for k, v in st.items() if k not in ("hits", "cancel")},
        "hits": st["hits"][offset:],
        "offset": offset,
        # None means the range is exhausted; the UI can then say "that is all"
        # instead of leaving the reader unsure whether it stopped early.
        "has_more": st.get("next_start_archive") is not None,
    }


@router.post("/search/{search_id}/cancel")
async def cancel_search(search_id: str):
    st = _searches.get(search_id)
    if st is None:
        return JSONResponse(_err("gone", "unknown or expired search"),
                            status_code=404)
    st["cancel"] = True
    log.info("Archive search cancel requested", search=search_id)
    return {"ok": True}


@router.post("/search/{search_id}/more")
async def search_more(search_id: str, request: Request):
    """Continue from where the last page stopped, not from the beginning."""
    st = _searches.get(search_id)
    if st is None:
        return JSONResponse(_err("gone", "unknown or expired search"),
                            status_code=404)
    if st.get("status") == "running":
        return JSONResponse(_err("still_running", "search still running"),
                            status_code=409)
    if st.get("next_start_archive") is None:
        return JSONResponse(_err("exhausted", "no more results in this range"),
                            status_code=409)
    if len(st["hits"]) >= MAX_RETAINED_HITS:
        return JSONResponse(
            _err("ceiling",
                 f"Reached the {MAX_RETAINED_HITS:,}-result ceiling for one "
                 f"search. Narrow the time range to see more.",
                 f"{MAX_RETAINED_HITS:,}"),
            status_code=409)

    q, err = _build_query(st["query"])
    if err:
        return JSONResponse(err, status_code=400)
    q.start_archive = int(st["next_start_archive"])
    q.skip_in_archive = int(st["next_skip_in_archive"])

    st.update(status="running", cancel=False, truncated=False, cancelled=False)
    _start_worker(search_id, request.app.state.db, q)
    return {"search_id": search_id, "status": "running"}

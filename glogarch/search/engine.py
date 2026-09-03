# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Search records inside archives.

There is no index. The whole corpus is gzipped JSON on disk — 173 GB and 1.06
billion messages on one test box, more at customer sites — so the design is
entirely about NOT reading most of it:

  1. Prune in SQL. `archives` already stores time_from/time_to, server,
     stream and the field schema, so the time range (mandatory) plus the
     optional server/stream filter usually eliminates >99% of archives before
     a single file is opened. This is the whole performance story.

  2. Two-stage scan of what survives. Measured on a real 49.5 MB / 303,825
     message archive:
         chunked byte prefilter, no match  1.57 s     (peak RSS +8 MB)
         chunked byte prefilter, early hit 0.01 s
         full streaming JSON parse         8.54 s
     So a term that is absent costs 1.57 s instead of 8.54 s — 5x — and only
     archives that really contain it pay the parse.

Why the prefilter reads fixed-size chunks rather than lines: the writer emits
one continuous JSON document with NO newlines at all. A line-oriented read
(what `zgrep` does) returns the entire decompressed archive as a single 698 MB
object — measured peak RSS +1,334 MB, on boxes that are already tight enough
to OOM during an import. Chunked reading is both faster and uses ~8 MB.
"""
from __future__ import annotations

import gzip
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from glogarch.utils.logging import get_logger

log = get_logger(__name__)

# 4 MiB decompressed window. Large enough that per-chunk overhead is noise,
# small enough that peak memory stays flat regardless of archive size.
CHUNK_BYTES = 4 * 1024 * 1024

# Characters JSON escapes inside a string. A term containing one of these would
# appear differently in the file than in the user's input, so the byte
# prefilter could MISS an archive that genuinely matches. Missing results is
# the one failure this design must never have, so such terms skip stage 1 and
# every candidate archive is parsed instead — slower, but correct.
_JSON_ESCAPED = set('"\\\n\r\t\b\f')


@dataclass
class SearchQuery:
    """What to look for. `terms` are ANDed, and so are `field_filters`."""
    terms: list[str] = field(default_factory=list)
    field_filters: dict[str, str] = field(default_factory=dict)
    time_from: datetime | None = None
    time_to: datetime | None = None
    server: str | None = None
    stream_id: str | None = None
    max_results: int = 500
    # Resume point, so "load more" continues instead of re-scanning. Archives
    # are visited in a deterministic order, so a cursor of (which archive,
    # how many hits already returned from it) resumes exactly. Only that ONE
    # archive is re-parsed; everything already scanned is never touched again.
    start_archive: int = 0
    skip_in_archive: int = 0

    def normalised_terms(self) -> list[str]:
        return [t.strip().lower() for t in self.terms if t and t.strip()]

    def prefilter_needles(self) -> list[bytes]:
        """Terms safe to look for in the raw file bytes (see _JSON_ESCAPED)."""
        out = []
        for t in self.normalised_terms():
            if any(c in _JSON_ESCAPED for c in t):
                continue
            out.append(t.encode("utf-8"))
        return out


@dataclass
class SearchHit:
    timestamp: str
    source: str
    level: str
    message: str
    doc: dict
    archive_id: int
    archive_file: str


@dataclass
class SearchResult:
    hits: list[SearchHit] = field(default_factory=list)
    archives_total: int = 0
    archives_scanned: int = 0
    archives_parsed: int = 0        # survived the prefilter
    messages_examined: int = 0
    duration_seconds: float = 0.0
    truncated: bool = False         # page filled; more may exist
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)
    # Where to resume for the next page; None means the range is exhausted —
    # which is what lets the UI say "that is all of them" instead of leaving
    # the reader unsure whether the search simply stopped early.
    next_start_archive: int | None = None
    next_skip_in_archive: int = 0


def archive_may_contain(path: Path, needles: list[bytes]) -> bool:
    """Stage 1 — could this archive contain every needle?

    Over-selection is safe (stage 2 rejects), under-selection is not: a missed
    archive is a silently missing result. So an empty needle list means "yes,
    parse it", and any read error also means "yes" rather than skipping data.
    """
    if not needles:
        return True
    try:
        remaining = set(needles)
        overlap = max(len(n) for n in needles) - 1
        tail = b""
        with gzip.open(path, "rb") as f:
            while remaining:
                chunk = f.read(CHUNK_BYTES)
                if not chunk:
                    break
                hay = (tail + chunk).lower()
                for n in tuple(remaining):
                    if n in hay:
                        remaining.discard(n)
                tail = chunk[-overlap:] if overlap > 0 else b""
        return not remaining
    except Exception as e:
        # Never let an unreadable archive silently drop out of the result set.
        log.warning("Search prefilter failed, parsing the archive anyway",
                    path=str(path), error=str(e))
        return True


def _message_matches(msg: dict, terms: list[str], filters: dict[str, str]) -> bool:
    """Stage 2 — does this one message satisfy every term and field filter?

    Terms match a substring of ANY field's value, case-insensitively. Stage 1
    searched the raw JSON, which contains every value, so anything matched here
    was also visible there — the prefilter can over-select but never under-.
    """
    for k, want in filters.items():
        v = msg.get(k)
        if v is None or str(v).lower() != want:
            return False
    if not terms:
        return True
    remaining = set(terms)
    for v in msg.values():
        if v is None:
            continue
        s = str(v).lower()
        for t in tuple(remaining):
            if t in s:
                remaining.discard(t)
        if not remaining:
            return True
    return not remaining


# How often a long archive reports what it has found so far. Time-based, not
# every-N-messages, so the cost is bounded whatever the archive size: a 300K
# message file would otherwise fire 600 callbacks, a small one none at all.
PROGRESS_INTERVAL_SEC = 0.4


def _make_hit(msg: dict, record, path: Path) -> SearchHit:
    """One place that decides what a hit looks like, for every caller."""
    return SearchHit(
        timestamp=str(msg.get("timestamp") or ""),
        source=str(msg.get("source") or ""),
        level=str(msg.get("level") if msg.get("level") is not None else ""),
        message=str(msg.get("message") or msg.get("full_message") or ""),
        doc=msg,
        archive_id=getattr(record, "id", 0) or 0,
        archive_file=path.name,
    )


def iter_all_hits(db, query: SearchQuery, *, cancel_check=None, yield_cb=None):
    """Yield every matching message, one at a time, and retain nothing.

    `run_search` below is built for a SCREEN: it stops at max_results and
    resumes by re-parsing the archive it stopped inside, because gzip cannot
    seek. Over a few "load more" clicks that is the right trade. For a full
    download it is quadratic — measured on staging, three consecutive
    1,000-row pages examined 220K, then 531K, then 464K messages, most of it
    re-reading what the previous page had already read.

    So a download gets a generator instead: one pass per archive, nothing
    accumulated, and the caller decides when to pull. The MATCHING rule is
    the same `_message_matches` and the same prefilter — only the traversal
    differs, so the two cannot disagree about what a hit is.
    """
    from glogarch.archive.storage import ArchiveIterator

    terms = query.normalised_terms()
    filters = {k: str(v).lower() for k, v in (query.field_filters or {}).items()}
    needles = query.prefilter_needles()

    records = db.list_archives_for_search(
        server=query.server, stream_id=query.stream_id,
        time_from=query.time_from, time_to=query.time_to)
    log.info("Archive search (streaming) starting", archives=len(records))

    for rec in records:
        if cancel_check and cancel_check():
            return
        if yield_cb:
            yield_cb()
        path = Path(rec.file_path)
        if not path.exists():
            log.warning("Skipping a missing archive during export",
                        path=str(rec.file_path))
            continue
        if not archive_may_contain(path, needles):
            continue
        try:
            for batch in ArchiveIterator(path, batch_size=500):
                if cancel_check and cancel_check():
                    return
                for msg in batch:
                    if _message_matches(msg, terms, filters):
                        yield _make_hit(msg, rec, path)
        except Exception as e:
            # One unreadable archive must not abort a download that has
            # already produced thousands of good rows.
            log.warning("Archive failed during streaming search",
                        path=str(path), error=str(e))


def search_archive(record, query: SearchQuery, out: SearchResult,
                   cancel_check=None, skip_hits: int = 0,
                   progress_cb=None) -> int:
    """Scan ONE archive, appending hits to `out`. Returns hits found.

    `skip_hits` discards that many MATCHING messages before collecting — this
    is how a resumed page continues mid-archive. The archive is re-parsed
    (gzip cannot seek), but only this one: every archive already scanned on a
    previous page is skipped entirely by the caller.
    """
    from glogarch.archive.storage import ArchiveIterator

    path = Path(record.file_path)
    if not path.exists():
        out.errors.append(f"missing file: {record.file_path}")
        return 0

    terms = query.normalised_terms()
    filters = {k: str(v).lower() for k, v in (query.field_filters or {}).items()}

    if not archive_may_contain(path, query.prefilter_needles()):
        return 0
    out.archives_parsed += 1

    found = 0
    # A single archive can take ~8.5 s to parse. Publishing only when it ends
    # means the first hits appear that much later than they were actually
    # found, and the screen sits still in the meantime.
    last_report = time.time()
    try:
        for batch in ArchiveIterator(path, batch_size=500):
            if cancel_check and cancel_check():
                out.cancelled = True
                return found
            if progress_cb and (time.time() - last_report) >= PROGRESS_INTERVAL_SEC:
                last_report = time.time()
                try:
                    progress_cb(out)
                except Exception as e:
                    log.warning("Search progress callback failed", error=str(e))
            for msg in batch:
                out.messages_examined += 1
                if not _message_matches(msg, terms, filters):
                    continue
                if skip_hits > 0:
                    skip_hits -= 1
                    continue
                out.hits.append(_make_hit(msg, record, path))
                found += 1
                if len(out.hits) >= query.max_results:
                    # Page is full. The CALLER owns the cursor: it knows how
                    # many hits it told us to skip, so `skip + found` is where
                    # the next page resumes inside this same archive.
                    out.truncated = True
                    return found
    except Exception as e:
        out.errors.append(f"{path.name}: {e}")
        log.warning("Search failed inside an archive", path=str(path), error=str(e))
    return found


def run_search(db, query: SearchQuery, *, progress_cb=None, cancel_check=None,
               yield_cb=None) -> SearchResult:
    """Search every archive matching the query's time range and filters.

    `yield_cb()` is called between archives so the caller can slow the search
    down while an export or import is running — archiving is the product,
    search is the assistant, and they share one disk.
    """
    out = SearchResult()
    started = time.time()

    records = db.list_archives_for_search(
        server=query.server, stream_id=query.stream_id,
        time_from=query.time_from, time_to=query.time_to)
    out.archives_total = len(records)
    # Report the denominator BEFORE opening anything, so the UI shows
    # "0 / 145" rather than "0 / 0" for however long the first archive takes.
    if progress_cb:
        try:
            progress_cb(out)
        except Exception as e:
            log.warning("Search progress callback failed", error=str(e))
    log.info("Archive search starting", archives=out.archives_total,
             terms=len(query.normalised_terms()),
             filters=len(query.field_filters or {}))

    # Resume: everything before start_archive was scanned on an earlier page
    # and is never touched again. Only the archive we stopped inside is
    # re-parsed, and only far enough to skip the hits already returned.
    idx = max(0, int(query.start_archive or 0))
    skip = max(0, int(query.skip_in_archive or 0))
    out.archives_scanned = idx

    while idx < len(records):
        if cancel_check and cancel_check():
            # Record the cursor here too, not only on the inner cancel path:
            # a cancelled search that forgets where it stopped can only be
            # restarted from the beginning, which on a wide range means
            # redoing everything the user already waited for.
            out.cancelled = True
            out.next_start_archive = idx
            out.next_skip_in_archive = skip
            break
        if yield_cb:
            yield_cb()
        rec = records[idx]
        found = search_archive(rec, query, out, cancel_check=cancel_check,
                               skip_hits=skip, progress_cb=progress_cb)
        if out.truncated:
            # Stopped mid-archive: resume here, past the hits just returned.
            out.next_start_archive = idx
            out.next_skip_in_archive = skip + found
            break
        if out.cancelled:
            out.next_start_archive = idx
            out.next_skip_in_archive = skip
            break
        skip = 0                      # only the first archive is ever skipped
        idx += 1
        out.archives_scanned = idx
        if progress_cb:
            # A reporting failure must not abort a search that is working, but
            # it must not vanish either: a progress hook that silently throws
            # is how a running job ends up looking frozen.
            try:
                progress_cb(out)
            except Exception as e:
                log.warning("Search progress callback failed",
                            archives_scanned=out.archives_scanned, error=str(e))
    else:
        out.next_start_archive = None  # range exhausted — that really is all

    out.duration_seconds = time.time() - started
    log.info("Archive search finished", hits=len(out.hits),
             scanned=out.archives_scanned, parsed=out.archives_parsed,
             examined=out.messages_examined, truncated=out.truncated,
             cancelled=out.cancelled, seconds=round(out.duration_seconds, 1))
    return out

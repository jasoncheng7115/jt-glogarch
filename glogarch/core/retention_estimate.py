"""Estimate how much longer the archive disk can hold logs.

The estimate is grounded in the archive's OWN data — no fixed assumptions about
compression or ingest rate:

    rate (bytes/day of log) = total_compressed_bytes / (latest - earliest)
    remaining_days          = available_bytes / rate

Because the numerator is the real compressed footprint and the denominator is
the real span of LOG time it covers, `rate` already folds in this deployment's
actual compression ratio and message volume. Multiplying free disk by it gives
the months of *future* log the disk can still absorb (assuming the log rate
stays roughly constant).

`available=False` is returned when there is not yet enough history (span too
short, or no completed archives) to make a meaningful estimate.
"""
from __future__ import annotations

from datetime import datetime

_DAYS_PER_MONTH = 30.44


def _parse_dt(value):
    """Parse an archive time string (naive, various formats) into a datetime."""
    if value is None or isinstance(value, datetime):
        return value
    s = str(value).strip().rstrip("Z")
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def estimate_archive_retention(total_compressed_bytes, earliest, latest,
                               available_bytes, min_span_days: float = 1.0) -> dict:
    """Return a dict describing the projected remaining archive retention.

    Keys: available (bool), span_days, bytes_per_day, bytes_per_month,
    remaining_days, remaining_months. When `available` is False the numeric
    fields are None (not enough history yet).
    """
    result = {
        "available": False,
        "span_days": None,
        "bytes_per_day": None,
        "bytes_per_month": None,
        "remaining_days": None,
        "remaining_months": None,
    }
    ef = _parse_dt(earliest)
    lt = _parse_dt(latest)
    try:
        total_compressed_bytes = float(total_compressed_bytes or 0)
        available_bytes = float(available_bytes) if available_bytes is not None else None
    except (TypeError, ValueError):
        return result
    if not ef or not lt or available_bytes is None or total_compressed_bytes <= 0:
        return result

    span_days = (lt - ef).total_seconds() / 86400.0
    if span_days > 0:
        result["span_days"] = round(span_days, 2)
    if span_days < min_span_days:
        return result  # not enough log-time history to trust the rate yet

    bytes_per_day = total_compressed_bytes / span_days
    if bytes_per_day <= 0:
        return result
    remaining_days = available_bytes / bytes_per_day
    result.update({
        "available": True,
        "bytes_per_day": bytes_per_day,
        "bytes_per_month": bytes_per_day * _DAYS_PER_MONTH,
        "remaining_days": round(remaining_days, 1),
        "remaining_months": round(remaining_days / _DAYS_PER_MONTH, 1),
    })
    return result

"""Adaptive backpressure guard for exports (API *and* OpenSearch-direct).

A heavy export puts search/read load on the same OpenSearch cluster that Graylog
uses for indexing. On busy clusters — especially slow HDD-backed storage — that
starves ingestion: the disk journal and ring buffers back up and Graylog stops
collecting logs (in the worst case it wedges until restarted).

This guard samples Graylog's own health signals between chunks/batches and, the
moment ingestion starts falling behind, PAUSES the export until it drains — then
resumes. It watches every signal:

  * JVM heap %                         (absolute threshold)
  * disk journal uncommitted entries   (sustained rise)
  * input / process / output buffers   (sustained rise)

Design principles:
  * **Fail-safe** — if Graylog can't be read (health is None), that counts as
    pressure and we pause. An unreachable Graylog is when we must back off most.
  * **Trend based** — buffers/journal trip on a *sustained climb*, not an
    absolute number, so it works on any deployment/storage without tuning.
  * **Resume only once drained** — not merely "stopped rising", the signal must
    fall back toward its pre-spike level.
  * **Observable** — every pause is logged AND surfaced to the UI with the exact
    signal(s) that triggered it.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

from glogarch.utils.logging import get_logger

log = get_logger("export.health")

# (tracker key, health-dict key, human label)
_BUFFERS = (
    ("buffer_process", "buffer_process", "process buffer"),
    ("buffer_output", "buffer_output", "output buffer"),
    ("buffer_input", "buffer_input", "input buffer"),
)
_DRAIN_METRICS = ("journal_uncommitted", "buffer_process", "buffer_output", "buffer_input")


class RisingTracker:
    """Detects a metric that keeps climbing across consecutive samples."""

    def __init__(self, samples: int = 3, min_delta: int = 1):
        self.samples = max(1, samples)
        self.min_delta = max(1, min_delta)
        self._h: deque[float] = deque(maxlen=self.samples + 1)

    def add(self, v) -> None:
        self._h.append(v or 0)

    def rising(self) -> bool:
        if len(self._h) < self.samples + 1:
            return False
        xs = list(self._h)
        return all(xs[i + 1] - xs[i] >= self.min_delta for i in range(len(xs) - 1))

    def latest(self):
        return self._h[-1] if self._h else 0


class HealthGuard:
    """Pause/resume an export based on Graylog ingestion backpressure.

    Call ``await guard.checkpoint(progress)`` between chunks/batches. It returns
    immediately when healthy; otherwise it blocks (pausing the export) until the
    pressure clears, or raises RuntimeError if it stays high past the max wait.
    """

    def __init__(self, monitor, cfg, progress_callback=None, ctx=None):
        self.monitor = monitor
        self.cfg = cfg
        self.progress_callback = progress_callback
        self.ctx = dict(ctx or {})
        self.pause_count = 0
        self.total_paused_sec = 0
        self._heap_streak = 0
        self._last_sample = 0.0
        self._interval = max(1, getattr(cfg, "health_sample_interval_sec", 15))
        rs = getattr(cfg, "health_rise_samples", 3)
        jd = getattr(cfg, "health_journal_min_delta", 200)
        bd = getattr(cfg, "health_buffer_min_delta", 64)
        self.trackers = {
            "journal": RisingTracker(rs, jd),
            "buffer_process": RisingTracker(rs, bd),
            "buffer_output": RisingTracker(rs, bd),
            "buffer_input": RisingTracker(rs, bd),
        }

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.cfg, "health_guard_enabled", True)) and self.monitor is not None

    async def _read(self):
        try:
            return await self.monitor.get_health()
        except Exception:
            return None

    def _tripped(self, health) -> list[str]:
        """Feed the trackers and return the list of tripped-signal descriptions
        (empty = healthy). health is None → fail-safe pressure."""
        if health is None:
            return ["Graylog 無回應（保守暫停）"]
        out: list[str] = []
        # Two-tier JVM heap: back off well before the ceiling, but don't let a
        # single GC-sawtooth peak cause a needless pause.
        #   * hard tier  → pause immediately on one reading (acute spike)
        #   * soft tier  → pause only when SUSTAINED for N reads (steady climb)
        soft = getattr(self.cfg, "jvm_memory_threshold_pct", 75.0)
        hard = getattr(self.cfg, "jvm_memory_hard_pct", 90.0)
        need = max(1, getattr(self.cfg, "health_heap_sustained_samples", 2))
        hp = health.get("jvm_pct", 0)
        if hp >= hard:
            out.append(f"JVM heap {hp:.0f}%（超過硬上限 {hard:.0f}%）")
            self._heap_streak = 0
        elif hp >= soft:
            self._heap_streak += 1
            if self._heap_streak >= need:
                out.append(f"JVM heap {hp:.0f}%（持續高於軟門檻 {soft:.0f}%）")
        else:
            self._heap_streak = 0
        self.trackers["journal"].add(health.get("journal_uncommitted", 0))
        if self.trackers["journal"].rising():
            out.append(f"disk journal 積壓上升（{int(self.trackers['journal'].latest()):,}）")
        for tkey, hkey, name in _BUFFERS:
            self.trackers[tkey].add(health.get(hkey, 0))
            if self.trackers[tkey].rising():
                out.append(f"{name} 持續上升（{int(self.trackers[tkey].latest()):,}）")
        return out

    async def checkpoint(self, progress: dict | None = None) -> None:
        """Called FREQUENTLY by the export loop (per batch). It only actually
        reads Graylog every `health_sample_interval_sec` — so the sampling
        cadence is fixed wall-clock time, decoupled from how big/slow a chunk is
        (a chunk-only cadence could take many minutes between reads, making the
        trend thresholds meaningless). Between samples it returns instantly."""
        if not self.enabled:
            return
        now = time.monotonic()
        if now - self._last_sample < self._interval:
            return
        self._last_sample = now
        tripped = self._tripped(await self._read())
        if tripped:
            await self._pause_until_clear(tripped, progress)

    async def _pause_until_clear(self, tripped: list[str], progress: dict | None) -> None:
        self.pause_count += 1
        log.warning("export paused — Graylog backpressure", signals=tripped)
        self._emit(progress, "偵測到高負載，暫停中：" + "；".join(tripped) + " → 等待降載")
        interval = getattr(self.cfg, "health_pause_interval_sec", 15)
        max_wait = getattr(self.cfg, "health_max_pause_min", 30) * 60
        drain = getattr(self.cfg, "health_resume_drain_ratio", 0.7)
        peak: dict[str, float] = {}
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(interval)
            waited += interval
            self.total_paused_sec += interval
            health = await self._read()
            if health is None:
                self._emit(progress, f"Graylog 無回應，續等降載（已暫停 {waited}s）")
                continue
            for mkey in _DRAIN_METRICS:
                peak[mkey] = max(peak.get(mkey, 0), health.get(mkey, 0))
            now_tripped = self._tripped(health)
            drained = all(
                health.get(mkey, 0) <= max(1, peak.get(mkey, 0)) * drain
                for mkey in _DRAIN_METRICS
            )
            if not now_tripped and drained:
                log.info("export resumed — backpressure cleared", waited_sec=waited)
                self._emit(progress, f"負載已降，續跑（暫停 {waited}s）")
                return
            self._emit(progress, "仍在等待降載：" + "；".join(now_tripped or ["尚未回落"])
                       + f"（已暫停 {waited}s）")
        msg = (f"高負載持續超過 {max_wait // 60} 分鐘未降（{'；'.join(tripped)}），已停止匯出。"
               f"建議改用 OpenSearch 直連、調高 Graylog heap，或縮小匯出範圍。")
        log.error("export stopped — backpressure did not clear", signals=tripped, waited_sec=waited)
        try:
            from glogarch.notify.sender import notify_error
            await notify_error("Export", msg)
        except Exception:
            pass
        raise RuntimeError(msg)

    def _emit(self, progress: dict | None, detail: str) -> None:
        if not self.progress_callback:
            return
        payload = dict(self.ctx)
        if progress:
            payload.update(progress)
        payload.update({"phase": "backpressure_wait", "detail": detail})
        try:
            self.progress_callback(payload)
        except Exception:
            pass

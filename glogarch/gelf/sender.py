"""GELF TCP sender for importing archived messages back into Graylog."""

from __future__ import annotations

import asyncio
import json
import struct
from datetime import datetime
from typing import Any, Callable

from glogarch.utils.logging import get_logger

log = get_logger("gelf.sender")

# Graylog syslog level mapping
SYSLOG_LEVELS = {
    "emergency": 0, "emerg": 0,
    "alert": 1,
    "critical": 2, "crit": 2,
    "error": 3, "err": 3,
    "warning": 4, "warn": 4,
    "notice": 5,
    "informational": 6, "info": 6,
    "debug": 7,
}


def _parse_timestamp(ts: Any) -> float:
    """Convert various timestamp formats to Unix epoch float."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        # Try ISO format first
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.timestamp()
            except ValueError:
                continue
    return datetime.utcnow().timestamp()


def _parse_level(level: Any) -> int:
    """Convert level to syslog numeric level."""
    if isinstance(level, int):
        return max(0, min(7, level))
    if isinstance(level, str):
        return SYSLOG_LEVELS.get(level.lower(), 6)
    return 6  # default: informational


# Fields that map directly to GELF standard fields
GELF_STANDARD_FIELDS = {"timestamp", "source", "host", "level", "facility", "message",
                        "full_message", "short_message", "file", "line"}
# Internal Graylog fields to skip
SKIP_FIELDS = {"_id", "gl2_message_id", "gl2_remote_ip", "gl2_remote_port",
               "gl2_source_input", "gl2_source_node", "gl2_source_collector",
               "gl2_processing_timestamp", "gl2_accounted_message_size",
               "gl2_receive_timestamp", "streams"}


def message_to_gelf(msg: dict) -> dict:
    """Convert an archived Graylog message to GELF format.

    Preserves original timestamp, source, level, facility, and all custom fields.
    """
    gelf: dict[str, Any] = {
        "version": "1.1",
    }

    # Timestamp - preserve original
    if "timestamp" in msg:
        gelf["timestamp"] = _parse_timestamp(msg["timestamp"])

    # Host/source - GELF requires "host", Graylog stores as "source"
    gelf["host"] = msg.get("source") or msg.get("host") or "archived"

    # Message
    gelf["short_message"] = msg.get("message") or msg.get("short_message") or ""
    if "full_message" in msg:
        gelf["full_message"] = msg["full_message"]

    # Level
    if "level" in msg:
        gelf["level"] = _parse_level(msg["level"])

    # Facility
    if "facility" in msg:
        gelf["_facility"] = msg["facility"]

    # All other fields become GELF additional fields (prefixed with _)
    for key, value in msg.items():
        if key in GELF_STANDARD_FIELDS or key in SKIP_FIELDS:
            continue
        if key.startswith("gl2_"):
            continue
        # GELF additional fields must start with _
        gelf_key = key if key.startswith("_") else f"_{key}"
        # GELF doesn't allow _id
        if gelf_key == "_id":
            gelf_key = "_original_id"
        if value is not None:
            gelf[gelf_key] = value

    return gelf


class GelfSender:
    """Async GELF sender — supports TCP (null-byte delimited) and UDP."""

    def __init__(self, host: str = "localhost", port: int = 32202, protocol: str = "tcp"):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._udp_transport = None
        self._connected = False
        self._messages_sent = 0

    async def connect(self) -> None:
        """Establish connection."""
        try:
            if self.protocol == "tcp":
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
            else:
                # UDP — create datagram endpoint
                loop = asyncio.get_event_loop()
                self._udp_transport, _ = await loop.create_datagram_endpoint(
                    asyncio.DatagramProtocol,
                    remote_addr=(self.host, self.port),
                )
            self._connected = True
            log.info(f"GELF {self.protocol.upper()} connected", host=self.host, port=self.port)
        except Exception as e:
            log.error(f"GELF {self.protocol.upper()} connection failed", host=self.host, port=self.port, error=str(e))
            raise

    async def close(self) -> None:
        """Close connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        if self._udp_transport:
            try:
                self._udp_transport.close()
            except Exception:
                pass
        self._connected = False
        log.info(f"GELF {self.protocol.upper()} disconnected", messages_sent=self._messages_sent)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def send_message(self, gelf_msg: dict) -> None:
        """Send a single GELF message."""
        if not self._connected:
            raise RuntimeError("Not connected to GELF endpoint")

        data = json.dumps(gelf_msg, ensure_ascii=False, default=str).encode("utf-8")

        if self.protocol == "tcp":
            if not self._writer:
                raise RuntimeError("TCP writer not available")
            self._writer.write(data + b"\x00")
            await self._writer.drain()
        else:
            if not self._udp_transport:
                raise RuntimeError("UDP transport not available")
            # GELF UDP: if message < 8192 bytes, send as-is (no chunking needed for most logs)
            if len(data) > 8192:
                import zlib
                data = zlib.compress(data)
            self._udp_transport.sendto(data)

        self._messages_sent += 1

    async def send_batch(
        self,
        messages: list[dict],
        batch_size: int = 500,
        delay_ms: int = 100,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        """Send messages in batches with delay between batches.

        Args:
            messages: List of archived messages (not yet GELF-converted).
            batch_size: Messages per batch.
            delay_ms: Milliseconds to wait between batches.
            progress_callback: Called with (sent_count, total_count).

        Returns:
            Number of messages successfully sent.
        """
        total = len(messages)
        sent = 0

        for i in range(0, total, batch_size):
            batch = messages[i:i + batch_size]
            for msg in batch:
                gelf_msg = message_to_gelf(msg)
                try:
                    await self.send_message(gelf_msg)
                    sent += 1
                except Exception as e:
                    log.error("Failed to send GELF message", error=str(e), sent=sent)
                    # Try to reconnect once
                    try:
                        await self.close()
                        await self.connect()
                        await self.send_message(gelf_msg)
                        sent += 1
                    except Exception as e2:
                        log.error("Reconnect failed", error=str(e2))
                        return sent

            if progress_callback:
                progress_callback(sent, total)

            if delay_ms > 0 and i + batch_size < total:
                await asyncio.sleep(delay_ms / 1000.0)

        return sent

    @property
    def messages_sent(self) -> int:
        return self._messages_sent

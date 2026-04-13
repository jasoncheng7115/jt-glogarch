"""Async Graylog REST API client for Graylog 6.x/7.x."""

from __future__ import annotations

from typing import Any

import httpx

from glogarch.core.config import GraylogServerConfig
from glogarch.ratelimit.limiter import RateLimiter
from glogarch.utils.logging import get_logger
from glogarch.utils.retry import retry_async

log = get_logger("graylog.client")


class GraylogClient:
    """Async HTTP client for Graylog 6.x/7.x REST API."""

    def __init__(self, config: GraylogServerConfig, rate_limiter: RateLimiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self._version: str | None = None

        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-By": "glogarch",
        }
        # Graylog API tokens use Basic Auth with token as username, "token" as password
        auth = None
        if config.auth_token:
            auth = httpx.BasicAuth(config.auth_token, "token")
        elif config.username and config.password:
            auth = httpx.BasicAuth(config.username, config.password)

        self._client = httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            headers=headers,
            auth=auth,
            verify=config.verify_ssl,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    @retry_async(max_retries=3, base_delay=2.0, exceptions=(httpx.HTTPError,))
    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        await self.rate_limiter.acquire()
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp

    async def get(self, path: str, **kwargs) -> dict:
        resp = await self._request("GET", path, **kwargs)
        return resp.json()

    async def post(self, path: str, **kwargs) -> dict:
        resp = await self._request("POST", path, **kwargs)
        return resp.json()

    async def get_version(self) -> str:
        """Get Graylog server version."""
        if self._version is None:
            data = await self.get("/api/system")
            self._version = data.get("version", "unknown")
            log.info("Graylog version detected", version=self._version)
        return self._version

    async def get_streams(self) -> list[dict]:
        """Get all streams."""
        data = await self.get("/api/streams")
        return data.get("streams", [])

    async def get_inputs(self) -> list[dict]:
        """Get all inputs."""
        data = await self.get("/api/system/inputs")
        return data.get("inputs", [])

    async def get_index_sets(self) -> list[dict]:
        """Get all index sets."""
        data = await self.get("/api/system/indices/index_sets", params={"stats": "false"})
        return data.get("index_sets", [])

    async def get_streams_for_index_set(self, index_set_id: str) -> list[dict]:
        """Get streams associated with a specific index set."""
        all_streams = await self.get_streams()
        return [s for s in all_streams if s.get("index_set_id") == index_set_id]

    async def check_connectivity(self) -> dict:
        """Check if Graylog server is reachable and return basic info."""
        try:
            data = await self.get("/api/system")
            return {
                "connected": True,
                "version": data.get("version"),
                "cluster_id": data.get("cluster_id"),
                "node_id": data.get("node_id"),
                "hostname": data.get("hostname"),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

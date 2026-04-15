"""Monitor Graylog Journal status to prevent buffer/journal overflow during import."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from glogarch.utils.logging import get_logger

log = get_logger("import.journal")


@dataclass
class JournalStatus:
    """Graylog journal status snapshot."""
    uncommitted: int = 0
    size_bytes: int = 0
    disk_free_bytes: int = 0
    available: bool = True
    error: str = ""


class JournalMonitor:
    """Monitor Graylog journal via API or SSH.

    Three modes:
    - none: No monitoring, rely on fixed rate + manual pause
    - api: Query Graylog REST API /api/system/journal
    - ssh: Run remote command via SSH to check journal dir size
    """

    # Thresholds for dynamic rate control
    THRESHOLD_SLOW = 100_000      # uncommitted > 100K -> double delay
    THRESHOLD_PAUSE = 500_000     # uncommitted > 500K -> pause 30s
    THRESHOLD_STOP = 1_000_000    # uncommitted > 1M -> stop import

    def __init__(
        self,
        mode: str = "none",       # "none", "api", "ssh"
        # API mode
        api_url: str = "",
        api_token: str = "",
        api_username: str = "",
        api_password: str = "",
        # SSH mode
        ssh_host: str = "",
        ssh_port: int = 22,
        ssh_user: str = "",
        ssh_password: str = "",
        ssh_key_path: str = "",
        journal_path: str = "/var/lib/graylog-server/journal",
    ):
        self.mode = mode
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.api_username = api_username
        self.api_password = api_password
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_key_path = ssh_key_path
        self.journal_path = journal_path
        self._ssh_client = None

    async def check(self) -> JournalStatus:
        """Get current journal status."""
        if self.mode == "api":
            return await self._check_api()
        elif self.mode == "ssh":
            return await self._check_ssh()
        return JournalStatus(available=False)

    async def _check_api(self) -> JournalStatus:
        """Query Graylog REST API for journal status."""
        import httpx

        try:
            auth = None
            if self.api_token:
                auth = (self.api_token, "token")
            elif self.api_username:
                auth = (self.api_username, self.api_password)

            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(
                    f"{self.api_url}/api/system/journal",
                    auth=auth,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

            return JournalStatus(
                uncommitted=data.get("uncommitted_journal_entries", 0),
                size_bytes=data.get("journal_size", 0),
                available=True,
            )
        except Exception as e:
            log.warning("Journal API check failed", error=str(e))
            return JournalStatus(available=False, error=str(e))

    async def _check_ssh(self) -> JournalStatus:
        """Check journal via SSH remote command."""
        try:
            import asyncssh
        except ImportError:
            # Fallback: use subprocess with ssh command
            return await self._check_ssh_subprocess()

        try:
            conn_kwargs = {
                "host": self.ssh_host,
                "port": self.ssh_port,
                "username": self.ssh_user,
                "known_hosts": None,  # Accept any host key
            }
            if self.ssh_password:
                conn_kwargs["password"] = self.ssh_password
            if self.ssh_key_path:
                conn_kwargs["client_keys"] = [self.ssh_key_path]

            async with asyncssh.connect(**conn_kwargs) as conn:
                import shlex
                safe_path = shlex.quote(self.journal_path)
                # Get journal directory size
                result = await conn.run(
                    f"du -sb {safe_path} 2>/dev/null | cut -f1",
                    check=False,
                )
                size_bytes = int(result.stdout.strip() or "0")

                # Get disk free space
                result2 = await conn.run(
                    f"df -B1 {safe_path} 2>/dev/null | tail -1 | awk '{{print $4}}'",
                    check=False,
                )
                disk_free = int(result2.stdout.strip() or "0")

                # Estimate uncommitted from size (avg ~500 bytes per entry)
                uncommitted = size_bytes // 500

            return JournalStatus(
                uncommitted=uncommitted,
                size_bytes=size_bytes,
                disk_free_bytes=disk_free,
                available=True,
            )
        except Exception as e:
            log.warning("Journal SSH check failed (asyncssh)", error=str(e))
            return await self._check_ssh_subprocess()

    async def _check_ssh_subprocess(self) -> JournalStatus:
        """Fallback SSH check using subprocess."""
        try:
            cmd_parts = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
            if self.ssh_key_path:
                cmd_parts.extend(["-i", self.ssh_key_path])
            import shlex
            safe_path = shlex.quote(self.journal_path)
            cmd_parts.extend([
                "-p", str(self.ssh_port),
                f"{self.ssh_user}@{self.ssh_host}",
                f"du -sb {safe_path} 2>/dev/null | cut -f1; df -B1 {safe_path} 2>/dev/null | tail -1 | awk '{{print $4}}'",
            ])

            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            # For password auth, we need sshpass
            if self.ssh_password and not self.ssh_key_path:
                cmd_parts = [
                    "sshpass", f"-p{self.ssh_password}",
                ] + cmd_parts
                proc = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            lines = stdout.decode().strip().split("\n")

            size_bytes = int(lines[0]) if lines and lines[0].isdigit() else 0
            disk_free = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0
            uncommitted = size_bytes // 500

            return JournalStatus(
                uncommitted=uncommitted,
                size_bytes=size_bytes,
                disk_free_bytes=disk_free,
                available=True,
            )
        except Exception as e:
            log.warning("Journal SSH check failed (subprocess)", error=str(e))
            return JournalStatus(available=False, error=str(e))

    def recommend_action(self, status: JournalStatus) -> str:
        """Return recommended action based on journal status.

        Returns: "normal", "slow", "pause", "stop"
        """
        if not status.available:
            return "normal"  # Can't check, proceed at user-set rate

        if status.uncommitted >= self.THRESHOLD_STOP:
            return "stop"
        elif status.uncommitted >= self.THRESHOLD_PAUSE:
            return "pause"
        elif status.uncommitted >= self.THRESHOLD_SLOW:
            return "slow"
        return "normal"

#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Is the vendored mcp_graylog current and unmodified?

Owner's rule (2026-11-19): "每次改程式時都要查一下它有沒有新版" / "如果 github 有新版
就收進我們專案". run-tests.sh runs this on every release check.

    python3 scripts/check-mcp-graylog.py            # check
    python3 scripts/check-mcp-graylog.py --update   # take the newer upstream file in whole

Exit 0: current (or GitHub unreachable: prints WARN, never blocks a release
for a network problem). Exit 1: upstream has another version, or the vendored
file no longer matches its manifest (someone edited it - it must stay as
published; missing features go to the owner, who forwards them).
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "glogarch" / "vendor"
FILE = VENDOR / "mcp_graylog.py"
MANIFEST = VENDOR / "mcp_graylog.json"
COMMITS = ("https://api.github.com/repos/jasoncheng7115/jasontools-mcp/commits"
           "?path=mcp_graylog/mcp_graylog.py&per_page=1")


def version_of(text: str) -> str | None:
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    return m.group(1) if m else None


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "jt-glogarch-release-check"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - fixed https URLs above
        return r.read()


def main(argv: list[str]) -> int:
    update = "--update" in argv
    man = json.loads(MANIFEST.read_text())
    local = FILE.read_bytes()
    local_sha = hashlib.sha256(local).hexdigest()
    if local_sha != man["sha256"] and not update:
        print(f"mcp_graylog: FAIL - glogarch/vendor/mcp_graylog.py does not match its manifest "
              f"(sha256 {local_sha[:12]} != {man['sha256'][:12]}). It must stay as published; "
              f"report missing features to the owner instead of editing it.")
        return 1
    try:
        up = fetch(man["raw_url"])
    except Exception as e:  # network: warn, do not block
        print(f"mcp_graylog: WARN - could not reach GitHub to compare versions ({e}); "
              f"vendored {man['version']} is unmodified.")
        return 0
    up_ver = version_of(up.decode("utf-8", "replace"))
    up_sha = hashlib.sha256(up).hexdigest()
    if up_sha == man["sha256"]:
        print(f"mcp_graylog: OK - vendored {man['version']} is the published version.")
        return 0
    if not update:
        print(f"mcp_graylog: FAIL - GitHub has {up_ver or 'a different file'} "
              f"(vendored {man['version']}). Take it with: python3 scripts/check-mcp-graylog.py --update, "
              f"then run tests/test_ai_tools.py and scripts/e2e-ai-test.py.")
        return 1
    try:
        commit = json.loads(fetch(COMMITS))[0]["sha"]
    except Exception as e:
        print(f"mcp_graylog: WARN - could not read the upstream commit id ({e})")
        commit = ""
    FILE.write_bytes(up)
    man.update(version=up_ver or man["version"], sha256=up_sha, commit=commit or man.get("commit", ""))
    MANIFEST.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    print(f"mcp_graylog: updated to {man['version']} ({up_sha[:12]}). Run the AI tool tests and the "
          f"e2e check before releasing, and add a CHANGELOG line.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""End-to-end test of Graylog Data Node access (beta) against a REAL Data Node.

Every import/export path needs an e2e step or it is effectively untested, and
the archive e2e (e2e-archive-test.sh) runs against a plain OpenSearch. This one
needs a Graylog whose OpenSearch is a Data Node, e.g. the throwaway stack from
`bash scripts/datanode-stack/up.sh`, which prints the env below.

    GL_URL=http://127.0.0.1:19000 GL_USER=admin GL_PASS=... \\
    DN_OS_URL=https://127.0.0.1:19200 GELF_PORT=32212 \\
    python3 scripts/e2e-datanode-test.py

Steps (each asserts):
  [1] connect: Graylog issues a client certificate, OpenSearch answers with it
  [2] seed N GELF messages with a run marker, rotate so the index is sealed
  [3] OpenSearch Direct export through the certificate archives all N
  [4] Bulk import of those archives into a throwaway pattern lands all N
  [5] renewal: a forced renewal swaps the certificate and still connects
  [6] recovery: the role mapping removed behind our back is re-issued
  [7] scheduled run with an unusable certificate archives via the Graylog API
  [8] disconnect removes the files and the mapping; cleanup of the test set
Run it from the repository root (it imports the source tree). Writes only to
a temporary directory and to throwaway objects on the target Graylog.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

GL_URL = os.environ.get("GL_URL", "http://127.0.0.1:19000").rstrip("/")
GL_USER = os.environ.get("GL_USER", "admin")
GL_PASS = os.environ.get("GL_PASS", "")
DN_OS_URL = os.environ.get("DN_OS_URL", "")          # override if the hostname does not resolve
GELF_HOST = os.environ.get("GELF_HOST", "127.0.0.1")
GELF_PORT = int(os.environ.get("GELF_PORT", "32212"))
GELF_INPUT_PORT = int(os.environ.get("GELF_INPUT_PORT", "32202"))   # inside Graylog
N = int(os.environ.get("N", "3000"))
PATTERN = "jt_e2e_dn"
FAIL: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def gl(method, path, **kw):
    with httpx.Client(auth=(GL_USER, GL_PASS), timeout=60,
                      headers={"X-Requested-By": "jt-e2e", "Accept": "application/json"}) as c:
        return c.request(method, f"{GL_URL}{path}", **kw)


def ensure_gelf_input():
    for i in gl("GET", "/api/system/inputs").json().get("inputs", []):
        if i.get("type", "").endswith("GELFTCPInput") and \
                int((i.get("attributes") or {}).get("port", 0)) == GELF_INPUT_PORT:
            return
    gl("POST", "/api/system/inputs", json={
        "title": "jt-e2e gelf tcp", "type": "org.graylog2.inputs.gelf.tcp.GELFTCPInput",
        "global": True, "configuration": {"bind_address": "0.0.0.0", "port": GELF_INPUT_PORT,
                                          "recv_buffer_size": 1048576,
                                          "decompress_size_limit": 8388608}})
    time.sleep(8)


def seed(marker):
    s = socket.create_connection((GELF_HOST, GELF_PORT), timeout=30)
    now = time.time()
    for i in range(N):
        m = {"version": "1.1", "host": f"e2e{i % 5}", "short_message": f"dn e2e {i}",
             "timestamp": now - 7200 + i * (3600 / N), "_jt_e2e_run": marker, "_seq": i}
        s.sendall(json.dumps(m).encode() + b"\0")
    s.close()


async def main() -> int:
    if not GL_PASS:
        print("Set GL_PASS (and GL_URL / DN_OS_URL / GELF_PORT); see scripts/datanode-stack/up.sh")
        return 2
    from glogarch.core.config import load_settings
    from glogarch.graylog import datanode as dn
    from glogarch.opensearch.tls import httpx_options

    tmp = Path(tempfile.mkdtemp(prefix="jt-e2e-dn-"))
    cfgp = tmp / "config.yaml"
    yaml.safe_dump({
        "servers": [{"name": "e2e-dn", "url": GL_URL, "username": GL_USER, "password": GL_PASS,
                     "verify_ssl": False}],
        "default_server": "e2e-dn", "export_mode": "opensearch",
        "export": {"base_path": str(tmp / "archives")}, "database_path": str(tmp / "jt.db"),
        "op_audit": {"enabled": False}}, open(cfgp, "w"))
    (tmp / "archives").mkdir()
    st = load_settings(str(cfgp))
    marker = uuid.uuid4().hex[:12]
    print(f"Data Node e2e — {GL_URL}  marker={marker}  tmp={tmp}")

    # [1] connect
    print("[1] connect")
    res = await dn.connect(st, "e2e-dn", hosts=[DN_OS_URL] if DN_OS_URL else None)
    check("certificate issued and OpenSearch answers", res["test"].get("connected"),
          f"{res['test'].get('version')} via {res['hosts']}")
    cfg = st.get_server("e2e-dn").opensearch
    key_mode = oct(os.stat(cfg.client_key_file).st_mode & 0o777)
    check("private key is 0600", key_mode == "0o600", key_mode)
    saved = yaml.safe_load(open(cfgp))["servers"][0]["opensearch"]
    check("config.yaml carries the certificate block", saved.get("datanode") is True
          and saved.get("client_key_file") == cfg.client_key_file)
    os_url = cfg.hosts[0]

    async def os_count(index, query=None):
        async with httpx.AsyncClient(**httpx_options(st.get_server("e2e-dn").opensearch),
                                     timeout=60) as c:
            r = await c.post(f"{os_url}/{index}/_count",
                             json={"query": query or {"match_all": {}}})
            return r.json().get("count", -1) if r.status_code == 200 else -1

    # [2] seed + rotate
    print("[2] seed")
    ensure_gelf_input()
    seed(marker)
    q = {"term": {"jt_e2e_run": marker}}
    got = 0
    for _ in range(60):
        got = await os_count("graylog_*", q)
        if got >= N:
            break
        await asyncio.sleep(2)
    check(f"{N} seeded messages indexed", got == N, str(got))
    sets = gl("GET", "/api/system/indices/index_sets").json()["index_sets"]
    default_set = next(s for s in sets if s.get("default"))
    gl("POST", f"/api/cluster/deflector/{default_set['id']}/cycle")
    await asyncio.sleep(6)

    # [3] OS-direct export through the certificate
    print("[3] OpenSearch Direct export")
    from glogarch.core.database import ArchiveDB
    from glogarch.opensearch.exporter import OpenSearchExporter
    from glogarch.archive.storage import ArchiveIterator
    db = ArchiveDB(st.database_path)
    exp = OpenSearchExporter(st.get_server("e2e-dn"), st.get_server("e2e-dn").opensearch,
                             st.export, st.rate_limit, db, integrity=st.integrity)
    from datetime import datetime, timedelta
    r = await exp.export(time_from=datetime.utcnow() - timedelta(days=2), time_to=datetime.utcnow(),
                         index_set_ids=[default_set["id"]], source="manual:opensearch:e2e")
    archived = 0
    for a in db.list_archives():
        for batch in ArchiveIterator(Path(a.file_path), batch_size=5000):
            archived += sum(1 for m in batch if m.get("jt_e2e_run") == marker)
    check("every seeded message archived", archived == N, f"{archived}/{N}, errors={r.errors[:2]}")

    # [4] Bulk import through the certificate
    print("[4] Bulk import")
    p = subprocess.run([sys.executable, "-m", "glogarch", "--config", str(cfgp), "import",
                        "--mode", "bulk", "--target-api-url", GL_URL,
                        "--target-api-username", GL_USER, "--target-api-password", GL_PASS,
                        "--target-index-pattern", PATTERN],
                       cwd=str(REPO), capture_output=True, text=True, timeout=900)
    out = p.stdout + p.stderr
    check("bulk import used the Data Node certificate",
          "Data Node OpenSearch (client certificate" in out, out[-300:] if p.returncode else "")
    landed = -1
    for _ in range(30):
        landed = await os_count(f"{PATTERN}_*", q)
        if landed >= N:
            break
        await asyncio.sleep(2)
    check("every archived message landed in the target pattern", landed == N, str(landed))

    # [5] forced renewal
    print("[5] renewal")
    before = open(st.get_server("e2e-dn").opensearch.client_cert_file).read()
    cfg2, renewed, err = await dn.ensure_fresh(st, "e2e-dn", force=True)
    check("forced renewal replaced the certificate", renewed and
          open(cfg2.client_cert_file).read() != before, err or "")
    check("renewed certificate connects", (await dn.probe(cfg2)).get("connected"))

    # [6] mapping removed behind our back
    print("[6] recovery")
    gl("DELETE", f"/api/ca/clientcert/all_access/{cfg2.datanode_principal}")
    t = await dn.probe(cfg2)
    check("removing the role mapping locks the certificate out", not t.get("connected"),
          (t.get("error") or "")[:60])
    cfg3, problem = await dn.ensure_working(st, "e2e-dn")
    check("ensure_working re-issued and recovered", problem is None
          and (await dn.probe(cfg3)).get("connected"), problem or "")

    # [6b] Data Node unreachable (restarting): wait and try again, no new certificate
    print("[6b] unreachable Data Node")
    dn_container = os.environ.get("DN_CONTAINER", "dn-datanode")
    subprocess.run(["docker", "stop", dn_container], capture_output=True, timeout=120)
    cert_before = open(cfg3.client_cert_file).read()
    stats = {}
    _c, problem = await dn.ensure_working(st, "e2e-dn", retry_delays=(1, 1, 1), stats=stats)
    check("a stopped Data Node is tried 4 times, then reported", problem is not None
          and stats == {"attempts": 4, "waited_sec": 3}, f"{stats} {(problem or '')[:80]}")
    check("no new certificate is minted for an unreachable node",
          open(cfg3.client_cert_file).read() == cert_before)
    started = []

    async def _sleep_and_start(sec):
        if not started:
            subprocess.run(["docker", "start", dn_container], capture_output=True, timeout=120)
            started.append(1)
        await asyncio.sleep(sec)
    stats = {}
    cfg4, problem = await dn.ensure_working(st, "e2e-dn", retry_delays=(15,) * 16, stats=stats,
                                            sleep=_sleep_and_start)
    check("the Data Node coming back during the wait is used directly",
          problem is None and stats["attempts"] > 1 and (await dn.probe(cfg4)).get("connected"),
          f"{stats} {(problem or '')[:80]}")
    if not started:
        subprocess.run(["docker", "start", dn_container], capture_output=True, timeout=120)

    # [7] scheduled run with an unusable certificate falls back to the API
    print("[7] scheduler fallback")
    from glogarch.core.models import ScheduleRecord
    import glogarch.scheduler.scheduler as smod
    db.save_schedule(ScheduleRecord(name="e2e-os", job_type="export", cron_expr="0 3 * * *",
                                    config_json=json.dumps({"mode": "opensearch", "server": "e2e-dn",
                                                            "days": 1})))
    sch = smod.ArchiveScheduler.__new__(smod.ArchiveScheduler)
    sch.settings, sch.db = st, db
    good = dn.ensure_working

    async def _bad(settings, name, **k):
        return settings.get_server(name).opensearch, "e2e: simulated 403 Forbidden"
    dn.ensure_working = _bad
    # Record which exporter the scheduler builds; both stay the real classes.
    # (The API run may find nothing new: step [3] already archived it all.)
    import glogarch.opensearch.exporter as osmod
    built = []
    RealAPI, RealOS = smod.Exporter, osmod.OpenSearchExporter

    class _API(RealAPI):
        def __init__(self, *a, **k):
            built.append("api")
            super().__init__(*a, **k)

    class _OS(RealOS):
        def __init__(self, *a, **k):
            built.append("os")
            super().__init__(*a, **k)
    smod.Exporter, osmod.OpenSearchExporter = _API, _OS
    try:
        await sch._run_export_once("e2e-os")
    finally:
        dn.ensure_working = good
        smod.Exporter, osmod.OpenSearchExporter = RealAPI, RealOS
    check("the scheduled run archived through the Graylog API", built == ["api"], str(built))

    # [8] disconnect + cleanup
    print("[8] disconnect")
    principal = cfg3.datanode_principal
    keyfile = cfg3.client_key_file
    d = await dn.disconnect(st, "e2e-dn")
    check("disconnect removed files and config", not os.path.exists(keyfile)
          and yaml.safe_load(open(cfgp))["servers"][0].get("opensearch") is None,
          str(d["revoke_errors"]))
    r = gl("GET", "/api/system/indices/index_sets").json()["index_sets"]
    for s in r:
        if s.get("index_prefix") == PATTERN:
            for stream in gl("GET", "/api/streams").json().get("streams", []):
                if stream.get("index_set_id") == s["id"]:
                    gl("DELETE", f"/api/streams/{stream['id']}")
            gl("DELETE", f"/api/system/indices/index_sets/{s['id']}?delete_indices=true")
    print(f"  (principal {principal} removed from its role mapping)")

    print("RESULT: ALL PASS" if not FAIL else f"RESULT: {len(FAIL)} FAILED: {FAIL}")
    if not FAIL:
        # Holds a config with the Graylog password; kept only when a step failed.
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"  (kept {tmp} for inspection; it holds the Graylog password - delete it after)")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

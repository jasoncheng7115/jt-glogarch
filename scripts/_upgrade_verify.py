"""Assert the three upgrade principles against state written by an old release."""
import json, os, asyncio
from unittest.mock import patch, MagicMock

import glogarch
from glogarch.core.config import load_settings
from glogarch.core.database import ArchiveDB
from glogarch.scheduler.scheduler import ArchiveScheduler

W = os.environ["W"]
before = json.load(open(f"{W}/before.json"))
ok = True


def chk(cond, label, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"    [{'PASS' if cond else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")


print(f"    {before['version']} state -> running {glogarch.__version__}")

# --- principle 2: the system must still work with the OLD config ---
st = load_settings(f"{W}/old_config.yaml")
chk(st is not None, "old config.yaml loads")
chk(st.retention.retention_days == 1095, "retention_days preserved",
    str(st.retention.retention_days))
chk(getattr(st, "op_audit", None) is not None and st.op_audit.enabled,
    "legacy `api_audit:` migrated to op_audit")
chk(isinstance(getattr(st.retention, "disk_alert_months", None), float),
    "fields added since then get defaults")

# --- principle 1: no data may be lost ---
db = ArchiveDB(f"{W}/jt.db"); db.connect()          # triggers _migrate()
s0 = db.get_archive_stats()
chk(s0["total"] == before["archives"], "archive rows intact",
    f'{s0["total"]}=={before["archives"]}')
chk(s0["total_messages"] == before["messages"], "message counts intact",
    f'{s0["total_messages"]}=={before["messages"]}')
chk(not [a for a in db.list_archives() if not os.path.exists(a.file_path)],
    "archive FILES all present")
cols = {r[1] for r in db.conn.execute("PRAGMA table_info(archives)")}
chk({"hmac_sha256", "field_schema"} <= cols, "migration added the new columns")

# --- principle 3: scheduled archiving must survive ---
kept = {x.name for x in db.list_schedules()}
sched = ArchiveScheduler(settings=st, db=db)
asyncio.new_event_loop().run_until_complete(asyncio.sleep(0))
sched.setup()
jobs = {j.id for j in sched.scheduler.get_jobs()}
enabled = {x.name for x in db.list_schedules() if x.enabled}
chk(kept <= {x.name for x in db.list_schedules()}, "no pre-existing schedule dropped",
    f"{sorted(kept)}")
chk(enabled <= jobs, "every enabled schedule REGISTERED with APScheduler",
    f"{len(enabled & jobs)}/{len(enabled)}")

# the retention trap: stored 200 while 1095 was in force
eff = {x.name: json.loads(x.config_json or "{}") for x in db.list_schedules()}
chk(eff["auto-cleanup"].get("retention_days") == 1095,
    "cleanup retention NOT shortened by the upgrade",
    f'stored 200 -> {eff["auto-cleanup"].get("retention_days")}')
with patch("glogarch.scheduler.scheduler.Cleaner") as C:
    C.return_value.cleanup.return_value = MagicMock(files_deleted=0, bytes_freed=0)
    sched._create_run_job = MagicMock(return_value="j")
    sched._finish_run_job = MagicMock()
    sched._update_schedule_last_run = MagicMock()
    sched._run_cleanup("auto-cleanup")
    used = C.return_value.cleanup.call_args.kwargs.get("retention_days")
chk(used == 1095, "the cleanup RUN would use the safe value", f"retention_days={used}")
chk(ArchiveDB(f"{W}/jt.db").connect() or db.get_archive_stats()["total"] == before["archives"],
    "no archive deleted anywhere in the upgrade path")

raise SystemExit(0 if ok else 1)

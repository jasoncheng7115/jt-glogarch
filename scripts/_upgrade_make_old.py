"""Create archive + schedule state using an OLD release's own code.

Run with W=<workdir> pointing at a dir containing `old/glogarch` extracted from
git history. Prints a JSON summary of what was written.
"""
import json, os, sys, gzip
from datetime import datetime, timedelta

W = os.environ["W"]
sys.path.insert(0, f"{W}/old")                  # the OLD package must win
import glogarch
from glogarch.core.database import ArchiveDB
from glogarch.core.models import ArchiveRecord, ArchiveStatus, ScheduleRecord

db = ArchiveDB(f"{W}/jt.db"); db.connect()
base, total = datetime(2026, 5, 1), 0
for i in range(12):
    p = f"{W}/arch/old_{i}.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump({"metadata": {"server": "log-old", "time_from": "", "time_to": "",
                                "message_count": 100 + i},
                   "messages": [{"message": f"m{j}"} for j in range(100 + i)]}, f)
    db.record_archive(ArchiveRecord(
        server_name="log-old", stream_id=f"graylog_{i}", stream_name="graylog",
        time_from=base + timedelta(hours=i), time_to=base + timedelta(hours=i + 1),
        file_path=p, file_size_bytes=os.path.getsize(p), original_size_bytes=5000,
        message_count=100 + i, checksum_sha256="a" * 64,
        status=ArchiveStatus.COMPLETED))
    total += 100 + i

# A cleanup schedule whose stored retention is SHORTER than config.yaml's — the
# exact trap that would delete 200-1095-day-old archives on the first run after
# an upgrade if the new code simply started honouring it.
db.save_schedule(ScheduleRecord(name="auto-export", job_type="export",
    cron_expr="0 3 * * *", enabled=True,
    config_json=json.dumps({"mode": "opensearch", "days": 1, "index_set": ""})))
db.save_schedule(ScheduleRecord(name="auto-cleanup", job_type="cleanup",
    cron_expr="0 4 * * *", enabled=True,
    config_json=json.dumps({"retention_days": 200})))
db.save_schedule(ScheduleRecord(name="auto-verify", job_type="verify",
    cron_expr="0 3 1-7 * 6", enabled=True, config_json=None))
db.close()

with open(f"{W}/old_config.yaml", "w") as f:
    f.write(f"""servers:
  - {{name: log-old, url: http://10.0.0.9:9000, username: admin, password: secret, verify_ssl: false}}
default_server: log-old
export_mode: opensearch
export: {{base_path: {W}/arch}}
opensearch: {{hosts: ["http://10.0.0.9:9200"]}}
retention: {{enabled: true, retention_days: 1095}}
api_audit: {{enabled: true, listen_port: 8991}}
database_path: {W}/jt.db
""")
print(json.dumps({"version": glogarch.__version__, "archives": 12,
                  "messages": total, "schedules": 3}))

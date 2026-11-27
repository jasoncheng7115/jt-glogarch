#!/usr/bin/env python3
"""Real AI summary PDF from a real conversation, for the release check (owner 2026-11-27:
"以後你也要做這個測試").

Run ON the jt-glogarch host, as the service user, while the service keeps running:

    sudo -u jt-glogarch env HOME=/opt/jt-glogarch PLAYWRIGHT_BROWSERS_PATH=/opt/jt-glogarch/.playwright \\
        TMPDIR=/opt/jt-glogarch/.playwright/tmp python3 ai-summary-live-check.py --conversation 19 --user admin

- The live database is only READ: it is copied (sqlite online backup) to --work, and the job and the
  report-history row go into the copy, so the running service's write lock is never touched.
- Graylog is queried read-only with the configured server connection (the browser's Graylog
  session is not available here); the summary text uses the configured LLM server.
- Prints "DONE <hist_id> <charts> <text_error> <file name>"; the PDF is in the reports folder.
  Then render every page (fitz) and read them: cover rows, findings, every picture (dashboard
  blocks whole and light, none cut at a page end), timelines (events / columns / bars), charts,
  recommendations and the query list.
"""
import argparse
import asyncio
import os
import sqlite3
import sys
import traceback
import uuid
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/opt/jt-glogarch/config.yaml")
    ap.add_argument("--conversation", type=int, required=True)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--title", default="")
    ap.add_argument("--lang", default="zh-TW")
    ap.add_argument("--work", default="/tmp/jtsum")
    a = ap.parse_args()

    from glogarch.ai.graylog_tools import Ctx
    from glogarch.core.config import load_settings
    from glogarch.core.database import ArchiveDB
    from glogarch.core.models import JobRecord, JobStatus, JobType
    from glogarch.web.routes import ai as R

    settings = load_settings(a.config)
    os.makedirs(a.work, exist_ok=True)
    copy = os.path.join(a.work, "jtsum.db")
    src = sqlite3.connect("file:" + settings.database_path + "?mode=ro", uri=True)
    dst = sqlite3.connect(copy)
    src.backup(dst)
    dst.close()
    src.close()
    db = ArchiveDB(copy)
    conv = db.ai_get_conversation(a.conversation, a.user)
    if not conv:
        sys.exit(f"conversation {a.conversation} of {a.user} not found")
    srv = next(s for s in settings.servers if s.name == (conv.get("server") or settings.servers[0].name))
    auth = (srv.auth_token, "token") if getattr(srv, "auth_token", "") else (srv.username, srv.password)
    ctx = Ctx(settings=settings, db=db, server=srv, auth=auth, username=a.user, channel="chat")
    cfg = settings.ai.llm(None)
    job_id = str(uuid.uuid4())
    db.create_job(JobRecord(id=job_id, job_type=JobType.REPORT, status=JobStatus.RUNNING,
                            source="manual:ai-summary", started_at=datetime.utcnow()))
    R._SUMMARY_JOBS[job_id] = {"user": a.user, "cid": a.conversation, "hist_id": None, "error": "", "done": False}
    try:
        res = asyncio.run(R._make_summary_pdf(settings, db, ctx, conv, job_id, lang=a.lang, cfg=cfg, user=a.user,
                                              title=a.title or conv.get("title") or "", ids=None, titles={},
                                              style_cfg=dict(settings.ai.summary_style or {}), cancelled=lambda: False))
        h = db.conn.execute("select filename from report_history where id=?", (res["hist_id"],)).fetchone()
        print("DONE", res["hist_id"], res["charts"], res["text_error"] or "-", h[0] if h else "")
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Content packs page: what each connected Graylog holds, plus the Jason Tools library.

Graylog calls run as the logged-in user (web/gl_identity.py), as on the Alerting page. The
facts behind each step are in graylog/packs.py. The server re-reads Graylog before every
write: the page's copy may be old, and another admin may be on the same pack.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from glogarch.graylog import pack_compat, pack_guide
from glogarch.graylog import packs as P
from glogarch.utils.logging import get_logger
from glogarch.utils.sanitize import sanitize
from glogarch.web.routes.alerting import _audit, _call, _need_signin, _server, _ident

log = get_logger("web.packs")
router = APIRouter()

_INSTALL_ID = re.compile(r"^[0-9a-f]{24}$")


def _lib(request: Request) -> P.Library:
    return P.Library(P.local_library_dir(request.app.state.settings.database_path))


def _err(msg: str, code: int = 400, **extra) -> JSONResponse:
    return JSONResponse({"error": msg, **extra}, status_code=code)


async def _body(request: Request) -> tuple[dict | None, JSONResponse | None]:
    try:
        if int(request.headers.get("content-length") or 0) > P.MAX_PACK_BYTES:
            return None, _err("Content pack is too large", 413)
        d = await request.json()
    except ValueError:
        return None, _err("Not valid JSON")
    return (d, None) if isinstance(d, dict) else (None, _err("Not valid JSON"))


async def _gl(request: Request, server: str | None, fn):
    """Returns (result, error response); fn(client) runs as the signed-in user."""
    srv = _server(request, server)
    if srv is None:
        return None, _err("No Graylog server configured", 404)
    return await _call(request, srv, fn, P.PackClient)


def _rev(v) -> int | None:
    try:
        r = int(v)
    except (TypeError, ValueError):
        return None
    return r if r >= 1 else None


def _attachment(request: Request, pack: dict, lang, target: str) -> Response:
    """The pack and its guide, in the language the page is showing."""
    data, fname = pack_guide.bundle(pack, lang, _lib(request).guide_notes(str(pack.get("id"))), target)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition":
                             f"attachment; filename=\"pack-r{pack.get('rev')}.zip\"; "
                             f"filename*=UTF-8''{quote(fname)}"})


def _sensitive_gate(request: Request, pack: dict, body: dict, doing: str):
    """Returns (pack to use, refusal). A pack leaves this site only after someone decided what
    happens to the addresses and credentials in it. The default is to refuse, never to pass."""
    found = P.blocking_sensitive(pack)
    if not found:
        return pack, None
    choice = body.get("sensitive")
    if choice == "strip":
        try:
            return P.strip_sensitive(pack), None
        except P.PackError as e:
            return None, _err(str(e), 409, sensitive=found)
    if choice == "keep":
        _audit(request, "pack_sensitive_kept",
               f"{doing}: {pack.get('name')} {pack.get('id')} rev {pack.get('rev')} kept "
               f"{len(found)} sensitive value(s)")
        return pack, None
    return None, _err("This content pack holds e-mail addresses, endpoints or credentials - "
                      "decide what to do with them first", 409, sensitive=found, need_decision=True)


async def _load(request: Request, body: dict) -> tuple[dict | None, JSONResponse | None]:
    """The pack a request names: body.source is "library" or "graylog"."""
    pid, rev = str(body.get("id") or ""), _rev(body.get("rev"))
    if not P.is_pack_id(pid) or rev is None:
        return None, _err("Invalid content pack id or revision")
    if body.get("source") == "library":
        try:
            return _lib(request).get(pid, rev)[0], None
        except KeyError:
            return None, _err("Content pack not found in the library", 404)
    pack, err = await _gl(request, body.get("server"), lambda c: c.get_pack(pid, rev))
    return (None, err) if err else (pack, None)


# ---- Connected Graylog ------------------------------------------------------

@router.get("/packs/graylog")
async def graylog_list(request: Request, server: str = ""):
    out, err = await _gl(request, server, lambda c: c.latest())
    if err:
        return err
    packs, meta = out
    items = []
    for p in packs:
        item = P.list_item(p)
        item["installed_revs"] = sorted(int(r) for r in (meta.get(p.get("id")) or {}))
        items.append(item)
    srv = _server(request, server)
    return {"server": srv.name, "graylog_user": _ident(request, srv).username,
            "items": sorted(items, key=lambda i: str(i["name"]).lower())}


@router.get("/packs/graylog/{pack_id}/detail")
async def graylog_detail(request: Request, pack_id: str, server: str = ""):
    """Revisions and installations of one pack."""
    if not re.fullmatch(r"[\w.-]{1,64}", pack_id):
        return _err("Invalid content pack id or revision")

    async def fn(c):
        return await c.revisions(pack_id), await c.installations(pack_id)

    out, err = await _gl(request, server, fn)
    if err:
        return err
    revs, installs = out
    return {
        "revisions": sorted(int(r) for r in (revs.get("content_pack_revisions") or {})),
        "constraints": revs.get("constraints_result") or {},
        "installations": [{"id": i.get("_id"), "rev": i.get("content_pack_revision"),
                           "comment": i.get("comment") or "", "created_by": i.get("created_by") or "",
                           "created_at": i.get("created_at"),
                           "entities": [{"title": e.get("title"), "type": (e.get("type") or {}).get("name"),
                                         "found_on_system": bool(e.get("found_on_system"))}
                                        for e in i.get("entities") or []]} for i in installs],
    }


@router.post("/packs/view")
async def pack_view(request: Request):
    body, err = await _body(request)
    if err:
        return err
    if "pack" in body:      # a file about to be uploaded: nothing is stored yet
        errs = P.validate_pack(body["pack"])
        if errs:
            return _err(". ".join(errs))
        return P.view_of(body["pack"])
    pack, err = await _load(request, body)
    return err or P.view_of(pack)


@router.get("/packs/target-versions")
def pack_target_versions():
    return {"versions": pack_compat.TARGET_VERSIONS}


@router.post("/packs/sensitive")
async def pack_sensitive(request: Request):
    """What the download dialog shows before anything leaves."""
    body, err = await _body(request)
    if err:
        return err
    pack, err = await _load(request, body)
    return err or {"sensitive": P.blocking_sensitive(pack)}


@router.post("/packs/download")
async def pack_download(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pack, err = await _load(request, body)
    if err:
        return err
    pack, err = _sensitive_gate(request, pack, body, "download")
    if err:
        return err
    target = str(body.get("target_version") or "")
    if target:
        try:
            head, items = pack_compat.retarget(
                {k: v for k, v in pack.items() if k != "entities"}, pack["entities"], target)
        except ValueError as e:
            return _err(str(e))
        pack = {**head, "entities": items}
    return _attachment(request, pack, body.get("lang"), target)


@router.post("/packs/graylog/upload")
async def graylog_upload(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pack = body.get("pack")
    errs = P.validate_pack(pack)
    if errs:
        return _err(". ".join(errs))
    pack, err = _sensitive_gate(request, pack, body, "upload")
    if err:
        return err
    srv = _server(request, body.get("server"))
    _, err = await _gl(request, body.get("server"), lambda c: c.upload(pack))
    if err:
        return err
    _audit(request, "pack_upload", f"{pack['name']} {pack['id']} rev {pack['rev']} @ {srv.name}")
    return {"status": "ok", "id": pack["id"], "rev": pack["rev"]}


@router.post("/packs/graylog/save")
async def graylog_save(request: Request):
    """An edit made on a pack in Graylog: uploaded as the next revision. Nothing installed
    changes, and the revision it was based on stays."""
    body, err = await _body(request)
    if err:
        return err
    pid, base = str(body.get("id") or ""), _rev(body.get("base_rev"))
    if not P.is_pack_id(pid) or base is None:
        return _err("Invalid content pack id or revision")
    pack = body.get("pack")
    errs = P.validate_pack({**pack, "id": pid, "rev": base} if isinstance(pack, dict) else pack)
    if errs:
        return _err(". ".join(errs))

    async def fn(c):
        revs = sorted(int(r) for r in ((await c.revisions(pid)).get("content_pack_revisions") or {}))
        if not revs or revs[-1] != base:
            return None, revs
        new = P.as_new_revision(pack, pid, base + 1)
        await c.upload(new)
        return new, revs

    out, err = await _gl(request, body.get("server"), fn)
    if err:
        return err
    new, revs = out
    if new is None:
        return _err("A newer revision appeared while you were editing - reload and edit that one",
                    409, revisions=revs)
    srv = _server(request, body.get("server"))
    _audit(request, "pack_edit", f"{new['name']} {pid} rev {base} -> {new['rev']} @ {srv.name}")
    return {"status": "ok", "id": pid, "rev": new["rev"]}


@router.post("/packs/graylog/delete")
async def graylog_delete(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pid, rev = str(body.get("id") or ""), body.get("rev")
    if not re.fullmatch(r"[\w.-]{1,64}", pid):
        return _err("Invalid content pack id or revision")
    if rev is not None and _rev(rev) is None:
        return _err("Invalid content pack id or revision")

    async def fn(c):
        installs = await c.installations(pid)
        if rev is None and installs:
            return False
        await (c.delete_all(pid) if rev is None else c.delete_revision(pid, _rev(rev)))
        return True

    done, err = await _gl(request, body.get("server"), fn)
    if err:
        return err
    if not done:
        return _err("This content pack is installed - uninstall it first", 409)
    srv = _server(request, body.get("server"))
    _audit(request, "pack_delete", f"{pid} rev {rev if rev is not None else 'all'} @ {srv.name}")
    return {"status": "ok"}


@router.post("/packs/check")
async def pack_check(request: Request):
    """The install preview: what this pack would do on that Graylog. Writes nothing."""
    body, err = await _body(request)
    if err:
        return err
    if "pack" in body:
        pack = body["pack"]
        errs = P.validate_pack(pack)
        if errs:
            return _err(". ".join(errs))
    else:
        pack, err = await _load(request, body)
        if err:
            return err

    async def fn(c):
        live = await c.live_state()
        return live, await c.installations(pack["id"])

    out, err = await _gl(request, body.get("server"), fn)
    if err:
        return err
    live, installs = out
    return {"version": live["version"], "findings": P.check_install(pack, live),
            "sensitive": P.blocking_sensitive(pack),
            "installed_revs": sorted({i.get("content_pack_revision") for i in installs})}


@router.post("/packs/parse")
async def pack_parse(request: Request):
    """Graylog's parser on one rule or pipeline being edited; it stores nothing."""
    body, err = await _body(request)
    if err:
        return err
    kind = body.get("kind")
    if kind not in ("pipeline_rule", "pipeline"):
        return _err("Only rules and pipelines can be checked")
    out, err = await _gl(request, body.get("server"),
                         lambda c: c.parse_source(kind, str(body.get("source") or "")))
    return err or {"errors": out}


@router.post("/packs/install")
async def pack_install(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pack, err = await _load(request, body)
    if err:
        return err
    if body.get("source") == "library":     # leaving the library for another Graylog
        pack, err = _sensitive_gate(request, pack, body, "install")
        if err:
            return err
    pid, rev = pack["id"], pack["rev"]
    params = body.get("parameters") if isinstance(body.get("parameters"), dict) else {}
    uploaded = []

    async def fn(c):
        findings = P.check_install(pack, await c.live_state())
        if any(f["level"] == "block" for f in findings):
            return {"blocked": findings}
        if body.get("source") == "library":
            have = await c.has_revision(pid, rev)
            if have is None:
                await c.upload(pack)
                uploaded.append(rev)
            elif not P.same_content(have, pack):
                return {"differs": True}
        try:
            inst = await c.install(pid, rev, params, str(body.get("comment") or ""))
        except Exception:
            # Graylog rolled the install back; do not leave our upload behind either.
            if uploaded:
                try:
                    await c.delete_revision(pid, rev)
                except Exception as e:
                    log.warning("Could not remove the revision uploaded for a failed install",
                                pack=pid, rev=rev, error=str(e))
            raise
        return {"installation": inst, "findings": findings}

    srv = _server(request, body.get("server"))
    out, err = await _gl(request, body.get("server"), fn)
    if err:
        return err
    if out.get("blocked"):
        return _err("Graylog would refuse this install - see the install preview", 409,
                    findings=out["blocked"])
    if out.get("differs"):
        return _err("This Graylog already has this revision with different content - "
                    "save the library copy as a new revision first", 409)
    inst = out["installation"]
    ents = inst.get("entities") or []
    _audit(request, "pack_install", f"{pack.get('name')} {pid} rev {rev} @ {srv.name}: "
                                    f"{len(ents)} entities, installation {inst.get('_id')}")
    return {"status": "ok", "installation_id": inst.get("_id"), "entity_count": len(ents),
            "paused_streams": [{"id": e.get("id"), "title": e.get("title")} for e in ents
                               if (e.get("type") or {}).get("name") == "stream"
                               and not e.get("found_on_system")],
            "findings": out["findings"]}


@router.post("/packs/start-streams")
async def pack_start_streams(request: Request):
    """A stream comes out of an install paused; this is the follow-up, only when asked."""
    body, err = await _body(request)
    if err:
        return err
    ids = [str(i) for i in (body.get("stream_ids") or []) if re.fullmatch(r"[0-9a-f]{24}", str(i))]
    if not ids:
        return _err("Select at least one stream")

    async def fn(c):
        for i in ids:
            await c.start_stream(i)

    _, err = await _gl(request, body.get("server"), fn)
    if err:
        return err
    srv = _server(request, body.get("server"))
    _audit(request, "pack_start_streams", f"{', '.join(ids)} @ {srv.name}")
    return {"status": "ok", "started": len(ids)}


@router.post("/packs/uninstall-preview")
async def pack_uninstall_preview(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pid, iid = str(body.get("id") or ""), str(body.get("installation_id") or "")
    if not _INSTALL_ID.match(iid) or not re.fullmatch(r"[\w.-]{1,64}", pid):
        return _err("Invalid content pack id or revision")
    out, err = await _gl(request, body.get("server"), lambda c: c.uninstall_details(pid, iid))
    if err:
        return err
    return {"entities": [{"title": e.get("title"), "type": (e.get("type") or {}).get("name"),
                          "found_on_system": bool(e.get("found_on_system"))}
                         for e in out.get("entities") or []]}


@router.post("/packs/uninstall")
async def pack_uninstall(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pid, iid = str(body.get("id") or ""), str(body.get("installation_id") or "")
    if not _INSTALL_ID.match(iid) or not re.fullmatch(r"[\w.-]{1,64}", pid):
        return _err("Invalid content pack id or revision")
    out, err = await _gl(request, body.get("server"), lambda c: c.uninstall(pid, iid))
    if err:
        return err
    srv = _server(request, body.get("server"))
    failed = out.get("failed_entities") or []
    skipped = out.get("skipped_entities") or []
    _audit(request, "pack_uninstall", f"{pid} installation {iid} @ {srv.name}: "
                                      f"{len(failed)} failed, {len(skipped)} kept")
    return {"status": "ok", "removed": len(out.get("entity_objects") or {}),
            "failed": len(failed), "skipped": len(skipped)}


# ---- The library ------------------------------------------------------------

@router.get("/packs/library")
def library_list(request: Request):
    return {"items": _lib(request).list()}


@router.post("/packs/library/upload")
async def library_upload(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pack = body.get("pack")
    try:
        _lib(request).add(pack)
    except P.PackError as e:
        return _err(str(e))
    except OSError as e:
        return _err(sanitize(f"Could not write to the library: {e}"), 500)
    _audit(request, "pack_library_add", f"{pack.get('name')} {pack.get('id')} rev {pack.get('rev')}")
    return {"status": "ok", "id": pack["id"], "rev": pack["rev"]}


@router.post("/packs/library/from-graylog")
async def library_from_graylog(request: Request):
    """Copy a revision from a connected Graylog into the library."""
    body, err = await _body(request)
    if err:
        return err
    pack, err = await _load(request, {**body, "source": "graylog"})
    if err:
        return err
    try:
        _lib(request).add(pack)
    except P.PackError as e:
        return _err(str(e))
    except OSError as e:
        return _err(sanitize(f"Could not write to the library: {e}"), 500)
    _audit(request, "pack_library_add", f"{pack.get('name')} {pack.get('id')} rev {pack.get('rev')}"
                                        f" from Graylog {body.get('server')}")
    return {"status": "ok", "id": pack["id"], "rev": pack["rev"]}


@router.post("/packs/library/save")
async def library_save(request: Request):
    """An edit: stored as the next revision, next to the one it came from."""
    body, err = await _body(request)
    if err:
        return err
    pid, base = str(body.get("id") or ""), _rev(body.get("base_rev"))
    if not P.is_pack_id(pid) or base is None:
        return _err("Invalid content pack id or revision")
    lib = _lib(request)
    revs = lib.revisions(pid)
    if not revs:
        return _err("Content pack not found in the library", 404)
    if revs[-1] != base:
        return _err("A newer revision appeared while you were editing - reload and edit that one",
                    409, revisions=revs)
    pack = body.get("pack")
    if not isinstance(pack, dict):
        return _err("Not a content pack: expected a JSON object")
    new = P.as_new_revision(pack, pid, base + 1)
    try:
        lib.add(new)
    except P.PackError as e:
        return _err(str(e))
    except OSError as e:
        return _err(sanitize(f"Could not write to the library: {e}"), 500)
    _audit(request, "pack_edit", f"{new.get('name')} {pid} rev {base} -> {new['rev']} (library)")
    return {"status": "ok", "id": pid, "rev": new["rev"]}


@router.post("/packs/library/delete")
async def library_delete(request: Request):
    body, err = await _body(request)
    if err:
        return err
    pid, rev = str(body.get("id") or ""), _rev(body.get("rev"))
    if not P.is_pack_id(pid) or rev is None:
        return _err("Invalid content pack id or revision")
    try:
        _lib(request).delete(pid, rev)
    except KeyError:
        return _err("Content pack not found in the library", 404)
    except P.PackError as e:
        return _err(str(e))
    except OSError as e:
        return _err(sanitize(f"Could not write to the library: {e}"), 500)
    _audit(request, "pack_library_delete", f"{pid} rev {rev}")
    return {"status": "ok"}


@router.post("/packs/diff")
async def pack_diff(request: Request):
    """The review step before an edit is saved."""
    body, err = await _body(request)
    if err:
        return err
    new = body.get("pack")
    errs = P.validate_pack(new)
    if errs:
        return _err(". ".join(errs))
    old, err = await _load(request, body)
    if err:
        return err
    return {**P.diff_packs(old, new), "analysis": P.analyze(new)}

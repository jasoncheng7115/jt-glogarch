/* jt-glogarch — Content packs page: each connected Graylog's packs, plus the Jason Tools
 * library. Writes never trust the copy held here: the server re-reads Graylog first and
 * re-runs the install check (web/routes/packs.py). An edit never overwrites anything:
 * revisions are immutable, so it is saved as the next one. */

const _pk = {
    server: '', servers: [], loginUser: '', tab: 'graylog', q: '', onlyInstalled: false,
    gl: null, lib: [], v: null, pendingInstall: null, pendingUninstall: null, pendingFile: null,
    afterSignin: null,
};

const PK_TYPE_ORDER = ['dashboard', 'pipeline', 'pipeline_rule', 'stream', 'event_definition',
    'notification', 'lookup_table', 'lookup_cache', 'lookup_adapter', 'grok_pattern', 'input'];

function pkTypeLabel(type) {
    const k = 'pk_t_' + type;
    const s = t(k);
    return s === k ? type : s;
}

function pkJsonPost(url, body) {
    return fetchJSON(`${API}${url}`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)});
}

function pkMsg(text, level) {
    const el = document.getElementById('pk-message');
    if (!el) return;
    el.className = 'pk-message ' + (level === 'err' ? 'pk-err' : 'pk-ok');
    el.textContent = text || '';
    el.classList.toggle('hidden', !text);
}

// ---- Page ------------------------------------------------------------------

async function pkInit() {
    if (!document.getElementById('pk-tabs')) return;
    const d = await fetchJSON(`${API}/alerting/servers`);
    _pk.servers = d.items || [];
    _pk.loginUser = d.login_user || '';
    const sel = document.getElementById('pk-server');
    sel.innerHTML = _pk.servers.map(s => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
    _pk.server = d.default || (_pk.servers[0] || {}).name || '';
    sel.value = _pk.server;
    initCustomSelects();
    await pkReload();
}

async function pkReload() {
    pkMsg('');
    await Promise.all([pkLoadGraylog(), pkLoadLibrary()]);
    pkRender();
}

function pkServerChange(name) {
    _pk.server = name;
    _pk.gl = null;
    pkReload();
}

function pkTab(tab) {
    _pk.tab = tab;
    document.querySelectorAll('#pk-tabs .arch-tab').forEach(b => b.classList.toggle('active', b.dataset.arg === tab));
    pkMsg('');
    pkRender();
}

function pkSearch(q) { _pk.q = String(q || '').toLowerCase(); pkRender(); }

function pkToggleInstalled(checked) { _pk.onlyInstalled = !!checked; pkRender(); }

async function pkLoadGraylog() {
    const d = await fetchJSON(`${API}/packs/graylog?server=${encodeURIComponent(_pk.server)}`);
    if (d.need_signin) { _pk.gl = {needSignin: true, error: d.error, items: []}; return; }
    if (d.error) { _pk.gl = {error: d.error, items: []}; return; }
    _pk.gl = d;
}

async function pkLoadLibrary() {
    const d = await fetchJSON(`${API}/packs/library`);
    _pk.lib = d.items || [];
}

function pkRenderWho() {
    const el = document.getElementById('pk-who');
    if (!el) return;
    if (_pk.gl && _pk.gl.needSignin) {
        el.className = 'al-who al-warn';
        el.innerHTML = `${esc(t('al_need_signin'))} <button class="btn-sm btn-primary" data-act="pkOpenSignin">${icon('login', 14)} ${t('al_signin_btn')}</button>`;
    } else if (_pk.gl && _pk.gl.graylog_user) {
        el.className = 'al-who';
        el.innerHTML = t('al_acting_as').replace('{user}', `<strong>${esc(_pk.gl.graylog_user)}</strong>`);
    } else {
        el.className = 'al-who';
        el.textContent = '';
    }
}

function pkMatches(p) {
    if (!_pk.q) return true;
    return `${p.name}\n${p.summary}\n${p.description}\n${p.vendor}`.toLowerCase().includes(_pk.q);
}

function pkCountsText(counts) {
    return Object.entries(counts || {})
        .sort((a, b) => PK_TYPE_ORDER.indexOf(a[0]) - PK_TYPE_ORDER.indexOf(b[0]))
        .map(([k, n]) => `${pkTypeLabel(k)} ${n}`).join(' · ');
}

function pkRender() {
    pkRenderWho();
    const hint = document.getElementById('pk-hint');
    const installedWrap = document.getElementById('pk-installed-wrap');
    if (hint) hint.textContent = t(_pk.tab === 'graylog' ? 'pk_hint_graylog' : 'pk_hint_library');
    if (installedWrap) installedWrap.classList.toggle('hidden', _pk.tab !== 'graylog');
    if (_pk.tab === 'graylog') pkRenderGraylog(); else pkRenderLibrary();
}

/** Same buttons as the rest of the app. Under a narrow window the words give way to the
 *  icons (util.css), so a pack stays one line; the title keeps the word. */
function pkBtn(act, args, iconName, key, cls) {
    const label = esc(t(key));
    return `<button class="btn-sm ${cls || 'btn-secondary'} pk-btn" title="${label}" aria-label="${label}" data-act="${act}" data-args="${esc(JSON.stringify(args))}">${icon(iconName, 14)}<span>${label}</span></button>`;
}

const PK_BTN_GAP = '<span class="pk-btn-gap"></span>';

/** "Jason Cheng <j@x>" -> "Jason Cheng": the address is in the tooltip, not the column. */
function pkVendorCell(vendor) {
    const v = String(vendor || '');
    return `<td class="pk-vendor" title="${esc(v)}">${esc(v.replace(/\s*<[^>]*>\s*$/, '') || v)}</td>`;
}

/** One tag per kind of item; past three the rest are counted, with the full list on hover. */
function pkCountChips(counts) {
    const rows = Object.entries(counts || {}).sort((a, b) => {
        const x = PK_TYPE_ORDER.indexOf(a[0]), y = PK_TYPE_ORDER.indexOf(b[0]);
        return (x < 0 ? 99 : x) - (y < 0 ? 99 : y);
    });
    if (!rows.length) return '<span class="text-muted">0</span>';
    const chip = ([k, n]) => `<span class="pk-chip">${esc(pkTypeLabel(k))}<strong>${esc(n)}</strong></span>`;
    const more = rows.length > 3 ? `<span class="pk-chip pk-chip-more">+${rows.length - 3}</span>` : '';
    return `<div class="pk-chips" title="${esc(pkCountsText(counts))}">${rows.slice(0, 3).map(chip).join('')}${more}</div>`;
}

/** A summary repeating the name ("AD" / "AD") says nothing; many packs have one. */
function pkNameCell(p, act) {
    const sum = String(p.summary || '').trim();
    const show = sum && sum.toLowerCase() !== String(p.name || '').trim().toLowerCase();
    const flag = p.sensitive ? `<span class="pk-badge pk-badge-danger" title="${esc(t('pk_s_chip_tip'))}">${esc(t('pk_s_chip').replace('{n}', p.sensitive))}</span>` : '';
    return `<td class="pk-name-cell"><div class="pk-name-row"><a class="pk-name" data-act="${act}" data-args="${esc(JSON.stringify([p.id, p.rev]))}" title="${esc(p.name)}">${esc(p.name)}</a>${flag}</div>
        ${show ? `<div class="pk-sum" title="${esc(sum)}">${esc(sum)}</div>` : ''}</td>`;
}

function pkInstalledCell(revs) {
    return revs.length
        ? `<span class="pk-badge pk-badge-ok">${esc(t('pk_installed_rev').replace('{rev}', revs.join(', ')))}</span>`
        : `<span class="text-muted">${esc(t('pk_not_installed'))}</span>`;
}

function pkRenderGraylog() {
    const host = document.getElementById('pk-table');
    if (!host) return;
    const g = _pk.gl || {items: []};
    if (g.error && !g.needSignin) { host.innerHTML = `<div class="u141">${esc(g.error)}</div>`; return; }
    if (g.needSignin) { host.innerHTML = `<div class="u143">${esc(t('al_need_signin'))}</div>`; return; }
    const items = (g.items || []).filter(p => pkMatches(p) && (!_pk.onlyInstalled || p.installed_revs.length));
    const count = document.getElementById('pk-count');
    if (count) count.textContent = t('pk_count').replace('{n}', items.length).replace('{total}', (g.items || []).length);
    if (!items.length) { host.innerHTML = `<div class="u143">${esc(t('pk_empty_graylog'))}</div>`; return; }
    host.innerHTML = `<table class="pk-table pk-list"><thead><tr><th>${t('pk_col_name')}</th><th>${t('pk_col_vendor')}</th><th>${t('pk_col_rev')}</th><th>${t('pk_col_content')}</th><th>${t('pk_col_installed')}</th><th>${t('pk_col_actions')}</th></tr></thead><tbody>` +
        items.map(p => {
            const on = p.installed_revs.length > 0;
            return `<tr>
            ${pkNameCell(p, 'pkOpenGraylog')}
            ${pkVendorCell(p.vendor)}
            <td>${esc(p.rev)}</td>
            <td>${pkCountChips(p.counts)}</td>
            <td class="pk-nowrap">${pkInstalledCell(p.installed_revs)}</td>
            <td class="pk-nowrap"><div class="pk-btns">
                ${pkBtn('pkOpenGraylog', [p.id, p.rev], 'eye', 'pk_view')}
                ${pkBtn('pkEditGraylog', [p.id, p.rev], 'edit', 'pk_edit')}
                ${pkBtn('pkDownload', ['graylog', p.id, p.rev], 'download', 'pk_download')}
                ${on ? pkBtn('pkUninstallStart', [p.id], 'close', 'pk_uninstall', 'btn-danger pk-btn-slot') : pkBtn('pkInstallGraylog', [p.id, p.rev], 'play', 'pk_install', 'btn-primary pk-btn-slot')}
                ${on ? PK_BTN_GAP : pkBtn('pkDeleteGraylog', [p.id, p.name], 'trash', 'btn_delete', 'btn-danger')}
            </div></td></tr>`;
        }).join('') + '</tbody></table>';
}

function pkInstalledOnServer(id) {
    const hit = ((_pk.gl && _pk.gl.items) || []).find(p => p.id === id);
    return hit ? hit.installed_revs : [];
}

function pkRenderLibrary() {
    const host = document.getElementById('pk-table');
    if (!host) return;
    const items = _pk.lib.filter(pkMatches);
    const count = document.getElementById('pk-count');
    if (count) count.textContent = t('pk_count').replace('{n}', items.length).replace('{total}', _pk.lib.length);
    if (!items.length) { host.innerHTML = `<div class="u143">${esc(t(_pk.lib.length ? 'pk_empty_graylog' : 'pk_empty_library'))}</div>`; return; }
    host.innerHTML = `<table class="pk-table pk-list"><thead><tr><th>${t('pk_col_name')}</th><th>${t('pk_col_rev')}</th><th>${t('pk_col_origin')}</th><th>${t('pk_col_content')}</th><th>${esc(t('pk_col_on_server').replace('{server}', _pk.server))}</th><th>${t('pk_col_actions')}</th></tr></thead><tbody>` +
        items.map(p => `<tr>
            ${pkNameCell(p, 'pkOpenLibrary')}
            <td>${esc(p.rev)}</td>
            <td class="pk-nowrap">${pkOriginBadge(p.origin)}</td>
            <td>${pkCountChips(p.counts)}</td>
            <td class="pk-nowrap">${pkInstalledCell(pkInstalledOnServer(p.id))}</td>
            <td class="pk-nowrap"><div class="pk-btns">
                ${pkBtn('pkOpenLibrary', [p.id, p.rev], 'eye', 'pk_view')}
                ${pkBtn('pkEditLibrary', [p.id, p.rev], 'edit', 'pk_edit')}
                ${pkBtn('pkDownload', ['library', p.id, p.rev], 'download', 'pk_download')}
                ${pkBtn('pkInstallLibrary', [p.id, p.rev], 'play', 'pk_install', 'btn-primary')}
                ${p.origin === 'local' ? pkBtn('pkDeleteLibrary', [p.id, p.rev], 'trash', 'btn_delete', 'btn-danger') : PK_BTN_GAP}
            </div></td></tr>`).join('') + '</tbody></table>';
}

function pkOriginBadge(origin) {
    return origin === 'published'
        ? `<span class="pk-badge pk-badge-ok">${esc(t('pk_origin_published'))}</span>`
        : `<span class="pk-badge">${esc(t('pk_origin_local'))}</span>`;
}

// ---- Sign in ---------------------------------------------------------------

function pkOpenSignin(why, after) {
    const m = document.getElementById('pk-signin-modal');
    if (!m) return;
    document.querySelectorAll('.pk-modal-x').forEach(b => { if (!b.firstChild) b.innerHTML = icon('close', 16); });
    _pk.afterSignin = typeof after === 'function' ? after : null;
    const u = document.getElementById('pk-signin-user');
    if (u && !u.value && _pk.loginUser && !['localadmin', 'token-user'].includes(_pk.loginUser)) u.value = _pk.loginUser;
    document.getElementById('pk-signin-why').textContent =
        (typeof why === 'string' && why ? why + ' — ' : '') + t('al_signin_why').replace('{server}', _pk.server);
    document.getElementById('pk-signin-result').textContent = '';
    m.classList.remove('hidden');
    m.style.display = 'flex';
}

function pkCloseSignin() {
    const m = document.getElementById('pk-signin-modal');
    if (m) { m.classList.add('hidden'); m.style.display = 'none'; }
    const p = document.getElementById('pk-signin-pass');
    if (p) p.value = '';
}

async function pkSignin() {
    const user = document.getElementById('pk-signin-user').value.trim();
    const pass = document.getElementById('pk-signin-pass').value;
    const r = await pkJsonPost('/alerting/signin', {server: _pk.server, username: user, password: pass});
    if (r.error) {
        document.getElementById('pk-signin-result').innerHTML = `<span class="pk-err">${esc(r.error)}</span>`;
        return;
    }
    pkCloseSignin();
    const after = _pk.afterSignin;
    _pk.afterSignin = null;
    await pkReload();
    if (after) after();
}

// ---- Viewer ----------------------------------------------------------------

function pkShow(id, on) {
    const m = document.getElementById(id);
    if (!m) return;
    m.classList.toggle('hidden', !on);
    m.style.display = on ? 'flex' : 'none';
}

async function pkOpen(source, id, rev, pane, edit) {
    const d = await pkJsonPost('/packs/view', {source, id, rev, server: _pk.server});
    if (d.need_signin) { pkOpenSignin(d.error, () => pkOpen(source, id, rev, pane, edit)); return; }
    if (d.error) { pkMsg(d.error, 'err'); return; }
    await pkShowViewer(source, d, pane, edit);
}

async function pkShowViewer(source, data, pane, edit) {
    _pk.v = {source, data, pack: data.pack, working: null, removed: new Set(), pane: pane || 'overview',
        sel: null, tab: 0, filter: '', detail: null, check: null, result: null, jsonError: ''};
    if (source === 'graylog') {
        const d = await fetchJSON(`${API}/packs/graylog/${encodeURIComponent(data.pack.id)}/detail?server=${encodeURIComponent(_pk.server)}`);
        if (!d.error) _pk.v.detail = d;
    } else if (source === 'library') {
        const hit = _pk.lib.find(p => p.id === data.pack.id);
        _pk.v.detail = {revisions: hit ? hit.revs.map(r => r.rev) : [data.pack.rev], installations: []};
    }
    if (edit) pkStartEdit(); else pkRenderViewer();
    pkShow('pk-viewer', true);
    document.querySelectorAll('.pk-modal-x').forEach(b => { if (!b.firstChild) b.innerHTML = icon('close', 16); });
    if (pane === 'install') pkRunCheck();
}

function pkOpenGraylog(id, rev) { pkOpen('graylog', id, rev); }
function pkEditGraylog(id, rev) { pkOpen('graylog', id, rev, 'overview', true); }
function pkInstallGraylog(id, rev) { pkOpen('graylog', id, rev, 'install'); }
function pkOpenLibrary(id, rev) { pkOpen('library', id, rev); }
function pkEditLibrary(id, rev) { pkOpen('library', id, rev, 'overview', true); }
function pkInstallLibrary(id, rev) { pkOpen('library', id, rev, 'install'); }

function pkCloseViewer() {
    pkShow('pk-viewer', false);
    _pk.v = null;
}

/** The corner X. While editing, the footer's only way out says it discards; the X must not
 *  throw edits away more quietly than that. */
function pkAskCloseViewer() {
    const v = _pk.v;
    if (!v) return;
    if (v.working && JSON.stringify(pkFinal()) !== JSON.stringify(v.pack)) {
        showConfirm(t('pk_cancel_edit'), t('pk_discard_confirm'), () => pkCloseViewer());
        return;
    }
    pkCloseViewer();
}

function pkPane(pane) {
    const v = _pk.v;
    if (!v) return;
    v.pane = pane;
    if (v.working) {
        pkRefreshWorking().then(pkRenderViewer);
        return;
    }
    pkRenderViewer();
    if (pane === 'install' && !v.check) pkRunCheck();
}

/** The normalized view is built by the server; ask again after edits so the dashboard
 *  layout and reference warnings describe what is being edited. */
async function pkRefreshWorking() {
    const v = _pk.v;
    if (!v || !v.working) return;
    const d = await pkJsonPost('/packs/view', {pack: pkFinal()});
    if (!d.error) v.data = d;
}

function pkRevChange(rev) {
    const v = _pk.v;
    if (v) pkOpen(v.source, v.pack.id, Number(rev), v.pane);
}

function pkRenderViewer() {
    const v = _pk.v;
    if (!v) return;
    const p = v.working || v.pack;
    const revs = (v.detail && v.detail.revisions) || [v.pack.rev];
    document.getElementById('pk-v-title').textContent = p.name || '';
    document.getElementById('pk-v-rev').innerHTML = v.source === 'upload' || v.working
        ? `<span class="pk-badge">${esc(t(v.working ? 'pk_editing_rev' : 'pk_upload_preview').replace('{rev}', v.pack.rev))}</span>`
        : `<label class="al-inline-label">${t('pk_col_rev')}</label> <select data-act-change="pkRevChange">${revs.map(r => `<option value="${esc(r)}"${r === v.pack.rev ? ' selected' : ''}>${esc(r)}</option>`).join('')}</select>`;
    const panes = [['overview', 'pk_p_overview'], ['contents', 'pk_p_contents'], ['dashboards', 'pk_p_dashboards'],
        ['install', 'pk_p_install'], ['json', 'pk_p_json']];
    if (v.working) panes.splice(3, 1);
    document.getElementById('pk-v-tabs').innerHTML = panes.map(([k, key]) =>
        `<button class="arch-tab${v.pane === k ? ' active' : ''}" data-act="pkPane" data-arg="${k}">${t(key)}</button>`).join('');
    const body = document.getElementById('pk-v-body');
    if (v.pane === 'contents') body.innerHTML = pkPaneContents();
    else if (v.pane === 'dashboards') { body.innerHTML = pkPaneDashboards(); pkApplyGrid(); }
    else if (v.pane === 'install') body.innerHTML = pkPaneInstall();
    else if (v.pane === 'json') body.innerHTML = pkPaneJson();
    else body.innerHTML = pkPaneOverview();
    document.getElementById('pk-v-buttons').innerHTML = pkViewerButtons();
    initCustomSelects();
}

function pkViewerButtons() {
    const v = _pk.v;
    const close = `<button class="btn-secondary" data-act="pkCloseViewer">${icon('close')} ${t('pk_close')}</button>`;
    if (v.working) {
        return `<button class="btn-primary" data-act="pkReview">${icon('eye')} ${t('pk_review')}</button>
            <button class="btn-secondary" data-act="pkCancelEdit">${t('pk_cancel_edit')}</button>`;
    }
    if (v.source === 'upload') {
        const lib = _pk.tab === 'library';
        return `<button class="btn-primary" data-act="pkConfirmUpload">${icon('upload')} ${esc(lib ? t('pk_add_library') : t('pk_upload_to').replace('{server}', _pk.server))}</button>${close}`;
    }
    const extra = v.source === 'graylog'
        ? `<button class="btn-secondary" data-act="pkCopyToLibrary">${icon('copy')} ${t('pk_copy_library')}</button>`
        : `<button class="btn-secondary" data-act="pkUploadFromLibrary">${icon('upload')} ${esc(t('pk_upload_to').replace('{server}', _pk.server))}</button>`;
    const installed = ((v.detail && v.detail.installations) || []).some(i => i.rev === v.pack.rev);
    const revs = (v.detail && v.detail.revisions) || [];
    const delRev = v.source === 'graylog' && revs.length > 1 && !installed
        ? `<button class="btn-danger" data-act="pkDeleteRevision">${icon('trash')} ${t('pk_delete_rev')}</button>` : '';
    return `<button class="btn-secondary" data-act="pkStartEdit">${icon('edit')} ${t('pk_edit')}</button>
        <button class="btn-primary" data-act="pkPane" data-arg="install">${icon('play')} ${t('pk_install')}</button>
        <button class="btn-secondary" data-act="pkDownload" data-args="${esc(JSON.stringify([v.source, v.pack.id, v.pack.rev]))}">${icon('download')} ${t('pk_download')}</button>
        ${extra}${delRev}${close}`;
}

function pkRefWarnings(a) {
    const rows = [];
    const add = (key, items) => { if (items && items.length) rows.push({key, items}); };
    add('pk_f_rule_missing', (a.missing_rules || []).map(m => `${m.pipeline}: ${m.rule}`));
    add('pk_f_title_mismatch', a.title_mismatch);
    add('pk_f_lookup_used', a.lookup_tables_used);
    add('pk_f_stream_refs', a.stream_refs);
    add('pk_f_default_stream', a.default_stream_pipelines);
    return rows.map(r => pkFindingBox('warn', t(r.key), r.items)).join('');
}

function pkFindingBox(level, text, items) {
    return `<div class="pk-finding pk-${esc(level)}"><div>${esc(text)}</div>${(items || []).length ? `<ul>${items.slice(0, 40).map(i => `<li>${esc(i)}</li>`).join('')}${items.length > 40 ? `<li>${esc(t('pk_more').replace('{n}', items.length - 40))}</li>` : ''}</ul>` : ''}</div>`;
}

function pkPaneOverview() {
    const v = _pk.v;
    const a = v.data.analysis;
    const fields = [['name', 'pk_m_name'], ['summary', 'pk_m_summary'], ['description', 'pk_m_description'],
        ['vendor', 'pk_col_vendor'], ['url', 'pk_m_url']];
    let meta;
    if (v.working) {
        meta = fields.map(([k, key]) => `<div class="form-group"><label>${t(key)}</label>${k === 'description'
            ? `<textarea class="pk-input" rows="3" data-act-change="pkEditMeta" data-act-self data-field="${k}">${esc(v.working[k] || '')}</textarea>`
            : `<input type="text" class="pk-input" value="${esc(v.working[k] || '')}" data-act-change="pkEditMeta" data-act-self data-field="${k}">`}</div>`).join('');
    } else {
        meta = `<table class="pk-kv">${fields.filter(([k]) => v.pack[k]).map(([k, key]) => `<tr><th>${t(key)}</th><td class="pk-pre">${esc(v.pack[k])}</td></tr>`).join('')}
            <tr><th>${t('pk_m_id')}</th><td class="pk-mono">${esc(v.pack.id)}</td></tr></table>`;
    }
    const counts = Object.entries(a.counts).sort((x, y) => PK_TYPE_ORDER.indexOf(x[0]) - PK_TYPE_ORDER.indexOf(y[0]))
        .map(([k, n]) => `<div class="pk-count"><strong>${esc(n)}</strong><span>${esc(pkTypeLabel(k))}</span></div>`).join('');
    const installs = ((v.detail && v.detail.installations) || []);
    const installRows = installs.length ? `<h4>${t('pk_installations')}</h4><table class="pk-table"><thead><tr><th>${t('pk_col_rev')}</th><th>${t('pk_col_by')}</th><th>${t('pk_col_when')}</th><th>${t('pk_col_content')}</th><th></th></tr></thead><tbody>${installs.map(i => `<tr><td>${esc(i.rev)}</td><td>${esc(i.created_by)}</td><td>${esc(String(i.created_at || '').slice(0, 19).replace('T', ' '))}</td><td>${esc(i.entities.length)}</td><td><button class="btn-sm btn-danger" data-act="pkUninstallOne" data-args="${esc(JSON.stringify([v.pack.id, i.id]))}">${t('pk_uninstall')}</button></td></tr>`).join('')}</tbody></table>` : '';
    const sens = v.data.sensitive || [];
    const blocking = sens.filter(f => ['email', 'credential', 'endpoint'].includes(f.kind));
    const soft = sens.filter(f => !blocking.includes(f));
    const sensBox = (blocking.length ? pkFindingBox('block', t('pk_s_intro').replace('{n}', blocking.length)) + pkSensitiveBox(blocking) : '') +
        (soft.length ? pkFindingBox('info', t('pk_s_soft').replace('{n}', soft.length), [...new Set(soft.map(f => f.value))]) : '');
    return `${sensBox}${meta}<div class="pk-counts-row">${counts || `<span class="text-muted">${esc(t('pk_no_entities'))}</span>`}</div>${pkRefWarnings(a)}${installRows}`;
}

// ---- Contents --------------------------------------------------------------

function pkPaneContents() {
    const v = _pk.v;
    const list = v.working ? v.working.entities : v.pack.entities;
    const views = {};
    v.data.entities.forEach(e => { views[e.id] = e; });
    const groups = {};
    list.forEach((e, i) => {
        const type = (e.type || {}).name || '?';
        (groups[type] = groups[type] || []).push({e, i});
    });
    const f = v.filter.toLowerCase();
    const titleOf = e => pkEntityTitle(e);
    const order = Object.keys(groups).sort((a, b) => {
        const x = PK_TYPE_ORDER.indexOf(a), y = PK_TYPE_ORDER.indexOf(b);
        return (x < 0 ? 99 : x) - (y < 0 ? 99 : y);
    });
    const nav = order.map(type => {
        const rows = groups[type].filter(({e}) => !f || titleOf(e).toLowerCase().includes(f));
        if (!rows.length) return '';
        return `<details class="pk-group" ${f || groups[type].length <= 12 || groups[type].some(r => r.i === v.sel) ? 'open' : ''}>
            <summary>${esc(pkTypeLabel(type))} (${esc(rows.length)})</summary>
            ${rows.map(({e, i}) => `<div class="pk-nav-row${i === v.sel ? ' active' : ''}${v.removed.has(e.id) ? ' pk-removed' : ''}">
                ${v.working ? `<input type="checkbox" title="${esc(t('pk_keep'))}" ${v.removed.has(e.id) ? '' : 'checked'} data-act-change="pkToggleKeep" data-act-self data-id="${esc(e.id)}">` : ''}
                <a data-act="pkSelect" data-args="[${i}]">${esc(titleOf(e))}</a></div>`).join('')}
        </details>`;
    }).join('');
    const sel = v.sel !== null ? list[v.sel] : null;
    const detail = !sel ? `<div class="u143">${esc(t('pk_pick_entity'))}</div>`
        : (v.working ? pkEntityEditor(sel) : pkEntityDetail(views[sel.id], sel));
    return `<div class="pk-split"><div class="pk-nav">
        <input type="text" class="pk-input" placeholder="${esc(t('pk_filter_entities'))}" value="${esc(v.filter)}" data-act-change="pkFilterEntities" data-act-self>
        ${nav}</div><div class="pk-detail">${detail}</div></div>`;
}

function pkEntityTitle(e) {
    const d = e.data || {};
    return String(pkGet(d, 'title') || pkGet(d, 'name') || e.id);
}

function pkGet(o, k) {
    const x = o ? o[k] : undefined;
    return x && typeof x === 'object' && '@value' in x ? x['@value'] : x;
}

function pkSet(o, k, value) {
    if (o[k] && typeof o[k] === 'object' && '@value' in o[k]) o[k]['@value'] = value;
    else o[k] = value;
}

function pkFilterEntities(el) { _pk.v.filter = el.value; pkRenderViewer(); }

function pkSelect(i) { _pk.v.sel = i; pkRenderViewer(); }

function pkToggleKeep(el) {
    const v = _pk.v;
    if (el.checked) v.removed.delete(el.dataset.id); else v.removed.add(el.dataset.id);
    pkRenderViewer();
}

function pkKv(rows) {
    return `<table class="pk-kv">${rows.filter(r => r[1] !== '' && r[1] !== null && r[1] !== undefined)
        .map(([k, val]) => `<tr><th>${esc(k)}</th><td>${esc(val)}</td></tr>`).join('')}</table>`;
}

function pkDuration(ms) {
    return ms === null || ms === undefined ? '' : alDuration(ms);
}

function pkEntityDetail(view, raw) {
    if (!view) return '';
    let out = `<h4>${esc(view.title)} <span class="pk-sub">${esc(pkTypeLabel(view.type))}</span></h4>`;
    if (view.description) out += `<p class="pk-sub pk-pre">${esc(view.description)}</p>`;
    if (view.type === 'pipeline') {
        out += `<table class="pk-table"><thead><tr><th>${t('pk_stage')}</th><th>${t('pk_match')}</th><th>${t('pk_t_pipeline_rule')}</th></tr></thead><tbody>${view.stages.map(s => `<tr><td>${esc(s.stage)}</td><td>${esc(s.match)}</td><td>${s.rules.map(r => esc(r)).join('<br>')}</td></tr>`).join('')}</tbody></table>`;
        out += pkKv([[t('pk_connected_streams'), pkStreamNames(view.connected_streams)]]);
    } else if (view.type === 'stream') {
        out += pkKv([[t('pk_match'), view.matching_type]]);
        out += `<table class="pk-table"><thead><tr><th>${t('pk_field')}</th><th>${t('pk_rule_type')}</th><th>${t('pk_value')}</th><th>${t('pk_inverted')}</th></tr></thead><tbody>${view.rules.map(r => `<tr><td>${esc(r.field)}</td><td>${esc(r.type)}</td><td class="pk-mono">${esc(r.value)}</td><td>${r.inverted ? esc(t('pk_yes')) : ''}</td></tr>`).join('')}</tbody></table>`;
    } else if (view.type === 'event_definition') {
        out += pkKv([[t('pk_query'), view.query], [t('pk_priority'), view.priority],
            [t('pk_series'), view.series], [t('pk_group_by'), view.group_by.join(', ')],
            [t('pk_search_within'), pkDuration(view.search_within_ms)],
            [t('pk_execute_every'), pkDuration(view.execute_every_ms)],
            [t('pk_connected_streams'), pkStreamNames(view.streams)],
            [t('pk_notifications'), view.notifications]]);
    } else if (view.type === 'dashboard') {
        out += `<p><a class="link-inline" data-act="pkPane" data-arg="dashboards">${t('pk_see_layout')}</a></p>`;
        out += `<ul>${view.tabs.map(tb => `<li>${esc(tb.title || t('pk_tab_untitled'))} (${esc(tb.widgets.length)})</li>`).join('')}</ul>`;
    }
    if (view.source) out += `<pre class="pk-code">${esc(view.source)}</pre>`;
    else if (view.type !== 'dashboard') out += `<details><summary>${t('pk_p_json')}</summary><pre class="pk-code">${esc(JSON.stringify(raw.data, null, 2))}</pre></details>`;
    return out;
}

function pkStreamNames(ids) {
    const names = {};
    (_pk.v.working || _pk.v.pack).entities.forEach(e => {
        if ((e.type || {}).name === 'stream') names[e.id] = pkEntityTitle(e);
    });
    return (ids || []).map(i => i === '000000000000000000000001' ? t('pk_default_stream') : (names[i] || i)).join(', ');
}

// ---- Editing ---------------------------------------------------------------

function pkStartEdit() {
    const v = _pk.v;
    if (!v) return;
    v.working = JSON.parse(JSON.stringify(v.pack));
    v.removed = new Set();
    v.jsonError = '';
    v.sel = null;
    if (v.pane === 'install') v.pane = 'overview';
    pkRenderViewer();
}

function pkCancelEdit() {
    const v = _pk.v;
    if (!v) return;
    v.working = null;
    v.removed = new Set();
    v.jsonError = '';
    pkJsonPost('/packs/view', {pack: v.pack}).then(d => {
        if (!d.error) v.data = d;
        pkRenderViewer();
    });
}

function pkEditMeta(el) { _pk.v.working[el.dataset.field] = el.value; if (el.dataset.field === 'name') pkRenderViewer(); }

/** Title edits keep the source in step: a rule's name lives in its own source and in every
 *  pipeline that runs it, and a mismatch installs a pipeline that cannot find its rule. */
function pkRename(e, oldName, newName) {
    if (!oldName || oldName === newName) return;
    const type = (e.type || {}).name;
    const swap = (d, word) => {
        const s = pkGet(d, 'source');
        if (typeof s === 'string') pkSet(d, 'source', s.split(`${word} "${oldName}"`).join(`${word} "${newName}"`));
    };
    if (type === 'pipeline') swap(e.data, 'pipeline');
    if (type === 'pipeline_rule') {
        swap(e.data, 'rule');
        _pk.v.working.entities.filter(x => (x.type || {}).name === 'pipeline').forEach(x => swap(x.data, 'rule'));
    }
}

function pkEditField(el) {
    const v = _pk.v;
    const e = v.working.entities[v.sel];
    let target = e.data;
    const path = el.dataset.path.split('.');
    path.slice(0, -1).forEach(p => { target = target[p]; });
    const key = path[path.length - 1];
    let value = el.value;
    if (el.dataset.num !== undefined) value = Number(value);
    if (key === 'title' && path.length === 1) pkRename(e, String(pkGet(target, key) || ''), value);
    pkSet(target, key, value);
    pkRenderViewer();
}

function pkEditStreamRule(el) {
    const v = _pk.v;
    const rule = v.working.entities[v.sel].data.stream_rules[Number(el.dataset.idx)];
    pkSet(rule, el.dataset.key, el.dataset.key === 'inverted' ? el.checked : el.value);
}

function pkEditEntityJson(el) {
    const v = _pk.v;
    try {
        v.working.entities[v.sel].data = JSON.parse(el.value);
        v.jsonError = '';
    } catch (err) {
        v.jsonError = String(err.message || err);
    }
    pkRenderViewer();
}

function pkEditPackJson(el) {
    const v = _pk.v;
    try {
        const p = JSON.parse(el.value);
        if (!p || !Array.isArray(p.entities)) throw new Error(t('pk_json_not_pack'));
        v.working = p;
        v.jsonError = '';
    } catch (err) {
        v.jsonError = String(err.message || err);
    }
    pkRenderViewer();
}

function pkInputRow(labelKey, path, value, opts) {
    const o = opts || {};
    const attrs = `class="pk-input${o.mono ? ' pk-mono' : ''}" data-act-change="pkEditField" data-act-self data-path="${esc(path)}"${o.num ? ' data-num="1"' : ''}`;
    const ctl = o.rows
        ? `<textarea rows="${o.rows}" spellcheck="false" ${attrs}>${esc(value)}</textarea>`
        : `<input type="${o.num ? 'number' : 'text'}" value="${esc(value)}" ${attrs}>`;
    return `<div class="form-group"><label>${t(labelKey)}</label>${ctl}</div>`;
}

function pkEntityEditor(e) {
    const v = _pk.v;
    const type = (e.type || {}).name;
    const d = e.data || {};
    let out = `<h4>${esc(pkEntityTitle(e))} <span class="pk-sub">${esc(pkTypeLabel(type))}</span></h4>`;
    if (v.removed.has(e.id)) out += pkFindingBox('warn', t('pk_will_remove'));
    if ('title' in d) out += pkInputRow('pk_m_name', 'title', pkGet(d, 'title') || '');
    if ('description' in d) out += pkInputRow('pk_m_description', 'description', pkGet(d, 'description') || '');
    if (type === 'dashboard' && 'summary' in d) out += pkInputRow('pk_m_summary', 'summary', pkGet(d, 'summary') || '');
    if (type === 'pipeline_rule' || type === 'pipeline') {
        out += pkInputRow('pk_source', 'source', pkGet(d, 'source') || '', {rows: 14, mono: true});
        out += `<div class="pk-inline"><button class="btn-sm btn-secondary" data-act="pkParse">${icon('check', 14)} ${esc(t('pk_parse').replace('{server}', _pk.server))}</button><span id="pk-parse-result"></span></div>`;
    }
    if (type === 'event_definition') {
        out += pkInputRow('pk_priority', 'priority', pkGet(d, 'priority') ?? '', {num: true});
        if (d.config) out += pkInputRow('pk_query', 'config.query', pkGet(d.config, 'query') || '', {mono: true, rows: 3});
    }
    if (type === 'stream') {
        out += `<table class="pk-table"><thead><tr><th>${t('pk_field')}</th><th>${t('pk_rule_type')}</th><th>${t('pk_value')}</th><th>${t('pk_inverted')}</th></tr></thead><tbody>${(d.stream_rules || []).map((r, i) => `<tr>
            <td><input type="text" class="pk-input" value="${esc(pkGet(r, 'field') || '')}" data-act-change="pkEditStreamRule" data-act-self data-idx="${i}" data-key="field"></td>
            <td><input type="text" class="pk-input" value="${esc(pkGet(r, 'type') || '')}" data-act-change="pkEditStreamRule" data-act-self data-idx="${i}" data-key="type"></td>
            <td><input type="text" class="pk-input pk-mono" value="${esc(pkGet(r, 'value') || '')}" data-act-change="pkEditStreamRule" data-act-self data-idx="${i}" data-key="value"></td>
            <td><input type="checkbox" ${pkGet(r, 'inverted') ? 'checked' : ''} data-act-change="pkEditStreamRule" data-act-self data-idx="${i}" data-key="inverted"></td></tr>`).join('')}</tbody></table>`;
    }
    out += `<details class="pk-raw"><summary>${t('pk_edit_json')}</summary>
        <textarea class="pk-input pk-mono" rows="14" spellcheck="false" data-act-change="pkEditEntityJson" data-act-self>${esc(JSON.stringify(d, null, 2))}</textarea></details>`;
    if (v.jsonError) out += pkFindingBox('block', t('pk_json_error').replace('{m}', v.jsonError));
    return out;
}

async function pkParse() {
    const v = _pk.v;
    const e = v.working.entities[v.sel];
    const out = document.getElementById('pk-parse-result');
    const d = await pkJsonPost('/packs/parse', {server: _pk.server, kind: e.type.name, source: pkGet(e.data, 'source')});
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    if (d.error) { out.innerHTML = `<span class="pk-err">${esc(d.error)}</span>`; return; }
    out.innerHTML = d.errors.length
        ? d.errors.map(x => `<div class="pk-err">${esc(x.line ? `L${x.line}: ` : '')}${esc(x.reason)}</div>`).join('')
        : `<span class="pk-ok">${esc(t('pk_parse_ok'))}</span>`;
}

function pkFinal() {
    const v = _pk.v;
    const p = JSON.parse(JSON.stringify(v.working));
    p.entities = p.entities.filter(e => !v.removed.has(e.id));
    return p;
}

async function pkReview() {
    const v = _pk.v;
    if (v.jsonError) { pkShowReview(`<div>${pkFindingBox('block', t('pk_json_error').replace('{m}', v.jsonError))}</div>`, false); return; }
    const d = await pkJsonPost('/packs/diff', {source: v.source, id: v.pack.id, rev: v.pack.rev, server: _pk.server, pack: pkFinal()});
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    if (d.error) { pkShowReview(`<div>${pkFindingBox('block', d.error)}</div>`, false); return; }
    const parts = [];
    if (d.meta.length) parts.push(`<h4>${t('pk_diff_meta')}</h4><table class="pk-kv">${d.meta.map(m => `<tr><th>${esc(t(m.field === 'vendor' ? 'pk_col_vendor' : 'pk_m_' + m.field))}</th><td class="pk-pre"><del>${esc(m.old || '')}</del><br><ins>${esc(m.new || '')}</ins></td></tr>`).join('')}</table>`);
    if (d.removed.length) parts.push(`<h4>${t('pk_diff_removed')}</h4><ul>${d.removed.map(x => `<li>${esc(pkTypeLabel(x.type))}: ${esc(x.title)}</li>`).join('')}</ul>`);
    if (d.added.length) parts.push(`<h4>${t('pk_diff_added')}</h4><ul>${d.added.map(x => `<li>${esc(pkTypeLabel(x.type))}: ${esc(x.title)}</li>`).join('')}</ul>`);
    d.changed.forEach(c => parts.push(`<h4>${esc(pkTypeLabel(c.type))}: ${esc(c.title)}</h4><pre class="pk-code pk-diff">${c.diff.map(l => `<span class="${l[0] === '+' ? 'pk-add' : l[0] === '-' ? 'pk-del' : l[0] === '@' ? 'pk-hunk' : ''}">${esc(l) || ' '}</span>`).join('')}</pre>${c.truncated ? `<div class="pk-sub">${esc(t('pk_diff_truncated'))}</div>` : ''}`));
    if (d.parameters_changed) parts.push(`<p>${esc(t('pk_diff_params'))}</p>`);
    const changed = parts.length > 0;
    if (!changed) parts.push(`<div class="u143">${esc(t('pk_diff_none'))}</div>`);
    const warn = pkRefWarnings(d.analysis);
    pkShowReview(`${parts.join('')}${warn}<p class="pk-sub">${esc(t(v.source === 'graylog' ? 'pk_save_note_graylog' : 'pk_save_note_library').replace('{rev}', v.pack.rev + 1).replace('{server}', _pk.server))}</p>`, changed);
}

function pkShowReview(html, canSave) {
    document.getElementById('pk-review-body').innerHTML = html;
    document.getElementById('pk-review-save').classList.toggle('hidden', !canSave);
    pkShow('pk-review', true);
}

function pkCloseReview() { pkShow('pk-review', false); }

async function pkSave() {
    const v = _pk.v;
    const body = {server: _pk.server, id: v.pack.id, base_rev: v.pack.rev, pack: pkFinal()};
    const r = await pkJsonPost(v.source === 'graylog' ? '/packs/graylog/save' : '/packs/library/save', body);
    if (r.need_signin) { pkOpenSignin(r.error); return; }
    if (r.error) { document.getElementById('pk-review-body').insertAdjacentHTML('beforeend', pkFindingBox('block', r.error)); return; }
    pkCloseReview();
    const source = v.source;
    await pkReload();
    await pkOpen(source, r.id, r.rev);
    pkMsg(t('pk_saved').replace('{rev}', r.rev));
}

// ---- Dashboard layout ------------------------------------------------------

/** Stable pseudo-random numbers per widget: redrawing never changes the picture. */
function pkRand(seed) {
    let h = 2166136261;
    String(seed).split('').forEach(c => { h = Math.imul(h ^ c.charCodeAt(0), 16777619); });
    return () => {
        h = Math.imul(h ^ (h >>> 15), 2246822507);
        h = Math.imul(h ^ (h >>> 13), 3266489909);
        h ^= h >>> 16;
        return (h >>> 0) / 4294967296;
    };
}

function pkWave(rnd, n) {
    let v = 0.3 + rnd() * 0.4;
    return Array.from({length: n}, () => {
        v = Math.min(0.95, Math.max(0.08, v + (rnd() - 0.5) * 0.38));
        return v;
    });
}

const PK_AXES = [10, 20, 30].map(y => `<line x1="0" x2="100" y1="${y}" y2="${y}" class="pk-gridline"/>`).join('');

function pkDrawBars(w, rnd) {
    const n = 22;
    const stacks = w.cols.length ? 3 : 1;
    const wave = pkWave(rnd, n);
    const bars = wave.map((v, i) => {
        let y = 40, out = '';
        for (let s = 0; s < stacks; s++) {
            const h = v * 36 * (stacks === 1 ? 1 : [0.5, 0.3, 0.2][s]);
            y -= h;
            out += `<rect x="${(i * 100 / n + 0.5).toFixed(2)}" y="${y.toFixed(2)}" width="${(100 / n - 1).toFixed(2)}" height="${h.toFixed(2)}" class="pk-f${s}"/>`;
        }
        return out;
    }).join('');
    return `<svg class="pk-chart" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">${PK_AXES}${bars}</svg>`;
}

function pkDrawLine(w, rnd, filled) {
    const lines = w.cols.length ? 3 : 1;
    let out = PK_AXES;
    for (let l = 0; l < lines; l++) {
        const pts = pkWave(rnd, 16).map((v, i) => [i * 100 / 15, 39 - v * 34 / (l + 1)]);
        const d = pts.map((p, i) => {
            if (!i) return `M${p[0].toFixed(2)} ${p[1].toFixed(2)}`;
            const q = pts[i - 1], mid = (q[0] + p[0]) / 2;
            return `C${mid.toFixed(2)} ${q[1].toFixed(2)} ${mid.toFixed(2)} ${p[1].toFixed(2)} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`;
        }).join('');
        if (filled) out += `<path d="${d}L100 40L0 40Z" class="pk-f${l} pk-soft"/>`;
        out += `<path d="${d}" class="pk-s${l}" fill="none" vector-effect="non-scaling-stroke"/>`;
    }
    return `<svg class="pk-chart" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">${out}</svg>`;
}

function pkDrawPie(w, rnd, ring) {
    const parts = Array.from({length: 5}, () => 0.25 + rnd());
    const sum = parts.reduce((a, b) => a + b, 0);
    const r = ring ? 15.9 : 8;
    const c = 2 * Math.PI * r;
    let off = 0;
    const arcs = parts.map((p, i) => {
        const len = p / sum * c;
        const el = `<circle cx="20" cy="20" r="${r}" fill="none" class="pk-s${i} pk-arc${ring ? '' : ' pk-arc-solid'}" stroke-dasharray="${len.toFixed(2)} ${(c - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}"/>`;
        off += len;
        return el;
    }).join('');
    const legend = parts.map((p, i) => `<div class="pk-legend-row"><i class="pk-b${i}"></i><span class="pk-ghost" data-w="${Math.round(35 + rnd() * 55)}"></span></div>`).join('');
    return `<div class="pk-pie"><svg viewBox="0 0 40 40" aria-hidden="true"><g transform="rotate(-90 20 20)">${arcs}</g></svg><div class="pk-legend">${legend}</div></div>`;
}

function pkDrawTable(w, rnd, headers) {
    const heads = (headers.length ? headers : ['']).slice(0, 7);
    const lastNumeric = w.type !== 'messages';
    const rows = Math.max(2, Math.min(9, Number.isInteger(w.height) ? Math.floor(w.height * 1.05) : 4));
    const cell = (j) => `<td class="${lastNumeric && j === heads.length - 1 && heads.length > 1 ? 'pk-td-num' : ''}"><span class="pk-ghost" data-w="${Math.round(lastNumeric && j === heads.length - 1 && heads.length > 1 ? 30 + rnd() * 30 : 40 + rnd() * 55)}"></span></td>`;
    return `<div class="pk-mini-wrap"><table class="pk-mini"><thead><tr>${heads.map(h => `<th title="${esc(h)}">${esc(h)}</th>`).join('')}</tr></thead>
        <tbody>${Array.from({length: rows}, () => `<tr>${heads.map((h, j) => cell(j)).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function pkDrawHeat(w, rnd) {
    const cols = 12, rows = 6;
    let out = '';
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            out += `<rect x="${(x * 100 / cols + 0.3).toFixed(2)}" y="${(y * 40 / rows + 0.3).toFixed(2)}" width="${(100 / cols - 0.6).toFixed(2)}" height="${(40 / rows - 0.6).toFixed(2)}" class="pk-h${Math.floor(rnd() * 5)}"/>`;
        }
    }
    return `<svg class="pk-chart" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">${out}</svg>`;
}

function pkDrawMap(w, rnd) {
    const lines = [20, 40, 60, 80].map(x => `<line x1="${x}" x2="${x}" y1="0" y2="50" class="pk-gridline"/>`).join('') +
        [12.5, 25, 37.5].map(y => `<line x1="0" x2="100" y1="${y}" y2="${y}" class="pk-gridline"/>`).join('');
    const dots = Array.from({length: 11}, () => {
        const r = 0.8 + rnd() * 2.8;
        return `<circle cx="${(8 + rnd() * 84).toFixed(1)}" cy="${(8 + rnd() * 32).toFixed(1)}" r="${r.toFixed(1)}" class="pk-f0 pk-dot"/>`;
    }).join('');
    return `<svg class="pk-chart" viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${lines}${dots}</svg>`;
}

function pkDrawNumber(w, rnd) {
    const n = Math.floor(rnd() * 90000) + 100;
    return `<div class="pk-number">${n.toLocaleString()}</div>`;
}

/** The picture is invented; column names, metrics and layout are the pack's own. */
function pkDrawWidget(w) {
    const rnd = pkRand(w.id || w.title);
    const headers = w.type === 'messages' ? (w.fields || []) : [...w.rows, ...w.cols, ...w.series];
    switch (w.viz) {
        case 'numeric': return pkDrawNumber(w, rnd);
        case 'bar': return pkDrawBars(w, rnd);
        case 'line': return pkDrawLine(w, rnd, false);
        case 'area': return pkDrawLine(w, rnd, true);
        case 'pie': return pkDrawPie(w, rnd, false);
        case 'donut': return pkDrawPie(w, rnd, true);
        case 'heatmap': return pkDrawHeat(w, rnd);
        case 'map':
        case 'worldmap': return pkDrawMap(w, rnd);
        default: return pkDrawTable(w, rnd, headers);
    }
}

function pkVizLabel(viz) {
    const k = 'pk_viz_' + viz;
    const s = t(k);
    return s === k ? (viz || '') : s;
}

function pkWidgetCaption(w) {
    if (w.type === 'messages' || w.viz === 'table' || !w.viz) return '';
    return [...w.series, ...w.rows.filter(f => f !== 'timestamp'), ...w.cols].join(' · ');
}

function pkDashboards() {
    return (_pk.v.data.entities || []).filter(e => e.type === 'dashboard');
}

function pkPaneDashboards() {
    const v = _pk.v;
    const dashes = pkDashboards();
    if (!dashes.length) return `<div class="u143">${esc(t('pk_no_dashboards'))}</div>`;
    const dIdx = Math.min(v.dash || 0, dashes.length - 1);
    const d = dashes[dIdx];
    const tIdx = Math.min(v.tab || 0, d.tabs.length - 1);
    const tb = d.tabs[tIdx];
    const pickDash = dashes.length > 1 ? `<div class="pk-inline">${dashes.map((x, i) => `<button class="btn-sm ${i === dIdx ? 'btn-primary' : 'btn-secondary'}" data-act="pkPickDash" data-args="[${i}]">${esc(x.title)}</button>`).join('')}</div>` : '';
    const tabs = `<div class="pk-dash-tabs">${d.tabs.map((x, i) => `<button class="pk-dash-tab${i === tIdx ? ' active' : ''}" data-act="pkPickTab" data-args="[${i}]">${esc(x.title || t('pk_tab_untitled'))}<span class="pk-dash-n">${esc(x.widgets.length)}</span></button>`).join('')}</div>`;
    const grid = tb ? `<div class="pk-canvas"><div class="pk-grid" id="pk-grid">${tb.widgets.map((w, i) => {
        const cap = pkWidgetCaption(w);
        const tip = [pkVizLabel(w.viz), w.query].filter(Boolean).join('\n');
        return `<div class="pk-widget pk-v-${esc(w.viz || 'table')}" data-i="${i}" title="${esc(tip)}">
        <div class="pk-widget-title">${esc(w.title || t('pk_widget_untitled'))}</div>
        <div class="pk-widget-body">${pkDrawWidget(w)}</div>
        ${cap ? `<div class="pk-widget-cap">${esc(cap)}</div>` : ''}</div>`;
    }).join('')}</div></div>` : '';
    return `<p class="pk-sub">${esc(t('pk_layout_note'))}</p>${pickDash}${tabs}${tb && tb.query ? `<div class="pk-page-query">${esc(tb.query)}</div>` : ''}${grid}`;
}

/** Positions are data, so they are set through the DOM: the CSP forbids style attributes. */
function pkApplyGrid() {
    const host = document.getElementById('pk-grid');
    if (!host) return;
    const dashes = pkDashboards();
    const d = dashes[Math.min(_pk.v.dash || 0, dashes.length - 1)];
    const tb = d.tabs[Math.min(_pk.v.tab || 0, d.tabs.length - 1)];
    host.querySelectorAll('.pk-widget').forEach(el => {
        const w = tb.widgets[Number(el.dataset.i)];
        const num = (x, dflt) => (Number.isInteger(x) && x > 0 ? x : dflt);
        const col = Math.min(num(w.col, 1), 12);
        const width = Math.min(num(w.width, 12), 13 - col);
        el.style.gridColumn = `${col} / span ${width}`;
        el.style.gridRow = `${num(w.row, 1)} / span ${num(w.height, 3)}`;
    });
    host.querySelectorAll('.pk-ghost').forEach(el => { el.style.width = `${el.dataset.w}%`; });
}

function pkPickDash(i) { _pk.v.dash = i; _pk.v.tab = 0; pkRenderViewer(); }
function pkPickTab(i) { _pk.v.tab = i; pkRenderViewer(); }

// ---- JSON ------------------------------------------------------------------

function pkPaneJson() {
    const v = _pk.v;
    if (v.working) {
        return `${v.jsonError ? pkFindingBox('block', t('pk_json_error').replace('{m}', v.jsonError)) : ''}
            <textarea class="pk-input pk-mono pk-json" spellcheck="false" data-act-change="pkEditPackJson" data-act-self>${esc(JSON.stringify(v.working, null, 2))}</textarea>`;
    }
    return `<pre class="pk-code pk-json">${esc(JSON.stringify(v.pack, null, 2))}</pre>`;
}

// ---- Install ---------------------------------------------------------------

async function pkRunCheck() {
    const v = _pk.v;
    if (!v) return;
    const body = v.source === 'upload' ? {server: _pk.server, pack: v.pack}
        : {server: _pk.server, source: v.source, id: v.pack.id, rev: v.pack.rev};
    v.check = {loading: true};
    v.result = null;
    if (v.pane === 'install') pkRenderViewer();
    const d = await pkJsonPost('/packs/check', body);
    if (d.need_signin) {
        v.check = null;
        pkOpenSignin(d.error, () => pkRunCheck());
        pkRenderViewer();
        return;
    }
    v.check = d;
    if (_pk.v === v && v.pane === 'install') pkRenderViewer();
}

function pkFindingText(f) {
    const key = 'pk_f_' + f.code;
    const s = t(key);
    return s === key ? f.code : s;
}

function pkPaneInstall() {
    const v = _pk.v;
    const c = v.check;
    if (v.source === 'upload') {
        if (!c) return '';
    }
    if (v.result) return pkInstallResult();
    if (!c || c.loading) return `<div class="u143">${esc(t('loading'))}</div>`;
    if (c.error) return `<div class="u141">${esc(c.error)}</div>`;
    const blocked = (c.findings || []).some(f => f.level === 'block');
    const findings = (c.findings || []).map(f => {
        const items = f.code === 'not_checked' ? f.items.map(pkTypeLabelForCheck) : f.items;
        return pkFindingBox(f.level, pkFindingText(f), items);
    }).join('') || pkFindingBox('info', t('pk_no_findings'));
    const params = (v.pack.parameters || []).map(p => `<div class="form-group"><label>${esc(p.title || p.name)}</label>
        <input type="text" class="pk-input" data-param="${esc(p.name)}" data-ptype="${esc(p.type || '')}" value="${esc(p.default_value ?? '')}">
        <div class="pk-sub">${esc(p.description || '')}</div></div>`).join('');
    const installedHere = (c.installed_revs || []).length
        ? pkFindingBox('warn', t('pk_already_installed').replace('{rev}', c.installed_revs.join(', '))) : '';
    const sensHere = (c.sensitive || []).length
        ? pkFindingBox('block', t('pk_s_intro').replace('{n}', c.sensitive.length)) + pkSensitiveBox(c.sensitive) : '';
    return `<p>${esc(t('pk_check_intro').replace('{server}', _pk.server).replace('{version}', c.version || '?'))}</p>
        ${sensHere}${installedHere}${findings}${params}
        ${v.source === 'upload' ? `<p class="pk-sub">${esc(t('pk_upload_first'))}</p>` : `
        <div class="form-group"><label>${t('pk_comment')}</label><input type="text" class="pk-input" id="pk-install-comment"></div>
        <div class="pk-inline"><button class="btn-primary" data-act="pkDoInstall" ${blocked ? 'disabled' : ''}>${icon('play')} ${esc(t('pk_install_on').replace('{server}', _pk.server))}</button>
        <button class="btn-secondary" data-act="pkRunCheck">${icon('refresh', 14)} ${t('pk_recheck')}</button></div>
        ${blocked ? `<p class="pk-err">${esc(t('pk_blocked_note'))}</p>` : ''}
        <div id="pk-install-error"></div>`}`;
}

function pkTypeLabelForCheck(k) {
    return {rules: t('pk_t_pipeline_rule'), pipelines: t('pk_t_pipeline'), stream_titles: t('pk_t_stream'),
        dashboards: t('pk_t_dashboard'), events: t('pk_t_event_definition'), lookup_tables: t('pk_t_lookup_table')}[k] || k;
}

function pkParamValues() {
    const out = {};
    document.querySelectorAll('#pk-v-body [data-param]').forEach(el => {
        const type = el.dataset.ptype;
        const value = /integer|long|double|float/i.test(type) ? Number(el.value)
            : /boolean/i.test(type) ? /^(true|1|yes)$/i.test(el.value) : el.value;
        out[el.dataset.param] = {'@type': (type || 'string').toLowerCase(), '@value': value};
    });
    return out;
}

async function pkDoInstall(choice) {
    const v = _pk.v;
    const sens = typeof choice === 'string' ? choice : undefined;
    const comment = (document.getElementById('pk-install-comment') || {}).value || '';
    const r = await pkJsonPost('/packs/install', {server: _pk.server, source: v.source, id: v.pack.id,
        rev: v.pack.rev, parameters: pkParamValues(), comment, sensitive: sens});
    if (r.need_signin) { pkOpenSignin(r.error); return; }
    if (r.need_decision) {
        pkOpenLeave(t('pk_install_on').replace('{server}', _pk.server), r.sensitive, false, c => pkDoInstall(c));
        return;
    }
    if (r.error) {
        if (r.findings) v.check = {...v.check, findings: r.findings};
        pkRenderViewer();
        const out = document.getElementById('pk-install-error');
        if (out) out.innerHTML = pkFindingBox('block', r.error);
        return;
    }
    v.result = r;
    await pkReload();
    pkRenderViewer();
}

function pkInstallResult() {
    const r = _pk.v.result;
    const streams = r.paused_streams || [];
    return `${pkFindingBox('info', t('pk_install_done').replace('{n}', r.entity_count).replace('{server}', _pk.server))}
        ${streams.length ? `${pkFindingBox('warn', t('pk_streams_paused'), streams.map(s => s.title))}
        <div class="pk-inline"><button class="btn-primary" data-act="pkStartStreams">${icon('play')} ${t('pk_start_streams')}</button><span id="pk-start-result"></span></div>` : ''}`;
}

async function pkStartStreams() {
    const r = _pk.v.result;
    const out = document.getElementById('pk-start-result');
    const d = await pkJsonPost('/packs/start-streams', {server: _pk.server, stream_ids: r.paused_streams.map(s => s.id)});
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    out.innerHTML = d.error ? `<span class="pk-err">${esc(d.error)}</span>`
        : `<span class="pk-ok">${esc(t('pk_streams_started').replace('{n}', d.started))}</span>`;
}

// ---- Uninstall -------------------------------------------------------------

async function pkUninstallStart(id) {
    const d = await fetchJSON(`${API}/packs/graylog/${encodeURIComponent(id)}/detail?server=${encodeURIComponent(_pk.server)}`);
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    if (d.error) { pkMsg(d.error, 'err'); return; }
    if (!d.installations.length) { pkMsg(t('pk_not_installed')); pkReload(); return; }
    pkUninstallOne(id, d.installations[0].id);
}

async function pkUninstallOne(id, installationId) {
    const d = await pkJsonPost('/packs/uninstall-preview', {server: _pk.server, id, installation_id: installationId});
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    if (d.error) { pkMsg(d.error, 'err'); return; }
    _pk.pendingUninstall = {id, installationId};
    const removed = d.entities.filter(e => !e.found_on_system);
    const kept = d.entities.filter(e => e.found_on_system);
    const row = e => `${pkTypeLabel(e.type)}: ${e.title}`;
    document.getElementById('pk-uninstall-title').textContent = t('pk_uninstall_title').replace('{server}', _pk.server);
    document.getElementById('pk-uninstall-body').innerHTML =
        pkFindingBox('block', t('pk_uninstall_removes').replace('{n}', removed.length), removed.map(row)) +
        (kept.length ? pkFindingBox('info', t('pk_uninstall_keeps'), kept.map(row)) : '');
    pkShow('pk-uninstall', true);
}

function pkCloseUninstall() { pkShow('pk-uninstall', false); _pk.pendingUninstall = null; }

async function pkDoUninstall() {
    const u = _pk.pendingUninstall;
    if (!u) return;
    const r = await pkJsonPost('/packs/uninstall', {server: _pk.server, id: u.id, installation_id: u.installationId});
    if (r.need_signin) { pkOpenSignin(r.error); return; }
    if (r.error) { document.getElementById('pk-uninstall-body').insertAdjacentHTML('beforeend', pkFindingBox('block', r.error)); return; }
    pkCloseUninstall();
    if (_pk.v) pkCloseViewer();
    await pkReload();
    pkMsg(r.failed ? t('pk_uninstall_partial').replace('{n}', r.failed) : t('pk_uninstall_done'), r.failed ? 'err' : 'ok');
}

// ---- Download / upload / delete --------------------------------------------

/** Everything leaving this site passes here: a download, an upload to a Graylog, an install
 *  from the library. Whoever holds the pack next may be a customer. */
function pkSensitiveBox(found) {
    const by = {};
    found.forEach(f => { (by[f.kind] = by[f.kind] || []).push(`${pkTypeLabel(f.entity_type)}: ${f.entity} › ${f.where} = ${f.value}`); });
    return Object.entries(by).map(([k, items]) => pkFindingBox('block', t('pk_s_kind_' + k), items)).join('');
}

function pkOpenLeave(titleText, found, withVersion, onChoice) {
    document.getElementById('pk-leave-title').textContent = titleText;
    document.getElementById('pk-leave-version-wrap').classList.toggle('hidden', !withVersion);
    const body = document.getElementById('pk-leave-body');
    body.innerHTML = (found.length
        ? `${pkFindingBox('block', t('pk_s_intro').replace('{n}', found.length))}${pkSensitiveBox(found)}`
        : `<p class="pk-ok">${esc(t('pk_s_clean'))}</p>`) +
        (withVersion ? `<p class="pk-hint">${esc(t('pk_download_bundle'))}</p>` : '');
    _pk.leaveChoice = onChoice;
    const go = (act, key, cls, ic) => `<button class="${cls}" data-act="pkLeaveGo" data-arg="${act}">${icon(ic)} ${esc(t(key))}</button>`;
    document.getElementById('pk-leave-buttons').innerHTML = found.length
        ? go('strip', 'pk_s_strip', 'btn-primary', 'shield') + go('keep', 'pk_s_keep', 'btn-danger', 'warning') +
          `<button class="btn-secondary" data-act="pkCloseLeave">${icon('close')} ${t('btn_cancel')}</button>`
        : go('', 'pk_s_continue', 'btn-primary', 'check') +
          `<button class="btn-secondary" data-act="pkCloseLeave">${icon('close')} ${t('btn_cancel')}</button>`;
    document.querySelectorAll('.pk-modal-x').forEach(b => { if (!b.firstChild) b.innerHTML = icon('close', 16); });
    pkShow('pk-leave', true);
}

function pkCloseLeave() { pkShow('pk-leave', false); _pk.leaveChoice = null; }

function pkLeaveGo(choice) {
    const fn = _pk.leaveChoice;
    const version = document.getElementById('pk-leave-version').value;
    pkCloseLeave();
    if (fn) fn(choice, version);
}

async function pkDownload(source, id, rev) {
    const d = await pkJsonPost('/packs/sensitive', {source, id, rev, server: _pk.server});
    if (d.need_signin) { pkOpenSignin(d.error); return; }
    if (d.error) { pkMsg(d.error, 'err'); return; }
    if (!_pk.versions) {
        const v = await fetchJSON(`${API}/packs/target-versions`);
        _pk.versions = v.versions || [];
        document.getElementById('pk-leave-version').innerHTML =
            `<option value="">${esc(t('pk_target_asis'))}</option>` +
            _pk.versions.map(x => `<option value="${esc(x)}">Graylog ${esc(x)}</option>`).join('');
    }
    pkOpenLeave(t('pk_download'), d.sensitive || [], true, (choice, version) => pkFetchDownload(source, id, rev, choice, version));
}

async function pkFetchDownload(source, id, rev, sensitive, target_version) {
    const resp = await fetch(`${API}/packs/download`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({source, id, rev, server: _pk.server, sensitive, target_version, lang: getLang()})});
    if (!resp.ok) {
        let d = {};
        try { d = await resp.json(); } catch (e) { d = {error: `HTTP ${resp.status}`}; }
        if (d.need_signin) { pkOpenSignin(d.error); return; }
        pkMsg(typeof trSrv === 'function' ? trSrv(d.error || '') : d.error, 'err');
        return;
    }
    const m = /filename\*=UTF-8''([^;]+)/.exec(resp.headers.get('content-disposition') || '');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await resp.blob());
    a.download = m ? decodeURIComponent(m[1]) : `pack-r${rev}.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}

function pkUploadPick() {
    const el = document.getElementById('pk-upload-file');
    if (el) { el.value = ''; el.click(); }
}

async function pkFilePicked(el) {
    const file = el.files && el.files[0];
    if (!file) return;
    pkMsg('');
    if (/\.zip$/i.test(file.name)) {
        pkMsg(t('pk_zip_unpack_first'), 'err');
        return;
    }
    let pack;
    try {
        pack = JSON.parse(await file.text());
    } catch (e) {
        pkMsg(t('pk_json_error').replace('{m}', String(e.message || e)), 'err');
        return;
    }
    const d = await pkJsonPost('/packs/view', {pack});
    if (d.error) { pkMsg(d.error, 'err'); return; }
    await pkShowViewer('upload', d);
}

async function pkConfirmUpload(choice) {
    const v = _pk.v;
    const lib = _pk.tab === 'library';
    const r = await pkJsonPost(lib ? '/packs/library/upload' : '/packs/graylog/upload', {server: _pk.server, pack: v.pack, sensitive: choice});
    if (r.need_decision) {
        pkOpenLeave(t('pk_upload_to').replace('{server}', _pk.server), r.sensitive, false, c => pkConfirmUpload(c));
        return;
    }
    if (r.need_signin) { pkOpenSignin(r.error, () => pkConfirmUpload(choice)); return; }
    if (r.error) { pkShowReview(pkFindingBox('block', r.error), false); return; }
    await pkReload();
    await pkOpen(lib ? 'library' : 'graylog', r.id, r.rev);
    pkMsg(t('pk_uploaded'));
}

async function pkCopyToLibrary() {
    const v = _pk.v;
    const r = await pkJsonPost('/packs/library/from-graylog', {server: _pk.server, id: v.pack.id, rev: v.pack.rev});
    if (r.need_signin) { pkOpenSignin(r.error); return; }
    if (r.error) { pkShowReview(pkFindingBox('block', r.error), false); return; }
    await pkLoadLibrary();
    pkShowReview(pkFindingBox('info', t('pk_copied')), false);
}

async function pkUploadFromLibrary(choice) {
    const v = _pk.v;
    const r = await pkJsonPost('/packs/graylog/upload', {server: _pk.server, pack: v.pack, sensitive: choice});
    if (r.need_signin) { pkOpenSignin(r.error, () => pkUploadFromLibrary(choice)); return; }
    if (r.need_decision) {
        pkOpenLeave(t('pk_upload_to').replace('{server}', _pk.server), r.sensitive, false, c => pkUploadFromLibrary(c));
        return;
    }
    pkShowReview(pkFindingBox(r.error ? 'block' : 'info', r.error || t('pk_uploaded')), false);
    if (!r.error) { await pkLoadGraylog(); pkRender(); }
}

function pkDeleteGraylog(id, name) {
    showConfirm(t('btn_delete'), t('pk_delete_confirm').replace('{name}', name).replace('{server}', _pk.server), async () => {
        const r = await pkJsonPost('/packs/graylog/delete', {server: _pk.server, id});
        if (r.need_signin) { pkOpenSignin(r.error); return; }
        pkMsg(r.error || t('pk_deleted'), r.error ? 'err' : 'ok');
        await pkLoadGraylog();
        pkRender();
    });
}

function pkDeleteRevision() {
    const v = _pk.v;
    const {id, rev, name} = v.pack;
    showConfirm(t('btn_delete'), t('pk_delete_rev_confirm').replace('{name}', name).replace('{rev}', rev).replace('{server}', _pk.server), async () => {
        const r = await pkJsonPost('/packs/graylog/delete', {server: _pk.server, id, rev});
        if (r.need_signin) { pkOpenSignin(r.error); return; }
        if (r.error) { pkShowReview(pkFindingBox('block', r.error), false); return; }
        const left = v.detail.revisions.filter(x => x !== rev);
        await pkReload();
        await pkOpen('graylog', id, left[left.length - 1]);
        pkMsg(t('pk_deleted'));
    });
}

function pkDeleteLibrary(id, rev) {
    const p = _pk.lib.find(x => x.id === id) || {};
    showConfirm(t('btn_delete'), t('pk_delete_library_confirm').replace('{name}', p.name || id).replace('{rev}', rev), async () => {
        const r = await pkJsonPost('/packs/library/delete', {id, rev});
        pkMsg(r.error || t('pk_deleted'), r.error ? 'err' : 'ok');
        await pkLoadLibrary();
        pkRender();
    });
}

document.addEventListener('DOMContentLoaded', pkInit);

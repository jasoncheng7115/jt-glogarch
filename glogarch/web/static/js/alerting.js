/* jt-glogarch — Alerting page: Graylog event definitions + notifications in bulk.
 *
 * All definitions are loaded once (a site has hundreds, not millions), so the
 * filters run in the browser and stay instant. Writes never trust this copy:
 * Preview asks the server, which re-reads Graylog and keeps the plan; Apply
 * runs that plan as a job, and every definition is re-read again right before
 * it is written (see glogarch/graylog/alerting.py). */

const _al = {
    server: '', data: null, notifById: {}, selected: new Set(), page: 1, perPage: 50,
    preset: '', tags: new Set(), q: '', lastIdx: null, tab: 'defs', planId: null,
    jobId: null, jobTimer: null, tagsExpanded: false, servers: [], loginUser: '',
    pendingAction: null,
};

const _AL_STALE_DAYS = 90;

// ---- Query language -------------------------------------------------------

/** "a -b notif:Zulip tag:"Apache (Linux)"" → [{neg, field, value}]. Quotes keep
 *  spaces; a leading "-" negates; field:value narrows to one attribute. */
function alParseQuery(q) {
    const terms = [];
    const s = String(q || '');
    let i = 0;
    while (i < s.length) {
        while (i < s.length && /\s/.test(s[i])) i++;
        if (i >= s.length) break;
        let neg = false;
        if (s[i] === '-' && i + 1 < s.length && !/\s/.test(s[i + 1])) { neg = true; i++; }
        let field = '';
        const m = /^([a-z]+):/i.exec(s.slice(i));
        if (m && ['notif', 'tag', 'prio', 'state'].includes(m[1].toLowerCase())) {
            field = m[1].toLowerCase(); i += m[0].length;
        }
        let value = '';
        if (s[i] === '"') {
            const end = s.indexOf('"', i + 1);
            value = end === -1 ? s.slice(i + 1) : s.slice(i + 1, end);
            i = end === -1 ? s.length : end + 1;
        } else {
            const start = i;
            while (i < s.length && !/\s/.test(s[i])) i++;
            value = s.slice(start, i);
        }
        value = value.trim().toLowerCase();
        if (value) terms.push({neg, field, value});
    }
    return terms;
}

function _alTermHit(d, term, notifById) {
    const v = term.value;
    switch (term.field) {
        case 'notif':
            if (v === 'none') return d.notifications.length === 0;
            return d.notifications.some(id => id === v ||
                String((notifById[id] || {}).title || '').toLowerCase().includes(v));
        case 'tag':
            return (d.tags || []).some(tg => tg.toLowerCase().includes(v));
        case 'prio':
            return String(d.priority) === v;
        case 'state':
            if (['enabled', 'on', 'enable'].includes(v)) return d.state === 'ENABLED';
            if (['disabled', 'off', 'disable'].includes(v)) return d.state !== 'ENABLED';
            return false;
        default:
            return (d.title + '\n' + d.description + '\n' + d.query).toLowerCase().includes(v);
    }
}

/** Every term must hold (AND); a negated term must not. */
function alMatchQuery(d, terms, notifById) {
    return terms.every(term => _alTermHit(d, term, notifById) !== term.neg);
}

function _alDaysSince(iso) {
    if (!iso) return Infinity;
    const ms = Date.parse(iso);
    return isNaN(ms) ? Infinity : (Date.now() - ms) / 86400000;
}

/** Quick filters. `test` decides membership; order is the chip order. */
const AL_PRESETS = [
    {key: 'enabled_no_notif', label: 'al_p_enabled_no_notif',
     test: (d) => d.state === 'ENABLED' && d.notifications.length === 0},
    {key: 'no_notif', label: 'al_p_no_notif', test: (d) => d.notifications.length === 0},
    {key: 'dangling', label: 'al_p_dangling',
     test: (d, nb) => d.notifications.some(id => !nb[id])},
    {key: 'enabled', label: 'al_p_enabled', test: (d) => d.state === 'ENABLED'},
    {key: 'disabled', label: 'al_p_disabled', test: (d) => d.state !== 'ENABLED'},
    {key: 'never_matched', label: 'al_p_never', test: (d) => !d.matched_at},
    {key: 'stale', label: 'al_p_stale',
     test: (d) => !!d.matched_at && _alDaysSince(d.matched_at) > _AL_STALE_DAYS},
    {key: 'high', label: 'al_p_high', test: (d) => d.priority === 3},
];

function _alPreset(key) { return AL_PRESETS.find(p => p.key === key); }

/** The definitions the current filters show, in title order. */
function alFiltered() {
    const defs = (_al.data && _al.data.definitions) || [];
    const terms = alParseQuery(_al.q);
    const pre = _alPreset(_al.preset);
    const tags = [..._al.tags].map(x => x.toLowerCase());
    return defs.filter(d =>
        // Graylog's own system definition is not a finding of any quick filter.
        (!pre || (!d.system && pre.test(d, _al.notifById))) &&
        (!tags.length || (d.tags || []).some(tg => tags.includes(tg.toLowerCase()))) &&
        alMatchQuery(d, terms, _al.notifById)
    ).sort((a, b) => a.title.localeCompare(b.title));
}

/** Shift-click: the ids between the last clicked row and this one. */
function alRangeIds(list, fromIdx, toIdx) {
    const a = Math.max(0, Math.min(fromIdx, toIdx)), b = Math.min(list.length - 1, Math.max(fromIdx, toIdx));
    return list.slice(a, b + 1).map(d => d.id);
}

// ---- Loading --------------------------------------------------------------

async function alInit() {
    const sp = new URLSearchParams(location.search);
    _al.q = sp.get('q') || '';
    _al.preset = sp.get('preset') || '';
    (sp.get('tags') || '').split('|').filter(Boolean).forEach(tg => _al.tags.add(tg));
    const qEl = document.getElementById('al-q');
    if (qEl) qEl.value = _al.q;
    const tab = sp.get('tab');
    if (tab) alTab(tab);
    const r = await fetchJSON(`${API}/alerting/servers`);
    _al.servers = r.items || [];
    _al.loginUser = r.login_user || '';
    _al.server = sp.get('server') || r.default || (_al.servers[0] || {}).name || '';
    const sel = document.getElementById('al-server');
    if (sel) {
        sel.innerHTML = _al.servers.map(s =>
            `<option value="${esc(s.name)}" ${s.name === _al.server ? 'selected' : ''}>${esc(s.name)}</option>`).join('');
        initCustomSelects();
    }
    if (!_al.servers.length) {
        document.getElementById('al-who').textContent = t('al_no_server');
        return;
    }
    await alLoad();
}

function alServerChange(v) {
    _al.server = v;
    _al.selected.clear();
    _al.page = 1;
    alSyncUrl();
    alLoad();
}

function alReload() { return alLoad(); }

let _alLoadTimer = null;

/** Loading: say so everywhere the data will appear, and lock the buttons that
 *  act on it. Hundreds of definitions take seconds to read from Graylog; a page
 *  that looks ready but is empty reads as broken. */
function alSetLoading(on) {
    clearInterval(_alLoadTimer); _alLoadTimer = null;
    document.querySelectorAll('#al-batch button, #al-reload').forEach(b => { b.disabled = on; });
    if (!on) return;
    const started = Date.now();
    const msg = () => {
        const sec = Math.floor((Date.now() - started) / 1000);
        return t('al_loading_from').replace('{server}', esc(_al.server)) +
            (sec >= 2 ? ` <span class="al-loading-sec">${t('al_loading_sec').replace('{n}', sec)}</span>` : '');
    };
    const who = document.getElementById('al-who');
    if (who) { who.className = 'al-who'; who.innerHTML = `<span class="spinner-text">${msg()}</span>`; }
    const f = document.getElementById('al-fetched'); if (f) f.textContent = '';
    const row = (cols, sub) => `<tr><td class="al-loading" colspan="${cols}"><span class="spinner-text">${t('al_loading_defs')}</span>${sub ? `<span class="al-loading-sub">${t('al_loading_hint')}</span>` : ''}</td></tr>`;
    const defs = document.querySelector('#al-defs-table tbody'); if (defs) defs.innerHTML = row(6, true);
    const ns = document.querySelector('#al-notifs-table tbody'); if (ns) ns.innerHTML = row(5, false);
    const h = document.getElementById('al-health'); if (h) h.innerHTML = `<div class="al-loading-block"><span class="spinner-text">${t('al_loading_defs')}</span></div>`;
    ['al-presets', 'al-tags'].forEach(id => { const el = document.getElementById(id); if (el) el.innerHTML = `<span class="spinner-text al-chip-loading">${t('loading')}</span>`; });
    const sel = document.getElementById('al-sel-count'); if (sel) sel.textContent = '';
    _alLoadTimer = setInterval(() => {
        const s2 = who && who.querySelector('.spinner-text');
        if (s2) s2.innerHTML = msg(); else { clearInterval(_alLoadTimer); _alLoadTimer = null; }
    }, 1000);
}

async function alLoad() {
    const tbody = document.querySelector('#al-defs-table tbody');
    alSetLoading(true);
    let d;
    try {
        d = await fetchJSON(`${API}/alerting/data?server=${encodeURIComponent(_al.server)}`);
    } finally {
        alSetLoading(false);
    }
    if (d.need_signin) {
        _al.data = null;
        alRenderWho(d.error);
        if (tbody) tbody.innerHTML = `<tr><td class="u143" colspan="6">${esc(t('al_need_signin'))}</td></tr>`;
        alOpenSignin(d.error);
        return;
    }
    if (d.error) {
        _al.data = null;
        alRenderWho();
        if (tbody) tbody.innerHTML = `<tr><td class="u141" colspan="6">${esc(d.error)}</td></tr>`;
        return;
    }
    _al.data = d;
    _al.notifById = {};
    (d.notifications || []).forEach(n => { _al.notifById[n.id] = n; });
    // Drop selections that no longer exist in Graylog.
    const ids = new Set((d.definitions || []).map(x => x.id));
    [..._al.selected].forEach(id => { if (!ids.has(id)) _al.selected.delete(id); });
    alRenderAll();
}

function alRenderAll() {
    alRenderWho();
    alRenderChips();
    alRenderDefs();
    alRenderNotifs();
    alRenderHealth();
    if (_al.tab === 'changes') alLoadChanges();
}

function alRenderWho(err) {
    const el = document.getElementById('al-who');
    if (!el) return;
    const d = _al.data;
    if (!d) {
        el.className = 'al-who al-warn';
        el.innerHTML = `${esc(err || t('al_need_signin'))} <button class="btn-sm btn-primary" data-act="alOpenSignin">${icon('login', 14)} ${t('al_signin_btn')}</button>`;
        return;
    }
    el.className = 'al-who';
    el.innerHTML = t('al_acting_as').replace('{user}', `<strong>${esc(d.graylog_user || '?')}</strong>`) +
        (d.running_job ? ` · <span class="al-warn">${t('al_job_running')}</span>` : '');
    const f = document.getElementById('al-fetched');
    if (f) f.textContent = t('al_fetched').replace('{n}', formatNumber(d.definitions.length))
        .replace('{m}', formatNumber(d.notifications.length)).replace('{time}', formatDT(d.fetched_at));
}

// ---- Definitions tab ------------------------------------------------------

function alRenderChips() {
    const defs = (_al.data && _al.data.definitions) || [];
    const pres = document.getElementById('al-presets');
    if (pres) {
        pres.innerHTML = AL_PRESETS.map(p => {
            const n = defs.filter(d => !d.system && p.test(d, _al.notifById)).length;
            return `<button type="button" class="al-chip ${_al.preset === p.key ? 'active' : ''}" data-act="alSetPreset" data-arg="${p.key}">${t(p.label)}<span class="al-n">${formatNumber(n)}</span></button>`;
        }).join('');
    }
    const counts = {};
    defs.forEach(d => (d.tags || []).forEach(tg => { counts[tg] = (counts[tg] || 0) + 1; }));
    const tags = Object.entries(counts).filter(([, n]) => n >= 2).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const shown = _al.tagsExpanded ? tags : tags.slice(0, 16);
    const tagEl = document.getElementById('al-tags');
    if (tagEl) {
        document.querySelectorAll('.al-tags-row').forEach(x => x.classList.toggle('is-hidden', !tags.length));
        tagEl.innerHTML = !tags.length ? '' : shown.map(([tg, n]) =>
                `<button type="button" class="al-chip ${_al.tags.has(tg) ? 'active' : ''}" data-act="alToggleTag" data-arg="${esc(tg)}">${esc(tg)}<span class="al-n">${formatNumber(n)}</span></button>`).join('') +
            (tags.length > 16 ? `<button type="button" class="al-chip" data-act="alToggleTagsExpanded">${_al.tagsExpanded ? t('al_tags_less') : t('al_tags_more').replace('{n}', tags.length - 16)}</button>` : '');
    }
}

function alSetPreset(key) {
    _al.preset = _al.preset === key ? '' : key;
    _al.page = 1; _al.lastIdx = null;
    alSyncUrl(); alRenderChips(); alRenderDefs();
}

function alApplyPreset(key) {
    _al.preset = key; _al.page = 1;
    alTab('defs'); alSyncUrl(); alRenderChips(); alRenderDefs();
}

function alToggleTag(tg) {
    if (_al.tags.has(tg)) _al.tags.delete(tg); else _al.tags.add(tg);
    _al.page = 1; _al.lastIdx = null;
    alSyncUrl(); alRenderChips(); alRenderDefs();
}

function alToggleTagsExpanded() { _al.tagsExpanded = !_al.tagsExpanded; alRenderChips(); }

let _alQTimer = null;
function alQueryInput(v) {
    clearTimeout(_alQTimer);
    _alQTimer = setTimeout(() => {
        _al.q = v; _al.page = 1; _al.lastIdx = null;
        alSyncUrl(); alRenderDefs();
    }, 200);
}

function alClearFilters() {
    _al.q = ''; _al.preset = ''; _al.tags.clear(); _al.page = 1; _al.lastIdx = null;
    const qEl = document.getElementById('al-q'); if (qEl) qEl.value = '';
    alSyncUrl(); alRenderChips(); alRenderDefs();
}

function alFilterByNotif(title) {
    _al.q = `notif:"${title}"`; _al.preset = ''; _al.tags.clear(); _al.page = 1;
    const qEl = document.getElementById('al-q'); if (qEl) qEl.value = _al.q;
    alTab('defs'); alSyncUrl(); alRenderChips(); alRenderDefs();
}

function alSyncUrl() {
    const sp = new URLSearchParams();
    if (_al.server) sp.set('server', _al.server);
    if (_al.q) sp.set('q', _al.q);
    if (_al.preset) sp.set('preset', _al.preset);
    if (_al.tags.size) sp.set('tags', [..._al.tags].join('|'));
    if (_al.tab !== 'defs') sp.set('tab', _al.tab);
    const qs = sp.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
}

function _alNotifChips(ids) {
    if (!ids.length) return `<span class="al-none">${t('al_no_notif')}</span>`;
    return ids.map(id => {
        const n = _al.notifById[id];
        return n ? `<span class="al-nchip">${esc(n.title)}</span>`
                 : `<span class="al-nchip al-dangling" title="${esc(id)}">${t('al_missing_notif')}</span>`;
    }).join('');
}

function alRenderDefs() {
    const tbody = document.querySelector('#al-defs-table tbody');
    if (!tbody || !_al.data) return;
    const list = alFiltered();
    const pages = Math.max(1, Math.ceil(list.length / _al.perPage));
    if (_al.page > pages) _al.page = pages;
    const start = (_al.page - 1) * _al.perPage;
    const rows = list.slice(start, start + _al.perPage);
    tbody.innerHTML = rows.length ? rows.map((d, i) => {
        const sel = _al.selected.has(d.id);
        const prio = {1: t('al_prio_low'), 2: t('al_prio_normal'), 3: t('al_prio_high')}[d.priority] || esc(d.priority);
        const state = d.state === 'ENABLED'
            ? `<span class="al-state-on">${t('al_enabled')}</span>`
            : `<span class="al-state-off">${t('al_disabled')}</span>`;
        return `<tr class="${sel ? 'al-row-sel' : ''}">
            <td><input type="checkbox" ${sel ? 'checked' : ''} ${d.system ? 'disabled' : ''} data-act="alRowCheck" data-act-event data-id="${esc(d.id)}" data-idx="${start + i}"></td>
            <td class="al-title"><button type="button" class="al-name" data-act="alShowDef" data-arg="${esc(d.id)}" title="${esc(t('al_d_open'))}">${esc(d.title)}</button>${d.system ? `<span class="al-sys">${t('al_system')}</span>` : ''}
                ${d.description ? `<span class="al-desc" title="${esc(d.description)}">${esc(d.description)}</span>` : ''}</td>
            <td>${prio}</td>
            <td>${state}</td>
            <td>${_alNotifChips(d.notifications)}</td>
            <td class="al-matched">${d.matched_at ? formatDT(d.matched_at) : `<span class="al-none">${t('al_never')}</span>`}</td>
        </tr>`;
    }).join('') : `<tr><td class="u143" colspan="6">${t('al_no_match')}</td></tr>`;
    const all = document.getElementById('al-page-all');
    const selectable = rows.filter(d => !d.system);
    if (all) all.checked = selectable.length > 0 && selectable.every(d => _al.selected.has(d.id));
    alRenderPagination(pages);
    alRenderSelCount(list);
}

function alRenderPagination(pages) {
    const el = document.getElementById('al-defs-pagination');
    if (!el) return;
    if (pages <= 1) { el.innerHTML = ''; return; }
    const cur = _al.page;
    let html = `<button ${cur === 1 ? 'disabled' : ''} data-act="alGoPage" data-args="[${cur - 1}]">&laquo;</button>`;
    for (let p = 1; p <= pages; p++) {
        if (p === 1 || p === pages || Math.abs(p - cur) <= 2) {
            html += `<button class="${p === cur ? 'active' : ''}" data-act="alGoPage" data-args="[${p}]">${p}</button>`;
        } else if (Math.abs(p - cur) === 3) {
            html += '<span>…</span>';
        }
    }
    html += `<button ${cur === pages ? 'disabled' : ''} data-act="alGoPage" data-args="[${cur + 1}]">&raquo;</button>`;
    el.innerHTML = html;
}

function alGoPage(p) { _al.page = p; alRenderDefs(); }

/** "N selected (M not in the current results)" — a selection survives a filter
 *  change, so say when part of it is out of sight before anyone applies it. */
function alRenderSelCount(list) {
    const el = document.getElementById('al-sel-count');
    if (!el) return;
    const visible = new Set((list || alFiltered()).map(d => d.id));
    const hidden = [..._al.selected].filter(id => !visible.has(id)).length;
    el.innerHTML = t('al_selected').replace('{n}', `<strong>${formatNumber(_al.selected.size)}</strong>`)
        .replace('{m}', formatNumber((list || []).length)) +
        (hidden ? ` <span class="al-warn">${t('al_selected_hidden').replace('{n}', formatNumber(hidden))}</span>` : '');
}

function alRowCheck(e) {
    const box = e.target.closest('input');
    if (!box) return;
    const id = box.dataset.id, idx = parseInt(box.dataset.idx, 10);
    const list = alFiltered();
    const on = box.checked;
    const ids = (e.shiftKey && _al.lastIdx !== null) ? alRangeIds(list, _al.lastIdx, idx) : [id];
    const byId = Object.fromEntries(list.map(d => [d.id, d]));
    ids.forEach(x => {
        if (byId[x] && byId[x].system) return;
        if (on) _al.selected.add(x); else _al.selected.delete(x);
    });
    _al.lastIdx = idx;
    alRenderDefs();
}

function alTogglePage(e) {
    const on = e.target.checked;
    const list = alFiltered();
    const start = (_al.page - 1) * _al.perPage;
    list.slice(start, start + _al.perPage).filter(d => !d.system)
        .forEach(d => { if (on) _al.selected.add(d.id); else _al.selected.delete(d.id); });
    alRenderDefs();
}

function alSelectAllMatching() {
    alFiltered().filter(d => !d.system).forEach(d => _al.selected.add(d.id));
    alRenderDefs();
}

function alClearSelection() { _al.selected.clear(); _al.lastIdx = null; alRenderDefs(); }

function alTab(name) {
    _al.tab = name;
    ['defs', 'notifs', 'health', 'changes'].forEach(k => {
        const pane = document.getElementById(`al-pane-${k}`);
        if (pane) pane.classList.toggle('is-hidden', k !== name);
    });
    document.querySelectorAll('#al-tabs .arch-tab').forEach(b => b.classList.toggle('active', b.dataset.arg === name));
    if (name === 'changes') alLoadChanges();
    if (_al.server) alSyncUrl();
}

// ---- Notifications tab ----------------------------------------------------

function alNotifType(type) {
    const m = {'email-notification-v1': 'Email', 'http-notification-v1': 'HTTP',
               'http-notification-v2': 'Custom HTTP', 'slack-notification-v1': 'Slack',
               'teams-notification-v1': 'Microsoft Teams', 'teams-notification-v2': 'Microsoft Teams',
               'pagerduty-notification-v1': 'PagerDuty', 'legacy-alarm-callback-notification-v1': 'Legacy'};
    return m[type] || type || '';
}

function alRenderNotifs() {
    const tbody = document.querySelector('#al-notifs-table tbody');
    if (!tbody || !_al.data) return;
    const ns = [...(_al.data.notifications || [])].sort((a, b) => a.title.localeCompare(b.title));
    tbody.innerHTML = ns.length ? ns.map(n => `<tr>
        <td>${esc(n.title)}</td>
        <td>${esc(alNotifType(n.type))}</td>
        <td class="u028">${esc(n.description)}</td>
        <td>${n.used_by
            ? `<button class="btn-sm btn-secondary" data-act="alFilterByNotif" data-arg="${esc(n.title)}">${t('al_used_by').replace('{n}', formatNumber(n.used_by))}</button>`
            : `<span class="al-warn">${t('al_unused')}</span>`}</td>
        <td><button class="btn-sm btn-secondary" data-act="alTestNotif" data-args="${esc(JSON.stringify([n.id, n.title]))}">${icon('play', 14)} ${t('al_test_send')}</button></td>
    </tr>`).join('') : `<tr><td class="u143" colspan="5">${t('log_no_data')}</td></tr>`;
}

function alTestNotif(id, title) {
    showConfirm(t('al_test_title'), esc(t('al_test_confirm').replace('{name}', title)), async () => {
        const r = await fetchJSON(`${API}/alerting/test-notification`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({server: _al.server, notification_id: id})});
        if (r.need_signin) { alOpenSignin(r.error); return; }
        setTimeout(() => showAlert(r.error ? esc(r.error)
            : r.ok ? esc(t('al_test_ok').replace('{name}', title))
                   : esc(t('al_test_failed').replace('{name}', title)) + '<br><code>' + esc(r.message) + '</code>'), 50);
    });
}

// ---- Health tab -----------------------------------------------------------

function alHealthFindings() {
    const d = _al.data || {definitions: [], notifications: []};
    const defs = d.definitions.filter(x => !x.system);
    const count = key => defs.filter(x => _alPreset(key).test(x, _al.notifById)).length;
    const unused = d.notifications.filter(n => !n.used_by);
    return [
        {key: 'enabled_no_notif', n: count('enabled_no_notif'), bad: true, title: 'al_h_enabled_no_notif', desc: 'al_h_enabled_no_notif_d'},
        {key: 'dangling', n: count('dangling'), bad: true, title: 'al_h_dangling', desc: 'al_h_dangling_d'},
        {key: 'unused', n: unused.length, warn: true, title: 'al_h_unused', desc: 'al_h_unused_d',
         list: unused.map(x => x.title)},
        {key: 'stale', n: count('stale'), warn: true, title: 'al_h_stale', desc: 'al_h_stale_d'},
        {key: 'never_matched', n: count('never_matched'), title: 'al_h_never', desc: 'al_h_never_d'},
        {key: 'disabled', n: count('disabled'), title: 'al_h_disabled', desc: 'al_h_disabled_d'},
    ];
}

function alRenderHealth() {
    const el = document.getElementById('al-health');
    if (!el || !_al.data) return;
    el.innerHTML = '<div class="al-health">' + alHealthFindings().map(f => {
        const cls = !f.n ? 'al-hok' : f.bad ? 'al-hbad' : f.warn ? 'al-hwarn' : '';
        const action = f.key === 'unused'
            ? (f.n ? `<button class="btn-sm btn-secondary" data-act="alTab" data-arg="notifs">${t('al_h_view')}</button>` : '')
            : (f.n ? `<button class="btn-sm btn-secondary" data-act="alApplyPreset" data-arg="${f.key}">${icon('filter', 14)} ${t('al_h_filter')}</button>` : '');
        return `<div class="al-hcard ${cls}">
            <h4>${t(f.title).replace('{days}', _AL_STALE_DAYS)}</h4>
            <div class="al-hn">${formatNumber(f.n)}</div>
            <p>${t(f.desc).replace('{days}', _AL_STALE_DAYS)}</p>
            ${f.list && f.list.length ? `<ul class="al-hlist">${f.list.slice(0, 8).map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
            ${action}
        </div>`;
    }).join('') + '</div>';
}

// ---- Bulk change dialog ---------------------------------------------------

function _alModal(show) {
    const m = document.getElementById('al-action-modal');
    if (!m) return;
    m.classList.toggle('hidden', !show);
    m.style.display = show ? 'flex' : 'none';
}

function alCloseAction() {
    if (_al.jobTimer) { clearInterval(_al.jobTimer); _al.jobTimer = null; }
    _al.planId = null;
    _modalButtons('');
    _alModal(false);
}

function _modalButtons(html) { document.getElementById('al-action-buttons').innerHTML = html; }

/** How many of the selected definitions carry each notification. */
function _alSelectedNotifCounts() {
    const byId = Object.fromEntries(((_al.data && _al.data.definitions) || []).map(d => [d.id, d]));
    const counts = {};
    _al.selected.forEach(id => (byId[id] ? byId[id].notifications : []).forEach(n => { counts[n] = (counts[n] || 0) + 1; }));
    return counts;
}

function alOpenAction(type) {
    if (!_al.data) return;
    if (!_al.selected.size) { showAlert(t('al_select_first')); return; }
    _al.pendingAction = type;
    const counts = _alSelectedNotifCounts();
    const ns = [...(_al.data.notifications || [])].sort((a, b) => a.title.localeCompare(b.title));
    const sel = _al.selected.size;
    const opt = (n, picked) => `<label><input type="checkbox" class="al-pick-n" value="${esc(n.id)}" ${picked ? 'checked' : ''}> ${esc(n.title)} <span class="al-n">${esc(alNotifType(n.type))} · ${t('al_on_selected').replace('{n}', formatNumber(counts[n.id] || 0)).replace('{m}', formatNumber(sel))}</span></label>`;
    let form = '';
    if (type === 'add' || type === 'remove') {
        const list = type === 'remove' ? ns.filter(n => counts[n.id]) : ns;
        form = `<div class="form-group"><label>${t(type === 'add' ? 'al_pick_add' : 'al_pick_remove')}</label>
            ${list.length ? `<div class="al-pick">${list.map(n => opt(n, false)).join('')}</div>` : `<div class="al-note">${t('al_nothing_to_remove')}</div>`}</div>`;
    } else {
        const from = ns.filter(n => counts[n.id]);
        form = `<div class="form-group"><label>${t('al_replace_from')}</label>
              <select id="al-rep-from">${from.map(n => `<option value="${esc(n.id)}">${esc(n.title)} (${formatNumber(counts[n.id])})</option>`).join('')}</select></div>
            <div class="form-group"><label>${t('al_replace_to')}</label>
              <select id="al-rep-to">${ns.map(n => `<option value="${esc(n.id)}">${esc(n.title)}</option>`).join('')}</select></div>`;
        if (!from.length) form = `<div class="al-note">${t('al_nothing_to_remove')}</div>`;
    }
    const visible = new Set(alFiltered().map(d => d.id));
    const hidden = [..._al.selected].filter(id => !visible.has(id)).length;
    document.getElementById('al-action-title').innerHTML =
        icon(type === 'add' ? 'plus' : type === 'remove' ? 'close' : 'refresh') + ' ' + t('al_title_' + type);
    document.getElementById('al-action-form').innerHTML =
        `<div class="al-note">${t('al_applies_to').replace('{n}', `<strong>${formatNumber(sel)}</strong>`)}${hidden ? ` <span class="al-warn">${t('al_selected_hidden').replace('{n}', formatNumber(hidden))}</span>` : ''}</div>` + form;
    document.getElementById('al-action-preview').innerHTML = '';
    _modalButtons(`<button class="btn-primary" data-act="alPreview">${icon('eye', 15)} ${t('al_btn_preview')}</button>
        <button class="btn-secondary" data-act="alCloseAction">${icon('close', 15)} ${t('btn_cancel')}</button>`);
    _alModal(true);
    if (type === 'replace') setTimeout(initCustomSelects, 0);
}

function _alActionFromForm() {
    const type = _al.pendingAction;
    if (type === 'replace') {
        const f = document.getElementById('al-rep-from'), to = document.getElementById('al-rep-to');
        return {type, from: f ? f.value : '', to: to ? to.value : ''};
    }
    return {type, notification_ids: [...document.querySelectorAll('.al-pick-n:checked')].map(x => x.value)};
}

async function alPreview() {
    const action = _alActionFromForm();
    const pv = document.getElementById('al-action-preview');
    pv.innerHTML = `<div class="al-note"><span class="spinner-text">${t('loading')}...</span></div>`;
    const r = await fetchJSON(`${API}/alerting/preview`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server: _al.server, action, definition_ids: [..._al.selected]})});
    if (r.need_signin) { alCloseAction(); alOpenSignin(r.error); return; }
    if (r.error) { pv.innerHTML = `<div class="al-note al-warn">${esc(r.error)}</div>`; return; }
    alShowPlan(r, false);
}

function _alNames(ids) {
    return ids.length ? ids.map(id => esc((_al.notifById[id] || {}).title || id)).join(', ') : t('al_no_notif');
}

/** Render a server-made plan: what will change, what already is, what is skipped. */
function alShowPlan(r, isUndo) {
    _al.planId = r.plan_id;
    const pv = document.getElementById('al-action-preview');
    const ch = r.change || [], un = r.unchanged || [], sk = r.skipped || [];
    const disabled = ch.filter(x => x.state !== 'ENABLED').length;
    pv.innerHTML = `
        <div class="al-summary">
            <div class="al-sum al-sum-change"><div class="al-sum-n">${formatNumber(ch.length)}</div><div class="al-sum-l">${t('al_will_change')}</div></div>
            <div class="al-sum"><div class="al-sum-n">${formatNumber(un.length)}</div><div class="al-sum-l">${t('al_already')}</div></div>
            <div class="al-sum al-sum-skip"><div class="al-sum-n">${formatNumber(sk.length)}</div><div class="al-sum-l">${t('al_skipped')}</div></div>
        </div>
        ${ch.length ? `<div class="al-list">${ch.slice(0, 300).map(x => `<div><strong>${esc(x.title)}</strong>${x.state !== 'ENABLED' ? ` <span class="al-state-off">(${t('al_disabled')})</span>` : ''}<br><span class="u028">${_alNames(x.before)} → ${_alNames(x.after)}</span></div>`).join('')}${ch.length > 300 ? `<div class="u028">… +${formatNumber(ch.length - 300)}</div>` : ''}</div>` : ''}
        ${sk.length ? `<div class="al-list">${sk.map(x => `<div>${esc(x.title || x.id)}<span class="al-why">${esc(trSrv(x.reason))}</span></div>`).join('')}</div>` : ''}
        <div class="al-note">${t('al_state_kept')}${disabled ? ' ' + t('al_state_kept_n').replace('{n}', formatNumber(disabled)) : ''}</div>
        <div class="al-note">${t(isUndo ? 'al_undo_note' : 'al_undo_hint')}</div>`;
    _modalButtons((ch.length ? `<button class="btn-primary" data-act="alApply">${icon('check', 15)} ${t('al_btn_apply').replace('{n}', formatNumber(ch.length))}</button>` : '') +
        `<button class="btn-secondary" data-act="alCloseAction">${icon('close', 15)} ${t(ch.length ? 'btn_cancel' : 'btn_close')}</button>`);
}

async function alApply() {
    if (!_al.planId) return;
    _modalButtons(`<span class="spinner-text">${t('loading')}...</span>`);
    const r = await fetchJSON(`${API}/alerting/apply`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({plan_id: _al.planId})});
    _al.planId = null;
    if (r.need_signin) { alCloseAction(); alOpenSignin(r.error); return; }
    if (r.error) {
        document.getElementById('al-action-preview').insertAdjacentHTML('beforeend', `<div class="al-note al-warn">${esc(r.error)}</div>`);
        _modalButtons(`<button class="btn-secondary" data-act="alCloseAction">${icon('close', 15)} ${t('btn_close')}</button>`);
        return;
    }
    _al.jobId = r.job_id;
    _al.selected.clear();
    document.getElementById('al-action-form').innerHTML = '';
    document.getElementById('al-action-preview').innerHTML = `
        <div class="al-note" id="al-job-text">${t('al_running')}</div>
        <div class="progress-bar u099"><div class="progress-fill" id="al-job-bar"></div></div>`;
    _modalButtons(`<button class="btn-danger" data-act="alCancelJob">${icon('close', 15)} ${t('btn_cancel')}</button>
        <button class="btn-secondary" data-act="alCloseAction">${icon('close', 15)} ${t('al_close_keep')}</button>`);
    _al.jobTimer = setInterval(alPollJob, 1000);
    alPollJob();
}

async function alPollJob() {
    if (!_al.jobId) return;
    const j = await fetchJSON(`${API}/jobs/${encodeURIComponent(_al.jobId)}`);
    const bar = document.getElementById('al-job-bar'), txt = document.getElementById('al-job-text');
    if (!j || j.error || !bar) return;
    bar.style.width = `${Math.min(100, j.progress_pct || 0)}%`;
    if (txt) txt.textContent = t('al_progress').replace('{done}', formatNumber(j.messages_done || 0)).replace('{total}', formatNumber(j.messages_total || 0));
    if (j.status === 'running' || j.status === 'pending') return;
    clearInterval(_al.jobTimer); _al.jobTimer = null;
    const res = (j.result && j.result.alerting) || {};
    const failed = res.failed || [], skipped = res.skipped || [];
    bar.style.width = '100%';
    document.getElementById('al-action-preview').innerHTML = `
        <div class="al-summary">
            <div class="al-sum al-sum-change"><div class="al-sum-n">${formatNumber(res.changed || 0)}</div><div class="al-sum-l">${t('al_changed')}</div></div>
            <div class="al-sum al-sum-skip"><div class="al-sum-n">${formatNumber(skipped.length)}</div><div class="al-sum-l">${t('al_skipped')}</div></div>
            <div class="al-sum al-sum-skip"><div class="al-sum-n">${formatNumber(failed.length)}</div><div class="al-sum-l">${t('al_failed')}</div></div>
        </div>
        <div class="al-note">${statusBadge(j.status, j.error_message)} ${esc(jobNote(j.error_message || ''))}</div>
        ${failed.length || skipped.length ? `<div class="al-list">${failed.concat(skipped).map(x => `<div>${esc(x.title || x.id)}<span class="al-why">${esc(trSrv(x.reason))}</span></div>`).join('')}</div>` : ''}`;
    _modalButtons(`<button class="btn-primary" data-act="alCloseAction">${icon('check', 15)} ${t('btn_close')}</button>
        <a class="btn-secondary al-link-btn" href="/jobs">${icon('task', 15)} ${t('nav_jobs')}</a>`);
    _al.jobId = null;
    alLoad();
    if (_al.tab === 'changes') alLoadChanges();
}

function alCancelJob() {
    const jid = _al.jobId;
    if (!jid) return;
    fetchJSON(`${API}/jobs/${encodeURIComponent(jid)}/cancel`, {method: 'POST'});
}

// ---- Change history + undo ------------------------------------------------

async function alLoadChanges() {
    const tbody = document.querySelector('#al-changes-table tbody');
    if (!tbody || !_al.server) return;
    const r = await fetchJSON(`${API}/alerting/batches?server=${encodeURIComponent(_al.server)}`);
    const items = r.items || [];
    const undone = new Set(items.map(b => b.undoes_batch).filter(Boolean));
    tbody.innerHTML = items.length ? items.map(b => {
        // failed rows too: a write can land and still be reported failed (timeout, Graylog
        // storing something else); the server skips what that batch did not leave in place
        const canUndo = (b.applied + b.pending + (b.failed || 0)) > 0 && !b.undoes_batch;
        const result = t('al_batch_result').replace('{applied}', formatNumber(b.applied + b.restored))
            .replace('{failed}', formatNumber(b.failed)) +
            (b.restored ? ` · ${t('al_batch_restored').replace('{n}', formatNumber(b.restored))}` : '');
        const what = b.undoes_batch ? t('al_batch_undo').replace('{id}', esc(String(b.undoes_batch).slice(0, 8)))
                                    : t('al_act_' + b.action);
        return `<tr>
            <td class="u147">${formatDT(b.created_at)}</td>
            <td>${esc(b.username)}</td>
            <td>${what} <span class="u028">${esc(String(b.batch_id).slice(0, 8))}</span></td>
            <td>${result}${undone.has(b.batch_id) ? ` · <span class="u028">${t('al_batch_was_undone')}</span>` : ''}</td>
            <td><button class="btn-sm btn-secondary" data-act="alBatchDetail" data-arg="${esc(b.batch_id)}">${t('al_detail')}</button>
                ${canUndo ? `<button class="btn-sm btn-secondary" data-act="alUndo" data-arg="${esc(b.batch_id)}">${icon('refresh', 14)} ${t('al_undo')}</button>` : ''}</td>
        </tr>`;
    }).join('') : `<tr><td class="u143" colspan="5">${t('al_no_changes')}</td></tr>`;
}

async function alBatchDetail(batchId) {
    const r = await fetchJSON(`${API}/alerting/batches/${encodeURIComponent(batchId)}`);
    const rows = r.items || [];
    const names = list => list.length ? list.map(x => esc((_al.notifById[x.notification_id] || {}).title || x.notification_id)).join(', ') : t('al_no_notif');
    showAlert(`<div class="al-list">${rows.map(x => `<div><strong>${esc(x.title)}</strong> · ${esc(t('al_row_' + x.status))}${x.error ? `<span class="al-why">${esc(x.error)}</span>` : ''}<br><span class="u028">${names(x.before_notifications)} → ${names(x.after_notifications)}</span></div>`).join('')}</div>`);
}

async function alUndo(batchId) {
    const r = await fetchJSON(`${API}/alerting/undo-preview`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({batch_id: batchId})});
    if (r.need_signin) { alOpenSignin(r.error); return; }
    if (r.error) { showAlert(esc(r.error)); return; }
    document.getElementById('al-action-title').innerHTML = icon('refresh') + ' ' + t('al_title_undo');
    document.getElementById('al-action-form').innerHTML = '';
    _alModal(true);
    alShowPlan(r, true);
}

// ---- Sign in --------------------------------------------------------------

function alOpenSignin(why) {
    const m = document.getElementById('al-signin-modal');
    if (!m) return;
    const u = document.getElementById('al-signin-user');
    if (u && !u.value && _al.loginUser && !['localadmin', 'token-user'].includes(_al.loginUser)) u.value = _al.loginUser;
    document.getElementById('al-signin-why').textContent =
        (typeof why === 'string' && why ? why + ' — ' : '') + t('al_signin_why').replace('{server}', _al.server);
    document.getElementById('al-signin-result').textContent = '';
    m.classList.remove('hidden');
    m.style.display = 'flex';
}

function alCloseSignin() {
    const m = document.getElementById('al-signin-modal');
    if (m) { m.classList.add('hidden'); m.style.display = 'none'; }
    const p = document.getElementById('al-signin-pass'); if (p) p.value = '';
}

async function alSignin() {
    const user = document.getElementById('al-signin-user').value.trim();
    const pass = document.getElementById('al-signin-pass').value;
    const out = document.getElementById('al-signin-result');
    const r = await fetchJSON(`${API}/alerting/signin`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server: _al.server, username: user, password: pass})});
    if (r.error) { out.innerHTML = `<span class="u141">${esc(r.error)}</span>`; return; }
    alCloseSignin();
    alLoad();
}

// ---- Definition detail ----------------------------------------------------

/** 300000 → "5 min" in the UI language. */
function alDuration(ms) {
    const n = Number(ms) || 0;
    if (!n) return t('al_u_sec').replace('{n}', 0);
    const units = [[86400000, 'al_u_day'], [3600000, 'al_u_hour'], [60000, 'al_u_min'], [1000, 'al_u_sec']];
    for (const [size, key] of units) {
        if (n >= size && n % size === 0) return t(key).replace('{n}', n / size);
    }
    return t('al_u_sec').replace('{n}', Math.round(n / 1000));
}

/** A series {type|function, field} → "count()" / "avg(bytes)". */
function alSeriesText(s) {
    if (!s) return '?';
    const fn = s.type || s.function || '?';
    return `${fn}(${s.field || ''})`;
}

/** Graylog's condition tree → "count() > 10 AND avg(bytes) >= 5". */
function alExprText(e, series) {
    if (!e) return '';
    const L = () => alExprText(e.left, series), R = () => alExprText(e.right, series);
    switch (e.expr) {
        case 'number': return String(e.value);
        case 'number-ref': return series[e.ref] ? alSeriesText(series[e.ref]) : String(e.ref);
        case '&&': return `${L()} AND ${R()}`;
        case '||': return `${L()} OR ${R()}`;
        case '!': return `NOT ${alExprText(e.child || e.left, series)}`;
        case 'group': return `(${alExprText(e.child, series)})`;
        case '<': case '<=': case '>': case '>=': case '==': return `${L()} ${e.expr} ${R()}`;
        default: return JSON.stringify(e);
    }
}

function _alKv(label, value) {
    return `<div class="al-kv-k">${label}</div><div class="al-kv-v">${value}</div>`;
}

async function alShowDef(id) {
    const m = document.getElementById('al-detail-modal');
    if (!m) return;
    const summary = ((_al.data && _al.data.definitions) || []).find(d => d.id === id) || {};
    document.getElementById('al-detail-title').innerHTML = icon('warning') + ' ' + esc(summary.title || id);
    const body = document.getElementById('al-detail-body');
    body.innerHTML = `<div class="al-loading-block"><span class="spinner-text">${t('al_loading_def')}</span></div>`;
    document.getElementById('al-detail-buttons').innerHTML =
        `<button class="btn-secondary" data-act="alCloseDetail">${icon('close', 15)} ${t('btn_close')}</button>`;
    m.classList.remove('hidden'); m.style.display = 'flex';

    const r = await fetchJSON(`${API}/alerting/definition?server=${encodeURIComponent(_al.server)}&id=${encodeURIComponent(id)}`);
    if (r.need_signin) { alCloseDetail(); alOpenSignin(r.error); return; }
    if (r.error) { body.innerHTML = `<div class="al-note al-warn">${esc(r.error)}</div>`; return; }
    const d = r.definition || {}, cfg = d.config || {}, ns = d.notification_settings || {};
    const series = {};
    (cfg.series || []).forEach(s => { series[s.id] = s; });
    const streams = (cfg.streams || []).map(sid => esc((r.streams || {})[sid] || sid));
    const enabled = String(d.state || '').toUpperCase() === 'ENABLED';
    const prio = {1: t('al_prio_low'), 2: t('al_prio_normal'), 3: t('al_prio_high')}[d.priority] || esc(d.priority);
    const sched = cfg.use_cron_scheduling
        ? `${t('al_d_cron')} <code>${esc(cfg.cron_expression || '')}</code> ${esc(cfg.cron_timezone || '')}`
        : t('al_d_every').replace('{every}', alDuration(cfg.execute_every_ms)).replace('{within}', alDuration(cfg.search_within_ms));
    const cond = cfg.conditions && cfg.conditions.expression ? alExprText(cfg.conditions.expression, series) : '';
    const notifs = (d.notifications || []).map(n => n.notification_id);
    const rows = [
        _alKv(t('th_status'), `<span class="${enabled ? 'al-state-on' : 'al-state-off'}">${t(enabled ? 'al_enabled' : 'al_disabled')}</span> · ${t('al_th_priority')} ${prio}`),
        d.description ? _alKv(t('al_th_description'), `<div class="al-d-desc">${esc(d.description)}</div>`) : '',
        cfg.type === 'aggregation-v1' || cfg.query !== undefined ? _alKv(t('al_d_query'), cfg.query ? `<code class="al-d-code">${esc(cfg.query)}</code>` : `<span class="al-none">${t('al_d_any')}</span>`) : '',
        cfg.streams !== undefined ? _alKv(t('al_d_streams'), streams.length ? streams.map(x => `<span class="al-nchip">${x}</span>`).join('') : `<span class="al-none">${t('al_d_all_streams')}</span>`) : '',
        cfg.execute_every_ms !== undefined || cfg.use_cron_scheduling ? _alKv(t('al_d_schedule'), sched) : '',
        (cfg.series || []).length ? _alKv(t('al_d_series'), (cfg.series || []).map(s => `<code class="al-d-code">${esc(alSeriesText(s))}</code>`).join(' ') +
            ((cfg.group_by || []).length ? ` <span class="u028">${t('al_d_group_by')} ${(cfg.group_by || []).map(esc).join(', ')}</span>` : '')) : '',
        cond ? _alKv(t('al_d_condition'), `<code class="al-d-code">${esc(cond)}</code>`) : '',
        _alKv(t('al_th_notifications'), _alNotifChips(notifs) +
            `<div class="u028 al-d-sub">${t('al_d_grace').replace('{grace}', alDuration(ns.grace_period_ms)).replace('{n}', formatNumber(ns.backlog_size || 0))}</div>`),
        _alKv(t('al_th_matched'), d.matched_at ? formatDT(d.matched_at) : `<span class="al-none">${t('al_never')}</span>`),
        _alKv(t('al_d_updated'), d.updated_at ? formatDT(d.updated_at) : '—'),
        _alKv(t('al_d_type'), `<code>${esc(cfg.type || '')}</code> · ID <code>${esc(d.id || id)}</code>`),
    ].join('');
    body.innerHTML = `<div class="al-kv">${rows}</div>
        <details class="search-help al-d-json"><summary>${t('al_d_json')}</summary><pre>${esc(JSON.stringify(d, null, 2))}</pre></details>`;
    const sel = _al.selected.has(id);
    const gl = r.graylog_url ? `${r.graylog_url}/alerts/definitions/${encodeURIComponent(id)}` : '';
    document.getElementById('al-detail-buttons').innerHTML =
        (summary.system ? '' : `<button class="btn-primary" data-act="alToggleFromDetail" data-arg="${esc(id)}">${icon(sel ? 'close' : 'check', 15)} ${t(sel ? 'al_d_unselect' : 'al_d_select')}</button>`) +
        (gl ? `<a class="btn-secondary al-link-btn" href="${esc(gl)}" target="_blank" rel="noopener noreferrer">${icon('globe', 15)} ${t('al_d_open_graylog')}</a>` : '') +
        `<button class="btn-secondary" data-act="alCloseDetail">${icon('close', 15)} ${t('btn_close')}</button>`;
}

function alToggleFromDetail(id) {
    if (_al.selected.has(id)) _al.selected.delete(id); else _al.selected.add(id);
    alRenderDefs();
    alShowDef(id);
}

function alCloseDetail() {
    const m = document.getElementById('al-detail-modal');
    if (m) { m.classList.add('hidden'); m.style.display = 'none'; }
}

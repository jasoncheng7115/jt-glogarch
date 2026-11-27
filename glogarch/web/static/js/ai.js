/* jt-glogarch — AI chat page (added 1.21).
 * The model reads Graylog through read-only tools as the signed-in user's own
 * Graylog account (web/routes/ai.py). Its answers can quote log text, which an
 * attacker can write: aiMarkdown() escapes everything first and only then adds
 * a small set of formatting; links are https only. */

const _ai = {toolStart: 0, toolsDone: [], llm: '', sideCollapsed: false, folded: {}, preview: null, status: null, conv: null, server: '', busy: false, abort: null, poll: null, search: '', searchTimer: null, renaming: false, partial: '', reasoning: '', thinkOpen: null, partialTimer: null, started: 0, ticker: null, incidents: [], gotDone: false, stopPending: false, codeOpen: {}, pvDismissed: false, pvSig: '', pvAt: 0, pvWatch: null, convLimit: 50};

function aiMsg(text, level) {
    const el = document.getElementById('ai-message');
    if (!el) return;
    el.className = 'pk-message ' + (level === 'err' ? 'pk-err' : 'pk-ok');
    el.textContent = text || '';
    el.classList.toggle('hidden', !text);
}

// per-browser preferences (1.36): the folded list, folded groups, the LLM picked,
// whether the thinking is shown. Storage can be off (private window): never fatal.
function _aiPref(k, v) {
    try {
        if (v === undefined) return localStorage.getItem('jt-ai-' + k);
        if (v === null) localStorage.removeItem('jt-ai-' + k); else localStorage.setItem('jt-ai-' + k, v);
    } catch (_) { /* storage blocked: the default stays */ }
    return null;
}

// ---- Markdown (escape first, then format) -------------------------------------

function _aiInline(s) {
    s = s.replace(/`([^`]+)`/g, (m, c) => `<code>${c}</code>`);
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g,
        (m, txt, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${txt}</a>`);
    return s;
}

function aiMarkdown(src) {
    const lines = esc(src || '').split('\n');
    const out = [];
    let i = 0;
    while (i < lines.length) {
        const ln = lines[i];
        if (/^```/.test(ln)) {
            const lang = (ln.slice(3).trim().match(/^[A-Za-z0-9_+-]{1,20}/) || [''])[0].toLowerCase();
            const buf = [];
            i++;
            while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
            i++;
            out.push(`<pre class="ai-code"${lang ? ` data-lang="${lang}"` : ''}><code>${buf.join('\n')}</code></pre>`);
            continue;
        }
        if (/^\s*\|.*\|\s*$/.test(ln) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
            const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => _aiInline(c.trim()));
            const head = cells(ln);
            i += 2;
            const rows = [];
            // a last row cut off before its closing | is still a row
            while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(cells(lines[i])); i++; }
            // a column whose cells are all numbers (counts, %, sizes) is right-aligned and never wraps mid-number
            const isNum = c => /^(&lt;|&gt;|[~≈+-])?\s*[\d][\d,.\s]*\s*(%|[KMGT]i?B|ms|s)?$/.test(c);
            const num = head.map((_, k) => rows.length > 0 && rows.every(r => r[k] === undefined || r[k] === '' || isNum(r[k])));
            const cls = k => num[k] ? ' class="num"' : '';
            out.push(`<div class="table-wrap"><table class="ai-table"><thead><tr>${head.map((h, k) => `<th${cls(k)}>${h}</th>`).join('')}</tr></thead>`
                + `<tbody>${rows.map(r => `<tr>${r.map((c, k) => `<td${cls(k)}>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
            continue;
        }
        const h = ln.match(/^(#{1,3})\s+(.*)$/);
        if (h) { out.push(`<h${h[1].length + 2} class="ai-h">${_aiInline(h[2])}</h${h[1].length + 2}>`); i++; continue; }
        if (/^\s*([-*]|\d+\.)\s+/.test(ln)) {
            const ordered = /^\s*\d+\./.test(ln);
            const items = [];
            while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
                items.push(_aiInline(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, '')));
                i++;
            }
            const tag = ordered ? 'ol' : 'ul';
            out.push(`<${tag}>${items.map(x => `<li>${x}</li>`).join('')}</${tag}>`);
            continue;
        }
        if (!ln.trim()) { i++; continue; }
        const para = [];
        while (i < lines.length && lines[i].trim() && !/^```|^#{1,3}\s|^\s*([-*]|\d+\.)\s+|^\s*\|/.test(lines[i])) {
            para.push(_aiInline(lines[i]));
            i++;
        }
        if (para.length) out.push(`<p>${para.join('<br>')}</p>`);
        else { out.push(`<p>${_aiInline(ln)}</p>`); i++; }
    }
    return out.join('');
}

// ---- Page -------------------------------------------------------------------------

// The chat fills the window down to a small margin (owner 2026-11-23: a fixed
// calc(100vh - 250px) left an empty band at the bottom once the bar was one row).
// What sits below the chat is the page's own bottom padding (style.css sets it to
// 24 px on this page) plus the chat's margin: subtract what is really there, or the
// page is that much taller than the window and shows a scroll bar (owner 2026-11-25:
// 23 px over at every window size, a fixed 24 px gap under a 48 px padding).
const AI_MIN_HEIGHT = 420;   // below this the page scrolls instead (a 700 px window fits)
function _aiFitHeight() {
    const el = document.getElementById('ai-layout');
    if (!el) return;
    if (window.matchMedia('(max-width: 900px)').matches) { el.style.height = ''; return; }  // one column: natural height
    const top = el.getBoundingClientRect().top + window.scrollY;   // page position, not scroll position
    const page = el.closest('.content');
    const below = (page ? parseFloat(getComputedStyle(page).paddingBottom) || 0 : 0)
        + (parseFloat(getComputedStyle(el).marginBottom) || 0);
    el.style.height = `${Math.max(AI_MIN_HEIGHT, Math.floor(window.innerHeight - top - below))}px`;
}

async function aiInit() {
    if (!document.getElementById('ai-layout')) return;
    _aiFitHeight();
    window.addEventListener('resize', _aiFitHeight);
    // the bar above can grow (settings open, sign-in, a message): keep the chat filling the window
    if (typeof ResizeObserver === 'function') new ResizeObserver(_aiFitHeight).observe(document.getElementById('ai-status-card'));
    const chev = document.getElementById('ai-settings-chev');
    if (chev) chev.innerHTML = icon('chevron_down', 14);   // turns up while the settings are open
    _ai.llm = _aiPref('llm') || '';
    _ai.sideCollapsed = _aiPref('side') === 'collapsed';
    try { _ai.folded = JSON.parse(_aiPref('folded') || '{}') || {}; } catch (_) { _ai.folded = {}; }
    _aiApplySide();
    const tp = document.getElementById('ai-think-pref');
    if (tp) tp.checked = _aiPref('think') !== 'fold';
    const inp = document.getElementById('ai-input');
    inp.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); aiSend(); } });
    _aiEnterHint();
    document.addEventListener('langchange', _aiEnterHint);
    await aiLoadStatus();
    await aiLoadConvs();
    await _aiLoadIncidents();
    aiRenderThread();
    // from the Security Incidents page: "Ask in AI chat" (?incident=<id>)
    const inc = new URLSearchParams(window.location.search).get('incident');
    if (inc && /^\d+$/.test(inc)) {
        inp.value = t('ai_prefill_incident').replace('{id}', inc);
        inp.focus();
    }
}

async function aiLoadStatus() {
    const q = _ai.server ? `?server=${encodeURIComponent(_ai.server)}` : '';
    const d = await fetchJSON(`${API}/ai/status${q}`);
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    _ai.status = d;
    _ai.server = d.server;
    const s = d.settings;
    // left: what answers (state, model, where the LLM is); right: whose Graylog it reads
    const left = [s.enabled
        ? `<span class="ai-chip ai-chip-on"><span class="ai-dot"></span><span class="glyph-centre">${esc(t('ai_on'))}</span></span>`
        : `<span class="ai-chip"><span class="ai-dot ai-dot-off"></span><span class="glyph-centre">${esc(t('ai_off'))}</span></span>`];
    // which LLM server answers: a picker when there are several (1.36), remembered per browser
    const llms = d.llms || [];
    if (!llms.some(x => x.name === _ai.llm)) _ai.llm = (llms.find(x => x.default) || llms[0] || {}).name || '';
    const cur = llms.find(x => x.name === _ai.llm);
    const label = x => `${x.name}${x.model && x.model !== x.name ? ' · ' + x.model : ''}`;
    if (llms.length > 1) {
        left.push(`<span class="ai-gl" title="${esc(t('ai_llm_pick_tip'))}">${icon('chat', 14)}<select id="ai-llm" data-act-change="aiLlmChange">${llms.map(x => `<option value="${esc(x.name)}" ${x.name === _ai.llm ? 'selected' : ''}>${esc(label(x))}</option>`).join('')}</select></span>`);
    } else if (cur) {
        left.push(`<span class="ai-chip ai-chip-model" title="${esc(t('ai_model'))}${esc(t('sec_colon'))}${esc(label(cur))}">${icon('chat', 14)}<span class="ai-chip-text">${esc(cur.model || cur.name)}</span></span>`);
    }
    if (cur) left.push(cur.private === false
        ? `<span class="ai-chip ai-chip-ext">${icon('warning', 14)}<span class="glyph-centre">${esc(t(cur.kind === 'anthropic' ? 'ai_llm_claude' : 'ai_llm_external'))}</span></span>`
        : `<span class="ai-chip ai-chip-int" title="${esc(t('ai_llm_private_tip'))}">${icon('lock', 14)}<span class="glyph-centre">${esc(t('ai_llm_private'))}</span></span>`);
    const sel = d.servers.length > 1
        ? `<select id="ai-server" data-act-change="aiServerChange">${d.servers.map(n => `<option value="${esc(n)}" ${n === d.server ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>`
        : `<strong>${esc(d.server)}</strong>`;
    const who = [`<span class="ai-gl"><span class="ai-gl-label glyph-centre">${esc(t('al_server'))}</span>${sel}</span>`,
        d.signed_in
            ? `<span class="ai-chip" title="${esc(t('ai_gl_user'))}">${icon('user', 14)}<span class="glyph-centre">${esc(d.graylog_user)}</span></span>`
            : `<button class="btn-secondary btn-sm" data-act="aiShowSignin">${icon('login', 14)} ${esc(t('ai_signin_btn'))}</button>`];
    // one row: what answers | whose Graylog it reads; token use sits under the conversation
    // list (owner 2026-11-23: on a 1436 px window it wrapped to a second line of the bar)
    document.getElementById('ai-status').innerHTML =
        `<div class="ai-status-group">${left.join('')}</div><span class="ai-sep" aria-hidden="true"></span>`
        + `<div class="ai-status-group">${who.join('')}</div>`;
    const usage = document.getElementById('ai-usage');
    usage.title = t('ai_usage_tip');
    const mine = d.usage_mine || {day: 0, month: 0};
    usage.innerHTML = `${icon('report', 14)}<span class="ai-usage-lines"><span>${esc(t('ai_usage').replace('{d}', formatNumber(d.usage.day)).replace('{m}', formatNumber(d.usage.month)))}</span>`
        + `<span>${esc(t('ai_usage_mine').replace('{d}', formatNumber(mine.day)).replace('{m}', formatNumber(mine.month)))}</span></span>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
    const off = !s.enabled || !llms.length;
    document.getElementById('ai-send').disabled = off || _ai.busy;
    aiMsg('');
    aiNotice(off ? 'off' : (!d.signed_in ? 'signin' : ''));
    if (!document.getElementById('ai-settings').classList.contains('hidden')) aiRenderSettings(true);
}

// what stands between the user and a first question, shown above the box they type in
function aiNotice(kind) {
    const el = document.getElementById('ai-notice');
    if (!el) return;
    if (!kind) { el.classList.add('hidden'); el.innerHTML = ''; return; }
    el.innerHTML = kind === 'off'
        ? `${icon('warning', 16)}<span>${esc(t('ai_off_hint'))}</span><button class="btn-secondary btn-sm" data-act="aiToggleSettings">${icon('settings', 14)} ${esc(t('sec_btn_settings'))}</button>`
        : `${icon('lock', 16)}<span>${esc(t('ai_need_signin'))}</span><button class="btn-primary btn-sm" data-act="aiShowSignin">${icon('login', 14)} ${esc(t('ai_signin_btn'))}</button>`;
    el.classList.remove('hidden');
}

// The open incidents worth asking about first (highest severity, newest), as
// one-click examples on an empty conversation. Nothing when there are none.
async function _aiLoadIncidents() {
    const d = await fetchJSON(`${API}/security/incidents?status=open&limit=50`);
    const rank = {high: 0, medium: 1, low: 2};
    _ai.incidents = ((d && d.incidents) || []).slice()
        .sort((a, b) => (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3)).slice(0, 2);
}

function aiUseIncident(id) {
    const inp = document.getElementById('ai-input');
    inp.value = t('ai_prefill_incident').replace('{id}', id);
    inp.focus();
}

function aiUseExample(n) {
    const inp = document.getElementById('ai-input');
    inp.value = t('ai_ex' + n);
    inp.focus();
}

function aiServerChange(v) { _ai.server = v; aiLoadStatus(); }

function aiLlmChange(v) { _ai.llm = v; _aiPref('llm', v); aiLoadStatus(); }

// ---- the conversation list: fold it away, fold a group, pin (1.36) ----

function _aiApplySide() {
    const lay = document.getElementById('ai-layout');
    const btn = document.getElementById('ai-side-fold');
    if (!lay || !btn) return;
    lay.classList.toggle('ai-side-collapsed', _ai.sideCollapsed);
    const mini = lay.querySelector('.ai-new-mini');
    if (mini && !mini.firstChild) { mini.innerHTML = icon('plus', 16); mini.setAttribute('aria-label', t('ai_new_chat')); }
    btn.innerHTML = icon(_ai.sideCollapsed ? 'sidebar_expand' : 'sidebar_collapse', 16);
    const key = _ai.sideCollapsed ? 'ai_side_unfold' : 'ai_side_fold';
    btn.title = t(key);
    btn.setAttribute('aria-label', t(key));
    btn.setAttribute('aria-expanded', String(!_ai.sideCollapsed));
}

function aiToggleSide() {
    _ai.sideCollapsed = !_ai.sideCollapsed;
    _aiPref('side', _ai.sideCollapsed ? 'collapsed' : null);
    _aiApplySide();
}

function aiToggleGroup(g) {
    _ai.folded[g] = !_ai.folded[g];
    _aiPref('folded', JSON.stringify(_ai.folded));
    aiLoadConvs();
}

async function aiTogglePin(id, pin) {
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`, {method: 'PATCH',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pinned: !!pin})});
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    aiMsg('');
    aiLoadConvs();
}

function aiThinkPref(el) {
    _aiPref('think', el && el.checked ? null : 'fold');
    _ai.thinkOpen = null;
    _aiDrawPartial();
}

function aiShowSignin() {
    const el = document.getElementById('ai-signin');
    el.innerHTML = `<div class="ai-signin-row">
        <span>${esc(t('ai_signin_to').replace('{s}', _ai.server))}</span>
        <input type="text" id="ai-gl-user" autocomplete="username" placeholder="${esc(t('ai_username'))}">
        <div class="secret-field"><input type="password" id="ai-gl-pass" autocomplete="current-password" placeholder="${esc(t('ai_password'))}"><button type="button" class="secret-toggle" data-act="toggleSecret" data-act-self tabindex="-1">${icon('eye_closed')}</button></div>
        <button class="btn-primary btn-sm" data-act="aiSignin">${icon('login', 14)} ${esc(t('ai_signin_btn'))}</button>
    </div><div class="text-muted fs-08">${esc(t('ai_signin_note'))}</div>`;
    el.classList.remove('hidden');
}

async function aiSignin() {
    const d = await fetchJSON(`${API}/alerting/signin`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server: _ai.server, username: document.getElementById('ai-gl-user').value,
            password: document.getElementById('ai-gl-pass').value})});
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    document.getElementById('ai-signin').classList.add('hidden');
    await aiLoadStatus();
}

async function aiLoadConvs() {
    const q = (_ai.search || '').trim();
    const qs = new URLSearchParams({limit: String(_ai.convLimit)});
    if (q) qs.set('q', q);
    const d = await fetchJSON(`${API}/ai/conversations?${qs}`);
    if ((_ai.search || '').trim() !== q) return;   // typed on meanwhile; that search follows
    const el = document.getElementById('ai-convs');
    const items = (d && d.items) || [];
    if (!items.length) {
        el.innerHTML = `<div class="text-muted fs-08 ai-convs-empty">${esc(t(q ? 'ai_conv_none_found' : 'ai_no_convs'))}</div>`;
        return;
    }
    // pinned first, then today / yesterday / the week before / older; a group's header folds it
    const groups = [];
    for (const c of items) {
        const g = c.pinned_at ? 'pinned' : _aiGroup(c.updated_at);
        let grp = groups.find(x => x.g === g);
        if (!grp) { grp = {g, items: []}; groups.push(grp); }
        grp.items.push(c);
    }
    const maxPin = (_ai.status && _ai.status.max_pinned) || 5;
    const npinned = (groups.find(x => x.g === 'pinned') || {items: []}).items.length;
    const row = c => {
        const pinned = !!c.pinned_at;
        const pinKey = pinned ? 'ai_unpin' : (npinned >= maxPin ? 'ai_pin_full' : 'ai_pin');
        return `<div class="ai-conv ${_ai.conv && _ai.conv.id === c.id ? 'ai-conv-current' : ''} ${pinned ? 'ai-conv-pinned' : ''}">
        <button class="ai-conv-open" data-act="aiOpenConv" data-args="${esc(JSON.stringify([c.id]))}" title="${esc(c.title)}"><span class="ai-conv-title">${esc(c.title || '—')}</span><span class="text-muted fs-08">${c.running ? `<span class="ai-conv-running"><span class="ai-dot ai-dot-busy"></span>${esc(t('ai_conv_running'))}</span>` : `<span title="${esc(formatDT(c.updated_at))}">${esc(_aiShort(c.updated_at))}</span>`}</span></button>
        <button class="ai-conv-pin" data-act="aiTogglePin" data-args="${esc(JSON.stringify([c.id, !pinned]))}" title="${esc(t(pinKey).replace('{n}', maxPin))}" aria-label="${esc(t(pinKey).replace('{n}', maxPin))}" aria-pressed="${pinned}"${!pinned && npinned >= maxPin ? ' disabled' : ''}>${icon(pinned ? 'pin_off' : 'pin', 14)}</button>
        <button class="ai-conv-del" data-act="aiDeleteConv" data-args="${esc(JSON.stringify([c.id]))}" title="${esc(t('btn_delete'))}" aria-label="${esc(t('btn_delete'))}">${icon('trash', 14)}</button>
    </div>`;
    };
    el.innerHTML = groups.map(grp => {
        const open = !_ai.folded[grp.g] || (_ai.conv && grp.items.some(c => c.id === _ai.conv.id) && q);
        return `<button type="button" class="ai-conv-group${grp.g === 'pinned' ? ' ai-grp-pinned' : ''}" data-act="aiToggleGroup" data-arg="${grp.g}" aria-expanded="${open ? 'true' : 'false'}">${icon('chevron_down', 12)}<span>${esc(t('ai_grp_' + grp.g))}</span><span class="ai-grp-n">${grp.items.length}</span></button>`
            + (open ? grp.items.map(row).join('') : '');
    }).join('')
        // older conversations are read 50 more at a time
        + (d.more ? `<button type="button" class="btn-secondary btn-sm ai-conv-more" data-act="aiMoreConvs">${icon('chevron_down', 13)}<span>${esc(t('ai_conv_more'))}</span></button>` : '');
}

function aiMoreConvs() {
    _ai.convLimit = Math.min(1000, (_ai.convLimit || 50) + 50);
    aiLoadConvs();
}

// today / yesterday / the 7 days before / older, by the browser's own calendar
function _aiGroup(ts) {
    const d = _aiDate(ts);
    if (!d) return 'older';
    const day = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const days = Math.round((day(new Date()) - day(d)) / 86400000);
    return days <= 0 ? 'today' : days === 1 ? 'yesterday' : days <= 7 ? 'week' : 'older';
}

function aiSearchConvs(v) {
    _ai.search = v || '';
    clearTimeout(_ai.searchTimer);
    _ai.searchTimer = setTimeout(aiLoadConvs, 250);
}

// ---- the open conversation's header: title, rename, download ----

function aiRenderHead() {
    const el = document.getElementById('ai-head');
    if (!el) return;
    const c = _ai.conv;
    if (!c || !c.id) { el.classList.add('hidden'); el.innerHTML = ''; return; }
    const b = (act, ic, key) => `<button type="button" class="ai-act" data-act="${act}" title="${esc(t(key))}" aria-label="${esc(t(key))}">${icon(ic, 15)}</button>`;
    el.innerHTML = _ai.renaming
        ? `<input type="text" id="ai-rename" class="pk-input ai-rename" maxlength="200" value="${esc(c.title || '')}" aria-label="${esc(t('ai_rename'))}">
           <button type="button" class="btn-primary btn-sm" data-act="aiRenameSave">${icon('check', 14)} ${esc(t('btn_save'))}</button>
           <button type="button" class="btn-secondary btn-sm" data-act="aiRenameCancel">${esc(t('btn_cancel'))}</button>`
        : `<span class="ai-head-title" title="${esc(c.title || '')}">${esc(c.title || '—')}</span>
           ${c.server ? `<span class="ai-head-server" title="${esc(t('al_server'))}">${icon('server', 12)}${esc(c.server)}</span>` : ''}
           <span class="ai-head-acts">${b('aiRenameStart', 'edit', 'ai_rename')}${b('aiExportConv', 'download', 'ai_export')}${(c.messages || []).some(m => m.role === 'assistant' && m.id) ? b('aiSummaryDialog', 'page', 'ai_summary_btn') + b('aiCaseDialog', 'log', 'ai_case_btn') : ''}</span>`;
    el.classList.remove('hidden');
    const inp = document.getElementById('ai-rename');
    if (inp) {
        inp.focus();
        inp.select();
        inp.addEventListener('keydown', e => {
            if (e.key === 'Enter') { e.preventDefault(); aiRenameSave(); }
            else if (e.key === 'Escape') { e.preventDefault(); aiRenameCancel(); }
        });
    }
}

function aiRenameStart() { _ai.renaming = true; aiRenderHead(); }
function aiRenameCancel() { _ai.renaming = false; aiRenderHead(); }

async function aiRenameSave() {
    const c = _ai.conv;
    const inp = document.getElementById('ai-rename');
    if (!c || !c.id || !inp) return;
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(c.id)}`, {method: 'PATCH',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({title: inp.value})});
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    if (_ai.conv && _ai.conv.id === c.id) _ai.conv.title = d.title;
    _ai.renaming = false;
    aiMsg('');
    aiRenderHead();
    aiLoadConvs();
}

// The conversation as a Markdown file, built here from what the page shows
function aiConvMarkdown(c) {
    const C = t('sec_colon');
    const cell = v => String(v ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
    const lines = [`# ${(c.title || '—').replace(/\n/g, ' ')}`, ''];
    if (c.server) lines.push(`- Graylog${C}${c.server}`);
    lines.push(`- ${t('ai_md_exported').replace('{t}', formatDT(new Date().toISOString()))}`, '');
    for (const m of c.messages || []) {
        if (m.role === 'user') {
            lines.push(`## ${t('ai_md_question')} · ${formatDT(m.created_at)}`, '', m.content || '', '');
            continue;
        }
        const meta = [formatDT(m.created_at), m.model, m.tokens ? t('ai_tokens').replace('{n}', formatNumber(m.tokens)) : '',
            m.elapsed_ms ? `${(m.elapsed_ms / 1000).toFixed(1)} s` : ''].filter(Boolean).join(' · ');
        lines.push(`## ${t('ai_md_answer')} · ${meta}`, '', _aiDemote(m.content || ''), '');
        if (m.truncated) lines.push(`> ${t('ai_truncated')}`, '');
        if ((m.calls || []).length) {
            lines.push(`### ${t('ai_calls_title')}`, '',
                `| # | ${t('ai_md_tool')} | ${t('ai_md_query')} | ${t('ai_md_range')} | ${t('ai_md_result')} |`,
                '|---|---|---|---|---|');
            m.calls.forEach((x, k) => {
                const rng = x.range ? `${x.range.from} – ${x.range.to}` : '';
                lines.push(`| ${k + 1} | ${cell(x.name)} | ${x.query !== undefined ? '`' + cell(x.query || '*').replace(/`/g, "'") + '`' : ''} | ${cell(rng)} | ${cell(_aiCallResult(x))} |`);
            });
            lines.push('');
        }
    }
    return lines.join('\n') + '\n';
}

// the answer's own headings go under "## Answer" (### and below), code blocks untouched
function _aiDemote(md) {
    let fence = false;
    return md.split('\n').map(ln => {
        if (/^```/.test(ln)) fence = !fence;
        return !fence && /^#{1,4}\s/.test(ln) ? '##' + ln : ln;
    }).join('\n');
}

function aiExportConv() {
    const c = _ai.conv;
    if (!c || !c.id) return;
    const blob = new Blob([aiConvMarkdown(c)], {type: 'text/markdown;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `jt-glogarch-chat-${c.id}.md`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

async function aiOpenConv(id, keepMsg) {
    if (_ai.abort && _ai.conv && _ai.conv.id !== id) { _ai.detached = true; _ai.abort.abort(); }
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`);
    if (!d || d.error) {
        aiMsg(d && d.error, 'err');
        if (!_ai.abort) _aiBusy(false);   // a stream left for this conversation must not leave the page busy
        return;
    }
    const live = _ai.abort && _ai.conv && _ai.conv.id === id;   // reopened while its own stream runs
    if (!_ai.conv || _ai.conv.id !== id) aiClosePreview();
    _ai.conv = d;
    _ai.renaming = false;
    if (!keepMsg) aiMsg('');
    aiRenderThread();
    aiLoadConvs();
    _aiLanded();
    if (!live) _aiFollow(d);   // the stream delivers the answer; a poll as well would show it twice
}

// A question still being answered (on the server; the page may have been left
// and come back): show its progress and pick the answer up when it lands.
function _aiFollow(d) {
    clearTimeout(_ai.poll);
    const run = d && d.run;
    if (!run || !run.running) {
        if (!_ai.abort) {
            const was = _ai.busy;
            _aiBusy(false);
            if (was && _aiUnanswered()) aiRenderThread();
        }
        if (run && run.error === 'Stopped') aiMsg(t('ai_stopped'), 'ok');
        else if (run && run.error && !_aiHasAnswerAfterLastQuestion(d)) aiMsg(t('ai_failed') + jobNote(run.error), 'err');
        return;
    }
    if (_ai.pvWatch !== d.id) { _ai.pvWatch = d.id; _ai.pvDismissed = false; }
    _aiBusy(true, run.started_at ? run.started_at * 1000 : undefined);
    _aiProgress(run.progress && run.progress.phase ? run.progress : {phase: 'thinking', round: 1});
    if (run.reasoning !== undefined) _ai.reasoning = run.reasoning || '';
    if (run.partial !== undefined) _aiSetPartial(run.partial);
    const id = d.id;
    _ai.poll = setTimeout(async () => {
        if (!_ai.conv || _ai.conv.id !== id) return;
        const n = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`);
        if (!_ai.conv || _ai.conv.id !== id) return;
        if (!n || n.error) {
            if (n && n.error && /not found/i.test(n.error)) { _aiBusy(false); return; }   // deleted meanwhile
            _aiFollow(_ai.conv);   // a failed poll (network blip, 502): try again, do not stop following
            return;
        }
        if (!n.run || !n.run.running) { _ai.conv = n; aiRenderThread(); aiLoadConvs(); aiLoadStatus(); _aiLanded(); }
        _aiFollow(n);
    }, ((run.progress || {}).phase === 'writing' || run.reasoning) ? 1000 : 2000);   // text arriving: smoother at 1 s
}

function _aiHasAnswerAfterLastQuestion(d) {
    const m = (d.messages || []);
    return m.length && m[m.length - 1].role === 'assistant';
}

function aiDeleteConv(id) {
    showConfirm(t('ai_delete_title'), t('ai_delete_msg'), async () => {
        await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`, {method: 'DELETE'});
        if (_ai.conv && _ai.conv.id === id) {
            if (_ai.abort) { _ai.detached = true; _ai.abort.abort(); }
            _ai.conv = null;
            _aiBusy(false);   // the server stopped it; nothing left to follow
        }
        aiRenderThread();
        aiLoadConvs();
    });
}

function aiNewChat() {
    if (_ai.abort) { _ai.detached = true; _ai.abort.abort(); }   // the answer goes on; it is in the list
    clearTimeout(_ai.poll);
    _ai.conv = null; _ai.renaming = false; aiMsg(''); _aiBusy(false); aiClosePreview();
    aiRenderThread(); aiLoadConvs(); document.getElementById('ai-input').focus();
}

// "HH:MM" today, "MM-DD HH:MM" this year, else the full date; the whole time on hover
function _aiDate(ts) {
    if (!ts) return null;
    const d = new Date(/Z$|[+-]\d\d:?\d\d$/.test(ts) ? ts : ts + 'Z');
    return isNaN(d) ? null : d;
}

function _aiShort(ts) {
    const d = _aiDate(ts);
    if (!d) return '';
    const p = n => String(n).padStart(2, '0');
    const now = new Date();
    const hm = `${p(d.getHours())}:${p(d.getMinutes())}`;
    return d.toDateString() === now.toDateString() ? hm
        : (d.getFullYear() === now.getFullYear() ? `${p(d.getMonth() + 1)}-${p(d.getDate())} ${hm}`
            : `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${hm}`);
}

function _aiTime(ts) {
    const d = _aiDate(ts);
    if (!d) return '';
    return `<time class="ai-time" datetime="${esc(d.toISOString())}" title="${esc(formatDT(ts))}">${esc(_aiShort(ts))}</time>`;
}

function _aiMeta(m, i) {
    const bits = [];
    if (m.model) bits.push(`<span class="ai-meta-item ai-meta-model" title="${esc(t('ai_model'))}${esc(t('sec_colon'))}${esc(m.model)}">${icon('server', 12)}<span>${esc(m.model)}</span></span>`);
    if (m.elapsed_ms) bits.push(`<span class="ai-meta-item" title="${esc(t('ai_meta_elapsed'))}">${icon('clock', 12)}<span>${esc((m.elapsed_ms / 1000).toFixed(1))} s</span></span>`);
    if (m.tokens) bits.push(`<span class="ai-meta-item" title="${esc(t('ai_meta_tokens'))}">${icon('report', 12)}<span>${esc(t('ai_tokens').replace('{n}', formatNumber(m.tokens)))}</span></span>`);
    const tools = [...new Set(m.tools || [])];
    if ((m.calls || []).length) {
        // the queries themselves, one click away (answers made before they were kept show tool names only)
        bits.push(`<button type="button" class="ai-meta-item ai-calls-toggle" data-act="aiToggleCalls" data-act-event data-arg="${i}" aria-expanded="false" title="${esc(t('ai_calls_title'))}">${icon('search', 12)}<span>${esc(t('ai_calls_n').replace('{n}', m.calls.length))}</span>${icon('chevron_down', 12)}</button>`);
    } else if (tools.length) {
        bits.push(`<span class="ai-meta-item" title="${esc(tools.join('\n'))}">${icon('settings', 12)}<span>${esc(t('ai_meta_tools').replace('{n}', tools.length))}</span></span>`);
    }
    return bits.length ? `<span class="ai-meta">${bits.join('')}</span>` : '';
}

function _aiCallResult(x) {
    if (!x.ok) return t('ai_call_failed') + (x.error ? `${t('sec_colon')}${x.error}` : '');
    if (typeof x.count === 'number') return t('ai_call_count').replace('{n}', formatNumber(x.count));
    if (typeof x.rows === 'number') return t('ai_call_rows').replace('{n}', formatNumber(x.rows));
    return '';
}

// "11/20 14:00 – 11/21 14:00" in the reader's time; the UTC values on hover
function _aiRange(r) {
    if (!r || !r.from || !r.to) return '';
    return `<span class="ai-call-range" title="${esc(r.from + ' – ' + r.to)}">${icon('clock', 12)}${esc(_aiShort(r.from))} – ${esc(_aiShort(r.to))}</span>`;
}

function _aiCalls(i, m) {
    const rows = (m.calls || []).map((x, k) => {
        const other = Object.entries(x.args || {}).filter(([a]) => !['query', 'range_from', 'range_to'].includes(a))
            .map(([a, v]) => `<span class="ai-call-arg">${esc(a)}=${esc(typeof v === 'string' ? v : JSON.stringify(v))}</span>`).join('');
        const link = /^https?:\/\//.test(x.graylog_url || '')
            ? `<a class="btn-secondary btn-sm ai-call-open" href="${esc(x.graylog_url)}" target="_blank" rel="noopener noreferrer">${icon('search', 13)}<span>${esc(t('ai_call_open'))}</span></a>` : '';
        const res = _aiCallResult(x);
        return `<li class="ai-call ${x.ok ? '' : 'ai-call-err'}">
            <div class="ai-call-line"><span class="ai-call-n">${k + 1}</span>${aiToolName(x.name)} <code class="ai-call-tool">${esc(x.name)}</code>
                ${res ? `<span class="ai-call-res">${x.ok ? '' : icon('warning', 12)}${esc(res)}</span>` : ''}
                ${typeof x.ms === 'number' ? `<span class="ai-call-ms" title="${esc(t('ai_tool_elapsed_tip'))}">${icon('clock', 12)}${esc(_aiSecs(x.ms))}</span>` : ''}
                ${_aiRange(x.range)}${link}</div>
            ${x.query !== undefined ? `<div class="ai-call-qrow"><code class="ai-call-q">${esc(x.query || '*')}</code><button type="button" class="ai-act ai-call-copy" data-act="aiCopyQuery" data-act-event data-args="${esc(JSON.stringify([i, k]))}" title="${esc(t('ai_act_copy_query'))}" aria-label="${esc(t('ai_act_copy_query'))}">${icon('copy', 14)}</button></div>` : ''}
            ${other ? `<div class="ai-call-args">${other}</div>` : ''}
        </li>`;
    }).join('');
    return `<div class="ai-calls hidden" id="ai-calls-${i}"><div class="ai-calls-note">${icon('info', 14)}<span>${esc(t('ai_calls_note'))}</span></div><ol class="ai-call-list">${rows}</ol></div>`;
}

function aiCopyQuery(e) {
    const btn = e && e.target && e.target.closest('[data-act]');
    if (!btn) return;
    const [i, k] = JSON.parse(btn.dataset.args || '[]');
    const m = ((_ai.conv && _ai.conv.messages) || [])[i];
    const x = m && (m.calls || [])[k];
    if (x) _aiClip(x.query || '*', btn);
}

function aiToggleCalls(e) {
    const {btn, i} = _aiMsgOf(e);
    const el = document.getElementById('ai-calls-' + i);
    if (!el || !btn) return;
    const open = el.classList.toggle('hidden') === false;
    btn.setAttribute('aria-expanded', String(open));
    btn.classList.toggle('ai-calls-open', open);
    if (open) _aiScrollToTop(btn);
}

// Opened the query list: bring its button to the top of the thread so the list
// reads downward from there (owner 2026-11-25: "捲到 18次查詢 剛好在畫面可視最上面").
// Near the end of the thread it stops where the thread ends.
const AI_SCROLL_MARGIN = 8;
function _aiScrollToTop(el) {
    const th = document.getElementById('ai-thread');
    if (!th || !el) return;
    const top = th.scrollTop + el.getBoundingClientRect().top - th.getBoundingClientRect().top - AI_SCROLL_MARGIN;
    const smooth = !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    th.scrollTo({top: Math.max(0, top), behavior: smooth ? 'smooth' : 'auto'});
}

function _aiActions(i, m) {
    const b = (act, ic, key) => `<button type="button" class="ai-act" data-act="${act}" data-act-event data-arg="${i}" title="${esc(t(key))}" aria-label="${esc(t(key))}">${icon(ic, 14)}</button>`;
    return `<span class="ai-actions">${m.role === 'user'
        ? b('aiCopyMsg', 'copy', 'ai_act_copy') + b('aiEditMsg', 'edit', 'ai_act_edit')
        : b('aiCopyMsg', 'copy', 'ai_act_copy') + b('aiRetryMsg', 'refresh', 'ai_act_retry')
          + (m.id && typeof aixChartable === 'function' && aixChartable(m) ? b('aiDashboardDialog', 'view_grid', 'ai_act_dashboard') : '')}</span>`;
}

// the last question has no answer and nothing is working on it (a restart, a failure)
function _aiUnanswered() {
    const c = _ai.conv;
    const msgs = (c && c.messages) || [];
    return !!(c && c.id && msgs.length && msgs[msgs.length - 1].role === 'user' && !_ai.busy
        && !(c.run && c.run.running));
}

// Questions the model suggests asking next, under the LAST answer only (an older
// answer's suggestions no longer follow from where the conversation is). One click
// asks it. They are model text: escaped like everything else.
function _aiFollowups(m) {
    const qs = (m.followups || []).filter(q => typeof q === 'string' && q.trim());
    // no busy check: the done event renders while the page is still marked busy, and a new
    // question is pushed before any render, so the last message is then the user's
    if (!qs.length) return '';
    return `<div class="ai-fus"><span class="ai-fus-h">${esc(t('ai_followups'))}</span>${qs.map((q, k) =>
        `<button type="button" class="ai-fu" data-act="aiAskFollowup" data-arg="${k}" title="${esc(t('ai_followup_title'))}">${icon('chat', 14)}<span>${esc(q)}</span></button>`).join('')}</div>`;
}

function aiAskFollowup(k) {
    const msgs = (_ai.conv && _ai.conv.messages) || [];
    const last = msgs[msgs.length - 1];
    const q = last && last.role === 'assistant' && (last.followups || [])[Number(k)];
    if (!q || _ai.busy) return;
    document.getElementById('ai-input').value = q;
    aiSend();
}

function aiRenderThread() {
    aiRenderHead();
    if (!_ai.busy) _ai.partial = '';
    const el = document.getElementById('ai-thread');
    const msgs = (_ai.conv && _ai.conv.messages) || [];
    if (!msgs.length) {
        const det = i => typeof secDetTitle === 'function' ? secDetTitle(i.detector, i.detector_title) : i.detector;
        const inc = (_ai.incidents || []).map(i => `<button type="button" class="ai-ex ai-ex-inc" data-act="aiUseIncident" data-arg="${esc(String(i.id))}">${icon('shield', 14)}<span>${esc(t('ai_ex_incident').replace('{id}', i.id).replace('{d}', det(i)).replace('{e}', i.entity || '—'))}</span><span class="sec-sev sec-sev-${esc(i.severity)}">${esc(t('sec_sev_' + i.severity))}</span></button>`).join('');
        const ex = inc + [1, 2, 3].map(n => `<button type="button" class="ai-ex" data-act="aiUseExample" data-arg="${n}">${icon('chat', 14)}<span>${esc(t('ai_ex' + n))}</span></button>`).join('');
        el.innerHTML = `<div class="ai-empty"><div class="ai-empty-icon">${icon('chat', 26)}</div>
            <p class="ai-empty-h">${esc(t('ai_empty'))}</p><div class="ai-exs">${ex}</div>
            <p class="ai-disclaimer">${esc(t('ai_disclaimer'))}</p></div>`;
        return;
    }
    // a question the user stopped and that never got an answer (owner 2026-11-27)
    const stopped = i => msgs[i].stopped_at && !(msgs[i + 1] && msgs[i + 1].role === 'assistant');
    el.innerHTML = msgs.map((m, i) => m.role === 'user'
        ? `<div class="ai-msg ai-msg-user"><div class="ai-bubble ai-user">${esc(m.content).replace(/\n/g, '<br>')}</div>
            <div class="ai-foot">${stopped(i) ? `<span class="ai-q-stopped">${icon('close', 12)}${esc(t('ai_q_stopped'))}</span>` : ''}${_aiActions(i, m)}${_aiTime(m.created_at)}</div></div>`
        : `<div class="ai-msg ai-msg-bot" data-mid="${esc(String(m.id || ''))}"><div class="ai-bubble ai-bot">${aiMarkdown(m.content)}${m.truncated
            ? `<div class="ai-truncated">${icon('warning', 14)}<span>${esc(t('ai_truncated'))}</span></div>` : ''}</div>
            <div class="ai-foot">${_aiTime(m.created_at)}${_aiMeta(m, i)}${_aiActions(i, m)}</div>${(m.calls || []).length ? _aiCalls(i, m) : ''}${i === msgs.length - 1 ? _aiFollowups(m) : ''}</div>`).join('')
        + (_aiUnanswered() ? `<div class="ai-unanswered">${icon('warning', 16)}<span>${esc(t(stopped(msgs.length - 1) ? 'ai_unanswered_stopped' : 'ai_unanswered'))}</span>
            <button type="button" class="btn-primary btn-sm" data-act="aiAnswerAgain">${icon('refresh', 14)} ${esc(t('ai_answer_now'))}</button></div>` : '');
    _aiDecorateBlocks(el);
    if (typeof aiTimelineDecorate === 'function') aiTimelineDecorate(el);
    el.scrollTop = el.scrollHeight;
    if (_ai.busy && (_ai.partial || _ai.reasoning)) _aiDrawPartial();
}


// Code blocks and tables in the answers: a copy button; code blocks also get a bar with
// what they are, Preview (a page, diagram or SVG; needs the stored id) and fold / unfold.
// A long block starts folded (owner 2026-11-27: "不一定要全顯示"); the reader's choice is kept.
const AI_CODE_FOLD_LINES = 15;
function _aiDecorateBlocks(el) {
    el.querySelectorAll('.ai-bot pre.ai-code, .ai-bot .table-wrap').forEach(blk => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'ai-act ai-block-copy';
        btn.title = t(blk.matches('pre') ? 'ai_act_copy_code' : 'ai_act_copy_table');
        btn.setAttribute('aria-label', btn.title);
        btn.innerHTML = icon('copy', 14);
        btn.addEventListener('click', () => _aiCopyBlock(blk, btn));
        const box = document.createElement('div');
        box.className = 'ai-block';
        blk.parentNode.insertBefore(box, blk);
        box.appendChild(blk);
        box.appendChild(btn);
    });
    el.querySelectorAll('.ai-msg-bot[data-mid]').forEach(msg => {
        const mid = msg.dataset.mid;
        let n = 0;
        msg.querySelectorAll('pre.ai-code').forEach((pre, idx) => {
            const lang = pre.dataset.lang || '';
            const kind = lang === 'md' ? 'markdown' : lang;
            const previewable = !!mid && ['html', 'mermaid', 'svg', 'markdown'].includes(kind);
            const k = previewable ? n++ : -1;
            const box = pre.parentNode.classList.contains('ai-block') ? pre.parentNode : pre;
            const lines = (pre.textContent.match(/\n/g) || []).length + 1;
            const key = `${mid}:${idx}`;
            // a bar above the block (never over the code)
            const bar = document.createElement('div');
            bar.className = 'ai-block-bar';
            bar.innerHTML = `<span class="ai-block-lang">${esc((lang || t('ai_code')).toUpperCase())}</span>`;
            if (previewable) {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'btn-secondary btn-sm ai-preview-btn';
                b.innerHTML = `${icon('eye', 13)}<span class="glyph-centre">${esc(t('ai_preview'))}</span>`;
                b.title = t('ai_preview_tip');
                b.addEventListener('click', () => { _ai.pvDismissed = false; aiOpenPreview(mid, k, kind); });
                bar.appendChild(b);
            }
            if (lines > AI_CODE_FOLD_LINES) {
                const f = document.createElement('button');
                f.type = 'button';
                f.className = 'btn-secondary btn-sm ai-fold-btn';
                const draw = () => {
                    const folded = box.classList.contains('ai-folded');
                    f.innerHTML = `${icon(folded ? 'expand' : 'collapse', 13)}<span class="glyph-centre">${esc(folded
                        ? t('ai_code_unfold').replace('{n}', formatNumber(lines)) : t('ai_code_fold'))}</span>`;
                };
                if (!_ai.codeOpen[key]) box.classList.add('ai-folded');
                draw();
                f.addEventListener('click', () => {
                    const open = box.classList.toggle('ai-folded') === false;
                    _ai.codeOpen[key] = open;
                    draw();
                });
                bar.appendChild(f);
            }
            box.classList.add('ai-block-has-bar');
            box.parentNode.insertBefore(bar, box);
        });
    });
}

// ---- message actions ----

async function _aiClip(text, btn) {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; } catch (_) {
        const ta = document.createElement('textarea');
        ta.value = text; ta.setAttribute('readonly', ''); ta.className = 'ai-clip';
        document.body.appendChild(ta); ta.select();
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        ta.remove();
    }
    if (btn) {
        const prev = btn.innerHTML;
        btn.innerHTML = icon(ok ? 'check' : 'warning', 14);
        btn.classList.add(ok ? 'ai-act-ok' : 'ai-act-err');
        setTimeout(() => { btn.innerHTML = prev; btn.classList.remove('ai-act-ok', 'ai-act-err'); }, 1400);
    }
}

function _aiCopyBlock(blk, btn) {
    if (blk.matches('pre')) { _aiClip(blk.innerText, btn); return; }
    // a table goes out tab-separated: it pastes into a spreadsheet as cells
    const rows = [...blk.querySelectorAll('tr')].map(tr => [...tr.children].map(c => c.innerText.trim()).join('\t'));
    _aiClip(rows.join('\n'), btn);
}

// the action buttons pass the click event (data-act-event): the button holds the index
function _aiMsgOf(e) {
    const btn = e && e.target && e.target.closest('[data-act]');
    return {btn, i: btn ? Number(btn.dataset.arg) : -1, m: btn ? ((_ai.conv && _ai.conv.messages) || [])[Number(btn.dataset.arg)] : null};
}

function aiCopyMsg(e) {
    const {btn, m} = _aiMsgOf(e);
    if (m) _aiClip(m.content, btn);
}

function aiEditMsg(e) {
    const {m} = _aiMsgOf(e);
    if (!m) return;
    const inp = document.getElementById('ai-input');
    inp.value = m.content;
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
}

// ask the question before this answer again (a new answer is added; the old one stays)
function aiRetryMsg(e) {
    if (_ai.busy) return;
    const {i} = _aiMsgOf(e);
    const msgs = (_ai.conv && _ai.conv.messages) || [];
    for (let k = i - 1; k >= 0; k--) {
        if (msgs[k].role === 'user') { document.getElementById('ai-input').value = msgs[k].content; aiSend(); return; }
    }
}

// ---- the answer as it is written (streamed) ----

function _aiSetPartial(text) {
    _ai.partial = text || '';
    _aiScheduleDraw();
}

// the model's reasoning as it is written (owner 2026-11-23: text the model writes shows at once;
// a reasoning model can think for minutes before the first word of the answer)
function _aiSetReasoning(text) {
    _ai.reasoning = text || '';
    _aiScheduleDraw();
}

function _aiScheduleDraw() {
    if (_ai.partialTimer) return;
    _ai.partialTimer = setTimeout(() => { _ai.partialTimer = null; _aiDrawPartial(); }, 120);
}

function _aiDrawPartial() {
    const th = document.getElementById('ai-thread');
    if (!th) return;
    let box = document.getElementById('ai-partial');
    if (!(_ai.partial || _ai.reasoning) || !_ai.busy) { if (box) box.remove(); return; }
    const atEnd = th.scrollHeight - th.scrollTop - th.clientHeight < 80;
    if (!box) {
        box = document.createElement('div');
        box.id = 'ai-partial';
        box.className = 'ai-msg ai-msg-bot ai-partial';
        th.querySelectorAll('.ai-unanswered').forEach(x => x.remove());
        th.appendChild(box);
    }
    // open while the model only thinks, folded once the answer starts, unless the reader chose
    const show = _aiPref('think') !== 'fold';   // the switch under the box (1.36)
    const open = _ai.thinkOpen === null ? (show && !_ai.partial) : _ai.thinkOpen;
    const n = t('ai_think_chars').replace('{n}', formatNumber(_ai.reasoning.length));
    box.innerHTML = (_ai.reasoning ? `<details class="ai-think"${open ? ' open' : ''}><summary>${icon('chat', 13)}<span>${esc(t('ai_think_title'))}</span><span class="ai-think-n">${esc(n)}</span>${icon('chevron_down', 13)}</summary><div class="ai-think-text">${esc(_ai.reasoning)}</div></details>` : '')
        + (_ai.partial ? `<div class="ai-bubble ai-bot">${aiMarkdown(_ai.partial)}</div>` : '');
    const det = box.querySelector('.ai-think');
    // only the reader's click counts: a details element drawn open fires 'toggle' by itself
    if (det) det.querySelector('summary').addEventListener('click', () => { _ai.thinkOpen = !det.open; });
    const txt = box.querySelector('.ai-think-text');
    if (txt) txt.scrollTop = txt.scrollHeight;
    // the caret at the end of the last line written, not on a line of its own
    const bub = box.querySelector('.ai-bubble') || txt;
    const caret = document.createElement('span');
    caret.className = 'ai-caret';
    caret.setAttribute('aria-hidden', 'true');
    (_ai.partial ? ([...bub.querySelectorAll('p, li, h3, h4, h5, td, pre code')].pop() || bub) : bub).appendChild(caret);
    // a block being written stays a few lines tall and shows its newest lines
    box.querySelectorAll('pre.ai-code').forEach(pre => { pre.scrollTop = pre.scrollHeight; });
    if (atEnd) th.scrollTop = th.scrollHeight;
    _aiLivePreview();
}

// A page / diagram being written opens in the preview pane on its own and follows the
// text (owner 2026-11-27: "已經可以預覽時就開始打開預覽 內容如有更新也要即時更新").
// A page shows as far as it got; a diagram or SVG only once its block is closed (half
// a diagram is a syntax error). Closing the pane stops it for this answer.
const AI_PV_OPEN = /```[ \t]*(html|mermaid|svg|markdown|md)[ \t]*\n/gi;
const AI_PV_REFRESH_MS = 3000;
function _aiLivePreview() {
    if (!_ai.busy || _ai.pvDismissed || !_ai.conv || !_ai.conv.id) return;
    const txt = _ai.partial || '';
    const found = [...txt.matchAll(AI_PV_OPEN)];
    if (!found.length) return;
    const n = found.length - 1;
    const last = found[n];
    const kind = last[1].toLowerCase() === 'md' ? 'markdown' : last[1].toLowerCase();
    const body = txt.slice(last.index + last[0].length);
    const closed = /\n```/.test(body);
    if (body.length < 40 || (kind !== 'html' && !closed)) return;
    const sig = `${n}:${closed ? 'end' : body.length}`;
    const p = _ai.preview;
    if (!p || !p.live || p.n !== n || p.mid !== _ai.conv.id) {
        aiOpenPreview(_ai.conv.id, n, kind, true);
    } else if (sig !== _ai.pvSig && (closed || Date.now() - _ai.pvAt >= AI_PV_REFRESH_MS)) {
        _aiReloadPreview();
    } else return;
    _ai.pvSig = sig;
    _ai.pvAt = Date.now();
}

// the newer page loads behind the one on screen and replaces it once it has drawn
function _aiReloadPreview() {
    const pane = document.getElementById('ai-preview');
    const old = pane && pane.querySelector('.ai-pv-frames iframe:not(.ai-pv-next)');
    if (!old || !_ai.preview) return;
    pane.querySelectorAll('.ai-pv-next').forEach(x => x.remove());
    const fr = old.cloneNode(false);
    fr.classList.add('ai-pv-next');
    fr.addEventListener('load', () => { old.remove(); fr.classList.remove('ai-pv-next'); }, {once: true});
    fr.src = `${_aiPreviewUrl(_ai.preview)}&t=${Date.now()}`;
    old.after(fr);
}

function _aiProgress(ev) {
    const el = document.getElementById('ai-progress');
    let text = '';
    if (ev.phase === 'reasoning') {   // the phase line (round, tool) stays as it is
        _aiSetReasoning(ev.reset ? ev.text : (_ai.reasoning || '') + (ev.delta || ''));
        return;
    }
    if (ev.phase === 'answer') {
        _aiSetPartial(ev.reset ? ev.text : (_ai.partial || '') + (ev.delta || ''));
        text = t('ai_ph_writing');
    } else if (ev.phase === 'writing') text = t('ai_ph_writing');
    else if (ev.phase === 'thinking') text = t('ai_ph_thinking').replace('{n}', ev.round);
    else if (ev.phase === 'tool') {
        const a = ev.args || {};
        const brief = ['query', 'field', 'range_from'].filter(k => a[k]).map(k => `${k}=${a[k]}`).join(' ');
        text = t('ai_ph_tool').replace('{t}', ev.name) + (brief ? ` (${brief})` : '');
        _ai.toolStart = Date.now();          // this lookup's own clock, beside the answer's
    } else if (ev.phase === 'tool_done') {
        // what the lookup took, kept in a line under the progress until the answer is done
        _ai.toolStart = 0;
        _ai.toolsDone.push(ev);
        _aiDrawToolsDone();
        return;
    } else if (ev.phase === 'composing') text = t('ai_ph_composing');
    else if (ev.phase === 'continuing') text = t('ai_ph_continuing');
    else if (ev.phase === 'waiting_model') text = t('ai_ph_waiting_model');
    else if (ev.phase === 'loop_retry') text = t('ai_ph_loop_retry');
    else if (ev.phase === 'model') {
        // which model answers and how much it can take: the budget comes from this
        text = t('ai_ph_model').replace('{m}', ev.llm || '').replace('{n}', formatNumber(ev.context || 0));
    }
    if (ev.phase !== 'tool') _ai.toolStart = 0;
    el.innerHTML = `<span class="spinner-text">${esc(text)}</span>`
        + (_ai.toolStart ? `<span class="ai-tool-elapsed" id="ai-tool-elapsed" title="${esc(t('ai_tool_elapsed_tip'))}">${_aiToolElapsed()}</span>` : '')
        + `<span class="ai-elapsed" id="ai-elapsed" title="${esc(t('ai_meta_elapsed'))}">${_aiElapsed()}</span>`
        + `<div class="ai-tools-done" id="ai-tools-done"></div>`;
    el.classList.remove('hidden');
    _aiDrawToolsDone();
}

function _aiSecs(ms) {
    return ms >= 60000 ? `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}` : `${(ms / 1000).toFixed(1)} s`;
}

function _aiToolElapsed() {
    return _ai.toolStart ? _aiSecs(Date.now() - _ai.toolStart) : '';
}

// a tool by a name people read, the tool's own name and where it gets its data in the tooltip
// (owner 2026-11-27 asked whether these were Graylog API calls or our own tools)
const AI_OWN_TOOLS = new Set(["aggregate", "count_messages", "top_values", "sample_messages", "summarize_messages", "read_result", "archive_status", "list_security_incidents", "get_security_incident", "list_security_cases", "get_security_case", "security_risk_ranking"]);
function aiToolName(name) {
    const k = 'ai_tn_' + name, label = t(k) !== k ? t(k) : name;
    const src = t(AI_OWN_TOOLS.has(name) ? 'ai_tool_src_own' : 'ai_tool_src_mcpg');
    return `<span class="ai-tool-name" title="${esc(name + ' · ' + src)}">${esc(label)}</span>`;
}

// the lookups of this answer so far, each with its time ("aggregate 1.2 s · count_messages 0.3 s")
function _aiDrawToolsDone() {
    const el = document.getElementById('ai-tools-done');
    if (!el) return;
    const done = _ai.toolsDone || [];
    el.innerHTML = done.length ? done.map(d => {
        const res = typeof d.count === 'number' ? t('ai_call_count').replace('{n}', formatNumber(d.count))
            : typeof d.rows === 'number' ? t('ai_call_rows').replace('{n}', formatNumber(d.rows)) : '';
        // one grid row per lookup: icon | tool | time | result, so the columns line up
        return `<span class="ai-tool-done${d.ok ? '' : ' ai-tool-err'}">${icon(d.ok ? 'check' : 'warning', 12)}${aiToolName(d.name)}`
            + `<span class="ai-td-ms" title="${esc(t('ai_tool_took').replace('{s}', _aiSecs(d.ms || 0)))}">${esc(_aiSecs(d.ms || 0))}</span><span class="ai-td-res">${esc(res)}</span></span>`;
    }).join('') : '';
}

// how long this answer has been running (m:ss): a reasoning model can think for a minute or more
function _aiElapsed() {
    if (!_ai.started) return '';
    const sec = Math.max(0, Math.floor((Date.now() - _ai.started) / 1000));
    return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`;
}

function _aiTick() {
    const el = document.getElementById('ai-elapsed');
    if (el) el.textContent = _aiElapsed();
    const te = document.getElementById('ai-tool-elapsed');
    if (te) te.textContent = _aiToolElapsed();
}

function _aiBusy(on, since) {
    _ai.busy = on;
    clearInterval(_ai.ticker);
    if (on) {
        _ai.started = typeof since === 'number' ? since : (_ai.started || Date.now());
        _ai.ticker = setInterval(_aiTick, 1000);
    } else _ai.started = 0;
    if (!on) { clearTimeout(_ai.poll); _ai.partial = ''; _ai.reasoning = ''; _ai.thinkOpen = null; _ai.toolStart = 0; _ai.toolsDone = []; _aiDrawPartial(); }
    document.getElementById('ai-send').disabled = on;
    document.getElementById('ai-stop').classList.toggle('hidden', !on);
    if (!on) document.getElementById('ai-progress').classList.add('hidden');
}

// answer the conversation's last question, which has none (it is not stored again)
function aiAnswerAgain() { aiSend(true); }

async function aiSend(retry) {
    if (_ai.busy) return;
    retry = retry === true;
    const inp = document.getElementById('ai-input');
    const q = retry ? '' : inp.value.trim();
    if (!q && !retry) return;
    if (retry && !_aiUnanswered()) return;
    aiMsg('');
    if (!_ai.conv) _ai.conv = {id: null, messages: []};
    if (!retry) {
        _ai.conv.messages.push({role: 'user', content: q, created_at: new Date().toISOString()});
        inp.value = '';
    }
    if (_ai.conv.run) _ai.conv.run = null;
    _ai.busy = true;   // before the render: no "unanswered" notice under a question being sent
    aiRenderThread();
    _ai.toolsDone = [];
    _aiBusy(true, Date.now());
    _aiProgress({phase: 'thinking', round: 1});
    _ai.gotDone = false;
    _ai.stopPending = false;
    _ai.pvDismissed = false;
    _ai.abort = new AbortController();
    try {
        const resp = await fetch(`${API}/ai/chat`, {method: 'POST', signal: _ai.abort.signal,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: q, conversation_id: _ai.conv.id, server: _ai.server, lang: getLang(),
                                  theme: typeof getTheme === 'function' ? getTheme() : 'light',
                                  llm: _ai.llm || undefined, retry: retry || undefined})});
        if (resp.status === 401) { window.location.href = '/login'; return; }
        if (!resp.ok) {
            let d = {};
            try { d = await resp.json(); } catch (_) { d = {error: `HTTP ${resp.status}`}; }
            _localizeServerText(d);
            if (d.need_signin) aiShowSignin();
            aiMsg(d.error || `HTTP ${resp.status}`, 'err');
            if (!retry) { _ai.conv.messages.pop(); inp.value = q; }   // nothing was asked: give the text back
            _ai.gotDone = true;   // refused, not cut off: nothing to follow, and the message stays
            _aiBusy(false);
            aiRenderThread();
            return;
        }
        await _aiReadStream(resp);
    } catch (e) {
        if (e.name !== 'AbortError') aiMsg(String(e), 'err');
        else if (!_ai.detached) aiMsg(t('ai_stopped'), 'ok');
    } finally {
        _ai.abort = null;
        _ai.stopPending = false;
        const id = _ai.conv && _ai.conv.id;
        if (_ai.detached) { _ai.detached = false; } else if (!_ai.gotDone && id) {
            // the stream ended without its last event (a proxy, the network): the server may well
            // still be answering, so read the conversation again and follow it from there
            _aiBusy(false);
            aiOpenConv(id, true);
        } else {
            _aiBusy(false);
            aiLoadStatus();
            if (_aiUnanswered()) aiRenderThread();   // failed or stopped: offer to answer it
        }
    }
}

async function _aiReadStream(resp) {
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    for (;;) {
        const {value, done} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream: true});
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
            const block = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            let ev = '', data = '';
            for (const line of block.split('\n')) {
                if (line.startsWith('event: ')) ev = line.slice(7);
                else if (line.startsWith('data: ')) data += line.slice(6);
            }
            if (!ev || !data) continue;
            let obj;
            try { obj = JSON.parse(data); } catch (_) { continue; }
            if (ev === 'start') {
                if (!_ai.conv.id) _ai.conv.title = (_ai.conv.messages[0] || {}).content.slice(0, 80);
                _ai.conv.id = obj.conversation_id;
                _ai.pvWatch = obj.conversation_id;   // its answer opens the preview however it lands
                if (!_ai.conv.server) _ai.conv.server = _ai.server;
                aiRenderHead();
                aiLoadConvs();
                if (_ai.stopPending) {   // Stop was pressed before the server said which conversation
                    _ai.stopPending = false;
                    fetchJSON(`${API}/ai/conversations/${encodeURIComponent(_ai.conv.id)}/stop`, {method: 'POST'});
                }
            }
            else if (ev === 'progress') _aiProgress(obj);
            else if (ev === 'done') {
                _ai.gotDone = true;
                _ai.partial = '';
                _ai.reasoning = '';
                const last = (_ai.conv.messages || [])[_ai.conv.messages.length - 1];
                if (obj.answer && !(last && last.role === 'assistant' && last.content === obj.answer)) {
                    _ai.conv.messages.push({id: obj.message_id, role: 'assistant', content: obj.answer, model: obj.model,
                        tokens: obj.tokens, elapsed_ms: obj.elapsed_ms, tools: obj.tools, calls: obj.calls || [],
                        followups: obj.followups || [], llm: obj.llm,
                        truncated: obj.truncated, created_at: new Date().toISOString()});
                }
                if (obj.stopped) {
                    aiMsg(t('ai_stopped'), 'ok');
                    const q = [...(_ai.conv.messages || [])].reverse().find(m => m.role === 'user');
                    if (q && !(last && last.role === 'assistant' && last.content === obj.answer && obj.answer)) {
                        q.stopped_at = q.stopped_at || new Date().toISOString();
                    }
                }
                else if (obj.error && !obj.answer) aiMsg(t('ai_failed') + jobNote(obj.error), 'err');
                else if (obj.error) aiMsg(jobNote(obj.error), 'err');
                else if ((obj.notes || []).length) aiMsg(obj.notes.map(n => t('ai_note_' + n)).join(' '), 'ok');
                aiRenderThread();
                aiLoadConvs();
                _aiLanded();
            }
        }
    }
}

// the answer that just came: its last page / diagram goes to the pane (the live one, if
// it was showing, becomes the stored one), unless the reader closed the pane meanwhile
// The answer being watched has landed: the stream's done event, the poll that follows a
// run (the page was left and came back), or reading the conversation again after a
// stream a proxy cut (owner 2026-11-27: a finished dashboard did not open by itself).
function _aiLanded() {
    const c = _ai.conv;
    if (!c || !c.id || _ai.pvWatch !== c.id) return;
    const msgs = c.messages || [];
    const last = msgs[msgs.length - 1];
    if (!last || last.role !== 'assistant' || !last.id) return;
    _ai.pvWatch = null;
    _aiAutoPreview(last.id, last.content);
}

function _aiAutoPreview(mid, text) {
    if (_ai.pvDismissed) return;
    const kinds = [...String(text).matchAll(/```[ \t]*(html|mermaid|svg|markdown|md)[ \t]*\n[\s\S]*?\n```/gi)]
        .map(m => (m[1].toLowerCase() === 'md' ? 'markdown' : m[1].toLowerCase()));
    if (!kinds.length) { if (_ai.preview && _ai.preview.live) aiClosePreview(); return; }
    aiOpenPreview(mid, kinds.length - 1, kinds[kinds.length - 1]);
}

// Stop asks the server to stop (leaving the page does not); the stream then ends by itself
async function aiStop() {
    // not started yet: the server has not said which conversation; stop it as soon as it does
    // (closing the stream would not stop it: an answer outlives the page)
    if (!_ai.conv || !_ai.conv.id) { if (_ai.abort) { _ai.stopPending = true; aiMsg(t('ai_stopped'), 'ok'); } return; }
    const id = _ai.conv.id;
    await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}/stop`, {method: 'POST'});
    if (!_ai.abort) {   // following a run started on an earlier visit
        aiMsg(t('ai_stopped'), 'ok');
        setTimeout(() => { if (_ai.conv && _ai.conv.id === id) aiOpenConv(id); }, 800);
    }
}

function _aiEnterHint() {
    const el = document.getElementById('ai-enter-hint');
    if (!el) return;
    const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
    const keys = `<kbd class="ai-key">${mac ? '⌘' : 'Ctrl'}</kbd><span class="ai-key-plus">+</span><kbd class="ai-key">Enter</kbd>`;
    el.innerHTML = esc(t('ai_enter_hint')).replace('{keys}', keys);
}

// ---- preview pane (1.36): a page / Mermaid diagram / SVG the model wrote ----------
// The server serves it with a sandboxing CSP (no cookies, no network, no access to
// this page); the frame is sandboxed again here. Owner 2026-11-26.

// Markdown and Mermaid follow the page's theme (an HTML page keeps its own colours)
function _aiPreviewUrl(p) {
    const theme = typeof getTheme === 'function' && getTheme() === 'dark' ? 'dark' : 'light';
    return (p.live
        ? `${API}/ai/conversations/${encodeURIComponent(p.mid)}/live-preview/${encodeURIComponent(p.n)}`
        : `${API}/ai/messages/${encodeURIComponent(p.mid)}/preview/${encodeURIComponent(p.n)}`) + `?theme=${theme}`;
}

// live: the block of the answer being written (`mid` is then the conversation id)
function aiOpenPreview(mid, n, kind, live) {
    const pane = document.getElementById('ai-preview');
    const lay = document.getElementById('ai-layout');
    if (!pane || !lay) return;
    _ai.preview = {mid, n, kind, live: !!live};
    const url = _aiPreviewUrl(_ai.preview);
    const b = (act, ic, key) => `<button type="button" class="ai-act" data-act="${act}" title="${esc(t(key))}" aria-label="${esc(t(key))}">${icon(ic, 15)}</button>`;
    const wide = lay.classList.contains('ai-preview-wide');
    pane.innerHTML = `<div class="ai-head ai-preview-head"><span class="ai-head-title ai-preview-title">${icon('eye', 15)}<span>${esc(t('ai_preview_title_' + kind))}</span>${live ? `<span class="ai-pv-live">${esc(t('ai_preview_live'))}</span>` : ''}</span>
        <span class="ai-head-acts">${b('aiPreviewWide', wide ? 'collapse' : 'expand', wide ? 'ai_preview_narrow' : 'ai_preview_wide')}
        ${live ? '' : `<a class="ai-act" href="${esc(url)}" target="_blank" rel="noopener noreferrer" title="${esc(t('ai_preview_open'))}" aria-label="${esc(t('ai_preview_open'))}">${icon('open_window', 15)}</a>
        <a class="ai-act" href="${esc(url)}&download=1" title="${esc(t('ai_preview_download'))}" aria-label="${esc(t('ai_preview_download'))}">${icon('download', 15)}</a>`}
        ${b('aiClosePreview', 'close', 'btn_close')}</span></div>
        <div class="ai-pv-frames"><iframe sandbox="allow-scripts" referrerpolicy="no-referrer" title="${esc(t('ai_preview_title_' + kind))}" src="${esc(url)}"></iframe>${live
            ? `<div class="ai-pv-busy" role="status"><span><i aria-hidden="true"></i>${esc(t('ai_preview_live'))}</span></div>` : ''}</div>
        <div class="ai-preview-note">${icon('lock', 12)}<span>${esc(t('ai_preview_note'))}</span></div>`;
    pane.classList.remove('hidden');
    lay.classList.add('ai-preview-open');
    _aiApplyPreviewWidth();
    requestAnimationFrame(_aiPlaceSplit);
}

// Drag the left edge of the pane to share the width with the chat (owner 2026-11-27);
// double-click goes back to the default. The width is kept for next time.
const AI_PV_MIN = 320, AI_CHAT_MIN = 360;
function _aiApplyPreviewWidth(w) {
    const lay = document.getElementById('ai-layout');
    if (!lay) return;
    const want = w != null ? w : parseInt(_aiPref('pvw') || '', 10);
    const max = lay.clientWidth - (lay.classList.contains('ai-side-collapsed') ? 52 : 260) - AI_CHAT_MIN - 32;
    if (!want || max < AI_PV_MIN) { lay.style.removeProperty('--ai-pv-w'); return; }
    lay.style.setProperty('--ai-pv-w', `${Math.max(AI_PV_MIN, Math.min(want, max))}px`);
}

// The handle lives in the gap between the chat card and the pane (owner 2026-11-27: "要在兩個卡片
// 中間"), placed from the pane's own box and moved whenever the layout changes size.
function _aiSplitEl() {
    const lay = document.getElementById('ai-layout');
    if (!lay) return null;
    let h = document.getElementById('ai-split');
    if (!h) {
        h = document.createElement('div');
        h.id = 'ai-split';
        h.className = 'ai-split';
        h.setAttribute('role', 'separator');
        h.setAttribute('aria-orientation', 'vertical');
        h.title = t('ai_split_tip');
        lay.appendChild(h);
        _aiBindSplit(h);
        if (window.ResizeObserver) new ResizeObserver(() => _aiPlaceSplit()).observe(lay);
        window.addEventListener('resize', () => _aiPlaceSplit());
    }
    return h;
}

function _aiPlaceSplit() {
    const lay = document.getElementById('ai-layout');
    const pane = document.getElementById('ai-preview');
    const h = _aiSplitEl();
    if (!lay || !pane || !h) return;
    const shown = lay.classList.contains('ai-preview-open') && !lay.classList.contains('ai-preview-wide')
        && !pane.classList.contains('hidden') && getComputedStyle(lay).gridTemplateColumns.split(' ').length >= 3;
    h.classList.toggle('hidden', !shown);
    if (!shown) return;
    const gap = parseFloat(getComputedStyle(lay).columnGap) || 16;
    h.style.setProperty('left', `${pane.offsetLeft - gap}px`);
    h.style.setProperty('width', `${gap}px`);
    h.style.setProperty('top', `${pane.offsetTop}px`);
    h.style.setProperty('height', `${pane.offsetHeight}px`);
}

function _aiBindSplit(h) {
    const lay = document.getElementById('ai-layout');
    h.addEventListener('pointerdown', e => {
        const pane = document.getElementById('ai-preview');
        if (!pane) return;
        e.preventDefault();
        h.setPointerCapture(e.pointerId);
        lay.classList.add('ai-dragging');   // the frame would swallow the pointer otherwise
        const right = pane.getBoundingClientRect().right;
        const move = ev => { _aiApplyPreviewWidth(Math.round(right - ev.clientX)); _aiPlaceSplit(); };
        const up = () => {
            h.removeEventListener('pointermove', move);
            lay.classList.remove('ai-dragging');
            _aiPref('pvw', String(Math.round(pane.getBoundingClientRect().width)));
            _aiPlaceSplit();
        };
        h.addEventListener('pointermove', move);
        h.addEventListener('pointerup', up, {once: true});
        h.addEventListener('pointercancel', up, {once: true});
    });
    h.addEventListener('dblclick', () => { _aiPref('pvw', ''); _aiApplyPreviewWidth(0); _aiPlaceSplit(); });
}

function aiPreviewWide() {
    const lay = document.getElementById('ai-layout');
    if (!lay || !_ai.preview) return;
    lay.classList.toggle('ai-preview-wide');
    const p = _ai.preview;
    aiOpenPreview(p.mid, p.n, p.kind, p.live);
}

function aiClosePreview() {
    const pane = document.getElementById('ai-preview');
    const lay = document.getElementById('ai-layout');
    if (pane) { pane.classList.add('hidden'); pane.innerHTML = ''; }
    if (lay) lay.classList.remove('ai-preview-open', 'ai-preview-wide');
    _ai.preview = null;
    _aiPlaceSplit();
    if (_ai.busy) _ai.pvDismissed = true;   // not again for this answer
}

// ---- Settings ---------------------------------------------------------------------

function aiToggleSettings() {
    const el = document.getElementById('ai-settings');
    el.classList.toggle('hidden');
    const open = !el.classList.contains('hidden');
    // the panel opens inside the status card, under this button (owner 2026-11-23:
    // a separate card did not read as something that had opened)
    const btn = document.getElementById('ai-settings-btn');
    if (btn) { btn.classList.toggle('is-open', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    if (open) { _ai.llmEdit = null; aiRenderSettings(); }
}

// The LLM servers being edited (a working copy: kept while the form is open, so a
// re-render after changing a type or adding a server does not lose what was typed)
function _aiLlmEditFrom(s) {
    return (s.llm_servers || []).map(x => ({...x, old_name: x.name}));
}

function _aiCaptureLlms() {
    const list = _ai.llmEdit || [];
    list.forEach((x, i) => {
        const g = id => document.getElementById(`ai-l${i}-${id}`);
        if (!g('name')) return;
        x.name = g('name').value.trim();
        x.kind = g('kind').value;
        x.url = g('url').value.trim();
        x.model = (g('model').value || '').trim();
        x.api_key = g('key').value;
        x.timeout_seconds = Number(g('timeout').value);
        if (g('temp')) x.temperature = Number(g('temp').value);
        if (g('effort')) x.effort = g('effort').value;
        x.context_tokens = Number(g('ctx').value || 0);
        x.daily_tokens = Number(g('daily').value || 0);
        x.monthly_tokens = Number(g('monthly').value || 0);
        x.allow_external = g('external').checked;
    });
    const def = document.querySelector('input[name="ai-llm-default"]:checked');
    if (def) _ai.llmDefault = (list[Number(def.value)] || {}).name || '';
    return list;
}

function _aiLlmCard(x, i) {
    const num = (id, v, min, max, step) => `<input type="number" id="ai-l${i}-${id}" value="${esc(String(v ?? ''))}" min="${min}" max="${max}" ${step ? `step="${step}"` : ''}>`;
    const claude = x.kind === 'anthropic';
    const isDef = (_ai.llmDefault || '') === x.name || (!_ai.llmDefault && i === 0);
    return `<div class="ai-llm" id="ai-llm-${i}">
        <div class="ai-llm-head">
            <label class="sec-chk"><input type="radio" name="ai-llm-default" value="${i}" ${isDef ? 'checked' : ''}> ${esc(t('ai_llm_default'))}</label>
            <span class="ai-llm-acts">
                <button type="button" class="btn-secondary btn-sm" data-act="aiTestLlm" data-arg="${i}">${icon('refresh', 14)} ${esc(t('btn_test_connection'))}</button>
                <button type="button" class="btn-danger btn-sm" data-act="aiDeleteLlm" data-arg="${i}">${icon('trash', 14)} ${esc(t('btn_delete'))}</button>
            </span></div>
        <div class="sec-form ai-llm-form">
            <div class="ai-f2"><label>${esc(t('ai_llm_name'))}</label><input type="text" id="ai-l${i}-name" maxlength="60" value="${esc(x.name || '')}"></div>
            <div class="ai-f4"><label>${esc(t('ai_llm_kind'))}</label><select id="ai-l${i}-kind" data-act-change="aiLlmKind" data-act-self data-i="${i}">
                <option value="openai" ${!claude ? 'selected' : ''}>${esc(t('ai_llm_kind_openai'))}</option>
                <option value="anthropic" ${claude ? 'selected' : ''}>${esc(t('ai_llm_kind_anthropic'))}</option></select></div>
            <div class="ai-f6"><label>${esc(t(claude ? 'ai_llm_url_claude' : 'ai_s_url'))}</label><input type="text" id="ai-l${i}-url" value="${esc(x.url || '')}" placeholder="${claude ? 'https://api.anthropic.com' : 'http://10.0.0.5:8080/v1'}"></div>
            <div class="ai-f6"><label>${esc(t('ai_model'))}</label>
                <div class="ai-model-row"><select id="ai-l${i}-model">${_aiModelOptions([], x.model || (claude ? 'claude-opus-5-5' : ''))}</select>
                <button type="button" class="btn-secondary btn-sm" data-act="aiLoadModels" data-arg="${i}" title="${esc(t('ai_models_reload'))}">${icon('refresh', 14)}</button></div>
                <div id="ai-l${i}-models-msg" class="ai-llm-hint"></div></div>
            <div class="ai-f2"><label>${esc(t('ai_s_key'))}</label>${_secretField(`ai-l${i}-key`, x.api_key || '')}</div>
            <div class="ai-f2"><label>${esc(t('ai_s_timeout'))}</label>${num('timeout', x.timeout_seconds ?? 300, 10, 900)}</div>
            ${claude
                ? `<div class="ai-f2"><label>${esc(t('ai_llm_effort'))}</label><select id="ai-l${i}-effort">${['', 'low', 'medium', 'high', 'xhigh', 'max'].map(e => `<option value="${e}" ${(x.effort || '') === e ? 'selected' : ''}>${esc(e ? e : t('ai_llm_effort_default'))}</option>`).join('')}</select></div>`
                : `<div class="ai-f2"><label>${esc(t('ai_s_temperature'))}</label>${num('temp', x.temperature ?? 0.2, 0, 1, '0.1')}</div>`}
            <div class="ai-f2"><label>${esc(t('ai_llm_ctx'))}</label>${num('ctx', x.context_tokens || 0, 0, 10000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_ctx_hint'))}</div><div class="ai-llm-ctx ai-llm-hint" id="ai-l${i}-ctxinfo"></div></div>
            <div class="ai-f2"><label>${esc(t('ai_llm_daily'))}</label>${num('daily', x.daily_tokens || 0, 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
            <div class="ai-f2"><label>${esc(t('ai_llm_monthly'))}</label>${num('monthly', x.monthly_tokens || 0, 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
            <div class="ai-f6"><label class="sec-chk"><input type="checkbox" id="ai-l${i}-external" ${x.allow_external ? 'checked' : ''}> ${esc(t('ai_s_external'))}</label>
                <div class="ai-llm-hint">${esc(t(claude ? 'ai_llm_claude_note' : 'ai_s_external_note'))}</div></div>
        </div>
        <div id="ai-l${i}-test" class="fs-085"></div>
    </div>`;
}

function aiRenderSettings(keepEdit) {
    const d = _ai.status;
    if (!d) return;
    const s = d.settings;
    if (!keepEdit || !_ai.llmEdit) { _ai.llmEdit = _aiLlmEditFrom(s); _ai.llmDefault = s.default_llm || ''; }
    const num = (id, v, min, max, step) => `<input type="number" id="${id}" value="${esc(String(v ?? ''))}" min="${min}" max="${max}" ${step ? `step="${step}"` : ''}>`;
    const chk = (id, v, label) => `<label class="sec-chk"><input type="checkbox" id="${id}" ${v ? 'checked' : ''}> ${esc(label)}</label>`;
    const mg = d.mcp_graylog;
    const enabledTools = (s.mcp_graylog_tools && s.mcp_graylog_tools.length) ? s.mcp_graylog_tools : d.mcp_graylog_default;
    const optional = d.mcp_graylog_optional || [];
    const toolBoxes = d.mcp_graylog_default.concat(optional).map(n => `<label class="sec-chk ai-tool"${optional.includes(n) ? ` title="${esc(t('ai_mg_heavy_tip'))}"` : ''}><input type="checkbox" class="ai-mg-tool" value="${esc(n)}" ${enabledTools.includes(n) ? 'checked' : ''}> <code>${esc(n)}</code>${optional.includes(n) ? ` <span class="sec-tag">${esc(t('ai_mg_heavy'))}</span>` : ''}</label>`).join('');
    // the address the browser uses (behind a reverse proxy the server sees another)
    const mcpCfg = JSON.stringify({mcpServers: {'jt-glogarch': {type: 'http', url: window.location.origin + '/mcp',
        headers: {Authorization: 'Bearer <Graylog API token>'}}}}, null, 2);
    const keep = id => { const el = document.getElementById(id); return el ? (el.type === 'checkbox' ? el.checked : el.value) : undefined; };
    const kv = (id, v) => { const k = keep(id); return keepEdit && k !== undefined ? k : v; };
    document.getElementById('ai-settings').innerHTML = `
        <div class="ai-set-head"><h3>${esc(t('ai_set_title'))}</h3>
            <button type="button" class="ai-act" data-act="aiToggleSettings" title="${esc(t('btn_collapse'))}" aria-label="${esc(t('btn_collapse'))}">${icon('close', 14)}</button></div>
        ${_aiSetSec('general', t('ai_set_general'), `
        <div class="sec-form">
            <div class="sec-wide">${chk('ai-s-enabled', kv('ai-s-enabled', s.enabled), t('ai_s_enabled'))}</div>
            <div class="sec-wide">${chk('ai-s-analysis', kv('ai-s-analysis', s.analysis_enabled), t('ai_s_analysis'))}
                <div class="text-muted fs-08">${esc(t('ai_s_analysis_note'))}</div></div>
            <div class="sec-wide">${chk('ai-s-sumllm', kv('ai-s-sumllm', s.summary_cover_llm !== false), t('ai_s_sum_llm'))}
                <div class="text-muted fs-08">${esc(t('ai_s_sum_llm_note'))}</div></div>
        </div>
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}
        ${_aiSetSec('llm', t('ai_llm_title'), `
        <p class="text-muted fs-085">${esc(t('ai_llm_help'))}</p>
        <div class="ai-llms">${_ai.llmEdit.length ? _ai.llmEdit.map(_aiLlmCard).join('') : `<div class="text-muted fs-085">${esc(t('ai_llm_none'))}</div>`}</div>
        <button type="button" class="btn-secondary btn-sm" data-act="aiAddLlm">${icon('plus', 14)} ${esc(t('ai_llm_add'))}</button>
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}
        ${_aiSetSec('limits', t('ai_limits_title'), `
        <div class="sec-form ai-llm-form">
            <div class="ai-f2"><label>${esc(t('ai_s_rounds'))}</label>${num('ai-s-rounds', kv('ai-s-rounds', s.max_tool_rounds), 1, 10)}</div>
            <div class="ai-f2"><label>${esc(t('ai_s_range'))}</label>${num('ai-s-range', kv('ai-s-range', s.max_range_hours), 1, 168)}</div>
            <div class="ai-f2"><label>${esc(t('ai_s_retention'))}</label>${num('ai-s-retention', kv('ai-s-retention', s.chat_retention_days), 0, 3650)}
                <div class="ai-llm-hint">${esc(t('ai_s_retention_hint'))}</div></div>
            <div class="ai-f2 ai-row-start"><label>${esc(t('ai_s_daily'))}</label>${num('ai-s-daily', kv('ai-s-daily', s.daily_tokens), 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
            <div class="ai-f2"><label>${esc(t('ai_s_monthly'))}</label>${num('ai-s-monthly', kv('ai-s-monthly', s.monthly_tokens), 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
            <div class="ai-f2 ai-row-start"><label>${esc(t('ai_s_user_daily'))}</label>${num('ai-s-udaily', kv('ai-s-udaily', s.user_daily_tokens), 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
            <div class="ai-f2"><label>${esc(t('ai_s_user_monthly'))}</label>${num('ai-s-umonthly', kv('ai-s-umonthly', s.user_monthly_tokens), 0, 1000000000)}
                <div class="ai-llm-hint">${esc(t('ai_llm_limit_hint'))}</div></div>
        </div>
        <div class="text-muted fs-08">${esc(t('ai_limits_note'))}</div>
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}
        ${_aiSetSec('report', t('ai_set_report'), _aiReportStyleForm(s.summary_style || {}) + `
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}
        ${_aiSetSec('mcp', t('ai_mcp_title'), `
        <p class="text-muted fs-085">${esc(t('ai_mcp_help'))}</p>
        <div>${chk('ai-s-mcp', kv('ai-s-mcp', s.mcp_enabled), t('ai_s_mcp'))}</div>
        <pre class="ai-code"><code>${esc(mcpCfg)}</code></pre>
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}
        ${_aiSetSec('mcpg', 'mcp_graylog ' + mg.version, `
        <p class="fs-085 ${mg.available ? 'pk-ok' : 'pk-err'}">${esc(mg.available ? t('ai_mg_ok') : t('ai_mg_unavailable') + ' ' + mg.error)}</p>
        <div class="ai-tools">${toolBoxes}</div>
        <p class="text-muted fs-08">${esc(t('ai_mg_note'))}</p>
        <div class="sec-save-row ai-btns"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`)}`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
    _ai.llmEdit.forEach((x, i) => {
        const u = document.getElementById(`ai-l${i}-url`);
        if (u) u.addEventListener('change', () => aiLoadModels(i));
        if (x.url || x.kind === 'anthropic') aiLoadModels(i);
    });
}

// Each settings card folds from its title (owner 2026-11-27: "每一區卡片要可以收折"); which ones
// are folded is kept per browser. Folded fields stay in the page, so Save still sends them.
// The summary PDF's own look: the report editor's cover / logo / watermark fields (owner 2026-11-27:
// "要設定 報告的 logo 或文字"), the same logo controls (reportLogoPick / reportLogoClear by prefix).
function _aiReportStyleForm(st) {
    const opt = (v, cur, key) => `<option value="${v}"${v === cur ? ' selected' : ''}>${esc(t(key))}</option>`;
    const ap = st.watermark_append || [];
    return `<p class="text-muted fs-085">${esc(t('ai_set_report_help'))}</p>
        <div class="ai-report-style">
        ${_reportLogoField('ai-r-logo', st.logo_data_uri, 'logo-preview-cover', 'reports_f_logo', 'reports_logo_hint')}
        <div class="form-group"><label>${esc(t('reports_f_logo_size'))}</label><input type="number" id="ai-r-logo-size" min="20" max="200" step="2" value="${esc(String(st.logo_height_px || 72))}" class="mw120"> <span class="text-muted fs-08">px</span></div>
        ${_reportLogoField('ai-r-hlogo', st.header_logo_data_uri, 'logo-preview-dark', 'reports_f_hlogo_dark', 'reports_hlogo_dark_hint')}
        <div class="sec-form ai-llm-form">
            <div class="ai-f2"><label>${esc(t('ai_r_kicker'))}</label><input type="text" id="ai-r-kicker" maxlength="80" value="${esc(st.kicker || '')}" placeholder="jt-glogarch"></div>
            <div class="ai-f2"><label>${esc(t('reports_f_author'))}</label><input type="text" id="ai-r-author" maxlength="120" value="${esc(st.author || '')}" placeholder="${esc(t('ai_r_author_ph'))}"></div>
            <div class="ai-f2"><label>${esc(t('ai_r_color'))}</label><input type="text" id="ai-r-color" maxlength="7" value="${esc(st.brand_color || '')}" placeholder="#6c63ff"></div>
            <div class="ai-f2 ai-row-start"><label>${esc(t('reports_f_header'))}</label><input type="text" id="ai-r-header" maxlength="120" value="${esc(st.header_text || '')}" placeholder="${esc(t('ai_r_header_ph'))}"></div>
        </div>
        <div class="form-group"><label class="inline-check"><input type="checkbox" id="ai-r-wm" ${st.watermark_enabled ? 'checked' : ''}> ${esc(t('reports_f_wm'))}</label></div>
        <div class="sec-form ai-llm-form">
            <div class="ai-f2"><label>${esc(t('reports_f_wm_text'))}</label><input type="text" id="ai-r-wm-text" maxlength="120" value="${esc(st.watermark_text || '')}" placeholder="${esc(t('reports_wm_text_ph'))}"></div>
            <div class="ai-f2"><label>${esc(t('reports_f_wm_size'))}</label><select id="ai-r-wm-size">${opt('small', st.watermark_size, 'reports_wm_small')}${opt('medium', st.watermark_size, 'reports_wm_medium')}${opt('large', st.watermark_size || 'large', 'reports_wm_large')}</select></div>
            <div class="ai-f2"><label>${esc(t('reports_f_wm_dir'))}</label><select id="ai-r-wm-dir">${opt('diagonal', st.watermark_direction || 'diagonal', 'reports_wm_diagonal')}${opt('horizontal', st.watermark_direction, 'reports_wm_horizontal')}</select></div>
        </div>
        <div class="form-group"><label>${esc(t('reports_f_wm_append'))}</label><div class="wm-append">
            ${['server', 'ip', 'time'].map(k => `<label class="inline-check"><input type="checkbox" class="ai-r-wm-ap" value="${k}" ${ap.includes(k) ? 'checked' : ''}> ${esc(t('reports_wm_ap_' + k))}</label>`).join('')}</div></div>
        </div>`;
}

function _aiReportStyleBody() {
    const v = id => (document.getElementById(id) || {}).value || '';
    if (!document.getElementById('ai-r-logo')) return undefined;
    return {logo_data_uri: v('ai-r-logo'), header_logo_data_uri: v('ai-r-hlogo'),
            logo_height_px: Number(v('ai-r-logo-size') || 72), kicker: v('ai-r-kicker'), author: v('ai-r-author'),
            header_text: v('ai-r-header'),
            brand_color: v('ai-r-color').trim(), watermark_enabled: !!(document.getElementById('ai-r-wm') || {}).checked,
            watermark_text: v('ai-r-wm-text'), watermark_size: v('ai-r-wm-size'), watermark_direction: v('ai-r-wm-dir'),
            watermark_append: [...document.querySelectorAll('.ai-r-wm-ap:checked')].map(x => x.value)};
}

function _aiSetFolded() {
    try { return JSON.parse(localStorage.getItem('jt-ai-set-fold') || '[]'); } catch (e) { return []; }
}

function _aiSetSec(key, title, body) {
    const folded = _aiSetFolded().includes(key);
    return `<section class="ai-set-sec${folded ? ' ai-set-folded' : ''}" data-fold="${esc(key)}">
        <button type="button" class="ai-set-fold" data-act="aiFoldSet" data-arg="${esc(key)}" aria-expanded="${folded ? 'false' : 'true'}">
            <span class="ai-set-chev" aria-hidden="true">${icon('chevron_down', 14)}</span><span class="ai-sub">${esc(title)}</span></button>
        <div class="ai-set-body">${body}</div></section>`;
}

function aiFoldSet(key) {
    const sec = document.querySelector(`.ai-set-sec[data-fold="${CSS.escape(String(key))}"]`);
    if (!sec) return;
    const folded = sec.classList.toggle('ai-set-folded');
    sec.querySelector('.ai-set-fold').setAttribute('aria-expanded', folded ? 'false' : 'true');
    const keep = new Set(_aiSetFolded());
    if (folded) keep.add(key); else keep.delete(key);
    try { localStorage.setItem('jt-ai-set-fold', JSON.stringify([...keep])); } catch (e) { /* not remembered */ }
}

function aiAddLlm() {
    _aiCaptureLlms();
    const used = new Set(_ai.llmEdit.map(x => x.name));
    let n = _ai.llmEdit.length + 1;
    while (used.has(`LLM ${n}`)) n++;
    _ai.llmEdit.push({name: `LLM ${n}`, kind: 'openai', url: '', model: '', api_key: '', timeout_seconds: 300,
        temperature: 0.2, effort: '', context_tokens: 0, daily_tokens: 0, monthly_tokens: 0, allow_external: false});
    aiRenderSettings(true);
}

function aiDeleteLlm(i) {
    _aiCaptureLlms();
    const x = _ai.llmEdit[Number(i)];
    if (!x) return;
    showConfirm(t('ai_llm_delete_title'), t('ai_llm_delete_msg').replace('{n}', x.name), () => {
        _ai.llmEdit.splice(Number(i), 1);
        aiRenderSettings(true);
    });
}

function aiLlmKind(el) {
    _aiCaptureLlms();
    const x = _ai.llmEdit[Number(el.dataset.i)];
    if (!x) return;
    x.kind = el.value;
    if (x.kind === 'anthropic') {
        if (!x.url || /\/v1\/?$/.test(x.url)) x.url = '';
        if (!x.model || !/^claude/.test(x.model)) x.model = 'claude-opus-5-5';
        x.allow_external = true;   // the Claude API is outside the private network by definition
    }
    aiRenderSettings(true);
}

function _aiLlmForm(i) {
    _aiCaptureLlms();
    const x = _ai.llmEdit[Number(i)] || {};
    return {name: x.name, old_name: x.old_name, kind: x.kind, url: x.url, api_key: x.api_key, model: x.model,
        allow_external: x.allow_external, timeout_seconds: x.timeout_seconds, context_tokens: x.context_tokens};
}

function _aiModelOptions(models, current) {
    const list = models.slice();
    if (current && !list.includes(current)) list.unshift(current);
    if (!list.length) return `<option value="">${esc(t('ai_models_none'))}</option>`;
    return list.map(m => `<option value="${esc(m)}" ${m === current ? 'selected' : ''}>${esc(m)}${models.length && m === current && !models.includes(m) ? ' ' + esc(t('ai_models_not_listed')) : ''}</option>`).join('');
}

// the model list and context window come from the LLM server named in that card
async function aiLoadModels(i) {
    i = Number(i);
    const sel = document.getElementById(`ai-l${i}-model`);
    const msg = document.getElementById(`ai-l${i}-models-msg`);
    if (!sel) return;
    const form = _aiLlmForm(i);
    if (!form.url && form.kind !== 'anthropic') { msg.textContent = t('ai_models_need_url'); return; }
    msg.textContent = t('ai_models_loading');
    const d = await fetchJSON(`${API}/ai/models`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(form)});
    if (!document.getElementById(`ai-l${i}-model`)) return;   // form closed meanwhile
    if (!d || d.error) { msg.innerHTML = `<span class="pk-err">${esc((d && d.error) || t('ai_models_failed'))}</span>`; return; }
    const current = form.model;
    const pick = current || (d.models.length === 1 ? d.models[0] : '');
    sel.innerHTML = _aiModelOptions(d.models, pick);
    sel.value = pick;
    if (typeof initCustomSelects === 'function') initCustomSelects();
    msg.textContent = d.models.length ? t('ai_models_count').replace('{n}', d.models.length) : t('ai_models_empty');
    _aiShowContext(i, {...form, model: pick});
}

async function _aiShowContext(i, form) {
    const el = document.getElementById(`ai-l${i}-ctxinfo`);
    if (!el) return;
    const p = await fetchJSON(`${API}/ai/profile`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(form)});
    if (!document.getElementById(`ai-l${i}-ctxinfo`) || !p || p.error) return;
    el.textContent = p.known
        ? t('ai_llm_ctx_found').replace('{n}', formatNumber(p.context)).replace('{s}', p.source === 'set' ? t('ai_llm_ctx_set') : p.source)
        : t('ai_llm_ctx_unknown').replace('{n}', formatNumber(p.context));
}

function _aiSettingsBody() {
    const v = id => document.getElementById(id).value;
    const c = id => document.getElementById(id).checked;
    const llms = _aiCaptureLlms();
    return {
        enabled: c('ai-s-enabled'), analysis_enabled: c('ai-s-analysis'), summary_cover_llm: c('ai-s-sumllm'),
        llm_servers: llms, default_llm: _ai.llmDefault || (llms[0] || {}).name || '',
        max_tool_rounds: Number(v('ai-s-rounds')), max_range_hours: Number(v('ai-s-range')),
        daily_tokens: Number(v('ai-s-daily')), monthly_tokens: Number(v('ai-s-monthly')),
        user_daily_tokens: Number(v('ai-s-udaily')), user_monthly_tokens: Number(v('ai-s-umonthly')),
        chat_retention_days: Number(v('ai-s-retention')),
        mcp_enabled: c('ai-s-mcp'), summary_style: _aiReportStyleBody(),
        mcp_graylog_tools: [...document.querySelectorAll('.ai-mg-tool:checked')].map(x => x.value),
    };
}

async function aiSaveSettings() {
    const d = await fetchJSON(`${API}/ai/settings`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(_aiSettingsBody())});
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    aiMsg(t('ai_saved'), 'ok');
    _ai.llmEdit = null;
    await aiLoadStatus();
}

// tests what is in that card (not saved yet): the model list, one short request, the context window
async function aiTestLlm(i) {
    i = Number(i);
    const el = document.getElementById(`ai-l${i}-test`);
    const form = _aiLlmForm(i);
    el.innerHTML = `<span class="spinner-text">${esc(t('ai_testing'))}</span>`;
    const d = await fetchJSON(`${API}/ai/test`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(form)});
    if (!document.getElementById(`ai-l${i}-test`)) return;
    if (!d || d.error) { el.innerHTML = `<span class="pk-err">${esc(d && d.error)}</span>`; return; }
    el.innerHTML = `<span class="pk-ok">${esc(t('ai_test_ok').replace('{r}', d.reply || '—').replace('{n}', formatNumber(d.tokens)))}</span>`
        + (d.model_listed ? '' : ` <span class="pk-err">${esc(t('ai_test_model_missing').replace('{m}', (d.models || []).slice(0, 20).join(', ')))}</span>`);
    _aiShowContext(i, form);
}

document.addEventListener('DOMContentLoaded', aiInit);

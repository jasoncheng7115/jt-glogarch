/* jt-glogarch — AI chat page (added 1.21).
 * The model reads Graylog through read-only tools as the signed-in user's own
 * Graylog account (web/routes/ai.py). Its answers can quote log text, which an
 * attacker can write: aiMarkdown() escapes everything first and only then adds
 * a small set of formatting; links are https only. */

const _ai = {status: null, conv: null, server: '', busy: false, abort: null};

function aiMsg(text, level) {
    const el = document.getElementById('ai-message');
    if (!el) return;
    el.className = 'pk-message ' + (level === 'err' ? 'pk-err' : 'pk-ok');
    el.textContent = text || '';
    el.classList.toggle('hidden', !text);
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
            const buf = [];
            i++;
            while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
            i++;
            out.push(`<pre class="ai-code"><code>${buf.join('\n')}</code></pre>`);
            continue;
        }
        if (/^\s*\|.*\|\s*$/.test(ln) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
            const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => _aiInline(c.trim()));
            const head = cells(ln);
            i += 2;
            const rows = [];
            while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(cells(lines[i])); i++; }
            out.push(`<div class="table-wrap"><table class="ai-table"><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead>`
                + `<tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
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

async function aiInit() {
    if (!document.getElementById('ai-layout')) return;
    const inp = document.getElementById('ai-input');
    inp.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); aiSend(); } });
    await aiLoadStatus();
    await aiLoadConvs();
    aiRenderThread();
}

async function aiLoadStatus() {
    const q = _ai.server ? `?server=${encodeURIComponent(_ai.server)}` : '';
    const d = await fetchJSON(`${API}/ai/status${q}`);
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    _ai.status = d;
    _ai.server = d.server;
    const s = d.settings;
    const parts = [];
    parts.push(s.enabled ? `<span class="status-completed">${esc(t('ai_on'))}</span>` : `<span class="status-pending">${esc(t('ai_off'))}</span>`);
    if (s.model) parts.push(`<span>${esc(t('ai_model'))}${esc(t('sec_colon'))}<code>${esc(s.model)}</code></span>`);
    if (s.url) parts.push(d.llm_private === false
        ? `<span class="ai-ext">${icon('warning', 14)} ${esc(t('ai_llm_external'))}</span>`
        : `<span class="ai-int">${icon('lock', 14)} ${esc(t('ai_llm_private'))}</span>`);
    const sel = d.servers.length > 1
        ? `<select id="ai-server" data-act-change="aiServerChange">${d.servers.map(n => `<option value="${esc(n)}" ${n === d.server ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>`
        : `<strong>${esc(d.server)}</strong>`;
    parts.push(`<span>${esc(t('al_server'))}${esc(t('sec_colon'))}${sel}</span>`);
    parts.push(d.signed_in
        ? `<span>${icon('user', 14)} ${esc(d.graylog_user)}</span>`
        : `<button class="btn-secondary btn-sm" data-act="aiShowSignin">${icon('login', 14)} ${esc(t('ai_signin_btn'))}</button>`);
    parts.push(`<span class="text-muted fs-08">${esc(t('ai_usage').replace('{d}', formatNumber(d.usage.day)).replace('{m}', formatNumber(d.usage.month)))}</span>`);
    document.getElementById('ai-status').innerHTML = parts.join('<span class="sep">·</span>');
    if (typeof initCustomSelects === 'function') initCustomSelects();
    const off = !s.enabled || !s.url;
    document.getElementById('ai-send').disabled = off || _ai.busy;
    if (off) aiMsg(t('ai_off_hint'), 'ok');
    else if (!d.signed_in) aiMsg(t('ai_need_signin'), 'ok');
    else aiMsg('');
    if (!document.getElementById('ai-settings').classList.contains('hidden')) aiRenderSettings();
}

function aiServerChange(v) { _ai.server = v; aiLoadStatus(); }

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
    const d = await fetchJSON(`${API}/ai/conversations`);
    const el = document.getElementById('ai-convs');
    const items = (d && d.items) || [];
    if (!items.length) { el.innerHTML = `<div class="text-muted fs-08">${esc(t('ai_no_convs'))}</div>`; return; }
    el.innerHTML = items.map(c => `<div class="ai-conv ${_ai.conv && _ai.conv.id === c.id ? 'ai-conv-current' : ''}">
        <button class="ai-conv-open" data-act="aiOpenConv" data-args="${esc(JSON.stringify([c.id]))}" title="${esc(c.title)}"><span class="ai-conv-title">${esc(c.title || '—')}</span><span class="text-muted fs-08">${esc(formatDT(c.updated_at))}</span></button>
        <button class="ai-conv-del" data-act="aiDeleteConv" data-args="${esc(JSON.stringify([c.id]))}" title="${esc(t('btn_delete'))}">${icon('trash', 14)}</button>
    </div>`).join('');
}

async function aiOpenConv(id) {
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`);
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    _ai.conv = d;
    aiRenderThread();
    aiLoadConvs();
}

function aiDeleteConv(id) {
    showConfirm(t('ai_delete_title'), t('ai_delete_msg'), async () => {
        await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(id)}`, {method: 'DELETE'});
        if (_ai.conv && _ai.conv.id === id) _ai.conv = null;
        aiRenderThread();
        aiLoadConvs();
    });
}

function aiNewChat() { _ai.conv = null; aiRenderThread(); aiLoadConvs(); document.getElementById('ai-input').focus(); }

function _aiMeta(m) {
    const bits = [];
    if (m.model) bits.push(esc(m.model));
    if (m.elapsed_ms) bits.push(esc((m.elapsed_ms / 1000).toFixed(1) + ' s'));
    if (m.tokens) bits.push(esc(t('ai_tokens').replace('{n}', formatNumber(m.tokens))));
    if (m.tools && m.tools.length) bits.push(esc(t('ai_tools_used').replace('{t}', [...new Set(m.tools)].join(', '))));
    return bits.length ? `<div class="ai-meta">${bits.join(' · ')}</div>` : '';
}

function aiRenderThread() {
    const el = document.getElementById('ai-thread');
    const msgs = (_ai.conv && _ai.conv.messages) || [];
    if (!msgs.length) {
        el.innerHTML = `<div class="ai-empty"><p>${esc(t('ai_empty'))}</p><ul>
            <li>${esc(t('ai_ex1'))}</li><li>${esc(t('ai_ex2'))}</li><li>${esc(t('ai_ex3'))}</li></ul>
            <p class="text-muted fs-08">${esc(t('ai_disclaimer'))}</p></div>`;
        return;
    }
    el.innerHTML = msgs.map(m => m.role === 'user'
        ? `<div class="ai-bubble ai-user">${esc(m.content).replace(/\n/g, '<br>')}</div>`
        : `<div class="ai-bubble ai-bot">${aiMarkdown(m.content)}${_aiMeta(m)}</div>`).join('');
    el.scrollTop = el.scrollHeight;
}

function _aiProgress(ev) {
    const el = document.getElementById('ai-progress');
    let text = '';
    if (ev.phase === 'thinking') text = t('ai_ph_thinking').replace('{n}', ev.round);
    else if (ev.phase === 'tool') {
        const a = ev.args || {};
        const brief = ['query', 'field', 'range_from'].filter(k => a[k]).map(k => `${k}=${a[k]}`).join(' ');
        text = t('ai_ph_tool').replace('{t}', ev.name) + (brief ? ` (${brief})` : '');
    } else if (ev.phase === 'composing') text = t('ai_ph_composing');
    el.innerHTML = `<span class="spinner-text">${esc(text)}</span>`;
    el.classList.remove('hidden');
}

function _aiBusy(on) {
    _ai.busy = on;
    document.getElementById('ai-send').disabled = on;
    document.getElementById('ai-stop').classList.toggle('hidden', !on);
    if (!on) document.getElementById('ai-progress').classList.add('hidden');
}

async function aiSend() {
    if (_ai.busy) return;
    const inp = document.getElementById('ai-input');
    const q = inp.value.trim();
    if (!q) return;
    aiMsg('');
    if (!_ai.conv) _ai.conv = {id: null, messages: []};
    _ai.conv.messages.push({role: 'user', content: q});
    aiRenderThread();
    inp.value = '';
    _aiBusy(true);
    _aiProgress({phase: 'thinking', round: 1});
    _ai.abort = new AbortController();
    try {
        const resp = await fetch(`${API}/ai/chat`, {method: 'POST', signal: _ai.abort.signal,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: q, conversation_id: _ai.conv.id, server: _ai.server, lang: getLang()})});
        if (resp.status === 401) { window.location.href = '/login'; return; }
        if (!resp.ok) {
            let d = {};
            try { d = await resp.json(); } catch (_) { d = {error: `HTTP ${resp.status}`}; }
            _localizeServerText(d);
            if (d.need_signin) aiShowSignin();
            aiMsg(d.error || `HTTP ${resp.status}`, 'err');
            _ai.conv.messages.pop();
            aiRenderThread();
            return;
        }
        await _aiReadStream(resp);
    } catch (e) {
        if (e.name !== 'AbortError') aiMsg(String(e), 'err');
        else aiMsg(t('ai_stopped'), 'ok');
    } finally {
        _aiBusy(false);
        _ai.abort = null;
        aiLoadStatus();
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
            if (ev === 'start') { _ai.conv.id = obj.conversation_id; }
            else if (ev === 'progress') _aiProgress(obj);
            else if (ev === 'done') {
                if (obj.answer) {
                    _ai.conv.messages.push({role: 'assistant', content: obj.answer, model: obj.model,
                        tokens: obj.tokens, elapsed_ms: obj.elapsed_ms, tools: obj.tools});
                }
                if (obj.error) aiMsg(t('ai_failed') + jobNote(obj.error), 'err');
                aiRenderThread();
                aiLoadConvs();
            }
        }
    }
}

function aiStop() { if (_ai.abort) _ai.abort.abort(); }

// ---- Settings ---------------------------------------------------------------------

function aiToggleSettings() {
    const el = document.getElementById('ai-settings');
    el.classList.toggle('hidden');
    if (!el.classList.contains('hidden')) aiRenderSettings();
}

function aiRenderSettings() {
    const d = _ai.status;
    if (!d) return;
    const s = d.settings;
    const num = (id, v, min, max, step) => `<input type="number" id="${id}" value="${esc(String(v ?? ''))}" min="${min}" max="${max}" ${step ? `step="${step}"` : ''}>`;
    const chk = (id, v, label) => `<label class="sec-chk"><input type="checkbox" id="${id}" ${v ? 'checked' : ''}> ${esc(label)}</label>`;
    const mg = d.mcp_graylog;
    const enabledTools = (s.mcp_graylog_tools && s.mcp_graylog_tools.length) ? s.mcp_graylog_tools : d.mcp_graylog_default;
    const toolBoxes = d.mcp_graylog_default.map(n => `<label class="sec-chk ai-tool"><input type="checkbox" class="ai-mg-tool" value="${esc(n)}" ${enabledTools.includes(n) ? 'checked' : ''}> <code>${esc(n)}</code></label>`).join('');
    // the address the browser uses (behind a reverse proxy the server sees another)
    const mcpCfg = JSON.stringify({mcpServers: {'jt-glogarch': {type: 'http', url: window.location.origin + '/mcp',
        headers: {Authorization: 'Bearer <Graylog API token>'}}}}, null, 2);
    document.getElementById('ai-settings').innerHTML = `
        <h3>${esc(t('ai_set_title'))}</h3>
        <div class="sec-form">
            <div class="sec-wide">${chk('ai-s-enabled', s.enabled, t('ai_s_enabled'))}</div>
            <div class="sec-wide"><label>${esc(t('ai_s_url'))}</label><input type="text" id="ai-s-url" value="${esc(s.url)}" placeholder="http://10.0.0.5:8080/v1"></div>
            <div><label>${esc(t('ai_model'))}</label><input type="text" id="ai-s-model" value="${esc(s.model)}"></div>
            <div><label>${esc(t('ai_s_key'))}</label>${_secretField('ai-s-key', s.api_key)}</div>
            <div><label>${esc(t('ai_s_timeout'))}</label>${num('ai-s-timeout', s.timeout_seconds, 10, 900)}</div>
            <div><label>${esc(t('ai_s_temperature'))}</label>${num('ai-s-temp', s.temperature, 0, 1, '0.1')}</div>
            <div><label>${esc(t('ai_s_rounds'))}</label>${num('ai-s-rounds', s.max_tool_rounds, 1, 10)}</div>
            <div><label>${esc(t('ai_s_range'))}</label>${num('ai-s-range', s.max_range_hours, 1, 168)}</div>
            <div><label>${esc(t('ai_s_daily'))}</label>${num('ai-s-daily', s.daily_tokens, 0, 1000000000)}</div>
            <div><label>${esc(t('ai_s_monthly'))}</label>${num('ai-s-monthly', s.monthly_tokens, 0, 1000000000)}</div>
            <div><label>${esc(t('ai_s_retention'))}</label>${num('ai-s-retention', s.chat_retention_days, 0, 3650)}</div>
            <div class="sec-wide">${chk('ai-s-external', s.allow_external, t('ai_s_external'))}
                <div class="text-muted fs-08">${esc(t('ai_s_external_note'))}</div></div>
        </div>
        <div class="sec-save-row ai-btns">
            <button class="btn-secondary" data-act="aiTest">${icon('refresh', 16)} ${esc(t('btn_test_connection'))}</button>
            <button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button>
        </div>
        <div id="ai-test-result" class="fs-085"></div>
        <h3 class="ai-sub">${esc(t('ai_mcp_title'))}</h3>
        <p class="text-muted fs-085">${esc(t('ai_mcp_help'))}</p>
        <div>${chk('ai-s-mcp', s.mcp_enabled, t('ai_s_mcp'))}</div>
        <pre class="ai-code"><code>${esc(mcpCfg)}</code></pre>
        <h3 class="ai-sub">mcp_graylog ${esc(mg.version)}</h3>
        <p class="fs-085 ${mg.available ? 'pk-ok' : 'pk-err'}">${esc(mg.available ? t('ai_mg_ok') : t('ai_mg_unavailable') + ' ' + mg.error)}</p>
        <div class="ai-tools">${toolBoxes}</div>
        <p class="text-muted fs-08">${esc(t('ai_mg_note'))}</p>
        <div class="sec-save-row"><button class="btn-primary" data-act="aiSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
}

function _aiSettingsBody() {
    const v = id => document.getElementById(id).value;
    const c = id => document.getElementById(id).checked;
    return {
        enabled: c('ai-s-enabled'), url: v('ai-s-url').trim(), model: v('ai-s-model').trim(), api_key: v('ai-s-key'),
        timeout_seconds: Number(v('ai-s-timeout')), temperature: Number(v('ai-s-temp')),
        max_tool_rounds: Number(v('ai-s-rounds')), max_range_hours: Number(v('ai-s-range')),
        daily_tokens: Number(v('ai-s-daily')), monthly_tokens: Number(v('ai-s-monthly')),
        chat_retention_days: Number(v('ai-s-retention')), allow_external: c('ai-s-external'),
        mcp_enabled: c('ai-s-mcp'),
        mcp_graylog_tools: [...document.querySelectorAll('.ai-mg-tool:checked')].map(x => x.value),
    };
}

async function aiSaveSettings() {
    const d = await fetchJSON(`${API}/ai/settings`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(_aiSettingsBody())});
    if (!d || d.error) { aiMsg(d && d.error, 'err'); return; }
    aiMsg(t('ai_saved'), 'ok');
    await aiLoadStatus();
}

async function aiTest() {
    // test what is in the form: save it first (the server tests the saved settings)
    const saved = await fetchJSON(`${API}/ai/settings`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(_aiSettingsBody())});
    const el = document.getElementById('ai-test-result');
    if (!saved || saved.error) { el.innerHTML = `<span class="pk-err">${esc(saved && saved.error)}</span>`; return; }
    el.innerHTML = `<span class="spinner-text">${esc(t('ai_testing'))}</span>`;
    const d = await fetchJSON(`${API}/ai/test`, {method: 'POST'});
    if (!d || d.error) { el.innerHTML = `<span class="pk-err">${esc(d && d.error)}</span>`; return; }
    el.innerHTML = `<span class="pk-ok">${esc(t('ai_test_ok').replace('{r}', d.reply || '—').replace('{n}', formatNumber(d.tokens)))}</span>`
        + (d.model_listed ? '' : ` <span class="pk-err">${esc(t('ai_test_model_missing').replace('{m}', (d.models || []).join(', ')))}</span>`);
}

document.addEventListener('DOMContentLoaded', aiInit);

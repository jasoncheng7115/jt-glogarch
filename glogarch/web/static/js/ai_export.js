/* jt-glogarch — AI chat 1.37: an answer as a Graylog dashboard, a conversation as a
 * summary PDF, a table with times as a timeline. Both exports list the charts the
 * SERVER made from the queries the answers ran (glogarch/ai/charts.py); the page
 * only picks. Every value from logs, the model or Graylog goes through esc(). */

const _aix = {mode: '', mid: 0, charts: [], server: '', job: '', timer: null};
const AIX_VIS = {timeseries: ['line', 'area', 'bar', 'table'], bar: ['bar', 'pie', 'table'],
                 table: ['table'], number: ['numeric']};
const AIX_RANGES = ['8h', '1d', '7d', '30d', 'custom'];

// an answer whose calls can be charts gets the dashboard button (the server decides which)
function aixChartable(m) {
    return (m.calls || []).some(c => c && c.ok && ['aggregate', 'top_values', 'count_messages'].includes(c.name)
        && c.range && c.range.from);
}

function _aixOpen(titleKey, iconName) {
    const h = document.getElementById('ai-export-title');
    h.innerHTML = `${icon(iconName, 18)} ${esc(t(titleKey))}`;
    document.getElementById('ai-export-content').innerHTML = `<p class="text-muted"><span class="spinner-text">${esc(t('loading'))}</span></p>`;
    document.getElementById('ai-export-modal').style.display = 'flex';
}

function aiExportClose() {
    clearTimeout(_aix.timer);
    _aix.timer = null;
    document.getElementById('ai-export-modal').style.display = 'none';
}

function _aixErr(text) {
    const box = document.getElementById('aix-msg');
    if (!box) return;
    box.className = text ? 'pk-message pk-err' : 'pk-message hidden';
    box.textContent = text || '';
}

function _aixKind(c) {
    return `<span class="aix-kind">${esc(t('ai_chart_kind_' + c.kind))}</span>`;
}

// a chart's default title in the reader's language, from what it counts and how it groups
const AIX_PICTURES = ['mermaid', 'timeline', 'html', 'svg'];

function aixChartTitle(c) {
    if (AIX_PICTURES.includes(c.kind)) return c.title || t('ai_chart_kind_' + c.kind);
    const sep = getLang() === 'en' ? ', ' : '、';
    const fieldOf = g => String(g).split(':')[0];
    const metric = m => {
        const [fn, f] = String(m).split(':');
        if (fn === 'count' && !f) return t('ai_ct_count');
        if (fn === 'card') return t('ai_ct_card').replace('{f}', f);
        if (f === 'timestamp' && fn === 'min') return t('ai_ct_first');
        if (f === 'timestamp' && (fn === 'max' || fn === 'latest')) return t('ai_ct_last');
        return f ? `${fn}(${f})` : fn;
    };
    const ms = (c.metrics || ['count']).map(metric).join(sep);
    const gs = (c.group_by || []).map(fieldOf).filter(f => f !== 'timestamp');
    if (c.kind === 'number') {
        // a count alone says nothing: name what it counts (same rule as charts.py local_title)
        let q = String(c.query || '').replace(/\s+/g, ' ').trim();
        if (q === '*' || q === '*:*') q = '';
        if (q.length > 40) q = q.slice(0, 39) + '…';
        return q ? (getLang() === 'en' ? `${ms} (${q})` : `${ms}（${q}）`) : ms;
    }
    if (c.kind === 'timeseries') return t('ai_ct_trend').replace('{m}', ms) + (gs.length ? t('ai_ct_split').replace('{g}', gs.join(sep)) : '');
    if (c.kind === 'bar') return t('ai_ct_top').replace('{g}', gs.join(sep)).replace('{m}', ms);
    return t('ai_ct_by').replace('{m}', ms).replace('{g}', gs.join(sep));
}

function _aixChartRows(withVis) {
    return _aix.charts.map((c, k) => {
        const vis = (AIX_VIS[c.kind] || ['table']).map(v => `<option value="${v}">${esc(t('ai_dash_vis_' + v))}</option>`).join('');
        return `<div class="aix-chart">
            <label class="sec-chk aix-pick"><input type="checkbox" id="aix-on-${k}" checked></label>
            <div class="aix-chart-main">
                <input type="text" class="pk-input aix-title" id="aix-t-${k}" maxlength="120" value="${esc(aixChartTitle(c))}" aria-label="${esc(t('ai_chart_title'))}">
                <div class="aix-chart-meta">${_aixKind(c)}${AIX_PICTURES.includes(c.kind) ? '' : `<code class="aix-q">${esc(c.query || '*')}</code>`}</div>
            </div>
            ${withVis ? `<select id="aix-v-${k}" aria-label="${esc(t('ai_dash_vis'))}">${vis}</select>` : ''}
        </div>`;
    }).join('');
}

function _aixPicked(withVis) {
    const out = [];
    _aix.charts.forEach((c, k) => {
        const on = document.getElementById(`aix-on-${k}`);
        if (!on || !on.checked) return;
        const p = {id: c.id, title: (document.getElementById(`aix-t-${k}`).value || '').trim()};
        if (withVis) p.vis = document.getElementById(`aix-v-${k}`).value;
        out.push(p);
    });
    return out;
}

// ---- Graylog dashboard from one answer -------------------------------------------

async function aiDashboardDialog(e) {
    const btn = e && e.target && e.target.closest('[data-act]');
    const i = btn ? Number(btn.dataset.arg) : -1;
    const m = ((_ai.conv && _ai.conv.messages) || [])[i];
    if (!m || !m.id) return;
    _aix.mode = 'dash';
    _aix.mid = m.id;
    _aixOpen('ai_dash_title', 'view_grid');
    const d = await fetchJSON(`${API}/ai/messages/${encodeURIComponent(m.id)}/charts`);
    const box = document.getElementById('ai-export-content');
    if (!d || d.error) { box.innerHTML = `<p class="pk-err">${esc(d && d.error || '')}</p>`; return; }
    _aix.charts = d.charts || [];
    _aix.server = d.server || '';
    if (!_aix.charts.length) {
        box.innerHTML = `<p class="text-muted">${esc(t('ai_dash_none'))}</p>
            <div class="sec-ai-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button></div>`;
        return;
    }
    const conv = _ai.conv || {};
    const ranges = AIX_RANGES.map(r => `<option value="${r}"${r === '1d' ? ' selected' : ''}>${esc(t('ai_dash_r_' + r))}</option>`).join('');
    box.innerHTML = `
        <div class="ai-note aix-help">${icon('info', 14)}<span>${esc(t('ai_dash_help'))}</span></div>
        <div class="sec-form aix-form">
            <div class="sec-wide"><label for="aix-name">${esc(t('ai_dash_name'))}</label>
                <input type="text" id="aix-name" class="pk-input" maxlength="120" value="${esc(conv.title || '')}"></div>
            <div><label for="aix-range">${esc(t('ai_dash_range'))}</label><select id="aix-range" data-act-change="aixRangeChange">${ranges}</select></div>
            <div class="aix-custom hidden" id="aix-custom">
                <label for="aix-from">${esc(t('ai_dash_from'))}</label><input type="datetime-local" id="aix-from" class="pk-input">
                <label for="aix-to">${esc(t('ai_dash_to'))}</label><input type="datetime-local" id="aix-to" class="pk-input"></div>
        </div>
        <h4 class="aix-h">${esc(t('ai_dash_charts'))}</h4>
        <div class="aix-charts">${_aixChartRows(true)}</div>
        <p class="text-muted fs-08">${esc(t('ai_dash_time_auto'))}</p>
        <p class="text-muted fs-08">${esc(t('ai_dash_server').replace('{s}', _aix.server || '—'))}</p>
        <div class="pk-message hidden" id="aix-msg"></div>
        <div class="sec-ai-btns" id="aix-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" id="aix-go" data-act="aiDashboardCreate">${icon('view_grid', 16)} ${esc(t('ai_dash_create'))}</button></div>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

function aixRangeChange() {
    const v = (document.getElementById('aix-range') || {}).value;
    const c = document.getElementById('aix-custom');
    if (c) c.classList.toggle('hidden', v !== 'custom');
}

function _aixIso(id) {
    const v = (document.getElementById(id) || {}).value;
    if (!v) return '';
    const d = new Date(v);              // the reader's local time
    return isNaN(d) ? '' : d.toISOString();
}

async function aiDashboardCreate() {
    const widgets = _aixPicked(true);
    const title = (document.getElementById('aix-name').value || '').trim();
    if (!title) { _aixErr(t('srv_ai_dash_title')); return; }
    if (!widgets.length) { _aixErr(t('srv_ai_pick_chart')); return; }
    const range = document.getElementById('aix-range').value;
    const body = {title, range, widgets};
    if (range === 'custom') { body.from = _aixIso('aix-from'); body.to = _aixIso('aix-to'); }
    const go = document.getElementById('aix-go');
    go.disabled = true;
    go.innerHTML = `${icon('view_grid', 16)} ${esc(t('ai_dash_creating'))}`;
    _aixErr('');
    const d = await fetchJSON(`${API}/ai/messages/${encodeURIComponent(_aix.mid)}/graylog-dashboard`,
        {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    if (!d || d.error) {
        go.disabled = false;
        go.innerHTML = `${icon('view_grid', 16)} ${esc(t('ai_dash_create'))}`;
        if (d && d.need_signin && typeof aiShowSignin === 'function') { aiExportClose(); aiShowSignin(); }
        _aixErr(d && d.error);
        return;
    }
    const url = /^https?:\/\//.test(d.url || '') ? d.url : '';
    document.getElementById('ai-export-content').innerHTML = `
        <div class="pk-message pk-ok">${icon('check', 16)} ${esc(t('ai_dash_done').replace('{t}', title))}</div>
        <div class="sec-ai-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
            ${url ? `<a class="btn-primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${icon('open_window', 16)} ${esc(t('ai_dash_open'))}</a>` : ''}</div>`;
}

// ---- summary PDF of the whole conversation ---------------------------------------

async function aiSummaryDialog() {
    const conv = _ai.conv;
    if (!conv || !conv.id) return;
    _aix.mode = 'pdf';
    _aixOpen('ai_summary_title', 'page');
    const [d, rp] = await Promise.all([fetchJSON(`${API}/ai/conversations/${encodeURIComponent(conv.id)}/charts`),
                                       fetchJSON(`${API}/reports`)]);
    const box = document.getElementById('ai-export-content');
    if (!d || d.error) { box.innerHTML = `<p class="pk-err">${esc(d && d.error || '')}</p>`; return; }
    _aix.charts = d.charts || [];
    _aix.server = d.server || '';
    // the look of an existing report (owner 2026-11-27: logo, watermark ... "參考統計報表那邊的設定")
    _aix.styles = ((rp && rp.items) || []).map(r => ({name: r.name, cfg: r.config || {}}));
    let pick = '';
    try { pick = localStorage.getItem('jt-ai-sum-style') || ''; } catch (e) { pick = ''; }
    // the look set in the AI settings comes first and is the default
    const aiStyle = ((_ai.status || {}).settings || {}).summary_style || {};
    _aix.styles.unshift({name: '@ai', cfg: aiStyle, label: t('ai_summary_style_ai')});
    if (pick !== '-' && !_aix.styles.some(x => x.name === pick)) pick = '@ai';
    const opts = `<option value="@ai"${pick === '@ai' ? ' selected' : ''}>${esc(t('ai_summary_style_ai'))}</option>`
        + `<option value="-"${pick === '-' ? ' selected' : ''}>${esc(t('ai_summary_style_none'))}</option>`
        + _aix.styles.filter(x => x.name !== '@ai').map(x => `<option value="${esc(x.name)}"${x.name === pick ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    box.innerHTML = `
        <div class="ai-note aix-help">${icon('info', 14)}<span>${esc(t('ai_summary_help'))}</span></div>
        <div class="sec-form aix-form">
            <div class="sec-wide"><label for="aix-name">${esc(t('ai_summary_name'))}</label>
                <input type="text" id="aix-name" class="pk-input" maxlength="120" value=""></div>
            <div class="sec-wide"><label for="aix-style">${esc(t('ai_summary_style'))}</label>
                <div class="aix-style-row"><select id="aix-style" data-act-change="aixStyleChange">${opts}</select>
                    <span id="aix-style-info" class="aix-style-info"></span></div>
                <div class="text-muted fs-08">${esc(t('ai_summary_style_hint'))}</div></div>
        </div>
        <h4 class="aix-h">${esc(t('ai_summary_charts'))}</h4>
        ${_aix.charts.length ? `<div class="aix-charts">${_aixChartRows(false)}</div>` : `<p class="text-muted">${esc(t('ai_summary_no_charts'))}</p>`}
        <div class="pk-message hidden" id="aix-msg"></div>
        <div class="sec-ai-btns" id="aix-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" id="aix-go" data-act="aiSummaryStart">${icon('page', 16)} ${esc(t('ai_summary_start'))}</button></div>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
    aixStyleChange();
}

// what the picked report's look brings: its cover logo (on the cover's colour) and the watermark
function aixStyleChange() {
    const sel = document.getElementById('aix-style');
    const info = document.getElementById('aix-style-info');
    if (!sel || !info) return;
    try { localStorage.setItem('jt-ai-sum-style', sel.value); } catch (e) { /* storage blocked: not remembered */ }
    const st = (_aix.styles || []).find(x => x.name === sel.value);
    if (!st) { info.innerHTML = ''; return; }
    const c = st.cfg;
    const logo = /^data:image\/(png|jpeg|gif|webp|svg\+xml);base64,/.test(c.logo_data_uri || '')
        ? `<span class="aix-logo logo-preview-cover"><img src="${esc(c.logo_data_uri)}" alt=""></span>`
        : `<span class="text-muted fs-08">${esc(t('ai_summary_style_nologo'))}</span>`;
    const wm = `<span class="aix-wm">${icon(c.watermark_enabled ? 'check' : 'close', 12)}${esc(t(c.watermark_enabled ? 'ai_summary_style_wm_on' : 'ai_summary_style_wm_off'))}</span>`;
    info.innerHTML = logo + wm;
}

async function aiSummaryStart() {
    const conv = _ai.conv;
    if (!conv || !conv.id) return;
    const picked = _aixPicked(false);
    const titles = {};
    // a title left as the default is the model's to choose (it names charts by what they show);
    // only a title the reader typed overrides it
    picked.forEach(p => {
        const c = _aix.charts.find(x => x.id === p.id);
        if (p.title && c && p.title !== aixChartTitle(c)) titles[p.id] = p.title;
    });
    const sty = (document.getElementById('aix-style') || {}).value || '-';
    const body = {lang: getLang(), title: (document.getElementById('aix-name').value || '').trim(),
                  charts: picked.map(p => p.id), chart_titles: titles};
    if (sty !== '-') body.style = sty;
    if (_ai.llm) body.llm = _ai.llm;
    const go = document.getElementById('aix-go');
    go.disabled = true;
    _aixErr('');
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(conv.id)}/summary-pdf`,
        {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    if (!d || d.error) {
        go.disabled = false;
        if (d && d.need_signin && typeof aiShowSignin === 'function') { aiExportClose(); aiShowSignin(); return; }
        if (d && d.job_id) { _aix.job = d.job_id; _aixPoll(); return; }   // one already running: follow it
        _aixErr(d && d.error);
        return;
    }
    _aix.job = d.job_id;
    _aixPoll();
}

async function _aixPoll() {
    const btns = document.getElementById('aix-btns');
    const d = await fetchJSON(`${API}/ai/summary-jobs/${encodeURIComponent(_aix.job)}`);
    if (!document.getElementById('aix-btns') || _aix.mode !== 'pdf') return;   // closed meanwhile
    if (!d || d.error && !d.done) {
        _aixErr(d && d.error);
        return;
    }
    if (!d.done) {
        const step = d.detail ? (typeof trSrv === 'function' ? trSrv(d.detail) : d.detail) : '';
        btns.innerHTML = `<span class="aix-bg text-muted fs-08">${esc(t('ai_summary_bg'))}</span>
            <span class="aix-running-box"><span class="spinner-text aix-running">${esc(t('ai_summary_running').replace('{p}', Math.round(d.progress || 0)))}</span>
                ${step ? `<span class="aix-step text-muted fs-08">${esc(step)}</span>` : ''}</span>
            <button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>`;
        _aix.timer = setTimeout(_aixPoll, 2000);
        return;
    }
    if (d.error) {
        _aixErr(t('ai_summary_failed').replace('{e}', d.error));
        btns.innerHTML = `<button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>`;
        return;
    }
    const dl = /^\/api\/reports\/history\/\d+\/download$/.test(d.download || '') ? d.download : '';
    if (d.warning) _aixErr(t('ai_summary_no_text').replace('{e}', d.warning));
    btns.innerHTML = `<span class="aix-done">${icon('check', 16)} ${esc(t('ai_summary_done'))} <span class="text-muted fs-08">${esc(t('ai_summary_where'))}</span></span>
        <button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
        ${dl ? `<a class="btn-primary" href="${esc(dl)}">${icon('download', 16)} ${esc(t('ai_summary_download'))}</a>` : ''}`;
}

// ---- a table whose cells are times -> a timeline (owner 2026-11-27) ---------------
// Drawn here from the table's own cells: no model round trip, the same values.

const AIX_TL_MAX = 60;

function aixParseTime(s) {
    s = String(s || '').trim();
    if (!s) return null;
    let m = s.match(/^(\d{4})[-/](\d{2})[-/](\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?\s*(Z|[+-]\d{2}:?\d{2})?$/);
    if (m) {
        const iso = `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6] || '00'}${m[7] ? '.' + m[7].slice(0, 3).padEnd(3, '0') : ''}${m[8] ? m[8].replace(/^([+-]\d{2})(\d{2})$/, '$1:$2') : ''}`;
        const d = Date.parse(iso);
        return isNaN(d) ? null : d;
    }
    m = s.match(/^(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (m) return new Date(2000, Number(m[1]) - 1, Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5] || 0)).getTime();
    m = s.match(/^(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?$/);
    if (m && Number(m[1]) < 24) return Date.UTC(2000, 0, 1, Number(m[1]), Number(m[2]), Number(m[3] || 0));
    return null;
}

// {label, start, end?} rows from a table, or null when it has no time column
function aixTimelineRows(table) {
    const head = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    const body = Array.from(table.querySelectorAll('tbody tr')).map(tr => Array.from(tr.children).map(td => td.textContent.trim()));
    if (body.length < 2 || !head.length) return null;
    const timeCols = [];
    head.forEach((h, k) => {
        const vals = body.map(r => r[k]).filter(v => v);
        if (vals.length < 2) return;
        const ok = vals.filter(v => aixParseTime(v) !== null).length;
        if (ok / vals.length >= 0.8) timeCols.push(k);
    });
    if (!timeCols.length) return null;
    const [a, b] = timeCols;
    const labelCol = head.findIndex((_, k) => !timeCols.includes(k));
    const rows = body.slice(0, AIX_TL_MAX).map(r => {
        const start = aixParseTime(r[a]);
        let end = b !== undefined ? aixParseTime(r[b]) : null;
        if (end !== null && start !== null && end < start && end - start > -86400000 && /^\d{1,2}:/.test(r[b])) end += 86400000;
        return {label: labelCol >= 0 ? r[labelCol] : '', start, end: end !== null && start !== null && end >= start ? end : null,
                startText: r[a], endText: b !== undefined ? r[b] : ''};
    }).filter(r => r.start !== null);
    if (rows.length < 2) return null;
    return {rows, startName: head[a], endName: b !== undefined ? head[b] : '', more: Math.max(0, body.length - AIX_TL_MAX)};
}

function _aixFmt(ms, span, timeOnly) {
    const d = new Date(ms);
    const p = n => String(n).padStart(2, '0');
    const get = timeOnly ? ['getUTCHours', 'getUTCMinutes', 'getUTCSeconds', 'getUTCMonth', 'getUTCDate']
                         : ['getHours', 'getMinutes', 'getSeconds', 'getMonth', 'getDate'];
    const hm = `${p(d[get[0]]())}:${p(d[get[1]]())}` + (span < 3600000 ? `:${p(d[get[2]]())}` : '');
    return span > 86400000 && !timeOnly ? `${p(d[get[3]]() + 1)}-${p(d[get[4]]())} ${hm}` : hm;
}

function aixTimelineSvg(tl) {
    const rows = tl.rows;
    const lo = Math.min(...rows.map(r => r.start));
    const hi = Math.max(...rows.map(r => r.end !== null ? r.end : r.start));
    const span = Math.max(hi - lo, 1000);
    const timeOnly = lo < Date.UTC(2000, 0, 3) && lo >= Date.UTC(2000, 0, 1);
    const W = 760, L = 170, R = 16, rowH = 22, top = 8, axisH = 28;
    const H = top + rows.length * rowH + axisH;
    const x = v => L + (v - lo) / span * (W - L - R);
    // round steps (10:00, 10:30 ...), at most about 6 of them, aligned to the reader's clock
    const M = 60000;
    const step = [1, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 10080].map(m => m * M).find(st => span / st <= 6) || 10080 * M;
    const off = timeOnly ? 0 : new Date(lo).getTimezoneOffset() * M;
    const ticks = [];
    for (let v = Math.ceil((lo - off) / step) * step + off; v <= hi; v += step) {
        const px = x(v);
        const anchor = px < L + 20 ? 'start' : px > W - R - 20 ? 'end' : 'middle';
        ticks.push(`<line class="aix-tl-grid" x1="${px.toFixed(1)}" x2="${px.toFixed(1)}" y1="${top}" y2="${H - axisH}"/>`
            + `<text class="aix-tl-tick" x="${px.toFixed(1)}" y="${H - axisH + 16}" text-anchor="${anchor}">${esc(_aixFmt(v, span, timeOnly))}</text>`);
    }
    const marks = rows.map((r, k) => {
        const y = top + k * rowH;
        const label = r.label.length > 24 ? r.label.slice(0, 23) + '…' : r.label;
        const tip = `${r.label} · ${r.startText}${r.end !== null ? ' → ' + r.endText : ''}`;
        const mark = r.end !== null && x(r.end) - x(r.start) >= 3
            ? `<rect class="aix-tl-bar" x="${x(r.start).toFixed(1)}" y="${y + 5}" width="${(x(r.end) - x(r.start)).toFixed(1)}" height="${rowH - 10}" rx="3"/>`
            : `<circle class="aix-tl-dot" cx="${x(r.start).toFixed(1)}" cy="${y + rowH / 2}" r="5"/>`;
        return `<g class="aix-tl-row"><title>${esc(tip)}</title>`
            + `<text class="aix-tl-label" x="${L - 8}" y="${y + rowH / 2 + 4}" text-anchor="end">${esc(label)}</text>${mark}</g>`;
    }).join('');
    return `<svg class="aix-tl-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t('ai_timeline'))}">${ticks.join('')}${marks}</svg>`;
}

function aiTimelineDecorate(el) {
    el.querySelectorAll('.ai-bot .ai-block').forEach(box => {
        const table = box.querySelector(':scope > .table-wrap table');
        if (!table || box.querySelector('.ai-block-tl')) return;
        const tl = aixTimelineRows(table);
        if (!tl) return;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.title = t('ai_timeline_tip');
        btn.setAttribute('aria-label', btn.title);
        btn.setAttribute('aria-pressed', 'false');
        btn.className = 'btn-secondary btn-sm ai-block-tl';
        btn.innerHTML = `${icon('clock', 13)}<span>${esc(t('ai_timeline'))}</span>`;
        btn.addEventListener('click', () => {
            let fig = box.nextElementSibling;
            if (fig && fig.classList.contains('aix-tl')) {
                fig.remove();
                btn.setAttribute('aria-pressed', 'false');
                return;
            }
            fig = document.createElement('figure');
            fig.className = 'aix-tl';
            const note = tl.more ? `<figcaption class="text-muted fs-08">${esc(t('ai_timeline_more').replace('{n}', formatNumber(tl.more)))}</figcaption>` : '';
            const legend = `<figcaption class="aix-tl-legend text-muted fs-08">${icon('clock', 12)}${esc(tl.startName)}${tl.endName ? ' → ' + esc(tl.endName) : ''}</figcaption>`;
            fig.innerHTML = legend + aixTimelineSvg(tl) + note;
            box.parentNode.insertBefore(fig, box.nextSibling);
            btn.setAttribute('aria-pressed', 'true');
        });
        box.appendChild(btn);
    });
}


// ---- the conversation as an investigation case (owner 2026-11-27) ---------------------

function aiCaseDialog() {
    const conv = _ai.conv;
    if (!conv || !conv.id) return;
    _aix.mode = 'case';
    _aixOpen('ai_case_title', 'log');
    const sev = ['low', 'medium', 'high'].map(v => `<option value="${v}"${v === 'medium' ? ' selected' : ''}>${esc(t('sec_sev_' + v))}</option>`).join('');
    document.getElementById('ai-export-content').innerHTML = `
        <div class="ai-note aix-help">${icon('info', 14)}<span>${esc(t('ai_case_help'))}</span></div>
        <div class="sec-form aix-form">
            <div class="sec-wide"><label for="aix-case-title">${esc(t('case_th_title'))}</label>
                <input type="text" id="aix-case-title" class="pk-input" maxlength="200" value="${esc(conv.title || '')}"></div>
            <div><label for="aix-case-sev">${esc(t('sec_th_severity'))}</label><select id="aix-case-sev">${sev}</select></div>
        </div>
        <div class="pk-message hidden" id="aix-msg"></div>
        <div class="sec-ai-btns" id="aix-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" id="aix-go" data-act="aiCaseCreate">${icon('log', 16)} ${esc(t('ai_case_create'))}</button></div>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

async function aiCaseCreate() {
    const conv = _ai.conv;
    if (!conv || !conv.id) return;
    const go = document.getElementById('aix-go');
    go.disabled = true;
    _aixErr('');
    const d = await fetchJSON(`${API}/ai/conversations/${encodeURIComponent(conv.id)}/to-case`, {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: (document.getElementById('aix-case-title').value || '').trim(),
                              severity: document.getElementById('aix-case-sev').value, lang: getLang()})});
    if (!d || d.error) { go.disabled = false; _aixErr(d && d.error); return; }
    const url = /^\/security\?case=\d+$/.test(d.url || '') ? d.url : '';
    document.getElementById('ai-export-content').innerHTML = `
        <div class="pk-message pk-ok">${icon('check', 16)} ${esc(t('ai_case_done').replace('{n}', d.id))}</div>
        <div class="sec-ai-btns"><button class="btn-secondary" data-act="aiExportClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
            ${url ? `<a class="btn-primary" href="${esc(url)}">${icon('log', 16)} ${esc(t('ai_case_open'))}</a>` : ''}</div>`;
}

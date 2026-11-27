// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Jason Cheng (Jason Tools)
// Field mapping for the built-in detectors (added 1.35): where this site's logs
// keep what each detection reads. Rendered inside the Security settings panel.
const _fm = {form: null, open: false, results: {}, busy: ''};

const FM_GROUPS = ['auth', 'ids', 'waf', 'other'];

function fmView() { return (_sec.data && _sec.data.field_map) || null; }

// What the inputs hold now (kept across a re-render of the settings panel).
function fmCapture() {
    const box = document.getElementById('sec-fm');
    if (!box) return;
    _fm.open = box.open;
    const form = {};
    box.querySelectorAll('input[data-fm]').forEach(i => { form[i.dataset.fm] = i.value; });
    if (Object.keys(form).length) _fm.form = form;
}

function fmValue(key) {
    const v = fmView();
    if (_fm.form && key in _fm.form) return _fm.form[key];
    return (v && v.stored && v.stored[key]) || '';
}

function fmPanelHtml() {
    const v = fmView();
    if (!v) return '';
    const changed = Object.keys(v.stored || {}).length;
    const groups = FM_GROUPS.map(g => {
        const rows = (v.groups[g] || []).map(k => {
            const kind = v.kinds[k];
            return `<div class="sec-fm-row${kind === 'query' ? ' sec-fm-q' : ''}">
                <label for="fm-${esc(k)}">${esc(t('fm_k_' + k))}</label>
                <input type="text" id="fm-${esc(k)}" data-fm="${esc(k)}" maxlength="500" value="${esc(fmValue(k))}" placeholder="${esc(v.defaults[k])}">
                <div class="text-muted fs-08">${esc(t(kind === 'fields' ? 'fm_hint_list' : (kind === 'query' ? 'fm_hint_query' : 'fm_hint_field')))}</div>
            </div>`;
        }).join('');
        const btn = g === 'other' ? '' : `<button type="button" class="btn-sm btn-secondary" data-act="fmDetect" data-args="${esc(JSON.stringify([g]))}" ${_fm.busy ? 'disabled' : ''}>${icon('search', 14)} ${esc(t(_fm.busy === g ? 'fm_detecting' : 'fm_detect'))}</button>`;
        return `<div class="sec-fm-group"><div class="sec-fm-head"><h4>${esc(t('fm_g_' + g))}</h4>${btn}</div>
            ${rows}<div class="sec-fm-res" id="fm-res-${esc(g)}">${fmResultHtml(g)}</div></div>`;
    }).join('');
    return `<details class="sec-fm" id="sec-fm" ${_fm.open ? 'open' : ''}>
        <summary>${icon('chevron_down', 14)} ${esc(t('fm_title'))}${changed ? ` <span class="sec-tag">${esc(t('fm_changed').replace('{n}', changed))}</span>` : ''}</summary>
        <p class="text-muted fs-085">${esc(t('fm_help'))}</p>
        ${groups}
        <div class="sec-save-row">
            <button class="btn-primary" data-act="fmSave">${icon('check', 16)} ${esc(t('fm_save'))}</button>
            <button class="btn-secondary" data-act="fmReset">${icon('refresh', 16)} ${esc(t('fm_reset'))}</button>
            <button class="btn-secondary" data-act="fmExport">${icon('download', 16)} ${esc(t('fm_export'))}</button>
            <label class="btn-secondary sec-fm-import">${icon('upload', 16)} ${esc(t('fm_import'))}
                <input type="file" accept="application/json,.json" data-act-change="fmImport" data-act-self></label>
        </div>
    </details>`;
}

function fmForm() {
    fmCapture();
    return {...(_fm.form || {})};
}

function fmPct(share, qk) {
    const s = share && share[qk];
    if (!s) return '—';
    // 4 of 9,598 rounds to 0.0%: say "<0.1%" so a field with data never reads as empty
    const pct = s.events && !s.pct ? '<0.1' : s.pct;
    return `${formatNumber(s.events)} (${pct}%)`;
}

function fmResultHtml(g) {
    const r = _fm.results[g];
    if (!r) return '';
    if (r.error) return `<div class="sec-fm-err">${esc(r.error)}</div>`;
    const qks = Object.keys(r.queries || {});
    const live = qks.filter(q => r.queries[q].events);
    const qline = qks.map(q => `<span>${esc(t('fm_k_' + q))}${esc(t('sec_colon'))}<strong>${esc(formatNumber(r.queries[q].events))}</strong></span>`).join('<span class="sep">·</span>');
    let html = `<div class="text-muted fs-085">${esc(t('fm_res_head').replace('{d}', r.days).replace('{n}', formatNumber(r.sampled || 0)))}</div><div class="sec-fm-qline">${qline}</div>`;
    if (!live.length) return html + `<div class="sec-fm-err">${esc(t('fm_res_noevents'))}</div>`;
    for (const [key, d] of Object.entries(r.fields || {})) {
        const head = live.map(q => `<th class="num">${esc(t('fm_k_' + q))}</th>`).join('');
        const rows = d.candidates.map(c => `<tr>
            <td><code>${esc(c.field)}</code>${c.current ? ` <span class="sec-tag">${esc(t('fm_current'))}</span>` : ''}${c.destination_like ? ` <span class="sec-tag sec-tag-warn">${esc(t('fm_dest_like'))}</span>` : ''}</td>
            ${live.map(q => `<td class="num">${esc(fmPct(c.share, q))}</td>`).join('')}
            <td class="sec-fm-ex">${c.examples.map(x => `<code>${esc(x)}</code>`).join(' ')}</td>
            <td>${c.current && fmIsOnly(key, c.field) ? '' : `<button type="button" class="btn-sm btn-secondary" data-act="fmUse" data-args="${esc(JSON.stringify([key, c.field]))}">${esc(t('fm_use'))}</button>`}</td>
        </tr>`).join('');
        const none = live.filter(q => d.none[q] && d.none[q].events).map(q => {
            const ins = d.none[q].inputs.map(i => `${i.input} ${formatNumber(i.events)}`).join(t('fm_list_sep'));
            return esc(t('fm_none').replace('{q}', t('fm_k_' + q)).replace('{n}', formatNumber(d.none[q].events)).replace('{i}', ins));
        });
        html += `<div class="sec-fm-key"><strong>${esc(t('fm_k_' + key))}</strong>
            <div class="table-wrap"><table class="sec-fm-table"><thead><tr><th>${esc(t('fm_th_field'))}</th>${head}<th>${esc(t('fm_th_examples'))}</th><th></th></tr></thead>
            <tbody>${rows || `<tr><td colspan="${live.length + 3}" class="text-muted">${esc(t('fm_no_candidates'))}</td></tr>`}</tbody></table></div>
            ${none.length ? `<div class="sec-fm-none">${icon('warning', 13)} ${none.join('<br>')} ${esc(t('fm_none_hint'))}</div>` : ''}</div>`;
    }
    return html;
}

// a field already the only one in its box needs no "Use" button
function fmIsOnly(key, field) {
    const v = fmValue(key) || ((fmView() || {}).defaults || {})[key] || '';
    return v.split(',').map(x => x.trim()).filter(Boolean).join(',') === field;
}

async function fmDetect(group) {
    const form = fmForm();
    _fm.busy = group;
    _fm.results[group] = null;
    fmRerender();
    const d = await fetchJSON(`${API}/security/fieldmap/detect`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({group, field_map: form})});
    _fm.busy = '';
    _fm.results[group] = (!d || d.error) ? {error: (d && d.error) || t('fm_detect_failed')} : d;
    fmRerender();
}

function fmRerender() {
    fmCapture();
    const box = document.getElementById('sec-fm');
    if (!box) return;
    box.outerHTML = fmPanelHtml();
}

function fmUse(key, field) {
    const inp = document.getElementById('fm-' + key);
    if (!inp) return;
    const v = fmView();
    if (v.kinds[key] === 'fields') {
        const cur = (inp.value || v.defaults[key]).split(',').map(x => x.trim()).filter(x => x && x !== field);
        inp.value = [field, ...cur].slice(0, 4).join(',');
    } else {
        inp.value = field;
    }
    inp.classList.add('sec-fm-edited');
    secMsg(t('fm_use_note'), 'ok');
}

async function fmSave() {
    const d = await fetchJSON(`${API}/security/fieldmap`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({field_map: fmForm()})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    _fm.form = null;
    if (_sec.data) _sec.data.field_map = d.field_map;
    secMsg(t('fm_saved'), 'ok');
    await secLoadOverview();
}

function fmReset() {
    document.querySelectorAll('#sec-fm input[data-fm]').forEach(i => { i.value = ''; });
    secMsg(t('fm_reset_note'), 'ok');
}

function fmExport() {
    const body = {'jt-glogarch-field-map': 1, field_map: {}};
    for (const [k, v] of Object.entries(fmForm())) if (v.trim()) body.field_map[k] = v.trim();
    const blob = new Blob([JSON.stringify(body, null, 2) + '\n'], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'jt-glogarch-field-map.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

function fmImport(el) {
    const f = el.files && el.files[0];
    if (!f) return;
    const v = fmView();
    const rd = new FileReader();
    rd.onload = () => {
        let obj;
        try { obj = JSON.parse(rd.result); } catch (e) { secMsg(t('fm_import_bad'), 'err'); return; }
        const m = obj && typeof obj === 'object' ? (obj.field_map && typeof obj.field_map === 'object' ? obj.field_map : obj) : null;
        const keys = m ? Object.keys(m).filter(k => v.kinds[k]) : [];
        if (!keys.length) { secMsg(t('fm_import_bad'), 'err'); return; }
        document.querySelectorAll('#sec-fm input[data-fm]').forEach(i => { i.value = m[i.dataset.fm] != null ? String(m[i.dataset.fm]) : ''; });
        secMsg(t('fm_import_note').replace('{n}', keys.length), 'ok');
    };
    rd.readAsText(f);
    el.value = '';
}

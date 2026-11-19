/* jt-glogarch — Investigations (cases) on the Security Incidents page (added 1.24).
 * A case groups incidents, keeps who works on it and a timeline of notes and
 * changes. Titles, notes and incident entities are user- or log-supplied: esc(). */

const _case = {list: [], cur: null, pickFor: null};

function secTab(which) {
    document.querySelectorAll('#sec-tabs .arch-tab').forEach(b => b.classList.toggle('active', b.dataset.arg === which));
    ['overview', 'incidents', 'cases', 'risk', 'sigma'].forEach(k => document.getElementById(`sec-${k}-panel`).classList.toggle('hidden', which !== k));
    if (which === 'overview' && typeof ovLoad === 'function') ovLoad();
    if (which === 'sigma' && typeof sigmaLoad === 'function') sigmaLoad();
    if (which === 'cases') caseLoadList();
    if (which === 'risk' && typeof riskInit === 'function') riskInit();
}

function caseStatusChip(st) {
    return `<span class="case-st case-st-${esc(st)}">${esc(t('case_st_' + st))}</span>`;
}

async function caseLoadList() {
    const f = document.getElementById('sec-c-status').value;
    const q = f && f !== 'all' ? `?status=${encodeURIComponent(f)}` : '';
    const d = await fetchJSON(`${API}/security/cases${q}`);
    const tb = document.getElementById('sec-c-tbody');
    if (!d || d.error) { tb.innerHTML = `<tr><td colspan="8">${esc(d && d.error || '')}</td></tr>`; return; }
    let cases = d.cases || [];
    if (!f) cases = cases.filter(c => c.status !== 'closed');
    _case.list = cases;
    document.getElementById('sec-c-total').textContent = t('sec_total').replace('{n}', formatNumber(cases.length));
    tb.innerHTML = cases.length ? cases.map(c => `<tr>
        <td class="text-muted">#${esc(String(c.id))}</td>
        <td class="al-title"><button type="button" class="al-name" data-act="caseOpen" data-args="${esc(JSON.stringify([c.id]))}">${esc(c.title)}</button></td>
        <td>${secSevBadge(c.severity)}</td>
        <td>${caseStatusChip(c.status)}</td>
        <td>${esc(c.assignee || '—')}</td>
        <td>${formatNumber(c.incidents)}${c.notes ? ` <span class="text-muted fs-08">· ${esc(t('case_n_notes').replace('{n}', c.notes))}</span>` : ''}</td>
        <td>${esc(secUtc(c.updated_at))}</td>
        <td class="sec-actions"><button class="btn-sm btn-secondary" data-act="caseOpen" data-args="${esc(JSON.stringify([c.id]))}">${icon('eye', 14)} ${esc(t('case_btn_open'))}</button></td>
    </tr>`).join('') : `<tr><td colspan="8" class="text-muted">${esc(t('case_empty'))}</td></tr>`;
}

// ---- pick: add incident(s) to a new or an existing case --------------------------------

async function casePick(incidentId) {
    _case.pickFor = incidentId;
    const i = (_sec.rows || {})[incidentId] || {};
    const d = await fetchJSON(`${API}/security/cases`);
    const open = ((d && d.cases) || []).filter(c => c.status !== 'closed');
    const opts = [`<option value="new">${esc(t('case_pick_new'))}</option>`]
        .concat(open.map(c => `<option value="${esc(String(c.id))}">#${esc(String(c.id))} ${esc(c.title)}</option>`)).join('');
    const sevs = ['high', 'medium', 'low'].map(v => `<option value="${v}" ${v === (i.severity || 'medium') ? 'selected' : ''}>${esc(t('sec_sev_' + v))}</option>`).join('');
    const title = `${secDetTitle(i.detector || '', i.detector_title)} — ${i.entity || ''}`.slice(0, 200);
    document.getElementById('sec-case-pick-content').innerHTML = `
        <div class="sec-ai-inc">${secSevBadge(i.severity || '')} <strong>${esc(secDetTitle(i.detector || '', i.detector_title))}</strong> <code>${esc(i.entity || '')}</code></div>
        <div class="sec-form case-form">
            <div class="sec-wide"><label>${esc(t('case_pick_target'))}</label><select id="case-pick-target" data-act-change="casePickTarget">${opts}</select></div>
            <div class="sec-wide case-new-only"><label>${esc(t('case_th_title'))}</label><input type="text" id="case-pick-name" maxlength="200" value="${esc(title)}"></div>
            <div class="case-new-only"><label>${esc(t('sec_th_severity'))}</label><select id="case-pick-sev">${sevs}</select></div>
        </div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="casePickClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
            <button class="btn-primary" data-act="casePickSave">${icon('check', 16)} ${esc(t('case_btn_add'))}</button></div>`;
    document.getElementById('sec-case-pick-modal').style.display = 'flex';
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

function casePickTarget(v) {
    document.querySelectorAll('#sec-case-pick-content .case-new-only').forEach(el => el.classList.toggle('hidden', v !== 'new'));
}

function casePickClose() { document.getElementById('sec-case-pick-modal').style.display = 'none'; }

async function casePickSave() {
    const target = document.getElementById('case-pick-target').value;
    const ids = [_case.pickFor];
    let d, cid;
    if (target === 'new') {
        d = await fetchJSON(`${API}/security/cases`, {method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title: document.getElementById('case-pick-name').value,
                                  severity: document.getElementById('case-pick-sev').value, incident_ids: ids})});
        cid = d && d.id;
    } else {
        cid = Number(target);
        d = await fetchJSON(`${API}/security/cases/${cid}/incidents`, {method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({incident_ids: ids})});
    }
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    casePickClose();
    await secLoad(Math.floor(_sec.offset / _sec.limit));
    caseOpen(cid);
}

// ---- one case -------------------------------------------------------------------------

async function caseNew() {
    const d = await fetchJSON(`${API}/security/cases`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: t('case_untitled'), severity: 'medium'})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    await caseLoadList();
    caseOpen(d.id);
}

async function caseOpen(id) {
    document.getElementById('sec-case-modal').style.display = 'flex';
    document.getElementById('sec-case-content').innerHTML = `<span class="spinner-text">${esc(t('loading'))}</span>`;
    const d = await fetchJSON(`${API}/security/cases/${encodeURIComponent(id)}`);
    if (!d || d.error) { document.getElementById('sec-case-content').innerHTML = `<p class="pk-err">${esc(d && d.error)}</p>`; return; }
    _case.cur = d;
    caseRender();
}

function caseClose() {
    document.getElementById('sec-case-modal').style.display = 'none';
    _case.cur = null;
    if (!document.getElementById('sec-cases-panel').classList.contains('hidden')) caseLoadList();
    else secLoad(Math.floor(_sec.offset / _sec.limit));
}

function _caseEvent(e) {
    const who = `<strong>${esc(e.username || '—')}</strong>`;
    const when = `<span class="text-muted fs-08">${esc(secUtc(e.created_at))}</span>`;
    if (e.kind === 'note') return `<div class="case-ev case-note"><div>${who} ${when}</div><div class="case-note-body">${esc(e.body)}</div></div>`;
    const k = 'case_ev_' + e.kind;
    const label = t(k) === k ? e.kind : t(k);
    const body = e.body ? ' ' + esc(_caseChange(e)) : '';
    return `<div class="case-ev">${when} ${who} ${esc(label)}${body}</div>`;
}

function caseRender() {
    const c = _case.cur;
    const opt = (v, cur, label) => `<option value="${esc(v)}" ${v === cur ? 'selected' : ''}>${esc(label)}</option>`;
    const sts = ['open', 'in_progress', 'closed'].map(v => opt(v, c.status, t('case_st_' + v))).join('');
    const sevs = ['high', 'medium', 'low'].map(v => opt(v, c.severity, t('sec_sev_' + v))).join('');
    const incs = c.incidents.length ? c.incidents.map(i => {
        const link = /^https?:\/\//.test(i.graylog_url || '')
            ? `<a class="btn-sm btn-secondary" href="${esc(i.graylog_url)}" target="_blank" rel="noopener noreferrer">${icon('search', 14)} Graylog</a>` : '';
        return `<tr><td>${secSevBadge(i.severity)}</td>
            <td>${esc(secDetTitle(i.detector, i.detector_title))}${secAttackChips(i.attack)}</td>
            <td class="sec-entity"><code>${esc(i.entity)}</code><div class="text-muted fs-08">#${esc(String(i.id))} · ${esc(t('sec_st_' + i.status))}</div></td>
            <td>${i.ai ? secVerdictChip(i.ai.verdict) : '<span class="text-muted">—</span>'}</td>
            <td>${esc(secUtc(i.last_seen))}</td>
            <td class="sec-actions">${link}<button class="btn-sm btn-secondary" data-act="caseUnlink" data-args="${esc(JSON.stringify([i.id]))}" title="${esc(t('case_btn_unlink'))}">${icon('close', 14)}</button></td></tr>`;
    }).join('') : `<tr><td colspan="6" class="text-muted">${esc(t('case_no_incidents'))}</td></tr>`;
    document.getElementById('sec-case-content').innerHTML = `
        <div class="text-muted fs-08">#${esc(String(c.id))} · ${esc(t('case_created_by').replace('{u}', c.created_by || '—').replace('{t}', secUtc(c.created_at)))}${c.closed_at ? ' · ' + esc(t('case_closed_at').replace('{t}', secUtc(c.closed_at))) : ''}</div>
        <div class="sec-form case-form">
            <div class="sec-wide"><label>${esc(t('case_th_title'))}</label><input type="text" id="case-f-title" maxlength="200" value="${esc(c.title)}"></div>
            <div><label>${esc(t('sec_th_status'))}</label><select id="case-f-status">${sts}</select></div>
            <div><label>${esc(t('sec_th_severity'))}</label><select id="case-f-sev">${sevs}</select></div>
            <div><label>${esc(t('case_th_assignee'))}</label><input type="text" id="case-f-assignee" maxlength="100" value="${esc(c.assignee)}"></div>
            <div class="sec-wide"><label>${esc(t('case_f_description'))}</label><textarea id="case-f-desc" rows="3" maxlength="8000">${esc(c.description)}</textarea></div>
            <div class="sec-wide"><label>${esc(t('case_f_resolution'))}</label><textarea id="case-f-res" rows="2" maxlength="8000" placeholder="${esc(t('case_f_resolution_ph'))}">${esc(c.resolution)}</textarea></div>
        </div>
        <div class="sec-ai-btns case-save-row"><button class="btn-primary" data-act="caseSave">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>
        <h4>${esc(t('case_incidents').replace('{n}', c.incidents.length))}</h4>
        <div class="table-wrap"><table class="sec-table"><thead><tr><th>${esc(t('sec_th_severity'))}</th><th>${esc(t('sec_th_detector'))}</th>
            <th>${esc(t('sec_th_entity'))}</th><th>${esc(t('sec_ai_title'))}</th><th>${esc(t('sec_th_last'))}</th><th></th></tr></thead><tbody>${incs}</tbody></table></div>
        <p class="text-muted fs-08">${esc(t('case_add_hint'))}</p>
        <h4>${esc(t('case_timeline'))}</h4>
        <div class="case-timeline">${c.timeline.map(_caseEvent).join('')}</div>
        <div class="case-add-note"><textarea id="case-note" rows="2" maxlength="8000" placeholder="${esc(t('case_note_ph'))}"></textarea>
            <button class="btn-secondary" data-act="caseAddNote">${icon('plus', 16)} ${esc(t('case_btn_note'))}</button></div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="caseClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
            <button class="btn-secondary" data-act="caseExport">${icon('download', 16)} ${esc(t('case_btn_export'))}</button></div>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

async function _casePost(path, body) {
    const d = await fetchJSON(`${API}/security/cases/${encodeURIComponent(_case.cur.id)}${path}`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    if (!d || d.error) {
        document.getElementById('sec-case-content').insertAdjacentHTML('afterbegin', `<p class="pk-err">${esc(d && d.error)}</p>`);
        return null;
    }
    return d;
}

async function caseSave() {
    const v = id => document.getElementById(id).value;
    const d = await _casePost('', {title: v('case-f-title'), status: v('case-f-status'), severity: v('case-f-sev'),
        assignee: v('case-f-assignee'), description: v('case-f-desc'), resolution: v('case-f-res')});
    if (d) caseOpen(_case.cur.id);
}

async function caseAddNote() {
    const body = document.getElementById('case-note').value.trim();
    if (!body) return;
    if (await _casePost('/notes', {body})) caseOpen(_case.cur.id);
}

function caseUnlink(incidentId) {
    showConfirm(t('case_btn_unlink'), t('case_unlink_confirm').replace('{n}', incidentId), async () => {
        if (await _casePost('/incidents', {incident_ids: [incidentId], remove: true})) caseOpen(_case.cur.id);
    });
}

/* A Markdown handoff report, built in the browser from what the page shows.
 * Free text gets `<` / `>` escaped (a Markdown viewer would render HTML in it);
 * log-derived values go in code spans. */
function _md(v) { return String(v == null ? '' : v).replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/([\[\]()!`*_\\])/g, '\\$1'); }
function _mdCode(v) { return '`' + String(v == null ? '' : v).replace(/`/g, "'").replace(/\n/g, ' ') + '`'; }

function _caseChange(e) {
    const pre = {status_changed: 'case_st_', severity_changed: 'sec_sev_'}[e.kind];
    if (pre) return e.body.split(' -> ').map(v => t(pre + v)).join(' → ');
    if (e.kind === 'incident_added' || e.kind === 'incident_removed') return '#' + e.body;
    if (e.body.includes(' -> ')) return e.body.split(' -> ').map(v => v || '—').join(' → ');
    return e.body;
}

function caseMarkdown(c) {
    const C = t('sec_colon');
    const lines = [`# ${t('case_title')} #${c.id}${C}${_md(c.title)}`, '',
        `- ${t('sec_th_status')}${C}${t('case_st_' + c.status)}`,
        `- ${t('sec_th_severity')}${C}${t('sec_sev_' + c.severity)}`,
        `- ${t('case_th_assignee')}${C}${_md(c.assignee || '—')}`,
        `- ${t('case_created_by').replace('{u}', _md(c.created_by || '—')).replace('{t}', secUtc(c.created_at))}`];
    if (c.closed_at) lines.push(`- ${t('case_closed_at').replace('{t}', secUtc(c.closed_at))}`);
    if (c.description) lines.push('', `## ${t('case_f_description')}`, '', _md(c.description));
    if (c.resolution) lines.push('', `## ${t('case_f_resolution')}`, '', _md(c.resolution));
    lines.push('', `## ${t('case_incidents').replace('{n}', c.incidents.length)}`, '');
    c.incidents.forEach(i => {
        const tech = (i.attack || []).map(x => x.id).join(', ');
        lines.push(`- #${i.id} [${t('sec_sev_' + i.severity)}] ${_md(secDetTitle(i.detector, i.detector_title))}${C}${_mdCode(i.entity)}`
            + `${tech ? ` (ATT&CK ${tech})` : ''}${i.ai ? ` — AI: ${t('sec_ai_v_' + i.ai.verdict)}` : ''}`
            + ` — ${secUtc(i.first_seen)} → ${secUtc(i.last_seen)}`);
        if (i.query) lines.push(`  - ${_mdCode(i.query)}`);
    });
    lines.push('', `## ${t('case_timeline')}`, '');
    c.timeline.forEach(e => {
        const k = 'case_ev_' + e.kind;
        lines.push(e.kind === 'note' ? `- ${secUtc(e.created_at)} ${_md(e.username)}${C}${_md(e.body).replace(/\n/g, ' ')}`
            : `- ${secUtc(e.created_at)} ${_md(e.username)}${C}${t(k) === k ? e.kind : t(k)} ${_md(_caseChange(e))}`);
    });
    return lines.join('\n') + '\n';
}

function caseExport() {
    const c = _case.cur;
    const blob = new Blob([caseMarkdown(c)], {type: 'text/markdown;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `jt-glogarch-case-${c.id}.md`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

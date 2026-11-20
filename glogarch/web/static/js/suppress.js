/* jt-glogarch — Suppressions (added 1.31): "this detection on this entity is known".
 * The detection keeps running; a matching finding is dropped before it becomes an
 * incident and counted on the suppression (hits, last hit). Reason required, expiry
 * by default. Every value from logs or users goes through esc(). */

const _sup = {incident: null, days: [0, 1, 7, 30, 90, 365]};

function supDaysLabel(d) {
    return d ? t('sup_days_n').replace('{n}', d) : t('sup_days_never');
}

function secSuppress(incidentId) {
    const i = (_sec.rows || {})[incidentId];
    if (!i) return;
    _sup.incident = i;
    const days = _sup.days.map(d => `<option value="${d}" ${d === 30 ? 'selected' : ''}>${esc(supDaysLabel(d))}</option>`).join('');
    const det = secDetTitle(i.detector, i.detector_title);
    document.getElementById('sec-suppress-content').innerHTML = `
        <div class="sec-ai-inc">${secSevBadge(i.severity)} <strong>${esc(det)}</strong> <code>${esc(i.entity)}</code></div>
        <p class="text-muted fs-085">${esc(t('sup_help'))}</p>
        <div class="sec-form case-form">
            <div class="sec-wide"><label>${esc(t('sup_scope'))}</label><select id="sup-scope">
                <option value="this">${esc(t('sup_scope_this').replace('{d}', det))}</option>
                <option value="*">${esc(t('sup_scope_all'))}</option></select></div>
            <div class="sec-wide"><label>${esc(t('sec_th_entity'))}</label><input type="text" id="sup-entity" maxlength="512" value="${esc(i.entity)}">
                <div class="text-muted fs-08">${esc(t('sup_entity_hint'))}</div></div>
            <div class="sec-wide"><label>${esc(t('sup_reason'))}</label><textarea id="sup-reason" rows="3" maxlength="500" placeholder="${esc(t('sup_reason_ph'))}"></textarea></div>
            <div><label>${esc(t('sup_expires'))}</label><select id="sup-days">${days}</select></div>
            <div><label class="sec-chk"><input type="checkbox" id="sup-close" ${i.status !== 'closed' ? 'checked' : ''}> ${esc(t('sup_close_incident'))}</label></div>
        </div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="secSuppressClose">${icon('close', 16)} ${esc(t('btn_close'))}</button>
            <button class="btn-primary" data-act="secSuppressSave">${icon('eye_closed', 16)} ${esc(t('sup_btn_save'))}</button></div>`;
    document.getElementById('sec-suppress-modal').style.display = 'flex';
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

function secSuppressClose() { document.getElementById('sec-suppress-modal').style.display = 'none'; }

async function secSuppressSave() {
    const i = _sup.incident;
    const reason = document.getElementById('sup-reason').value.trim();
    if (!reason) { secMsg(t('sup_reason_required'), 'err'); return; }
    const scope = document.getElementById('sup-scope').value;
    const d = await fetchJSON(`${API}/security/suppressions`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server: i.server || '', detector: scope === '*' ? '*' : i.detector,
                              entity: document.getElementById('sup-entity').value, reason,
                              days: Number(document.getElementById('sup-days').value),
                              close_incident: document.getElementById('sup-close').checked, incident_id: i.id})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secSuppressClose();
    secMsg(t(d.created ? 'sup_saved' : 'sup_updated').replace('{e}', d.entity), 'ok');
    await secLoad(Math.floor(_sec.offset / _sec.limit));
    await supLoad();
}

async function supLoad() {
    const box = document.getElementById('sec-supp-list');
    if (!box) return;
    const d = await fetchJSON(`${API}/security/suppressions`);
    if (!d || d.error) { box.innerHTML = `<p class="pk-err">${esc(d && d.error || '')}</p>`; return; }
    if (Array.isArray(d.days)) _sup.days = d.days;
    _sup.rows = {};
    d.suppressions.forEach(s => { _sup.rows[s.id] = s; });
    const active = d.suppressions.filter(s => s.active).length;
    document.getElementById('sec-supp-count').textContent = t('sup_count').replace('{a}', formatNumber(active)).replace('{n}', formatNumber(d.suppressions.length));
    if (!d.suppressions.length) { box.innerHTML = `<p class="text-muted fs-085">${esc(t('sup_none'))}</p>`; return; }
    const rows = d.suppressions.map(s => {
        const det = s.detector === '*' ? t('sup_scope_all') : secDetTitle(s.detector, s.detector_title);
        const exp = s.expires_at ? secUtc(s.expires_at) : t('sup_days_never');
        const state = s.active ? '' : ` <span class="sec-tag">${esc(t('sup_expired'))}</span>`;
        return `<tr${s.active ? '' : ' class="sup-expired"'}>
            <td>${esc(det)}</td>
            <td class="sec-entity"><code>${esc(s.entity)}</code>${s.server ? `<div class="text-muted fs-08">${esc(s.server)}</div>` : ''}</td>
            <td class="sup-reason">${esc(s.reason)}<div class="text-muted fs-08">${esc(s.created_by || '')} · ${esc(secUtc(s.created_at))}</div></td>
            <td>${esc(exp)}${state}</td>
            <td>${formatNumber(s.hits)}<div class="text-muted fs-08">${esc(s.last_hit_at ? secUtc(s.last_hit_at) : '—')}</div></td>
            <td class="sec-actions"><button class="btn-sm btn-danger" data-act="supDelete" data-args="${esc(JSON.stringify([s.id]))}" title="${esc(t('sup_btn_delete'))}" aria-label="${esc(t('sup_btn_delete'))}">${icon('trash', 14)}</button></td>
        </tr>`;
    }).join('');
    box.innerHTML = `<div class="table-wrap"><table class="sec-table"><thead><tr>
        <th>${esc(t('sec_th_detector'))}</th><th>${esc(t('sec_th_entity'))}</th><th>${esc(t('sup_reason'))}</th>
        <th>${esc(t('sup_expires'))}</th><th>${esc(t('sup_hits'))}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function supDelete(id) {
    const s = (_sup.rows || {})[id];
    if (!s) return;
    showConfirm(t('sup_btn_delete'), t('sup_delete_confirm').replace('{e}', esc(s.entity)), async () => {
        const d = await fetchJSON(`${API}/security/suppressions/${id}`, {method: 'DELETE'});
        if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
        await supLoad();
    });
}

document.addEventListener('DOMContentLoaded', () => { if (document.getElementById('sec-supp-list')) supLoad(); });

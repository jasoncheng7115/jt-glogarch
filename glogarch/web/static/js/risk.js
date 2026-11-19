/* jt-glogarch — Assets and risk ranking on the Security Incidents page (added 1.25).
 * Asset names and owners are typed by people, entities come from logs: esc(). */

const _risk = {assets: [], edit: null, loaded: false};

function riskInit() {
    riskLoad();
    assetLoad();
    tiLoad();
}

function tiAbout(f) {
    const k = 'ti_about_' + f.id;
    return t(k) === k ? f.about : t(k);
}

function tiTags(list) {
    return (list || []).map(x => ` <span class="sec-tag ti-tag" title="${esc(tiAbout(x))}">${icon('warning', 11)} ${esc(x.name)}</span>`).join('');
}

async function tiLoad() {
    const el = document.getElementById('sec-ti-card');
    if (!el) return;
    const d = await fetchJSON(`${API}/security/ti`);
    if (!d || d.error) { el.innerHTML = `<p class="pk-err">${esc(d && d.error || '')}</p>`; return; }
    const rows = d.feeds.map(f => `<tr>
        <td><label class="sec-chk"><input type="checkbox" class="ti-feed" value="${esc(f.id)}" ${f.selected ? 'checked' : ''}> <strong>${esc(f.name)}</strong></label>
            <div class="text-muted fs-08">${esc(tiAbout(f))}</div></td>
        <td>${f.count != null && f.refreshed_at ? esc(t('ti_entries').replace('{n}', formatNumber(f.count))) : '—'}</td>
        <td>${f.refreshed_at ? esc(secUtc(f.refreshed_at)) : '—'}${f.error ? `<div class="pk-err fs-08">${esc(jobNote(f.error))}</div>` : ''}</td>
    </tr>`).join('');
    el.innerHTML = `<div class="filters sec-filters"><h3 class="risk-h">${esc(t('ti_title'))}</h3>
            <label class="sec-chk sec-c-new"><input type="checkbox" id="ti-enabled" ${d.enabled ? 'checked' : ''}> ${esc(t('ti_enable'))}</label></div>
        <p class="text-muted fs-085">${esc(t('ti_help'))}</p>
        <div class="table-wrap"><table class="sec-table"><thead><tr><th>${esc(t('ti_th_feed'))}</th><th>${esc(t('ti_th_entries'))}</th><th>${esc(t('ti_th_refreshed'))}</th></tr></thead>
            <tbody>${rows}</tbody></table></div>
        <div class="sec-ai-btns"><button class="btn-secondary" data-act="tiRefresh" ${d.enabled ? '' : 'disabled'}>${icon('refresh', 16)} ${esc(t('ti_btn_refresh'))}</button>
            <button class="btn-primary" data-act="tiSave">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
}

async function tiSave() {
    const feeds = [...document.querySelectorAll('#sec-ti-card .ti-feed:checked')].map(x => x.value);
    const d = await fetchJSON(`${API}/security/ti/settings`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled: document.getElementById('ti-enabled').checked, feeds})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg(t('ti_saved'), 'ok');
    tiLoad();
}

async function tiRefresh() {
    secMsg(t('ti_refreshing'), 'ok');
    const d = await fetchJSON(`${API}/security/ti/refresh`, {method: 'POST'});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    const bad = Object.entries(d.result).filter(([, v]) => v.error);
    secMsg(bad.length ? t('ti_refresh_partial').replace('{n}', bad.length) : t('ti_refresh_ok'), bad.length ? 'err' : 'ok');
    tiLoad();
    riskLoad();
}

function assetCritChip(c) {
    return `<span class="asset-crit asset-crit-${esc(c)}">${esc(t('asset_crit_' + c))}</span>`;
}

function assetTag(a) {
    if (!a) return '';
    return ` <span class="asset-tag asset-crit-${esc(a.criticality)}" title="${esc(t('asset_th_crit'))}: ${esc(t('asset_crit_' + a.criticality))}">${icon('server', 11)} ${esc(a.name || a.value)}</span>`;
}

function riskFactor(f) {
    const label = {severity: t('sec_sev_' + f.v), external: t('sec_external'),
                   asset: t('risk_f_asset').replace('{c}', t('asset_crit_' + f.v)),
                   ai: 'AI ' + t('sec_ai_v_' + f.v), ti: t('risk_f_ti').replace('{f}', f.v)}[f.k] || f.k;
    return `${label} ${f.x}`;
}

async function riskLoad() {
    const days = document.getElementById('sec-r-days').value || 7;
    const d = await fetchJSON(`${API}/security/risk?days=${encodeURIComponent(days)}`);
    const tb = document.getElementById('sec-r-tbody');
    if (!d || d.error) { tb.innerHTML = `<tr><td colspan="6">${esc(d && d.error || '')}</td></tr>`; return; }
    document.getElementById('sec-r-total').textContent = t('risk_total').replace('{n}', formatNumber(d.incidents));
    if (!d.entities.length) { tb.innerHTML = `<tr><td colspan="6" class="text-muted">${esc(t('risk_empty'))}</td></tr>`; return; }
    const top = d.entities[0].score || 1;
    tb.innerHTML = d.entities.map((r, n) => {
        const ext = r.external === 1 || r.external === true ? ` <span class="sec-tag">${esc(t('sec_external'))}</span>` : '';
        const parts = r.parts.map(p => `<div class="risk-part">#${esc(String(p.incident))} ${esc(secDetTitle(p.detector, p.title))} · <strong>${esc(String(p.points))}</strong> = ${esc(p.factors.map(riskFactor).join(' × '))}</div>`).join('');
        return `<tr>
            <td class="text-muted">${n + 1}</td>
            <td class="sec-entity"><code>${esc(r.entity)}</code>${ext}${assetTag(r.asset)}${r.threat_intel && r.threat_intel.length ? ` <span class="sec-tag ti-tag">${icon('warning', 11)} TI</span>` : ''}<div class="text-muted fs-08">${esc(r.entity_field)}</div></td>
            <td class="risk-score-cell"><details><summary><progress class="risk-bar" max="100" value="${Math.max(4, Math.round(r.score * 100 / top))}"></progress> <strong>${esc(String(r.score))}</strong></summary>${parts}</details></td>
            <td>${formatNumber(r.incidents)}</td>
            <td>${secSevBadge(r.max_severity)}</td>
            <td>${esc(secUtc(r.last_seen))}</td>
        </tr>`;
    }).join('');
}

async function assetLoad() {
    const d = await fetchJSON(`${API}/security/assets`);
    const tb = document.getElementById('sec-a-tbody');
    if (!d || d.error) { tb.innerHTML = `<tr><td colspan="6">${esc(d && d.error || '')}</td></tr>`; return; }
    _risk.assets = d.assets || [];
    document.getElementById('sec-a-total').textContent = t('sec_total').replace('{n}', formatNumber(_risk.assets.length));
    tb.innerHTML = _risk.assets.length ? _risk.assets.map(a => `<tr>
        <td>${esc(t('asset_kind_' + a.kind))}</td>
        <td><code>${esc(a.value)}</code></td>
        <td>${esc(a.name || '—')}${a.notes ? `<div class="text-muted fs-08">${esc(a.notes)}</div>` : ''}</td>
        <td>${assetCritChip(a.criticality)}</td>
        <td>${esc(a.owner || '—')}</td>
        <td class="sec-actions"><button class="btn-sm btn-secondary" data-act="assetForm" data-args="${esc(JSON.stringify([a.id]))}">${icon('edit', 14)} ${esc(t('asset_btn_edit'))}</button><button class="btn-sm btn-secondary" data-act="assetDelete" data-args="${esc(JSON.stringify([a.id]))}">${icon('trash', 14)} ${esc(t('asset_btn_delete'))}</button></td>
    </tr>`).join('') : `<tr><td colspan="6" class="text-muted">${esc(t('asset_empty'))}</td></tr>`;
}

function assetForm(id) {
    const a = _risk.assets.find(x => x.id === id) || {kind: 'ip', value: '', name: '', criticality: 'medium', owner: '', notes: ''};
    _risk.edit = id || null;
    const opt = (v, cur, label) => `<option value="${esc(v)}" ${v === cur ? 'selected' : ''}>${esc(label)}</option>`;
    const kinds = ['ip', 'cidr', 'host', 'account'].map(v => opt(v, a.kind, t('asset_kind_' + v))).join('');
    const crits = ['critical', 'high', 'medium', 'low'].map(v => opt(v, a.criticality, t('asset_crit_' + v))).join('');
    const el = document.getElementById('sec-a-form');
    el.innerHTML = `<div class="sec-form">
            <div><label>${esc(t('asset_th_kind'))}</label><select id="asset-f-kind">${kinds}</select></div>
            <div><label>${esc(t('asset_th_value'))}</label><input type="text" id="asset-f-value" maxlength="255" value="${esc(a.value)}" placeholder="10.0.0.5 · 10.0.0.0/24 · dc1 · administrator"></div>
            <div><label>${esc(t('asset_th_name'))}</label><input type="text" id="asset-f-name" maxlength="200" value="${esc(a.name)}"></div>
            <div><label>${esc(t('asset_th_crit'))}</label><select id="asset-f-crit">${crits}</select></div>
            <div><label>${esc(t('asset_th_owner'))}</label><input type="text" id="asset-f-owner" maxlength="100" value="${esc(a.owner)}"></div>
            <div class="sec-wide"><label>${esc(t('asset_f_notes'))}</label><input type="text" id="asset-f-notes" maxlength="2000" value="${esc(a.notes)}"></div>
        </div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="assetFormClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" data-act="assetSave">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
    el.classList.remove('hidden');
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

function assetFormClose() {
    const el = document.getElementById('sec-a-form');
    el.classList.add('hidden');
    el.innerHTML = '';
}

async function assetSave() {
    const v = id => document.getElementById(id).value;
    const body = {kind: v('asset-f-kind'), value: v('asset-f-value'), name: v('asset-f-name'),
                  criticality: v('asset-f-crit'), owner: v('asset-f-owner'), notes: v('asset-f-notes')};
    if (_risk.edit) body.id = _risk.edit;
    const d = await fetchJSON(`${API}/security/assets`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg('');
    assetFormClose();
    await assetLoad();
    riskLoad();
}

function assetDelete(id) {
    const a = _risk.assets.find(x => x.id === id);
    if (!a) return;
    showConfirm(t('asset_btn_delete'), t('asset_delete_confirm').replace('{v}', esc(a.value)), async () => {
        const d = await fetchJSON(`${API}/security/assets/${encodeURIComponent(id)}`, {method: 'DELETE'});
        if (d && d.error) { secMsg(d.error, 'err'); return; }
        await assetLoad();
        riskLoad();
    });
}

function assetImportForm() {
    const el = document.getElementById('sec-a-form');
    el.innerHTML = `<p class="text-muted fs-085">${esc(t('asset_import_help'))}</p>
        <textarea id="asset-import-text" class="asset-import" rows="6" placeholder="cidr,10.0.0.0/24,Server LAN,high,IT&#10;host,dc1,Domain controller,critical,IT&#10;account,administrator,Built-in admin,critical"></textarea>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="assetFormClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" data-act="assetImport">${icon('upload', 16)} ${esc(t('asset_btn_import'))}</button></div>`;
    el.classList.remove('hidden');
}

async function assetImport() {
    const d = await fetchJSON(`${API}/security/assets/import`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: document.getElementById('asset-import-text').value})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg(t('asset_imported').replace('{n}', d.saved) + (d.errors.length ? ' ' + d.errors.map(jobNote).join('; ') : ''),
           d.errors.length ? 'err' : 'ok');
    assetFormClose();
    await assetLoad();
    riskLoad();
}

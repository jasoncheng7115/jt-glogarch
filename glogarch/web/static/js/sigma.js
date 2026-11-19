/* jt-glogarch — Sigma rules on the Security Incidents page (added 1.27).
 * Rule titles, YAML and queries are user-supplied: esc() everything. */

const _sigma = {rules: [], fieldMap: {}, max: 50};

function sigmaLevelChip(level) {
    const sev = {informational: 'low', low: 'low', medium: 'medium', high: 'high', critical: 'high'}[level] || 'medium';
    return `${secSevBadge(sev)} <span class="text-muted fs-08">${esc(level)}</span>`;
}

async function sigmaLoad() {
    const d = await fetchJSON(`${API}/security/sigma`);
    const tb = document.getElementById('sec-s-tbody');
    if (!d || d.error) { tb.innerHTML = `<tr><td colspan="6">${esc(d && d.error || '')}</td></tr>`; return; }
    _sigma.rules = d.rules || [];
    _sigma.fieldMap = d.field_map || {};
    _sigma.max = d.max_rules;
    document.getElementById('sec-s-total').textContent = t('sigma_total').replace('{n}', formatNumber(_sigma.rules.length)).replace('{e}', formatNumber(d.enabled)).replace('{m}', formatNumber(d.max_rules));
    tb.innerHTML = _sigma.rules.length ? _sigma.rules.map(r => {
        const last = r.last_run_at
            ? (r.last_error ? `<span class="pk-err fs-08">${esc(jobNote(r.last_error))}</span>`
                : `${esc(t('sigma_last_count').replace('{n}', formatNumber(r.last_count || 0)))}<div class="text-muted fs-08">${esc(secUtc(r.last_run_at))}</div>`)
            : `<span class="text-muted">—</span>`;
        const q = r.query ? `<code class="sigma-q">${esc(r.query)}</code>` : `<span class="pk-err fs-08">${esc(jobNote(r.error))}</span>`;
        return `<tr>
            <td><strong>${esc(r.title)}</strong>${secAttackChips(r.attack)}<div class="text-muted fs-08">${esc(t('sigma_group'))}${esc(t('sec_colon'))}<code>${esc(r.group_by)}</code> · ${esc(t('sigma_threshold'))}${esc(t('sec_colon'))}${esc(String(r.threshold))}</div></td>
            <td>${sigmaLevelChip(r.level)}</td>
            <td class="sigma-q-cell">${q}</td>
            <td>${last}</td>
            <td><label class="sec-chk"><input type="checkbox" data-act-change="sigmaToggle" data-act-self data-id="${esc(String(r.id))}" ${r.enabled ? 'checked' : ''} ${r.query ? '' : 'disabled'}> ${esc(t(r.enabled ? 'sigma_on' : 'sigma_off'))}</label></td>
            <td class="sec-actions"><button class="btn-sm btn-secondary" data-act="sigmaTest" data-args="${esc(JSON.stringify([r.id]))}" ${r.query ? '' : 'disabled'}>${icon('play', 14)} ${esc(t('sigma_btn_test'))}</button><button class="btn-sm btn-secondary" data-act="sigmaDelete" data-args="${esc(JSON.stringify([r.id]))}" title="${esc(t('asset_btn_delete'))}" aria-label="${esc(t('asset_btn_delete'))}">${icon('trash', 14)}</button></td>
        </tr><tr class="sigma-test-row hidden" id="sigma-test-${esc(String(r.id))}"><td colspan="6"></td></tr>`;
    }).join('') : `<tr><td colspan="6" class="text-muted">${esc(t('sigma_empty'))}</td></tr>`;
}

function sigmaFormClose() {
    const el = document.getElementById('sec-s-form');
    el.classList.add('hidden');
    el.innerHTML = '';
}

function sigmaAddForm() {
    const el = document.getElementById('sec-s-form');
    el.innerHTML = `<div class="sec-form">
            <div class="sec-wide"><label>${esc(t('sigma_f_yaml'))}</label><textarea id="sigma-f-yaml" class="asset-import sigma-yaml" rows="12" spellcheck="false" placeholder="title: ...&#10;logsource: ...&#10;detection:&#10;  selection:&#10;    event_category: authentication&#10;  condition: selection"></textarea></div>
            <div><label>${esc(t('sigma_group'))}</label><input type="text" id="sigma-f-group" value="source" maxlength="100"></div>
            <div><label>${esc(t('sigma_threshold'))}</label><input type="number" id="sigma-f-threshold" value="1" min="1"></div>
        </div>
        <div id="sigma-preview" class="sigma-preview hidden"></div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="sigmaFormClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-secondary" data-act="sigmaPreview">${icon('eye', 16)} ${esc(t('sigma_btn_preview'))}</button>
            <button class="btn-primary" data-act="sigmaAdd">${icon('check', 16)} ${esc(t('sigma_btn_save'))}</button></div>`;
    el.classList.remove('hidden');
}

async function sigmaPreview() {
    const box = document.getElementById('sigma-preview');
    const d = await fetchJSON(`${API}/security/sigma/preview`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({yaml: document.getElementById('sigma-f-yaml').value})});
    box.classList.remove('hidden');
    if (!d || d.error) { box.innerHTML = `<p class="pk-err">${esc(t('sigma_refused'))} ${esc(jobNote(d && d.error || ''))}</p>`; return; }
    box.innerHTML = `<div><strong>${esc(d.title)}</strong> ${sigmaLevelChip(d.level)}${secAttackChips(d.attack)}</div>
        <div class="text-muted fs-08">${esc(t('sigma_th_query'))}</div><code class="sigma-q">${esc(d.query)}</code>`;
}

async function sigmaAdd() {
    const d = await fetchJSON(`${API}/security/sigma`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({yaml: document.getElementById('sigma-f-yaml').value,
                              group_by: document.getElementById('sigma-f-group').value,
                              threshold: Number(document.getElementById('sigma-f-threshold').value)})});
    if (!d || d.error) {
        const box = document.getElementById('sigma-preview');
        box.classList.remove('hidden');
        box.innerHTML = `<p class="pk-err">${esc(t('sigma_refused'))} ${esc(jobNote(d && d.error || ''))}</p>`;
        return;
    }
    secMsg(t('sigma_saved'), 'ok');
    sigmaFormClose();
    sigmaLoad();
}

async function sigmaToggle(el) {
    const id = Number(el.dataset.id);
    // the state the box now shows is the one asked for (not a flip of a possibly stale list)
    const d = await fetchJSON(`${API}/security/sigma/${encodeURIComponent(id)}`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled: el.checked})});
    if (d && d.error) secMsg(d.error, 'err');
    sigmaLoad();
}

async function sigmaTest(id) {
    const row = document.getElementById(`sigma-test-${id}`);
    row.classList.remove('hidden');
    row.firstElementChild.innerHTML = `<span class="spinner-text">${esc(t('sigma_testing'))}</span>`;
    const d = await fetchJSON(`${API}/security/sigma/${encodeURIComponent(id)}/test`, {method: 'POST'});
    if (!d || d.error) { row.firstElementChild.innerHTML = `<span class="pk-err">${esc(jobNote(d && d.error || ''))}</span>`; return; }
    const groups = d.rows.filter(x => x.entity !== '(Empty Value)').map(x => `<code>${esc(String(x.entity))}</code> ${formatNumber(x.count)}`).join(' · ');
    row.firstElementChild.innerHTML = `${esc(t('sigma_test_result').replace('{n}', formatNumber(d.total)))} ${groups}`;
}

function sigmaDelete(id) {
    const r = _sigma.rules.find(x => x.id === id);
    if (!r) return;
    showConfirm(t('asset_btn_delete'), t('sigma_delete_confirm').replace('{t}', esc(r.title)), async () => {
        const d = await fetchJSON(`${API}/security/sigma/${encodeURIComponent(id)}`, {method: 'DELETE'});
        if (d && d.error) secMsg(d.error, 'err');
        sigmaLoad();
    });
}

function sigmaFieldMapForm() {
    const text = Object.entries(_sigma.fieldMap).map(([a, b]) => `${a}=${b}`).join('\n');
    const el = document.getElementById('sec-s-form');
    el.innerHTML = `<p class="text-muted fs-085">${esc(t('sigma_fieldmap_help'))}</p>
        <textarea id="sigma-f-map" class="asset-import" rows="8" spellcheck="false" placeholder="EventID=event_code&#10;CommandLine=process_command_line&#10;Image=process_path&#10;TargetUserName=user_name&#10;IpAddress=source_ip">${esc(text)}</textarea>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="sigmaFormClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-primary" data-act="sigmaFieldMapSave">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
    el.classList.remove('hidden');
}

async function sigmaFieldMapSave() {
    const d = await fetchJSON(`${API}/security/sigma-fieldmap`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: document.getElementById('sigma-f-map').value})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg(t('sigma_fieldmap_saved').replace('{n}', d.fields).replace('{r}', d.reconverted), 'ok');
    sigmaFormClose();
    sigmaLoad();
}

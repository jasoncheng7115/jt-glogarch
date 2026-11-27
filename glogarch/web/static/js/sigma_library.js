/* jt-glogarch — SigmaHQ rule library on the Sigma tab (added 1.33).
 * Titles, authors, paths and queries come from downloaded rules: esc() everything;
 * links go only to the source_url the server built for github.com. */

const _sl = {offset: 0, limit: 50, total: 0, items: [], sel: new Set(), data: null, busy: false};

function _slSelectOpts(id, opts, value) {
    const el = document.getElementById(id);
    el.innerHTML = opts.map(([v, label]) => `<option value="${esc(v)}" ${v === value ? 'selected' : ''}>${esc(label)}</option>`).join('');
}

function _slQuery() {
    const g = id => (document.getElementById(id) || {}).value || '';
    const p = new URLSearchParams({q: g('sl-q'), product: g('sl-product'), level: g('sl-level'),
                                   state: g('sl-state') || 'all', offset: _sl.offset, limit: _sl.limit});
    return p.toString();
}

async function slLoad() {
    const d = await fetchJSON(`${API}/security/sigma-library?${_slQuery()}`);
    if (!d || d.error) { document.getElementById('sl-status').innerHTML = `<p class="pk-err">${esc(jobNote(d && d.error || ''))}</p>`; return; }
    const first = !_sl.data;
    _sl.data = d;
    _sl.items = d.items || [];
    _sl.total = d.total;
    slRenderStatus();
    const m = d.meta || {};
    const has = Number(m.count || 0) > 0;
    document.getElementById('sl-browse').classList.toggle('hidden', !has);
    if (!has) return;
    if (first) {
        _slSelectOpts('sl-product', [['', t('sl_all_sources')], ...d.products.map(([k, n]) => [k, `${k} (${formatNumber(n)})`])], '');
        _slSelectOpts('sl-level', [['', t('sl_all_levels')], ...['critical', 'high', 'medium', 'low', 'informational'].map(l => [l, l])], '');
        _slSelectOpts('sl-state', ['all', 'convertible', 'fields_ok', 'not_added', 'added'].map(s => [s, t('sl_st_' + s)]), 'all');
        if (typeof initCustomSelects === 'function') initCustomSelects();
    }
    slRenderRows();
}

function slRenderStatus() {
    const d = _sl.data, m = d.meta || {}, s = d.settings || {};
    const total = document.getElementById('sl-total');
    total.textContent = m.count ? t('sl_counts').replace('{n}', formatNumber(Number(m.count))).replace('{c}', formatNumber(Number(m.converted || 0))) : '';
    const parts = [];
    if (!s.enabled) parts.push(`<span class="text-muted">${esc(t('sl_off'))}</span>`);
    else if (!m.count && !m.error) parts.push(`<span class="text-muted">${esc(t('sl_never'))}</span>`);
    if (m.tag) parts.push(`<span class="ai-chip">${icon('download', 14)} ${esc(t('sl_release').replace('{t}', m.tag))} · ${esc(m.package || '')}</span>`);
    if (m.graylog_field_count != null) parts.push(`<span class="ai-chip">${icon('db', 14)} ${esc(t('sl_fields').replace('{n}', formatNumber(m.graylog_field_count)).replace('{s}', m.fields_server || ''))}</span>`);
    if (m.checked_at) parts.push(`<span class="text-muted fs-08">${esc(t('sl_checked').replace('{d}', secUtc(m.checked_at)))}</span>`);
    let html = `<div class="sl-status-row">${parts.join('')}</div>`;
    if (m.error) html += `<p class="pk-err fs-085">${esc(t('sl_error').replace('{m}', jobNote(m.error)))}</p>`;
    if (m.fields_error) html += `<p class="pk-err fs-085">${esc(t('sl_fields_err').replace('{m}', jobNote(m.fields_error)))}</p>`;
    document.getElementById('sl-status').innerHTML = html;
    const btn = document.getElementById('sl-check');
    btn.disabled = !s.enabled || _sl.busy;
    document.getElementById('sl-license').innerHTML = esc(t('sl_license')).replace('{l}',
        `<a href="${esc(d.license_url)}" target="_blank" rel="noopener noreferrer">${esc(d.license)}</a>`);
}

function _slFields(it) {
    const miss = new Set(it.missing_fields || []);
    const unknown = it.missing_fields == null;
    return (it.fields || []).map(f => miss.has(f)
        ? `<code class="sl-field sl-field-miss" title="${esc(t('sl_missing'))}">${esc(f)}</code>`
        : `<code class="sl-field${unknown ? '' : ' sl-field-ok'}" ${unknown ? `title="${esc(t('sl_fields_unknown'))}"` : ''}>${esc(f)}</code>`).join(' ');
}

function slRenderRows() {
    const tb = document.getElementById('sl-tbody');
    if (!_sl.items.length) {
        tb.innerHTML = `<tr><td colspan="7" class="text-muted">${esc(t('sl_none'))}</td></tr>`;
    } else {
        tb.innerHTML = _sl.items.map(it => {
            const src = [it.product, it.category, it.service].filter(Boolean).map(x => `<code>${esc(x)}</code>`).join(' ');
            const canAdd = it.query && !it.added_rule_id;
            const conv = it.query
                ? `<details class="sl-q"><summary class="status-completed">${esc(t('sl_conv_ok'))}</summary><code class="sigma-q">${esc(it.query)}</code></details>`
                : `<span class="pk-err fs-08">${esc(jobNote(it.error))}</span>`;
            const author = (it.author || '').length > 70 ? it.author.slice(0, 68) + '…' : (it.author || '');
            const meta = [it.status, author ? t('sl_by').replace('{a}', author) : '', it.modified].filter(Boolean).map(esc).join(' · ');
            return `<tr>
                <td class="sl-chk">${canAdd ? `<input type="checkbox" data-act-change="slSelect" data-act-self data-id="${esc(it.sigma_id)}" ${_sl.sel.has(it.sigma_id) ? 'checked' : ''} aria-label="${esc(it.title)}">` : ''}</td>
                <td><strong>${esc(it.title)}</strong>${secAttackChips(it.attack)}
                    <div class="text-muted fs-08">${meta} · <a href="${esc(it.source_url)}" target="_blank" rel="noopener noreferrer">SigmaHQ</a></div></td>
                <td>${sigmaLevelChip(it.level || 'medium')}</td>
                <td>${src || '—'}</td>
                <td class="sl-fields">${_slFields(it)}</td>
                <td class="sl-conv">${conv}</td>
                <td class="sec-actions">${it.added_rule_id
                    ? `<span class="text-muted fs-08">${icon('check', 14)} ${esc(t('sl_added'))}</span>`
                    : `<button class="btn-sm btn-secondary" data-act="slAdd" data-arg="${esc(it.sigma_id)}" ${canAdd ? '' : 'disabled'}>${icon('plus', 14)} ${esc(t('sl_btn_add'))}</button>`}</td>
            </tr>`;
        }).join('');
    }
    const a = _sl.total ? _sl.offset + 1 : 0, b = Math.min(_sl.offset + _sl.limit, _sl.total);
    document.getElementById('sl-pager').innerHTML = `<span class="text-muted fs-085">${esc(t('sl_page').replace('{a}', formatNumber(a)).replace('{b}', formatNumber(b)).replace('{n}', formatNumber(_sl.total)))}</span>
        <button class="btn-sm btn-secondary" data-act="slPage" data-arg="-1" ${_sl.offset > 0 ? '' : 'disabled'} aria-label="prev">${icon('arrow_left', 14)}</button>
        <button class="btn-sm btn-secondary" data-act="slPage" data-arg="1" ${b < _sl.total ? '' : 'disabled'} aria-label="next">${icon('arrow_right', 14)}</button>`;
    _slSelButton();
}

function _slSelButton() {
    const b = document.getElementById('sl-add-sel');
    b.innerHTML = `${icon('plus', 14)} ${esc(t('sl_add_selected').replace('{n}', formatNumber(_sl.sel.size)))}`;
    b.disabled = !_sl.sel.size || !!_sl.adding;
    // the header box: ticked when every rule on this page that can be added is selected
    const page = _slPageIds();
    const all = document.getElementById('sl-chk-all');
    if (all) {
        const n = page.filter(i => _sl.sel.has(i)).length;
        all.checked = page.length > 0 && n === page.length;
        all.indeterminate = n > 0 && n < page.length;
        all.disabled = !page.length;
    }
    _slSelBar();
}

function _slPageIds() {
    return _sl.items.filter(it => it.query && !it.added_rule_id).map(it => it.sigma_id);
}

// after the whole page is ticked: offer every rule the filter matches (like a mail client does)
function _slSelBar() {
    const bar = document.getElementById('sl-selbar');
    if (!bar) return;
    const page = _slPageIds();
    const pageAll = page.length > 0 && page.every(i => _sl.sel.has(i));
    let html = '';
    if (_sl.selAll) {
        const left = _sl.selLeft || {added: 0, bad: 0};
        const parts = [];
        if (left.added) parts.push(t('sl_sel_left_added').replace('{n}', formatNumber(left.added)));
        if (left.bad) parts.push(t('sl_sel_left_bad').replace('{n}', formatNumber(left.bad)));
        const extra = parts.length ? ' ' + t('sl_sel_left').replace('{list}', parts.join(t('list_sep'))) : '';
        html = `<span>${esc(t('sl_sel_all_done').replace('{n}', formatNumber(_sl.sel.size)) + extra)}</span>
            <button type="button" class="btn-link" data-act="slSelectNone">${esc(t('sl_sel_clear'))}</button>`;
    } else if (pageAll && _sl.total > page.length) {
        html = `<span>${esc(t('sl_sel_page_done').replace('{n}', formatNumber(page.length)))}</span>
            <button type="button" class="btn-link" data-act="slSelectAllMatching">${esc(t('sl_sel_all_matching').replace('{n}', formatNumber(_sl.total)))}</button>`;
    }
    bar.innerHTML = html;
    bar.classList.toggle('hidden', !html);
}

function slSelect(el) {
    if (el.checked) _sl.sel.add(el.dataset.id); else { _sl.sel.delete(el.dataset.id); _sl.selAll = false; }
    _slSelButton();
}

function slSelectPage(el) {
    const page = _slPageIds();
    if (el.checked) page.forEach(i => _sl.sel.add(i));
    else { page.forEach(i => _sl.sel.delete(i)); _sl.selAll = false; }
    slRenderRows();
}

async function slSelectAllMatching() {
    const d = await fetchJSON(`${API}/security/sigma-library?${_slQuery()}&ids_only=1`);
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    (d.ids || []).forEach(i => _sl.sel.add(i));
    _sl.selAll = true;
    _sl.selLeft = {added: d.already_added || 0, bad: d.not_convertible || 0};
    slRenderRows();
}

function slSelectNone() {
    _sl.sel.clear();
    _sl.selAll = false;
    slRenderRows();
}

function slFilter() { _sl.offset = 0; _sl.sel.clear(); _sl.selAll = false; slLoad(); }

function slPage(dir) {
    _sl.offset = Math.max(0, _sl.offset + Number(dir) * _sl.limit);
    slLoad();
}

// The server takes 100 per request: send them in batches and say how far it got. Every rule
// comes in DISABLED, so adding a thousand starts no queries.
const SL_BATCH = 100;
async function _slAddIds(ids) {
    if (_sl.adding) return;
    _sl.adding = true;
    const b = document.getElementById('sl-add-sel');
    let added = 0, skipped = 0, err = '';
    for (let k = 0; k < ids.length; k += SL_BATCH) {
        if (b && ids.length > SL_BATCH) {
            b.disabled = true;
            b.innerHTML = `<span class="spinner-text">${esc(t('sl_adding').replace('{a}', formatNumber(k)).replace('{n}', formatNumber(ids.length)))}</span>`;
        }
        const part = ids.slice(k, k + SL_BATCH);
        const d = await fetchJSON(`${API}/security/sigma-library/add`, {method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ids: part})});
        if (!d || d.error) { err = (d && d.error) || 'error'; break; }
        added += d.added.length;
        skipped += d.skipped.length;
        part.forEach(i => _sl.sel.delete(i));
    }
    _sl.adding = false;
    _sl.selAll = false;
    let msg = t('sl_add_done').replace('{n}', formatNumber(added));
    if (skipped) msg += ' ' + t('sl_add_skipped').replace('{n}', formatNumber(skipped));
    if (err) secMsg(`${msg} ${err}`, 'err');
    else secMsg(msg, added ? 'ok' : 'err');
    if (typeof sigmaLoad === 'function') sigmaLoad();
    slLoad();
}

function slAdd(id) { _slAddIds([id]); }
function slAddSelected() { if (_sl.sel.size) _slAddIds([..._sl.sel]); }

async function slCheck(force) {
    if (_sl.busy) return;
    _sl.busy = true;
    const btn = document.getElementById('sl-check');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-text">${esc(t('sl_checking'))}</span>`;
    const d = await fetchJSON(`${API}/security/sigma-library/refresh`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({force: force === true})});
    _sl.busy = false;
    btn.innerHTML = `${icon('refresh', 14)} ${esc(t('sl_btn_check'))}`;
    if (!d || d.error) { secMsg(d && d.error, 'err'); slLoad(); return; }
    let msg = d.status === 'current' ? t('sl_done_current').replace('{t}', d.tag)
        : t('sl_done_downloaded').replace('{t}', d.tag).replace('{n}', formatNumber(d.count));
    if ((d.updated_rules || []).length) msg += ' ' + t('sl_done_updated').replace('{n}', formatNumber(d.updated_rules.length));
    secMsg(msg, 'ok');
    _sl.data = null;            // the products list can change with a new release
    _sl.offset = 0;
    if (typeof sigmaLoad === 'function' && (d.updated_rules || []).length) sigmaLoad();
    slLoad();
}

function slSettingsForm() {
    const d = _sl.data || {settings: {}, packages: []};
    const s = d.settings;
    const el = document.getElementById('sl-form');
    el.innerHTML = `<div class="sec-form">
            <label class="sec-enable"><input type="checkbox" id="sl-f-enabled" ${s.enabled ? 'checked' : ''}> ${esc(t('sl_f_enable'))}</label>
            <div class="sec-wide"><label>${esc(t('sl_f_package'))}</label><select id="sl-f-package">${d.packages.map(p =>
                `<option value="${esc(p.id)}" ${p.id === s.package ? 'selected' : ''}>${esc(t('sl_pkg_' + p.id))}</option>`).join('')}</select></div>
            <label class="sec-enable"><input type="checkbox" id="sl-f-auto" ${s.auto_update ? 'checked' : ''}> ${esc(t('sl_f_auto'))}</label>
            <p class="sec-wide text-muted fs-08">${esc(t('sl_f_note'))}</p>
        </div>
        <div class="sec-ai-btns"><button class="btn-secondary sec-ai-close" data-act="slFormClose">${icon('close', 16)} ${esc(t('btn_cancel'))}</button>
            <button class="btn-secondary" data-act="slRedownload" ${s.enabled ? '' : 'disabled'}>${icon('download', 16)} ${esc(t('sl_btn_redownload'))}</button>
            <button class="btn-primary" data-act="slSettingsSave">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
    el.classList.remove('hidden');
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

function slFormClose() {
    const el = document.getElementById('sl-form');
    el.classList.add('hidden');
    el.innerHTML = '';
}

async function slSettingsSave() {
    const d = await fetchJSON(`${API}/security/sigma-library/settings`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled: document.getElementById('sl-f-enabled').checked,
                              package: document.getElementById('sl-f-package').value,
                              auto_update: document.getElementById('sl-f-auto').checked})});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg(t('sl_saved'), 'ok');
    slFormClose();
    _sl.data = null;
    slLoad();
}

function slRedownload() { slFormClose(); slCheck(true); }

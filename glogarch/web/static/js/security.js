/* jt-glogarch — Security incidents page (added 1.20).
 * The server counts security events in Graylog on a schedule and keeps them as
 * incidents (glogarch/security/). Everything shown here that came from logs (an
 * account name, an IDS signature) is attacker-influenced: always esc(). */

const _sec = {data: null, offset: 0, limit: 100, total: 0, running: false};

function secMsg(text, level) {
    const el = document.getElementById('sec-message');
    if (!el) return;
    el.className = 'pk-message ' + (level === 'err' ? 'pk-err' : 'pk-ok');
    el.textContent = text || '';
    el.classList.toggle('hidden', !text);
}

function secDetTitle(id) {
    const k = 'sec_det_' + id;
    const s = t(k);
    return s === k ? id : s;
}

function secSevBadge(sev) {
    return `<span class="sec-sev sec-sev-${esc(sev)}">${esc(t('sec_sev_' + sev))}</span>`;
}

function secStats(m) {
    const order = ['count', 'success', 'card:user_name', 'card:source', 'card:source_ip',
        'card:uri', 'card:vhost', 'min:alert_severity'];
    const parts = [];
    for (const k of order) {
        if (m == null || m[k] == null) continue;
        const label = t('sec_m_' + k.replace(':', '_'));
        parts.push(k === 'min:alert_severity' ? `${label} ${esc(m[k])}` : `${formatNumber(m[k])} ${label}`);
    }
    return parts.join(' · ');
}

function secUtc(s) { return s ? formatDT(s.endsWith('Z') ? s : s + 'Z') : '—'; }

async function secInit() {
    if (!document.getElementById('sec-status-card')) return;
    await secLoadOverview();
    await secLoad();
}

async function secLoadOverview() {
    const d = await fetchJSON(`${API}/security/overview`);
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    _sec.data = d;
    _sec.running = !!d.running;
    const last = (d.runs || [])[0];
    const parts = [];
    parts.push(d.enabled
        ? `<span class="status-completed">${esc(t('sec_on'))}</span>`
        : `<span class="status-pending">${esc(t('sec_off'))}</span>`);
    parts.push(`<span>${esc(t('al_server'))}${esc(t('sec_colon'))}<strong>${esc(d.server || '—')}</strong></span>`);
    if (last) {
        const st = t('sec_run_' + last.status);
        parts.push(`<span>${esc(t('sec_last_run'))}${esc(t('sec_colon'))}${esc(secUtc(last.started_at))} · ${esc(st)}`
            + (last.note ? ` · ${esc(jobNote(last.note))}` : '') + `</span>`);
    } else {
        parts.push(`<span class="text-muted">${esc(t('sec_never_run'))}</span>`);
    }
    if (d.next_run) parts.push(`<span>${esc(t('sec_next_run'))}${esc(t('sec_colon'))}${esc(formatDT(d.next_run))}</span>`);
    const c = d.counts_24h || {};
    const openHigh = (c['high:open'] || 0);
    parts.push(`<span>${esc(t('sec_open_high_24h').replace('{n}', formatNumber(openHigh)))}</span>`);
    document.getElementById('sec-status').innerHTML = parts.join('<span class="sep">·</span>');
    const btn = document.getElementById('sec-run-btn');
    if (btn) btn.disabled = _sec.running;
    const lastErr = last && last.errors && last.errors.length ? last.errors[0] : '';
    if (last && last.status === 'error' && lastErr) secMsg(t('sec_last_error') + jobNote(lastErr), 'err');
    secRenderCoverage();
    if (!document.getElementById('sec-settings').classList.contains('hidden')) secRenderSettings();
}

async function secLoad(page) {
    if (typeof page === 'number') _sec.offset = Math.max(0, page) * _sec.limit;
    else _sec.offset = 0;
    const st = document.getElementById('sec-f-status').value;
    const sv = document.getElementById('sec-f-severity').value;
    const q = new URLSearchParams({status: st, severity: sv, limit: _sec.limit, offset: _sec.offset});
    const d = await fetchJSON(`${API}/security/incidents?${q}`);
    const tb = document.getElementById('sec-tbody');
    if (!d || d.error) { tb.innerHTML = `<tr><td colspan="8">${esc(d && d.error || '')}</td></tr>`; return; }
    _sec.total = d.total || 0;
    document.getElementById('sec-total').textContent = t('sec_total').replace('{n}', formatNumber(_sec.total));
    if (!d.incidents.length) {
        tb.innerHTML = `<tr><td colspan="8" class="text-muted">${esc(t(_sec.data && _sec.data.enabled ? 'sec_empty' : 'sec_empty_off'))}</td></tr>`;
    } else {
        tb.innerHTML = d.incidents.map(secRow).join('');
    }
    secRenderPager();
}

function secRow(i) {
    const ext = i.external === 1 ? ` <span class="sec-tag">${esc(t('sec_external'))}</span>`
        : (i.external === 0 ? ` <span class="sec-tag sec-tag-int">${esc(t('sec_internal'))}</span>` : '');
    const isNew = i.is_new ? ` <span class="sec-tag sec-tag-new">${esc(t('sec_new'))}</span>` : '';
    const link = /^https?:\/\//.test(i.graylog_url || '')
        ? `<a class="btn-sm btn-secondary" href="${esc(i.graylog_url)}" target="_blank" rel="noopener noreferrer" title="${esc(t('sec_open_graylog'))}">${icon('search', 14)} ${esc(t('sec_btn_graylog'))}</a>` : '';
    const acts = [];
    if (i.status === 'open') acts.push(`<button class="btn-sm btn-secondary" data-act="secSetStatus" data-args="${esc(JSON.stringify([i.id, 'acknowledged']))}">${icon('check', 14)} ${esc(t('sec_btn_ack'))}</button>`);
    if (i.status !== 'closed') acts.push(`<button class="btn-sm btn-secondary" data-act="secSetStatus" data-args="${esc(JSON.stringify([i.id, 'closed']))}">${icon('close', 14)} ${esc(t('sec_btn_close'))}</button>`);
    else acts.push(`<button class="btn-sm btn-secondary" data-act="secSetStatus" data-args="${esc(JSON.stringify([i.id, 'open']))}">${icon('refresh', 14)} ${esc(t('sec_btn_reopen'))}</button>`);
    const by = i.status_by ? `<div class="text-muted fs-08">${esc(i.status_by)}</div>` : '';
    return `<tr>
        <td>${secSevBadge(i.severity)}</td>
        <td>${esc(secDetTitle(i.detector))}</td>
        <td class="sec-entity"><code>${esc(i.entity)}</code>${ext}${isNew}<div class="text-muted fs-08">${esc(i.entity_field)}</div></td>
        <td>${secStats(i.metrics)}<div class="text-muted fs-08">${esc(t('sec_peak').replace('{n}', formatNumber(i.peak_count)))} · ${esc(t('sec_runs').replace('{n}', formatNumber(i.runs)))}</div></td>
        <td>${esc(secUtc(i.first_seen))}</td>
        <td>${esc(secUtc(i.last_seen))}</td>
        <td class="sec-status">${esc(t('sec_st_' + i.status))}${by}</td>
        <td class="sec-actions">${link}${acts.join('')}</td>
    </tr>`;
}

function secRenderPager() {
    const el = document.getElementById('sec-pager');
    const pages = Math.ceil(_sec.total / _sec.limit);
    if (pages <= 1) { el.innerHTML = ''; return; }
    const cur = Math.floor(_sec.offset / _sec.limit);
    el.innerHTML = `<button ${cur === 0 ? 'disabled' : ''} data-act="secLoad" data-args="[${cur - 1}]">&laquo;</button>`
        + `<span class="u028">${cur + 1} / ${pages}</span>`
        + `<button ${cur >= pages - 1 ? 'disabled' : ''} data-act="secLoad" data-args="[${cur + 1}]">&raquo;</button>`;
}

async function secSetStatus(id, status) {
    const d = await fetchJSON(`${API}/security/incidents/${encodeURIComponent(id)}/status`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status})});
    if (d && d.error) { secMsg(d.error, 'err'); return; }
    await secLoad(Math.floor(_sec.offset / _sec.limit));
    await secLoadOverview();
}

async function secRunNow() {
    const btn = document.getElementById('sec-run-btn');
    if (btn) btn.disabled = true;
    secMsg(t('sec_running'), 'ok');
    const d = await fetchJSON(`${API}/security/run`, {method: 'POST'});
    if (!d || d.error) secMsg(d && d.error, 'err');
    else if (d.status === 'skipped') secMsg(t('sec_run_skipped_msg') + jobNote(d.note || ''), 'err');
    else if (d.status === 'error') secMsg(t('sec_last_error') + jobNote((d.errors || [d.error || ''])[0] || ''), 'err');
    else secMsg(t('sec_run_done').replace('{f}', formatNumber(d.findings || 0)).replace('{q}', formatNumber(d.queries || 0)), 'ok');
    await secLoadOverview();
    await secLoad();
}

function secToggleCoverage() {
    const el = document.getElementById('sec-coverage');
    el.classList.toggle('hidden');
    secRenderCoverage();
}

function secRenderCoverage() {
    const el = document.getElementById('sec-coverage');
    if (!el || el.classList.contains('hidden') || !_sec.data) return;
    const cov = _sec.data.coverage || [];
    if (!cov.length) { el.innerHTML = `<p class="text-muted">${esc(t('sec_cov_none'))}</p>`; return; }
    // A probe tries several fields (the WAF's peer is client_ip, the firewall's
    // source_ip). An empty alternate is only a problem when NO field has data.
    const usedField = {};
    cov.forEach(c => { if (!c.error && c.events && c.missing < c.events && !usedField[c.probe]) usedField[c.probe] = c.field; });
    const rows = cov.map(c => {
        const filled = c.events - c.missing;
        const pct = c.events ? Math.round(filled * 100 / c.events) : null;
        let state;
        if (!c.error && pct === 0 && usedField[c.probe] && usedField[c.probe] !== c.field)
            state = `<span class="text-muted">${esc(t('sec_cov_alt_unused').replace('{f}', usedField[c.probe]))}</span>`;
        else if (c.error) state = `<span class="sec-cov-bad">${esc(t('sec_cov_error'))}</span> <span class="text-muted fs-08">${esc(jobNote(c.error))}</span>`;
        else if (!c.events) state = `<span class="text-muted">${esc(t('sec_cov_nodata'))}</span>`;
        else if (pct === 0) state = `<span class="sec-cov-bad">${esc(t('sec_cov_field_empty'))}</span>`;
        else state = `${pct}%`;
        return `<tr><td>${esc(t('sec_probe_' + c.probe))}</td><td><code>${esc(c.field)}</code></td>
            <td>${formatNumber(c.events)}</td><td>${state}${c.truncated ? ` <span class="text-muted fs-08">${esc(t('sec_cov_truncated'))}</span>` : ''}</td></tr>`;
    }).join('');
    el.innerHTML = `<h3>${esc(t('sec_cov_title'))}</h3>
        <p class="text-muted fs-085">${esc(t('sec_cov_help'))} ${esc(t('sec_cov_at').replace('{t}', secUtc(_sec.data.coverage_at)))}</p>
        <div class="table-wrap"><table><thead><tr><th>${esc(t('sec_cov_probe'))}</th><th>${esc(t('sec_cov_field'))}</th>
        <th>${esc(t('sec_cov_events'))}</th><th>${esc(t('sec_cov_filled'))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function secToggleSettings() {
    const el = document.getElementById('sec-settings');
    el.classList.toggle('hidden');
    if (!el.classList.contains('hidden')) secRenderSettings();
}

function secRenderSettings() {
    const d = _sec.data;
    if (!d) return;
    const s = d.settings;
    const opt = (v, cur, label) => `<option value="${esc(v)}" ${v === cur ? 'selected' : ''}>${esc(label)}</option>`;
    const servers = [opt('', s.server, t('sec_default_server'))].concat((d.servers || []).map(n => opt(n, s.server, n))).join('');
    const sevs = ['high', 'medium', 'low', 'off'].map(v => opt(v, s.notify_min_severity, t('sec_notify_' + v))).join('');
    const num = (id, v, min, max) => `<input type="number" id="${id}" value="${esc(v)}" min="${min}" max="${max}">`;
    const dets = d.detectors.map(x => `<tr data-det="${esc(x.id)}">
        <td><label class="sec-chk"><input type="checkbox" class="sec-det-en" ${x.enabled ? 'checked' : ''}> ${esc(secDetTitle(x.id))}</label>
            <div class="text-muted fs-08"><code>${esc(x.query)}</code> · ${esc(x.fields.join(' / '))}</div></td>
        <td><input type="number" class="sec-det-min" min="1" value="${esc(x.min_count)}" title="${esc(t('sec_default_is').replace('{v}', x.default_min_count))}"></td>
        <td><input type="text" class="sec-det-ex" value="${esc(x.exclude)}" placeholder="${esc(t('sec_exclude_ph'))}"></td>
    </tr>`).join('');
    document.getElementById('sec-settings').innerHTML = `
        <h3>${esc(t('sec_settings_title'))}</h3>
        <p class="text-muted fs-085">${esc(t('sec_settings_help'))}</p>
        <div class="sec-form">
            <label class="sec-chk sec-enable"><input type="checkbox" id="sec-s-enabled" ${s.enabled ? 'checked' : ''}> ${esc(t('sec_s_enabled'))}</label>
            <div><label>${esc(t('al_server'))}</label><select id="sec-s-server">${servers}</select></div>
            <div><label>${esc(t('sec_s_interval'))}</label>${num('sec-s-interval', s.interval_minutes, 5, 1440)}</div>
            <div><label>${esc(t('sec_s_window'))}</label>${num('sec-s-window', s.window_minutes, 5, 1440)}</div>
            <div><label>${esc(t('sec_s_notify'))}</label><select id="sec-s-notify">${sevs}</select></div>
            <div><label>${esc(t('sec_s_renotify'))}</label>${num('sec-s-renotify', s.renotify_hours, 1, 720)}</div>
            <div><label>${esc(t('sec_s_reopen'))}</label>${num('sec-s-reopen', s.reopen_hours, 1, 720)}</div>
            <div><label>${esc(t('sec_s_new_days'))}</label>${num('sec-s-newdays', s.new_days, 1, 365)}</div>
            <div><label>${esc(t('sec_s_retention'))}</label>${num('sec-s-retention', s.retention_days, 7, 3650)}</div>
            <div class="sec-wide"><label>${esc(t('sec_s_exclude'))}</label><input type="text" id="sec-s-exclude" value="${esc(s.exclude_query)}" placeholder="${esc(t('sec_exclude_ph'))}"></div>
        </div>
        <div class="table-wrap"><table class="sec-det-table"><thead><tr><th>${esc(t('sec_th_detector'))}</th>
            <th>${esc(t('sec_s_min_count'))}</th><th>${esc(t('sec_s_det_exclude'))}</th></tr></thead><tbody>${dets}</tbody></table></div>
        <div class="sec-save-row"><button class="btn-primary" data-act="secSaveSettings">${icon('check', 16)} ${esc(t('btn_save'))}</button></div>`;
    if (typeof initCustomSelects === 'function') initCustomSelects();
}

async function secSaveSettings() {
    const v = id => document.getElementById(id).value;
    const detectors = {};
    document.querySelectorAll('#sec-settings tr[data-det]').forEach(tr => {
        detectors[tr.dataset.det] = {
            enabled: tr.querySelector('.sec-det-en').checked,
            min_count: tr.querySelector('.sec-det-min').value,
            exclude: tr.querySelector('.sec-det-ex').value,
        };
    });
    const body = {
        enabled: document.getElementById('sec-s-enabled').checked,
        server: v('sec-s-server'),
        interval_minutes: Number(v('sec-s-interval')),
        window_minutes: Number(v('sec-s-window')),
        notify_min_severity: v('sec-s-notify'),
        renotify_hours: Number(v('sec-s-renotify')),
        reopen_hours: Number(v('sec-s-reopen')),
        new_days: Number(v('sec-s-newdays')),
        retention_days: Number(v('sec-s-retention')),
        exclude_query: v('sec-s-exclude'),
        detectors,
    };
    const d = await fetchJSON(`${API}/security/settings`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    if (!d || d.error) { secMsg(d && d.error, 'err'); return; }
    secMsg(t(d.registered ? 'sec_saved_on' : 'sec_saved_off'), 'ok');
    await secLoadOverview();
}

document.addEventListener('DOMContentLoaded', secInit);

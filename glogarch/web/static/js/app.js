/* jt-glogarch Web UI JavaScript */

const API = '/api';

async function fetchJSON(url, opts) {
    const resp = await fetch(url, opts);
    if (resp.status === 401) {
        document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        window.location.href = '/login';
        return {};
    }
    try {
        const data = await resp.json();
        if (!resp.ok && !data.error) {
            data.error = data.error || `HTTP ${resp.status}: ${resp.statusText}`;
        }
        return data;
    } catch (e) {
        return {error: `HTTP ${resp.status}: ${resp.statusText}`};
    }
}

// --- UI Helpers ---

/** Run async action with button disable + spinner, show errors */
async function withButton(btnOrEvent, asyncFn) {
    const btn = btnOrEvent?.target?.closest?.('button') || btnOrEvent;
    if (!btn) { await asyncFn(); return; }
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.style.opacity = '0.5';
    btn.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;
    try {
        await asyncFn();
    } catch (e) {
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.innerHTML = orig;
        applyI18n();
    }
}

/** Show loading in a table tbody, then load data */
async function loadTable(selector, asyncFn) {
    const tbody = document.querySelector(selector + ' tbody');
    if (tbody) tbody.innerHTML = `<tr><td class="u143" colspan="20"><span class="spinner-text">${t('loading')}...</span></td></tr>`;
    try {
        await asyncFn();
        if (tbody && tbody.innerHTML.includes('spinner-text')) {
            tbody.innerHTML = `<tr><td class="u143" colspan="20">${t('log_no_data')}</td></tr>`;
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td class="u141" colspan="20">${t('load_failed')}</td></tr>`;
    }
    initTableSort();
}

/** Replace native alert with custom modal */
function showAlert(msg) {
    showConfirm('', msg, null);
}

/** Copy arbitrary text to the clipboard (used by the fingerprint modal). */
function copyText(text) {
    if (!text) return;
    navigator.clipboard.writeText(String(text)).then(() => showAlert(t('msg_copied'))).catch(() => {});
}

/** Show a report's SHA-256 fingerprint + how to independently verify the PDF. */
function showReportFingerprint(arg) {
    const [hash, filename] = String(arg).split('|');
    const fn = filename || 'report.pdf';
    const body = `<div class="fp-modal">
        <div class="fp-label">${t('reports_fp_sha256')}</div>
        <div class="fp-hashbox">
          <code class="fp-full" id="fp-full-hash">${esc(hash)}</code>
          <button type="button" class="fp-copy btn-sm btn-secondary" data-act="copyText" data-arg="${esc(hash)}">${icon('copy',14)}</button>
        </div>
        <div class="fp-hint">${t('reports_fp_hint')}</div>
        <pre class="fp-cmd">sha256sum ${esc(fn)}</pre>
        <div class="fp-note">${t('reports_fp_note')}</div>
      </div>`;
    showConfirm(icon('shield') + ' ' + t('reports_verify_title'), body, null);
}

/** Escape HTML to prevent XSS */
function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatMB(mb) {
    if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB';
    return mb.toFixed(0) + ' MB';
}

function formatNumber(n) {
    return (n || 0).toLocaleString();
}

function _unitFor(jobType) {
    // verify counts archive files (份), cleanup counts deleted files (個檔),
    // export/import count messages (筆). Header reads "Processed" / "處理量"
    // and the row appends the right unit so "3,454" never gets misread as
    // "only 3,454 messages" when verify actually scanned 3,454 archives
    // containing millions of messages.
    if (jobType === 'verify')  return t('unit_archives');
    if (jobType === 'cleanup') return t('unit_files');
    return t('unit_records'); // export, import, default
}
function formatRecords(done, total, jobType) {
    const d = formatNumber(done);
    const u = jobType ? ` <span class="u024">${_unitFor(jobType)}</span>` : '';
    if (!total) return `${d}${u}`;
    const t_ = formatNumber(total);
    return `<span class="u149"><strong>${d}</strong> <span class="u027">of</span> <span class="u028">${t_}</span>${u}</span>`;
}

function formatDT(iso) {
    if (!iso) return '-';
    // Ensure UTC parsing — DB stores UTC without Z suffix
    let s = iso;
    if (!s.endsWith('Z') && !s.includes('+') && !s.includes('-', 10)) s += 'Z';
    const d = new Date(s);
    const pad = (n) => String(n).padStart(2, '0');
    const tz = -d.getTimezoneOffset();
    const tzSign = tz >= 0 ? '+' : '-';
    const tzH = pad(Math.floor(Math.abs(tz) / 60));
    const tzM = pad(Math.abs(tz) % 60);
    return `${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())} ${tzSign}${tzH}:${tzM}`;
}

function formatElapsed(startIso, endIso) {
    if (!startIso) return '-';
    let s = startIso;
    if (!s.endsWith('Z') && !s.includes('+') && !s.includes('-', 10)) s += 'Z';
    const start = new Date(s);
    let end;
    if (endIso) {
        let e = endIso;
        if (!e.endsWith('Z') && !e.includes('+') && !e.includes('-', 10)) e += 'Z';
        end = new Date(e);
    } else {
        end = new Date();
    }
    const sec = Math.max(0, Math.floor((end - start) / 1000));
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    const remSec = sec % 60;
    if (min < 60) return `${min}m${remSec ? remSec + 's' : ''}`;
    const hr = Math.floor(min / 60);
    const remMin = min % 60;
    return `${hr}h${remMin ? remMin + 'm' : ''}`;
}

function statusBadge(status, errorMessage) {
    const icons = {
        completed: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>',
        completed_with_failures: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff9800" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>',
        running: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff9800" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6v6l4 2"/><circle cx="12" cy="12" r="10"/></svg>',
        failed: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f44336" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        pending: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6"/></svg>',
        deleted: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 9L18 20.35C17.84 21.3 17.01 22 16.04 22H7.96C6.99 22 6.16 21.3 6 20.35L4 9"/><path d="M21 6H15.38M3 6H8.63M8.63 6V4C8.63 2.9 9.52 2 10.63 2H13.38C14.48 2 15.38 2.9 15.38 4V6M8.63 6H15.38"/></svg>',
        corrupted: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f44336" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>',
        missing: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff9800" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>',
        tampered: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d32f2f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9.5" y1="9.5" x2="14.5" y2="14.5"/><line x1="14.5" y1="9.5" x2="9.5" y2="14.5"/></svg>',
    };
    const labels = {
        corrupted: t('status_corrupted'),
        missing: t('status_missing'),
        tampered: t('status_tampered'),
        completed_with_failures: t('status_completed_with_failures'),
    };
    // A "completed" job with a non-empty error_message that mentions
    // "Compliance violation" is a partial success — render as
    // completed_with_failures (orange checkmark) with the violation message
    // as tooltip.
    let renderStatus = status;
    if (status === 'completed' && errorMessage && errorMessage.indexOf('Compliance violation') !== -1) {
        renderStatus = 'completed_with_failures';
    }
    const label = labels[renderStatus] || (renderStatus === 'completed_with_failures' ? errorMessage : renderStatus);
    const tooltip = renderStatus === 'completed_with_failures' ? errorMessage : (labels[renderStatus] || renderStatus);
    return `<span class="status-${renderStatus}" title="${esc(tooltip)}">${icons[renderStatus] || renderStatus}</span>`;
}

// ---- Dashboard ----
function buildSparkSVG(data, color, unit) {
    if (!data || data.length < 2) return '';
    const vals = data.map(d => d.count);
    const days = data.map(d => d.day);
    const max = Math.max(...vals, 1);
    const w = 200, h = 50;
    const step = w / (vals.length - 1);
    const points = vals.map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * h * 0.85).toFixed(1)}`).join(' ');
    const areaPoints = `0,${h} ${points} ${w},${h}`;
    // Invisible hover rects for tooltip
    const hoverRects = vals.map((v, i) => {
        const x = (i * step - step / 2).toFixed(1);
        const rw = step.toFixed(1);
        const label = unit === 'bytes' ? formatBytes(v) : formatNumber(v);
        return `<rect x="${Math.max(0, x)}" y="0" width="${rw}" height="${h}" fill="transparent"><title>${days[i]}: ${label}</title></rect>`;
    }).join('');
    return `<svg class="sparkline-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <defs><linearGradient id="sg-${color.replace('#','')}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0.05"/>
        </linearGradient></defs>
        <polygon points="${areaPoints}" fill="url(#sg-${color.replace('#','')})" />
        <polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" />
        ${hoverRects}
    </svg>`;
}

async function loadDashboard() {
    try {
        const status = await fetchJSON(`${API}/status`);
        const s = status.archive_stats;
        document.getElementById('stat-total').textContent = formatNumber(s.total);
        document.getElementById('stat-messages').textContent = formatNumber(s.total_messages);
        document.getElementById('stat-original').textContent = formatBytes(s.total_original_bytes || 0);
        document.getElementById('stat-size').textContent = formatBytes(s.total_bytes || 0);
        document.getElementById('stat-disk').textContent = formatMB(status.storage_stats.available_mb || 0);

        // Sparklines
        const sp = status.sparkline || {};
        const cardArchives = document.getElementById('card-archives');
        const cardMessages = document.getElementById('card-messages');
        const cardSize = document.getElementById('card-size');
        const cardOriginal = document.getElementById('card-original');
        if (cardArchives) cardArchives.insertAdjacentHTML('beforeend', buildSparkSVG(sp.archives, '#6c63ff', 'number'));
        if (cardMessages) cardMessages.insertAdjacentHTML('beforeend', buildSparkSVG(sp.messages, '#4caf50', 'number'));
        if (cardOriginal) cardOriginal.insertAdjacentHTML('beforeend', buildSparkSVG(sp.original_bytes, '#29b6f6', 'bytes'));
        if (cardSize) cardSize.insertAdjacentHTML('beforeend', buildSparkSVG(sp.bytes, '#ff9800', 'bytes'));
    } catch (e) {
        console.error('Failed to load dashboard stats:', e);
    }

    const _stb0 = document.querySelector('#servers-table tbody');
    if (_stb0) _stb0.innerHTML = `<tr><td colspan="5" class="text-center text-muted"><span class="spinner-text">${t('loading')}...</span></td></tr>`;
    try {
        const servers = await fetchJSON(`${API}/servers`);
        // Detect Data Node — set global flag for export/import mode warnings
        window._hasDataNode = (servers.items || []).some(s => s.has_datanode);
        // Store default server name for schedule table display
        if (servers.items && servers.items.length > 0) {
            window._defaultServerName = servers.items[0].name;
        }
        const tbody = document.querySelector('#servers-table tbody');
        tbody.innerHTML = servers.items.map((s, i) => `
            <tr>
                <td>${esc(s.name)}</td>
                <td>${esc(s.url)}</td>
                <td>${s.connected ? statusBadge('completed') : statusBadge('failed')}</td>
                <td>${s.version || '-'}${s.has_datanode ? ' <span class="u031">(Data Node)</span>' : ''}</td>
                <td><button class="btn-sm btn-secondary" data-act="testGraylogServer" data-args="${esc(JSON.stringify([s.name, i]))}">${icon('refresh', 14)} ${t('btn_test_connection')}</button></td>
            </tr>
            <tr class="srv-result-row hidden" id="srv-result-row-${i}"><td colspan="5"><div id="srv-result-${i}" class="test-result-line"></div></td></tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load servers:', e);
    }

    try {
        const jobs = await fetchJSON(`${API}/jobs?limit=5`);
        const tbody = document.querySelector('#recent-jobs-table tbody');
        tbody.innerHTML = jobs.items.map(j => {
            const srcParts = (j.source || '').split(':');
            const st = srcParts[0] || '', sm = srcParts[1] || '';
            let badges = '';
            if (st === 'scheduled') badges += '<span class="job-badge job-badge-sched">' + t('job_scheduled') + '</span> ';
            else if (st === 'manual') badges += '<span class="job-badge job-badge-manual">' + t('job_manual') + '</span> ';
            if (sm === 'api') badges += '<span class="job-badge u002">API</span>';
            else if (sm === 'opensearch') badges += '<span class="job-badge u001">OS</span>';
            else if (st && !sm) badges += '<span class="job-badge u002">API</span>';
            const isDim = j.status === 'completed' && j.messages_done === 0 && !j.error_message;
            return `
            <tr class="${isDim ? 'job-row-dim' : ''}">
                <td title="${j.id}">${j.id.substring(0, 8)}</td>
                <td>${j.job_type} ${badges}</td>
                <td>${statusBadge(j.status, j.error_message)}</td>
                <td>${j.progress_pct.toFixed(0)}%</td>
                <td class="u147">${isDim ? '<span class="u024">' + t('job_no_new_data') + '</span>' : formatRecords(j.messages_done, j.messages_total, j.job_type)}</td>
                <td>${formatDT(j.started_at)}</td>
                <td>${formatElapsed(j.started_at, j.completed_at)}</td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load jobs:', e);
    }
}

// ---- OpenSearch ----
async function loadOpenSearchStatus() {
    try {
        const el = document.getElementById('opensearch-info');
        if (!el) return;
        let servers = [];
        try { servers = (await fetchJSON(`${API}/servers`)).items || []; } catch (_) {}
        // Per-server view: show EACH Graylog server's resolved OpenSearch cluster
        // (its own per-server block, or the global fallback). A multi-cluster setup
        // used to hide every server except the global one — making users think the
        // others were on API mode.
        if (Array.isArray(servers) && servers.length) {
            const rows = [];
            for (const s of servers) {
                let data = null;
                try { data = await fetchJSON(`${API}/opensearch/status?server=${encodeURIComponent(s.name)}`); } catch (_) {}
                rows.push(renderOsServerRow(s.name, data));
            }
            el.innerHTML = rows.join('');
            return;
        }
        // Fallback (no server list): single global status.
        const data = await fetchJSON(`${API}/opensearch/status`);
        el.innerHTML = data.configured ? renderOsServerRow(null, data)
            : `<span class="u030">${t('opensearch_not_configured')}</span> <span class="text-muted">${t('opensearch_optional_note')}</span>`;
    } catch (e) {}
}

function renderOsServerRow(serverName, data) {
    const nameLabel = serverName
        ? `<span class="os-server-name">${icon('server')} ${esc(serverName)}</span>` : '';
    if (!data || !data.configured) {
        return `<div class="os-server-row">${nameLabel} <span class="u030">${t('opensearch_not_configured')}</span></div>`;
    }
    let src = '';
    if (serverName) {
        src = data.source === 'per-server'
            ? ` <span class="os-src os-src-own" title="${t('os_src_perserver_hint')}">${t('os_src_perserver')}</span>`
            : ` <span class="os-src os-src-global" title="${t('os_src_global_hint')}">${t('os_src_global')}</span>`;
    }
    const multi = data.hosts.length > 1;
    const hosts = data.hosts.map((h, i) => {
        // "Node 1" marks the first failover node WITHIN this cluster (only shown
        // when a cluster actually has >1 node) — not a "primary cluster".
        const badge = (multi && i === 0)
            ? ` <span class="u075" title="${t('os_primary_hint')}">&#9679; ${t('os_primary')}</span>` : '';
        const sv = serverName || '';
        return `<span class="host-label" data-server="${esc(sv)}" data-idx="${i}" data-count="${data.hosts.length}" oncontextmenu="showHostMenu(event)" title="${t('os_right_click')}">${icon('server')} ${esc(h)}${badge}</span>`;
    }).join(' ');
    return `<div class="os-server-row">${nameLabel}${src} <span class="os-hosts">${hosts}</span></div>`;
}

function showHostMenu(e) {
    e.preventDefault();
    const elx = e.currentTarget;
    const server = (elx && elx.dataset.server) || '';
    const idx = parseInt((elx && elx.dataset.idx) || '0', 10);
    const count = parseInt((elx && elx.dataset.count) || '1', 10);
    // Remove existing menu
    const old = document.getElementById('host-context-menu');
    if (old) old.remove();

    const menu = document.createElement('div');
    menu.id = 'host-context-menu';
    menu.className = 'context-menu';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';

    let items = '';
    // Reordering only means something for a multi-node cluster's non-first node.
    if (count > 1 && idx > 0) {
        items += `<div class="context-menu-item" data-act="osSetPrimary" data-args="${esc(JSON.stringify([server, idx]))}">${icon('shield')} ${t('os_set_primary')}</div>`;
    }
    items += `<div class="context-menu-item" data-act="osTestSingle" data-args="${esc(JSON.stringify([server, idx]))}">${icon('refresh')} ${t('btn_test_connection')}</div>`;
    if (count > 1 && idx === 0) {
        items += `<div class="context-menu-item disabled">${icon('shield')} ${t('os_is_primary')}</div>`;
    }

    menu.innerHTML = items;
    document.body.appendChild(menu);

    // Close on click anywhere
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }, {once: true});
    }, 10);
}

async function osSetPrimary(server, idx) {
    try {
        await fetchJSON(`${API}/opensearch/reorder`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({server: server || null, from_index: idx, to_index: 0}),
        });
        loadOpenSearchStatus();
    } catch (e) {
        const el = document.getElementById('opensearch-result');
        if (el) el.innerHTML = `<span class="status-failed">${e.message}</span>`;
    }
}

async function osTestSingle(server, idx) {
    const resultEl = document.getElementById('opensearch-result');
    try {
        const q = server ? `?server=${encodeURIComponent(server)}` : '';
        const data = await fetchJSON(`${API}/opensearch/status${q}`);
        const host = data.hosts[idx];
        resultEl.innerHTML = `<span class="spinner-text">${esc(host)}...</span>`;
        const res = await fetchJSON(`${API}/opensearch/test`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({hosts: [host]}),
        });
        if (res.connected) {
            resultEl.innerHTML = `<span class="status-completed">${esc(host)} — Connected!</span> ${esc(res.version || '')}`;
        } else {
            resultEl.innerHTML = `<span class="status-failed">${esc(host)} — ${esc(res.error || 'Failed')}</span>`;
        }
    } catch (e) {
        resultEl.innerHTML = `<span class="status-failed">${e.message}</span>`;
    }
}

async function testOpenSearch() {
    const resultEl = document.getElementById('opensearch-result');
    resultEl.innerHTML = '<span class="u022">Testing...</span>';
    try {
        const data = await fetchJSON(`${API}/opensearch/test`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}',
        });
        if (data.connected) {
            resultEl.innerHTML = `<span class="status-completed">${t('test_connected')}</span> ${esc(data.cluster_name || '')} — ${esc(data.version || '')} — ${t('os_status')}: ${esc(data.status || '')} — ${t('os_nodes')}: ${esc(String(data.nodes || ''))}`;
        } else {
            resultEl.innerHTML = `<span class="status-failed">${t('test_failed')}</span> ${esc(data.error || t('unknown_error'))}`;
        }
    } catch (e) {
        resultEl.innerHTML = `<span class="status-failed">${t('test_error')}</span> ${esc(e.message)}`;
    }
}

// ---- Notifications ----
async function loadNotifyStatus() {
    try {
        const data = await fetchJSON(`${API}/notify/status`);
        const el = document.getElementById('notify-info');
        const btn = document.querySelector('#notify-card .btn-secondary');
        if (!el) return;
        if (data.channels.length > 0) {
            const names = data.channels.map(c => c.name).join(', ');
            el.innerHTML = `${t('enabled_channels')}: <strong>${names}</strong>`;
            if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
        } else {
            el.innerHTML = `<span class="u030">${t('no_channels')}</span>`;
            if (btn) { btn.disabled = true; btn.style.opacity = '0.4'; btn.style.cursor = 'not-allowed'; }
        }
    } catch (e) {}
}

async function testNotify() {
    const el = document.getElementById('notify-result');
    el.innerHTML = '<span class="u022">Sending...</span>';
    try {
        const data = await fetchJSON(`${API}/notify/test`, {method: 'POST'});
        if (data.results && data.results.length > 0) {
            const lines = data.results.map(r =>
                `${esc(r.channel)}: ${r.success ? '<span class="status-completed">' + t('notify_sent') + '</span>' : '<span class="status-failed">' + esc(r.error || 'Failed') + '</span>'}`
            );
            el.innerHTML = lines.join('<br>');
        } else {
            el.innerHTML = `<span class="u030">${t('notify_no_channels')}</span>`;
        }
    } catch (e) {
        el.innerHTML = `<span class="status-failed">${e.message}</span>`;
    }
}

// ---- Archives ----
let archivePage = 1;
let archiveSort = 'time_from';
let archiveOrder = 'desc';

async function loadArchives(page) {
    archivePage = page || 1;
    const tbody = document.querySelector('#archives-table tbody');
    if (tbody) tbody.innerHTML = `<tr><td class="u144" colspan="20"><span class="spinner-text">${t('loading')}...</span></td></tr>`;
    try { await _loadArchivesInner(page); } catch(e) {
        if (tbody) tbody.innerHTML = `<tr><td class="u140" colspan="20">${t('load_failed')}</td></tr>`;
    }
}
async function _loadArchivesInner(page) {
    archivePage = page || 1;
    const params = new URLSearchParams({page: archivePage, page_size: 50, sort: archiveSort, order: archiveOrder});
    const server = document.getElementById('filter-server')?.value;
    const stream = document.getElementById('filter-stream')?.value;
    const fromRaw = document.getElementById('filter-from')?.value;
    const toRaw = document.getElementById('filter-to')?.value;
    // Convert local datetime-local to UTC ISO string for API
    const localToUTC = (v) => { if (!v) return ''; const d = new Date(v); return d.toISOString().replace('.000Z', 'Z'); };
    const from = localToUTC(fromRaw);
    const to = localToUTC(toRaw);
    if (server) params.set('server', server);
    if (stream) params.set('stream', stream);
    if (from) params.set('time_from', from);
    if (to) params.set('time_to', to);

    // Remember the ACTIVE filter so "select all matching" can span every page
    // (and reset a cross-page selection when the filter itself changes).
    const newFilter = {server: server || '', stream: stream || '', time_from: from || '', time_to: to || ''};
    if (JSON.stringify(newFilter) !== JSON.stringify(_archiveFilter)) {
        _selectAllPages = false;
        const _sa = document.getElementById('archive-select-all'); if (_sa) _sa.checked = false;
    }
    _archiveFilter = newFilter;

    const data = await fetchJSON(`${API}/archives?${params}`);
    _archiveTotal = data.total || 0;
    // Load stream names for display
    if (!window._streamNames) {
        try {
            const sd = await fetchJSON(`${API}/streams`);
            window._streamNames = {};
            (sd.items || []).forEach(s => { window._streamNames[s.id] = s.title; });
        } catch(e) { window._streamNames = {}; }
    }
    const _sn = window._streamNames || {};
    const tbody = document.querySelector('#archives-table tbody');
    tbody.innerHTML = data.items.map(a => `
        <tr>
            <td><input type="checkbox" class="archive-check" value="${a.id}" data-act-change="onArchiveCheckChange"></td>
            <td class="col-id">${a.id}</td>
            <td class="col-server">${esc(a.server_name)}</td>
            <td class="col-stream">${esc(a.stream_id && a.stream_id.match(/^[a-z]+_\d+$/) ? a.stream_id : (_sn[a.stream_id] || a.stream_name || (a.stream_id ? a.stream_id.substring(0,8) + '...' : 'all')))}</td>
            <td class="col-from">${formatDT(a.time_from)}</td>
            <td class="col-to">${formatDT(a.time_to)}</td>
            <td class="col-records u147">${formatNumber(a.message_count)}</td>
            <td class="col-compressed u147">${formatBytes(a.file_size_bytes)}</td>
            <td class="col-original u147">${a.original_size_bytes ? formatBytes(a.original_size_bytes) : '~' + formatBytes(a.file_size_bytes * 8)}</td>
            <td class="col-status">${statusBadge(a.status)}</td>
            <td class="col-filename u087">${esc((a.file_path || '').split('/').pop())}</td>
            <td class="col-actions u149">
                <button class="btn-sm btn-primary" data-act="importSingle" data-args="[${a.id}]" data-i18n="btn_import">Import</button>
                <button class="btn-sm btn-danger" data-act="deleteArchive" data-args="[${a.id}]" data-i18n="btn_delete">Delete</button>
            </td>
        </tr>
    `).join('');
    applyI18n();
    applyColumnSettings();
    initTableSort();

    // Flash effect to indicate filter/load completed
    const table = document.getElementById('archives-table');
    if (table) {
        table.classList.remove('flash-loaded');
        // Force reflow to restart animation
        void table.offsetWidth;
        table.classList.add('flash-loaded');
    }

    const totalPages = Math.ceil(data.total / data.page_size);
    const pag = document.getElementById('archives-pagination');
    if (pag && totalPages > 1) {
        const cur = archivePage;
        const pages = [];
        pages.push(1);
        if (cur > 3) pages.push('...');
        for (let i = Math.max(2, cur - 1); i <= Math.min(totalPages - 1, cur + 1); i++) pages.push(i);
        if (cur < totalPages - 2) pages.push('...');
        if (totalPages > 1) pages.push(totalPages);

        let html = `<button ${cur === 1 ? 'disabled' : ''} data-act="loadArchives" data-args="[${cur - 1}]">&laquo;</button>`;
        pages.forEach(p => {
            if (p === '...') { html += `<span class="u126">...</span>`; }
            else { html += `<button class="${p === cur ? 'active' : ''}" data-act="loadArchives" data-args="[${p}]">${p}</button>`; }
        });
        html += `<button ${cur === totalPages ? 'disabled' : ''} data-act="loadArchives" data-args="[${cur + 1}]">&raquo;</button>`;
        html += `<span class="u104">${data.total} ${t('nav_archives').toLowerCase()}</span>`;
        pag.innerHTML = html;
    } else if (pag) {
        pag.innerHTML = data.total ? `<span class="u024">${data.total} ${t('nav_archives').toLowerCase()}</span>` : '';
    }
}

function toggleColumnSettings() {
    const el = document.getElementById('column-settings');
    el.style.display = el.style.display === 'none' ? 'flex' : 'none';
}

function applyColumnSettings() {
    document.querySelectorAll('#column-settings input[data-col]').forEach(cb => {
        const cls = cb.getAttribute('data-col');
        const show = cb.checked;
        document.querySelectorAll('.' + cls).forEach(el => {
            el.style.display = show ? '' : 'none';
        });
    });
}

// Init column settings — bind change events and apply defaults
function initColumnSettings() {
    document.querySelectorAll('#column-settings input[data-col]').forEach(cb => {
        // Load saved preference
        const cls = cb.getAttribute('data-col');
        const saved = localStorage.getItem('col-' + cls);
        if (saved !== null) cb.checked = saved === '1';
        cb.addEventListener('change', () => {
            localStorage.setItem('col-' + cls, cb.checked ? '1' : '0');
            applyColumnSettings();
        });
    });
    applyColumnSettings();
}

let _selectAllPages = false;   // true = "all archives matching the current filter"
let _archiveFilter = {};       // the filter the current list was loaded with
let _archiveTotal = 0;         // total archives matching that filter (all pages)

// Header checkbox: select/deselect the CURRENT page. A plain click no longer
// needs Shift — if more rows match the filter than are on this page, the
// batch bar offers a discoverable "select all N matching" link (Gmail-style).
function toggleArchiveSelectAll(evt) {
    const el = evt.target;
    _selectAllPages = false;   // a page-level toggle always clears cross-page mode
    document.querySelectorAll('.archive-check').forEach(cb => cb.checked = el.checked);
    onArchiveCheckChange();
}

// Cross-page: select EVERY archive matching the active filter (all pages).
function selectAllMatching() {
    _selectAllPages = true;
    document.querySelectorAll('.archive-check').forEach(cb => cb.checked = true);
    const sa = document.getElementById('archive-select-all'); if (sa) sa.checked = true;
    onArchiveCheckChange();
}

function clearArchiveSelection() {
    _selectAllPages = false;
    document.querySelectorAll('.archive-check').forEach(cb => cb.checked = false);
    const sa = document.getElementById('archive-select-all'); if (sa) sa.checked = false;
    onArchiveCheckChange();
}

function onArchiveCheckChange() {
    const checked = document.querySelectorAll('.archive-check:checked');
    const actions = document.getElementById('batch-actions');
    const count = document.getElementById('batch-count');
    const show = checked.length > 0 || _selectAllPages;
    if (actions) actions.style.display = show ? 'flex' : 'none';
    if (count) {
        if (_selectAllPages) {
            // whole filtered set selected — show the real total + a clear link
            count.innerHTML =
                `<strong class="u030">${t('sel_all_matching_active').replace('{n}', formatNumber(_archiveTotal))}</strong> · ` +
                `<a data-act="clearArchiveSelection" class="link-inline">${t('sel_clear')}</a>`;
        } else if (checked.length > 0 && _archiveTotal > checked.length) {
            // more rows match than are on this page — offer cross-page select
            count.innerHTML =
                `${checked.length} ${t('btn_selected')} · ` +
                `<a data-act="selectAllMatching" class="link-inline"><strong>${t('sel_all_matching_offer').replace('{n}', formatNumber(_archiveTotal))}</strong></a>`;
        } else {
            count.textContent = `${checked.length} ${t('btn_selected')}`;
        }
    }
    if (!checked.length && !_selectAllPages) {
        const sa = document.getElementById('archive-select-all'); if (sa) sa.checked = false;
    }
}

async function getSelectedArchiveIds() {
    if (_selectAllPages) {
        // One request returns EVERY id matching the active filter (server /
        // stream / time range) — not the whole archive store, and no per-page walk.
        const p = new URLSearchParams();
        if (_archiveFilter.server) p.set('server', _archiveFilter.server);
        if (_archiveFilter.stream) p.set('stream', _archiveFilter.stream);
        if (_archiveFilter.time_from) p.set('time_from', _archiveFilter.time_from);
        if (_archiveFilter.time_to) p.set('time_to', _archiveFilter.time_to);
        const data = await fetchJSON(`${API}/archives/ids?${p}`);
        return data.ids || [];
    }
    return Array.from(document.querySelectorAll('.archive-check:checked')).map(c => parseInt(c.value));
}

async function batchImport() {
    const selAll = _selectAllPages;
    const ids = await getSelectedArchiveIds();
    if (ids.length === 0) return;
    const openModal = () => {
        // Open import modal for batch
        _importArchiveId = null;
        const modal = document.getElementById('import-modal');
        document.getElementById('modal-import-result').innerHTML = '';
        modal.style.display = 'flex';
        // Override doImportSingle for batch
        window._batchImportIds = ids;
        applyI18n();
        _autofillImportModal();
        _applyImportDataNodeLock();
    };
    // Surface the real count before importing a large / cross-page selection so
    // "select all matching" can never silently queue thousands of archives.
    if (selAll || ids.length > 100) {
        showConfirm(t('batch_import_confirm_title'),
            t('batch_import_confirm_msg').replace('{n}', formatNumber(ids.length)),
            openModal);
    } else {
        openModal();
    }
}

// Pre-fill the import dialog's target fields from the saved restore-target
// defaults (系統設定 → 匯入預設目標). Only fills empty fields so it never
// clobbers something the user already typed. Secrets come back masked; the
// import endpoint substitutes the real stored secret for a masked value.
// Data Node can't reach OpenSearch _bulk → disable Bulk import and force GELF.
async function _applyImportDataNodeLock() {
    let dn = window._hasDataNode;
    if (dn === undefined) {
        try { const s = await fetchJSON(`${API}/servers`); dn = (s.items || []).some(x => x.has_datanode); window._hasDataNode = dn; }
        catch (e) { dn = false; }
    }
    const bulkRadio = document.querySelector('input[name="import-mode"][value="bulk"]');
    if (!bulkRadio) return;
    const bulkLabel = bulkRadio.closest('.mode-option');
    if (dn) {
        bulkRadio.disabled = true;
        if (bulkLabel) { bulkLabel.style.opacity = '0.5'; bulkLabel.title = t('datanode_warning'); }
        const gelfRadio = document.querySelector('input[name="import-mode"][value="gelf"]');
        if (gelfRadio && !gelfRadio.checked) gelfRadio.checked = true;
        onImportModeChange('gelf');
    } else {
        bulkRadio.disabled = false;
        if (bulkLabel) { bulkLabel.style.opacity = ''; bulkLabel.title = ''; }
    }
}

async function _autofillImportModal() {
    let c;
    try { c = await fetchJSON(`${API}/config/import-defaults`); } catch (e) { return; }
    if (!c || c.error) return;
    const setIf = (id, val) => {
        const el = document.getElementById(id);
        if (!el || val === undefined || val === null || val === '') return;
        if (!el.value) { el.value = val; if (el.dataset) el.dataset.userEdited = 'true'; }
    };
    setIf('modal-gelf-host', c.gelf_host);
    setIf('modal-gelf-port', c.gelf_port ? String(c.gelf_port) : '');
    const proto = document.getElementById('modal-gelf-protocol');
    if (proto && c.gelf_protocol && !proto.value) proto.value = c.gelf_protocol;
    setIf('modal-target-api-url', c.target_api_url);
    setIf('modal-target-api-user', c.target_api_username);
    if (c.has_token) setIf('modal-target-api-token', c.target_api_token);
    if (c.has_password) setIf('modal-target-api-pass', c.target_api_password);
}

async function batchDelete() {
    const ids = await getSelectedArchiveIds();
    if (ids.length === 0) return;
    showConfirm(
        `${icon('trash')} ${t('btn_batch_delete')}`,
        `${t('confirm_delete_archive')} (${ids.length} ${t('btn_selected')})`,
        async () => {
            const countEl = document.getElementById('batch-count');
            const btns = document.querySelectorAll('#batch-actions button');
            btns.forEach(b => { b.disabled = true; b.style.opacity = '0.5'; });
            let done = 0;
            let errors = 0;
            for (const id of ids) {
                try {
                    const resp = await fetch(`${API}/archives/${id}`, {method: 'DELETE'});
                    if (!resp.ok) errors++;
                } catch (e) { errors++; }
                done++;
                if (countEl) countEl.innerHTML = `<span class="spinner-text">${done}/${ids.length}...</span>`;
            }
            btns.forEach(b => { b.disabled = false; b.style.opacity = '1'; });
            if (errors > 0) {
                if (countEl) countEl.innerHTML = `<span class="status-failed">${errors} ${t('progress_error')}</span>`;
            }
            // Reset
            _selectAllPages = false;
            const selectAll = document.getElementById('archive-select-all');
            if (selectAll) selectAll.checked = false;
            onArchiveCheckChange();
            loadArchives(archivePage);
        }
    );
}

async function loadArchivePath() {
    try {
        const data = await fetchJSON(`${API}/settings/archive-path`);
        const el = document.getElementById('archive-path-info');
        if (el) el.innerHTML = `${icon('disk')} ${t('archive_path')}: <code>${data.base_path}</code>`;
        const input = document.getElementById('new-archive-path');
        if (input) input.value = data.base_path;
    } catch (e) {}
    loadArchiveTimeline();
}

function clearTimelineSelection() {
    const fromInput = document.getElementById('filter-from');
    const toInput = document.getElementById('filter-to');
    if (fromInput) fromInput.value = '';
    if (toInput) toInput.value = '';
    const selRect = document.getElementById('tl-selection');
    if (selRect) { selRect.setAttribute('width', '0'); selRect.style.display = 'none'; }
    const clearBtn = document.getElementById('tl-clear');
    if (clearBtn) clearBtn.style.visibility = 'hidden';
    const tooltip = document.getElementById('tl-tooltip');
    if (tooltip) tooltip.textContent = t('tl_drag_hint');
    loadArchives(1);
}

async function loadArchiveTimeline() {
    const el = document.getElementById('archive-timeline');
    if (!el) return;
    // Cleanup previous listeners
    if (el._cleanupListeners) el._cleanupListeners();
    try {
        const data = await fetchJSON(`${API}/archives/timeline`);
        if (!data.items || data.items.length === 0) {
            el.innerHTML = '';
            return;
        }
        const items = data.items;
        const earliest = new Date(items[0].day);
        const today = new Date();
        const totalDays = Math.max(1, Math.ceil((today - earliest) / 86400000) + 1);

        const dayMap = {};
        items.forEach(i => { dayMap[i.day] = i; });

        // Use messages (record count) for bar height — more meaningful than file count
        const maxMessages = Math.max(...items.map(i => i.messages), 1);

        const w = 800, h = 70;
        const barWidth = w / totalDays;
        let bars = '';
        let cur = new Date(earliest);
        for (let i = 0; i < totalDays; i++) {
            const dayStr = cur.toISOString().slice(0, 10);
            const item = dayMap[dayStr];
            const x = (i * barWidth).toFixed(2);
            if (item) {
                const barH = Math.max(2, (item.messages / maxMessages) * h * 0.9);
                const y = (h - barH).toFixed(2);
                bars += `<rect class="tl-bar" data-day="${dayStr}" data-count="${item.count}" data-messages="${item.messages}" data-bytes="${item.bytes}" x="${x}" y="${y}" width="${(barWidth - 0.3).toFixed(2)}" height="${barH.toFixed(2)}" fill="var(--accent)" opacity="0.75" />`;
            } else {
                bars += `<rect class="tl-gap" data-day="${dayStr}" x="${x}" y="${h - 3}" width="${(barWidth - 0.3).toFixed(2)}" height="3" fill="var(--danger)" opacity="0.3" />`;
            }
            cur.setDate(cur.getDate() + 1);
        }

        const fmtShort = (d) => `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')}`;
        const fmtShortH = (d) => `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:00`;
        const totalArchives = items.reduce((s, i) => s + i.count, 0);
        const totalMessages = items.reduce((s, i) => s + i.messages, 0);
        const totalBytes = items.reduce((s, i) => s + i.bytes, 0);

        el.innerHTML = `
        <div class="u057">
            <div class="u089">${icon('clock')} ${t('archive_timeline')} <span class="u029">(${totalDays} ${t('export_days')})</span></div>
            <div class="u079" id="tl-tooltip">${t('tl_drag_hint')}</div>
            <button class="u148" id="tl-clear" data-act="clearTimelineSelection">${t('tl_clear')}</button>
        </div>
        <div class="u136">
            <svg class="u152" id="tl-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
                ${bars}
                <rect class="u066" id="tl-selection" x="0" y="0" width="0" height="${h}" fill="var(--accent)" opacity="0.2" pointer-events="none"/>
                <line class="u066" id="tl-cursor" x1="0" y1="0" x2="0" y2="${h}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3,3" opacity="0.7" pointer-events="none"/>
            </svg>
        </div>
        <div class="u058">
            <span>${fmtShort(earliest)}</span>
            <span><strong>${formatNumber(totalArchives)}</strong> ${t('tl_archives')} · <strong>${formatNumber(totalMessages)}</strong> ${t('tl_records')} · <strong>${formatBytes(totalBytes)}</strong></span>
            <span>${fmtShort(today)}</span>
        </div>`;

        // Hover + drag selection handlers
        const tooltip = document.getElementById('tl-tooltip');
        const defaultText = t('tl_drag_hint');
        const svg = document.getElementById('tl-svg');
        const selRect = document.getElementById('tl-selection');
        const clearBtn = document.getElementById('tl-clear');

        // Map x position -> day index for column-based hover
        const xToDayIdx = (clientX) => {
            const r = svg.getBoundingClientRect();
            const ratio = Math.max(0, Math.min(0.9999, (clientX - r.left) / r.width));
            return Math.floor(ratio * totalDays);
        };
        const dayIdxToDate = (idx) => {
            const d = new Date(earliest);
            d.setDate(d.getDate() + idx);
            return d;
        };

        const cursorLine = document.getElementById('tl-cursor');
        let lastHoveredIdx = -1;
        const onSvgHover = (e) => {
            if (window._tlDragging) return;
            // Move cursor line
            const r = svg.getBoundingClientRect();
            const cursorX = ((e.clientX - r.left) / r.width) * w;
            cursorLine.style.display = 'block';
            cursorLine.setAttribute('x1', cursorX.toFixed(2));
            cursorLine.setAttribute('x2', cursorX.toFixed(2));

            const idx = xToDayIdx(e.clientX);
            if (idx === lastHoveredIdx) return;
            // Reset previous bar opacity
            if (lastHoveredIdx >= 0) {
                const prev = svg.querySelector(`[data-day-idx="${lastHoveredIdx}"]`);
                if (prev) prev.setAttribute('opacity', prev.classList.contains('tl-bar') ? '0.75' : '0.3');
            }
            lastHoveredIdx = idx;
            const d = dayIdxToDate(idx);
            const dayStr = d.toISOString().slice(0, 10);
            const item = dayMap[dayStr];
            const cur = svg.querySelector(`[data-day-idx="${idx}"]`);
            if (item) {
                tooltip.innerHTML = `<strong>${dayStr}</strong> · ${item.count} ${t('tl_archives')} · ${formatNumber(item.messages)} ${t('tl_records')} · ${formatBytes(item.bytes)}`;
                if (cur) cur.setAttribute('opacity', '1');
            } else {
                tooltip.innerHTML = `<strong>${dayStr}</strong> · <span class="u018">${t('tl_no_data')}</span>`;
                if (cur) cur.setAttribute('opacity', '0.6');
            }
        };
        const onSvgLeave = () => {
            if (window._tlDragging) return;
            cursorLine.style.display = 'none';
            if (lastHoveredIdx >= 0) {
                const prev = svg.querySelector(`[data-day-idx="${lastHoveredIdx}"]`);
                if (prev) prev.setAttribute('opacity', prev.classList.contains('tl-bar') ? '0.75' : '0.3');
            }
            lastHoveredIdx = -1;
            tooltip.textContent = defaultText;
        };
        svg.addEventListener('mousemove', onSvgHover);
        svg.addEventListener('mouseleave', onSvgLeave);

        // Drag-to-select with hour precision
        const xToDay = (clientX) => {
            const rect = svg.getBoundingClientRect();
            const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            const totalHours = totalDays * 24;
            const hourIdx = Math.floor(ratio * totalHours);
            const d = new Date(earliest);
            d.setHours(d.getHours() + hourIdx);
            return d;
        };

        let dragStart = null;
        let dragStartX = 0;
        let dragMoved = false;

        svg.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            window._tlDragging = true;
            dragMoved = false;
            dragStart = xToDay(e.clientX);
            const r = svg.getBoundingClientRect();
            dragStartX = ((e.clientX - r.left) / r.width) * w;
            e.preventDefault();
        });

        const onMove = (e) => {
            if (!window._tlDragging) return;
            const r = svg.getBoundingClientRect();
            const curX = Math.max(0, Math.min(w, ((e.clientX - r.left) / r.width) * w));
            const x1 = Math.min(dragStartX, curX);
            const x2 = Math.max(dragStartX, curX);
            // Only treat as drag once we've moved >3px
            if (Math.abs(curX - dragStartX) >= 3) {
                dragMoved = true;
                selRect.style.display = 'block';
                selRect.setAttribute('x', x1.toFixed(2));
                selRect.setAttribute('width', (x2 - x1).toFixed(2));
                const dragEnd = xToDay(e.clientX);
                const from = dragStart < dragEnd ? dragStart : dragEnd;
                const to = dragStart < dragEnd ? dragEnd : dragStart;
                tooltip.innerHTML = `<strong>${fmtShortH(from)} ~ ${fmtShortH(to)}</strong>`;
            }
        };

        const onUp = (e) => {
            if (!window._tlDragging) return;
            window._tlDragging = false;
            const dragEnd = xToDay(e.clientX);
            let from, to;
            if (!dragMoved) {
                // Pure click — select 1 hour at click position and move the selection rect
                from = new Date(dragStart);
                to = new Date(dragStart);
                const totalHours = totalDays * 24;
                const hourW = w / totalHours;
                selRect.style.display = 'block';
                selRect.setAttribute('x', dragStartX.toFixed(2));
                selRect.setAttribute('width', hourW.toFixed(2));
            } else {
                from = dragStart < dragEnd ? dragStart : dragEnd;
                to = dragStart < dragEnd ? dragEnd : dragStart;
            }
            // Set "to" to end of day
            // Hour precision: from = start of hour, to = end of hour
            from.setMinutes(0, 0, 0);
            to.setMinutes(59, 59, 0);
            // Format for datetime-local input (local time, no Z)
            const toLocal = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}T${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
            const fromInput = document.getElementById('filter-from');
            const toInput = document.getElementById('filter-to');
            if (fromInput) fromInput.value = toLocal(from);
            if (toInput) toInput.value = toLocal(to);
            clearBtn.style.visibility = 'visible';
            tooltip.innerHTML = `<strong class="u017">${fmtShortH(from)} ~ ${fmtShortH(to)}</strong> ${t('tl_filtering')}`;
            // Apply filter
            loadArchives(1);
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        // Cleanup on next reload
        el._cleanupListeners = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    } catch (e) {
        console.error('Failed to load timeline:', e);
    }
}

function togglePathSettings() {
    const el = document.getElementById('path-settings');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
    document.getElementById('path-save-result').innerHTML = '';
}

async function saveArchivePath() {
    const newPath = document.getElementById('new-archive-path')?.value?.trim();
    const resultEl = document.getElementById('path-save-result');
    if (!newPath) { resultEl.innerHTML = `<span class="status-failed">${t('field_required')}</span>`; return; }

    const data = await fetchJSON(`${API}/settings/archive-path`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({base_path: newPath}),
    });

    if (data.new_path) {
        const msg = t('path_changed_hint')
            .replace('{old}', data.old_path)
            .replace('{new}', data.new_path);
        resultEl.innerHTML = `<span class="status-completed">${t('saved')}</span> (${formatMB(data.available_mb)} ${t('disk_available').toLowerCase()})
            <div class="form-hint u114">${msg}</div>`;
        loadArchivePath();
    } else {
        resultEl.innerHTML = `<span class="status-failed">${data.error || 'Failed'}</span>`;
    }
}

async function rescanArchives() {
    const el = document.getElementById('rescan-result');
    const btn = event.target.closest('button');
    btn.disabled = true;
    btn.style.opacity = '0.5';
    el.innerHTML = `<span class="spinner-text u022">${t('loading')}...</span>`;
    try {
        const data = await fetchJSON(`${API}/settings/rescan`, {method: 'POST'});
        if (data.registered !== undefined) {
            const parts = [];
            parts.push(t('rescan_done').replace('{n}', data.registered));
            if (data.removed > 0) parts.push(t('rescan_removed').replace('{n}', data.removed));
            el.innerHTML = `<span class="status-completed">${parts.join(' ')}</span>`;
            if (data.registered > 0 || data.removed > 0) loadArchives();
        } else {
            el.innerHTML = `<span class="status-failed">${data.error || 'Failed'}</span>`;
        }
    } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
    }
}

function deleteArchive(archiveId) {
    showConfirm(
        `${icon('trash')} ${t('confirm_delete_archive')}`,
        t('confirm_delete_archive'),
        async () => {
            await fetch(`${API}/archives/${archiveId}`, {method: 'DELETE'});
            loadArchives(archivePage);
        }
    );
}

let _importArchiveId = null;

function importSingle(archiveId) {
    _importArchiveId = archiveId;
    const modal = document.getElementById('import-modal');
    document.getElementById('modal-import-result').innerHTML = '';
    modal.style.display = 'flex';
    applyI18n();
    _autofillImportModal();
    _applyImportDataNodeLock();
}

function closeImportModal() {
    // If a job is still running, just hide the modal — don't reset state.
    // The user can reopen via the sidebar progress indicator.
    document.getElementById('import-modal').style.display = 'none';
    if (_activeImportJobId) {
        // Active import is still running. Keep _activeImportJobId, _batchImportIds,
        // progressDiv visibility, etc. so reopen() can show progress mid-stream.
        return;
    }
    _importArchiveId = null;
    window._batchImportIds = null;
    const progressDiv = document.getElementById('import-modal-progress');
    if (progressDiv) progressDiv.style.display = 'none';
    const controls = document.getElementById('import-controls');
    if (controls) controls.style.display = 'none';
    // Reset the post-completion Close button so the next fresh open doesn't
    // show a stale "done" state.
    const doneBtn = document.getElementById('import-done-btn');
    if (doneBtn) doneBtn.style.display = 'none';
    const resultEl = document.getElementById('modal-import-result');
    if (resultEl) resultEl.innerHTML = '';
    const form = document.getElementById('import-modal-form');
    if (form) form.style.display = 'block';
    // Reset auto-fill flags so the next fresh open auto-fills cleanly
    const portEl = document.getElementById('modal-gelf-port');
    if (portEl) portEl.dataset.userEdited = 'false';
    const apiEl = document.getElementById('modal-target-api-url');
    if (apiEl) apiEl.dataset.userEdited = 'false';
    stopImportStatusPoll();
}

// Re-open the import modal mid-import (e.g., user clicked outside to dismiss
// it accidentally and wants to come back to watch the progress). Called from
// the sidebar running-job indicator.
function reopenActiveImportModal() {
    if (!_activeImportJobId) {
        // No active import — fall back to navigating to /jobs
        window.location.href = '/jobs';
        return;
    }
    const modal = document.getElementById('import-modal');
    if (!modal) {
        // Not on a page that has the modal — go to /jobs instead
        window.location.href = '/jobs';
        return;
    }
    modal.style.display = 'flex';
    const form = document.getElementById('import-modal-form');
    if (form) form.style.display = 'none';
    const progressDiv = document.getElementById('import-modal-progress');
    if (progressDiv) progressDiv.style.display = 'block';
    const controls = document.getElementById('import-controls');
    if (controls) controls.style.display = 'flex';
}

let _activeImportJobId = null;

// GELF protocol → port auto-switch
// Default ports: UDP=32201, TCP=32202.
// If the user has manually typed a port we leave it alone.
function onGelfProtocolChange(proto) {
    const portEl = document.getElementById('modal-gelf-port');
    if (!portEl) return;
    if (portEl.dataset.userEdited === 'true') return;
    portEl.value = proto === 'tcp' ? '32202' : '32201';
}

// When user types a GELF host (typically an IP), auto-suggest the matching
// Graylog API URL: http://<host>:9000. Only sets the value if the user hasn't
// manually edited the API URL field.
function onGelfHostChange(host) {
    const apiEl = document.getElementById('modal-target-api-url');
    if (!apiEl) return;
    if (apiEl.dataset.userEdited === 'true') return;
    apiEl.value = host ? `http://${host}:9000` : '';
}

// Switch between GELF and OpenSearch Bulk import modes
function onImportModeChange(mode) {
    const gelfFields = document.getElementById('gelf-mode-fields');
    const bulkFields = document.getElementById('bulk-mode-fields');
    const bulkWarning = document.getElementById('bulk-mode-warning');
    if (gelfFields) gelfFields.style.display = mode === 'gelf' ? 'block' : 'none';
    if (bulkFields) bulkFields.style.display = mode === 'bulk' ? 'block' : 'none';
    if (bulkWarning) bulkWarning.style.display = mode === 'bulk' ? 'block' : 'none';
    // Show Data Node warning when bulk mode selected
    let dnWarn = document.getElementById('datanode-bulk-warning');
    if (!dnWarn && mode === 'bulk' && window._hasDataNode) {
        const parent = bulkWarning?.parentElement || bulkFields?.parentElement;
        if (parent) {
            dnWarn = document.createElement('div');
            dnWarn.id = 'datanode-bulk-warning';
            dnWarn.style.cssText = 'background:rgba(244,67,54,0.1);border:1px solid var(--danger);border-radius:6px;padding:10px 12px;margin:8px 0;font-size:0.9em;color:var(--danger)';
            dnWarn.textContent = t('datanode_warning');
            parent.insertBefore(dnWarn, bulkFields || parent.firstChild);
        }
    }
    if (dnWarn) dnWarn.style.display = (mode === 'bulk' && window._hasDataNode) ? 'block' : 'none';
    // Update visual selection on radio cards
    document.querySelectorAll('.mode-option').forEach(opt => {
        const radio = opt.querySelector('input[type="radio"]');
        if (radio) {
            opt.classList.toggle('mode-option-selected', radio.value === mode);
        }
    });
}

function onBulkAutoDetectToggle(autoDetect) {
    const manual = document.getElementById('bulk-os-manual');
    if (manual) manual.style.display = autoDetect ? 'none' : 'block';
}

async function doImportSingle() {
    const ids = window._batchImportIds || (_importArchiveId ? [_importArchiveId] : []);
    if (ids.length === 0) return;

    const mode = document.querySelector('input[name="import-mode"]:checked')?.value || 'gelf';
    const host = document.getElementById('modal-gelf-host')?.value;
    const port = document.getElementById('modal-gelf-port')?.value || '32202';
    const protocol = document.getElementById('modal-gelf-protocol')?.value || 'tcp';
    const target = document.getElementById('modal-target-name')?.value || host;
    const rateMs = document.getElementById('modal-rate-ms')?.value || '100';
    const apiUrl = document.getElementById('modal-target-api-url')?.value?.trim() || '';
    const apiToken = document.getElementById('modal-target-api-token')?.value?.trim() || '';
    const apiUser = document.getElementById('modal-target-api-user')?.value?.trim() || '';
    const apiPass = document.getElementById('modal-target-api-pass')?.value || '';
    const resultEl = document.getElementById('modal-import-result');

    // --- Required field validation (compliance: zero indexer failures) ---
    // GELF host only required for GELF mode
    if (mode === 'gelf' && !host) {
        resultEl.innerHTML = `<span class="status-failed">${t('import_gelf_host')} is required</span>`;
        return;
    }
    if (!apiUrl) {
        resultEl.innerHTML = `<span class="status-failed">${t('import_target_api_required')}</span>`;
        return;
    }
    if (!apiToken && !(apiUser && apiPass)) {
        resultEl.innerHTML = `<span class="status-failed">${t('import_target_auth_required')}</span>`;
        return;
    }

    const btn = document.getElementById('modal-import-btn');
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
    resultEl.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;

    const body = {
        archive_ids: ids,
        target_server: target || 'restored',
        mode: mode,
        target_api_url: apiUrl,
        target_api_token: apiToken,
        target_api_username: apiUser,
        target_api_password: apiPass,
    };

    if (mode === 'gelf') {
        body.gelf_host = host;
        body.gelf_port = parseInt(port);
        body.gelf_protocol = protocol;
        body.rate_ms = parseInt(rateMs);
        body.batch_size = parseInt(document.getElementById('modal-batch-size')?.value || '500');
        // Sync the live-view batch selector to the chosen starting value.
        const liveBatch = document.getElementById('import-live-batch');
        if (liveBatch) liveBatch.value = String(body.batch_size);
    } else {
        // bulk mode
        body.target_index_pattern = document.getElementById('modal-bulk-index-pattern')?.value?.trim() || 'jt_restored';
        body.dedup_strategy = document.getElementById('modal-bulk-dedup')?.value || 'id';
        body.batch_docs = parseInt(document.getElementById('modal-bulk-batch-docs')?.value || '10000');
        const autoDetect = document.getElementById('modal-bulk-os-autodetect')?.checked;
        if (!autoDetect) {
            body.target_os_url = document.getElementById('modal-bulk-os-url')?.value?.trim() || '';
            body.target_os_username = document.getElementById('modal-bulk-os-user')?.value?.trim() || '';
            body.target_os_password = document.getElementById('modal-bulk-os-pass')?.value || '';
        }
    }

    const result = await fetchJSON(`${API}/import`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    // NOTE: do NOT clear window._batchImportIds here — if the job fails and the
    // user wants to retry (e.g. after fixing the host), we need the ids to be
    // available. closeImportModal() will clear them when the modal is closed.

    if (result.job_id) {
        _activeImportJobId = result.job_id;
        window._activeImportMode = mode;
        // Hide form, show progress
        document.getElementById('import-modal-form').style.display = 'none';
        const progressDiv = document.getElementById('import-modal-progress');
        if (progressDiv) progressDiv.style.display = 'block';
        const controls = document.getElementById('import-controls');
        if (controls) controls.style.display = 'flex';
        // Re-enable the cancel button (a previous run may have disabled it).
        const cancelBtn0 = document.getElementById('import-cancel-btn');
        if (cancelBtn0) { cancelBtn0.disabled = false; cancelBtn0.style.opacity = '1'; }
        // Hide GELF-only controls (pause + speed slider) when running bulk:
        // bulk has no inter-batch delay and pause is not honored by the bulk
        // loop, so the controls would just confuse the user.
        const gelfControls = document.getElementById('import-gelf-controls');
        if (gelfControls) gelfControls.style.display = (mode === 'bulk') ? 'none' : 'flex';
        // Set live rate slider
        const liveRate = document.getElementById('import-live-rate');
        if (liveRate) { liveRate.value = rateMs; const rd = document.getElementById('import-live-rate-display'); if (rd) rd.value = rateMs; }

        resultEl.innerHTML = `<span class="status-completed">${t('import_started')}${esc(result.job_id.substring(0,8))} (${ids.length} ${t('import_archives_unit')})</span>`;
        watchJob(result.job_id, 'import', () => {
            if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
            _activeImportJobId = null;
            // Keep the form HIDDEN after completion — only the progress bar
            // and result text should be visible. User can dismiss the modal
            // by clicking outside or via the explicit Close button shown
            // by the post-completion handler below.
            // (Form will be re-shown next time the modal is opened fresh.)
            if (controls) controls.style.display = 'none';
            // Show a Close button so user can dismiss the modal cleanly.
            const doneBtn = document.getElementById('import-done-btn');
            if (doneBtn) doneBtn.style.display = 'inline-flex';
        });
        // Start journal status polling
        // Always poll journal status — we always have target API credentials now
        startImportStatusPoll(result.job_id);
    } else {
        resultEl.innerHTML = `<span class="status-failed">${esc(result.error || 'Failed')}</span>`;
        if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
    }
}

async function cancelActiveImport() {
    if (!_activeImportJobId) return;
    if (!await customConfirm(t('confirm_cancel_import') || 'Cancel this import?')) return;
    // Immediate feedback: cancellation may take a moment to take effect (the
    // backend checks the cancel flag between preflight steps / message batches).
    const resultEl = document.getElementById('modal-import-result');
    if (resultEl) resultEl.innerHTML = `<span class="spinner-text">${t('import_cancelling')}</span>`;
    const cancelBtn = document.getElementById('import-cancel-btn');
    if (cancelBtn) { cancelBtn.disabled = true; cancelBtn.style.opacity = '0.5'; }
    try {
        await fetchJSON(`${API}/jobs/${_activeImportJobId}/cancel`, {method: 'POST'});
    } catch (e) {
        showAlert(t('error') + ': ' + (e && e.message ? e.message : e));
        if (cancelBtn) { cancelBtn.disabled = false; cancelBtn.style.opacity = '1'; }
    }
}

async function toggleImportPause() {
    if (!_activeImportJobId) return;
    const btn = document.getElementById('import-pause-btn');
    if (!btn) return;
    // Use data-state attribute (not textContent) so it survives i18n switches
    const wasPaused = btn.dataset.state === 'paused';
    const endpoint = wasPaused ? 'resume' : 'pause';
    await fetchJSON(`${API}/import/${_activeImportJobId}/${endpoint}`, {method: 'POST'});
    btn.dataset.state = wasPaused ? 'running' : 'paused';
    btn.dataset.i18n = wasPaused ? 'btn_pause' : 'btn_resume';
    btn.textContent = t(btn.dataset.i18n);
}

async function updateImportRate(val) {
    const rd = document.getElementById('import-live-rate-display'); if (rd) rd.value = parseInt(val);
    if (!_activeImportJobId) return;
    await fetchJSON(`${API}/import/${_activeImportJobId}/rate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate_ms: parseInt(val)}),
    });
}

// Keyboard/numeric entry for the live import speed — clamp, sync the slider,
// and push the new rate to the running job.
async function updateImportRateNum(val) {
    let n = parseInt(val, 10); if (isNaN(n)) n = 100;
    n = Math.max(1, Math.min(2000, n));
    const s = document.getElementById('import-live-rate'); if (s) s.value = n;
    const rd = document.getElementById('import-live-rate-display'); if (rd) rd.value = n;
    if (!_activeImportJobId) return;
    await fetchJSON(`${API}/import/${_activeImportJobId}/rate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate_ms: n}),
    });
}

// Live batch-size adjustment during an import (50/500/1000/2000).
async function updateImportBatch(val) {
    if (!_activeImportJobId) return;
    await fetchJSON(`${API}/import/${_activeImportJobId}/rate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({batch_size: parseInt(val)}),
    });
}

let _importStatusPoll = null;
function startImportStatusPoll(jobId) {
    stopImportStatusPoll();
    _importStatusPoll = setInterval(async () => {
        if (!_activeImportJobId) { stopImportStatusPoll(); return; }
        try {
            const st = await fetchJSON(`${API}/import/${jobId}/status`);
            // Reflect the ACTUAL running batch size in the live selector (unless the
            // user is mid-selection) so it never shows a stale value.
            const lb = document.getElementById('import-live-batch');
            if (lb && st.batch_size && document.activeElement !== lb && String(st.batch_size) !== lb.value) {
                lb.value = String(st.batch_size);
            }
            const badge = document.getElementById('import-journal-badge');
            if (badge && st.journal) {
                badge.style.display = 'inline';
                const u = st.journal.uncommitted;
                const action = st.journal_action;
                const color = action === 'normal' ? 'var(--success)' : action === 'slow' ? 'var(--warning)' : 'var(--danger)';
                const label = t('import_journal_label');
                const actionLabel = t(`import_journal_${action}`) || action;
                let html = `<span data-style="color:${color}">${label}: ${u !== null ? formatNumber(u) : '?'} (${actionLabel})</span>`;
                // Target Graylog JVM heap — the second signal the throttle watches.
                const hp = st.heap_percent;
                if (hp !== null && hp !== undefined) {
                    const hc = hp >= 98 ? 'var(--danger)' : hp >= 95 ? 'var(--warning)' : 'var(--success)';
                    html += ` <span data-style="color:${hc}">· ${t('import_heap_label')}: ${hp}%</span>`;
                }
                // Output ring buffer — the EARLIEST sign Graylog can't drain to
                // OpenSearch (this is what wedges Graylog first).
                const bo = st.buffer_output_pct;
                if (bo !== null && bo !== undefined) {
                    const bc = bo >= 90 ? 'var(--danger)' : bo >= 70 ? 'var(--warning)' : 'var(--success)';
                    html += ` <span data-style="color:${bc}">· ${t('import_buffer_label')}: ${bo}%</span>`;
                }
                // Local box free memory — jt-glogarch shares the VM with Graylog/OS,
                // so low free memory means the import is paused to avoid an OOM.
                const mm = st.mem_available_mb;
                if (mm !== null && mm !== undefined) {
                    const mc = mm <= 700 ? 'var(--danger)' : mm <= 1400 ? 'var(--warning)' : 'var(--success)';
                    html += ` <span data-style="color:${mc}">· ${t('import_mem_label')}: ${formatNumber(mm)}MB</span>`;
                }
                badge.innerHTML = html;
            }
        } catch(e) {}
    }, 5000);
}
function stopImportStatusPoll() {
    if (_importStatusPoll) { clearInterval(_importStatusPoll); _importStatusPoll = null; }
}

// ---- Export ----
async function loadExportPage() {
    // Load current mode from server config
    try {
        const osStatus = await fetchJSON(`${API}/opensearch/status`);
        const modeSelect = document.getElementById('export-mode');
        if (modeSelect) modeSelect.value = osStatus.export_mode || 'api';
        onExportModeChange();
    } catch (e) {}

    // Load servers (from /api/servers — carries per-server Data Node flag).
    try {
        const servers = await fetchJSON(`${API}/servers`);
        const items = servers.items || [];
        window._exportServerDN = {};
        items.forEach(s => { window._exportServerDN[s.name] = !!s.has_datanode; });
        const sel = document.getElementById('export-server');
        if (sel) {
            sel.innerHTML = items.map(s =>
                `<option value="${esc(s.name)}">${esc(s.name)} (${esc(s.url)})${s.has_datanode ? ' — Data Node' : ''}</option>`).join('');
        }
        onExportServerChange();   // apply the Data Node lock for the initial server
    } catch (e) {}

    // Load streams and index sets
    try {
        const servers = await fetchJSON(`${API}/servers`);
        if (servers.items && servers.items.length > 0 && servers.items[0].connected) {
            loadExportStreams();
            loadExportIndexSets();
        }
    } catch (e) {}
}

async function loadExportStreams() {
    const div = document.getElementById('export-stream-list');
    if (div) div.innerHTML = `<span class="u022">${icon('refresh')} ${t('loading')}...</span>`;
    try {
        const data = await fetchJSON(`${API}/streams`);
        if (div && data.items) {
            div.innerHTML = data.items.map(s =>
                `<label><input type="checkbox" class="export-stream-check" value="${s.id}"> ${s.title || s.id}</label>`
            ).join('');
        }
    } catch (e) {
        if (div) div.innerHTML = `<span class="u018">${t('load_failed')}</span>`;
    }
}

// System index prefixes to exclude
const SYSTEM_INDEX_PREFIXES = ['gl-events', 'gl-system-events', 'gl-failures', 'investigation_', 'restored-archive'];

async function loadExportIndexSets() {
    const sel = document.getElementById('export-indexset');
    if (sel) sel.innerHTML = `<option>${t('loading')}...</option>`;
    try {
        const resp = await fetch(`${API}/index-sets`);
        const data = await resp.json();
        if (data.error) {
            if (sel) sel.innerHTML = `<option>${esc(data.error)}</option>`;
            return;
        }
        if (sel && data.items) {
            const filtered = data.items.filter(s =>
                !SYSTEM_INDEX_PREFIXES.some(p => s.index_prefix.startsWith(p))
            );
            sel.innerHTML = '<option value="">-- All (default) --</option>' +
                filtered.map(s =>
                    `<option value="${s.id}" data-prefix="${esc(s.index_prefix)}">${esc(s.title)} (${esc(s.index_prefix)})</option>`
                ).join('');
        }
    } catch (e) {
        if (sel) sel.innerHTML = `<option>${t('load_failed')}</option>`;
    }
    initCustomSelects();
}

// Also load into schedule form if present
async function loadSchedIndexSets() {
    const sel = document.getElementById('sched-indexset');
    if (!sel) return;
    sel.innerHTML = `<option>${t('loading')}...</option>`;
    try {
        const resp = await fetch(`${API}/index-sets`);
        const data = await resp.json();
        if (data.error) {
            sel.innerHTML = `<option>${esc(data.error)}</option>`;
            return;
        }
        if (data.items) {
            const filtered = data.items.filter(s =>
                !SYSTEM_INDEX_PREFIXES.some(p => s.index_prefix.startsWith(p))
            );
            sel.innerHTML = '<option value="">-- All (default) --</option>' +
                filtered.map(s =>
                    `<option value="${s.id}" data-prefix="${esc(s.index_prefix)}">${esc(s.title)} (${esc(s.index_prefix)})</option>`
                ).join('');
        }
    } catch (e) {
        sel.innerHTML = `<option>${t('load_failed')}</option>`;
    }
    initCustomSelects();
}

function onExportRangeChange() {
    const type = document.getElementById('export-range-type')?.value;
    document.getElementById('export-days-group').style.display = type === 'days' ? 'block' : 'none';
    document.getElementById('export-custom-group').style.display = type === 'custom' ? 'block' : 'none';
}

// Selected export server is a Data Node → OpenSearch Direct is unreachable, so
// lock the export to Graylog API (disable the OpenSearch option) instead of just
// warning about it. Falls back to enabling it for a standalone-OpenSearch server.
function onExportServerChange() {
    const srvSel = document.getElementById('export-server');
    const modeSel = document.getElementById('export-mode');
    if (!modeSel) return;
    const isDN = !!(srvSel && window._exportServerDN && window._exportServerDN[srvSel.value]);
    const osOpt = modeSel.querySelector('option[value="opensearch"]');
    if (osOpt) osOpt.disabled = isDN;
    if (isDN && modeSel.value === 'opensearch') modeSel.value = 'api';
    onExportModeChange();
}

function _selectedExportServerIsDN() {
    const srvSel = document.getElementById('export-server');
    return !!(srvSel && window._exportServerDN && window._exportServerDN[srvSel.value]);
}

function onExportModeChange() {
    const mode = document.getElementById('export-mode')?.value;
    const streamGroup = document.getElementById('export-stream-group');
    const hint = document.getElementById('export-mode-hint');
    const coverage = document.getElementById('export-mode-coverage');
    const rangeGroup = document.getElementById('export-range-type')?.closest('.form-group');
    const daysGroup = document.getElementById('export-days-group');
    const customGroup = document.getElementById('export-custom-group');
    if (streamGroup) streamGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (hint) {
        let hintText = mode === 'api' ? t('export_mode_api_hint') : t('export_mode_os_hint');
        const dn = _selectedExportServerIsDN();
        // Data Node: OpenSearch Direct is disabled → explain why the export is
        // locked to Graylog API. Also keep the plain warning if OS is somehow shown.
        if (dn || (mode === 'opensearch' && window._hasDataNode)) {
            hintText += '\n\n' + t('datanode_warning');
        }
        hint.textContent = hintText;
        hint.style.color = (dn || mode === 'opensearch') ? 'var(--warning)' : '';
    }
    // OpenSearch: hide time range selector, show index picker in coverage
    if (rangeGroup) rangeGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (daysGroup) daysGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (customGroup) customGroup.style.display = 'none';
    if (coverage) {
        coverage.style.display = 'block';
        coverage.dataset.wantMode = mode;   // guard against async load races
        if (mode === 'opensearch') {
            loadOsCoverage(coverage);
        } else {
            loadApiCoverage(coverage);
        }
    }
}

async function loadApiCoverage(el) {
    const _want = el.dataset.wantMode;
    el.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;
    try {
        const status = await fetchJSON(`${API}/status`);
        if (el.dataset.wantMode !== _want) return;   // mode switched mid-fetch
        const stats = status.archive_stats || {};
        if (!stats.earliest || !stats.latest) {
            el.innerHTML = `<div class="coverage-box"><span class="u022">${t('log_no_data')}</span></div>`;
            return;
        }

        const earliest = new Date(stats.earliest);
        const latest = new Date(stats.latest);
        const now = new Date();
        const totalSpan = now - earliest || 1;

        let html = '<div class="coverage-box">';
        html += `<div class="u081">${icon('archive')} ${t('api_coverage_title')}</div>`;

        // Timeline bar
        html += '<div class="timeline-bar u097">';
        // Archived range
        const archivedWidth = ((latest - earliest) / totalSpan) * 100;
        html += `<div class="timeline-segment" data-style="left:0;width:${archivedWidth}%;background:var(--success);opacity:0.7" title="${t('api_archived')}"></div>`;
        // Gap (not yet archived)
        if (latest < now) {
            const gapLeft = archivedWidth;
            const gapWidth = 100 - archivedWidth;
            html += `<div class="timeline-segment" data-style="left:${gapLeft}%;width:${gapWidth}%;background:var(--danger);opacity:0.3" title="${t('api_not_archived')}"></div>`;
        }
        html += '</div>';

        // Labels — positioned to match timeline bar
        const fmtShort = (iso) => { const d = new Date(iso); const p = n => String(n).padStart(2,'0'); return `${d.getFullYear()}/${p(d.getMonth()+1)}/${p(d.getDate())}`; };
        html += '<div class="u137">';
        html += `<span class="u132">${t('api_earliest')}<br>${fmtShort(stats.earliest)}</span>`;
        // Position "latest" label at the end of the green bar
        const latestPos = Math.min(archivedWidth, 85); // cap so it doesn't overlap "now"
        html += `<span data-style="position:absolute;left:${latestPos}%;transform:translateX(-50%);text-align:center;font-weight:600;color:var(--success)">${t('api_latest')}<br>${fmtShort(stats.latest)}</span>`;
        html += `<span class="u133">${t('api_now')}</span>`;
        html += '</div>';

        // Stats
        html += `<div class="u050">`;
        html += `<span><span class="u062"></span>${t('api_archived')}: ${formatNumber(stats.total)} ${t('nav_archives').toLowerCase()}, ${formatNumber(stats.total_messages)} ${t('unit_records')}</span>`;
        if (latest < now) {
            const gapHours = Math.round((now - latest) / 3600000);
            html += `<span><span class="u061"></span>${t('api_not_archived')}: ~${gapHours}h</span>`;
        }
        html += '</div>';

        html += '</div>';
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = `<div class="coverage-box u018">${t('load_failed')}</div>`;
    }
}

async function loadOsCoverage(el) {
    const _want = el.dataset.wantMode;
    el.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;
    try {
        // Use selected index set prefix if available
        const isetSel = document.getElementById('export-indexset') || document.getElementById('sched-indexset');
        const selectedOpt = isetSel?.selectedOptions?.[0];
        const prefix = selectedOpt?.getAttribute('data-prefix') || '';
        const qs = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
        const osData = await fetchJSON(`${API}/opensearch/indices${qs}`);
        if (el.dataset.wantMode !== _want) return;   // mode switched mid-fetch
        if (!osData.indices || osData.indices.length === 0) {
            el.innerHTML = `<div class="coverage-box"><span class="u018">${t('os_no_indices')}</span></div>`;
            return;
        }

        const indices = osData.indices;
        const active = osData.active_index || '';

        // Build timeline
        let html = '<div class="coverage-box">';
        html += `<div class="u081">${icon('db')} ${t('os_available_indices')} (${indices.length})</div>`;
        html += '<div class="coverage-timeline">';

        // Find time range
        const allDates = indices.filter(i => i.min_ts && i.max_ts);
        if (allDates.length === 0) {
            html += `<span class="u022">${t('os_no_time_data')}</span>`;
        } else {
            const minTime = new Date(Math.min(...allDates.map(i => new Date(i.min_ts))));
            const maxTime = new Date(Math.max(...allDates.map(i => new Date(i.max_ts))));
            const totalSpan = maxTime - minTime || 1;

            // Today marker
            const now = new Date();

            html += '<div class="timeline-bar">';

            allDates.forEach(idx => {
                const start = new Date(idx.min_ts);
                const end = new Date(idx.max_ts);
                const left = ((start - minTime) / totalSpan) * 100;
                const width = Math.max(((end - start) / totalSpan) * 100, 1);
                const isActive = idx.index === active;
                const color = isActive ? 'var(--warning)' : 'var(--accent)';
                const label = `${idx.index} (${formatNumber(idx.docs_count)} docs)`;
                html += `<div class="timeline-segment" data-style="left:${left}%;width:${width}%;background:${color}" title="${label}"></div>`;
            });

            html += '</div>';

            // Index list (read-only display)
            const exportable = allDates.filter(i => i.index !== active);
            html += `<div class="os-index-list u115">`;
            allDates.forEach(idx => {
                const isActive = idx.index === active;
                const shortName = idx.index.replace(/.*_/, '#');
                const start = new Date(idx.min_ts);
                const end = new Date(idx.max_ts);
                const pad = n => String(n).padStart(2, '0');
                const dateRange = `${pad(start.getMonth()+1)}/${pad(start.getDate())} ~ ${pad(end.getMonth()+1)}/${pad(end.getDate())}`;
                const ic = isActive ? icon('clock') : icon('archive');
                html += `<div class="os-index-item ${isActive ? 'os-index-active' : ''}" title="${esc(idx.index)}">
                    <span>${ic} ${shortName}</span>
                    <span class="os-index-date">${dateRange}</span>
                    ${isActive ? '<span class="os-index-tag">' + t('os_active_skip') + '</span>' : '<span></span>'}
                    <span class="os-index-docs">${formatNumber(idx.docs_count)}</span>
                </div>`;
            });
            html += '</div>';

            // Keep N indices input — prominent
            html += `<div class="u107">
                <div class="u038">
                    <label class="u088">${icon('archive')} ${t('os_keep_recent')}</label>
                    <input class="u161" type="number" id="os-keep-n" value="${exportable.length}" min="1"
                       >
                    <span class="u090"> ${t('os_of_exportable').replace('{n}', exportable.length)}</span>
                </div>
                <small class="form-hint u113">${t('os_keep_recent_hint')}</small>
            </div>`;

            // Legend
            html += '<div class="u049">';
            html += `<span><span class="u060"></span>${t('os_exportable')}</span>`;
            html += `<span><span class="u063"></span>${t('os_active_skip')}</span>`;
            html += `<span class="u018">${t('os_not_available')}</span>`;
            html += '</div>';
        }

        html += '</div></div>';
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = `<div class="coverage-box u018">${t('load_failed')}</div>`;
    }
}

async function startExport() {
    const mode = document.getElementById('export-mode')?.value || 'api';
    const server = document.getElementById('export-server')?.value;
    const rangeType = document.getElementById('export-range-type')?.value || 'days';
    const from = document.getElementById('export-from')?.value;
    const to = document.getElementById('export-to')?.value;
    const days = document.getElementById('export-days')?.value;
    const resume = document.getElementById('export-resume')?.checked;
    const indexSet = document.getElementById('export-indexset')?.value;

    const streamChecks = document.querySelectorAll('.export-stream-check:checked');
    const streams = Array.from(streamChecks).map(c => c.value);

    if (rangeType === 'days' && !days) { showConfirm(icon('warning'), t('export_days') + ' is required', null); return; }
    if (rangeType === 'custom' && !from) { showConfirm(icon('warning'), t('alert_set_start_time'), null); return; }

    const body = {
        mode: mode,
        server: server,
        time_from: (rangeType === 'custom' && from) ? new Date(from).toISOString().replace('.000Z', 'Z') : null,
        time_to: (rangeType === 'custom' && to) ? new Date(to).toISOString().replace('.000Z', 'Z') : null,
        days: rangeType === 'days' ? parseInt(days) : null,
        resume: resume,
        index_set: indexSet || null,
        streams: streams.length > 0 ? streams : null,
    };

    // Disable button
    const btn = document.querySelector('[data-act="startExport"]');
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; btn.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`; }

    const result = await fetchJSON(`${API}/export`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    const resetBtn = () => { if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.innerHTML = `${icon('play')} ${t('btn_start_export')}`; } };

    if (result.job_id) {
        document.getElementById('export-progress').style.display = 'block';
        document.getElementById('export-progress-text').textContent = t('loading') + '...';
        // Poll immediately once, then start watchJob
        setTimeout(async () => {
            try {
                const job = await fetchJSON(`${API}/jobs/${result.job_id}`);
                if (job && (job.status === 'completed' || job.status === 'failed')) {
                    // Already done — show result directly
                    const bar = document.getElementById('export-progress-bar');
                    const text = document.getElementById('export-progress-text');
                    if (bar) bar.style.width = '100%';
                    if (job.status === 'failed') {
                        if (text) text.innerHTML = `<span class="status-failed">${t('progress_error')}${job.error_message || ''}</span>`;
                    } else if ((job.messages_done || 0) === 0) {
                        if (text) text.innerHTML = `<span class="u030">${t('export_no_data')}</span>`;
                    } else {
                        if (text) text.innerHTML = `<span class="status-completed">${t('progress_completed')} (${formatNumber(job.messages_done)} ${t('unit_records')})</span>`;
                    }
                    resetBtn();
                    return;
                }
            } catch(e) {}
            // Not done yet — use watchJob for ongoing progress
            watchJob(result.job_id, 'export', resetBtn);
        }, 1500);
    } else {
        resetBtn();
        document.getElementById('export-progress').style.display = 'block';
        document.getElementById('export-progress-text').innerHTML = `<span class="status-failed">${esc(result.error || 'Failed')}</span>`;
    }
}

// ---- Import ----
// Import page removed — import is done via batch actions on the Archives page

// ---- Jobs ----
// Colored chip summarising an OpenSearch export's index-set coverage
// (from the job's structured `result`). Green = all covered; amber = some skipped.
function coverageChip(job) {
    const r = job && job.result;
    if (!r || r.index_sets_covered === undefined || r.index_sets_covered === null) return '';
    const skipped = r.index_sets_skipped || [];
    if (skipped.length === 0) {
        return `<span class="cov-chip cov-ok" title="${t('job_cov_all_hint')}">&#10003; ${t('job_cov_all')}</span>`;
    }
    return `<span class="cov-chip cov-warn" title="${t('job_cov_partial_hint')}: ${esc(skipped.join(', '))}">&#9888; ${skipped.length} ${t('job_cov_partial')}</span>`;
}

async function loadJobs() {
    const tbody = document.querySelector('#jobs-table tbody');
    if (!tbody) return;
    const data = await fetchJSON(`${API}/jobs?limit=100`);
    if (!data.items) return;
    tbody.innerHTML = data.items.map(j => {
        const isRunning = j.status === 'running' || j.status === 'pending';
        const cancelBtn = isRunning
            ? `<button class="btn-sm btn-danger" data-act="cancelJob" data-arg="${j.id}" data-i18n="btn_cancel">Cancel</button>`
            : '';
        // Records display with context
        let recordsHtml;
        if (j.status === 'completed' && j.messages_done === 0 && !j.error_message) {
            recordsHtml = `<span class="u024">${t('job_no_new_data')}</span>`;
        } else {
            recordsHtml = formatRecords(j.messages_done, j.messages_total, j.job_type);
        }

        // Source + mode badges
        const srcParts = (j.source || '').split(':');
        const srcType = srcParts[0] || '';
        const srcMode = srcParts[1] || '';
        let srcHtml = '';
        if (srcType === 'scheduled') srcHtml += `<span class="job-badge job-badge-sched">${t('job_scheduled')}</span> `;
        else if (srcType === 'manual') srcHtml += `<span class="job-badge job-badge-manual">${t('job_manual')}</span> `;
        if (srcMode === 'api') srcHtml += `<span class="job-badge u002">API</span>`;
        else if (srcMode === 'opensearch') srcHtml += `<span class="job-badge u001">OpenSearch</span>`;
        else if (srcType && !srcMode) srcHtml += `<span class="job-badge u002">API</span>`;

        return `<tr class="${j.status === 'completed' && j.messages_done === 0 ? 'job-row-dim' : ''}">
            <td title="${j.id}">${j.id.substring(0, 8)}</td>
            <td>${j.job_type} ${srcHtml}</td>
            <td>${statusBadge(j.status)}</td>
            <td class="u149">
                <div class="progress-bar u155">
                    <div class="progress-fill" data-style="width:${j.progress_pct}%"></div>
                </div> ${j.progress_pct.toFixed(0)}%
                ${j.current_detail && j.status === 'running' ? `<div class="u074" title="${esc(j.current_detail)}">${esc(j.current_detail)}</div>` : ''}
            </td>
            <td class="u147">${recordsHtml}</td>
            <td>${formatDT(j.started_at)}</td>
            <td>${formatDT(j.completed_at)}</td>
            <td>${formatElapsed(j.started_at, j.completed_at)}</td>
            <td data-style="color:${j.status === 'failed' || (j.error_message || '').indexOf('Compliance violation') !== -1 || (j.error_message || '').indexOf('Interrupted') !== -1 ? 'var(--danger)' : (j.error_message || '').indexOf('Skipped') !== -1 ? 'var(--text-muted)' : 'var(--text-muted)'};font-size:0.85em;max-width:220px;overflow:hidden;text-overflow:ellipsis" title="${esc(j.error_message || '')}">${coverageChip(j)}${esc(j.error_message || '')}</td>
            <td>${cancelBtn}</td>
        </tr>`;
    }).join('');
    applyI18n();
}

function cancelJob(jobId) {
    showConfirm(
        `${icon('trash')} ${t('confirm_cancel_job')}`,
        t('cancel_job_desc'),
        async () => {
            await fetchJSON(`${API}/jobs/${jobId}/cancel`, {method: 'POST'});
            loadJobs();
        }
    );
}

// ---- Schedules ----
async function loadSchedules() {
    // Load schedule list + running jobs
    const [data, jobsData] = await Promise.all([
        fetchJSON(`${API}/schedules`),
        fetchJSON(`${API}/jobs?limit=5`),
    ]);
    const tbody = document.querySelector('#schedules-table tbody');
    if (!tbody) return;
    // Build a map of running export jobs keyed by schedule name. The job's
    // `source` field is "{manual|scheduled}:{api|opensearch}:{schedule_name}".
    // Two-part values ("manual:api" / "scheduled:api" without a schedule
    // name) belong to /export-page runs and are not attached to any
    // schedule row.
    const runningBySchedule = {};
    let anyRunningExport = false;
    (jobsData.items || []).forEach(j => {
        if (j.status === 'running' && j.job_type === 'export' && j.progress_pct < 100) {
            anyRunningExport = true;
            const schedName = (j.source || '').split(':')[2];
            if (schedName) runningBySchedule[schedName] = j;
        }
    });

    tbody.innerHTML = data.items.map(s => {
        const c = s.config || {};
        let modeHtml = '-';
        let configHtml = '';
        if (s.job_type === 'export') {
            const mode = c.mode === 'opensearch' ? 'OpenSearch' : 'API';
            const serverName = c.server || window._defaultServerName || '';
            const serverLabel = serverName ? `<span class="host-label u076">${esc(serverName)}</span>` : '';
            modeHtml = `${serverLabel}<span class="host-label u072">${mode}</span>`;
            if (c.mode === 'opensearch') {
                if (c.keep_indices) {
                    configHtml = `${c.keep_indices} ${t('sched_indices_unit')}`;
                } else {
                    configHtml = `${c.days || '?'} ${t('export_days')} (${t('sched_all_indices')})`;
                }
            } else {
                configHtml = `${c.days || '?'} ${t('export_days')}`;
            }
        } else if (s.job_type === 'cleanup') {
            modeHtml = '-';
            configHtml = `${c.retention_days || '?'} ${t('export_days')}`;
        } else if (s.job_type === 'verify') {
            modeHtml = '-';
            configHtml = 'SHA256';
        } else if (s.job_type === 'report_cleanup') {
            modeHtml = '-';
            configHtml = `${c.days || 720} ${t('export_days')}`;
        }
        // Show running status only on the schedule that actually triggered the job.
        let runningHtml = '';
        const runningJob = runningBySchedule[s.name];
        if (s.job_type === 'export' && runningJob) {
            const pct = runningJob.progress_pct?.toFixed(0) || 0;
            const msgs = formatNumber(runningJob.messages_done || 0);
            const elapsed = formatElapsed(runningJob.started_at);
            const detail = runningJob.current_detail || '';
            const statsLine = runningJob.messages_done ? `${pct}% ${msgs} ${elapsed}` : `${pct}% ${elapsed}`;
            runningHtml = `<div class="u112">
                <div class="progress-bar u096">
                    <div class="progress-fill" data-style="width:${pct}%"></div>
                </div>
                <span class="u084">${esc(statsLine)}</span>
                ${detail ? `<div class="u073" title="${esc(detail)}">${esc(detail)}</div>` : ''}
            </div>`;
        }
        return `<tr>
            <td>${esc(s.name)}</td>
            <td>${esc(s.job_type)}</td>
            <td><code>${esc(s.cron_expr)}</code></td>
            <td>${modeHtml}</td>
            <td>${configHtml}</td>
            <td>${s.enabled ? '<span class="status-completed">' + t('yes') + '</span>' : '<span class="status-failed">' + t('no') + '</span>'}</td>
            <td>${formatDT(s.last_run_at)}${runningHtml}</td>
            <td>${s.enabled ? formatDT(s.next_run_at) : '<span class="u022">-</span>'}</td>
            <td><div class="u051">
                <button class="btn-sm btn-primary" data-act="editSchedule" data-arg="${esc(s.name)}">${icon('shield')} ${t('btn_edit')}</button>
                ${(s.job_type === 'export' || s.job_type === 'cleanup' || s.job_type === 'verify') && !anyRunningExport ? `<button class="btn-sm btn-success" data-act="runScheduleNow" data-arg="${esc(s.name)}" title="${t('btn_run_now')}">${icon('play')} ${t('btn_run_now')}</button>` : ''}
                <button class="btn-sm ${s.enabled ? 'btn-secondary' : 'btn-primary'}" data-act="toggleSchedule" data-args='["${esc(s.name)}",${!s.enabled}]'>${s.enabled ? icon('pause') + ' ' + t('btn_disable') : icon('play') + ' ' + t('btn_enable')}</button>
                ${s.name.startsWith('auto-') ? '' : `<button class="btn-sm btn-danger" data-act="deleteSchedule" data-arg="${esc(s.name)}">${icon('trash')}</button>`}
            </div></td>
        </tr>`;
    }).join('');
    applyI18n();

    // Load index sets for schedule form
    loadSchedIndexSets();

    // Set default mode from config
    try {
        const osStatus = await fetchJSON(`${API}/opensearch/status`);
        const modeSelect = document.getElementById('sched-mode');
        if (modeSelect) modeSelect.value = osStatus.export_mode || 'api';
    } catch (e) {}
}

function openSchedModal() {
    stopSchedPoll(); // Pause auto-refresh while editing
    _editingSchedule = null;
    document.getElementById('sched-name').readOnly = false;
    document.getElementById('sched-name').value = '';
    const titleEl = document.getElementById('sched-modal-title');
    if (titleEl) {
        titleEl.setAttribute('data-i18n', 'add_schedule');
        titleEl.setAttribute('data-icon', 'plus');
        titleEl.innerHTML = `${icon('plus')} ${t('add_schedule')}`;
    }
    document.getElementById('sched-modal').style.display = 'flex';
    loadSchedIndexSets();
    loadSchedStreams();
    loadSchedServers();
    onSchedModeChange();
    onSchedTypeChange();
    onSchedFreqChange();
    setTimeout(initCustomSelects, 100);
    applyI18n();
}

async function loadSchedServers() {
    const sel = document.getElementById('sched-server');
    if (!sel) return;
    try {
        const data = await fetchJSON(`${API}/servers`);
        sel.innerHTML = `<option value="">${t('sched_server_default')}</option>` +
            (data.items || []).map(s =>
                `<option value="${esc(s.name)}">${esc(s.name)} (${esc(s.url)})</option>`
            ).join('');
    } catch (e) {}
    initCustomSelects();
}

function closeSchedModal() {
    document.getElementById('sched-modal').style.display = 'none';
    startSchedPoll(); // Resume auto-refresh
    _editingSchedule = null;
    document.getElementById('sched-name').readOnly = false;
}

function onSchedModeChange() {
    const mode = document.getElementById('sched-mode')?.value;
    const hint = document.getElementById('sched-mode-hint');
    const streamGroup = document.getElementById('sched-stream-group');
    const daysGroup = document.getElementById('sched-days-group');
    const coverage = document.getElementById('sched-mode-coverage');
    if (hint) {
        let hintText = mode === 'api' ? t('export_mode_api_hint') : t('export_mode_os_hint');
        if (mode === 'opensearch' && window._hasDataNode) {
            hintText += '\n\n' + t('datanode_warning');
        }
        hint.textContent = hintText;
        hint.style.color = mode === 'opensearch' ? 'var(--warning)' : '';
    }
    if (streamGroup) streamGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (daysGroup) daysGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (coverage) {
        coverage.style.display = 'block';
        // Stamp the wanted mode so a slower in-flight loader for the OTHER mode
        // can't overwrite this panel after the user switches (async race).
        coverage.dataset.wantMode = mode;
        if (mode === 'opensearch') {
            loadOsCoverage(coverage);
        } else {
            loadApiCoverage(coverage);
        }
    }
}

async function loadSchedStreams() {
    const div = document.getElementById('sched-stream-list');
    if (!div) return;
    div.innerHTML = `<span class="u022">${t('loading')}...</span>`;
    try {
        const data = await fetchJSON(`${API}/streams`);
        if (data.items) {
            div.innerHTML = data.items.map(s =>
                `<label><input type="checkbox" class="sched-stream-check" value="${s.id}"> ${esc(s.title || s.id)}</label>`
            ).join('');
        }
    } catch (e) {
        div.innerHTML = `<span class="u018">${t('load_failed')}</span>`;
    }
}

function onSchedTypeChange() {
    const type = document.getElementById('sched-type')?.value;
    const exportOpts = document.getElementById('sched-export-options');
    const cleanupOpts = document.getElementById('sched-cleanup-options');
    const verifyOpts = document.getElementById('sched-verify-options');
    const reportCleanupOpts = document.getElementById('sched-report-cleanup-options');
    if (exportOpts) exportOpts.style.display = type === 'export' ? 'block' : 'none';
    if (cleanupOpts) cleanupOpts.style.display = type === 'cleanup' ? 'block' : 'none';
    if (verifyOpts) verifyOpts.style.display = type === 'verify' ? 'block' : 'none';
    if (reportCleanupOpts) reportCleanupOpts.style.display = type === 'report_cleanup' ? 'block' : 'none';
}

function onSchedFreqChange() {
    const freq = document.getElementById('sched-freq')?.value;
    const customGroup = document.getElementById('sched-custom-group');
    if (customGroup) customGroup.style.display = freq === 'custom' ? 'block' : 'none';
}

async function addSchedule() {
    const name = document.getElementById('sched-name')?.value;
    const type = document.getElementById('sched-type')?.value;
    const freqSel = document.getElementById('sched-freq')?.value;
    const customCron = document.getElementById('sched-cron')?.value;
    const cron = freqSel === 'custom' ? customCron : freqSel;

    if (!name) { showAlert(t('alert_name_cron_required')); return; }
    if (!cron) { showAlert(t('alert_name_cron_required')); return; }

    const btn = event.target.closest('button');
    await withButton(btn, async () => {
        const body = { name, job_type: type, cron_expr: cron };
        if (type === 'export') {
            body.server = document.getElementById('sched-server')?.value || '';
            body.mode = document.getElementById('sched-mode')?.value || 'api';
            body.days = parseInt(document.getElementById('sched-days')?.value) || 1095;
            body.index_set = document.getElementById('sched-indexset')?.value || '';
            body.streams = Array.from(document.querySelectorAll('.sched-stream-check:checked')).map(c => c.value);
            // OpenSearch: save keep_indices from the OS coverage widget
            if (body.mode === 'opensearch') {
                const keepN = document.getElementById('os-keep-n')?.value;
                if (keepN) body.keep_indices = parseInt(keepN);
            }
        } else if (type === 'cleanup') {
            body.retention_days = parseInt(document.getElementById('sched-retention-days')?.value) || 1095;
        } else if (type === 'report_cleanup') {
            body.days = parseInt(document.getElementById('sched-report-days')?.value) || 720;
        }
        await fetchJSON(`${API}/schedules`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        closeSchedModal();
        loadSchedules();
    });
}

let _editingSchedule = null;

async function editSchedule(name) {
    stopSchedPoll(); // Pause auto-refresh while editing
    // Find schedule data
    const data = await fetchJSON(`${API}/schedules`);
    const sched = data.items.find(s => s.name === name);
    if (!sched) return;

    _editingSchedule = name;
    const c = sched.config || {};

    // Show the modal with edit title
    document.getElementById('sched-modal').style.display = 'flex';
    const titleEl = document.getElementById('sched-modal-title');
    if (titleEl) {
        titleEl.removeAttribute('data-i18n');
        titleEl.removeAttribute('data-icon');
        titleEl.innerHTML = `${icon('shield')} ${t('btn_edit')}: ${esc(name)}`;
    }

    // Populate fields
    document.getElementById('sched-name').value = sched.name;
    document.getElementById('sched-name').readOnly = true; // Can't rename
    document.getElementById('sched-type').value = sched.job_type;
    onSchedTypeChange();

    // Set frequency
    const freqSel = document.getElementById('sched-freq');
    const predefined = Array.from(freqSel.options).find(o => o.value === sched.cron_expr);
    if (predefined) {
        freqSel.value = sched.cron_expr;
    } else {
        freqSel.value = 'custom';
        document.getElementById('sched-cron').value = sched.cron_expr;
    }
    onSchedFreqChange();

    // Set type-specific options
    if (sched.job_type === 'cleanup') {
        const retDays = document.getElementById('sched-retention-days');
        if (retDays) retDays.value = c.retention_days || 1095;
    }
    if (sched.job_type === 'report_cleanup') {
        const rd = document.getElementById('sched-report-days');
        if (rd) rd.value = c.days || 720;
    }
    if (sched.job_type === 'export') {
        await loadSchedServers();
        const serverSel = document.getElementById('sched-server');
        if (serverSel && c.server) serverSel.value = c.server;
        const modeSel = document.getElementById('sched-mode');
        if (modeSel) modeSel.value = c.mode || 'api';
        onSchedModeChange();
        const daysSel = document.getElementById('sched-days');
        if (daysSel) daysSel.value = c.days || 1095;
        await loadSchedIndexSets();
        const isetSel = document.getElementById('sched-indexset');
        if (isetSel && c.index_set) isetSel.value = c.index_set;
        // Load and check streams
        await loadSchedStreams();
        const savedStreams = c.streams || [];
        document.querySelectorAll('.sched-stream-check').forEach(cb => {
            cb.checked = savedStreams.includes(cb.value);
        });
        // Restore keep_indices after coverage widget has rendered
        if (c.keep_indices) {
            setTimeout(() => {
                const keepN = document.getElementById('os-keep-n');
                if (keepN) keepN.value = c.keep_indices;
            }, 500);
        }
    }

    setTimeout(initCustomSelects, 100);
    applyI18n();
}

function cancelEditSchedule() {
    _editingSchedule = null;
    document.getElementById('sched-name').readOnly = false;
    closeSchedModal();
}

async function toggleSchedule(name, enabled) {
    await withButton(event.target.closest('button'), async () => {
        await fetchJSON(`${API}/schedules/${name}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled}),
        });
        loadSchedules();
    });
}

async function runScheduleNow(name) {
    await withButton(event.target.closest('button'), async () => {
        const result = await fetchJSON(`${API}/schedules/${name}/run`, {method: 'POST'});
        if (result.error) {
            showAlert(result.error);
        } else if (result.job_id) {
            showAlert(`${t('btn_run_now')}: ${result.job_id.substring(0, 8)}`);
            setTimeout(() => loadSchedules(), 1000);
        } else if (result.status === 'completed') {
            // Cleanup/Verify completed synchronously
            const info = result.files_deleted !== undefined
                ? `${t('btn_run_now')}: ${result.files_deleted} files deleted`
                : `${t('btn_run_now')}: ${result.total_checked} checked, ${result.corrupted || 0} corrupted`;
            showAlert(info);
            loadSchedules();
        }
    });
}

// Auto-refresh schedule page every 10s while on it
let _schedPollInterval = null;
function startSchedPoll() {
    stopSchedPoll();
    _schedPollInterval = setInterval(() => {
        if (window.location.pathname === '/schedules') loadSchedules();
        else stopSchedPoll();
    }, 10000);
}
function stopSchedPoll() {
    if (_schedPollInterval) { clearInterval(_schedPollInterval); _schedPollInterval = null; }
}

function deleteSchedule(name) {
    showConfirm(
        `${icon('trash')} ${t('confirm_delete_sched')}`,
        `"${name}"`,
        async () => {
            await fetch(`${API}/schedules/${name}`, {method: 'DELETE'});
            loadSchedules();
        }
    );
}

// ---- SSE Progress Watcher ----
function watchJob(jobId, type, onComplete) {
    const bar = document.getElementById(`${type}-progress-bar`);
    const text = document.getElementById(`${type}-progress-text`);

    // Reset any leftover state from a previous run (e.g. failed attempt)
    if (bar) bar.style.width = '0%';
    if (text) text.textContent = '';

    function showResult(job) {
        const msgs = job.messages_done || 0;
        if (bar) bar.style.width = '100%';
        if (text) {
            if (job.status === 'failed' || job.phase === 'error') {
                text.innerHTML = `<span class="status-failed">${t('progress_error')}${esc(job.error_message || job.error || '')}</span>`;
            } else if (msgs === 0) {
                text.innerHTML = `<span class="u030">${t('export_no_data')}</span>`;
            } else {
                let html = `<span class="status-completed">${t('progress_completed')} (${formatNumber(msgs)} ${t('unit_records')})</span>`;
                const cov = coverageChip(job);
                if (cov) html += ` <span class="cov-chip-wrap">${cov}</span>`;
                // Surface bulk-mode "where to find" notice (and any other
                // post-completion info written into the job's error_message)
                if (job.error_message) {
                    const isViolation = job.error_message.indexOf('Compliance violation') !== -1;
                    const colour = isViolation ? 'var(--warning)' : 'var(--accent)';
                    html += `<div data-style="margin-top:8px;padding:8px 10px;background:rgba(108,99,255,0.08);border-left:3px solid ${colour};border-radius:4px;font-size:0.85em">${esc(job.error_message)}</div>`;
                }
                text.innerHTML = html;
            }
        }
        if (onComplete) onComplete(job);
    }

    function cleanup() {
        clearInterval(pollInterval);
        try { es.close(); } catch (_) {}
    }

    // Try SSE first
    let sseOk = false;
    const es = new EventSource(`${API}/jobs/${jobId}/stream`);
    es.addEventListener('progress', (e) => {
        sseOk = true;
        const data = JSON.parse(e.data);
        if (bar) bar.style.width = (data.pct || 0) + '%';
        if (text) {
            // Show detail string for scanning/dedup/skipping phases (no records yet)
            if (data.detail && (!data.messages_done || data.phase === 'scanning' || data.phase === 'dedup' || data.phase === 'skipping')) {
                text.textContent = data.detail;
            } else {
                const msgs = formatNumber(data.messages_done || 0);
                const total = data.messages_total ? formatNumber(data.messages_total) : '?';
                const idx = data.index ? ` ${data.index}` : '';
                text.textContent = `${msgs}/${total}${idx} — ${(data.pct || 0).toFixed(1)}%`;
            }
        }
    });
    es.addEventListener('done', async (e) => {
        sseOk = true;
        cleanup();
        // SSE 'done' event payload only has phase/pct/messages, NOT the
        // job's error_message (where post-completion notes live, e.g.
        // bulk-mode "find your data in stream X"). Fetch the full job
        // record before showing the result so the notice surfaces.
        try {
            const resp = await fetch(`${API}/jobs/${jobId}`);
            if (resp.ok) {
                const job = await resp.json();
                // Merge SSE event data with full job record
                const evt = JSON.parse(e.data);
                showResult({...job, ...evt, error_message: job.error_message});
                return;
            }
        } catch (_) {}
        // Fallback: just show what SSE gave us
        showResult(JSON.parse(e.data));
    });
    es.onerror = () => { es.close(); };

    // Clean up EventSource on page navigation/unload
    const _cleanupOnUnload = () => cleanup();
    window.addEventListener('beforeunload', _cleanupOnUnload, {once: true});

    // Polling fallback — check every 2s until job finishes
    let pollCount = 0;
    const pollInterval = setInterval(async () => {
        pollCount++;
        try {
            const resp = await fetch(`${API}/jobs/${jobId}`);
            if (resp.status === 401) {
                cleanup();
                window.removeEventListener('beforeunload', _cleanupOnUnload);
                if (text) text.innerHTML = `<span class="status-failed">${t('progress_error')}Session expired. Please refresh and login.</span>`;
                if (onComplete) onComplete({});
                return;
            }
            const job = await resp.json();
            if (!job || !job.status) return;

            if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
                cleanup();
                window.removeEventListener('beforeunload', _cleanupOnUnload);
                showResult(job);
            } else if (!sseOk) {
                if (bar) bar.style.width = (job.progress_pct || 0) + '%';
                if (text) {
                    if (job.current_detail && !job.messages_done) {
                        text.textContent = job.current_detail;
                    } else {
                        text.textContent = `${formatNumber(job.messages_done || 0)}/${job.messages_total ? formatNumber(job.messages_total) : '?'} — ${(job.progress_pct || 0).toFixed(0)}%`;
                    }
                }
            }
        } catch (e) {
            // Network error — stop after 30 attempts (1 min)
            if (pollCount > 30) {
                cleanup();
                window.removeEventListener('beforeunload', _cleanupOnUnload);
                if (text) text.innerHTML = `<span class="status-failed">${t('progress_error')}Connection lost</span>`;
                if (onComplete) onComplete({});
            }
        }
    }, 2000);
}

// ---- System Logs ----
function _colorizeLogLine(raw) {
    const e = esc(raw);
    // Determine line color by log level
    if (/\bERROR\b/i.test(raw)) return `<span class="u013">${e}</span>`;
    if (/\bWARN/i.test(raw)) return `<span class="u015">${e}</span>`;
    if (/\berror\b/.test(raw)) return `<span class="u012">${e}</span>`;
    if (/\[info\s*\]/.test(raw)) return `<span class="u008">${e}</span>`;
    if (/\bINFO\b/.test(raw)) return `<span class="u011">${e}</span>`;
    if (/\bDEBUG\b/i.test(raw)) return `<span class="u004">${e}</span>`;
    if (/Started|Completed|startup complete/i.test(raw)) return `<span class="u008">${e}</span>`;
    if (/systemd\[/.test(raw)) return `<span class="u005">${e}</span>`;
    return `<span class="u009">${e}</span>`;
}

async function loadRealtimeLog() {
    const lines = document.getElementById('log-lines')?.value || 100;
    const el = document.getElementById('log-output');
    el.textContent = t('loading') + '...';
    try {
        const data = await fetchJSON(`${API}/logs/realtime?lines=${lines}`);
        const raw = data.lines || t('log_no_data');
        el.innerHTML = raw.split('\n').map(_colorizeLogLine).join('\n');
        el.scrollTop = el.scrollHeight;
    } catch (e) {
        el.textContent = t('load_failed');
    }
}

async function loadAuditLog() {
    const tbody = document.querySelector('#audit-table tbody');
    if (!tbody) return;
    const data = await fetchJSON(`${API}/logs/audit?limit=100`);
    if (!data.items) return;
    tbody.innerHTML = data.items.map(a => `<tr>
        <td>${formatDT(a.timestamp)}</td>
        <td>${esc(a.username || '-')}</td>
        <td><strong>${esc(a.action || '')}</strong></td>
        <td class="u082" title="${esc(a.detail || '')}">${esc(a.detail || '')}</td>
        <td>${esc(a.ip_address || '')}</td>
    </tr>`).join('');
}

async function loadHistory() {
    const tbody = document.querySelector('#history-table tbody');
    if (!tbody) return;
    const data = await fetchJSON(`${API}/logs/history?limit=100`);
    if (!data.items) return;
    tbody.innerHTML = data.items.map(j => `<tr>
        <td title="${j.id}">${j.id.substring(0, 8)}</td>
        <td>${j.job_type}</td>
        <td>${statusBadge(j.status)}</td>
        <td class="u147">${formatRecords(j.messages_done, j.messages_total, j.job_type)}</td>
        <td>${formatDT(j.started_at)}</td>
        <td>${formatDT(j.completed_at)}</td>
        <td data-style="color:${j.status === 'failed' || (j.error_message || '').indexOf('Compliance violation') !== -1 || (j.error_message || '').indexOf('Interrupted') !== -1 ? 'var(--danger)' : 'var(--text-muted)'};font-size:0.85em;max-width:220px;overflow:hidden;text-overflow:ellipsis" title="${esc(j.error_message || '')}">${coverageChip(j)}${esc(j.error_message || '')}</td>
    </tr>`).join('');
}

// ---- Notification Settings ----
async function loadNotifySettings() {
    let data;
    try { data = await fetchJSON(`${API}/notify/config`); } catch(e) { return; }
    if (!data) return;

    // Events
    const eventsEl = document.getElementById('notify-events-form');
    if (eventsEl) {
        const events = [
            {key: 'on_export_complete', label: t('evt_export_complete'), ic: 'upload'},
            {key: 'on_import_complete', label: t('evt_import_complete'), ic: 'download'},
            {key: 'on_cleanup_complete', label: t('evt_cleanup_complete'), ic: 'trash'},
            {key: 'on_error', label: t('evt_error'), ic: 'warning'},
            {key: 'on_verify_failed', label: t('evt_verify_failed'), ic: 'shield'},
            {key: 'on_sensitive_operation', label: t('evt_sensitive_operation'), ic: 'lock'},
            {key: 'on_audit_alert', label: t('evt_audit_alert'), ic: 'warning'},
        ];
        eventsEl.innerHTML = events.map(e =>
            `<label class="u042">
                <input type="checkbox" class="notify-event" data-key="${e.key}" ${data[e.key] ? 'checked' : ''}> ${icon(e.ic)} ${e.label}
            </label>`
        ).join('');
    }

    // Notification language
    const langEl = document.getElementById('notify-lang-form');
    if (langEl) {
        langEl.innerHTML = `<div class="form-group u120">
            <label data-i18n="notify_language">${t('notify_language')}</label>
            <select id="nf-language">
                <option value="en" ${data.language === 'en' ? 'selected' : ''}>English</option>
                <option value="zh-TW" ${data.language === 'zh-TW' ? 'selected' : ''}>繁體中文</option>
            </select>
        </div>`;
        initCustomSelects();
    }

    // Channels
    const chEl = document.getElementById('notify-channels-form');
    if (chEl) {
        const chLogos = {
            tg: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#229ED9"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>',
            discord: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.8 19.8 0 00-4.885-1.515.07.07 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.74 19.74 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.08.08 0 00.031.057 19.9 19.9 0 005.993 3.03.08.08 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.1 13.1 0 01-1.872-.892.077.077 0 01-.008-.128 10 10 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.3 12.3 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.84 19.84 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.06.06 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>',
            slack: '<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#E01E5A" d="M5.042 15.165a2.528 2.528 0 01-2.52 2.523A2.528 2.528 0 010 15.165a2.527 2.527 0 012.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 012.521-2.52 2.527 2.527 0 012.521 2.52v6.313A2.528 2.528 0 018.834 24a2.528 2.528 0 01-2.521-2.522v-6.313z"/><path fill="#36C5F0" d="M8.834 5.042a2.528 2.528 0 01-2.521-2.52A2.528 2.528 0 018.834 0a2.528 2.528 0 012.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 012.521 2.521 2.528 2.528 0 01-2.521 2.521H2.522A2.528 2.528 0 010 8.834a2.528 2.528 0 012.522-2.521h6.312z"/><path fill="#2EB67D" d="M18.956 8.834a2.528 2.528 0 012.522-2.521A2.528 2.528 0 0124 8.834a2.528 2.528 0 01-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 01-2.523 2.521 2.527 2.527 0 01-2.52-2.521V2.522A2.527 2.527 0 0115.163 0a2.528 2.528 0 012.523 2.522v6.312z"/><path fill="#ECB22E" d="M15.163 18.956a2.528 2.528 0 012.523 2.522A2.528 2.528 0 0115.163 24a2.527 2.527 0 01-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 01-2.52-2.523 2.527 2.527 0 012.52-2.52h6.315A2.528 2.528 0 0124 15.163a2.528 2.528 0 01-2.522 2.523h-6.315z"/></svg>',
            teams: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#6264A7"><path d="M20.625 8.5h-3.75c-.69 0-1.25.56-1.25 1.25v5c0 .69.56 1.25 1.25 1.25h2.5v2.5c0 .414.336.75.75.75s.75-.336.75-.75V9.75c0-.69-.56-1.25-1.25-1.25zM19.5 7a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM14.5 6.5h-9C4.672 6.5 4 7.172 4 8v8c0 .828.672 1.5 1.5 1.5H9v3.25c0 .414.336.75.75.75s.75-.336.75-.75V17.5h4c.828 0 1.5-.672 1.5-1.5V8c0-.828-.672-1.5-1.5-1.5zM10 5a2 2 0 100-4 2 2 0 000 4z"/></svg>',
            nc: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#0082C9"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-1.5 14.5L7 13l1.414-1.414L10.5 13.672l5.086-5.086L17 10l-6.5 6.5z"/></svg>',
            email: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 9l5 3.5L17 9"/><path d="M2 17V7c0-1.1.9-2 2-2h16c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2z"/></svg>',
        };
        const _chk = (id, en) => `<label class="u041"><input type="checkbox" id="${id}" ${en ? 'checked' : ''} data-act-change="toggleChannelFields" data-act-self> ${t('notify_enabled')}</label>`;
        const _vis = (en) => en ? '' : 'data-collapsed="1"';
        // Secret field: password input + eye toggle button
        const _secret = (id, val, extra = '') => `<div class="secret-field"><input type="password" id="${id}" value="${esc(val)}" autocomplete="new-password" ${extra}><button type="button" class="secret-toggle" data-act="toggleSecret" data-act-self tabindex="-1" data-i18n-title="show_hide" title="Show/Hide">${icon('eye_closed')}</button></div>`;
        chEl.innerHTML = `
        <div class="channel-card">
            <h4>${chLogos.tg} Telegram</h4>
            ${_chk('nf-tg-enabled', data.telegram.enabled)}
            <div class="channel-fields" ${_vis(data.telegram.enabled)}>
                <div class="form-group"><label>${t('notify_bot_token')}</label>${_secret('nf-tg-token', data.telegram.bot_token || '')}</div>
                <div class="form-group"><label>${t('notify_chat_id')}</label>${_secret('nf-tg-chatid', data.telegram.chat_id || '')}</div>
            </div>
        </div>
        <div class="channel-card">
            <h4>${chLogos.discord} Discord</h4>
            ${_chk('nf-discord-enabled', data.discord.enabled)}
            <div class="channel-fields" ${_vis(data.discord.enabled)}>
                <div class="form-group"><label>${t('notify_webhook_url')}</label>${_secret('nf-discord-url', data.discord.webhook_url || '')}</div>
            </div>
        </div>
        <div class="channel-card">
            <h4>${chLogos.slack} Slack</h4>
            ${_chk('nf-slack-enabled', data.slack.enabled)}
            <div class="channel-fields" ${_vis(data.slack.enabled)}>
                <div class="form-group"><label>${t('notify_webhook_url')}</label>${_secret('nf-slack-url', data.slack.webhook_url || '')}</div>
            </div>
        </div>
        <div class="channel-card">
            <h4>${chLogos.teams} Microsoft Teams</h4>
            ${_chk('nf-teams-enabled', data.teams.enabled)}
            <div class="channel-fields" ${_vis(data.teams.enabled)}>
                <div class="form-group"><label>${t('notify_webhook_url')}</label>${_secret('nf-teams-url', data.teams.webhook_url || '')}</div>
            </div>
        </div>
        <div class="channel-card">
            <h4>${chLogos.nc} Nextcloud Talk</h4>
            ${_chk('nf-nc-enabled', data.nextcloud_talk.enabled)}
            <div class="channel-fields" ${_vis(data.nextcloud_talk.enabled)}>
                <div class="form-group"><label>${t('notify_nc_server')}</label>${_secret('nf-nc-server', data.nextcloud_talk.server_url || '')}</div>
                <div class="form-group"><label>${t('notify_nc_token')}</label>${_secret('nf-nc-token', data.nextcloud_talk.token || '')}</div>
                <div class="form-group"><label>${t('notify_nc_user')}</label>${_secret('nf-nc-user', data.nextcloud_talk.username || '')}</div>
                <div class="form-group"><label>${t('notify_nc_pass')}</label>${_secret('nf-nc-pass', data.nextcloud_talk.password || '')}</div>
            </div>
        </div>
        <div class="channel-card">
            <h4>${chLogos.email} Email (SMTP)</h4>
            ${_chk('nf-email-enabled', data.email.enabled)}
            <div class="channel-fields" ${_vis(data.email.enabled)}>
                <div class="form-group"><label>${t('notify_smtp_host')}</label><input type="text" id="nf-email-host" value="${esc(data.email.smtp_host || '')}"></div>
                <div class="form-group"><label>${t('notify_smtp_port')}</label><input type="number" id="nf-email-port" value="${data.email.smtp_port || 587}"></div>
                <div class="form-group"><label class="u033"><input type="checkbox" id="nf-email-tls" ${data.email.smtp_tls ? 'checked' : ''}> ${t('notify_smtp_tls')}</label></div>
                <div class="form-group"><label>${t('notify_smtp_user')}</label><input type="text" id="nf-email-user" value="${esc(data.email.smtp_user || '')}" autocomplete="off"></div>
                <div class="form-group"><label>${t('notify_smtp_password')}</label>${_secret('nf-email-pass', data.email.smtp_password || '')}</div>
                <div class="form-group"><label>${t('notify_from')}</label><input type="text" id="nf-email-from" value="${esc(data.email.from_addr || '')}"></div>
                <div class="form-group"><label>${t('notify_to')}</label><textarea class="u153" id="nf-email-to" rows="3">${esc((data.email.to_addrs || []).join('\n'))}</textarea></div>
                <div class="form-group"><label>${t('notify_subject_prefix')}</label><input type="text" id="nf-email-prefix" value="${esc(data.email.subject_prefix || '[jt-glogarch]')}"></div>
            </div>
        </div>`;
    }
}

async function saveNotifySettings(evt) {
    const body = {};
    // Language
    body.language = document.getElementById('nf-language')?.value || 'zh-TW';
    // Events
    document.querySelectorAll('.notify-event').forEach(cb => {
        body[cb.getAttribute('data-key')] = cb.checked;
    });
    // Channels
    body.telegram = {enabled: !!document.getElementById('nf-tg-enabled')?.checked, bot_token: document.getElementById('nf-tg-token')?.value || '', chat_id: document.getElementById('nf-tg-chatid')?.value || ''};
    body.discord = {enabled: !!document.getElementById('nf-discord-enabled')?.checked, webhook_url: document.getElementById('nf-discord-url')?.value || ''};
    body.slack = {enabled: !!document.getElementById('nf-slack-enabled')?.checked, webhook_url: document.getElementById('nf-slack-url')?.value || ''};
    body.teams = {enabled: !!document.getElementById('nf-teams-enabled')?.checked, webhook_url: document.getElementById('nf-teams-url')?.value || ''};
    body.nextcloud_talk = {enabled: !!document.getElementById('nf-nc-enabled')?.checked, server_url: document.getElementById('nf-nc-server')?.value || '', token: document.getElementById('nf-nc-token')?.value || '', username: document.getElementById('nf-nc-user')?.value || '', password: document.getElementById('nf-nc-pass')?.value || ''};
    const toAddrs = (document.getElementById('nf-email-to')?.value || '').split('\n').map(s => s.trim()).filter(s => s);
    body.email = {enabled: !!document.getElementById('nf-email-enabled')?.checked, smtp_host: document.getElementById('nf-email-host')?.value || '', smtp_port: parseInt(document.getElementById('nf-email-port')?.value) || 587, smtp_tls: !!document.getElementById('nf-email-tls')?.checked, smtp_user: document.getElementById('nf-email-user')?.value || '', smtp_password: document.getElementById('nf-email-pass')?.value || '', from_addr: document.getElementById('nf-email-from')?.value || '', to_addrs: toAddrs, subject_prefix: document.getElementById('nf-email-prefix')?.value || '[jt-glogarch]'};

    const el = document.getElementById('notify-settings-result');
    const data = await fetchJSON(`${API}/notify/config`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    if (data.status === 'saved') {
        el.innerHTML = `<span class="status-completed">${t('notify_save_success')}</span>`;
    } else {
        el.innerHTML = `<span class="status-failed">${data.error || 'Failed'}</span>`;
    }
}

function toggleChannelFields(checkbox) {
    const fields = checkbox.closest('.channel-card')?.querySelector('.channel-fields');
    if (fields) fields.style.display = checkbox.checked ? '' : 'none';
}

function toggleSecret(btn) {
    // Delegation passes the clicked toggle button; the input is its sibling.
    const el = btn.parentElement.querySelector('input');
    if (!el) return;
    const showing = el.type === 'text';
    el.type = showing ? 'password' : 'text';
    btn.innerHTML = showing ? icon('eye_closed') : icon('eye');
}

async function testNotifyFromSettings() {
    const el = document.getElementById('notify-settings-result');
    el.innerHTML = `<span class="u022">${t('loading')}...</span>`;
    const data = await fetchJSON(`${API}/notify/test`, {method: 'POST'});
    if (data.results && data.results.length > 0) {
        el.innerHTML = data.results.map(r => `${esc(r.channel)}: ${r.success ? `<span class="status-completed">${t('result_ok')}</span>` : `<span class="status-failed">${esc(r.error || t('result_failed'))}</span>`}`).join('<br>');
    } else {
        el.innerHTML = `<span class="u030">${t('notify_no_channels')}</span>`;
    }
}

// ---- Custom Dropdown ----
function initCustomSelects() {
    document.querySelectorAll('select:not(.no-custom)').forEach(sel => {
        // Remove old wrapper if exists (for reinit)
        const oldWrapper = sel.closest('.custom-select');
        if (oldWrapper) {
            oldWrapper.parentNode.insertBefore(sel, oldWrapper);
            oldWrapper.remove();
            sel.classList.remove('custom-done');
        }

        sel.classList.add('custom-done');
        sel.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select';

        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        const selectedOpt = sel.options[sel.selectedIndex];
        trigger.innerHTML = `<span>${selectedOpt ? selectedOpt.text : ''}</span><span class="arrow">&#9662;</span>`;

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'custom-select-options';
        Array.from(sel.options).forEach((opt, i) => {
            const d = document.createElement('div');
            d.className = 'custom-select-option' + (i === sel.selectedIndex ? ' selected' : '');
            d.textContent = opt.text;
            d.setAttribute('data-value', opt.value);
            d.addEventListener('click', () => {
                sel.value = opt.value;
                // MUST bubble: the app's data-act-change handlers are delegated
                // on `document`, so a non-bubbling change event never reaches
                // them (that's why some selects needed `class="no-custom"` to
                // work). Bubbling makes custom selects behave like native ones.
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                trigger.querySelector('span').textContent = opt.text;
                optionsDiv.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
                d.classList.add('selected');
                wrapper.classList.remove('open');
            });
            optionsDiv.appendChild(d);
        });

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.custom-select.open').forEach(cs => { if (cs !== wrapper) cs.classList.remove('open'); });
            // Auto-detect: drop up or down based on viewport position
            const rect = trigger.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            if (spaceBelow > 220) {
                optionsDiv.classList.add('drop-down');
            } else {
                optionsDiv.classList.remove('drop-down');
            }
            wrapper.classList.toggle('open');
        });

        sel.parentNode.insertBefore(wrapper, sel);
        wrapper.appendChild(trigger);
        wrapper.appendChild(optionsDiv);
        wrapper.appendChild(sel);
    });
}

// Close custom selects on outside click
document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select.open').forEach(cs => cs.classList.remove('open'));
});

// ---- Confirm Modal ----
let _confirmCallback = null;

function showConfirm(title, message, onConfirm) {
    _confirmCallback = onConfirm;
    let modal = document.getElementById('global-confirm-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'global-confirm-modal';
        modal.className = 'confirm-modal-overlay';
        // Do NOT close on backdrop click — only close via buttons
        modal.innerHTML = `<div class="confirm-modal-card">
            <h3 id="confirm-title"></h3>
            <p id="confirm-message"></p>
            <div class="btn-row" id="confirm-buttons"></div>
        </div>`;
        document.body.appendChild(modal);
    }
    document.getElementById('confirm-title').innerHTML = title;
    document.getElementById('confirm-message').innerHTML = message;
    const btnRow = document.getElementById('confirm-buttons');
    if (onConfirm) {
        btnRow.innerHTML = `<button class="btn-danger" data-act="doConfirm">${icon('shield')} ${t('btn_confirm')}</button>
            <button class="btn-secondary" data-act="closeConfirm">${t('btn_cancel')}</button>`;
    } else {
        btnRow.innerHTML = `<button class="btn-primary" data-act="closeConfirm">${t('btn_ok')}</button>`;
    }
    modal.style.display = 'flex';
}

function closeConfirm() {
    const modal = document.getElementById('global-confirm-modal');
    if (modal) modal.style.display = 'none';
    _confirmCallback = null;
}

function doConfirm() {
    if (_confirmCallback) _confirmCallback();
    closeConfirm();
}

// ---- Tooltip Init ----
function initTooltips() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.classList.contains('btn-sm')) {
            const key = el.getAttribute('data-i18n');
            if (!el.hasAttribute('data-tooltip')) {
                el.setAttribute('data-tooltip', t(key));
            }
        }
    });
}

// ---- Table Sort ----
function initTableSort() {
    document.querySelectorAll('table thead th').forEach(th => {
        if (th.querySelector('input')) return; // Skip checkbox columns
        if (th._sortBound) return; // Already bound
        th._sortBound = true;
        th.addEventListener('click', () => sortTable(th));
    });
}

function sortTable(th) {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    // Server-side sort for archives table
    if (table.id === 'archives-table') {
        const colMap = {
            'col-server': 'server_name', 'col-from': 'time_from', 'col-to': 'time_to',
            'col-records': 'message_count', 'col-compressed': 'file_size_bytes',
        };
        const cls = Array.from(th.classList).find(c => colMap[c]);
        if (cls) {
            const isAsc = th.classList.contains('sort-asc');
            table.querySelectorAll('th').forEach(h => { h.classList.remove('sort-asc','sort-desc'); const a = h.querySelector('.sort-icon'); if(a) a.remove(); });
            archiveSort = colMap[cls];
            archiveOrder = isAsc ? 'desc' : 'asc';
            th.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
            const span = document.createElement('span'); span.className = 'sort-icon'; span.textContent = isAsc ? ' ▼' : ' ▲'; th.appendChild(span);
            loadArchives(1);
            return;
        }
    }

    const idx = Array.from(th.parentNode.children).indexOf(th);
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0) return;

    // Toggle direction
    const isAsc = th.classList.contains('sort-asc');
    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
        const arrow = h.querySelector('.sort-icon');
        if (arrow) arrow.remove();
    });
    th.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
    const arrowHtml = isAsc ? ' ▼' : ' ▲';
    const span = document.createElement('span');
    span.className = 'sort-icon';
    span.textContent = arrowHtml;
    th.appendChild(span);
    const dir = isAsc ? -1 : 1;

    rows.sort((a, b) => {
        const cellA = a.children[idx]?.textContent?.trim() || '';
        const cellB = b.children[idx]?.textContent?.trim() || '';
        // Try date first (yyyy/mm/dd or yyyy-mm-dd)
        if (cellA.match(/^\d{4}[\/-]/) && cellB.match(/^\d{4}[\/-]/)) return cellA.localeCompare(cellB) * dir;
        // Try numeric (handle commas and units like "31.06 MB")
        const numA = parseFloat(cellA.replace(/,/g, '').replace(/[^\d.-]/g, ''));
        const numB = parseFloat(cellB.replace(/,/g, '').replace(/[^\d.-]/g, ''));
        if (!isNaN(numA) && !isNaN(numB)) return (numA - numB) * dir;
        // String
        return cellA.localeCompare(cellB) * dir;
    });

    rows.forEach(r => tbody.appendChild(r));
}

// ---- Sidebar Job Status ----
async function checkRunningJobs() {
    try {
        const data = await fetchJSON(`${API}/jobs?limit=10`);
        // Filter truly running jobs (not ones that are done in _job_progress but DB not yet updated)
        const running = (data.items || []).filter(j => j.status === 'running' && j.progress_pct < 100);
        const el = document.getElementById('sidebar-job-status');
        const text = document.getElementById('sidebar-job-text');
        if (!el || !text) return;
        if (running.length === 0) {
            el.classList.add('hidden');
            el.style.display = 'none';
            return;
        }
        el.classList.remove('hidden');
        el.style.display = 'block';
        el.style.cursor = 'pointer';
        el.title = t('reopen_running_job') || 'Click to reopen';
        // Clicking reopens an active import modal on this page, else goes to /jobs.
        el.onclick = () => {
            const imp = running.find(j => j.job_type === 'import' && _activeImportJobId === j.id);
            if (imp && document.getElementById('import-modal')) reopenActiveImportModal();
            else window.location.href = '/jobs';
        };
        // Render EVERY running job (export + report can run at once). A report job
        // has no incremental progress (0% until it finishes) → show an
        // indeterminate "running" bar rather than a stuck 0%.
        const isIndet = (j) => j.job_type === 'report' || (j.progress_pct == null && !j.messages_total);
        text.innerHTML = running.map(j => {
            const indet = isIndet(j);
            const pct = j.progress_pct != null ? Number(j.progress_pct).toFixed(0) : 0;
            const elapsed = formatElapsed(j.started_at);
            const msgs = j.messages_done ? formatNumber(j.messages_done) : '0';
            const total = j.messages_total ? formatNumber(j.messages_total) : '?';
            const detail = j.current_detail || j.phase || '';
            const statusLine = indet ? (t('job_running') || 'Running…')
                                     : (detail && !j.messages_done ? esc(detail) : `${msgs} / ${total}`);
            const head = indet ? esc(j.job_type) : `${esc(j.job_type)} <strong>${pct}%</strong>`;
            const bar = indet ? `<div class="progress-fill indet"></div>`
                              : `<div class="progress-fill" data-style="width:${pct}%"></div>`;
            // Wrap each job so consecutive jobs get a separator (see .sb-job CSS).
            return `<div class="sb-job">
                <div class="job-detail-full u044">
                    <span>${head} · ${elapsed}</span>
                    <div class="progress-bar u099">${bar}</div>
                    <span class="u091">${statusLine}</span>
                </div>
                <div class="job-detail-mini u067" title="${esc(j.job_type)} ${indet ? '' : pct + '%'} ${elapsed}">
                    <strong>${indet ? '···' : pct + '%'}</strong>
                    <div class="progress-bar u098">${bar}</div>
                </div>
            </div>`;
        }).join('');
    } catch (e) {}
}

// Poll every 5s
setInterval(checkRunningJobs, 5000);

// ---- Sidebar Collapse ----
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed') ? '1' : '');
}

// Restore sidebar state on load
(function() {
    if (localStorage.getItem('sidebar-collapsed') === '1') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('collapsed');
    }
})();

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => { initCustomSelects(); initTooltips(); initTableSort(); checkRunningJobs(); }, 100);

    const path = window.location.pathname;
    if (path === '/' || path === '') { loadDashboard(); loadOpenSearchStatus(); loadNotifyStatus(); }
    else if (path === '/archives') { initColumnSettings(); loadArchives(); loadArchivePath(); }
    else if (path === '/export') { loadExportPage().then(() => setTimeout(initCustomSelects, 200)); }
    else if (path === '/import') { window.location.href = '/archives'; return; }
    else if (path === '/jobs') loadTable('#jobs-table', loadJobs);
    else if (path === '/schedules') {
        // Render the schedule table immediately (it is a fast DB-only read) with
        // a loading spinner. Do NOT block it on /api/servers, which runs live
        // per-server connectivity + Data Node probes — those carry retries and
        // connect timeouts that take 20-40s when a node is slow or unreachable.
        // The server name is only a display fallback (schedules store their own
        // c.server); it fills in on the next poll once /api/servers resolves.
        loadTable('#schedules-table', () => loadSchedules().then(() => setTimeout(initCustomSelects, 200)));
        fetchJSON(`${API}/servers`).then(d => { if (d.items?.length) window._defaultServerName = d.items[0].name; }).catch(()=>{});
        startSchedPoll();
    }
    else if (path === '/notify-settings') loadNotifySettings();
    else if (path === '/logs') { loadRealtimeLog(); loadTable('#audit-table', loadAuditLog); }
    else if (path === '/op-audit') { loadAuditData(1); loadAuditStatus(); loadAuditNginxConfig(); }
    else if (path === '/settings') loadSettingsPage();
    else if (path === '/reports') loadReportsPage();
});

// Re-translate dynamic JS-rendered content when language changes.
// applyI18n() handles static data-i18n elements; this re-fires each page's
// loader so JS-built innerHTML (badges, modal labels, table cells, etc.) is
// rebuilt under the new language without forcing a browser refresh.
document.addEventListener('langchange', () => {
    const path = window.location.pathname;
    if (path === '/' || path === '') {
        loadDashboard(); loadOpenSearchStatus(); loadNotifyStatus();
    } else if (path === '/archives') {
        loadArchives(typeof archivePage !== 'undefined' ? archivePage : 1);
        loadArchivePath();
    } else if (path === '/jobs') {
        loadJobs();
    } else if (path === '/schedules') {
        loadSchedules();
    } else if (path === '/notify-settings') {
        loadNotifySettings();
    } else if (path === '/logs') {
        loadRealtimeLog(); loadTable('#audit-table', loadAuditLog);
    } else if (path === '/op-audit') {
        loadAuditData(_auditPage || 1); loadAuditStatus(); loadAuditNginxConfig();
    } else if (path === '/settings') {
        loadSettingsPage();
    } else if (path === '/reports') {
        loadReportsPage();
    }
});

// --- API Audit page ---

let _auditPage = 1;

async function loadAuditData(page) {
    _auditPage = page || 1;
    const fromVal = document.getElementById('audit-filter-from')?.value || '';
    const toVal = document.getElementById('audit-filter-to')?.value || '';
    const params = new URLSearchParams({page: _auditPage, page_size: 50});
    const user = document.getElementById('audit-filter-user')?.value;
    const method = document.getElementById('audit-filter-method')?.value;
    const uri = document.getElementById('audit-filter-uri')?.value;
    const sc = document.getElementById('audit-filter-status')?.value;
    const sens = document.getElementById('audit-filter-sensitive')?.checked;
    if (user) params.set('username', user);
    if (method) params.set('method', method);
    if (uri) params.set('uri', uri);
    if (sc) params.set('status_code', sc);
    if (sens) params.set('sensitive_only', 'true');
    if (fromVal) params.set('time_from', new Date(fromVal).toISOString());
    if (toVal) params.set('time_to', new Date(toVal).toISOString());
    const tbody = document.querySelector('#audit-table tbody');
    if (tbody) tbody.innerHTML = `<tr><td class="u146" colspan="8">${t('loading')}...</td></tr>`;

    try {
        const data = await fetchJSON(`${API}/audit?${params}`);
        if (!data.items || data.items.length === 0) {
            if (tbody) tbody.innerHTML = `<tr><td class="u146" colspan="8">${t('log_no_data')}</td></tr>`;
        } else {
            const methodColors = {GET:'#4caf50',POST:'#2196f3',PUT:'#ff9800',DELETE:'#f44336',PATCH:'#9c27b0'};
            if (tbody) tbody.innerHTML = data.items.map(a => {
                const mc = methodColors[a.method] || '#888';
                const sc = a.status_code >= 400 ? 'color:var(--danger)' : '';
                const sens = a.is_sensitive ? `<span class="u030" title="${esc(a.operation)}">⚠</span>` : '';
                const target = a.target_name || '';
                const sensIcon = a.is_sensitive ? `<span class="u018" title="${t('audit_sensitive_ops')}">${icon('warning',16)}</span>` : '';
                return `<tr class="u033" data-act="showAuditDetail" data-args="[${a.id}]">
                    <td class="u149">${formatDT(a.timestamp)}</td>
                    <td class="u077">${esc(a.server_name || '')}</td>
                    <td>${esc(a.username || '-')}</td>
                    <td class="u077">${esc(a.remote_addr || '')}</td>
                    <td>${esc(a.operation || '')}</td>
                    <td class="u119" title="${esc(a.uri)}">${esc(target || a.uri || '')}</td>
                    <td class="u139">${sensIcon}</td>
                </tr>`;
            }).join('');
        }
        // Pagination
        const totalPages = Math.ceil((data.total || 0) / (data.page_size || 50));
        const pag = document.getElementById('audit-pagination');
        if (pag && totalPages > 1) {
            let html = '';
            if (_auditPage > 1) html += `<button class="btn-sm btn-secondary" data-act="loadAuditData" data-args="[${_auditPage-1}]">${icon('arrow_left')}</button>`;
            html += `<span class="u100">${_auditPage} / ${totalPages} (${data.total})</span>`;
            if (_auditPage < totalPages) html += `<button class="btn-sm btn-secondary" data-act="loadAuditData" data-args="[${_auditPage+1}]">${icon('arrow_right')}</button>`;
            pag.innerHTML = html;
        } else if (pag) {
            pag.innerHTML = data.total ? `<span class="u022">${data.total} ${t('unit_records')}</span>` : '';
        }

        // Stats
        const stats = await fetchJSON(`${API}/audit/stats?hours=24`);
        const s1 = document.getElementById('audit-stat-total');
        const s2 = document.getElementById('audit-stat-users');
        const s3 = document.getElementById('audit-stat-errors');
        const s4 = document.getElementById('audit-stat-sensitive');
        const sLF = document.getElementById('audit-stat-loginfail');
        if (s1) s1.querySelector('.card-value').textContent = formatNumber(stats.total || 0);
        if (s2) s2.querySelector('.card-value').textContent = stats.unique_users || 0;
        if (sLF) sLF.querySelector('.card-value').textContent = stats.login_failures || 0;
        if (s4) s4.querySelector('.card-value').textContent = stats.sensitive || 0;
        // Sparklines
        const sp = stats.sparkline || {};
        if (s1 && sp.ops && !s1.querySelector('.sparkline-svg')) s1.insertAdjacentHTML('beforeend', buildSparkSVG(sp.ops, '#6c63ff', 'number'));
        if (s2 && sp.ops && !s2.querySelector('.sparkline-svg')) s2.insertAdjacentHTML('beforeend', buildSparkSVG(sp.ops, '#4caf50', 'number'));
        if (sLF && sp.login_failures && !sLF.querySelector('.sparkline-svg')) sLF.insertAdjacentHTML('beforeend', buildSparkSVG(sp.login_failures, '#ff9800', 'number'));
        if (s4 && sp.sensitive && !s4.querySelector('.sparkline-svg')) s4.insertAdjacentHTML('beforeend', buildSparkSVG(sp.sensitive, '#f44336', 'number'));
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td class="u145" colspan="7">${t('load_failed')}</td></tr>`;
    }
}

async function loadAuditStatus() {
    try {
        const st = await fetchJSON(`${API}/audit/status`);
        const bar = document.getElementById('audit-listener-status');
        const last = document.getElementById('audit-last-received');
        const btn = document.getElementById('audit-toggle-btn');
        if (btn) {
            if (st.enabled) {
                btn.className = 'btn-sm btn-danger';
                btn.innerHTML = `${icon('pause',14)} ${t('btn_disable')}`;
            } else {
                btn.className = 'btn-sm btn-success';
                btn.innerHTML = `${icon('play',14)} ${t('btn_enable')}`;
            }
        }
        if (bar) {
            if (st.enabled && st.listening) {
                const ips = st.allowed_ips?.join(', ') || '-';
                const rx = st.last_received_at
                    ? `${t('audit_last_received')}: ${formatDT(st.last_received_at)} (${formatNumber(st.received)} ${t('audit_received_count')})`
                    : `${t('audit_last_received')}: -`;
                const hbAlert = st.heartbeat_alert
                    ? `<span class="u019">${icon('warning',14)} ${t('audit_heartbeat_alert')}</span>`
                    : '';
                const ret = st.retention_days ? `<span class="u123">${t('audit_retention')}: ${st.retention_days} ${t('audit_retention_days')}</span>` : '';
                bar.innerHTML = `<span class="u021">● ${t('audit_listening')}</span>`
                    + `<span>UDP :${st.port}</span>`
                    + `<span class="u123">${rx}</span>`
                    + ret
                    + hbAlert;
            } else if (st.enabled) {
                bar.innerHTML = `<span class="u032">● ${t('audit_starting')}...</span>`;
            } else {
                bar.innerHTML = '';
            }
        }
        if (last) last.textContent = '';
    } catch (e) {}
}

async function toggleAuditEnabled() {
    const btn = document.getElementById('audit-toggle-btn');
    if (btn) btn.disabled = true;
    try {
        await fetchJSON(`${API}/audit/toggle`, {method: 'POST'});
        await loadAuditStatus();
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function showAuditDetail(id) {
    try {
        const entry = await fetchJSON(`${API}/audit/${id}`);
        const el = document.getElementById('audit-detail-content');
        if (!el) return;
        let bodyHtml = '';
        if (entry.request_body) {
            let formatted = null;
            try {
                formatted = JSON.stringify(JSON.parse(entry.request_body), null, 2);
            } catch {
                // Truncated JSON — try to pretty-print what we have
                try {
                    // Simple heuristic: add enough closing braces/brackets
                    let fix = entry.request_body.replace(/\.\.\.\[truncated\]$/, '');
                    fix = fix.replace(/,[^,]*$/, '');  // remove incomplete last field
                    const opens = (fix.match(/[{[]/g) || []).length;
                    const closes = (fix.match(/[}\]]/g) || []).length;
                    for (let i = 0; i < opens - closes; i++) fix += fix.includes('[') ? ']' : '}';
                    formatted = JSON.stringify(JSON.parse(fix), null, 2) + '\n... (truncated)';
                } catch { /* give up */ }
            }
            if (formatted) {
                bodyHtml = `<pre class="log-output u124">${_syntaxHL(formatted)}</pre>`;
            } else {
                bodyHtml = `<pre class="log-output u125">${esc(entry.request_body)}</pre>`;
            }
        }
        const L = 'class="audit-k"';
        const V = 'class="audit-v"';
        const tgt = entry.target_name || '';
        el.innerHTML = `
            <table class="u151">
                <tr><td ${L}>${t('th_time')}</td><td ${V}>${formatDT(entry.timestamp)}</td></tr>
                <tr><td ${L}>${t('login_username')}</td><td ${V}>${esc(entry.username || '-')}</td></tr>
                <tr><td ${L}>${t('audit_operation')}</td><td ${V}>${esc(entry.operation || '-')}</td></tr>
                <tr><td ${L}>${t('audit_target')}</td><td ${V}>${esc(tgt || '-')}</td></tr>
                <tr><td ${L}>${t('audit_sensitive_ops')}</td><td ${V}>${entry.is_sensitive ? `<span class="u018">${icon('warning',16)} ${t('audit_sensitive_yes')}</span>` : '-'}</td></tr>
                <tr><td ${L}>${t('audit_method')}</td><td ${V}><strong>${esc(entry.method)}</strong> ${entry.status_code}</td></tr>
                <tr><td ${L}>URI</td><td ${V}>${esc(entry.uri)}${entry.query_string ? '?' + esc(entry.query_string) : ''}</td></tr>
                <tr><td ${L}>${t('audit_ip')}</td><td ${V}>${esc(entry.remote_addr)}</td></tr>
                <tr><td ${L}>${t('audit_user_agent')}</td><td class="u130" ${V}>${esc(entry.user_agent || '-')}</td></tr>
                <tr><td ${L}>${t('audit_response_time')}</td><td ${V}>${(entry.request_time_ms || 0).toFixed(1)} ms</td></tr>
                <tr><td ${L}>${t('audit_server')}</td><td ${V}>${esc(entry.server_name || '-')}</td></tr>
            </table>
            ${bodyHtml ? `<div class="u138"><h4 class="u117">${t('audit_request_body')}</h4><button class="u135" data-act="copyAuditBody" data-act-self>${t('btn_copy')}</button><div class="u066" id="audit-body-raw">${esc(entry.request_body)}</div>${bodyHtml}</div>` : ''}
        `;
        document.getElementById('audit-detail-modal').style.display = 'flex';
    } catch (e) {}
}

async function loadAuditNginxConfig() {
    try {
        const cfg = await fetchJSON(`${API}/audit/nginx-config`);
        const el = document.getElementById('audit-nginx-config');
        const port = cfg.server_block?.match(/:(\d+),/)?.[1] || '8991';
        if (el) el.innerHTML = _nginxHL(
`# ======================================================
# Step 1: /etc/nginx/nginx.conf
# Add inside http { } block, BEFORE "include" lines
# ======================================================
#
# http {
#     ...existing settings...
#
${cfg.log_format}
#
#     include /etc/nginx/conf.d/*.conf;      <-- must be AFTER log_format
#     include /etc/nginx/sites-enabled/*;    <-- must be AFTER log_format
# }

# ======================================================
# Step 2: Graylog site config
# e.g. /etc/nginx/sites-available/graylog.conf
# Add inside server { } block
# ======================================================
#
# server {
#     ...existing settings...
#
${cfg.server_block}
#
# }

# ======================================================
# Step 3: Open UDP port ${port} on jt-glogarch server
# ======================================================
# sudo ufw allow ${port}/udp
# or: sudo firewall-cmd --add-port=${port}/udp --permanent && sudo firewall-cmd --reload

# ======================================================
# Step 4: Test and reload nginx (on each Graylog server)
# ======================================================
# sudo nginx -t && sudo systemctl reload nginx`);
    } catch (e) {}
}

function _nginxHL(text) {
    // nginx config syntax highlighting
    // Content is from our own API (safe), so we escape < > & only, not quotes
    const e = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const C = '#6a9955', D = '#569cd6', S = '#ce9178', V = '#dcdcaa', T = '#4ec9b0', P = '#c586c0';
    return text.split('\n').map(line => {
        let s = e(line);
        if (/^\s*#/.test(line)) return `<span data-style="color:${C}">${s.replace(/(Step \d)/g, `</span><span data-style="color:${P};font-weight:600">$1</span><span data-style="color:${C}">`)}</span>`;
        s = s.replace(/\b(http|server|location|log_format|access_log|client_body_buffer_size|include|sudo|nginx|systemctl|ufw|firewall-cmd)\b/g, `<span data-style="color:${D};font-weight:600">$1</span>`);
        s = s.replace(/('[^']*')/g, `<span data-style="color:${S}">$1</span>`);
        s = s.replace(/(\$\w+)/g, `<span data-style="color:${V}">$1</span>`);
        s = s.replace(/(escape=json|syslog:server=|facility=|tag=)/g, `<span data-style="color:${T}">$1</span>`);
        return s;
    }).join('\n');
}

function _syntaxHL(json) {
    // JSON syntax highlighting — returns HTML with color spans
    return esc(json).replace(
        /("(?:\\.|[^"\\])*")\s*:/g,  // keys
        '<span class="u006">$1</span>:'
    ).replace(
        /:\s*("(?:\\.|[^"\\])*")/g,  // string values
        ': <span class="u010">$1</span>'
    ).replace(
        /:\s*(\d+\.?\d*)/g,  // numbers
        ': <span class="u014">$1</span>'
    ).replace(
        /:\s*(true|false)/g,  // booleans
        ': <span class="u016">$1</span>'
    ).replace(
        /:\s*(null)/g,  // null
        ': <span class="u007">$1</span>'
    );
}

function copyAuditNginxConfig() {
    const el = document.getElementById('audit-nginx-config');
    if (el) navigator.clipboard.writeText(el.textContent).then(() => showAlert(t('msg_copied'))).catch(() => {});
}


// ============================================================
// System Settings page — Graylog servers + OpenSearch (Web UI editable)
// ============================================================

let _serversCache = [];
let _osCache = {};

function _setResult(elId, ok, msg) {
    const el = document.getElementById(elId);
    if (el) el.innerHTML = `<span data-style="color:${ok ? 'var(--success)' : 'var(--danger)'}">${esc(msg)}</span>`;
}

function _secretField(id, val) {
    return `<div class="secret-field"><input type="password" id="${id}" value="${esc(val || '')}" autocomplete="new-password"><button type="button" class="secret-toggle" data-act="toggleSecret" data-act-self tabindex="-1" title="Show/Hide">${icon('eye_closed')}</button></div>`;
}

async function loadSettingsPage() {
    const [servers, os, imp] = await Promise.all([
        fetchJSON(`${API}/config/servers`),
        fetchJSON(`${API}/config/opensearch`),
        fetchJSON(`${API}/config/import-defaults`),
    ]);
    _serversCache = servers.items || [];
    _osCache = os || {};
    renderServersTable(servers);
    const modeSel = document.getElementById('settings-export-mode');
    if (modeSel && servers.export_mode) modeSel.value = servers.export_mode;
    toggleMaxResultHint(modeSel ? modeSel.value : 'api');
    renderOpenSearchForm(os);
    renderImportDefaultsForm(imp || {});
    renderAdminForm();
    applyI18n();
}

function renderImportDefaultsForm(c) {
    const el = document.getElementById('settings-import-form');
    if (!el) return;
    el.innerHTML = `
      <div class="form-group"><label>${t('settings_imp_gelf_host')}</label>
        <input type="text" id="settings-imp-host" value="${esc(c.gelf_host || '')}" placeholder="192.168.1.10"></div>
      <div class="u039">
        <div class="form-group"><label>${t('settings_imp_gelf_port')}</label>
          <input type="text" id="settings-imp-port" value="${esc(String(c.gelf_port || 32202))}"></div>
        <div class="form-group"><label>${t('settings_imp_gelf_proto')}</label>
          <select id="settings-imp-proto" class="no-custom u131">
            <option value="tcp" ${(c.gelf_protocol || 'tcp') === 'tcp' ? 'selected' : ''}>TCP</option>
            <option value="udp" ${c.gelf_protocol === 'udp' ? 'selected' : ''}>UDP</option>
          </select></div>
      </div>
      <div class="form-group"><label>${t('settings_imp_api_url')}</label>
        <input type="text" id="settings-imp-api-url" value="${esc(c.target_api_url || '')}" placeholder="http://192.168.1.10:9000"></div>
      <div class="form-group"><label>${t('settings_imp_api_token')}</label>${_secretField('settings-imp-token', c.target_api_token)}</div>
      <div class="form-group"><label>${t('settings_imp_api_user')}</label>
        <input type="text" id="settings-imp-user" value="${esc(c.target_api_username || '')}" autocomplete="off"></div>
      <div class="form-group"><label>${t('settings_imp_api_pass')}</label>${_secretField('settings-imp-pass', c.target_api_password)}</div>`;
}

function _gatherImportBody() {
    return {
        gelf_host: document.getElementById('settings-imp-host')?.value?.trim() || '',
        gelf_port: document.getElementById('settings-imp-port')?.value?.trim() || '32202',
        gelf_protocol: document.getElementById('settings-imp-proto')?.value || 'tcp',
        target_api_url: document.getElementById('settings-imp-api-url')?.value?.trim() || '',
        target_api_token: document.getElementById('settings-imp-token')?.value || '',
        target_api_username: document.getElementById('settings-imp-user')?.value?.trim() || '',
        target_api_password: document.getElementById('settings-imp-pass')?.value || '',
    };
}

async function saveImportDefaults() {
    const r = await fetchJSON(`${API}/config/import-defaults`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(_gatherImportBody()),
    });
    _setResult('settings-import-result', !r.error, r.error || t('settings_saved'));
    if (!r.error) loadSettingsPage();
}

async function testImportDefaults() {
    _setResult('settings-import-result', true, t('loading') + '...');
    const r = await fetchJSON(`${API}/config/import-defaults/test`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(_gatherImportBody()),
    });
    if (r.connected) {
        _setResult('settings-import-result', true, `${t('test_ok')} — Graylog ${esc(r.version || '')}`);
    } else {
        _setResult('settings-import-result', false, esc(r.error || t('test_failed')));
    }
}

function renderServersTable(data) {
    const tbody = document.querySelector('#servers-table tbody');
    if (!tbody) return;
    const items = data.items || [];
    const def = data.default_server || '';
    if (!items.length) {
        tbody.innerHTML = `<tr><td class="u142" colspan="6">${t('settings_none')}</td></tr>`;
        return;
    }
    tbody.innerHTML = items.map(s => {
        const auth = s.auth_token ? t('settings_auth_token') : (s.username ? t('settings_auth_userpass') : '-');
        const isDef = s.name === def;
        const osCell = s.has_opensearch ? t('settings_yes') : t('settings_no');
        const defCell = isDef
            ? `<span class="u020">${t('settings_is_default')}</span>`
            : `<button class="btn-sm btn-secondary" data-act="setDefaultServer" data-arg="${esc(s.name)}">${icon('shield', 14)} ${t('settings_make_default')}</button>`;
        return `<tr>
            <td>${esc(s.name)}</td>
            <td>${esc(s.url)}</td>
            <td>${esc(auth)}</td>
            <td>${esc(osCell)}</td>
            <td>${defCell}</td>
            <td>
                <button class="btn-sm btn-secondary" data-act="testGraylogServer" data-arg="${esc(s.name)}">${icon('refresh', 14)} ${t('btn_test_connection')}</button>
                <button class="btn-sm btn-secondary" data-act="flushServer" data-arg="${esc(s.name)}" title="${esc(t('flush_target_hint'))}">${icon('refresh', 14)} ${t('flush_server')}</button>
                <button class="btn-sm btn-secondary" data-act="openServerModal" data-arg="${esc(s.name)}" data-icon-btn>${icon('lock', 14)} ${t('btn_edit')}</button>
                <button class="btn-sm btn-danger" data-act="deleteServer" data-arg="${esc(s.name)}">${icon('trash', 14)} ${t('btn_delete')}</button>
            </td>
        </tr>`;
    }).join('');
}

function buildServerForm(s) {
    s = s || {};
    const os = s.opensearch || {};
    const hasOs = !!s.has_opensearch;
    const authType = s.auth_token ? 'token' : (s.username ? 'userpass' : 'token');
    return `
      <input type="hidden" id="srv-orig-name" value="${esc(s.name || '')}">
      <div class="form-group"><label>${t('settings_srv_name')}</label>
        <input type="text" id="srv-name" value="${esc(s.name || '')}" ${s.name ? 'readonly' : ''} placeholder="graylog-main"></div>
      <div class="form-group"><label>${t('settings_srv_url')}</label>
        <input type="text" id="srv-url" value="${esc(s.url || '')}" placeholder="http://192.168.1.10:9000"></div>
      <div class="form-group"><label>${t('settings_srv_auth_type')}</label>
        <select id="srv-auth-type" class="no-custom u131" data-act-change="_toggleSrvAuth">
          <option value="token" ${authType === 'token' ? 'selected' : ''}>${t('settings_auth_token')}</option>
          <option value="userpass" ${authType === 'userpass' ? 'selected' : ''}>${t('settings_auth_userpass')}</option>
        </select></div>
      <div class="form-group" id="srv-token-group"><label>${t('settings_srv_token')}</label>${_secretField('srv-token', s.auth_token)}</div>
      <div class="form-group" id="srv-user-group"><label>${t('settings_srv_user')}</label>
        <input type="text" id="srv-user" value="${esc(s.username || '')}" autocomplete="off"></div>
      <div class="form-group" id="srv-pass-group"><label>${t('settings_srv_pass')}</label>${_secretField('srv-pass', s.password)}</div>
      <div class="form-group"><label class="u065">
        <input type="checkbox" id="srv-verify-ssl" ${s.verify_ssl ? 'checked' : ''}> ${t('settings_verify_ssl')}</label></div>
      <hr class="u003">
      <div class="form-group"><label class="u065">
        <input type="checkbox" id="srv-os-enable" ${hasOs ? 'checked' : ''} data-act-change="_toggleSrvOs"> ${t('settings_per_os_enable')}</label></div>
      <div id="srv-os-group" data-style="${hasOs ? '' : 'display:none'}">
        <div class="form-group"><label>${t('settings_os_hosts')}</label>
          <textarea class="u150" id="srv-os-hosts" rows="2">${esc((os.hosts || []).join('\n'))}</textarea></div>
        <div class="form-group"><label>${t('settings_os_user')}</label>
          <input type="text" id="srv-os-user" value="${esc(os.username || '')}" autocomplete="off"></div>
        <div class="form-group"><label>${t('settings_os_pass')}</label>${_secretField('srv-os-pass', os.password)}</div>
        <div class="form-group"><label class="u065">
          <input type="checkbox" id="srv-os-verify" ${os.verify_ssl ? 'checked' : ''}> ${t('settings_verify_ssl')}</label></div>
      </div>`;
}

function _toggleSrvAuth() {
    const type = document.getElementById('srv-auth-type')?.value;
    const tok = document.getElementById('srv-token-group');
    const usr = document.getElementById('srv-user-group');
    const pas = document.getElementById('srv-pass-group');
    if (tok) tok.style.display = (type === 'token') ? '' : 'none';
    if (usr) usr.style.display = (type === 'userpass') ? '' : 'none';
    if (pas) pas.style.display = (type === 'userpass') ? '' : 'none';
}

function _toggleSrvOs() {
    const on = document.getElementById('srv-os-enable')?.checked;
    const g = document.getElementById('srv-os-group');
    if (g) g.style.display = on ? '' : 'none';
}

function openServerModal(name) {
    const s = name ? _serversCache.find(x => x.name === name) : null;
    const title = document.getElementById('server-modal-title');
    if (title) title.innerHTML = icon('server') + ' ' + esc(s ? t('settings_edit_server') : t('settings_add_server'));
    document.getElementById('server-modal-form').innerHTML = buildServerForm(s);
    _setResult('server-modal-result', true, '');
    document.getElementById('server-modal-result').innerHTML = '';
    document.getElementById('server-modal').style.display = 'flex';
    _toggleSrvAuth();
}

function _gatherServerBody() {
    const v = id => (document.getElementById(id)?.value || '').trim();
    const ck = id => !!document.getElementById(id)?.checked;
    const authType = document.getElementById('srv-auth-type')?.value;
    const body = {
        name: v('srv-name'),
        url: v('srv-url'),
        verify_ssl: ck('srv-verify-ssl'),
    };
    if (authType === 'token') {
        body.auth_token = v('srv-token');
        body.username = '';
        body.password = '';
    } else {
        body.username = v('srv-user');
        body.password = v('srv-pass');
        body.auth_token = '';
    }
    if (ck('srv-os-enable')) {
        const hosts = v('srv-os-hosts').split('\n').map(h => h.trim()).filter(Boolean);
        body.opensearch = {
            hosts,
            username: v('srv-os-user'),
            password: v('srv-os-pass'),
            verify_ssl: ck('srv-os-verify'),
        };
    } else {
        body.opensearch = { hosts: [] };  // explicit empty → drop per-server OS
    }
    return body;
}

async function saveServer() {
    const body = _gatherServerBody();
    if (!body.name || !body.url) { _setResult('server-modal-result', false, t('settings_srv_name') + ' / ' + t('settings_srv_url')); return; }
    const r = await fetchJSON(`${API}/config/servers`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (r.error) { _setResult('server-modal-result', false, r.error); return; }
    document.getElementById('server-modal').style.display = 'none';
    loadSettingsPage();
}

// Render Graylog JVM heap sizing advice from a connection-test response.
function _heapAdviceHtml(heap) {
    if (!heap || !heap.heap_max_gb) return '';
    const used = (heap.used_pct != null) ? `（${t('heap_used')} ${heap.used_pct}%）` : '';
    let verdict, cls;
    if (heap.level === 'low') { verdict = t('heap_low').replace('{n}', heap.recommended_min_gb); cls = 'status-failed'; }
    else if (heap.level === 'ok') { verdict = t('heap_ok').replace('{n}', heap.recommended_min_gb); cls = 'u022'; }
    else { verdict = t('heap_good'); cls = 'status-completed'; }
    return `<div class="test-result-line" style="margin-top:4px">`
        + `${t('heap_label')}: <b>${heap.heap_max_gb} GB</b>${used} — <span class="${cls}">${esc(verdict)}</span>`
        + (heap.level !== 'good' ? `<br><span class="u022">${t('heap_hint')}</span>` : '')
        + `</div>`;
}

async function testServerFromModal() {
    const body = _gatherServerBody();
    // Omit masked secrets so the backend falls back to the stored value.
    if (body.auth_token && body.auth_token.includes('***')) delete body.auth_token;
    if (body.password && body.password.includes('***')) delete body.password;
    if (!body.url) { _setResult('server-modal-result', false, t('settings_srv_url')); return; }
    _setResult('server-modal-result', true, t('loading') + '...');
    const r = await fetchJSON(`${API}/config/servers/test`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (r.connected) {
        _setResult('server-modal-result', true, `${t('test_ok')} (${esc(r.version || '')})`);
        const box = document.getElementById('server-modal-result');
        if (box && r.heap) box.insertAdjacentHTML('beforeend', _heapAdviceHtml(r.heap));
    } else _setResult('server-modal-result', false, `${t('test_failed')}: ${esc(r.error || '')}`);
}

function deleteServer(name) {
    showConfirm(t('settings_edit_server'), t('settings_confirm_delete').replace('{name}', name), async () => {
        const r = await fetchJSON(`${API}/config/servers/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (r.error) { showAlert(r.error); return; }
        loadSettingsPage();
    });
}

async function testGraylogServer(name, i) {
    // Inline result shown in a sub-row directly under this server (like the
    // OpenSearch panel shows its result inside its own box).
    const row = (i !== undefined) ? document.getElementById('srv-result-row-' + i) : null;
    const el = (i !== undefined) ? document.getElementById('srv-result-' + i)
        : (document.getElementById('servers-result') || document.getElementById('config-servers-result'));
    if (row) row.classList.remove('hidden');
    if (el) el.innerHTML = `<span class="u022">${esc(name)} — ${t('btn_test_connection')}…</span>`;
    const r = await fetchJSON(`${API}/config/servers/${encodeURIComponent(name)}/test`, { method: 'POST' });
    const html = (r && r.connected)
        ? `<span class="status-completed">${t('test_connected')}</span> ${esc(name)} — Graylog ${esc(r.version || '')}` + (r.heap ? _heapAdviceHtml(r.heap) : '')
        : `<span class="status-failed">${t('test_failed')}</span> ${esc(name)} — ${esc((r && r.error) || t('unknown_error'))}`;
    if (el) el.innerHTML = html;
    else showAlert(html.replace(/<[^>]+>/g, ''));
}

async function setDefaultServer(name) {
    const r = await fetchJSON(`${API}/config/general`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_server: name }),
    });
    if (r.error) { showAlert(r.error); return; }
    loadSettingsPage();
}

// --- Non-destructive "relieve / flush" a wedged target Graylog --------------
// Renders the before/after backpressure snapshot + per-action outcome. NEVER
// deletes data — the backend only cycles the write index and rebuilds ranges.
function _flushResultHtml(r) {
    if (!r || r.error) {
        return `<span class="status-failed">${t('flush_failed')}</span> ${esc((r && r.error) || t('unknown_error'))}`;
    }
    const actName = n => n === 'cycle_deflector' ? t('flush_action_cycle')
        : (n === 'rebuild_index_ranges' ? t('flush_action_rebuild') : n);
    const acts = (r.actions || []).map(a => {
        const cls = a.status === 'ok' ? 'status-completed' : 'status-failed';
        const detail = a.status === 'ok' ? '' : ` — ${esc(a.detail || '')}`;
        return `<div><span class="${cls}">${esc(actName(a.name))}</span>${detail}</div>`;
    }).join('');
    const b = r.before || {}, af = r.after || {};
    const delta = (before, after) => {
        if (before == null || after == null) return '';
        const d = after - before;
        return ` <span class="u030">(${before} → ${after}${d ? (d < 0 ? ' ▼' : ' ▲') : ''})</span>`;
    };
    const snap = (Object.keys(b).length || Object.keys(af).length)
        ? `<div class="u030" style="margin-top:6px">
             ${t('flush_journal')}:${delta(b.journal_uncommitted, af.journal_uncommitted)}<br>
             ${t('flush_buffers')}:${delta(b.buffer_process, af.buffer_process)} /${delta(b.buffer_output, af.buffer_output)}
           </div>` : '';
    const head = r.ok ? `<span class="status-completed">${t('flush_done')}</span>`
        : `<span class="status-failed">${t('flush_failed')}</span>`;
    return `${head}${acts}${snap}`;
}

async function flushServer(name) {
    showConfirm(t('flush_confirm_title'), t('flush_confirm_msg'), async () => {
        const el = document.getElementById('servers-result') || document.getElementById('config-servers-result');
        if (el) el.innerHTML = `<span class="u022">${esc(name)} — ${t('flush_running')}</span>`;
        const r = await fetchJSON(`${API}/graylog/flush`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server: name }),
        });
        const html = `${esc(name)} — ${_flushResultHtml(r)}`;
        if (el) el.innerHTML = html; else showAlert(html.replace(/<[^>]+>/g, ''));
    });
}

async function flushImportTarget() {
    showConfirm(t('flush_confirm_title'), t('flush_confirm_msg'), async () => {
        const el = document.getElementById('modal-import-result');
        if (el) el.innerHTML = `<span class="u022">${t('flush_running')}</span>`;
        // Empty body → backend uses the stored import-default target creds.
        const r = await fetchJSON(`${API}/graylog/flush`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
        });
        if (el) el.innerHTML = _flushResultHtml(r);
        else showAlert(_flushResultHtml(r).replace(/<[^>]+>/g, ''));
    });
}

async function saveExportMode(mode) {
    toggleMaxResultHint(mode);
    const r = await fetchJSON(`${API}/config/general`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ export_mode: mode }),
    });
    _setResult('settings-export-mode-result', !r.error, r.error || t('settings_saved'));
}

// The max_result_window caveat only applies to Graylog API mode (offset
// pagination bounded by index.max_result_window). Show it only for API mode.
function toggleMaxResultHint(mode) {
    const hint = document.getElementById('settings-max-result-hint');
    if (!hint) return;
    hint.classList.toggle('hidden', mode !== 'api');
}

function renderOpenSearchForm(os) {
    const el = document.getElementById('settings-os-form');
    if (!el) return;
    el.innerHTML = `
      <div class="form-group"><label>${t('settings_os_hosts')}</label>
        <textarea class="u150" id="settings-os-hosts" rows="2">${esc((os.hosts || []).join('\n'))}</textarea></div>
      <div class="form-group"><label>${t('settings_os_user')}</label>
        <input type="text" id="settings-os-user" value="${esc(os.username || '')}" autocomplete="off"></div>
      <div class="form-group"><label>${t('settings_os_pass')}</label>${_secretField('settings-os-pass', os.password)}</div>
      <div class="form-group"><label class="u065">
        <input type="checkbox" id="settings-os-verify" ${os.verify_ssl ? 'checked' : ''}> ${t('settings_verify_ssl')}</label></div>`;
}

function _gatherOsBody() {
    const v = id => (document.getElementById(id)?.value || '').trim();
    const hosts = v('settings-os-hosts').split('\n').map(h => h.trim()).filter(Boolean);
    return {
        hosts,
        username: v('settings-os-user'),
        password: v('settings-os-pass'),
        verify_ssl: !!document.getElementById('settings-os-verify')?.checked,
    };
}

async function saveOpenSearchConfig() {
    const body = _gatherOsBody();
    const r = await fetchJSON(`${API}/config/opensearch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    _setResult('settings-os-result', !r.error, r.error || t('settings_saved'));
    if (!r.error) loadSettingsPage();
}

async function testOpenSearchConfig() {
    const body = _gatherOsBody();
    if (body.password && body.password.includes('***')) delete body.password;
    _setResult('settings-os-result', true, t('loading') + '...');
    const r = await fetchJSON(`${API}/opensearch/test`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (r.connected) _setResult('settings-os-result', true, `${t('test_ok')} (${esc(r.version || r.cluster_name || '')})`);
    else _setResult('settings-os-result', false, `${t('test_failed')}: ${esc(r.error || '')}`);
}

function renderAdminForm() {
    const el = document.getElementById('settings-admin-form');
    if (!el) return;
    el.innerHTML = `<div class="form-group u121"><label>${t('settings_admin_pass')}</label>${_secretField('settings-admin-pass', '')}</div>`;
}

async function saveAdminPassword() {
    const pw = (document.getElementById('settings-admin-pass')?.value || '');
    const r = await fetchJSON(`${API}/config/admin-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: pw }),
    });
    _setResult('settings-admin-result', !r.error, r.error || t('settings_admin_saved'));
    if (!r.error) { const f = document.getElementById('settings-admin-pass'); if (f) f.value = ''; }
}

// ============================================================
// CSP-safe event delegation. Replaces inline on* handlers (which require
// script-src 'unsafe-inline'). Markup uses:
//   data-act="fnName"                      -> fnName()
//   data-act="fnName" data-arg="x"         -> fnName("x")
//   data-act="fnName" data-args='["a","b"]'-> fnName("a","b")
//   data-act="fnName" data-act-self        -> fnName(clickedEl)
//   data-act="fnName" data-act-event       -> fnName(event)
//   data-act-change="fnName"               -> fnName(el.value)   (on change)
// The named functions remain global (declared with `function` in this file).
// ============================================================
(function () {
    function argsFor(el, e) {
        if (el.hasAttribute('data-act-self')) return [el];
        if (el.hasAttribute('data-act-event')) return [e];
        if (el.dataset.args !== undefined) { try { return JSON.parse(el.dataset.args); } catch (_) { return []; } }
        if (el.dataset.arg !== undefined) return [el.dataset.arg];
        return [];
    }
    document.addEventListener('click', e => {
        const el = e.target.closest('[data-act]');
        if (!el) return;
        const fn = window[el.dataset.act];
        if (typeof fn === 'function') fn.apply(null, argsFor(el, e));
    });
    document.addEventListener('change', e => {
        const el = e.target.closest('[data-act-change]');
        if (!el) return;
        const fn = window[el.dataset.actChange];
        if (typeof fn !== 'function') return;
        let arg;
        if (el.hasAttribute('data-act-self')) arg = el;
        else if (el.dataset.pass === 'checked') arg = el.checked;
        else if (el.dataset.arg !== undefined) arg = el.dataset.arg;
        else arg = el.value;
        fn(arg);
    });
    document.addEventListener('input', e => {
        const el = e.target;
        if (el.matches && el.matches('[data-mark-edited]')) el.dataset.userEdited = 'true';
        const host = el.closest && el.closest('[data-act-input]');
        if (host) { const fn = window[host.dataset.actInput]; if (typeof fn === 'function') fn(host.value); }
    });
    // Fixed chrome present on every SPA page (was inline onclick/onchange).
    document.addEventListener('DOMContentLoaded', () => {
        const st = document.getElementById('sidebar-toggle');
        if (st) st.addEventListener('click', () => toggleSidebar());
        const tt = document.getElementById('theme-toggle');
        if (tt) tt.addEventListener('click', () => toggleTheme());
        const ls = document.getElementById('lang-select');
        if (ls) ls.addEventListener('change', e => setLang(e.target.value));
    });
})();

// --- Small named helpers replacing former inline DOM-manipulation handlers ---
function closeModalById(id) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
function clearLogOutput() { const e = document.getElementById('log-output'); if (e) e.textContent = ''; }
function showRateMs(v) { const e = document.getElementById('rate-display'); if (e) e.value = v; }
// Keyboard/numeric entry for the batch delay (dialog) — clamp + sync the slider.
function setRateMsNum(v) {
    let n = parseInt(v, 10); if (isNaN(n)) n = 100;
    n = Math.max(1, Math.min(2000, n));
    const s = document.getElementById('modal-rate-ms'); if (s) s.value = n;
    const e = document.getElementById('rate-display'); if (e) e.value = n;
}
function copyAuditBody(btn) {
    const src = document.getElementById('audit-body-raw');
    if (!src) return;
    navigator.clipboard.writeText(src.textContent).then(() => {
        btn.innerHTML = icon('check');
        setTimeout(() => { btn.innerHTML = t('btn_copy'); }, 1500);
    });
}

// --- Hydrate dynamic styles under a strict CSP -------------------------------
// Inline style="" attributes are forbidden by our CSP, so genuinely dynamic
// values (widths, colours) are emitted as data-style="..." and applied here via
// CSSOM (element.style.cssText), which CSP does NOT govern. A MutationObserver
// hydrates any inserted node so every render path is covered automatically.
(function () {
    function hydrate(root) {
        if (root.nodeType !== 1) return;
        if (root.hasAttribute && root.hasAttribute('data-style')) {
            root.style.cssText = root.getAttribute('data-style');
            root.removeAttribute('data-style');
        }
        if (root.querySelectorAll) root.querySelectorAll('[data-style]').forEach(el => {
            el.style.cssText = el.getAttribute('data-style');
            el.removeAttribute('data-style');
        });
    }
    const obs = new MutationObserver(muts => {
        for (const m of muts) for (const n of m.addedNodes) hydrate(n);
    });
    document.addEventListener('DOMContentLoaded', () => {
        hydrate(document.body);
        obs.observe(document.body, { childList: true, subtree: true });
    });
})();

// ============================================================
// Reports (beta)
// ============================================================
let _reportServers = [];
let _reportDashboards = [];
let _reportDashTabs = {};   // {dashboardId: chosen tab state_id}

async function loadReportsPage() {
    const [defs, hist, status, servers] = await Promise.all([
        fetchJSON(`${API}/reports`), fetchJSON(`${API}/reports/history?limit=30`),
        fetchJSON(`${API}/reports/status`), fetchJSON(`${API}/config/servers`),
    ]);
    _reportServers = servers.items || [];
    const warn = document.getElementById('reports-engine-warn');
    if (warn) {
        if (status && status.render_engine === false) {
            warn.className = 'report-warn mb15';
            warn.innerHTML = `${t('reports_engine_missing')} <button type="button" class="btn-sm btn-secondary" data-act="showReportEngineHelp">${t('reports_engine_howto')}</button>`;
        } else { warn.className = 'hidden'; }
    }
    renderReportsTable(defs.items || []);
    renderReportHistory(hist.items || []);
    applyI18n();
}

// Show how to install the optional PDF render engine (custom modal, not native).
function showReportEngineHelp() {
    showConfirm(t('reports_engine_help_title'), t('reports_engine_help_body'), null);
}

function renderReportsTable(items) {
    const tb = document.querySelector('#reports-table tbody');
    if (!tb) return;
    if (!items.length) { tb.innerHTML = `<tr><td colspan="5" class="text-center text-muted u128">${t('settings_none')}</td></tr>`; return; }
    tb.innerHTML = items.map(r => {
        const c = r.config || {};
        const bits = [];
        if (c.include_archive_summary !== false) bits.push(t('reports_content_archive'));
        if ((c.dashboards || []).length) bits.push(`${c.dashboards.length} ${t('reports_content_dash')}`);
        return `<tr>
            <td>${esc(r.name)}${(c.schedule_cron ? ' <span class="job-badge job-badge-sched">'+esc(c.schedule_cron)+'</span>' : '')}</td>
            <td>${esc(bits.join('、') || '-')}</td>
            <td>${r.enabled ? t('settings_yes') : t('settings_no')}</td>
            <td class="text-muted fs-085">${r.last_run_at ? esc(formatDT(r.last_run_at)) : '-'}</td>
            <td>
                <div class="row-actions">
                    <button class="btn-sm btn-primary" data-act="generateReport" data-arg="${esc(r.name)}">${icon('play',14)} ${t('reports_generate')}</button>
                    <button class="btn-sm btn-secondary" data-act="openReportModal" data-arg="${esc(r.name)}">${icon('edit',14)} ${t('btn_edit')}</button>
                    <button class="btn-sm btn-info" data-act="duplicateReport" data-arg="${esc(r.name)}">${icon('copy',14)} ${t('reports_duplicate')}</button>
                    <button class="btn-sm btn-danger" data-act="deleteReport" data-arg="${esc(r.name)}">${icon('trash',14)} ${t('btn_delete')}</button>
                </div>
            </td></tr>`;
    }).join('');
}

function renderReportHistory(items) {
    const tb = document.querySelector('#reports-history-table tbody');
    if (!tb) return;
    if (!items.length) { tb.innerHTML = `<tr><td colspan="6" class="text-center text-muted u128">${t('log_no_data')}</td></tr>`; return; }
    tb.innerHTML = items.map(h => `<tr>
        <td>${esc(h.report_name)} ${h.triggered_by === 'scheduled' ? '<span class="job-badge job-badge-sched">' + t('job_scheduled') + '</span>' : '<span class="job-badge job-badge-manual">' + t('job_manual') + '</span>'}</td>
        <td class="text-muted fs-085">${esc(formatDT(h.created_at))}</td>
        <td>${h.status === 'completed' ? statusBadge('completed')
              : statusBadge('failed') + (h.error ? ` <span class="text-danger fs-08">${esc((h.error || '').slice(0, 18))}${(h.error || '').length > 18 ? '…' : ''}</span> <span class="link-like fs-08" data-act="showAlert" data-arg="${esc(h.error)}">${t('reports_err_detail')}</span>` : '')}</td>
        <td>${h.size_bytes ? formatBytes(h.size_bytes) : '-'}</td>
        <td>${h.sha256 ? `<code class="fp-hash" title="SHA-256: ${esc(h.sha256)}">${esc(h.sha256.slice(0,12))}…</code> <span class="link-like fs-08" data-act="showReportFingerprint" data-arg="${esc(h.sha256)}|${esc(h.filename||'')}">${t('reports_verify')}</span>` : '-'}</td>
        <td>${h.status === 'completed' && h.file_path ? `<a class="btn-sm btn-secondary" href="${API}/reports/history/${h.id}/download">${icon('download',14)} PDF</a>` : '-'}</td>
    </tr>`).join('');
}

function _reportSecret(id, val) {
    // Blank-on-edit: never echo the stored secret (not even masked) back into the
    // field. A non-empty `val` from the API means a password IS stored, so we show
    // an empty field with a "leave blank = unchanged" hint. This makes the save
    // rule unambiguous (empty → backend keeps the stored secret; typed → replaces)
    // and makes it IMPOSSIBLE to accidentally save a masked/partial value — the
    // exact trap that once overwrote a real password with its own mask.
    const hasSecret = !!(val && String(val).length);
    const ph = hasSecret ? t('secret_keep_hint') : '';
    return `<div class="secret-field"><input type="password" id="${id}" value="" autocomplete="new-password" placeholder="${esc(ph)}"><button type="button" class="secret-toggle" data-act="toggleSecret" data-act-self tabindex="-1" title="Show/Hide">${icon('eye_closed')}</button></div>`;
}

async function openReportModal(name) {
    let cfg = {}; let existing = false;
    if (name) {
        const list = await fetchJSON(`${API}/reports`);
        const r = (list.items || []).find(x => x.name === name);
        if (r) { cfg = r.config || {}; cfg.__name = r.name; cfg.__id = r.id; cfg.__enabled = r.enabled; existing = true; }
    }
    document.getElementById('report-modal-title').innerHTML = icon('log') + ' ' + esc(existing ? t('reports_edit') : t('reports_add'));
    // Default the Graylog server: if the report has none saved and exactly one
    // server is configured, pre-select it (and auto-load its dashboards below).
    const _rpServer = cfg.server || (_reportServers.length === 1 ? _reportServers[0].name : '');
    const serverOpts = _reportServers.map(s => `<option value="${esc(s.name)}"${_rpServer===s.name?' selected':''}>${esc(s.name)}</option>`).join('');
    // Max-widget picker: "全部" (0 = unlimited) is the default.
    const _mwVal = String((cfg.max_widgets === undefined || cfg.max_widgets === null) ? 0 : cfg.max_widgets);
    let _mwList = ['0', '10', '20', '30', '50'];
    if (!_mwList.includes(_mwVal)) _mwList.push(_mwVal);
    const _mwSelect = `<select id="rp-maxw" class="no-custom">${_mwList.map(v => `<option value="${v}"${v===_mwVal?' selected':''}>${v==='0'?esc(t('reports_maxw_all')):v}</option>`).join('')}</select>`;
    document.getElementById('report-modal-form').innerHTML = `
      <input type="hidden" id="rp-orig" value="${esc(cfg.__name||'')}">
      <input type="hidden" id="rp-id" value="${esc(cfg.__id!==undefined&&cfg.__id!==null?String(cfg.__id):'')}">
      <div class="form-group"><label>${t('reports_f_name')}</label><input type="text" id="rp-name" value="${esc(cfg.__name||'')}" placeholder="weekly-security">${existing?`<div class="text-muted fs-08 mt3">${t('reports_name_editable_hint')}</div>`:''}</div>
      <div class="form-group"><label>${t('reports_f_title')}</label><input type="text" id="rp-title" value="${esc(cfg.title||'')}" placeholder="安全事件週報"></div>
      <div class="form-group"><label>${t('reports_f_subtitle')}</label><input type="text" id="rp-subtitle" value="${esc(cfg.subtitle||'')}"></div>
      <div class="form-group"><label>${t('reports_f_author')}</label><input type="text" id="rp-author" value="${esc(cfg.author||'')}"></div>
      <div class="form-group"><label>${t('reports_f_lang')}</label>
        <select id="rp-lang" class="no-custom"><option value="zh-TW"${cfg.lang!=='en'?' selected':''}>繁體中文</option><option value="en"${cfg.lang==='en'?' selected':''}>English</option></select></div>
      <div class="form-group"><label>${t('reports_f_header')}</label><input type="text" id="rp-header" value="${esc(cfg.header_text||'')}" placeholder="機密"></div>
      ${_reportLogoField('rp-logo', cfg.logo_data_uri, 'logo-preview-cover', 'reports_f_logo', 'reports_logo_hint')}
      <div class="form-group"><label>${t('reports_f_logo_size')}</label><input type="number" id="rp-logo-size" min="20" max="200" step="2" value="${esc(String(cfg.logo_height_px||72))}" style="max-width:120px"> <span class="text-muted fs-08">px</span></div>
      ${_reportLogoField('rp-hlogo', cfg.header_logo_data_uri, 'logo-preview-dark', 'reports_f_hlogo_dark', 'reports_hlogo_dark_hint')}
      ${_reportLogoField('rp-hlogo2', cfg.header_logo_light_data_uri, '', 'reports_f_hlogo_light', 'reports_hlogo_light_hint')}
      <div class="form-group"><label class="inline-check"><input type="checkbox" id="rp-archive" ${cfg.include_archive_summary===true?'checked':''}> ${t('reports_f_archive')}</label></div>
      <hr class="u003">
      <div class="form-group"><label>${t('reports_f_server')}</label><select id="rp-server" class="no-custom" data-act-change="reportLoadDashboards"><option value="">-</option>${serverOpts}</select></div>
      <div class="form-group"><label>${t('reports_f_dashboards')}</label><div id="rp-dashboards" class="text-muted fs-085">${t('reports_pick_server')}</div></div>
      <div class="form-group"><label>${t('reports_f_mode')}</label>
        <select id="rp-mode" class="no-custom" data-act-change="reportToggleMode">
          <option value="rebuild"${cfg.dashboard_mode!=='screenshot'?' selected':''}>${t('reports_mode_rebuild')}</option>
          <option value="screenshot"${cfg.dashboard_mode==='screenshot'?' selected':''}>${t('reports_mode_shot')}</option>
        </select>
        <div class="text-muted fs-08 mt3" data-i18n="reports_mode_hint">${t('reports_mode_hint')}</div></div>
      <div class="form-group" id="rp-usedbtime-g"><label class="inline-check"><input type="checkbox" id="rp-usedbtime" ${cfg.use_dashboard_time!==false?'checked':''} data-act-change="reportToggleDbTime" data-act-self> ${t('reports_f_usedbtime')}</label>
        <div class="text-muted fs-08 mt3">${t('reports_usedbtime_hint')}</div></div>
      <div class="u037">
        <div class="form-group flex1${cfg.use_dashboard_time!==false?' hidden':''}" id="rp-hours-g"><label>${t('reports_f_hours')}</label><input type="text" id="rp-hours" value="${esc(String(Math.round((cfg.time_range_seconds||86400)/3600)))}" placeholder="24"></div>
        <div class="form-group flex1" id="rp-maxw-g"><label>${t('reports_f_maxw')}</label>${_mwSelect}</div>
      </div>
      <div id="rp-rebuild-opts">
        <div class="rp-grid3">
          <div class="form-group"><label>${t('reports_f_msgrows')}</label><input type="text" id="rp-msgrows" value="${esc(String(cfg.message_rows!==undefined?cfg.message_rows:20))}" placeholder="20"></div>
          <div class="form-group"><label>${t('reports_f_msgcols')}</label><input type="text" id="rp-msgcols" value="${esc(String(cfg.message_max_cols!==undefined?cfg.message_max_cols:8))}" placeholder="8"></div>
          <div class="form-group"><label>${t('reports_f_bardir')}</label>
            <select id="rp-bardir" class="no-custom">
              <option value="v"${cfg.bar_horizontal?'':' selected'}>${esc(t('reports_bar_vertical'))}</option>
              <option value="h"${cfg.bar_horizontal?' selected':''}>${esc(t('reports_bar_horizontal'))}</option>
            </select></div>
        </div>
        <div class="text-muted fs-08 mt3">${t('reports_msgcols_hint')}</div>
        <div class="form-group mt8"><label class="inline-check"><input type="checkbox" id="rp-heatval" ${cfg.heatmap_values===true?'checked':''}> ${t('reports_f_heatval')}</label>
          <div class="text-muted fs-08 mt3">${t('reports_heatval_hint')}</div></div>
      </div>
      <div id="rp-shot-creds"${cfg.dashboard_mode==='screenshot'?'':' class="hidden"'}>
        <div class="text-muted fs-08 mb8">${t('reports_web_note')}</div>
        <div class="form-group"><label>${t('reports_f_webuser')}</label><input type="text" id="rp-webuser" value="${esc(cfg.graylog_web_username||'')}" autocomplete="off" placeholder="${t('reports_web_hint')}"></div>
        <div class="form-group"><label>${t('reports_f_webpass')}</label>${_reportSecret('rp-webpass', cfg.graylog_web_password)}</div>
      </div>
      <hr class="u003">
      <div class="form-group"><label class="inline-check"><input type="checkbox" id="rp-wm-enabled" ${cfg.watermark_enabled?'checked':''} data-act-change="reportToggleWm" data-act-self> ${t('reports_f_wm')}</label></div>
      <div id="rp-wm-opts"${cfg.watermark_enabled?'':' class="hidden"'}>
        <div class="form-group"><label>${t('reports_f_wm_text')}</label><input type="text" id="rp-wm-text" value="${esc(cfg.watermark_text||'')}" placeholder="${esc(t('reports_wm_text_ph'))}"></div>
        <div class="rp-grid3">
          <div class="form-group"><label>${t('reports_f_wm_size')}</label>
            <select id="rp-wm-size" class="no-custom">
              <option value="small"${cfg.watermark_size==='small'?' selected':''}>${t('reports_wm_small')}</option>
              <option value="medium"${cfg.watermark_size==='medium'?' selected':''}>${t('reports_wm_medium')}</option>
              <option value="large"${(cfg.watermark_size||'large')==='large'?' selected':''}>${t('reports_wm_large')}</option>
            </select></div>
          <div class="form-group"><label>${t('reports_f_wm_dir')}</label>
            <select id="rp-wm-dir" class="no-custom">
              <option value="diagonal"${(cfg.watermark_direction||'diagonal')==='diagonal'?' selected':''}>${t('reports_wm_diagonal')}</option>
              <option value="horizontal"${cfg.watermark_direction==='horizontal'?' selected':''}>${t('reports_wm_horizontal')}</option>
            </select></div>
        </div>
        <div class="form-group"><label>${t('reports_f_wm_append')}</label>
          <div class="wm-append">
            ${['server','ip','time','dashboard','recipients'].map(k=>`<label class="inline-check"><input type="checkbox" class="rp-wm-ap" value="${k}" ${(cfg.watermark_append||[]).includes(k)?'checked':''}> ${t('reports_wm_ap_'+k)}</label>`).join('')}
          </div>
          <div class="text-muted fs-08 mt3">${t('reports_wm_hint')}</div></div>
      </div>
      <div class="form-group"><label>${t('reports_f_recipients')}</label><input type="text" id="rp-recipients" value="${esc((cfg.recipients||[]).join(', '))}" placeholder="a@x.com, b@y.com"></div>
      <div class="form-group"><label>${t('reports_f_cron')}</label>
        <select id="rp-cron-freq" class="no-custom" data-act-change="reportCronPreset">
          <option value="">${t('reports_cron_none')}</option>
          <option value="0 * * * *">${t('reports_cron_hourly')}</option>
          <option value="0 5 * * *">${t('reports_cron_daily')}</option>
          <option value="0 5 * * 1">${t('reports_cron_weekly')}</option>
          <option value="0 5 1 * *">${t('reports_cron_monthly')}</option>
          <option value="custom">${t('reports_cron_custom')}</option>
        </select>
        <input type="text" id="rp-cron" class="mt3" value="${esc(cfg.schedule_cron||'')}" placeholder="0 5 * * 1"></div>
      <div class="form-group"><label class="inline-check"><input type="checkbox" id="rp-align-midnight" ${cfg.align_midnight?'checked':''}> ${t('reports_f_align_midnight')}</label>
        <div class="text-muted fs-08 mt3">${t('reports_align_midnight_hint')}</div></div>
      <div class="form-group"><label class="inline-check"><input type="checkbox" id="rp-enabled" ${cfg.__enabled!==false?'checked':''}> ${t('reports_f_enabled')}</label></div>`;
    document.getElementById('report-modal-result').innerHTML = '';
    document.getElementById('report-modal').classList.remove('hidden');
    document.getElementById('report-modal').style.display = 'flex';
    _reportDashboards = cfg.dashboards || [];
    reportToggleMode(cfg.dashboard_mode || 'rebuild');
    reportCronInit(cfg.schedule_cron || '');
    _wireLogoDnD();
    if (_rpServer) reportLoadDashboards(_rpServer);
}

// Cron picker: presets fill the (advanced) text field; text field stays the
// single source of truth read by _gatherReport.
const _RP_CRON_PRESETS = ['', '0 * * * *', '0 5 * * *', '0 5 * * 1', '0 5 1 * *'];
function reportCronInit(cron) {
    const sel = document.getElementById('rp-cron-freq');
    const txt = document.getElementById('rp-cron');
    if (!sel || !txt) return;
    if (_RP_CRON_PRESETS.includes(cron)) {
        sel.value = cron;
        txt.classList.add('hidden');   // preset (incl. "none") controls it
    } else {
        sel.value = 'custom';
        txt.classList.remove('hidden');
    }
}
function reportCronPreset() {
    const sel = document.getElementById('rp-cron-freq');
    const txt = document.getElementById('rp-cron');
    if (!sel || !txt) return;
    if (sel.value === 'custom') { txt.classList.remove('hidden'); txt.focus(); }
    else { txt.value = sel.value; txt.classList.add('hidden'); }
}

// Cover logo: read the chosen image entirely client-side into a data URI stored
// in the report config (rendered on the cover; no backend upload needed).
// Generic logo picker (cover + header share this via a `data-lg` prefix).
function _applyLogoDataUri(prefix, uri) {
    document.getElementById(prefix).value = uri;
    const p = document.getElementById(prefix + '-prev');
    if (p) { p.src = uri; p.classList.remove('hidden'); }
    document.getElementById(prefix + '-ph')?.classList.add('hidden');
    document.getElementById(prefix + '-box')?.classList.remove('empty');
    document.getElementById(prefix + '-clear')?.classList.remove('hidden');
}

function _handleLogoFile(prefix, f) {
    if (!f) return;
    if (!/^image\//.test(f.type || '')) { showAlert(t('reports_logo_none')); return; }
    if (f.size > 3 * 1024 * 1024) { showAlert(t('reports_logo_too_big')); return; }
    const rd = new FileReader();
    rd.onload = e => _applyLogoDataUri(prefix, e.target.result);
    rd.readAsDataURL(f);
}

function reportLogoPick(el) {
    const prefix = (el && el.dataset && el.dataset.lg) || 'rp-logo';
    _handleLogoFile(prefix, document.getElementById(prefix + '-file')?.files?.[0]);
}

// Attach drag-and-drop to every logo preview box in the report modal.
function _wireLogoDnD() {
    document.querySelectorAll('#report-modal-form .logo-preview-box').forEach(box => {
        if (box._dndWired) return;
        box._dndWired = true;
        const prefix = box.id.replace(/-box$/, '');
        box.addEventListener('dragover', e => { e.preventDefault(); box.classList.add('logo-drag'); });
        box.addEventListener('dragleave', () => box.classList.remove('logo-drag'));
        box.addEventListener('drop', e => {
            e.preventDefault();
            box.classList.remove('logo-drag');
            _handleLogoFile(prefix, e.dataTransfer?.files?.[0]);
        });
    });
}
function reportLogoClear(prefix) {
    prefix = prefix || 'rp-logo';
    const h = document.getElementById(prefix); if (h) h.value = '';
    const p = document.getElementById(prefix + '-prev'); if (p) { p.src = ''; p.classList.add('hidden'); }
    const f = document.getElementById(prefix + '-file'); if (f) f.value = '';
    document.getElementById(prefix + '-ph')?.classList.remove('hidden');
    document.getElementById(prefix + '-box')?.classList.add('empty');
    document.getElementById(prefix + '-clear')?.classList.add('hidden');
}

// One tidy logo picker (preview box + a styled choose button + clear). bgClass
// sets the preview backdrop so you can judge the logo against where it'll sit:
// '' = light, 'logo-preview-cover' = brand cover, 'logo-preview-dark' = dark band.
function _reportLogoField(prefix, value, bgClass, labelKey, hintKey) {
    const has = !!value;
    return `<div class="form-group">
      <label>${t(labelKey)}</label>
      <div class="logo-field">
        <div class="logo-preview-box ${bgClass}${has?'':' empty'}" id="${prefix}-box">
          <img id="${prefix}-prev" class="report-logo-prev${has?'':' hidden'}" src="${esc(value||'')}" alt="">
          <span class="logo-placeholder${has?' hidden':''}" id="${prefix}-ph">${esc(t('reports_logo_none'))}</span>
        </div>
        <div class="logo-controls">
          <label class="logo-pick-btn">${icon('upload',14)} <span>${esc(t('reports_logo_choose'))}</span>
            <input type="file" id="${prefix}-file" accept="image/png,image/jpeg,image/svg+xml" data-act-change="reportLogoPick" data-act-self data-lg="${prefix}"></label>
          <button type="button" class="logo-clear-btn${has?'':' hidden'}" id="${prefix}-clear" data-act="reportLogoClear" data-arg="${prefix}">${icon('close',14)} ${esc(t('reports_logo_clear'))}</button>
        </div>
      </div>
      <input type="hidden" id="${prefix}" value="${esc(value||'')}">
      <div class="text-muted fs-08 mt3">${t(hintKey)}</div>
    </div>`;
}

function closeReportModal() { const m = document.getElementById('report-modal'); m.classList.add('hidden'); m.style.display = 'none'; }

async function reportLoadDashboards(server) {
    const el = document.getElementById('rp-dashboards');
    if (!server) { el.innerHTML = `<div class="load-block">${esc(t('reports_pick_server'))}</div>`; return; }
    el.innerHTML = `<div class="load-block"><span class="spinner-text">${esc(t('loading'))}...</span></div>`;
    const r = await fetchJSON(`${API}/reports/dashboards?server=${encodeURIComponent(server)}`);
    const items = r.items || [];
    const chosen = new Set((_reportDashboards || []).map(d => d.id || d));
    _reportDashTabs = {};
    (_reportDashboards || []).forEach(d => { if (d && d.id) _reportDashTabs[d.id] = d.tabs || (d.tab ? [d.tab] : []); });
    if (!items.length) { el.innerHTML = `<div class="load-block">${esc(t('reports_no_dash'))}</div>`; return; }
    el.innerHTML = items.map(d => `
      <div class="rp-dash-block">
        <label class="inline-check u113 rp-dash-row"><input type="checkbox" class="rp-dash" value="${esc(d.id)}" data-title="${esc(d.title)}" data-act-change="reportDashToggle" data-act-self ${chosen.has(d.id) ? 'checked' : ''}> ${esc(d.title)}</label>
        <div class="rp-dash-tabs hidden" data-id="${esc(d.id)}"></div>
      </div>`).join('');
    // Populate the tab checkboxes for any pre-selected (multi-tab) dashboards.
    items.forEach(d => { if (chosen.has(d.id)) _populateDashTabs(d.id); });
}

async function reportDashToggle(el) {
    const box = document.querySelector('.rp-dash-tabs[data-id="' + el.value + '"]');
    if (el.checked) { await _populateDashTabs(el.value); }
    else if (box) { box.classList.add('hidden'); box.innerHTML = ''; }
}

// Fetch a dashboard's tabs; show a multi-select checklist only when it has >1
// tab. No tab checked = all tabs. Each checked tab becomes its own report section.
async function _populateDashTabs(id) {
    const server = document.getElementById('rp-server')?.value;
    const box = document.querySelector('.rp-dash-tabs[data-id="' + id + '"]');
    if (!server || !box) return;
    const r = await fetchJSON(`${API}/reports/dashboard-tabs?server=${encodeURIComponent(server)}&id=${encodeURIComponent(id)}`);
    const tabs = r.items || [];
    if (tabs.length <= 1) { box.classList.add('hidden'); box.innerHTML = ''; return; }
    const cur = new Set(_reportDashTabs[id] || []);
    box.innerHTML = `<div class="rp-tabs-hint">${esc(t('reports_tabs_hint'))}</div>` +
        tabs.map((tb, i) => `<label class="inline-check fs-08"><input type="checkbox" class="rp-tab" data-dash="${esc(id)}" value="${esc(tb.id)}"${cur.has(tb.id) ? ' checked' : ''}> ${esc(tb.title || (t('reports_tab') + ' ' + (i + 1)))}</label>`).join('');
    box.classList.remove('hidden');
}

function reportToggleDbTime(el) {
    // When "use dashboard time" is on, the manual hours override is hidden.
    document.getElementById('rp-hours-g')?.classList.toggle('hidden', !!el.checked);
}

function reportToggleMode(mode) {
    const shot = mode === 'screenshot';
    const creds = document.getElementById('rp-shot-creds');
    const maxwg = document.getElementById('rp-maxw-g');
    const rebuildOpts = document.getElementById('rp-rebuild-opts');
    const usedbG = document.getElementById('rp-usedbtime-g');
    const hoursG = document.getElementById('rp-hours-g');
    const heatvalG = document.getElementById('rp-heatval-g');
    if (creds) creds.classList.toggle('hidden', !shot);
    if (maxwg) maxwg.classList.toggle('hidden', shot);
    // Message-rows + bar-direction + heatmap-values are rebuild-only (screenshot
    // renders the native dashboard as-is), as is the per-widget-time toggle.
    if (rebuildOpts) rebuildOpts.classList.toggle('hidden', shot);
    if (usedbG) usedbG.classList.toggle('hidden', shot);
    if (heatvalG) heatvalG.classList.toggle('hidden', shot);
    // Screenshot always needs an explicit capture window → force the hours field
    // visible; in rebuild it follows the use-dashboard-time checkbox.
    if (hoursG) {
        const useDb = document.getElementById('rp-usedbtime')?.checked;
        hoursG.classList.toggle('hidden', shot ? false : (useDb !== false));
    }
}

function reportToggleWm(on) {
    const opts = document.getElementById('rp-wm-opts');
    if (opts) opts.classList.toggle('hidden', !document.getElementById('rp-wm-enabled')?.checked);
}

function _gatherReport() {
    const v = id => (document.getElementById(id)?.value || '').trim();
    const ck = id => !!document.getElementById(id)?.checked;
    const dashboards = Array.from(document.querySelectorAll('.rp-dash:checked')).map(c => {
        const tabs = Array.from(document.querySelectorAll('.rp-tab[data-dash="' + c.value + '"]:checked')).map(x => x.value);
        return {id: c.value, title: c.dataset.title, tabs};
    });
    const hours = parseInt(v('rp-hours'), 10);
    const maxw = parseInt(v('rp-maxw'), 10);
    const msgrows = parseInt(v('rp-msgrows'), 10);
    const msgcols = parseInt(v('rp-msgcols'), 10);
    const rid = v('rp-id');
    return {
        id: rid === '' ? null : rid,
        name: v('rp-name'),
        enabled: ck('rp-enabled'),
        config: {
            title: v('rp-title'), subtitle: v('rp-subtitle'), author: v('rp-author'),
            lang: v('rp-lang'), header_text: v('rp-header'),
            include_archive_summary: ck('rp-archive'),
            server: v('rp-server'), dashboards,
            dashboard_mode: v('rp-mode') || 'rebuild',
            time_range_seconds: (isNaN(hours) ? 24 : hours) * 3600,
            max_widgets: isNaN(maxw) ? 0 : maxw,
            graylog_web_username: v('rp-webuser'), graylog_web_password: v('rp-webpass'),
            recipients: v('rp-recipients').split(',').map(s => s.trim()).filter(Boolean),
            watermark_enabled: ck('rp-wm-enabled'),
            watermark_text: v('rp-wm-text'),
            watermark_size: v('rp-wm-size') || 'large',
            watermark_direction: v('rp-wm-dir') || 'diagonal',
            watermark_append: Array.from(document.querySelectorAll('.rp-wm-ap:checked')).map(x => x.value),
            align_midnight: ck('rp-align-midnight'),
            schedule_cron: v('rp-cron'),
            logo_data_uri: v('rp-logo'),
            logo_height_px: Math.max(20, Math.min(200, parseInt(v('rp-logo-size'), 10) || 72)),
            header_logo_data_uri: v('rp-hlogo'),
            header_logo_light_data_uri: v('rp-hlogo2'),
            message_rows: isNaN(msgrows) ? 20 : msgrows,
            message_max_cols: isNaN(msgcols) ? 8 : msgcols,
            bar_horizontal: v('rp-bardir') === 'h',
            heatmap_values: ck('rp-heatval'),
            use_dashboard_time: ck('rp-usedbtime'),
        },
    };
}

async function saveReport() {
    const body = _gatherReport();
    if (!body.name) { document.getElementById('report-modal-result').innerHTML = `<span class="err-text">${t('reports_f_name')}</span>`; return; }
    const r = await fetchJSON(`${API}/reports`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    if (r.error) { document.getElementById('report-modal-result').innerHTML = `<span class="err-text">${esc(r.error)}</span>`; return; }
    closeReportModal(); loadReportsPage();
}

function deleteReport(name) {
    showConfirm(t('reports_edit'), t('reports_confirm_delete').replace('{name}', name), async () => {
        const r = await fetchJSON(`${API}/reports/${encodeURIComponent(name)}`, {method:'DELETE'});
        if (r.error) { showAlert(r.error); return; }
        loadReportsPage();
    });
}

// Duplicate a report definition; auto-name "<name> - (N)" avoiding collisions.
async function duplicateReport(name) {
    const list = await fetchJSON(`${API}/reports`);
    const items = list.items || [];
    const src = items.find(x => x.name === name);
    if (!src) return;
    const existing = new Set(items.map(x => x.name));
    let i = 1, newName;
    do { newName = `${name} - (${i})`; i++; } while (existing.has(newName));
    const cfg = JSON.parse(JSON.stringify(src.config || {}));
    cfg.name = newName;
    // Masked secrets (***) from the list can't be copied — clear so they're re-entered.
    if (typeof cfg.graylog_web_password === 'string' && cfg.graylog_web_password.includes('*')) cfg.graylog_web_password = '';
    const r = await fetchJSON(`${API}/reports`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: newName, enabled: src.enabled, config: cfg}),
    });
    if (r.error) { showAlert(r.error); return; }
    loadReportsPage();
}

async function generateReport(name) {
    const r = await fetchJSON(`${API}/reports/${encodeURIComponent(name)}/generate`, {method:'POST'});
    if (r.error) { showAlert(r.error); return; }
    showAlert(t('reports_started'));
    setTimeout(loadReportsPage, 4000);
    setTimeout(loadReportsPage, 12000);
}

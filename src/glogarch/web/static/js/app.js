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
    if (tbody) tbody.innerHTML = `<tr><td colspan="20" style="text-align:center;color:var(--text-muted);padding:20px"><span class="spinner-text">${t('loading')}...</span></td></tr>`;
    try {
        await asyncFn();
        if (tbody && tbody.innerHTML.includes('spinner-text')) {
            tbody.innerHTML = `<tr><td colspan="20" style="text-align:center;color:var(--text-muted);padding:20px">${t('log_no_data')}</td></tr>`;
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="20" style="text-align:center;color:var(--danger);padding:20px">${t('load_failed')}</td></tr>`;
    }
    initTableSort();
}

/** Replace native alert with custom modal */
function showAlert(msg) {
    showConfirm('', msg, null);
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

function formatRecords(done, total) {
    const d = formatNumber(done);
    if (!total) return d;
    const t_ = formatNumber(total);
    return `<span style="white-space:nowrap"><strong>${d}</strong> <span style="color:var(--text-muted);font-size:0.8em;opacity:0.7">of</span> <span style="color:var(--text-muted);font-size:0.9em">${t_}</span></span>`;
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
    };
    const labels = {
        corrupted: 'SHA256 損壞',
        missing: '檔案遺失',
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

    try {
        const servers = await fetchJSON(`${API}/servers`);
        const tbody = document.querySelector('#servers-table tbody');
        tbody.innerHTML = servers.items.map(s => `
            <tr>
                <td>${esc(s.name)}</td>
                <td>${esc(s.url)}</td>
                <td>${s.connected ? statusBadge('completed') : statusBadge('failed')}</td>
                <td>${s.version || '-'}</td>
            </tr>
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
            if (sm === 'api') badges += '<span class="job-badge" style="background:rgba(76,175,80,0.1);color:var(--success)">API</span>';
            else if (sm === 'opensearch') badges += '<span class="job-badge" style="background:rgba(255,152,0,0.1);color:var(--warning)">OS</span>';
            else if (st && !sm) badges += '<span class="job-badge" style="background:rgba(76,175,80,0.1);color:var(--success)">API</span>';
            const isDim = j.status === 'completed' && j.messages_done === 0 && !j.error_message;
            return `
            <tr class="${isDim ? 'job-row-dim' : ''}">
                <td title="${j.id}">${j.id.substring(0, 8)}</td>
                <td>${j.job_type} ${badges}</td>
                <td>${statusBadge(j.status, j.error_message)}</td>
                <td>${j.progress_pct.toFixed(0)}%</td>
                <td style="text-align:right">${isDim ? '<span style="color:var(--text-muted);font-size:0.85em">' + t('job_no_new_data') + '</span>' : formatRecords(j.messages_done, j.messages_total)}</td>
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
        const data = await fetchJSON(`${API}/opensearch/status`);
        const el = document.getElementById('opensearch-info');
        if (!el) return;
        if (data.configured) {
            const labels = data.hosts.map((h, i) => {
                const isPrimary = i === 0;
                const badge = isPrimary ? ` <span style="font-size:0.7em;color:var(--success)">&#9679; Primary</span>` : '';
                return `<span class="host-label" oncontextmenu="showHostMenu(event,${i},${isPrimary})" title="${t('os_right_click')}">${icon('server')} ${esc(h)}${badge}</span>`;
            }).join(' ');
            el.innerHTML = labels;
        } else {
            el.innerHTML = `<span style="color:var(--warning)">${t('opensearch_not_configured')}</span>`;
        }
    } catch (e) {}
}

function showHostMenu(e, idx, isPrimary) {
    e.preventDefault();
    // Remove existing menu
    const old = document.getElementById('host-context-menu');
    if (old) old.remove();

    const menu = document.createElement('div');
    menu.id = 'host-context-menu';
    menu.className = 'context-menu';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';

    let items = '';
    if (!isPrimary) {
        items += `<div class="context-menu-item" onclick="osSetPrimary(${idx})">${icon('shield')} ${t('os_set_primary')}</div>`;
    }
    items += `<div class="context-menu-item" onclick="osTestSingle(${idx})">${icon('refresh')} ${t('btn_test_connection')}</div>`;
    if (isPrimary) {
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

async function osSetPrimary(idx) {
    try {
        await fetchJSON(`${API}/opensearch/reorder`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({from_index: idx, to_index: 0}),
        });
        loadOpenSearchStatus();
    } catch (e) {
        const el = document.getElementById('opensearch-result');
        if (el) el.innerHTML = `<span class="status-failed">${e.message}</span>`;
    }
}

async function osTestSingle(idx) {
    const resultEl = document.getElementById('opensearch-result');
    try {
        const data = await fetchJSON(`${API}/opensearch/status`);
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
    resultEl.innerHTML = '<span style="color:var(--text-muted)">Testing...</span>';
    try {
        const data = await fetchJSON(`${API}/opensearch/test`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}',
        });
        if (data.connected) {
            resultEl.innerHTML = `<span class="status-completed">Connected!</span> ${data.cluster_name || ''} — ${data.version || ''} — Status: ${data.status || ''} — Nodes: ${data.nodes || ''}`;
        } else {
            resultEl.innerHTML = `<span class="status-failed">Failed:</span> ${data.error || 'Unknown error'}`;
        }
    } catch (e) {
        resultEl.innerHTML = `<span class="status-failed">Error:</span> ${e.message}`;
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
            el.innerHTML = `<span style="color:var(--warning)">${t('no_channels')}</span>`;
            if (btn) { btn.disabled = true; btn.style.opacity = '0.4'; btn.style.cursor = 'not-allowed'; }
        }
    } catch (e) {}
}

async function testNotify() {
    const el = document.getElementById('notify-result');
    el.innerHTML = '<span style="color:var(--text-muted)">Sending...</span>';
    try {
        const data = await fetchJSON(`${API}/notify/test`, {method: 'POST'});
        if (data.results && data.results.length > 0) {
            const lines = data.results.map(r =>
                `${esc(r.channel)}: ${r.success ? '<span class="status-completed">' + t('notify_sent') + '</span>' : '<span class="status-failed">' + esc(r.error || 'Failed') + '</span>'}`
            );
            el.innerHTML = lines.join('<br>');
        } else {
            el.innerHTML = `<span style="color:var(--warning)">${t('notify_no_channels')}</span>`;
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
    if (tbody) tbody.innerHTML = `<tr><td colspan="20" style="text-align:center;padding:20px"><span class="spinner-text">${t('loading')}...</span></td></tr>`;
    try { await _loadArchivesInner(page); } catch(e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="20" style="text-align:center;color:var(--danger)">${t('load_failed')}</td></tr>`;
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

    const data = await fetchJSON(`${API}/archives?${params}`);
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
            <td><input type="checkbox" class="archive-check" value="${a.id}" onchange="onArchiveCheckChange()"></td>
            <td class="col-id">${a.id}</td>
            <td class="col-server">${esc(a.server_name)}</td>
            <td class="col-stream">${esc(a.stream_id && a.stream_id.match(/^[a-z]+_\d+$/) ? a.stream_id : (_sn[a.stream_id] || a.stream_name || (a.stream_id ? a.stream_id.substring(0,8) + '...' : 'all')))}</td>
            <td class="col-from">${formatDT(a.time_from)}</td>
            <td class="col-to">${formatDT(a.time_to)}</td>
            <td class="col-records" style="text-align:right">${formatNumber(a.message_count)}</td>
            <td class="col-compressed" style="text-align:right">${formatBytes(a.file_size_bytes)}</td>
            <td class="col-original" style="text-align:right">${a.original_size_bytes ? formatBytes(a.original_size_bytes) : '~' + formatBytes(a.file_size_bytes * 8)}</td>
            <td class="col-status">${statusBadge(a.status)}</td>
            <td class="col-filename" style="font-size:0.8em;word-break:break-all">${esc((a.file_path || '').split('/').pop())}</td>
            <td class="col-actions" style="white-space:nowrap">
                <button class="btn-sm btn-primary" onclick="importSingle(${a.id})" data-i18n="btn_import">Import</button>
                <button class="btn-sm btn-danger" onclick="deleteArchive(${a.id})" data-i18n="btn_delete">Delete</button>
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

        let html = `<button ${cur === 1 ? 'disabled' : ''} onclick="loadArchives(${cur - 1})">&laquo;</button>`;
        pages.forEach(p => {
            if (p === '...') { html += `<span style="padding:0 6px;color:var(--text-muted)">...</span>`; }
            else { html += `<button class="${p === cur ? 'active' : ''}" onclick="loadArchives(${p})">${p}</button>`; }
        });
        html += `<button ${cur === totalPages ? 'disabled' : ''} onclick="loadArchives(${cur + 1})">&raquo;</button>`;
        html += `<span style="margin-left:10px;color:var(--text-muted);font-size:0.85em">${data.total} ${t('nav_archives').toLowerCase()}</span>`;
        pag.innerHTML = html;
    } else if (pag) {
        pag.innerHTML = data.total ? `<span style="color:var(--text-muted);font-size:0.85em">${data.total} ${t('nav_archives').toLowerCase()}</span>` : '';
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

let _selectAllPages = false;
let _selectAllTotal = 0;

function toggleArchiveSelectAll(el, evt) {
    if (evt && evt.shiftKey && el.checked) {
        _selectAllPages = true;
        document.querySelectorAll('.archive-check').forEach(cb => cb.checked = true);
        // Fetch total count
        fetchJSON(`${API}/archives?page_size=1`).then(data => {
            _selectAllTotal = data.total || 0;
            onArchiveCheckChange();
        });
    } else {
        _selectAllPages = false;
        _selectAllTotal = 0;
        document.querySelectorAll('.archive-check').forEach(cb => cb.checked = el.checked);
    }
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
            const total = _selectAllTotal || '...';
            count.innerHTML = `<strong style="color:var(--warning)">${total} ${t('select_all_pages')}</strong>`;
        } else {
            count.textContent = `${checked.length} ${t('btn_selected')}`;
        }
    }
    if (!checked.length) _selectAllPages = false;
}

async function getSelectedArchiveIds() {
    if (_selectAllPages) {
        // Fetch ALL archive IDs across all pages
        let allIds = [];
        let page = 1;
        while (true) {
            const data = await fetchJSON(`${API}/archives?page=${page}&page_size=500`);
            if (!data.items || data.items.length === 0) break;
            allIds = allIds.concat(data.items.map(a => a.id));
            if (allIds.length >= (data.total || 0)) break;
            page++;
        }
        return allIds;
    }
    return Array.from(document.querySelectorAll('.archive-check:checked')).map(c => parseInt(c.value));
}

async function batchImport() {
    const ids = await getSelectedArchiveIds();
    if (ids.length === 0) return;
    // Open import modal for batch
    _importArchiveId = null;
    const modal = document.getElementById('import-modal');
    document.getElementById('modal-import-result').innerHTML = '';
    modal.style.display = 'flex';
    // Override doImportSingle for batch
    window._batchImportIds = ids;
    applyI18n();
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
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:10px">
            <div style="font-size:0.95em;font-weight:500;color:var(--text-label);white-space:nowrap">${icon('clock')} ${t('archive_timeline')} <span style="color:var(--text-muted);font-weight:normal">(${totalDays} ${t('export_days')})</span></div>
            <div id="tl-tooltip" style="font-size:0.85em;color:var(--text-muted);min-height:1.2em;flex:1;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-variant-numeric:tabular-nums">${t('tl_drag_hint')}</div>
            <button id="tl-clear" onclick="clearTimelineSelection()" style="visibility:hidden;background:var(--danger);color:white;border:none;padding:3px 10px;border-radius:4px;font-size:0.75em;cursor:pointer;flex-shrink:0">${t('tl_clear')}</button>
        </div>
        <div style="position:relative">
            <svg id="tl-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:70px;background:var(--input-bg);border:1px solid var(--border);border-radius:6px;display:block;cursor:crosshair">
                ${bars}
                <rect id="tl-selection" x="0" y="0" width="0" height="${h}" fill="var(--accent)" opacity="0.2" pointer-events="none" style="display:none"/>
                <line id="tl-cursor" x1="0" y1="0" x2="0" y2="${h}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3,3" opacity="0.7" pointer-events="none" style="display:none"/>
            </svg>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.8em;color:var(--text-muted);margin-top:6px">
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
                tooltip.innerHTML = `<strong>${dayStr}</strong> · <span style="color:var(--danger)">${t('tl_no_data')}</span>`;
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
            tooltip.innerHTML = `<strong style="color:var(--accent)">${fmtShortH(from)} ~ ${fmtShortH(to)}</strong> ${t('tl_filtering')}`;
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
            <div class="form-hint" style="margin-top:6px;white-space:pre-line">${msg}</div>`;
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
    el.innerHTML = `<span style="color:var(--text-muted)" class="spinner-text">${t('loading')}...</span>`;
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
    } else {
        // bulk mode
        body.target_index_pattern = document.getElementById('modal-bulk-index-pattern')?.value?.trim() || 'jt_restored';
        body.dedup_strategy = document.getElementById('modal-bulk-dedup')?.value || 'id';
        body.batch_docs = parseInt(document.getElementById('modal-bulk-batch-docs')?.value || '5000');
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
        // Hide GELF-only controls (pause + speed slider) when running bulk:
        // bulk has no inter-batch delay and pause is not honored by the bulk
        // loop, so the controls would just confuse the user.
        const gelfControls = document.getElementById('import-gelf-controls');
        if (gelfControls) gelfControls.style.display = (mode === 'bulk') ? 'none' : 'flex';
        // Set live rate slider
        const liveRate = document.getElementById('import-live-rate');
        if (liveRate) { liveRate.value = rateMs; document.getElementById('import-live-rate-display').textContent = rateMs + 'ms'; }

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
    try {
        await fetchJSON(`${API}/jobs/${_activeImportJobId}/cancel`, {method: 'POST'});
    } catch (e) {
        showAlert(t('error') + ': ' + (e && e.message ? e.message : e));
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
    document.getElementById('import-live-rate-display').textContent = val + 'ms';
    if (!_activeImportJobId) return;
    await fetchJSON(`${API}/import/${_activeImportJobId}/rate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate_ms: parseInt(val)}),
    });
}

let _importStatusPoll = null;
function startImportStatusPoll(jobId) {
    stopImportStatusPoll();
    _importStatusPoll = setInterval(async () => {
        if (!_activeImportJobId) { stopImportStatusPoll(); return; }
        try {
            const st = await fetchJSON(`${API}/import/${jobId}/status`);
            const badge = document.getElementById('import-journal-badge');
            if (badge && st.journal) {
                badge.style.display = 'inline';
                const u = st.journal.uncommitted;
                const action = st.journal_action;
                const color = action === 'normal' ? 'var(--success)' : action === 'slow' ? 'var(--warning)' : 'var(--danger)';
                const label = t('import_journal_label');
                const actionLabel = t(`import_journal_${action}`) || action;
                badge.innerHTML = `<span style="color:${color}">${label}: ${u !== null ? formatNumber(u) : '?'} (${actionLabel})</span>`;
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

    // Load servers
    try {
        const status = await fetchJSON(`${API}/status`);
        const sel = document.getElementById('export-server');
        if (sel) {
            sel.innerHTML = status.servers.map(s => `<option value="${s.name}">${s.name} (${s.url})</option>`).join('');
        }
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
    if (div) div.innerHTML = `<span style="color:var(--text-muted)">${icon('refresh')} ${t('loading')}...</span>`;
    try {
        const data = await fetchJSON(`${API}/streams`);
        if (div && data.items) {
            div.innerHTML = data.items.map(s =>
                `<label><input type="checkbox" class="export-stream-check" value="${s.id}"> ${s.title || s.id}</label>`
            ).join('');
        }
    } catch (e) {
        if (div) div.innerHTML = `<span style="color:var(--danger)">${t('load_failed')}</span>`;
    }
}

// System index prefixes to exclude
const SYSTEM_INDEX_PREFIXES = ['gl-events', 'gl-system-events', 'gl-failures', 'investigation_', 'restored-archive'];

async function loadExportIndexSets() {
    const sel = document.getElementById('export-indexset');
    if (sel) sel.innerHTML = `<option>${t('loading')}...</option>`;
    try {
        const data = await fetchJSON(`${API}/index-sets`);
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
        const data = await fetchJSON(`${API}/index-sets`);
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
        hint.textContent = mode === 'api' ? t('export_mode_api_hint') : t('export_mode_os_hint');
        hint.style.color = mode === 'opensearch' ? 'var(--warning)' : '';
    }
    // OpenSearch: hide time range selector, show index picker in coverage
    if (rangeGroup) rangeGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (daysGroup) daysGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (customGroup) customGroup.style.display = 'none';
    if (coverage) {
        coverage.style.display = 'block';
        if (mode === 'opensearch') {
            loadOsCoverage(coverage);
        } else {
            loadApiCoverage(coverage);
        }
    }
}

async function loadApiCoverage(el) {
    el.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;
    try {
        const status = await fetchJSON(`${API}/status`);
        const stats = status.archive_stats || {};
        if (!stats.earliest || !stats.latest) {
            el.innerHTML = `<div class="coverage-box"><span style="color:var(--text-muted)">${t('log_no_data')}</span></div>`;
            return;
        }

        const earliest = new Date(stats.earliest);
        const latest = new Date(stats.latest);
        const now = new Date();
        const totalSpan = now - earliest || 1;

        let html = '<div class="coverage-box">';
        html += `<div style="font-size:0.85em;margin-bottom:8px;color:var(--text-label)">${icon('archive')} ${t('api_coverage_title')}</div>`;

        // Timeline bar
        html += '<div class="timeline-bar" style="height:24px">';
        // Archived range
        const archivedWidth = ((latest - earliest) / totalSpan) * 100;
        html += `<div class="timeline-segment" style="left:0;width:${archivedWidth}%;background:var(--success);opacity:0.7" title="${t('api_archived')}"></div>`;
        // Gap (not yet archived)
        if (latest < now) {
            const gapLeft = archivedWidth;
            const gapWidth = 100 - archivedWidth;
            html += `<div class="timeline-segment" style="left:${gapLeft}%;width:${gapWidth}%;background:var(--danger);opacity:0.3" title="${t('api_not_archived')}"></div>`;
        }
        html += '</div>';

        // Labels — positioned to match timeline bar
        const fmtShort = (iso) => { const d = new Date(iso); const p = n => String(n).padStart(2,'0'); return `${d.getFullYear()}/${p(d.getMonth()+1)}/${p(d.getDate())}`; };
        html += '<div style="position:relative;font-size:0.8em;color:var(--text-muted);margin-top:3px;height:2.4em">';
        html += `<span style="position:absolute;left:0">${t('api_earliest')}<br>${fmtShort(stats.earliest)}</span>`;
        // Position "latest" label at the end of the green bar
        const latestPos = Math.min(archivedWidth, 85); // cap so it doesn't overlap "now"
        html += `<span style="position:absolute;left:${latestPos}%;transform:translateX(-50%);text-align:center;font-weight:600;color:var(--success)">${t('api_latest')}<br>${fmtShort(stats.latest)}</span>`;
        html += `<span style="position:absolute;right:0;text-align:right">${t('api_now')}</span>`;
        html += '</div>';

        // Stats
        html += `<div style="display:flex;gap:15px;margin-top:8px;font-size:0.8em;color:var(--text-muted)">`;
        html += `<span><span style="display:inline-block;width:10px;height:10px;background:var(--success);border-radius:2px;margin-right:3px;opacity:0.7"></span>${t('api_archived')}: ${formatNumber(stats.total)} ${t('nav_archives').toLowerCase()}, ${formatNumber(stats.total_messages)} ${t('th_messages').toLowerCase()}</span>`;
        if (latest < now) {
            const gapHours = Math.round((now - latest) / 3600000);
            html += `<span><span style="display:inline-block;width:10px;height:10px;background:var(--danger);border-radius:2px;margin-right:3px;opacity:0.3"></span>${t('api_not_archived')}: ~${gapHours}h</span>`;
        }
        html += '</div>';

        html += '</div>';
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = `<div class="coverage-box" style="color:var(--danger)">${t('load_failed')}</div>`;
    }
}

async function loadOsCoverage(el) {
    el.innerHTML = `<span class="spinner-text">${t('loading')}...</span>`;
    try {
        // Use selected index set prefix if available
        const isetSel = document.getElementById('export-indexset') || document.getElementById('sched-indexset');
        const selectedOpt = isetSel?.selectedOptions?.[0];
        const prefix = selectedOpt?.getAttribute('data-prefix') || '';
        const qs = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
        const osData = await fetchJSON(`${API}/opensearch/indices${qs}`);
        if (!osData.indices || osData.indices.length === 0) {
            el.innerHTML = `<div class="coverage-box"><span style="color:var(--danger)">${t('os_no_indices')}</span></div>`;
            return;
        }

        const indices = osData.indices;
        const active = osData.active_index || '';

        // Build timeline
        let html = '<div class="coverage-box">';
        html += `<div style="font-size:0.85em;margin-bottom:8px;color:var(--text-label)">${icon('db')} ${t('os_available_indices')} (${indices.length})</div>`;
        html += '<div class="coverage-timeline">';

        // Find time range
        const allDates = indices.filter(i => i.min_ts && i.max_ts);
        if (allDates.length === 0) {
            html += `<span style="color:var(--text-muted)">${t('os_no_time_data')}</span>`;
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
                html += `<div class="timeline-segment" style="left:${left}%;width:${width}%;background:${color}" title="${label}"></div>`;
            });

            html += '</div>';

            // Index list (read-only display)
            const exportable = allDates.filter(i => i.index !== active);
            html += `<div class="os-index-list" style="margin-top:8px">`;
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
            html += `<div style="margin-top:12px;padding:10px 12px;background:rgba(108,99,255,0.08);border:1px solid var(--accent);border-radius:6px">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                    <label style="font-size:0.95em;font-weight:500;color:var(--text)">${icon('archive')} ${t('os_keep_recent')}</label>
                    <input type="number" id="os-keep-n" value="${exportable.length}" min="1"
                        style="width:70px;padding:6px 10px;border:2px solid var(--accent);border-radius:6px;background:var(--input-bg);color:var(--text);font-size:1.1em;font-weight:bold;text-align:center">
                    <span style="font-size:0.9em;color:var(--text-muted)"> ${t('os_of_exportable').replace('{n}', exportable.length)}</span>
                </div>
                <small class="form-hint" style="margin-top:6px;display:block">${t('os_keep_recent_hint')}</small>
            </div>`;

            // Legend
            html += '<div style="display:flex;gap:15px;margin-top:6px;font-size:0.8em;color:var(--text-muted)">';
            html += `<span><span style="display:inline-block;width:10px;height:10px;background:var(--accent);border-radius:2px;margin-right:3px"></span>${t('os_exportable')}</span>`;
            html += `<span><span style="display:inline-block;width:10px;height:10px;background:var(--warning);border-radius:2px;margin-right:3px"></span>${t('os_active_skip')}</span>`;
            html += `<span style="color:var(--danger)">${t('os_not_available')}</span>`;
            html += '</div>';
        }

        html += '</div></div>';
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = `<div class="coverage-box" style="color:var(--danger)">${t('load_failed')}</div>`;
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
    const btn = document.querySelector('[onclick="startExport()"]');
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
                        if (text) text.innerHTML = `<span style="color:var(--warning)">${t('export_no_data')}</span>`;
                    } else {
                        if (text) text.innerHTML = `<span class="status-completed">${t('progress_completed')} (${formatNumber(job.messages_done)} ${t('th_messages').toLowerCase()})</span>`;
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
async function loadJobs() {
    const tbody = document.querySelector('#jobs-table tbody');
    if (!tbody) return;
    const data = await fetchJSON(`${API}/jobs?limit=100`);
    if (!data.items) return;
    tbody.innerHTML = data.items.map(j => {
        const isRunning = j.status === 'running' || j.status === 'pending';
        const cancelBtn = isRunning
            ? `<button class="btn-sm btn-danger" onclick="cancelJob('${j.id}')" data-i18n="btn_cancel">Cancel</button>`
            : '';
        // Records display with context
        let recordsHtml;
        if (j.status === 'completed' && j.messages_done === 0 && !j.error_message) {
            recordsHtml = `<span style="color:var(--text-muted);font-size:0.85em">${t('job_no_new_data')}</span>`;
        } else {
            recordsHtml = formatRecords(j.messages_done, j.messages_total);
        }

        // Source + mode badges
        const srcParts = (j.source || '').split(':');
        const srcType = srcParts[0] || '';
        const srcMode = srcParts[1] || '';
        let srcHtml = '';
        if (srcType === 'scheduled') srcHtml += `<span class="job-badge job-badge-sched">${t('job_scheduled')}</span> `;
        else if (srcType === 'manual') srcHtml += `<span class="job-badge job-badge-manual">${t('job_manual')}</span> `;
        if (srcMode === 'api') srcHtml += `<span class="job-badge" style="background:rgba(76,175,80,0.1);color:var(--success)">API</span>`;
        else if (srcMode === 'opensearch') srcHtml += `<span class="job-badge" style="background:rgba(255,152,0,0.1);color:var(--warning)">OpenSearch</span>`;
        else if (srcType && !srcMode) srcHtml += `<span class="job-badge" style="background:rgba(76,175,80,0.1);color:var(--success)">API</span>`;

        return `<tr class="${j.status === 'completed' && j.messages_done === 0 ? 'job-row-dim' : ''}">
            <td title="${j.id}">${j.id.substring(0, 8)}</td>
            <td>${j.job_type} ${srcHtml}</td>
            <td>${statusBadge(j.status)}</td>
            <td style="white-space:nowrap">
                <div class="progress-bar" style="width:120px;height:14px;display:inline-block;vertical-align:middle">
                    <div class="progress-fill" style="width:${j.progress_pct}%"></div>
                </div> ${j.progress_pct.toFixed(0)}%
                ${j.current_detail && j.status === 'running' ? `<div style="font-size:0.75em;color:var(--text-muted);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px" title="${esc(j.current_detail)}">${esc(j.current_detail)}</div>` : ''}
            </td>
            <td style="text-align:right">${recordsHtml}</td>
            <td>${formatDT(j.started_at)}</td>
            <td>${formatDT(j.completed_at)}</td>
            <td>${formatElapsed(j.started_at, j.completed_at)}</td>
            <td style="color:${j.status === 'failed' || (j.error_message || '').indexOf('Compliance violation') !== -1 || (j.error_message || '').indexOf('Interrupted') !== -1 ? 'var(--danger)' : 'var(--text-muted)'};font-size:0.85em;max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${esc(j.error_message || '')}">${esc(j.error_message || '')}</td>
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
    // Find running export job
    const runningJob = (jobsData.items || []).find(j => j.status === 'running' && j.job_type === 'export' && j.progress_pct < 100);

    tbody.innerHTML = data.items.map(s => {
        const c = s.config || {};
        let modeHtml = '-';
        let configHtml = '';
        if (s.job_type === 'export') {
            const mode = c.mode === 'opensearch' ? 'OpenSearch' : 'API';
            modeHtml = `<span class="host-label" style="font-size:0.75em">${mode}</span>`;
            if (c.mode === 'opensearch' && c.keep_indices) {
                configHtml = `${c.keep_indices} ${t('sched_indices_unit')}`;
            } else {
                configHtml = `${c.days || '?'} ${t('export_days')}`;
            }
        } else if (s.job_type === 'cleanup') {
            modeHtml = '-';
            configHtml = `${c.retention_days || '?'} ${t('export_days')}`;
        } else if (s.job_type === 'verify') {
            modeHtml = '-';
            configHtml = 'SHA256';
        }
        // Show running status for export schedules
        let runningHtml = '';
        if (s.job_type === 'export' && runningJob) {
            const pct = runningJob.progress_pct?.toFixed(0) || 0;
            const msgs = formatNumber(runningJob.messages_done || 0);
            const elapsed = formatElapsed(runningJob.started_at);
            runningHtml = `<div style="margin-top:6px">
                <div class="progress-bar" style="height:12px;width:180px;display:inline-block;vertical-align:middle">
                    <div class="progress-fill" style="width:${pct}%"></div>
                </div>
                <span style="font-size:0.8em;color:var(--warning);margin-left:6px">${pct}% ${msgs} ${elapsed}</span>
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
            <td><div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
                <button class="btn-sm btn-primary" onclick="editSchedule('${esc(s.name)}')">${icon('shield')} ${t('btn_edit')}</button>
                ${(s.job_type === 'export' || s.job_type === 'cleanup' || s.job_type === 'verify') && !runningJob ? `<button class="btn-sm btn-success" onclick="runScheduleNow('${esc(s.name)}')" title="${t('btn_run_now')}">${icon('play')} ${t('btn_run_now')}</button>` : ''}
                <button class="btn-sm ${s.enabled ? 'btn-secondary' : 'btn-primary'}" onclick="toggleSchedule('${esc(s.name)}',${!s.enabled})">${s.enabled ? t('btn_disable') : t('btn_enable')}</button>
                ${s.name.startsWith('auto-') ? '' : `<button class="btn-sm btn-danger" onclick="deleteSchedule('${esc(s.name)}')">${icon('trash')}</button>`}
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
    onSchedModeChange();
    onSchedTypeChange();
    onSchedFreqChange();
    setTimeout(initCustomSelects, 100);
    applyI18n();
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
        hint.textContent = mode === 'api' ? t('export_mode_api_hint') : t('export_mode_os_hint');
        hint.style.color = mode === 'opensearch' ? 'var(--warning)' : '';
    }
    if (streamGroup) streamGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (daysGroup) daysGroup.style.display = mode === 'api' ? 'block' : 'none';
    if (coverage) {
        coverage.style.display = 'block';
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
    div.innerHTML = `<span style="color:var(--text-muted)">${t('loading')}...</span>`;
    try {
        const data = await fetchJSON(`${API}/streams`);
        if (data.items) {
            div.innerHTML = data.items.map(s =>
                `<label><input type="checkbox" class="sched-stream-check" value="${s.id}"> ${esc(s.title || s.id)}</label>`
            ).join('');
        }
    } catch (e) {
        div.innerHTML = `<span style="color:var(--danger)">${t('load_failed')}</span>`;
    }
}

function onSchedTypeChange() {
    const type = document.getElementById('sched-type')?.value;
    const exportOpts = document.getElementById('sched-export-options');
    const cleanupOpts = document.getElementById('sched-cleanup-options');
    const verifyOpts = document.getElementById('sched-verify-options');
    if (exportOpts) exportOpts.style.display = type === 'export' ? 'block' : 'none';
    if (cleanupOpts) cleanupOpts.style.display = type === 'cleanup' ? 'block' : 'none';
    if (verifyOpts) verifyOpts.style.display = type === 'verify' ? 'block' : 'none';
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
            body.mode = document.getElementById('sched-mode')?.value || 'api';
            body.days = parseInt(document.getElementById('sched-days')?.value) || 180;
            body.index_set = document.getElementById('sched-indexset')?.value || '';
            body.streams = Array.from(document.querySelectorAll('.sched-stream-check:checked')).map(c => c.value);
            // OpenSearch: save keep_indices from the OS coverage widget
            if (body.mode === 'opensearch') {
                const keepN = document.getElementById('os-keep-n')?.value;
                if (keepN) body.keep_indices = parseInt(keepN);
            }
        } else if (type === 'cleanup') {
            body.retention_days = parseInt(document.getElementById('sched-retention-days')?.value) || 180;
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
        if (retDays) retDays.value = c.retention_days || 180;
    }
    if (sched.job_type === 'export') {
        const modeSel = document.getElementById('sched-mode');
        if (modeSel) modeSel.value = c.mode || 'api';
        onSchedModeChange();
        const daysSel = document.getElementById('sched-days');
        if (daysSel) daysSel.value = c.days || 180;
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
                text.innerHTML = `<span style="color:var(--warning)">${t('export_no_data')}</span>`;
            } else {
                let html = `<span class="status-completed">${t('progress_completed')} (${formatNumber(msgs)} ${t('th_messages').toLowerCase()})</span>`;
                // Surface bulk-mode "where to find" notice (and any other
                // post-completion info written into the job's error_message)
                if (job.error_message) {
                    const isViolation = job.error_message.indexOf('Compliance violation') !== -1;
                    const colour = isViolation ? 'var(--warning)' : 'var(--accent)';
                    html += `<div style="margin-top:8px;padding:8px 10px;background:rgba(108,99,255,0.08);border-left:3px solid ${colour};border-radius:4px;font-size:0.85em">${esc(job.error_message)}</div>`;
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
            const msgs = formatNumber(data.messages_done || 0);
            const total = data.messages_total ? formatNumber(data.messages_total) : '?';
            const phaseKey = data.phase ? `import_phase_${data.phase}` : '';
            const phase = phaseKey ? (t(phaseKey) || data.phase) : '';
            text.textContent = `${phase} ${data.index || ''} — ${msgs}/${total} — ${(data.pct || 0).toFixed(1)}%`;
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
                if (text) text.textContent = `${formatNumber(job.messages_done || 0)}/${job.messages_total ? formatNumber(job.messages_total) : '?'} — ${(job.progress_pct || 0).toFixed(0)}%`;
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
async function loadRealtimeLog() {
    const lines = document.getElementById('log-lines')?.value || 100;
    const el = document.getElementById('log-output');
    el.textContent = t('loading') + '...';
    try {
        const data = await fetchJSON(`${API}/logs/realtime?lines=${lines}`);
        el.textContent = data.lines || t('log_no_data');
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
        <td style="font-size:0.85em;max-width:300px;overflow:hidden;text-overflow:ellipsis" title="${esc(a.detail || '')}">${esc(a.detail || '')}</td>
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
        <td style="text-align:right">${formatRecords(j.messages_done, j.messages_total)}</td>
        <td>${formatDT(j.started_at)}</td>
        <td>${formatDT(j.completed_at)}</td>
        <td style="color:${j.status === 'failed' || (j.error_message || '').indexOf('Compliance violation') !== -1 || (j.error_message || '').indexOf('Interrupted') !== -1 ? 'var(--danger)' : 'var(--text-muted)'};font-size:0.85em;max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${esc(j.error_message || '')}">${esc(j.error_message || '')}</td>
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
        ];
        eventsEl.innerHTML = events.map(e =>
            `<label style="display:flex;align-items:center;gap:8px;margin:8px 0;cursor:pointer">
                <input type="checkbox" class="notify-event" data-key="${e.key}" ${data[e.key] ? 'checked' : ''}> ${icon(e.ic)} ${e.label}
            </label>`
        ).join('');
    }

    // Notification language
    const langEl = document.getElementById('notify-lang-form');
    if (langEl) {
        langEl.innerHTML = `<div class="form-group" style="max-width:300px">
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
        const _chk = (id, en) => `<label style="display:flex;align-items:center;gap:6px;margin-bottom:8px;cursor:pointer"><input type="checkbox" id="${id}" ${en ? 'checked' : ''} onchange="toggleChannelFields(this)"> ${t('notify_enabled')}</label>`;
        const _vis = (en) => en ? '' : 'style="display:none"';
        // Secret field: password input + eye toggle button
        const _secret = (id, val, extra = '') => `<div class="secret-field"><input type="password" id="${id}" value="${esc(val)}" autocomplete="new-password" ${extra}><button type="button" class="secret-toggle" onclick="toggleSecret('${id}', this)" tabindex="-1" data-i18n-title="show_hide" title="Show/Hide">${icon('eye_closed')}</button></div>`;
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
                <div class="form-group"><label>${t('notify_smtp_host')}</label>${_secret('nf-email-host', data.email.smtp_host || '')}</div>
                <div class="form-group"><label>${t('notify_smtp_port')}</label><input type="number" id="nf-email-port" value="${data.email.smtp_port || 587}"></div>
                <div class="form-group"><label style="cursor:pointer"><input type="checkbox" id="nf-email-tls" ${data.email.smtp_tls ? 'checked' : ''}> ${t('notify_smtp_tls')}</label></div>
                <div class="form-group"><label>${t('notify_smtp_user')}</label>${_secret('nf-email-user', data.email.smtp_user || '')}</div>
                <div class="form-group"><label>${t('notify_smtp_password')}</label>${_secret('nf-email-pass', data.email.smtp_password || '')}</div>
                <div class="form-group"><label>${t('notify_from')}</label>${_secret('nf-email-from', data.email.from_addr || '')}</div>
                <div class="form-group"><label>${t('notify_to')}</label><textarea id="nf-email-to" rows="3" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--input-bg);color:var(--text)">${esc((data.email.to_addrs || []).join('\n'))}</textarea></div>
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

function toggleSecret(id, btn) {
    const el = document.getElementById(id);
    if (!el) return;
    const showing = el.type === 'text';
    el.type = showing ? 'password' : 'text';
    btn.innerHTML = showing ? icon('eye_closed') : icon('eye');
}

async function testNotifyFromSettings() {
    const el = document.getElementById('notify-settings-result');
    el.innerHTML = `<span style="color:var(--text-muted)">${t('loading')}...</span>`;
    const data = await fetchJSON(`${API}/notify/test`, {method: 'POST'});
    if (data.results && data.results.length > 0) {
        el.innerHTML = data.results.map(r => `${r.channel}: ${r.success ? '<span class="status-completed">OK</span>' : '<span class="status-failed">' + (r.error || 'Failed') + '</span>'}`).join('<br>');
    } else {
        el.innerHTML = `<span style="color:var(--warning)">${t('notify_no_channels')}</span>`;
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
                sel.dispatchEvent(new Event('change'));
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
        modal.onclick = (e) => { if (e.target === modal) closeConfirm(); };
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
        btnRow.innerHTML = `<button class="btn-danger" onclick="doConfirm()">${icon('shield')} ${t('btn_confirm')}</button>
            <button class="btn-secondary" onclick="closeConfirm()">${t('btn_cancel')}</button>`;
    } else {
        btnRow.innerHTML = `<button class="btn-primary" onclick="closeConfirm()">OK</button>`;
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
        if (el && text) {
            if (running.length > 0) {
                el.style.display = 'block';
                el.style.cursor = 'pointer';
                el.title = t('reopen_running_job') || 'Click to reopen';
                // For an active import on this page → reopen the import modal.
                // Otherwise navigate to /jobs.
                el.onclick = () => {
                    const j = running[0];
                    if (j.job_type === 'import' && _activeImportJobId === j.id &&
                        document.getElementById('import-modal')) {
                        reopenActiveImportModal();
                    } else {
                        window.location.href = '/jobs';
                    }
                };
                const j = running[0];
                const pct = j.progress_pct?.toFixed(0) || 0;
                const msgs = j.messages_done ? formatNumber(j.messages_done) : '0';
                const total = j.messages_total ? formatNumber(j.messages_total) : '?';
                const elapsed = formatElapsed(j.started_at);
                const detail = j.current_detail || j.phase || '';
                text.innerHTML = `
                    <div class="job-detail-full" style="display:flex;flex-direction:column;gap:2px;line-height:1.3">
                        <span>${j.job_type} <strong>${pct}%</strong> · ${elapsed}</span>
                        <div class="progress-bar" style="height:6px"><div class="progress-fill" style="width:${pct}%"></div></div>
                        <span style="font-size:0.9em;opacity:0.85">${msgs} / ${total}</span>
                        ${detail ? `<span style="font-size:0.85em;opacity:0.7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(detail)}</span>` : ''}
                    </div>
                    <div class="job-detail-mini" style="display:none;flex-direction:column;align-items:center;gap:3px;font-size:1.1em" title="${j.job_type} ${pct}% ${msgs} ${elapsed}">
                        <strong>${pct}%</strong>
                        <div class="progress-bar" style="height:4px;width:100%"><div class="progress-fill" style="width:${pct}%"></div></div>
                    </div>`;
            } else {
                el.style.display = 'none';
            }
        }
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
    else if (path === '/schedules') { loadSchedules().then(() => setTimeout(initCustomSelects, 200)); startSchedPoll(); }
    else if (path === '/notify-settings') loadNotifySettings();
    else if (path === '/logs') { loadRealtimeLog(); loadTable('#audit-table', loadAuditLog); }
});

// Re-translate dynamic JS-rendered content when language changes
document.addEventListener('langchange', () => {
    const path = window.location.pathname;
    if (path === '/logs') { loadRealtimeLog(); loadTable('#audit-table', loadAuditLog); }
});


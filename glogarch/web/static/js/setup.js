/* First-run setup wizard behaviour — external so setup.html needs no inline
   script (strict CSP). Loaded after i18n.js. */

let step = 1;
const TOTAL = 5;
const $ = id => document.getElementById(id);

function showError(msg) { const e = $('setup-error'); e.textContent = msg; e.classList.toggle('hidden', !msg); }
function busy(on) { $('setup-busy').textContent = on ? (t('setup_saving') || 'Saving...') : ''; $('btn-next').disabled = on; }

function render() {
    document.querySelectorAll('.setup-step').forEach(el => {
        el.classList.toggle('hidden', Number(el.dataset.step) !== step);
    });
    const dots = $('setup-dots').children;
    for (let i = 0; i < dots.length; i++) {
        dots[i].className = 'dot' + (i + 1 < step ? ' done' : (i + 1 === step ? ' active' : ''));
    }
    $('btn-back').classList.toggle('hidden', !(step > 1 && step < TOTAL));
    $('btn-skip').classList.toggle('hidden', step !== 3);
    $('btn-next').textContent = (step === TOTAL) ? t('setup_finish') : t('setup_next');
    $('setup-progress').textContent = `${t('setup_step')} ${Math.min(step, TOTAL)} ${t('setup_of')} ${TOTAL}`;
    showError('');
}

function s2ToggleAuth() {
    const type = $('s2-auth').value;
    $('s2-token-g').classList.toggle('hidden', type !== 'token');
    $('s2-user-g').classList.toggle('hidden', type !== 'userpass');
    $('s2-pass-g').classList.toggle('hidden', type !== 'userpass');
}

async function api(path, body, method) {
    const resp = await fetch('/api' + path, {
        method: method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await resp.json(); } catch (e) {}
    if (!resp.ok && !data.error) data.error = `HTTP ${resp.status}`;
    return data;
}

function serverBody() {
    const type = $('s2-auth').value;
    const b = { name: $('s2-name').value.trim(), url: $('s2-url').value.trim(), verify_ssl: $('s2-verify').checked };
    if (type === 'token') { b.auth_token = $('s2-token').value.trim(); }
    else { b.username = $('s2-user').value.trim(); b.password = $('s2-pass').value; }
    return b;
}
function osBody() {
    const hosts = $('s3-hosts').value.split('\n').map(h => h.trim()).filter(Boolean);
    return { hosts, username: $('s3-user').value.trim(), password: $('s3-pass').value, verify_ssl: $('s3-verify').checked };
}

async function testServer() {
    const b = serverBody();
    if (!b.url) { $('s2-result').textContent = ''; showError(t('settings_srv_url')); return; }
    $('s2-result').textContent = '...';
    const r = await api('/config/servers/test', b);
    $('s2-result').innerHTML = r.connected
        ? `<span class="ok-text">${t('test_ok')} (${r.version || ''})</span>`
        : `<span class="err-text">${t('test_failed')}: ${r.error || ''}</span>`;
}
async function testOs() {
    const b = osBody();
    if (!b.hosts.length) { showError(t('settings_os_hosts')); return; }
    $('s3-result').textContent = '...';
    const r = await api('/opensearch/test', b);
    $('s3-result').innerHTML = r.connected
        ? `<span class="ok-text">${t('test_ok')} (${r.version || r.cluster_name || ''})</span>`
        : `<span class="err-text">${t('test_failed')}: ${r.error || ''}</span>`;
}

async function setupNext() {
    showError('');
    if (step === 1) {
        const p = $('s1-pass').value, p2 = $('s1-pass2').value;
        if (p.length < 8) return showError(t('setup_pass_short'));
        if (p !== p2) return showError(t('setup_pass_mismatch'));
        busy(true);
        const r = await api('/setup/admin-password', { password: p });
        busy(false);
        if (r.error) return showError(r.error);
    } else if (step === 2) {
        const b = serverBody();
        if (!b.name || !b.url) return showError(t('settings_srv_name') + ' / ' + t('settings_srv_url'));
        busy(true);
        const r = await api('/config/servers', b);
        busy(false);
        if (r.error) return showError(r.error);
    } else if (step === 3) {
        const b = osBody();
        if (!b.hosts.length) return showError(t('settings_os_hosts'));
        busy(true);
        const r = await api('/config/opensearch', b);
        if (!r.error) await api('/config/general', { export_mode: 'opensearch' });
        busy(false);
        if (r.error) return showError(r.error);
    } else if (step === 4) {
        const path = $('s4-path').value.trim();
        if (path && path !== '/data/graylog-archives') {
            busy(true);
            const r = await api('/settings/archive-path', { path });
            busy(false);
            if (r.error) return showError(r.error);
        }
    } else if (step === 5) {
        window.location.href = '/';
        return;
    }
    step++;
    render();
}

async function setupSkip() {
    if (step === 3) { await api('/config/general', { export_mode: 'api' }); }
    step++;
    render();
}

function setupBack() { if (step > 1) { step--; render(); } }

// Add a show/hide reveal toggle to every password field (API token, passwords),
// matching the main settings page — so you can confirm a pasted token is complete.
function addRevealToggles() {
    document.querySelectorAll('.setup-card input[type=password]').forEach(inp => {
        if (inp.closest('.secret-field')) return;
        const wrap = document.createElement('div');
        wrap.className = 'secret-field';
        inp.parentNode.insertBefore(wrap, inp);
        wrap.appendChild(inp);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'secret-toggle';
        btn.tabIndex = -1;
        btn.title = 'Show/Hide';
        btn.innerHTML = icon('eye_closed');
        btn.addEventListener('click', () => {
            const reveal = inp.type === 'password';
            inp.type = reveal ? 'text' : 'password';
            btn.innerHTML = icon(reveal ? 'eye' : 'eye_closed');
        });
        wrap.appendChild(btn);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    applyI18n();
    addRevealToggles();
    $('btn-next').addEventListener('click', setupNext);
    $('btn-back').addEventListener('click', setupBack);
    $('btn-skip').addEventListener('click', setupSkip);
    $('s2-auth').addEventListener('change', s2ToggleAuth);
    $('s2-test').addEventListener('click', testServer);
    $('s3-test').addEventListener('click', testOs);
    const ls = $('lang-select'); if (ls) { ls.value = getLang(); ls.addEventListener('change', e => setLang(e.target.value)); }
    const tt = $('theme-toggle'); if (tt) tt.addEventListener('click', toggleTheme);
    render();
});

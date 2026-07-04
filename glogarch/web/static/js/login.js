/* Login page behaviour — kept external so login.html needs no inline script
   (strict CSP: no script-src 'unsafe-inline'). Loaded after i18n.js. */
document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';

document.addEventListener('DOMContentLoaded', () => {
    const ls = document.getElementById('lang-select');
    if (ls) { ls.value = getLang(); ls.addEventListener('change', e => setLang(e.target.value)); }
    const tt = document.getElementById('theme-toggle');
    if (tt) tt.addEventListener('click', toggleTheme);
    const form = document.getElementById('login-form');
    const btn = document.getElementById('login-btn');
    if (form && btn) {
        form.addEventListener('submit', () => {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-text">...</span>';
        });
    }
});

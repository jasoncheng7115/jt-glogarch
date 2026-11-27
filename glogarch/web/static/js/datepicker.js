// The app's own date / date-time picker, used instead of the browser's (owner 2026-11-27: the
// browser's picker "不好看", make it like jt-waf-mgr's). Like the select skin: the real
// <input type="datetime-local|date"> stays (hidden) and keeps its value format
// ("YYYY-MM-DDTHH:MM" / "YYYY-MM-DD"), so every caller that reads or sets .value is unchanged;
// a field-looking button shows the value and opens a calendar.
(function () {
    'use strict';
    const pad = (n) => String(n).padStart(2, '0');
    const CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>';
    const ARROW = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
    const tr = (k, en) => (typeof t === 'function' ? (t(k) !== k ? t(k) : en) : en);
    const lang = () => (typeof getLang === 'function' ? getLang() : 'en');

    function parse(v, withTime) {
        const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(v || '');
        if (!m) return null;
        return { y: +m[1], mo: +m[2] - 1, d: +m[3], h: withTime && m[4] ? +m[4] : 0, mi: withTime && m[5] ? +m[5] : 0 };
    }
    function fmt(p, withTime) {
        const date = `${p.y}-${pad(p.mo + 1)}-${pad(p.d)}`;
        return withTime ? `${date}T${pad(p.h)}:${pad(p.mi)}` : date;
    }
    function shown(inp) {
        const p = parse(inp.value, inp._dpTime);
        if (!p) return '';
        return `${p.y}-${pad(p.mo + 1)}-${pad(p.d)}` + (inp._dpTime ? ` ${pad(p.h)}:${pad(p.mi)}` : '');
    }

    function paintTrigger(inp) {
        const span = inp._dpTrigger.querySelector('.dp-text');
        const v = shown(inp);
        span.textContent = v || tr('dp_pick', 'Pick a date');
        span.classList.toggle('dp-placeholder', !v);
        inp._dpTrigger.disabled = !!inp.disabled;
    }

    // code sets .value directly: the button has to follow (as the select skin does)
    function follow(inp) {
        if (inp._dpFollowed) return;
        inp._dpFollowed = true;
        const native = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        Object.defineProperty(inp, 'value', {
            configurable: true,
            get: function () { return native.get.call(this); },
            set: function (v) { native.set.call(this, v); if (this._dpTrigger) paintTrigger(this); },
        });
        new MutationObserver(() => paintTrigger(inp)).observe(inp, { attributes: true, attributeFilter: ['disabled'] });
    }

    let pop = null, cur = null, view = null, sel = null;

    function close() {
        if (pop) { pop.remove(); pop = null; }
        if (cur && cur._dpTrigger) cur._dpTrigger.setAttribute('aria-expanded', 'false');
        cur = null;
    }

    function commit(p) {
        sel = p;
        cur.value = p ? fmt(p, cur._dpTime) : '';
        // MUST bubble: data-act-change handlers are delegated on document
        cur.dispatchEvent(new Event('input', { bubbles: true }));
        cur.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function render() {
        const L = lang();
        const month = new Intl.DateTimeFormat(L, { year: 'numeric', month: 'long' }).format(new Date(view.y, view.mo, 1));
        const wdFmt = new Intl.DateTimeFormat(L, { weekday: L === 'en' ? 'short' : 'narrow' });
        const wds = [0, 1, 2, 3, 4, 5, 6].map((i) => wdFmt.format(new Date(2026, 1, 1 + i)));   // 2026-02-01 is a Sunday
        const first = new Date(view.y, view.mo, 1).getDay();
        const days = new Date(view.y, view.mo + 1, 0).getDate();
        const prevDays = new Date(view.y, view.mo, 0).getDate();
        const now = new Date();
        let cells = '';
        for (let i = 0; i < 42; i++) {
            let y = view.y, mo = view.mo, d = i - first + 1, cls = 'dp-day';
            if (d < 1) { d += prevDays; mo -= 1; cls += ' dp-out'; }
            else if (d > days) { d -= days; mo += 1; cls += ' dp-out'; }
            const dt = new Date(y, mo, d);
            if (dt.toDateString() === now.toDateString()) cls += ' dp-today';
            if (sel && dt.getFullYear() === sel.y && dt.getMonth() === sel.mo && dt.getDate() === sel.d) cls += ' dp-sel';
            cells += `<button type="button" class="${cls}" data-y="${dt.getFullYear()}" data-m="${dt.getMonth()}" data-d="${dt.getDate()}">${dt.getDate()}</button>`;
        }
        const time = cur._dpTime ? `<div class="dp-time"><span class="dp-time-label">${tr('dp_time', 'Time')}</span>
            <input type="text" class="dp-hh" inputmode="numeric" maxlength="2" value="${pad(sel ? sel.h : 0)}" aria-label="hour">
            <span class="dp-colon">:</span>
            <input type="text" class="dp-mm" inputmode="numeric" maxlength="2" value="${pad(sel ? sel.mi : 0)}" aria-label="minute"></div>` : '';
        pop.innerHTML = `<div class="dp-head">
              <button type="button" class="dp-nav" data-nav="-1" aria-label="${tr('dp_prev', 'Previous month')}">${ARROW('M15 6l-6 6 6 6')}</button>
              <span class="dp-month">${month}</span>
              <button type="button" class="dp-nav" data-nav="1" aria-label="${tr('dp_next', 'Next month')}">${ARROW('M9 6l6 6-6 6')}</button></div>
            <div class="dp-grid">${wds.map((w) => `<span class="dp-wd">${w}</span>`).join('')}${cells}</div>
            ${time}
            <div class="dp-foot"><button type="button" class="dp-btn dp-clear">${tr('dp_clear', 'Clear')}</button>
              <button type="button" class="dp-btn dp-now">${cur._dpTime ? tr('dp_now', 'Now') : tr('dp_today', 'Today')}</button>
              <button type="button" class="dp-btn dp-done">${tr('dp_done', 'Done')}</button></div>`;
    }

    function place() {
        const r = cur._dpTrigger.getBoundingClientRect();
        const w = pop.offsetWidth, h = pop.offsetHeight;
        let left = r.left + window.scrollX, top = r.bottom + window.scrollY + 6;
        if (r.left + w > window.innerWidth - 8) left = Math.max(8, window.innerWidth - w - 8) + window.scrollX;
        if (r.bottom + h + 6 > window.innerHeight && r.top - h - 6 > 0) top = r.top + window.scrollY - h - 6;
        pop.style.left = left + 'px';
        pop.style.top = top + 'px';
    }

    function readTime() {
        if (!cur._dpTime || !pop) return;
        const hh = Math.max(0, Math.min(23, parseInt(pop.querySelector('.dp-hh').value, 10) || 0));
        const mm = Math.max(0, Math.min(59, parseInt(pop.querySelector('.dp-mm').value, 10) || 0));
        if (!sel) { const n = new Date(); sel = { y: n.getFullYear(), mo: n.getMonth(), d: n.getDate(), h: 0, mi: 0 }; }
        sel = Object.assign({}, sel, { h: hh, mi: mm });
        commit(sel);
    }

    function open(inp) {
        if (cur === inp) { close(); return; }
        close();
        cur = inp;
        sel = parse(inp.value, inp._dpTime);
        const base = sel || (() => { const n = new Date(); return { y: n.getFullYear(), mo: n.getMonth() }; })();
        view = { y: base.y, mo: base.mo };
        pop = document.createElement('div');
        pop.className = 'dp-pop';
        pop.setAttribute('role', 'dialog');
        document.body.appendChild(pop);
        render();
        place();
        inp._dpTrigger.setAttribute('aria-expanded', 'true');
        pop.addEventListener('click', (e) => {
            e.stopPropagation();
            const b = e.target.closest('button');
            if (!b) return;
            if (b.dataset.nav) {
                view.mo += +b.dataset.nav;
                if (view.mo < 0) { view.mo = 11; view.y -= 1; }
                if (view.mo > 11) { view.mo = 0; view.y += 1; }
                render(); place(); return;
            }
            if (b.classList.contains('dp-day')) {
                const p = { y: +b.dataset.y, mo: +b.dataset.m, d: +b.dataset.d, h: sel ? sel.h : 0, mi: sel ? sel.mi : 0 };
                if (cur._dpTime && pop.querySelector('.dp-hh')) {
                    p.h = Math.max(0, Math.min(23, parseInt(pop.querySelector('.dp-hh').value, 10) || 0));
                    p.mi = Math.max(0, Math.min(59, parseInt(pop.querySelector('.dp-mm').value, 10) || 0));
                }
                view = { y: p.y, mo: p.mo };
                commit(p);
                if (!cur._dpTime) { close(); return; }
                render(); return;
            }
            if (b.classList.contains('dp-clear')) { commit(null); close(); return; }
            if (b.classList.contains('dp-now')) {
                const n = new Date();
                const p = { y: n.getFullYear(), mo: n.getMonth(), d: n.getDate(), h: n.getHours(), mi: n.getMinutes() };
                view = { y: p.y, mo: p.mo };
                commit(p);
                if (!cur._dpTime) { close(); return; }
                render(); return;
            }
            if (b.classList.contains('dp-done')) { readTime(); close(); }
        });
        pop.addEventListener('change', (e) => { if (e.target.matches('.dp-hh, .dp-mm')) readTime(); });
        pop.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { close(); inp._dpTrigger.focus(); return; }
            if (e.target.matches('.dp-hh, .dp-mm') && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
                e.preventDefault();
                const max = e.target.classList.contains('dp-hh') ? 23 : 59;
                let v = (parseInt(e.target.value, 10) || 0) + (e.key === 'ArrowUp' ? 1 : -1);
                if (v < 0) v = max; if (v > max) v = 0;
                e.target.value = pad(v);
                readTime();
            }
            if (e.key === 'Enter' && e.target.matches('.dp-hh, .dp-mm')) { e.preventDefault(); readTime(); close(); }
        });
    }

    function initDatePickers(root) {
        (root || document).querySelectorAll('input[type="datetime-local"]:not(.dp-done), input[type="date"]:not(.dp-done)').forEach((inp) => {
            inp.classList.add('dp-done');
            inp._dpTime = inp.type === 'datetime-local';
            const wrap = document.createElement('span');
            wrap.className = 'dp-wrap';
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'dp-trigger';
            btn.setAttribute('aria-haspopup', 'dialog');
            btn.setAttribute('aria-expanded', 'false');
            if (inp.title) btn.title = inp.title;
            if (inp.id) btn.dataset.for = inp.id;
            btn.innerHTML = `<span class="dp-ic">${CAL}</span><span class="dp-text"></span>`;
            inp.parentNode.insertBefore(wrap, inp);
            wrap.appendChild(btn);
            wrap.appendChild(inp);
            inp.classList.add('dp-native');
            inp.tabIndex = -1;
            inp._dpTrigger = btn;
            follow(inp);
            paintTrigger(inp);
            btn.addEventListener('click', (e) => { e.stopPropagation(); open(inp); });
        });
    }
    window.initDatePickers = initDatePickers;

    document.addEventListener('click', () => close());
    window.addEventListener('resize', () => close());
    document.addEventListener('scroll', (e) => { if (pop && !pop.contains(e.target)) close(); }, true);
    document.addEventListener('langchange', () => {
        document.querySelectorAll('input.dp-done').forEach((i) => paintTrigger(i));
        if (pop && cur) render();
    });
    document.addEventListener('DOMContentLoaded', () => {
        initDatePickers();
        let pending = false;
        new MutationObserver(() => {
            if (pending) return;
            pending = true;
            setTimeout(() => {
                pending = false;
                if (document.querySelector('input[type="datetime-local"]:not(.dp-done), input[type="date"]:not(.dp-done)')) initDatePickers();
            }, 30);
        }).observe(document.body, { childList: true, subtree: true });
    });
})();

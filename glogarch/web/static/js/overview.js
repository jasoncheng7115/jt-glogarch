/* jt-glogarch — Security overview, the first tab of the Security Incidents page (added 1.29).
 * One read of /api/security/summary. The chart is plain SVG (attributes, never inline
 * style: the app's CSP blocks style attributes); colours come from CSS classes that
 * use the theme tokens, so it follows light and dark. Entities and titles: esc(). */

const _ov = {data: null};
const OV_SEVS = ['high', 'medium', 'low'];

function ovTile(label, value, sub, act) {
    const inner = `<div class="ov-tile-label">${esc(label)}</div><div class="ov-tile-value">${value}</div>${sub ? `<div class="ov-tile-sub">${sub}</div>` : ''}`;
    return act ? `<button type="button" class="ov-tile ov-tile-link" data-act="secTab" data-arg="${esc(act)}">${inner}</button>`
               : `<div class="ov-tile">${inner}</div>`;
}

/* Stacked bars: one per local day, high at the bottom (the eye starts at the baseline).
 * A 1px surface stroke separates the segments; <title> gives each day its numbers. */
function ovChart(days, perDay) {
    const W = 760, H = 180, padL = 28, padB = 22, padT = 8;
    const max = Math.max(1, ...perDay.map(d => d.high + d.medium + d.low));
    const step = Math.max(1, Math.ceil(max / 4));
    const top = step * Math.ceil(max / step);
    const plotW = W - padL - 4, plotH = H - padB - padT;
    const bw = plotW / days.length;
    const y = v => padT + plotH - (v / top) * plotH;
    let grid = '';
    for (let v = 0; v <= top; v += step) {
        grid += `<line class="ov-grid" x1="${padL}" x2="${W - 4}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"></line>`
            + `<text class="ov-axis" x="${padL - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v}</text>`;
    }
    let bars = '';
    days.forEach((d, i) => {
        const x = padL + i * bw + bw * 0.18, w = bw * 0.64;
        let acc = 0;
        const segs = OV_SEVS.map(s => {
            const n = perDay[i][s];
            if (!n) return '';
            const y0 = y(acc), y1 = y(acc + n);
            acc += n;
            return `<rect class="ov-bar ov-bar-${s}" x="${x.toFixed(1)}" y="${y1.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(1, y0 - y1).toFixed(1)}" rx="2"></rect>`;
        }).join('');
        const tip = `${d}  ` + OV_SEVS.map(s => `${t('sec_sev_' + s)} ${perDay[i][s]}`).join(' · ');
        bars += `<g class="ov-day"><title>${esc(tip)}</title><rect class="ov-hit" x="${(padL + i * bw).toFixed(1)}" y="${padT}" width="${bw.toFixed(1)}" height="${plotH}"></rect>${segs}</g>`;
        if (i % 2 === (days.length - 1) % 2) {
            bars += `<text class="ov-axis" x="${(padL + i * bw + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${esc(d.slice(5))}</text>`;
        }
    });
    const legend = OV_SEVS.map(s => `<span class="ov-key"><span class="ov-swatch ov-bar-${s}"></span>${esc(t('sec_sev_' + s))}</span>`).join('');
    return `<div class="ov-legend">${legend}</div>
        <svg class="ov-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t('ov_chart_title'))}">${grid}${bars}</svg>`;
}

function ovTable(days, perDay) {
    const rows = days.map((d, i) => `<tr><td>${esc(d)}</td>${OV_SEVS.map(s => `<td>${perDay[i][s]}</td>`).join('')}</tr>`).join('');
    return `<details class="ov-table"><summary>${esc(t('ov_as_table'))}</summary><div class="table-wrap"><table class="sec-table">
        <thead><tr><th>${esc(t('ov_day'))}</th>${OV_SEVS.map(s => `<th>${esc(t('sec_sev_' + s))}</th>`).join('')}</tr></thead>
        <tbody>${rows}</tbody></table></div></details>`;
}

async function ovLoad() {
    const el = document.getElementById('sec-overview-panel');
    if (!el) return;
    const d = await fetchJSON(`${API}/security/summary?days=14`);
    if (!d || d.error) { el.innerHTML = `<div class="card"><p class="pk-err">${esc(d && d.error || '')}</p></div>`; return; }
    _ov.data = d;
    const sevSub = OV_SEVS.map(s => `${secSevBadge(s)} ${formatNumber(d.open[s])}`).join(' ');
    const run = d.last_run;
    const runSub = run ? `${esc(secUtc(run.started_at))} · ${esc(t('sec_run_' + run.status))}` : esc(t(d.enabled ? 'sec_never_run' : 'sec_off'));
    const tiles = [
        ovTile(t('ov_open'), formatNumber(d.open_total), sevSub, 'incidents'),
        ovTile(t('ov_cases'), formatNumber(d.cases.open + d.cases.in_progress),
               esc(t('ov_cases_sub').replace('{o}', d.cases.open).replace('{p}', d.cases.in_progress)), 'cases'),
        ovTile(t('ov_attack'), `${formatNumber(d.attack.watched)}<span class="ov-of"> / ${formatNumber(d.attack.total)}</span>`,
               esc(t('ov_attack_sub')), null),
        ovTile(t('ov_last_run'), run ? esc(t('sec_run_' + run.status)) : '—', runSub, null),
    ].join('');
    const dets = d.top_detectors.length ? d.top_detectors.map(x => `<li><span>${esc(secDetTitle(x.detector, x.title))}</span><strong>${formatNumber(x.count)}</strong></li>`).join('')
        : `<li class="text-muted">${esc(t('ov_none'))}</li>`;
    const techs = d.top_techniques.length ? d.top_techniques.map(x => `<li><span><a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer"><code>${esc(x.id)}</code></a> ${esc(x.name || '')}</span><strong>${formatNumber(x.count)}</strong></li>`).join('')
        : `<li class="text-muted">${esc(t('ov_none'))}</li>`;
    const risk = d.risk_top.length ? d.risk_top.map(x => `<li><span><code>${esc(x.entity)}</code>${typeof assetTag === 'function' ? assetTag(x.asset) : ''}</span><strong>${esc(String(x.score))}</strong></li>`).join('')
        : `<li class="text-muted">${esc(t('ov_none'))}</li>`;
    el.innerHTML = `<div class="ov-tiles">${tiles}</div>
        <div class="card ov-card mb15"><h3 class="ov-card-h">${icon('report', 16)}<span>${esc(t('ov_chart_title'))}</span></h3>
            <p class="text-muted fs-08 ov-help">${esc(t('ov_chart_help'))}</p>
            ${ovChart(d.days, d.per_day)}${ovTable(d.days, d.per_day)}</div>
        <div class="ov-lists">
            <div class="card ov-card"><h3 class="ov-card-h">${icon('search', 16)}<span>${esc(t('ov_top_detectors'))}</span></h3><ol class="ov-list">${dets}</ol></div>
            <div class="card ov-card"><h3 class="ov-card-h">${icon('shield', 16)}<span>${esc(t('ov_top_techniques'))}</span></h3><ol class="ov-list">${techs}</ol></div>
            <div class="card ov-card"><h3 class="ov-card-h">${icon('warning', 16)}<span>${esc(t('ov_top_risk'))}</span></h3><ol class="ov-list">${risk}</ol>
                <button type="button" class="btn-sm btn-secondary" data-act="secTab" data-arg="risk">${icon('arrow_right', 14)} ${esc(t('ov_to_risk'))}</button></div>
        </div>`;
}

document.addEventListener('DOMContentLoaded', () => { if (document.getElementById('sec-overview-panel')) ovLoad(); });

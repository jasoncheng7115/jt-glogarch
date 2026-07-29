/* Flag calls to project helpers that are never defined.
 *
 * `node --check` only validates SYNTAX. `customConfirm(...)` was syntactically
 * perfect and undefined everywhere, so Cancel in the import dialog threw
 * ReferenceError on its first line and silently did nothing for releases.
 * This walks each file's call expressions and reports callees that are neither
 * declared in the bundle nor a known browser/global builtin. */
const fs = require('fs'), path = require('path'), vm = require('vm');
const dir = process.argv[2] || 'glogarch/web/static/js';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.js')).map(f => path.join(dir, f));

const src = files.map(f => fs.readFileSync(f, 'utf8')).join('\n');
const defined = new Set();
for (const re of [/\bfunction\s+([A-Za-z_$][\w$]*)/g,
                  /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()/g,
                  /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)/g,
                  /\bclass\s+([A-Za-z_$][\w$]*)/g]) {
  let m; while ((m = re.exec(src))) defined.add(m[1]);
}
// Parameters are locals, not missing globals — collect them too, else every
// callback argument (onComplete, asyncFn, ...) reads as undefined.
for (const re of [/\(([^()]{0,200}?)\)\s*=>/g, /\bfunction\s*[A-Za-z_$\w]*\s*\(([^()]{0,200}?)\)/g]) {
  let m;
  while ((m = re.exec(src))) {
    for (const part of m[1].split(',')) {
      const id = part.trim().replace(/[=:].*$/, '').replace(/^\.\.\./, '').trim();
      if (/^[A-Za-z_$][\w$]*$/.test(id)) defined.add(id);
    }
  }
}
// Everything the browser/runtime provides.
const globalsOk = new Set([...Object.getOwnPropertyNames(globalThis),
  'window','document','console','fetch','setTimeout','setInterval','clearTimeout','clearInterval',
  'requestAnimationFrame','alert','confirm','prompt','localStorage','sessionStorage','navigator',
  'location','history','EventSource','FormData','Blob','URL','URLSearchParams','CustomEvent',
  'Event','Image','Chart','FileReader','AbortController','IntersectionObserver','MutationObserver',
  'ResizeObserver','TextDecoder','TextEncoder','structuredClone','queueMicrotask','btoa','atob',
  'encodeURIComponent','decodeURIComponent','parseInt','parseFloat','isNaN','isFinite',
  'isSecureContext','getComputedStyle','matchMedia','scrollTo','open','close','print']);

const bad = [];
for (const f of files) {
  // Comments and string/template literals are PROSE, not code — scanning them
  // produced hundreds of false hits like "archive(s)" and "range (hours)".
  // Blank them out (preserving newlines) so line numbers still line up.
  const raw = fs.readFileSync(f, 'utf8');
  const blanked = raw
    .replace(/\/\*[\s\S]*?\*\//g, c => c.replace(/[^\n]/g, ' '))
    .replace(/(^|[^:\\])\/\/[^\n]*/g, (m, p1) => p1 + ' '.repeat(m.length - p1.length))
    .replace(/'(?:\\.|[^'\\\n])*'/g, c => "'" + ' '.repeat(Math.max(0, c.length - 2)) + "'")
    .replace(/"(?:\\.|[^"\\\n])*"/g, c => '"' + ' '.repeat(Math.max(0, c.length - 2)) + '"')
    .replace(/`(?:\\.|[^`\\])*`/g, c => c.replace(/[^\n$\{\}]/g, ' '));
  const lines = blanked.split('\n');
  lines.forEach((ln, i) => {
    // bare identifier call, not a method call (no preceding '.') and not a definition
    const re = /(^|[^.\w$'"`])\b([a-z_$][\w$]*)\s*\(/g;
    let m;
    while ((m = re.exec(ln))) {
      const name = m[2];
      if (['if','for','while','switch','catch','return','typeof','function','await','new',
           'else','do','case','delete','void','in','of','yield','throw','async'].includes(name)) continue;
      if (defined.has(name) || globalsOk.has(name)) continue;
      bad.push(`${f}:${i + 1}: calls undefined '${name}()'  ->  ${ln.trim().slice(0, 90)}`);
    }
  });
}
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
console.log(`JS undefined-call check: OK (${files.length} files)`);

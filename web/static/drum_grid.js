// The drum machine's step grid: one row per instrument (name, 32 step buttons in blocks of 4, volume 0-100).
import { esc } from './core.js';

export function gridHtml(st) {
  const cols = st.pattern[0].length;
  const head = `<tr><th></th>${Array.from({ length: cols }, (_, c) =>
    `${c && c % 4 === 0 ? '<td class="gap"></td>' : ''}<th class="mute" style="font:10px var(--mono);text-align:center">${c % 4 === 0 ? c + 1 : ''}</th>`).join('')}<th class="mute small">Vol</th></tr>`;
  const rows = st.pattern.map((line, r) => `<tr><th class="name" scope="row">${esc(st.names[r])}</th>${line.map((v, c) =>
    `${c && c % 4 === 0 ? '<td class="gap"></td>' : ''}<td><button class="cell${c % 4 === 0 ? ' beat' : ''}" data-r="${r}" data-c="${c}"
      aria-pressed="${v ? 'true' : 'false'}" aria-label="${esc(st.names[r])} step ${c + 1}"></button></td>`).join('')}
    <td class="vol"><input type="range" min="0" max="100" value="${st.volumes[r]}" data-vol="${r}"
      aria-label="${esc(st.names[r])} volume"></td></tr>`).join('');
  const html = `<table class="seq">${head}${rows}</table>`;
  queueMicrotask(() => { const g = document.getElementById('gridwrap'); if (g) paintGrid(g, st); });
  return html;
}

export function paintGrid(host, st) {
  host.querySelectorAll('button.cell').forEach(b => {
    const r = +b.dataset.r, c = +b.dataset.c, on = !!st.pattern[r][c];
    b.classList.toggle('on', on);
    b.classList.toggle('now', c === st.step);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
}

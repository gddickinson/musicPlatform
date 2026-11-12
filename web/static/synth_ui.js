// Track cards for the sound generator page: the controls of the desktop TrackControls (amplitude, type-specific dials
// with an automation rate each, continuous-note octave and harmonics, the effects rack), as HTML + event wiring.
import { esc } from './core.js';

export const COLORS = ['#ff4fd8', '#26e0ff', '#ffcf3f', '#7dff8a', '#b38bff', '#ff8f5a'];
const DIAL_LABEL = { frequency: 'Frequency (Hz)', carrier_freq: 'Carrier freq (Hz)', mod_freq: 'Mod freq (Hz)', mod_index: 'Mod index' };
export const DIALS_OF = { wave: ['frequency'], fm: ['carrier_freq', 'mod_freq', 'mod_index'], noise: [], note: [] };
const TITLE = { wave: 'Wave', noise: 'Noise', fm: 'FM synth', note: 'Note' };

const range = (id, label, min, max, value, step = 1, data = '') => `<div class="ctl"><label for="${id}">${label}
  <b>${value}</b></label><input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${value}" ${data}></div>`;

export function trackCard(t, info) {
  const s = info.synth, id = t.id;
  let body = range(`amp-${id}`, 'Amplitude (%)', 0, 100, Math.round(t.amplitude * 100), 1, 'data-k="amplitude"');
  if (t.type === 'wave') {
    body += `<label for="wt-${id}">Wave type</label><select id="wt-${id}" data-k="wave_type">${s.wave_types.map(w =>
      `<option${w === t.wave_type ? ' selected' : ''}>${w}</option>`).join('')}</select>`;
  }
  if (t.type === 'noise') {
    body += `<label for="nt-${id}">Noise type</label><select id="nt-${id}" data-k="noise_type">${s.noise_types.map(w =>
      `<option${w === t.noise_type ? ' selected' : ''}>${w}</option>`).join('')}</select>`;
  }
  for (const k of DIALS_OF[t.type]) {
    const [lo, hi] = s.dials[k], [rlo, rhi] = s.automation_rate;
    body += range(`d-${k}-${id}`, DIAL_LABEL[k], lo, hi, t[k], 1, `data-k="${k}"`) +
      range(`a-${k}-${id}`, `${DIAL_LABEL[k].replace(/ \(.*/, '')}: automation rate`, rlo, rhi, t.auto[k] || 0, 1, `data-auto="${k}"`);
  }
  if (t.type === 'note') {
    body += `<label for="oc-${id}">Octave</label><select id="oc-${id}" data-k="octave">${Array.from(
      { length: s.octaves[1] - s.octaves[0] + 1 }, (_, i) => s.octaves[0] + i).map(o =>
      `<option${o === t.octave ? ' selected' : ''}>${o}</option>`).join('')}</select>` +
      t.harmonics.map((h, i) => range(`h${i}-${id}`, `Harmonic ${i + 1} (%)`, 0, 100, Math.round(h * 100), 1, `data-h="${i}"`)).join('');
  }
  const fx = s.effects.map(e => {
    const st = t.effects[e.name];
    const params = Object.entries(e.params).map(([p, [lo, hi]]) => range(`fx-${e.name}-${p}-${id}`, `${p} (${lo}-${hi})`,
      0, 100, st.params[p], 1, `data-fx="${e.name}" data-p="${p}"`)).join('');
    return `<label class="${e.web ? '' : 'off'}"><input type="checkbox" data-fxon="${e.name}" ${st.on ? 'checked' : ''}
      ${e.web ? '' : `disabled title="${esc(e.omitted_because)}"`}> ${e.name.replace(/Effect$/, '')}</label>
      <div class="ps ${e.web ? '' : 'off'}">${e.web ? params : `<span class="small mute">not on the web: ${esc(e.omitted_because)}</span>`}</div>`;
  }).join('');
  return `<section class="panel trk" data-id="${id}">
    <h3><span><span class="sw" style="background:${t.color}"></span>${TITLE[t.type]}${t.type === 'note' ? ' ' + esc(t.note) : ''}</span>
      <button class="alt" data-remove="${id}">Remove</button></h3>
    ${body}
    <details><summary class="small">Effects (${Object.values(t.effects).filter(f => f.on).length} on)</summary>
      <div class="fx">${fx}</div></details>
  </section>`;
}

// Slider position 0-100 -> effect parameter, as TrackControls.add_effects_controls maps it.
export function fxValue(info, cls, p, pos) {
  const [lo, hi] = info.synth.effects.find(e => e.name === cls).params[p];
  return lo + (hi - lo) * pos / 100;
}

// Wire one card's inputs: onChange(track, kind, key, value) for every user change.
export function wireCard(card, t, onChange) {
  card.addEventListener('input', e => {
    const el = e.target, b = el.closest('.ctl')?.querySelector('b');
    if (b) b.textContent = el.value;
    if (el.dataset.k) onChange(t, 'param', el.dataset.k, el.tagName === 'SELECT' ? (el.dataset.k === 'octave' ? +el.value : el.value) : +el.value);
    else if (el.dataset.auto) onChange(t, 'auto', el.dataset.auto, +el.value);
    else if (el.dataset.h) onChange(t, 'harm', +el.dataset.h, +el.value / 100);
    else if (el.dataset.fx) onChange(t, 'fxparam', el.dataset.fx, [el.dataset.p, +el.value]);
    else if (el.dataset.fxon) onChange(t, 'fxon', el.dataset.fxon, el.checked);
  });
}

// Piano keyboard page (piano_keyboard.py): three octaves from C4, the computer-key map, the waveform menu and every
// synthesis/effect slider with the desktop ranges and defaults (piano_spec.py via /api/info). Sound: piano_audio.js.
import { route, app, api, esc, onLeave, $ } from './core.js';
import { audioContext } from './audio.js';
import { Voice, noteToFreq } from './piano_audio.js';

const WHITE = ['C', 'D', 'E', 'F', 'G', 'A', 'B'], BLACK_AFTER = { C: 'C#', D: 'D#', F: 'F#', G: 'G#', A: 'A#' };
let info, values = {}, waveform = 'Sine', active = new Map(), down = new Set(), indefinite = false, bendUp = 0, bendDown = 0;

function keyboardHtml(p) {
  const keys = [];
  let x = 0;
  const kw = 40, keyByNote = Object.fromEntries(Object.entries(p.key_map).map(([k, n]) => [n, k]));
  for (let o = 0; o < p.octaves; o++) {
    for (const w of WHITE) {
      const n = `${w}${o + p.first_octave}`;
      keys.push(`<button class="k w" data-note="${n}" style="left:${x}px;width:${kw}px" aria-label="${n}"><span>${n}${keyByNote[n] ? ' · ' + esc(keyByNote[n]) : ''}</span></button>`);
      if (BLACK_AFTER[w]) {
        const b = `${BLACK_AFTER[w]}${o + p.first_octave}`;
        keys.push(`<button class="k b" data-note="${b}" style="left:${x + kw * 0.68}px;width:${kw * 0.64}px" aria-label="${b}"><span>${keyByNote[b] ? esc(keyByNote[b]) : ''}</span></button>`);
      }
      x += kw;
    }
  }
  return { html: keys.join(''), width: x };
}

// play_note: restart a sounding note, steal the oldest past the polyphony limit, build the chain at current settings.
function playNote(note) {
  const ac = audioContext();
  if (active.has(note)) stopNote(note);
  if (active.size >= info.piano.polyphony) stopNote(active.keys().next().value);
  const v = new Voice(ac, noteToFreq(note), values, waveform);
  v.out.connect(ac.destination);
  active.set(note, v);
  keyEl(note)?.classList.add('down');
}
function releaseNote(note) {  // release_note: the envelope releases, the note stays "active" until replaced
  if (active.has(note) && !indefinite) { active.get(note).noteOff(); keyEl(note)?.classList.remove('down'); }
}
function stopNote(note) {
  const v = active.get(note);
  if (!v) return;
  v.stop(); active.delete(note); keyEl(note)?.classList.remove('down');
}
const keyEl = n => document.querySelector(`.kbd [data-note="${CSS.escape(n)}"]`);

function onSlider(label, v) {
  values[label] = v;
  if (label === 'Sustain') { for (const voice of active.values()) voice.setRelease(v / 1000); return; }  // update_sustain
  if (label === 'Release') for (const voice of active.values()) voice.setRelease(v / 1000);
  for (const voice of active.values()) voice.apply(values);
}

route('piano', async () => {
  info = await api('/info');
  const p = info.piano;
  if (!Object.keys(values).length) for (const [label, , , def] of p.sliders) values[label] = def;
  const kb = keyboardHtml(p);
  app().innerHTML = `
  <p class="kicker">piano_keyboard.py</p>
  <h1 class="glow">Piano keyboard</h1>
  <p class="lead">Play with the mouse, a touch screen or the computer keys (${esc(Object.keys(p.key_map).join(' ').toUpperCase())}).
  Up to ${p.polyphony} notes at once; the oldest is cut off first. The controls are the desktop's, with its ranges and defaults.</p>
  <p class="callout small">The desktop synthesises the piano with pyo (WGVerb, Delay, Chorus, Disto). This page rebuilds that
  chain from WebAudio nodes with the same parameter mappings, so it is an approximation of the desktop sound, not a
  sample-exact copy (the drum machine and sound generator pages are exact ports).</p>
  <div class="actions">
    <div><label for="wave">Waveform</label><select id="wave">${p.waveforms.map(w => `<option${w === waveform ? ' selected' : ''}>${w}</option>`).join('')}</select></div>
    <label style="margin:0"><input type="checkbox" id="indef" ${indefinite ? 'checked' : ''}> Indefinite sustain</label>
  </div>
  <div class="gridwrap"><div class="kbd" id="kbd" style="width:${kb.width}px">${kb.html}</div></div>
  <section class="panel"><div class="sliders" id="sliders"></div>
    <div class="sliders" id="bends"></div></section>`;
  const host = $('#sliders');
  for (const [label, min, max] of p.sliders) {
    const id = label.toLowerCase().replace(/\s+/g, '-');
    host.insertAdjacentHTML('beforeend', `<div class="ctl"><label for="p-${id}">${esc(label)} <b>${values[label]}</b></label>
      <input type="range" id="p-${id}" min="${min}" max="${max}" value="${values[label]}"></div>`);
    const el = document.getElementById(`p-${id}`);
    el.addEventListener('input', () => { el.previousElementSibling.querySelector('b').textContent = el.value; onSlider(label, +el.value); });
  }
  for (const [id, label] of [['up', 'Pitch bend up (cents)'], ['down', 'Pitch bend down (cents)']]) {
    $('#bends').insertAdjacentHTML('beforeend', `<div class="ctl"><label for="bend-${id}">${label} <b>0</b></label>
      <input type="range" id="bend-${id}" min="0" max="1200" value="${id === 'up' ? bendUp : bendDown}"></div>`);
    const el = document.getElementById(`bend-${id}`);
    el.addEventListener('input', () => {
      el.previousElementSibling.querySelector('b').textContent = el.value;
      if (id === 'up') bendUp = +el.value; else bendDown = +el.value;
      for (const v of active.values()) v.bend(bendUp, bendDown);
    });
  }
  $('#wave').onchange = e => { waveform = e.target.value; };
  $('#indef').onchange = e => {
    indefinite = e.target.checked;
    if (!indefinite) for (const n of [...active.keys()]) if (!down.has(n)) stopNote(n);
  };
  const kbd = $('#kbd');
  kbd.addEventListener('pointerdown', e => {
    const k = e.target.closest('[data-note]');
    if (!k) return;
    e.preventDefault(); kbd.setPointerCapture?.(e.pointerId);
    down.add(k.dataset.note); playNote(k.dataset.note); kbd.dataset.held = k.dataset.note;
  });
  const up = () => { const n = kbd.dataset.held; if (n) { down.delete(n); releaseNote(n); delete kbd.dataset.held; } };
  kbd.addEventListener('pointerup', up); kbd.addEventListener('pointercancel', up);
  kbd.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset.note && !e.repeat) { e.preventDefault(); playNote(e.target.dataset.note); }
  });
  kbd.addEventListener('keyup', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset.note) releaseNote(e.target.dataset.note); });
  const typing = e => ['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName) && e.target.type !== 'range';
  const kd = e => {
    const n = p.key_map[e.key.toLowerCase()] || p.key_map[e.key];
    if (!n || e.repeat || e.metaKey || e.ctrlKey || typing(e)) return;
    down.add(n); playNote(n);
  };
  const ku = e => { const n = p.key_map[e.key.toLowerCase()] || p.key_map[e.key]; if (n) { down.delete(n); releaseNote(n); } };
  window.addEventListener('keydown', kd); window.addEventListener('keyup', ku);
  onLeave(() => {
    window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku);
    for (const n of [...active.keys()]) stopNote(n);
  });
});

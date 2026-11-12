// Sound generator page (sound_generator.py): wave / noise / FM / continuous-note tracks with per-track effects,
// automated dials, a scope, WAV export and presets. The audio runs synth_engine.js (a tested port of synth_dsp.py)
// inside an AudioWorklet, in 1024-frame blocks like the desktop's PyAudio callback.
import { route, app, api, esc, onLeave, download, $ } from './core.js';
import { makeTrack, automationStep, mixBlock } from './synth_engine.js';
import { encodeWav } from './wav_writer.js';
import { audioContext, drawScope } from './audio.js';
import { trackCard, wireCard, fxValue, COLORS, DIALS_OF } from './synth_ui.js';

let info, tracks = [], nextId = 1, colorIdx = 0, node = null, autoTimer = 0, lastScope = null;

function newTrack(type, extra = {}) {
  const t = { id: nextId++, type, amplitude: 0.5, frequency: 440, wave_type: 'sine', noise_type: 'white', carrier_freq: 440,
    mod_freq: 220, mod_index: 2, note: 'C', octave: 4, harmonics: [1, 0, 0, 0, 0], auto: {}, effects: {},
    color: COLORS[colorIdx++ % COLORS.length], ...extra };
  for (const e of info.synth.effects) {
    t.effects[e.name] = t.effects[e.name] || { on: false, params: Object.fromEntries(Object.keys(e.params).map(p => [p, 50])) };
  }
  return t;
}
// The engine spec of a UI track (effects at their slider values, as the fixed desktop does when one is switched on).
function spec(t) {
  return { type: t.type, amplitude: t.amplitude, frequency: t.frequency, wave_type: t.wave_type, noise_type: t.noise_type,
    carrier_freq: t.carrier_freq, mod_freq: t.mod_freq, mod_index: t.mod_index, note: t.note, octave: t.octave,
    harmonics: t.harmonics, effects: Object.entries(t.effects).filter(([, f]) => f.on).map(([cls, f]) => ({ cls, ...fxParams(cls, f) })) };
}
const fxParams = (cls, f) => Object.fromEntries(Object.entries(f.params).map(([p, v]) => [p, fxValue(info, cls, p, v)]));
const send = m => node && node.port.postMessage(m);
const SETTER = { frequency: 'setFrequency', wave_type: 'setWaveType', noise_type: 'setNoiseType', carrier_freq: 'setCarrier',
  mod_freq: 'setModFreq', mod_index: 'setModIndex', amplitude: 'setAmplitude' };

function onChange(t, kind, key, value) {
  if (kind === 'param') {
    if (key === 'amplitude') value /= 100;
    t[key] = value;
    if (key === 'octave') send({ op: 'call', id: t.id, method: 'setNote', args: [t.note, value] });
    else send({ op: 'call', id: t.id, method: SETTER[key], args: [value] });
  } else if (kind === 'auto') t.auto[key] = value;
  else if (kind === 'harm') { t.harmonics[key] = value; send({ op: 'prop', id: t.id, key: 'harmonics', value: [...t.harmonics] }); }
  else if (kind === 'fxon') {
    t.effects[key].on = value;
    send({ op: 'fx', id: t.id, cls: key, on: value, params: fxParams(key, t.effects[key]) });
    const sum = document.querySelector(`.trk[data-id="${t.id}"] details summary`);
    if (sum) sum.textContent = `Effects (${Object.values(t.effects).filter(f => f.on).length} on)`;
  } else if (kind === 'fxparam') {
    const [p, pos] = value;
    t.effects[key].params[p] = pos;
    send({ op: 'fxparam', id: t.id, cls: key, key: p, value: fxValue(info, key, p, pos) });
  }
  if (!node) drawPreview();
}

function addTrack(t) { tracks.push(t); send({ op: 'add', id: t.id, spec: spec(t) }); renderTracks(); }
function removeTrack(id) { tracks = tracks.filter(t => t.id !== id); send({ op: 'remove', id }); renderTracks(); }

function renderTracks() {
  const host = $('#tracks');
  if (!host) return;
  host.innerHTML = tracks.length ? tracks.map(t => trackCard(t, info)).join('')
    : '<p class="mute">No tracks yet: add a wave, noise or FM track, or click a note.</p>';
  host.querySelectorAll('.trk').forEach(card => wireCard(card, tracks.find(t => t.id === +card.dataset.id), onChange));
  $('#notes').querySelectorAll('button').forEach(b => b.classList.toggle('on', tracks.some(t => t.type === 'note' && t.note === b.dataset.note)));
  if (!node) drawPreview();
}

// Scope: the last played blocks while running; otherwise a preview of fresh copies of the tracks (nothing advances).
function drawPreview() {
  const c = $('#scope');
  if (!c) return;
  const per = tracks.map(t => makeTrack(spec(t)).generate(1024));
  drawScope(c, per, { colors: tracks.map(t => t.color) });
}

async function start() {
  const ac = audioContext();
  try {
    await ac.audioWorklet.addModule(new URL('./synth_worklet.js', import.meta.url));
  } catch (e) {
    $('#amsg').textContent = `This browser could not start the audio worklet (${e.message}); the scope and WAV export still work.`;
    return;
  }
  node = new AudioWorkletNode(ac, 'synth-processor', { outputChannelCount: [2] });
  node.connect(ac.destination);
  node.port.onmessage = e => { lastScope = e.data; };
  for (const t of tracks) send({ op: 'add', id: t.id, spec: spec(t) });
  $('#start').textContent = 'Stop';
  const loop = () => {
    if (!node) return;
    const c = $('#scope');
    if (c && lastScope) drawScope(c, tracks.map(t => lastScope.scope[t.id]), { colors: tracks.map(t => t.color) });
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}
function stopAudio() {
  if (node) { node.disconnect(); node.port.postMessage({ op: 'clear' }); node = null; }
  const b = $('#start');
  if (b) b.textContent = 'Start';
  drawPreview();
}

// AutomatedDial: every 50 ms each dial with a non-zero rate moves by int(rate * 0.05), wrapping around its range.
function automate() {
  for (const t of tracks) {
    for (const k of DIALS_OF[t.type]) {
      const rate = t.auto[k] || 0;
      if (!rate) continue;
      const [lo, hi] = info.synth.dials[k];
      t[k] = automationStep(t[k], rate, lo, hi);
      send({ op: 'call', id: t.id, method: SETTER[k], args: [t[k]] });
      const el = document.getElementById(`d-${k}-${t.id}`);
      if (el) { el.value = t[k]; el.closest('.ctl').querySelector('b').textContent = t[k]; }
    }
  }
}

function exportWav(seconds) {
  const fresh = tracks.map(t => makeTrack(spec(t))), n = Math.round(seconds * 44100), out = new Float64Array(n);
  for (let i = 0; i < n; i += 1024) out.set(mixBlock(fresh, Math.min(1024, n - i)).out, i);
  download(`sound_generator_${seconds}s.wav`, new Blob([encodeWav(out)], { type: 'audio/wav' }));
}

// SoundGeneratorPreset data: {"tracks": [{type, amplitude, ...type fields, effects: [{name, ...params}]}]}.
function presetJson() {
  const data = { tracks: tracks.map(t => {
    const d = { type: t.type, amplitude: t.amplitude };
    if (t.type === 'wave') Object.assign(d, { frequency: t.frequency, wave_type: t.wave_type });
    if (t.type === 'noise') d.noise_type = t.noise_type;
    if (t.type === 'fm') Object.assign(d, { carrier_freq: t.carrier_freq, mod_freq: t.mod_freq, mod_index: t.mod_index });
    if (t.type === 'note') Object.assign(d, { note: t.note, octave: t.octave, harmonics: t.harmonics });
    d.effects = Object.entries(t.effects).filter(([, f]) => f.on).map(([name, f]) => ({ name, ...fxParams(name, f) }));
    return d;
  }) };
  const now = Date.now() / 1000;
  return JSON.stringify({ name: 'web sound', type: 'sound', data, tags: ['web'], created_at: now, modified_at: now });
}
function loadPreset(j) {
  for (const t of tracks) send({ op: 'remove', id: t.id });
  tracks = [];
  for (const d of (j.data || j).tracks || []) {
    if (!DIALS_OF[d.type]) continue;
    const t = newTrack(d.type);
    for (const k of ['amplitude', 'frequency', 'wave_type', 'noise_type', 'carrier_freq', 'mod_freq', 'mod_index', 'note', 'octave']) {
      if (d[k] !== undefined) t[k] = d[k];
    }
    if (d.harmonics) t.harmonics = [...d.harmonics, 0, 0, 0, 0, 0].slice(0, 5);
    for (const e of d.effects || []) {
      const name = { Reverb: 'ReverbEffect', Distortion: 'DistortionEffect' }[e.name] || e.name, def = info.synth.effects.find(x => x.name === name);
      if (!def || !def.web) continue;
      t.effects[name].on = true;
      for (const [p, [lo, hi]] of Object.entries(def.params)) if (e[p] !== undefined) t.effects[name].params[p] = Math.round((e[p] - lo) / (hi - lo) * 100);
    }
    tracks.push(t);
    send({ op: 'add', id: t.id, spec: spec(t) });
  }
  renderTracks();
}

route('synth', async () => {
  info = await api('/info');
  if (!tracks.length) tracks = [newTrack('wave', { frequency: 220, wave_type: 'triangle', amplitude: 0.4 })];
  app().innerHTML = `
  <p class="kicker">sound_generator.py · synth_dsp.py</p>
  <h1 class="glow">Sound generator</h1>
  <p class="lead">Stack wave, noise and FM tracks and held notes, shape each with effects and automated dials, and listen.
  The DSP is the Python's, line for line, run in your browser in 1024-sample blocks.</p>
  <div class="actions">
    <button id="start">Start</button>
    <button class="alt" data-add="wave">Add wave</button><button class="alt" data-add="noise">Add noise</button>
    <button class="alt" data-add="fm">Add FM synth</button>
  </div>
  <p class="small mute">Held notes (octave 4, five harmonics each):</p>
  <div class="notes" id="notes">${info.synth.notes.map(n => `<button data-note="${esc(n)}">${esc(n)}</button>`).join('')}</div>
  <p class="small" id="amsg"></p>
  <canvas class="scope" id="scope" role="img" aria-label="One block of each track's output"></canvas>
  <div class="tracks" id="tracks"></div>
  <section class="panel">
    <div class="actions"><label for="secs" style="margin:0">Seconds</label>
      <select id="secs" style="width:auto"><option>2</option><option selected>5</option><option>10</option></select>
      <button id="wav">Download WAV</button><button class="alt" id="savep">Save .preset</button>
      <label class="btn alt" for="loadp">Load .preset</label><input type="file" id="loadp" accept=".preset,.json" hidden></div>
    <p class="small mute">The WAV renders the tracks from the start (16-bit stereo, peak at 95%, as the desktop exporter);
    noise is random each time. Presets use the desktop SoundGeneratorPreset format.</p>
  </section>`;
  $('#start').onclick = () => (node ? stopAudio() : start());
  document.querySelectorAll('[data-add]').forEach(b => { b.onclick = () => addTrack(newTrack(b.dataset.add)); });
  $('#notes').onclick = e => {
    const b = e.target.closest('button[data-note]');
    if (!b) return;
    const have = tracks.find(t => t.type === 'note' && t.note === b.dataset.note);
    if (have) removeTrack(have.id); else addTrack(newTrack('note', { note: b.dataset.note }));
  };
  $('#tracks').addEventListener('click', e => { const b = e.target.closest('[data-remove]'); if (b) removeTrack(+b.dataset.remove); });
  $('#wav').onclick = () => exportWav(+$('#secs').value);
  $('#savep').onclick = () => download('web sound.preset', presetJson(), 'application/json');
  $('#loadp').onchange = async e => {
    const f = e.target.files[0];
    if (f) { try { loadPreset(JSON.parse(await f.text())); } catch (err) { $('#amsg').textContent = err.message; } }
    e.target.value = '';
  };
  renderTracks();
  autoTimer = setInterval(automate, 50);
  onLeave(() => { clearInterval(autoTimer); stopAudio(); });
});

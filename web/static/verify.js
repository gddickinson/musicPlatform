// Verify page: the Python reference values (/api/verify: synth_dsp.py, drum_engine.py, drum_kit.py, wav_export.py,
// midi_export.py) recomputed by the browser engines, case by case.
import { route, app, api, esc } from './core.js';
import { makeTrack, automationStep, ReverbEffect } from './synth_engine.js';
import * as de from './drum_engine.js';
import { buildKit } from './drum_kit.js';
import { encodeWav } from './wav_writer.js';
import { buildMidi } from './midi_writer.js';
import { sha256hex } from './audio.js';

const hex = b => [...b].map(x => x.toString(16).padStart(2, '0')).join('');

function synthRows(fx) {
  return fx.cases.map(c => {
    const t = makeTrack({ ...c.track, effects: c.effects || [] });
    if (c.white) { let k = 0; t.gauss = n => Float64Array.from(c.white.slice(k, k += n)); }
    let worst = 0, i = 0;
    for (let b = 0; b < fx.blocks; b++) {
      if (c.change_cutoff_at_block === b) t.getEffect('LowPassFilter').cutoff = 3000;
      for (const v of t.generate(fx.block)) worst = Math.max(worst, Math.abs(v - c.out[i++]));
    }
    return [c.name, `${i} samples`, `max |JS - Python| ${worst.toExponential(1)}`, worst < 1e-9];
  }).concat((fx.reverb || []).map(rv => {
    const x = new Float64Array(rv.n), eff = new ReverbEffect(rv.params);
    x[0] = 1;
    for (let i = 3000; i < 4000; i++) x[i] = 0.7 * (((i - 3000) * 330 / 44100) % 1 * 2 - 1);
    let worst = 0;
    for (let i = 0; i < rv.n; i += 1024) {
      eff.process(x.slice(i, i + 1024)).forEach((v, k) => {
        if ((i + k) % 7 === 0) worst = Math.max(worst, Math.abs(v - rv.every7[(i + k) / 7]));
      });
    }
    return [`reverb room ${rv.params.room_size}, damping ${rv.params.damping}, mix ${rv.params.mix}`, `${rv.n} samples`,
      `max |JS - Python| ${worst.toExponential(1)}`, worst < 1e-9];
  }));
}

async function drumRows(fx) {
  const rows = [];
  const tempos = Object.entries(fx.step_ms).filter(([b, ms]) => de.stepIntervalMs(+b) !== ms).length;
  rows.push(['Step clock 60-180 BPM', `${Object.keys(fx.step_ms).length} tempos`, `${tempos} differ`, tempos === 0]);
  const kit = buildKit();
  kit.forEach((v, r) => {
    const s = fx.kit[r];
    let sum = 0, sq = 0;
    for (const x of v) { sum += x; sq += x * x; }
    const d = Math.max(Math.abs(sum - s.sum), Math.abs(sq - s.sumsq) / Math.max(1, s.sumsq));
    const head = Math.max(...s.head.map((h, i) => Math.abs(v[i] - h)));
    rows.push([`Kit: ${de.SAMPLE_NAMES[r]}`, `${v.length} samples`, `sum/energy diff ${d.toExponential(1)}`,
      v.length === s.n && d < 1e-8 && head < 1e-9]);
  });
  for (const r of fx.renders) {
    const audio = de.renderPattern(de.examplePattern(), kit, r.bpm, de.EXAMPLE_VOLUMES, r.loops);
    const wav = await sha256hex(encodeWav(audio));
    rows.push([`Example beat ${r.bpm} BPM x${r.loops}: WAV`, `${r.wav_len} bytes`, wav === r.wav_sha256 ? 'SHA-256 identical' : 'bytes differ', wav === r.wav_sha256]);
    const midi = hex(buildMidi(de.patternToMidiTracks(de.examplePattern(), r.bpm, de.EXAMPLE_VOLUMES, r.loops)));
    rows.push([`Example beat ${r.bpm} BPM x${r.loops}: MIDI`, `${midi.length / 2} bytes`, midi === r.midi_hex ? 'identical' : 'bytes differ', midi === r.midi_hex]);
  }
  return rows;
}

route('verify', async () => {
  app().innerHTML = '<p class="mute">Fetching the Python results and re-running them in the browser...</p>';
  const fx = await api('/verify');
  const rows = [...synthRows(fx.synth), ...await drumRows(fx.drum)];
  const autoBad = fx.synth.automation.filter(([v, r, lo, hi, want]) => automationStep(v, r, lo, hi) !== want).length;
  rows.push(['Automated dial ticks', `${fx.synth.automation.length} cases`, `${autoBad} differ`, autoBad === 0]);
  const ok = rows.filter(r => r[3]).length;
  app().innerHTML = `
  <p class="kicker">browser vs Python</p>
  <h1 class="glow">Verify</h1>
  <p class="lead">The Python modules computed these reference results (on the static site: when the site was built).
  Your browser has just recomputed every one with the JavaScript engines the instruments use.</p>
  <div class="tiles"><div class="tile"><b>${ok}/${rows.length}</b><span>checks agree</span></div>
    <div class="tile"><b>${fx.synth.cases.length}</b><span>sound generator cases (tracks, noise filters, effects)</span></div>
    <div class="tile"><b>${fx.drum.kit.length + fx.drum.renders.length * 2}</b><span>drum kit voices, WAV and MIDI files</span></div></div>
  <div class="scroll"><table><tr><th>Check</th><th>Size</th><th>Result</th><th></th></tr>
  ${rows.map(([n, s, d, good]) => `<tr><td>${esc(n)}</td><td class="mono">${esc(s)}</td><td class="mono">${esc(d)}</td>
    <td class="${good ? 'ok' : 'err'}">${good ? 'match' : 'MISMATCH'}</td></tr>`).join('')}</table></div>
  <p class="small mute">Sound generator cases run three 512-sample blocks so state carried between blocks (phases,
  filter memories, the chorus buffer) is checked too. Floating-point results agree to within 1e-9 (sin/exp may differ
  in the last bit between JavaScript and NumPy); WAV and MIDI files are compared byte for byte. The noise tracks are fed
  the same white noise as the Python (the live page draws its own random numbers).</p>`;
});

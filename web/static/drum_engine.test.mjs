// node web/static/drum_engine.test.mjs: drum timing, kit, render, WAV and MIDI bytes against drum_engine.py,
// drum_kit.py, wav_export.py and midi_export.py (tests/fixtures/drum_fixture.json).
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as de from './drum_engine.js';
import { buildKit } from './drum_kit.js';
import { encodeWav } from './wav_writer.js';
import { buildMidi } from './midi_writer.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/drum_fixture.json', import.meta.url)));
let failed = 0;
const fail = msg => { failed++; console.log('FAIL', msg); };
const hex = b => Buffer.from(b).toString('hex');
const close = (a, b, tol) => Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));

function checkStats(name, a, s) {
  const idx = (x, i) => x * i;
  let sum = 0, sumsq = 0, w = 0;
  a.forEach((x, i) => { sum += x; sumsq += x * x; w += idx(x, i); });
  if (a.length !== s.n) return fail(`${name}: length ${a.length} != ${s.n}`);
  if (!close(sum, s.sum, 1e-9) || !close(sumsq, s.sumsq, 1e-9) || !close(w / a.length, s.wsum, 1e-9)) {
    fail(`${name}: sums ${sum}, ${sumsq} != ${s.sum}, ${s.sumsq}`);
  }
  const mid = Math.floor(a.length / 2);
  s.head.forEach((v, i) => { if (!close(a[i], v, 1e-9)) fail(`${name}: sample ${i} ${a[i]} != ${v}`); });
  s.mid.forEach((v, i) => { if (!close(a[mid + i], v, 1e-9)) fail(`${name}: sample ${mid + i} ${a[mid + i]} != ${v}`); });
}

for (const [bpm, ms] of Object.entries(fx.step_ms)) if (de.stepIntervalMs(+bpm) !== ms) fail(`step ms at ${bpm} BPM`);
if (JSON.stringify(de.stepOffsets(40, 97)) !== JSON.stringify(fx.offsets_97)) fail('step offsets at 97 BPM');
if (JSON.stringify(de.GM_NOTES) !== JSON.stringify(fx.gm_notes)) fail('GM notes');

const kit = buildKit();
kit.forEach((v, r) => checkStats(`kit ${de.SAMPLE_NAMES[r]}`, v, fx.kit[r]));

const pattern = de.examplePattern();
for (const r of fx.renders) {
  const audio = de.renderPattern(pattern, kit, r.bpm, de.EXAMPLE_VOLUMES, r.loops);
  checkStats(`render ${r.bpm} BPM x${r.loops}`, audio, r.audio);
  const wav = encodeWav(audio);
  if (wav.length !== r.wav_len || createHash('sha256').update(wav).digest('hex') !== r.wav_sha256) {
    fail(`WAV bytes ${r.bpm} BPM`);
  }
  const midi = hex(buildMidi(de.patternToMidiTracks(pattern, r.bpm, de.EXAMPLE_VOLUMES, r.loops)));
  if (midi !== r.midi_hex) fail(`MIDI bytes ${r.bpm} BPM:\n${midi}\n${r.midi_hex}`);
}
if (hex(encodeWav([0.3, -0.2, 0.0, 0.7, -0.7, 1e-6])) !== fx.wav_small_hex) fail('small WAV bytes');
if (JSON.stringify(de.presetData(pattern, 97, de.EXAMPLE_VOLUMES)) !== JSON.stringify(fx.preset)) fail('preset data');
const back = de.fromPresetData(fx.preset);
if (JSON.stringify(back.pattern) !== JSON.stringify(pattern) || back.bpm !== 97) fail('preset round trip');

console.log(`${Object.keys(fx.step_ms).length} tempos, ${kit.length} kit voices, ${fx.renders.length} renders ` +
  `(audio, WAV and MIDI bytes): ` + (failed ? `${failed} FAILED` : 'all match Python'));
process.exit(failed ? 1 : 0);

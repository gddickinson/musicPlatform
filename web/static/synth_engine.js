// Sound generator DSP: a line-by-line port of synth_dsp.py (tracks + effects), block by block like the desktop's
// 1024-frame PyAudio callback. Pure functions/classes (no DOM, no WebAudio) so node tests and the AudioWorklet share it.
// Checked against tests/fixtures/synth_fixture.json (synth_engine.test.mjs).
export const SR = 44100;
const TWO_PI = 2 * Math.PI;
export const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// scipy.signal.square (duty 0.5) and sawtooth (width w) of a phase argument in radians (non-negative).
export function square(x) { return (x % TWO_PI) < 0.5 * TWO_PI ? 1 : -1; }
export function sawtooth(x, w = 1) {
  const tm = x % TWO_PI;
  return tm < w * TWO_PI ? tm / (Math.PI * w) - 1 : (Math.PI * (w + 1) - tm) / (Math.PI * (1 - w));
}

// First-order Butterworth (scipy.signal.butter(1, fc / 22050)) as [b0, b1, a1].
export function butter1(fc, type) {
  const K = Math.tan(Math.PI * (fc / (SR / 2)) / 2);
  const a1 = (K - 1) / (K + 1);
  return type === 'low' ? [K / (1 + K), K / (1 + K), a1] : [1 / (1 + K), -1 / (1 + K), a1];
}
// scipy.signal.lfilter for a first-order filter, with its state z carried in st.z.
export function lfilter1([b0, b1, a1], x, st) {
  const y = new Float64Array(x.length);
  let z = st.z;
  for (let i = 0; i < x.length; i++) { const yi = z + b0 * x[i]; z = b1 * x[i] - a1 * yi; y[i] = yi; }
  st.z = z;
  return y;
}
// lfilter([1], [1, -pole]) with state.
function allPole(pole, x, st) { return lfilter1([1, 0, -pole], x, st); }

// numpy.interp(x, xp, fp) for increasing xp.
export function interp(x, xp, fp) {
  const n = xp.length, out = new Float64Array(x.length);
  for (let k = 0; k < x.length; k++) {
    const v = x[k];
    if (v <= xp[0]) { out[k] = fp[0]; continue; }
    if (v >= xp[n - 1]) { out[k] = fp[n - 1]; continue; }
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (xp[mid] <= v) lo = mid; else hi = mid; }
    const slope = (fp[lo + 1] - fp[lo]) / (xp[lo + 1] - xp[lo]);
    out[k] = slope * (v - xp[lo]) + fp[lo];
  }
  return out;
}

function gaussian(n) {  // np.random.normal(0, 1, n) stand-in (Box-Muller on Math.random)
  const out = new Float64Array(n);
  for (let i = 0; i < n; i += 2) {
    const r = Math.sqrt(-2 * Math.log(1 - Math.random())), th = TWO_PI * Math.random();
    out[i] = r * Math.cos(th); if (i + 1 < n) out[i + 1] = r * Math.sin(th);
  }
  return out;
}

// ---- effects ---------------------------------------------------------------------------------------------------
export class DistortionEffect {
  constructor({ amount = 0.5 } = {}) { this.amount = amount; }
  process(a) {
    if (this.amount === 0) return Float64Array.from(a);
    const d = Math.tanh(this.amount);
    return a.map(x => Math.tanh(x * this.amount) / d);
  }
}
export class EQEffect {
  constructor({ low_gain = 1.0, high_gain = 1.0 } = {}) {
    this.low_gain = low_gain; this.high_gain = high_gain;
    this.low = butter1(500, 'low'); this.high = butter1(2000, 'high');
    this.lowSt = { z: 0 }; this.highSt = { z: 0 };
  }
  process(a) {
    const lo = lfilter1(this.low, a, this.lowSt), hi = lfilter1(this.high, a, this.highSt);
    return a.map((x, i) => x + (this.low_gain - 1) * lo[i] + (this.high_gain - 1) * hi[i]);
  }
}
export class VibratoEffect {
  constructor({ rate = 5, depth = 0.005 } = {}) { this.rate = rate; this.depth = depth; this.phase = 0; }
  process(a) {
    const n = a.length, t = new Float64Array(n), q = new Float64Array(n), w = TWO_PI * this.rate;
    for (let i = 0; i < n; i++) t[i] = i / SR;
    for (let i = 0; i < n; i++) q[i] = t[i] + this.depth * Math.sin(w * t[i] + this.phase);
    this.phase += TWO_PI * this.rate * n / SR;
    this.phase %= TWO_PI;
    return interp(q, t, a);
  }
}
export class TremoloEffect {
  constructor({ rate = 5, depth = 0.5 } = {}) { this.rate = rate; this.depth = depth; this.phase = 0; }
  process(a) {
    const w = TWO_PI * this.rate;
    const out = a.map((x, i) => x * (1 - this.depth * (0.5 + 0.5 * Math.sin(w * (i / SR) + this.phase))));
    this.phase += TWO_PI * this.rate * a.length / SR;
    this.phase %= TWO_PI;
    return out;
  }
}
export class ChorusEffect {
  constructor({ rate = 1, depth = 0.01, mix = 0.5 } = {}) {
    this.rate = rate; this.depth = depth; this.mix = mix; this.phase = 0;
    this.L = Math.trunc(SR * 0.05); this.buf = new Float64Array(this.L); this.pos = 0;  // ring buffer, pos = next write
  }
  process(a) {
    const out = new Float64Array(a.length), L = this.L;
    for (let i = 0; i < a.length; i++) {
      const s = a[i];
      this.buf[this.pos] = s; this.pos = (this.pos + 1) % L;
      const lfo = Math.sin(TWO_PI * this.rate * i / SR + this.phase);
      const delay = Math.trunc(this.depth * SR * (1 + lfo));
      if (delay === 0) out[i] = s;
      else if (delay < L) out[i] = this.mix * this.buf[(this.pos - delay + L) % L] + (1 - this.mix) * s;
      else out[i] = s;
    }
    this.phase += TWO_PI * this.rate * a.length / SR;
    this.phase %= TWO_PI;
    return out;
  }
}
export class LowPassFilter {
  constructor({ cutoff = 1000 } = {}) { this.st = { z: 0 }; this.cutoff = cutoff; }
  set cutoff(v) { this._cutoff = +v; this.coef = butter1(this._cutoff, 'low'); }
  get cutoff() { return this._cutoff; }
  process(a) { return lfilter1(this.coef, a, this.st); }
}
export const EFFECTS = { DistortionEffect, EQEffect, VibratoEffect, TremoloEffect, ChorusEffect, LowPassFilter };

// ---- tracks ------------------------------------------------------------------------------------------------------
class Track {
  constructor() { this.amplitude = 0.5; this.effects = []; }
  setAmplitude(v) { this.amplitude = clamp(v, 0, 1); }
  getEffect(name) { return this.effects.find(e => e.constructor.name === name) || null; }
  addEffect(e) { this.effects.push(e); }
  removeEffect(name) { this.effects = this.effects.filter(e => e.constructor.name !== name); }
  finish(a) { for (const e of this.effects) a = e.process(a); return a.map(x => x * this.amplitude); }
}
export class WaveTrack extends Track {
  constructor() { super(); this.frequency = 440; this.wave_type = 'sine'; this.phase = 0; }
  setFrequency(f) { this.frequency = clamp(f, 20, 20000); }
  setWaveType(w) { if (['sine', 'square', 'sawtooth', 'triangle'].includes(w)) this.wave_type = w; }
  generate(n) {
    const w = TWO_PI * this.frequency, a = new Float64Array(n), k = this.wave_type;
    for (let i = 0; i < n; i++) {
      const x = w * ((i + this.phase) / SR);
      a[i] = k === 'sine' ? Math.sin(x) : k === 'square' ? square(x) : k === 'sawtooth' ? sawtooth(x) : sawtooth(x, 0.5);
    }
    this.phase += n;
    return this.finish(a);
  }
}
export class NoiseTrack extends Track {
  constructor() { super(); this.noise_type = 'white'; this.st = { pink: { z: 0 }, brown: { z: 0 } }; this.gauss = gaussian; }
  setNoiseType(t) { if (['white', 'pink', 'brown'].includes(t)) this.noise_type = t; }
  generate(n) {
    const white = this.gauss(n), k = this.noise_type;
    const a = k === 'pink' ? allPole(0.9, white, this.st.pink) : k === 'brown' ? allPole(0.98, white, this.st.brown) : white;
    return this.finish(a);
  }
}
export class FMSynthTrack extends Track {
  constructor() { super(); this.carrier_freq = 440; this.mod_freq = 220; this.mod_index = 2; this.phase = 0; }
  setCarrier(f) { this.carrier_freq = clamp(f, 20, 20000); }
  setModFreq(f) { this.mod_freq = clamp(f, 1, 5000); }
  setModIndex(v) { this.mod_index = clamp(v, 0, 10); }
  generate(n) {
    const wm = TWO_PI * this.mod_freq, wc = TWO_PI * this.carrier_freq, a = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const t = (i + this.phase) / SR;
      a[i] = Math.sin(wc * t + this.mod_index * Math.sin(wm * t));
    }
    this.phase += n;
    return this.finish(a);
  }
}
export function noteFreq(note, octave) { return 440 * (2 ** ((NOTE_NAMES.indexOf(note) - 9) / 12 + (octave - 4))); }
export class ContinuousNoteTrack extends Track {
  constructor(note, octave) { super(); this.setNote(note, octave); this.harmonics = [1.0]; this.current_sample = 0; }
  setNote(note, octave) { this.note = note; this.octave = octave; this.frequency = noteFreq(note, octave); }
  generate(n) {
    const a = new Float64Array(n), t0 = this.current_sample;
    this.current_sample += n;
    this.harmonics.forEach((amp, h) => {
      const w = TWO_PI * this.frequency * (h + 1);
      for (let i = 0; i < n; i++) a[i] += amp * Math.sin(w * ((i + t0) / SR));
    });
    return this.finish(a);
  }
}

// Build a track from a plain spec (the shape of SoundGeneratorPreset track data, plus 'note' tracks).
export function makeTrack(s) {
  let t;
  if (s.type === 'wave') { t = new WaveTrack(); t.setFrequency(s.frequency ?? 440); t.setWaveType(s.wave_type ?? 'sine'); }
  else if (s.type === 'noise') { t = new NoiseTrack(); t.setNoiseType(s.noise_type ?? 'white'); }
  else if (s.type === 'fm') {
    t = new FMSynthTrack(); t.setCarrier(s.carrier_freq ?? 440); t.setModFreq(s.mod_freq ?? 220); t.setModIndex(s.mod_index ?? 2);
  } else if (s.type === 'note') { t = new ContinuousNoteTrack(s.note, s.octave ?? 4); if (s.harmonics) t.harmonics = [...s.harmonics]; }
  else throw new Error('unknown track type ' + s.type);
  if (s.amplitude !== undefined) t.setAmplitude(s.amplitude);
  for (const e of s.effects || []) t.addEffect(new EFFECTS[e.cls](e));
  return t;
}

// AutomatedDial tick (synth_dsp.automation_step): Python's int() truncates and % is floored.
const pymod = (a, b) => ((a % b) + b) % b;
export function automationStep(value, rate, lo, hi) {
  const range = hi - lo;
  let v = value + Math.trunc(rate * 0.05);
  if (v > hi) v = lo + pymod(v - hi - 1, range);
  else if (v < lo) v = hi - pymod(lo - v - 1, range);
  return v;
}

// Mix the tracks for n frames in blocks (the desktop audio callback sums the tracks).
export function mixBlock(tracks, n) {
  const out = new Float64Array(n), per = [];
  for (const t of tracks) { const a = t.generate(n); per.push(a); for (let i = 0; i < n; i++) out[i] += a[i]; }
  return { out, per };
}

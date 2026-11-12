// The synthesised 12-voice drum kit: a port of drum_kit.py (the desktop's samples/sample0-11.wav are the same voices).
// Checked against tests/fixtures/drum_fixture.json (drum_engine.test.mjs).
const SR = 44100, PEAK = 0.9, TWO_PI = 2 * Math.PI;

export function xorshiftNoise(seed, n) {
  let x = seed >>> 0;
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    x = (x ^ (x << 13)) >>> 0; x = (x ^ (x >>> 17)) >>> 0; x = (x ^ (x << 5)) >>> 0;
    out[i] = x / 4294967296 * 2 - 1;
  }
  return out;
}
const times = dur => Float64Array.from({ length: Math.trunc(dur * SR) }, (_, i) => i / SR);
const decay = (t, tau) => t.map(v => Math.exp(-v / tau));
const mul = (...xs) => xs[0].map((v, i) => xs.slice(1).reduce((p, x) => p * (typeof x === 'number' ? x : x[i]), v));
const add = (a, b) => a.map((v, i) => v + b[i]);
const sine = (t, f) => t.map(v => Math.sin(TWO_PI * f * v));

function sweepSine(t, fEnd, fStart, tau) {
  const out = new Float64Array(t.length);
  let phase = 0;
  for (let i = 0; i < t.length; i++) {
    const freq = fEnd + (fStart - fEnd) * Math.exp(-t[i] / tau);
    phase += TWO_PI * freq / SR;
    out[i] = Math.sin(phase);
  }
  return out;
}
function onePoleLowpass(x, a) {
  const y = new Float64Array(x.length), b = 1 - a;
  let prev = 0;
  for (let i = 0; i < x.length; i++) { prev = b * x[i] + a * prev; y[i] = prev; }
  return y;
}
const highpass = (x, a) => { const lp = onePoleLowpass(x, a); return x.map((v, i) => v - lp[i]); };
function normalise(x) {
  let m = 0;
  for (const v of x) m = Math.max(m, Math.abs(v));
  const k = PEAK / m;
  return x.map(v => v * k);
}

function kick() {
  const t = times(0.5);
  return add(mul(sweepSine(t, 48, 160, 0.04), decay(t, 0.18)), mul(xorshiftNoise(1, t.length), decay(t, 0.003), 0.3));
}
function snare() {
  const t = times(0.35);
  return add(mul(sine(t, 185), decay(t, 0.08), 0.5), mul(highpass(xorshiftNoise(2, t.length), 0.6), decay(t, 0.12), 0.8));
}
function hihat() { const t = times(0.12); return mul(highpass(xorshiftNoise(3, t.length), 0.3), decay(t, 0.025)); }
function clap() {
  const t = times(0.3), noise = highpass(xorshiftNoise(4, t.length), 0.5);
  let env = mul(decay(t, 0.1), 0.6);
  for (const start of [0.0, 0.011, 0.022]) {
    env = add(env, t.map(v => (v >= start ? Math.exp(-Math.max(v - start, 0) / 0.006) : 0)));
  }
  return mul(noise, env);
}
const tom = (fEnd, fStart, dur, tauAmp) => () => { const t = times(dur); return mul(sweepSine(t, fEnd, fStart, 0.08), decay(t, tauAmp)); };
function crash() { const t = times(1.5); return mul(highpass(xorshiftNoise(7, t.length), 0.2), decay(t, 0.6)); }
function ride() {
  const t = times(1.2);
  const hiss = mul(highpass(xorshiftNoise(8, t.length), 0.2), decay(t, 0.5), 0.4);
  const bell = mul(t.map(v => Math.sin(TWO_PI * 520 * v + 2 * Math.sin(TWO_PI * 1300 * v))), decay(t, 0.6), 0.5);
  return add(hiss, bell);
}
function cowbell() {
  const t = times(0.3);
  const sq = t.map(v => Math.sign(Math.sin(TWO_PI * 540 * v)) + Math.sign(Math.sin(TWO_PI * 800 * v)));
  return mul(onePoleLowpass(sq, 0.7), decay(t, 0.09));
}
function rim() {
  const t = times(0.1);
  return add(mul(sine(t, 900), decay(t, 0.02)), mul(xorshiftNoise(10, t.length), decay(t, 0.002), 0.5));
}
function zap() { const t = times(0.4); return mul(sweepSine(t, 2000, 200, -0.25 / Math.log(0.1)), decay(t, 0.12)); }
function rumble() {
  const t = times(0.6), brown = onePoleLowpass(xorshiftNoise(12, t.length), 0.98);
  const trem = t.map(v => 1 - 0.8 * (0.5 + 0.5 * Math.sin(TWO_PI * 12 * v)));
  return mul(brown, trem, decay(t, 0.25));
}
const VOICES = [kick, snare, hihat, clap, tom(160, 220, 0.5, 0.25), tom(110, 150, 0.6, 0.3), crash, ride, cowbell, rim,
  zap, rumble];

export const kitVoice = row => normalise(VOICES[row]());
export const buildKit = () => VOICES.map((_, r) => kitVoice(r));

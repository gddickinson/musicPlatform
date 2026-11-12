// Piano voices: the signal chain of PianoKeyboardWindow.play_note (pyo) rebuilt from WebAudio nodes, with the same
// slider-to-parameter mappings. pyo's own oscillators, WGVerb, Chorus and Disto are not reproduced sample for sample:
// these are WebAudio stand-ins (a generated reverb tail, modulated delays, an arctangent shaper).
//   oscillator (volume) + 4 harmonic sines (1, h, h, h) -> low-pass biquad -> ADSR (x0.8) -> reverb (bal) -> delay
//   -> chorus -> distortion -> LFO tremolo (1 + 0.1 sin) -> out
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
export function noteToFreq(note) {  // piano_spec.note_to_freq
  const octave = +note.slice(-1), semitone = NOTE_NAMES.indexOf(note.slice(0, -1));
  return 440 * (2 ** ((octave - 4) + (semitone - 9) / 12));
}

let irCache = null;
function reverbIR(ac) {  // 2 s of decaying, darkened noise (WGVerb feedback 0.8, cutoff 5000 stand-in)
  if (irCache && irCache.sampleRate === ac.sampleRate) return irCache;
  const n = Math.round(ac.sampleRate * 2), buf = ac.createBuffer(2, n, ac.sampleRate);
  let seed = 7;
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    let lp = 0;
    for (let i = 0; i < n; i++) {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      lp = 0.5 * lp + 0.5 * (seed / 2147483648 - 1);
      d[i] = lp * Math.exp(-3 * i / n);
    }
  }
  return (irCache = buf);
}
function pulseWave(ac) {
  const n = 64, re = new Float32Array(n), im = new Float32Array(n);
  for (let k = 1; k < n; k++) im[k] = (2 / (k * Math.PI)) * Math.sin(k * Math.PI * 0.25) * 2;  // 25% duty pulse
  return ac.createPeriodicWave(re, im);
}
const TYPES = { Sine: 'sine', Square: 'square', Sawtooth: 'sawtooth', Triangle: 'triangle' };
const drive = v => v / 50;  // update_distortion
function shaper(node, d) {
  const k = 1 + Math.min(d, 1) * 30, n = 1024, curve = new Float32Array(n);
  for (let i = 0; i < n; i++) { const x = i / (n - 1) * 2 - 1; curve[i] = d > 0 ? Math.atan(k * x) / Math.atan(k) : x; }
  node.curve = curve;
}

export class Voice {
  constructor(ac, freq, s, waveform) {  // s: slider values by label
    const t = ac.currentTime;
    this.ac = ac; this.base = freq; this.s = s;
    this.osc = ac.createOscillator();
    if (waveform === 'PWM') this.osc.setPeriodicWave(pulseWave(ac)); else this.osc.type = TYPES[waveform] || 'sine';
    this.osc.frequency.value = freq;
    this.vol = ac.createGain(); this.vol.gain.value = s.Volume / 100;
    this.sum = ac.createGain(); this.sum.gain.value = 0.25;  // headroom: five sources are summed
    this.osc.connect(this.vol).connect(this.sum);
    this.harm = [0, 1, 2, 3].map(k => {
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = freq * (k + 1); g.gain.value = k === 0 ? 1 : s.Harmonics / 100;
      o.connect(g).connect(this.sum); o.start(t);
      return [o, g];
    });
    this.filter = ac.createBiquadFilter(); this.filter.type = 'lowpass';
    this.env = ac.createGain(); this.env.gain.value = 0;
    this.dry = ac.createGain(); this.wet = ac.createGain(); this.verb = ac.createConvolver(); this.verb.buffer = reverbIR(ac);
    this.delay = ac.createDelay(1); this.fb = ac.createGain();
    this.chDry = ac.createGain(); this.chWet = ac.createGain(); this.chDelay = ac.createDelay(0.1);
    this.chLfo = ac.createOscillator(); this.chDepth = ac.createGain(); this.chLfo.frequency.value = 1;
    this.disto = ac.createWaveShaper();
    this.lfoGain = ac.createGain(); this.lfoGain.gain.value = 1; this.lfo = ac.createOscillator(); this.lfoAmt = ac.createGain();
    this.lfoAmt.gain.value = 0.1;
    this.out = ac.createGain();
    this.sum.connect(this.filter).connect(this.env);
    this.env.connect(this.dry); this.env.connect(this.verb).connect(this.wet);
    const afterVerb = ac.createGain(); this.dry.connect(afterVerb); this.wet.connect(afterVerb);
    afterVerb.connect(this.delay); this.delay.connect(this.fb).connect(this.delay);
    const afterDelay = ac.createGain(); this.delay.connect(afterDelay);
    afterDelay.connect(this.chDry); afterDelay.connect(this.chDelay).connect(this.chWet);
    this.chLfo.connect(this.chDepth).connect(this.chDelay.delayTime);
    this.chDry.connect(this.disto); this.chWet.connect(this.disto);
    this.disto.connect(this.lfoGain).connect(this.out);
    this.lfo.connect(this.lfoAmt).connect(this.lfoGain.gain);
    this.apply(s);
    this.osc.start(t); this.chLfo.start(t); this.lfo.start(t);
    // Adsr(attack, decay, sustain, release, mul=0.8).play()
    const a = s.Attack / 1000, d = s.Decay / 1000;
    this.env.gain.setValueAtTime(0, t);
    this.env.gain.linearRampToValueAtTime(0.8, t + a);
    this.env.gain.linearRampToValueAtTime(0.8 * s['Sustain Level'] / 100, t + a + d);
    this.release = s.Release / 1000;
  }
  // The update_* handlers: every slider also changes the notes already sounding.
  apply(s) {
    const t = this.ac.currentTime;
    this.vol.gain.setTargetAtTime(s.Volume / 100, t, 0.01);
    this.harm.forEach(([, g], k) => { if (k) g.gain.setTargetAtTime(s.Harmonics / 100, t, 0.01); });
    this.filter.frequency.value = s['Filter Cutoff'];
    this.filter.Q.value = 20 * Math.log10(Math.max(0.1, s['Filter Q'] / 100));  // pyo q -> WebAudio dB
    const bal = s.Reverb / 100;
    this.dry.gain.value = 1 - bal; this.wet.gain.value = bal;
    this.delay.delayTime.value = s.Delay / 1000; this.fb.gain.value = s.Delay / 200;
    const depth = s.Chorus / 100;
    this.chDelay.delayTime.value = 0.015; this.chDepth.gain.value = depth * 0.005;
    this.chWet.gain.value = depth > 0 ? 0.5 : 0; this.chDry.gain.value = depth > 0 ? 0.5 : 1;
    shaper(this.disto, drive(s.Distortion));
    this.lfo.frequency.value = s.LFO;
  }
  bend(up, down) { this.osc.frequency.value = this.base * (2 ** (up / 1200 - down / 1200)); }  // update_pitch_bend
  setRelease(sec) { this.release = sec; }
  noteOff() {
    const t = this.ac.currentTime, g = this.env.gain;
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.linearRampToValueAtTime(0, t + Math.max(0.005, this.release));
  }
  stop() {
    const t = this.ac.currentTime + 0.02;
    this.env.gain.cancelScheduledValues(this.ac.currentTime); this.env.gain.linearRampToValueAtTime(0, t);
    for (const o of [this.osc, this.chLfo, this.lfo, ...this.harm.map(h => h[0])]) o.stop(t + 0.01);
    setTimeout(() => this.out.disconnect(), 3000);
  }
}

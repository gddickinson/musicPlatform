// AudioWorklet processor running the sound generator engine (synth_engine.js) in 1024-frame blocks, like the desktop's
// PyAudio callback, and feeding them out 128 frames at a time. The page sends track/effect changes as messages and
// receives each track's latest block for the scope (so drawing never advances the audio).
import { makeTrack, EFFECTS } from './synth_engine.js';

const BLOCK = 1024;

class SynthProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.tracks = new Map();
    this.fifo = new Float32Array(0); this.pos = 0; this.blocks = 0;
    this.port.onmessage = e => this.handle(e.data);
  }
  handle(m) {
    const t = this.tracks.get(m.id);
    if (m.op === 'add') this.tracks.set(m.id, makeTrack(m.spec));
    else if (m.op === 'remove') this.tracks.delete(m.id);
    else if (m.op === 'clear') this.tracks.clear();
    else if (!t) return;
    else if (m.op === 'call') t[m.method](...m.args);
    else if (m.op === 'prop') t[m.key] = m.value;
    else if (m.op === 'fx') {
      if (m.on && !t.getEffect(m.cls)) t.addEffect(new EFFECTS[m.cls](m.params));
      if (!m.on) t.removeEffect(m.cls);
    } else if (m.op === 'fxparam') { const fx = t.getEffect(m.cls); if (fx) fx[m.key] = m.value; }
  }
  nextBlock() {
    const out = new Float32Array(BLOCK), scope = {};
    for (const [id, t] of this.tracks) {
      const a = t.generate(BLOCK);
      for (let i = 0; i < BLOCK; i++) out[i] += a[i];
      scope[id] = Float32Array.from(a);
    }
    if (++this.blocks % 3 === 0) this.port.postMessage({ scope, mix: out });
    return out;
  }
  process(_inputs, outputs) {
    const ch = outputs[0];
    for (let i = 0; i < ch[0].length; i++) {
      if (this.pos >= this.fifo.length) { this.fifo = this.nextBlock(); this.pos = 0; }
      const v = this.fifo[this.pos++];
      for (const c of ch) c[i] = v;
    }
    return true;
  }
}
registerProcessor('synth-processor', SynthProcessor);

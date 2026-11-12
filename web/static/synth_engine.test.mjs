// node web/static/synth_engine.test.mjs: the JS sound generator against synth_dsp.py (tests/fixtures/synth_fixture.json).
import { readFileSync } from 'node:fs';
import { makeTrack, automationStep, ReverbEffect } from './synth_engine.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/synth_fixture.json', import.meta.url)));
let failed = 0, samples = 0;
const fail = msg => { failed++; console.log('FAIL', msg); };

for (const c of fx.cases) {
  const spec = { ...c.track, effects: c.effects || [] };
  const t = makeTrack(spec);
  if (c.white) { let k = 0; t.gauss = n => Float64Array.from(c.white.slice(k, k += n)); }
  const out = [];
  for (let b = 0; b < fx.blocks; b++) {
    if (c.change_cutoff_at_block === b) t.getEffect('LowPassFilter').cutoff = 3000;
    out.push(...t.generate(fx.block));
  }
  let worst = 0;
  out.forEach((v, i) => { worst = Math.max(worst, Math.abs(v - c.out[i])); });
  samples += out.length;
  if (out.length !== c.out.length || !(worst < 1e-9)) fail(`${c.name}: max |JS - Python| = ${worst}`);
}
for (const [v, rate, lo, hi, want] of fx.automation) {
  const got = automationStep(v, rate, lo, hi);
  if (got !== want) fail(`automation ${v},${rate},${lo},${hi}: ${got} != ${want}`);
}
for (const rv of fx.reverb) {
  const x = new Float64Array(rv.n);
  x[0] = 1;
  for (let i = 3000; i < 4000; i++) x[i] = 0.7 * (((i - 3000) * 330 / 44100) % 1 * 2 - 1);
  const eff = new ReverbEffect(rv.params), y = [];
  for (let i = 0; i < rv.n; i += 1024) y.push(...eff.process(x.slice(i, i + 1024)));
  let worst = 0, sumsq = 0;
  y.forEach((v, i) => { sumsq += v * v; if (i % 7 === 0) worst = Math.max(worst, Math.abs(v - rv.every7[i / 7])); });
  samples += y.length;
  if (!(worst < 1e-9) || Math.abs(sumsq - rv.sumsq) > 1e-9 * rv.sumsq) fail(`reverb ${JSON.stringify(rv.params)}: ${worst}`);
}
console.log(`${fx.cases.length + fx.reverb.length} synth cases (${samples} samples) and ${fx.automation.length} automation ticks: ` +
  (failed ? `${failed} FAILED` : 'all match Python within 1e-9'));
process.exit(failed ? 1 : 0);

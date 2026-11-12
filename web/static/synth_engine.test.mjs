// node web/static/synth_engine.test.mjs: the JS sound generator against synth_dsp.py (tests/fixtures/synth_fixture.json).
import { readFileSync } from 'node:fs';
import { makeTrack, automationStep } from './synth_engine.js';

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
console.log(`${fx.cases.length} synth cases (${samples} samples) and ${fx.automation.length} automation ticks: ` +
  (failed ? `${failed} FAILED` : 'all match Python within 1e-9'));
process.exit(failed ? 1 : 0);

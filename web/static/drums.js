// Drum machine page: the desktop's 12 x 32 step sequencer (drum_machine.py) in the browser. Timing, offline render,
// WAV/MIDI export and presets come from drum_engine.js (a tested port of drum_engine.py); sounds from drum_kit.js.
import { route, app, api, esc, isStatic, needsServer, onLeave, download, $ } from './core.js';
import * as de from './drum_engine.js';
import { buildKit } from './drum_kit.js';
import { encodeWav } from './wav_writer.js';
import { buildMidi } from './midi_writer.js';
import { audioContext, toBuffer, decodeMono, drawScope, sha256hex } from './audio.js';
import { gridHtml, paintGrid } from './drum_grid.js';

const kit = buildKit();
const st = { pattern: de.examplePattern(), bpm: 100, volumes: [...de.EXAMPLE_VOLUMES], custom: new Array(de.ROWS).fill(null),
  names: [...de.SAMPLE_NAMES], playing: false, step: -1 };

const sampleFor = r => st.custom[r] || kit[r];
const samples = () => st.pattern.map((_, r) => sampleFor(r));

route('drums', async () => {
  const info = await api('/info');
  app().innerHTML = `
  <p class="kicker">drum_machine.py · step sequencer</p>
  <h1 class="glow">Drum machine</h1>
  <p class="lead">${info.drums.rows} instruments x ${info.drums.cols} sixteenth-note steps, ${info.drums.bpm[0]}-${info.drums.bpm[1]} BPM, a volume per
  row. Click cells to edit the pattern, then Play. The step clock is the desktop's own: ${'60000 // BPM // 4'} whole
  milliseconds per step (${info.drums.step_ms[info.drums.bpm[2]]} ms at ${info.drums.bpm[2]} BPM).</p>
  <div class="actions">
    <button id="play">Play</button>
    <div class="bpm"><label for="bpm">BPM <b id="bpmv"></b></label>
      <input type="range" id="bpm" min="${info.drums.bpm[0]}" max="${info.drums.bpm[1]}" value="${st.bpm}"></div>
    <button class="alt" id="clear">Clear</button><button class="alt" id="example">Example beat</button>
  </div>
  <div class="gridwrap" id="gridwrap">${gridHtml(st)}</div>
  <h3>Mix of the current step (as the desktop's waveform view: the raw sounds of the hits, summed)</h3>
  <canvas class="scope" id="scope" role="img" aria-label="Waveform of the sounds triggered on the current step"></canvas>
  <div class="two">
    <section class="panel">
      <h3>Export</h3>
      <div class="row"><div><label for="loops">Passes of the pattern</label>
        <select id="loops"><option>1</option><option selected>2</option><option>4</option><option>8</option></select></div></div>
      <div class="actions"><button id="wav">Download WAV</button><button id="midi">Download MIDI</button></div>
      <p class="small mute">WAV: the pattern mixed offline, peak-normalised to 95%, 16-bit stereo 44.1 kHz, as the
      desktop AudioExporter writes it. MIDI: one General MIDI drum track (channel 10), a note per hit lasting one
      step, velocity = row volume, through the desktop MidiExporter's layout (480 ticks per beat at 120 BPM).</p>
      <div id="pycheck"></div>
    </section>
    <section class="panel">
      <h3>Sounds and presets</h3>
      <div class="row"><div><label for="row">Load your own sample into row</label>
        <select id="row">${st.names.map((n, r) => `<option value="${r}">${r + 1}: ${esc(n)}</option>`).join('')}</select></div>
        <div><label for="file">Audio file (WAV, MP3, OGG...)</label><input type="file" id="file" accept="audio/*"></div></div>
      <div class="actions"><button class="alt" id="resetkit">Back to the built-in kit</button></div>
      <div class="actions"><button class="alt" id="savep">Save .preset</button>
        <label class="btn alt" for="loadp">Load .preset</label><input type="file" id="loadp" accept=".preset,.json" hidden></div>
      <p class="small mute">Built-in sounds are synthesised in your browser (drum_kit.py), the same as the desktop's
      samples/ files. Your files stay in your browser. Presets use the desktop
      DrumPreset format (pattern, BPM, volumes) and load in either app.</p>
      <p id="msg" class="small"></p>
    </section>
  </div>`;
  const bpm = $('#bpm'), bpmv = $('#bpmv');
  const showBpm = () => { bpmv.textContent = `${st.bpm} (${de.stepIntervalMs(st.bpm)} ms/step)`; };
  showBpm();
  bpm.addEventListener('input', () => { st.bpm = +bpm.value; showBpm(); });
  const grid = $('#gridwrap');
  grid.addEventListener('click', e => {
    const b = e.target.closest('button.cell');
    if (!b) return;
    const r = +b.dataset.r, c = +b.dataset.c;
    st.pattern[r][c] = st.pattern[r][c] ? 0 : 1;
    paintGrid(grid, st);
  });
  grid.addEventListener('input', e => {
    if (e.target.dataset.vol !== undefined) { st.volumes[+e.target.dataset.vol] = +e.target.value; }
  });
  const redraw = () => { grid.innerHTML = gridHtml(st); };
  $('#clear').onclick = () => { st.pattern = de.emptyPattern(); paintGrid(grid, st); };
  $('#example').onclick = () => { st.pattern = de.examplePattern(); st.volumes = [...de.EXAMPLE_VOLUMES]; redraw(); };
  $('#play').onclick = () => (st.playing ? stop() : play());
  $('#wav').onclick = () => {
    const audio = de.renderPattern(st.pattern, samples(), st.bpm, st.volumes, +$('#loops').value);
    download(`drums_${st.bpm}bpm.wav`, new Blob([encodeWav(audio)], { type: 'audio/wav' }));
  };
  $('#midi').onclick = () => {
    const tracks = de.patternToMidiTracks(st.pattern, st.bpm, st.volumes, +$('#loops').value, st.names);
    download(`drums_${st.bpm}bpm.mid`, new Blob([buildMidi(tracks)], { type: 'audio/midi' }));
  };
  const msg = t => { $('#msg').textContent = t; };
  $('#file').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    const r = +$('#row').value;
    try {
      st.custom[r] = await decodeMono(audioContext(), f);
      st.names[r] = f.name; redraw(); msg(`Row ${r + 1} now plays ${f.name}.`);
    } catch (err) { msg(`Could not decode ${f.name}: ${err.message}`); }
    e.target.value = '';
  };
  $('#resetkit').onclick = () => { st.custom.fill(null); st.names = [...de.SAMPLE_NAMES]; redraw(); msg('Built-in kit restored.'); };
  $('#savep').onclick = () => {
    const now = Date.now() / 1000;
    const preset = { name: 'web pattern', type: 'drum', data: de.presetData(st.pattern, st.bpm, st.volumes), tags: ['web'],
      created_at: now, modified_at: now };
    download('web pattern.preset', JSON.stringify(preset), 'application/json');
  };
  $('#loadp').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const j = JSON.parse(await f.text());
      const p = de.fromPresetData(j.data || j);
      Object.assign(st, { pattern: p.pattern, bpm: p.bpm, volumes: p.volumes });
      bpm.value = st.bpm; showBpm(); redraw(); msg(`Loaded ${f.name}.`);
    } catch (err) { msg(`Not a drum preset: ${err.message}`); }
    e.target.value = '';
  };
  setupPythonCheck();
  drawStepMix(0);
  onLeave(stop);
});

// ---- playback: a look-ahead scheduler on the AudioContext clock, one step every stepIntervalMs ---------------------
let timer = 0, nextTime = 0, nextStep = 0, raf = 0, queue = [];
function play() {
  const ac = audioContext();
  st.playing = true; $('#play').textContent = 'Stop';
  nextTime = ac.currentTime + 0.06; nextStep = 0; queue = [];
  const buffers = samples().map(s => toBuffer(ac, s));
  const tick = () => {
    while (nextTime < ac.currentTime + 0.12) {
      st.pattern.forEach((line, r) => {
        if (!line[nextStep] || st.volumes[r] <= 0) return;
        const src = ac.createBufferSource(), g = ac.createGain();
        src.buffer = buffers[r]; g.gain.value = st.volumes[r] / 100;
        src.connect(g).connect(ac.destination); src.start(nextTime);
      });
      queue.push([nextTime, nextStep]);
      nextTime += de.stepIntervalMs(st.bpm) / 1000;
      nextStep = (nextStep + 1) % de.COLS;
    }
  };
  tick();
  timer = setInterval(tick, 25);
  const frame = () => {
    while (queue.length && queue[0][0] <= ac.currentTime) {
      st.step = queue.shift()[1];
      const g = $('#gridwrap');
      if (g) { paintGrid(g, st); drawStepMix(); }
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
}
function stop() {
  clearInterval(timer); cancelAnimationFrame(raf);
  st.playing = false; st.step = -1;
  const b = $('#play'), g = $('#gridwrap');
  if (b) b.textContent = 'Play';
  if (g) paintGrid(g, st);
}
// DrumMachineGUI.update_beat: 1 s buffer, every hit's sample added from the start (samples longer than 1 s skipped).
function drawStepMix(step = st.step) {
  const mix = new Float64Array(44100);
  st.pattern.forEach((line, r) => {
    const s = sampleFor(r);
    if (line[step] && s.length <= mix.length) for (let i = 0; i < s.length; i++) mix[i] += s[i];
  });
  const c = $('#scope');
  if (c) drawScope(c, [mix], { yRange: 'auto' });
}

function setupPythonCheck() {
  const host = $('#pycheck');
  if (isStatic()) { host.innerHTML = needsServer('Re-rendering this pattern with the Python code'); return; }
  host.innerHTML = '<button class="alt" id="pybtn">Check against the Python</button><p class="small" id="pyout"></p>';
  $('#pybtn').onclick = async () => {
    const out = $('#pyout');
    if (st.custom.some(Boolean)) { out.textContent = 'The Python check uses the built-in kit: restore it first.'; return; }
    out.textContent = 'Rendering with Python...';
    const loops = +$('#loops').value;
    try {
      const py = await api('/drums/render', { body: { pattern: st.pattern, bpm: st.bpm, volumes: st.volumes, loops } });
      const wav = encodeWav(de.renderPattern(st.pattern, kit, st.bpm, st.volumes, loops));
      const midi = buildMidi(de.patternToMidiTracks(st.pattern, st.bpm, st.volumes, loops));
      const [w, m] = [await sha256hex(wav), await sha256hex(midi)];
      out.innerHTML = `WAV (${wav.length} bytes): <b class="${w === py.wav_sha256 ? 'ok' : 'err'}">${w === py.wav_sha256 ? 'identical' : 'differs'}</b>
        · MIDI (${midi.length} bytes): <b class="${m === py.midi_sha256 ? 'ok' : 'err'}">${m === py.midi_sha256 ? 'identical' : 'differs'}</b>
        <span class="mute">(SHA-256 of the browser's bytes vs the Python's)</span>`;
    } catch (err) { out.textContent = err.message; }
  };
}

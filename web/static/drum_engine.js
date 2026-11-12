// Drum machine logic: a port of drum_engine.py (grid, step timing, offline render, MIDI tracks, preset data).
// Checked against tests/fixtures/drum_fixture.json (drum_engine.test.mjs).
export const ROWS = 12, COLS = 32, SR = 44100;
export const SAMPLE_NAMES = ['Kick', 'Snare', 'Hi-Hat', 'Clap', 'Tom 1', 'Tom 2', 'Crash', 'Ride', 'Perc 1', 'Perc 2',
  'FX 1', 'FX 2'];
export const BPM_MIN = 60, BPM_MAX = 180, BPM_DEFAULT = 120;
export const GM_NOTES = [36, 38, 42, 39, 48, 45, 49, 51, 56, 37, 75, 70];
const EXAMPLE_STEPS = { 0: [0, 8, 16, 22, 24], 1: [8, 24], 2: [...Array(16).keys()].map(i => 2 * i), 3: [30], 6: [0],
  8: [6, 14], 9: [12, 28], 10: [31] };
export const EXAMPLE_VOLUMES = [100, 90, 55, 70, 100, 100, 60, 60, 50, 60, 45, 100];

// The desktop QTimer interval per 16th-note step: 60000 // bpm // 4 whole milliseconds.
export const stepIntervalMs = bpm => Math.floor(Math.floor(60000 / Math.trunc(bpm)) / 4);
export function stepOffsets(nSteps, bpm, sr = SR) {
  const ms = stepIntervalMs(bpm);
  return Array.from({ length: nSteps }, (_, k) => Math.floor(k * ms * sr / 1000));
}
export const emptyPattern = () => Array.from({ length: ROWS }, () => new Array(COLS).fill(0));
export function examplePattern() {
  const p = emptyPattern();
  for (const [r, steps] of Object.entries(EXAMPLE_STEPS)) for (const c of steps) p[r][c] = 1;
  return p;
}

// Offline mix: each active step starts its row's sample scaled by volume/100; runs loops passes + the longest sample.
export function renderPattern(pattern, samples, bpm, volumes = null, loops = 1, sr = SR) {
  volumes = volumes || new Array(ROWS).fill(100);
  const cols = pattern.length ? pattern[0].length : COLS, nSteps = cols * loops;
  const offsets = stepOffsets(nSteps + 1, bpm, sr);
  const longest = Math.max(0, ...samples.filter(Boolean).map(s => s.length));
  const out = new Float64Array(offsets[nSteps] + longest);
  for (let k = 0; k < nSteps; k++) {
    const step = k % cols;
    pattern.forEach((line, row) => {
      const s = samples[row];
      if (line[step] && s && volumes[row] > 0) {
        const start = offsets[k], g = volumes[row] / 100;
        for (let i = 0; i < s.length; i++) out[start + i] += s[i] * g;
      }
    });
  }
  return out;
}

export function patternToMidiTracks(pattern, bpm, volumes = null, loops = 1, names = SAMPLE_NAMES) {
  volumes = volumes || new Array(ROWS).fill(100);
  const cols = pattern.length ? pattern[0].length : COLS, ms = stepIntervalMs(bpm), notes = [];
  for (let k = 0; k < cols * loops; k++) {
    pattern.forEach((line, row) => {
      if (line[k % cols] && volumes[row] > 0) {
        notes.push({ note: GM_NOTES[row], start_time: k * ms / 1000, end_time: (k + 1) * ms / 1000,
          velocity: Math.max(1, Math.min(127, Math.trunc(volumes[row]))) });
      }
    });
  }
  const used = pattern.map((line, r) => (line.some(Boolean) ? names[r] : null)).filter(Boolean);
  return [{ name: 'Drums: ' + used.join(', '), channel: 9, notes }];
}

// DrumPreset data (preset_manager.py): {"pattern": {"row,col": bool}, "bpm": int, "volumes": {"row": 0-1}}.
export function presetData(pattern, bpm, volumes) {
  const p = {};
  pattern.forEach((line, r) => line.forEach((v, c) => { p[`${r},${c}`] = !!v; }));
  return { pattern: p, bpm: Math.trunc(bpm), volumes: Object.fromEntries(volumes.map((v, r) => [String(r), v / 100])) };
}
export function fromPresetData(data) {
  const pattern = emptyPattern();
  for (const [pos, on] of Object.entries(data.pattern || {})) {
    const [r, c] = pos.split(',').map(Number);
    if (r >= 0 && r < ROWS && c >= 0 && c < COLS && on) pattern[r][c] = 1;
  }
  const bpm = Math.min(BPM_MAX, Math.max(BPM_MIN, Math.trunc(data.bpm ?? BPM_DEFAULT)));
  const volumes = new Array(ROWS).fill(100);
  for (const [r, v] of Object.entries(data.volumes || {})) if (+r >= 0 && +r < ROWS) volumes[+r] = Math.round(+v * 100);
  return { pattern, bpm, volumes };
}

// Home page: hero, counts from the API (all read from the Python modules), entry cards.
import { route, api, app, list, esc } from './core.js';

const DOORS = [
  ['#/drums', 'Drum machine', 'The 12 x 32 step sequencer: edit a beat, play it, download it as WAV or General MIDI, save desktop presets.'],
  ['#/synth', 'Sound generator', 'Wave, noise, FM and held-note tracks with reverb, distortion, EQ, vibrato, tremolo, chorus and low-pass, automated dials and a scope.'],
  ['#/piano', 'Piano keyboard', 'Three octaves you can play from the computer keyboard, with ADSR, filter, harmonics, effects and pitch bend.'],
  ['#/verify', 'Verify', 'Your browser recomputes the Python reference results: sample buffers, timing, WAV and MIDI bytes.'],
  ['#/about', 'About', 'What the desktop app is, what this site covers and leaves out, how to run both.'],
];

route('home', async () => {
  const info = await api('/info');
  const fx = info.synth.effects;
  app().innerHTML = `
  <section class="hero">
    <p class="kicker">PyQt5 DAW · in your browser</p>
    <h1 class="glow">Music Production Platform</h1>
    <p class="lead">${esc(info.summary)} This site is a working browser version of its instruments: the drum machine's
    sequencer and the sound generator's DSP are ported line for line from the Python and tested against it, sample for
    sample and byte for byte.</p>
    <a class="btn" href="#/drums">Open the drum machine</a><a class="btn alt" href="#/synth">Sound generator</a>
    <p class="small mute">Sound starts only after you press Play, Start or a key.</p>
  </section>
  <div class="tiles">
    <div class="tile"><b>${info.drums.rows} x ${info.drums.cols}</b><span>drum rows x steps</span></div>
    <div class="tile"><b>${info.drums.bpm[0]}-${info.drums.bpm[1]}</b><span>BPM</span></div>
    <div class="tile"><b>${info.synth.track_types.length}</b><span>sound generator track types</span></div>
    <div class="tile"><b>${fx.filter(e => e.web).length} of ${fx.length}</b><span>track effects on the web</span></div>
    <div class="tile"><b>${info.piano.octaves * 12}</b><span>piano keys, ${info.piano.sliders.length} sliders</span></div>
    <div class="tile"><b>WAV · MIDI</b><span>export, as the desktop exporters write them</span></div>
  </div>
  <div class="grid wide">${list(DOORS, ([href, t, d]) => `<a class="card" href="${href}"><b>${t}</b><span>${d}</span></a>`)}</div>`;
});

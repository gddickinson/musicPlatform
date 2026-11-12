// About page: what the desktop app is, what the web version covers, how to run both, credits (from the README).
import { route, app, api, esc } from './core.js';

route('about', async () => {
  const info = await api('/info');
  const omitted = info.synth.effects.filter(e => !e.web);
  app().innerHTML = `
  <p class="kicker">about</p>
  <h1 class="glow">About</h1>
  <p class="lead">${esc(info.summary)}</p>
  <h2>What runs here</h2>
  <div class="scroll"><table>
    <tr><th>Desktop component</th><th>On this site</th></tr>
    <tr><td>Drum machine (drum_machine.py)</td><td>Yes: grid, tempo, volumes, playback, your own samples, presets; plus WAV and
      MIDI export of the pattern through the desktop exporters' formats. Timing, mix, WAV and MIDI are exact ports
      (drum_engine.py).</td></tr>
    <tr><td>Sound generator (sound_generator.py)</td><td>Yes: wave / noise / FM / held-note tracks, automated dials, the effects
      rack, scope, presets, WAV. Exact port of synth_dsp.py${omitted.length ? `, except ${omitted.map(e => esc(e.name)).join(', ')}` : ''}.</td></tr>
    <tr><td>Piano keyboard (piano_keyboard.py)</td><td>Yes, with the same controls; the pyo sound chain is approximated with
      WebAudio nodes.</td></tr>
    <tr><td>Sample pad, recording studio, mixer, routing matrix, project manager, MIDI controller</td><td>Not on the web:
      they work on files on disk, the microphone or MIDI hardware, or only connect the other components.</td></tr>
  </table></div>
  ${omitted.map(e => `<p class="callout small"><b>${esc(e.name)}</b> is left out: ${esc(e.omitted_because)}</p>`).join('')}
  <h2>Sounds</h2>
  <p>The drum rows play a synthesised kit (drum_kit.py: swept sines, FM, seeded noise and simple filters). The repo's own
  WAV files (samples/, wav/) carry no stated source or licence, so they are not published here; the desktop app still
  loads them, and on this page you can load any file of your own into a row.</p>
  <h2>Run it</h2>
  <h3>Desktop app</h3>
  <pre>pip install -r requirements.txt
python main.py</pre>
  <p class="small mute">PyQt5, NumPy, SciPy, PyAudio, pygame, pyqtgraph, QDarkStyle, soundfile and mido. The piano needs
  pyo for sound.</p>
  <h3>Web app (this site, plus the Python checks)</h3>
  <pre>pip install -r requirements-web.txt
python run_web.py        # http://127.0.0.1:8167</pre>
  <p>The local app adds a button on the drum machine page that renders your pattern with the Python code and compares
  the WAV and MIDI bytes with the browser's.</p>
  <h2>Credits</h2>
  <p>Music Production Platform by George Dickinson (MIT licence), built with AI assistance from Claude (Anthropic).
  Source: <a href="https://github.com/gddickinson/musicPlatform">github.com/gddickinson/musicPlatform</a>.</p>`;
});

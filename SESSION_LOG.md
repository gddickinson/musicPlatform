# Session log

## 2026-11-12: web interface and static GitHub Pages site (branch `web-interface`)

- Factored the GUI-free logic out so the web app and tests can use it without Qt/PyAudio: `synth_dsp.py` (sound
  generator tracks and effects, moved unchanged first), `drum_engine.py`, `midi_export.py`, `wav_export.py`,
  `piano_spec.py`; the GUIs import them back (all four GUIs still build offscreen; tests pass).
- Bugs fixed (each with a failing-first regression test, separate commits):
  - Sound generator: scope redraw advanced every oscillator (audio skipped a buffer per redraw); continuous notes
    restarted their sine every buffer (clicks) and had no `.note` (octave selector crashed); pink/brown noise, EQ and
    low-pass reset filter state each buffer; low-pass cutoff slider did nothing; distortion amount 0 gave NaN;
    EQ at default gains (1, 1) was not flat (output low+high-signal); chorus at zero delay read the oldest sample;
    switched-on effects ignored their sliders.
  - MIDI export failed on any chord (negative delta) and put control changes after the last note.
  - Drum machine: samples looked up relative to the working folder; 32 stacked volume dials/FX buttons per row.
  - Presets: DrumPreset NameError (QDial); SoundGeneratorPreset NameErrors, add_track returned None, effect names
    never matched, held-note tracks saved without a type (applied to the previous track on load).
  - Piano without pyo: every key press raised (placeholder lacked Biquad and arithmetic).
- Web: drum machine, sound generator (AudioWorklet), piano (WebAudio approximation of pyo), verify, about pages.
  JS engines checked by node tests against `tests/fixtures/` (19 synth cases within 1e-9; 121 tempos; 12 kit voices;
  3 renders with identical WAV and MIDI bytes). libsndfile 1.2 writes PCM_16 as rint(x * 2^31) >> 16, which the
  browser's WAV writer reproduces.
- Drum sounds on the web are synthesised (`drum_kit.py`): samples/ and wav/ have no stated source or licence.
- Needs George: ReverbEffect formula (ROADMAP); whether the repo WAVs may be published (then the site could use them).
- Tests: `pytest tests` 41 passed; node suites pass; screenshots.py --static and --base (port 8167) all ok, phone 0 px.

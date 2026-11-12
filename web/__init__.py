"""Web interface for the Music Production Platform.

- app.py: FastAPI app (routes under /api, STATIC_ENDPOINTS exported for the static GitHub Pages site).
- static/: the front end (plain ES modules): drum machine, sound generator and piano keyboard ported to the browser
  (drum_engine.js, drum_kit.js, synth_engine.js, synth_worklet.js, midi_writer.js, wav_writer.js) with node tests
  (*.test.mjs) against the Python modules, plus the pages (home, drums, synth, piano, verify, about).
"""

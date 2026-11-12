# Music Production Platform - Interface Map

## Entry Point
- **main.py**: Application entry point. Sets up logging, checks dependencies, creates QApplication with QDarkStyle, launches `EnhancedMainGUI`.

## Core GUI
- **enhanced_main_gui.py**: Main window (`EnhancedMainGUI`). Tabbed interface integrating all instruments, project/preset management, and mixer. This is the active main GUI.
- **_archive/main_gui.py**: Legacy simpler GUI (superseded by enhanced_main_gui.py).

## Instruments / Components
- **piano_keyboard.py**: `PianoKeyboardWindow` - Interactive piano keyboard with MIDI support.
- **drum_machine.py**: `DrumMachineGUI` - Step sequencer drum machine.
- **sample_pad.py**: `SamplePadWindow` - Sample trigger pad interface.
- **sound_generator.py**: `EnhancedSoundGeneratorGUI` - Synthesizer with waveform generation.
- **recording_studio.py**: `RecordingStudioGUI` - Audio recording interface.

## Qt-free logic (used by the GUIs, the web app and the tests)
- **synth_dsp.py**: sound generator DSP: `Track`, `WaveTrack`, `NoiseTrack`, `FMSynthTrack`, `ContinuousNoteTrack`
  (`generate_audio(n)`, `preview(n)`), effects (`ReverbEffect`, `DistortionEffect`, `EQEffect`, `VibratoEffect`,
  `TremoloEffect`, `ChorusEffect`, `LowPassFilter`), `EFFECT_PARAMS`, `DIAL_RANGES`, `automation_step()`.
  sound_generator.py and preset_manager.py import from it.
- **reverb_dsp.py**: `ReverbEffect` (Freeverb-style: 8 damped combs + 4 allpasses, mix, peak guard `PEAK_FACTOR`=2),
  processed in <=225-sample chunks so it runs in real time; re-exported by synth_dsp.py.
- **drum_engine.py**: `ROWS`, `COLS`, `SAMPLE_NAMES`, BPM range, `step_interval_ms()`, `render_pattern()`,
  `pattern_to_midi_tracks()` (GM drums), `preset_data()` / `from_preset_data()` (DrumPreset format), `example_pattern()`.
  drum_machine.py imports its constants and timing.
- **drum_kit.py**: `build_kit()`: 12 synthesised drum voices (the web's sounds; the repo WAVs have no stated licence).
- **midi_export.py**: `build_midi(tracks)` -> mido MidiFile (absolute-time events; used by `MidiExporter`).
- **wav_export.py**: `normalize_buffer()` (used by `AudioExporter`), `encode_wav()`.
- **piano_spec.py**: `SLIDERS`, `WAVEFORMS`, `KEY_MAP`, `note_to_freq()` (piano_keyboard.py imports them).

## Web interface (`web/`)
- **web/app.py**: FastAPI app: `GET /api/info`, `GET /api/verify` (Python reference results), `POST /api/drums/render`
  (Python WAV/MIDI hashes); `STATIC_ENDPOINTS` for the static export. Started by **run_web.py** (port 8167).
- **web/static/**: ES-module front end (no build step). Engines (pure, node-tested against the Python):
  `synth_engine.js` (synth_dsp.py), `drum_engine.js` (drum_engine.py), `drum_kit.js` (drum_kit.py),
  `midi_writer.js` (midi_export.py + mido bytes), `wav_writer.js` (wav_export.py + libsndfile bytes);
  `synth_worklet.js` runs the synth engine in an AudioWorklet. Pages: `home.js`, `drums.js` (+ `drum_grid.js`),
  `synth.js` (+ `synth_ui.js`), `piano.js` (+ `piano_audio.js`, WebAudio approximation of the pyo chain),
  `verify.js`, `about.js`; shared `core.js`, `audio.js`, `static_api.js`, `background.js`, `main.js`.
- **scripts/build_static.py** (static site), **scripts/screenshots.py** (smoke test, README images),
  **scripts/make_fixtures.py** (writes tests/fixtures/*.json for the node tests).

## Audio Infrastructure
- **audio_system.py**: `AudioSystem` - Core audio engine using PyAudio. Handles streams, buffers, playback.
- **audio_routing.py**: `RoutingMatrix`, `AudioNode`, `ComponentNode`, `MixerNode`, `EffectNode` - Signal routing between components.
- **audio_export.py**: Audio file export functionality (WAV, FLAC, etc.).
- **mixer.py**: Mixer interface with volume, pan, and effects per channel.

## Management
- **preset_manager.py**: `PresetManagerWidget`, `Preset`, `PianoPreset`, `DrumPreset`, `SoundGeneratorPreset` - Save/load presets.
- **project_manager.py**: `ProjectManagerWidget`, `Project` - Project save/load/management.

## Utilities
- **logger.py**: `get_logger()` - Centralized logging setup.
- **file_dialog_utils.py**: File dialog helpers.
- **integration.py**: `IntegratedControlPanel` - Connects components together.
- **midi_controller.py**: MIDI hardware controller support.

## Other
- **setup_script.py**: Environment setup/installation helper.
- **run_music_platform.sh**: Shell launcher script.
- **tests/**: pytest: test_smoke.py (imports, logger), test_synth_dsp.py, test_midi_export.py,
  test_drum_and_presets.py, test_piano.py, test_reverb.py (regressions for fixed bugs), test_fixtures_current.py, test_web.py;
  conftest.py pins offscreen Qt / PyQt5. Node tests: web/static/*.test.mjs.
- **_archive/**: Legacy files (old main_gui.py, old unit tests with space-named directory).

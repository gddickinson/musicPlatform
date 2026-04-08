# Music Production Platform — Roadmap

## Current State
A feature-rich PyQt5 DAW with piano keyboard, drum machine, sample pad, sound generator, recording studio, mixer, and preset/project management. Well-organized into separate files per component (`piano_keyboard.py`, `drum_machine.py`, `mixer.py`, etc.). Has a tabbed UI with QDarkStyle theming, MIDI controller support, and audio routing. The directory named `unit tests` (with a space) suggests tests exist but naming is non-standard.

## Short-term Improvements
- [x] Rename `unit tests/` to `tests/` — spaces in directory names cause import and tooling issues
- [x] Add a `requirements.txt` with pinned versions (PyQt5, numpy, pyaudio, pygame, scipy, pyqtgraph, qdarkstyle, soundfile)
- [ ] Add error handling in `audio_system.py` for when PyAudio devices are unavailable or busy
- [ ] Add graceful shutdown in `main.py` to release audio resources on exit
- [ ] Add logging throughout instrument modules using the existing `logger.py` infrastructure
- [ ] Validate audio parameters (sample rate, buffer size) in `audio_system.py` before stream creation
- [ ] Add docstrings to public classes in `enhanced_main_gui.py`, `mixer.py`, and `integration.py`

## Feature Enhancements
- [ ] Add a waveform display widget showing real-time audio output in the mixer
- [ ] Add undo/redo support for drum machine pattern editing
- [ ] Implement click track / metronome for the recording studio
- [ ] Add keyboard shortcut reference dialog accessible from the Help menu
- [ ] Support drag-and-drop of audio files onto sample pads
- [ ] Add VST/AU plugin hosting via `pedalboard` or `dawdreamer` libraries
- [ ] Add a master bus with limiter/compressor in `mixer.py`

## Long-term Vision
- [ ] Migrate from PyAudio to a more robust backend (e.g., `sounddevice` or PortAudio directly)
- [ ] Add a timeline/arrangement view for multi-track composition
- [ ] Support MIDI file import/export for interoperability with other DAWs
- [ ] Add automation lanes for mixer parameters (volume, pan, effects)
- [ ] Package as a standalone app using PyInstaller or cx_Freeze

## Technical Debt
- [x] Audit `main_gui.py` vs `enhanced_main_gui.py` — consolidate if `main_gui.py` is legacy
- [ ] Standardize signal/slot naming conventions across all PyQt5 modules
- [ ] Add type hints across all modules (especially `audio_routing.py` and `integration.py`)
- [ ] Write integration tests that verify audio routing connections between instruments and mixer
- [ ] Move hardcoded file paths in `preset_manager.py` and `project_manager.py` to config
- [x] Clean up `__pycache__` and add a proper `.gitignore`

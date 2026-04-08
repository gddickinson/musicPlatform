# Music Production Platform

A digital audio workstation (DAW) built with Python and PyQt5. The platform integrates a piano keyboard, drum machine, sample pad, sound generator, recording studio, mixer, and project/preset management into a single tabbed interface with a dark theme (QDarkStyle).

## Features

### Instruments and Tools
- **Piano Keyboard** (`piano_keyboard.py`): Virtual piano with mouse and computer-keyboard input, real-time sound synthesis, customizable instrument presets
- **Drum Machine** (`drum_machine.py`): Grid-based rhythm sequencer with adjustable tempo, per-sample volume, and custom drum sample import
- **Sample Pad** (`sample_pad.py`): Trigger and manipulate audio samples with real-time effects
- **Sound Generator** (`sound_generator.py`): Synthesizer with multiple waveforms (sine, square, saw, triangle), ADSR envelopes, and effects chain
- **Recording Studio** (`recording_studio.py`): Multi-track audio recording and playback

### Audio Engine
- **Audio System** (`audio_system.py`): Core audio engine built on PyAudio for real-time sound output
- **Audio Routing** (`audio_routing.py`): Flexible signal routing between instruments, effects, and outputs
- **Audio Export** (`audio_export.py`): Export projects and tracks to WAV and other formats
- **Mixer** (`mixer.py`): Multi-channel mixer with audio buses, per-channel volume/pan/mute/solo

### Management
- **Project Manager** (`project_manager.py`): Save, load, and organize complete project sessions
- **Preset Manager** (`preset_manager.py`): Create, save, and load presets for piano, drum, sound generator, effects, mixer, samples, and tracks
- **MIDI Controller** (`midi_controller.py`): Connect and map external MIDI hardware
- **Integration Panel** (`integration.py`): Unified control panel linking all components

### Effects
- Reverb, delay, chorus, distortion, and more
- Per-instrument ADSR envelope shaping
- Real-time pitch bend modulation

## Project Structure

```
musicPlatform/
├── main.py                  # Entry point (dependency check, environment setup)
├── enhanced_main_gui.py     # Main tabbed window (EnhancedMainGUI)
├── piano_keyboard.py        # Piano keyboard instrument
├── drum_machine.py          # Drum machine sequencer
├── sample_pad.py            # Sample trigger pads
├── sound_generator.py       # Waveform synthesizer
├── recording_studio.py      # Multi-track recording
├── audio_system.py          # Core audio engine
├── audio_routing.py         # Signal routing
├── audio_export.py          # Export to file
├── mixer.py                 # Multi-channel mixer
├── integration.py           # Integrated control panel
├── project_manager.py       # Project save/load
├── preset_manager.py        # Preset management
├── midi_controller.py       # MIDI hardware support
├── file_dialog_utils.py     # File dialog helpers
├── logger.py                # Logging configuration
├── setup_script.py          # Dependency installer
├── run_music_platform.sh    # Shell launch script
├── presets/                  # Preset storage (drum, effect, mixer, piano, sample, sound, track)
├── samples/                 # Audio sample files
├── wav/                     # WAV file storage
├── projects/                # Saved project files
├── logs/                    # Application logs
└── unit tests/              # Test suite
```

## Requirements

- Python >= 3.8
- PyQt5 >= 5.15
- NumPy >= 1.19
- PyAudio
- Pygame >= 2.0
- SciPy >= 1.5
- pyqtgraph >= 0.12
- qdarkstyle
- soundfile (for audio export)

Optional:
- librosa (advanced audio analysis)
- matplotlib (visualization)
- pydub (additional export formats)
- rtmidi / mido (MIDI hardware)

## Installation

Install dependencies automatically:

```bash
python setup_script.py
```

Or install manually:

```bash
pip install PyQt5 numpy pyaudio pygame scipy pyqtgraph qdarkstyle soundfile
```

## Usage

```bash
python main.py
```

Or use the shell script:

```bash
./run_music_platform.sh
```

The application opens a tabbed window with sections for each instrument, the mixer, project manager, preset manager, and integration panel. Switch between tools using the tab bar at the top.

## GUI Framework

Built with **PyQt5** and styled with **QDarkStyle** for a dark production-oriented interface.

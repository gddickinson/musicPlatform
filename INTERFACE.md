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
- **tests/**: Unit tests (test_smoke.py with import and logger tests).
- **_archive/**: Legacy files (old main_gui.py, old unit tests with space-named directory).

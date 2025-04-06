"""
Piano Keyboard Module for the Music Production Platform.

This module provides a virtual piano keyboard interface with sound synthesis
capabilities, envelope control, and audio effects.
"""

import os
import time
import json
import traceback
from typing import Dict, List, Optional, Tuple, Union, Any, Set, Callable

from PyQt5.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QCheckBox,
    QComboBox, QDial, QFileDialog, QGridLayout, QMainWindow, QAction, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

# Import pyo for audio synthesis
try:
    from pyo import *
except ImportError:
    # Fallback implementation if pyo isn't available
    class PyoEmulator:
        """Placeholder class when pyo is not available."""
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            """Return a dummy function for any attribute access."""
            def dummy(*args, **kwargs):
                return PyoEmulator()
            return dummy

    # Create mock classes
    Server = PyoEmulator
    Sine = PyoEmulator
    LFO = PyoEmulator
    Adsr = PyoEmulator
    SndTable = PyoEmulator
    Osc = PyoEmulator
    PyoObject = PyoEmulator
    WGVerb = PyoEmulator
    Delay = PyoEmulator
    Chorus = PyoEmulator
    Disto = PyoEmulator

# Import the logger
from logger import get_logger

# Set up module logger
logger = get_logger(__name__)


class PianoError(Exception):
    """Base exception for piano keyboard-related errors."""
    pass


class SoundGenerationError(PianoError):
    """Exception raised for errors related to sound generation."""
    pass


class PresetError(PianoError):
    """Exception raised for errors related to presets."""
    pass


class AudioEffectError(PianoError):
    """Exception raised for errors related to audio effects."""
    pass


class PianoKey(QPushButton):
    """
    A piano key widget that can be pressed and released.

    Represents a single key on the piano keyboard with its visual
    representation and state management.

    Attributes:
        note: The musical note this key represents (e.g., "C4")
        is_black: Whether this is a black key
        default_color: The default color of the key
    """

    def __init__(self, note: str, is_black: bool = False, parent: Optional[QWidget] = None):
        """
        Initialize a piano key.

        Args:
            note: The musical note this key represents (e.g., "C4")
            is_black: Whether this is a black key
            parent: Parent widget
        """
        super().__init__(parent)
        self.note = note
        self.is_black = is_black
        self.setFixedSize(35 if is_black else 55, 160 if is_black else 240)
        self.default_color = "black" if is_black else "white"
        self.setStyleSheet(self.get_style(self.default_color))
        self.setText(note)
        logger.debug(f"Created piano key: {note} ({'black' if is_black else 'white'})")

    def get_style(self, bg_color: str) -> str:
        """
        Get the stylesheet for the key with the specified background color.

        Args:
            bg_color: Background color for the key

        Returns:
            Stylesheet for the key
        """
        text_color = "white" if self.is_black else "black"
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid black;
            }}
            QPushButton:pressed {{
                background-color: lightblue;
            }}
        """

    def set_color(self, color: str) -> None:
        """
        Set the key's color.

        Args:
            color: Color to set
        """
        self.setStyleSheet(self.get_style(color))

    def reset_color(self) -> None:
        """Reset the key's color to its default."""
        self.setStyleSheet(self.get_style(self.default_color))


class PianoKeyboardWindow(QMainWindow):
    """
    A window containing a piano keyboard with sound synthesis capabilities.

    This class provides a virtual piano keyboard interface with oscillators,
    envelope control, and audio effects.

    Attributes:
        notePressed: Signal emitted when a note is pressed
        noteReleased: Signal emitted when a note is released
        active_notes: Dictionary of currently active notes
        s: Pyo audio server
        current_waveform: Current oscillator waveform
        current_preset: Current preset name
        current_sound_source: Current sound source type
        keys: Dictionary of piano keys by note name
    """

    notePressed = pyqtSignal(str)
    noteReleased = pyqtSignal(str)

    def __init__(self):
        """Initialize the piano keyboard window."""
        super().__init__()
        logger.info("Initializing PianoKeyboardWindow")

        self.setWindowTitle("Advanced Piano Keyboard Synthesizer")
        self.setGeometry(100, 100, 1400, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        try:
            # Initialize audio server
            self.s = Server().boot()
            self.s.start()
            logger.debug("Audio server started")
        except Exception as e:
            logger.error(f"Error initializing audio server: {str(e)}")
            logger.debug(traceback.format_exc())
            # Create a dummy server for fallback
            self.s = Server()

        # Initialize attributes
        self.active_notes: Dict[str, Dict[str, Any]] = {}
        self.sustain_indefinite = False
        self.polyphony_limit = 8
        self.samples: Dict[str, Any] = {}
        self.current_preset = "Default"
        self.current_sound_source = "Waveform"
        self.current_waveform = "Sine"
        self.current_sample = None
        self.keys: Dict[str, PianoKey] = {}

        # Create UI
        try:
            self.create_menu_bar()
            self.create_keyboard()
            self.create_effects_controls()
            logger.debug("UI created")
        except Exception as e:
            logger.error(f"Error creating UI: {str(e)}")
            logger.debug(traceback.format_exc())
            raise PianoError(f"Error initializing piano keyboard: {str(e)}")

        logger.info("PianoKeyboardWindow initialized")

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        try:
            menubar = self.menuBar()

            # File menu
            file_menu = menubar.addMenu('File')

            load_preset_action = QAction('Load Preset', self)
            load_preset_action.triggered.connect(self.load_preset)
            file_menu.addAction(load_preset_action)

            save_preset_action = QAction('Save Preset', self)
            save_preset_action.triggered.connect(self.save_preset)
            file_menu.addAction(save_preset_action)

            # Sound menu
            sound_menu = menubar.addMenu('Sound')

            self.waveform_menu = sound_menu.addMenu('Waveform')
            waveforms = ["Sine", "Square", "Sawtooth", "Triangle", "PWM"]
            for waveform in waveforms:
                action = QAction(waveform, self)
                action.triggered.connect(lambda checked, w=waveform: self.set_waveform(w))
                self.waveform_menu.addAction(action)

            self.sample_menu = sound_menu.addMenu('Sample')
            load_sample_action = QAction('Load Sample', self)
            load_sample_action.triggered.connect(self.load_sample)
            self.sample_menu.addAction(load_sample_action)

            logger.debug("Menu bar created")
        except Exception as e:
            logger.error(f"Error creating menu bar: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def create_keyboard(self) -> None:
        """Create the piano keyboard layout."""
        try:
            octaves = 3
            white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
            black_notes = ['C#', 'D#', 'F#', 'G#', 'A#']

            keyboard_widget = QWidget()
            keyboard_layout = QHBoxLayout(keyboard_widget)

            for octave in range(octaves):
                octave_layout = QHBoxLayout()
                for note in white_notes:
                    key = PianoKey(f"{note}{octave+4}")
                    key.pressed.connect(lambda n=f"{note}{octave+4}": self.notePressed.emit(n))
                    key.released.connect(lambda n=f"{note}{octave+4}": self.noteReleased.emit(n))
                    octave_layout.addWidget(key)
                    self.keys[f"{note}{octave+4}"] = key

                black_key_layout = QHBoxLayout()
                black_key_layout.addSpacing(15)
                for i, note in enumerate(black_notes):
                    key = PianoKey(f"{note}{octave+4}", is_black=True)
                    key.pressed.connect(lambda n=f"{note}{octave+4}": self.notePressed.emit(n))
                    key.released.connect(lambda n=f"{note}{octave+4}": self.noteReleased.emit(n))
                    black_key_layout.addWidget(key)
                    self.keys[f"{note}{octave+4}"] = key
                    if i == 1:
                        black_key_layout.addSpacing(40)
                    else:
                        black_key_layout.addSpacing(20)

                octave_widget = QWidget()
                octave_widget.setLayout(QVBoxLayout())
                octave_widget.layout().addLayout(black_key_layout)
                octave_widget.layout().addLayout(octave_layout)
                keyboard_layout.addWidget(octave_widget)

            self.main_layout.addWidget(keyboard_widget)

            # Connect note signals
            self.notePressed.connect(self.play_note)
            self.noteReleased.connect(self.release_note)

            logger.debug("Keyboard created")
        except Exception as e:
            logger.error(f"Error creating keyboard: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def create_effects_controls(self) -> None:
        """Create the controls for audio effects and synthesis parameters."""
        try:
            controls_widget = QWidget()
            controls_layout = QHBoxLayout(controls_widget)

            # Create sliders with common format
            sliders = [
                ("Volume", 0, 100, 80, self.update_volume),
                ("Harmonics", 0, 100, 0, self.update_harmonics),
                ("Reverb", 0, 100, 20, self.update_reverb),
                ("Delay", 0, 100, 0, self.update_delay),
                ("Chorus", 0, 100, 0, self.update_chorus),
                ("Distortion", 0, 100, 0, self.update_distortion),
                ("LFO", 0, 10, 0, self.update_lfo),
                ("Sustain", 0, 5000, 500, self.update_sustain),
                ("Filter Cutoff", 20, 20000, 20000, self.update_filter),
                ("Filter Q", 0, 100, 50, self.update_filter),
                ("Attack", 1, 1000, 10, self.update_adsr),
                ("Decay", 1, 1000, 100, self.update_adsr),
                ("Sustain Level", 0, 100, 70, self.update_adsr),
                ("Release", 1, 2000, 500, self.update_adsr),
            ]

            # Create all sliders
            for label, min_val, max_val, default_val, connect_func in sliders:
                slider_info = self.create_slider(label, min_val, max_val, default_val, connect_func)
                controls_layout.addLayout(slider_info['layout'])
                setattr(self, f"{label.lower().replace(' ', '_')}_slider", slider_info)

            # Add pitch bend wheels
            pitch_bend_layout = QVBoxLayout()

            # Pitch bend up
            self.pitch_bend_up = QDial()
            self.pitch_bend_up.setRange(0, 1200)
            self.pitch_bend_up.setValue(0)
            self.pitch_bend_up.valueChanged.connect(self.update_pitch_bend)
            pitch_bend_layout.addWidget(QLabel("Pitch Bend Up"))
            pitch_bend_layout.addWidget(self.pitch_bend_up)

            # Pitch bend down
            self.pitch_bend_down = QDial()
            self.pitch_bend_down.setRange(0, 1200)
            self.pitch_bend_down.setValue(0)
            self.pitch_bend_down.valueChanged.connect(self.update_pitch_bend)
            pitch_bend_layout.addWidget(QLabel("Pitch Bend Down"))
            pitch_bend_layout.addWidget(self.pitch_bend_down)

            controls_layout.addLayout(pitch_bend_layout)

            # Indefinite sustain checkbox
            self.sustain_indefinite_checkbox = QCheckBox("Indefinite Sustain")
            self.sustain_indefinite_checkbox.stateChanged.connect(self.toggle_indefinite_sustain)
            controls_layout.addWidget(self.sustain_indefinite_checkbox)

            self.main_layout.addWidget(controls_widget)

            logger.debug("Effects controls created")
        except Exception as e:
            logger.error(f"Error creating effects controls: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def create_slider(self, label: str, min_val: int, max_val: int, default_val: int,
                    connect_func: Callable) -> Dict[str, Any]:
        """
        Create a slider with associated label and checkbox.

        Args:
            label: Label for the slider
            min_val: Minimum value
            max_val: Maximum value
            default_val: Default value
            connect_func: Function to connect to valueChanged signal

        Returns:
            Dictionary containing the layout, slider, and checkbox
        """
        try:
            layout = QVBoxLayout()

            # Create slider
            slider = QSlider(Qt.Vertical)
            slider.setRange(min_val, max_val)
            slider.setValue(default_val)
            slider.valueChanged.connect(connect_func)
            slider.setFixedHeight(150)

            # Create label
            layout.addWidget(QLabel(label))
            layout.addWidget(slider)

            # Create toggle checkbox
            checkbox = QCheckBox("Enable")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, s=slider: s.setEnabled(state == Qt.Checked))
            layout.addWidget(checkbox)

            return {'layout': layout, 'slider': slider, 'checkbox': checkbox}
        except Exception as e:
            logger.error(f"Error creating slider '{label}': {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def set_waveform(self, waveform: str) -> None:
        """
        Set the current oscillator waveform.

        Args:
            waveform: The waveform type to use
        """
        try:
            self.current_waveform = waveform
            self.current_sound_source = "Waveform"
            logger.debug(f"Set waveform to {waveform}")
        except Exception as e:
            logger.error(f"Error setting waveform: {str(e)}")
            logger.debug(traceback.format_exc())

    def load_sample(self) -> None:
        """Load an audio sample from a file."""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Open Audio File", "", "Audio Files (*.wav *.mp3)"
            )

            if file_name:
                try:
                    # Load the sample using pyo
                    sample_name = os.path.basename(file_name)
                    self.samples[sample_name] = SndTable(file_name)

                    # Add to the sample menu
                    action = QAction(sample_name, self)
                    action.triggered.connect(lambda checked, s=sample_name: self.set_sample(s))
                    self.sample_menu.addAction(action)

                    logger.info(f"Loaded sample: {file_name}")
                except Exception as e:
                    logger.error(f"Error loading sample '{file_name}': {str(e)}")
                    logger.debug(traceback.format_exc())
                    raise SoundGenerationError(f"Failed to load sample: {str(e)}")
        except Exception as e:
            logger.error(f"Error in load_sample: {str(e)}")
            logger.debug(traceback.format_exc())

    def set_sample(self, sample_name: str) -> None:
        """
        Set the current sample.

        Args:
            sample_name: Name of the sample to use
        """
        try:
            self.current_sample = sample_name
            self.current_sound_source = "Sample"
            logger.debug(f"Set sample to {sample_name}")
        except Exception as e:
            logger.error(f"Error setting sample: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_pitch_bend(self) -> None:
        """Update pitch bend for active notes."""
        try:
            bend_up = self.pitch_bend_up.value() / 1200  # Convert cents to pitch multiplier
            bend_down = self.pitch_bend_down.value() / 1200

            for note in self.active_notes.values():
                if 'synth' in note:
                    note['synth'].freq = note['base_freq'] * (2 ** (bend_up - bend_down))

            logger.debug(f"Updated pitch bend: up={bend_up}, down={bend_down}")
        except Exception as e:
            logger.error(f"Error updating pitch bend: {str(e)}")
            logger.debug(traceback.format_exc())

    def load_preset(self) -> None:
        """Load a preset from a file."""
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
            if file_name:
                try:
                    with open(file_name, 'r') as f:
                        preset = json.load(f)
                    self.apply_preset(preset)
                    logger.info(f"Loaded preset: {file_name}")
                except Exception as e:
                    logger.error(f"Error loading preset '{file_name}': {str(e)}")
                    logger.debug(traceback.format_exc())
                    raise PresetError(f"Failed to load preset: {str(e)}")
        except Exception as e:
            logger.error(f"Error in load_preset: {str(e)}")
            logger.debug(traceback.format_exc())

    def save_preset(self) -> None:
        """Save current settings as a preset to a file."""
        try:
            preset_name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
            if ok and preset_name:
                preset = self.get_current_settings()
                file_name, _ = QFileDialog.getSaveFileName(
                    self, "Save Preset", f"{preset_name}.json", "JSON Files (*.json)"
                )
                if file_name:
                    try:
                        with open(file_name, 'w') as f:
                            json.dump(preset, f)
                        logger.info(f"Saved preset: {file_name}")
                    except Exception as e:
                        logger.error(f"Error saving preset to '{file_name}': {str(e)}")
                        logger.debug(traceback.format_exc())
                        raise PresetError(f"Failed to save preset: {str(e)}")
        except Exception as e:
            logger.error(f"Error in save_preset: {str(e)}")
            logger.debug(traceback.format_exc())

    def get_current_settings(self) -> Dict[str, Any]:
        """
        Get the current settings as a preset.

        Returns:
            Dictionary of current settings
        """
        try:
            settings = {}

            # Get slider settings
            for control_name in dir(self):
                if control_name.endswith('_slider'):
                    slider_info = getattr(self, control_name)
                    settings[control_name] = {
                        'value': slider_info['slider'].value(),
                        'enabled': slider_info['checkbox'].isChecked()
                    }

            # Get other settings
            settings['waveform'] = self.current_waveform
            settings['sample'] = getattr(self, 'current_sample', None)
            settings['indefinite_sustain'] = self.sustain_indefinite_checkbox.isChecked()
            settings['pitch_bend_up'] = self.pitch_bend_up.value()
            settings['pitch_bend_down'] = self.pitch_bend_down.value()

            logger.debug("Retrieved current settings")
            return settings
        except Exception as e:
            logger.error(f"Error getting current settings: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        """
        Apply a preset to the keyboard.

        Args:
            preset: Preset settings to apply
        """
        try:
            for control_name, control_settings in preset.items():
                if control_name.endswith('_slider'):
                    if hasattr(self, control_name):
                        slider_info = getattr(self, control_name)
                        slider_info['slider'].setValue(control_settings['value'])
                        slider_info['checkbox'].setChecked(control_settings['enabled'])
                elif control_name == 'waveform':
                    self.set_waveform(control_settings)
                elif control_name == 'sample':
                    if control_settings in self.samples:
                        self.set_sample(control_settings)
                elif control_name == 'indefinite_sustain':
                    self.sustain_indefinite_checkbox.setChecked(control_settings)
                elif control_name == 'pitch_bend_up':
                    self.pitch_bend_up.setValue(control_settings)
                elif control_name == 'pitch_bend_down':
                    self.pitch_bend_down.setValue(control_settings)

            logger.debug("Applied preset")
        except Exception as e:
            logger.error(f"Error applying preset: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def update_sustain(self, value: int) -> None:
        """
        Update sustain time for all active notes.

        Args:
            value: Sustain time in milliseconds
        """
        try:
            for note in self.active_notes.values():
                if 'env' in note:
                    note['env'].release = value / 1000

            logger.debug(f"Updated sustain to {value}ms")
        except Exception as e:
            logger.error(f"Error updating sustain: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_filter(self, _: int) -> None:
        """Update filter parameters for all active notes."""
        try:
            cutoff = self.filter_cutoff_slider['slider'].value()
            q = self.filter_q_slider['slider'].value() / 100

            for note in self.active_notes.values():
                if 'filter' in note:
                    note['filter'].freq = cutoff
                    note['filter'].q = q

            logger.debug(f"Updated filter: cutoff={cutoff}, Q={q}")
        except Exception as e:
            logger.error(f"Error updating filter: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_adsr(self, _: int) -> None:
        """Update ADSR envelope parameters for all active notes."""
        try:
            attack = self.attack_slider['slider'].value() / 1000
            decay = self.decay_slider['slider'].value() / 1000
            sustain = self.sustain_level_slider['slider'].value() / 100
            release = self.release_slider['slider'].value() / 1000

            for note in self.active_notes.values():
                if 'env' in note:
                    note['env'].attack = attack
                    note['env'].decay = decay
                    note['env'].sustain = sustain
                    note['env'].release = release

            logger.debug(f"Updated ADSR: A={attack}s, D={decay}s, S={sustain}, R={release}s")
        except Exception as e:
            logger.error(f"Error updating ADSR: {str(e)}")
            logger.debug(traceback.format_exc())

    def toggle_indefinite_sustain(self, state: int) -> None:
        """
        Toggle indefinite sustain mode.

        Args:
            state: Qt checkbox state
        """
        try:
            self.sustain_indefinite = state == Qt.Checked
            logger.debug(f"Indefinite sustain: {'on' if self.sustain_indefinite else 'off'}")

            if not self.sustain_indefinite:
                # Stop notes that are not currently pressed
                for note in list(self.active_notes.keys()):
                    if note in self.keys and not self.keys[note].isDown():
                        self.stop_note(note)
        except Exception as e:
            logger.error(f"Error toggling indefinite sustain: {str(e)}")
            logger.debug(traceback.format_exc())

    def play_note(self, note: str) -> None:
        """
        Play a note.

        Args:
            note: The note to play (e.g., "C4")
        """
        try:
            # Stop note if already playing
            if note in self.active_notes:
                self.stop_note(note)

            # Check polyphony limit
            if len(self.active_notes) >= self.polyphony_limit:
                oldest_note = min(self.active_notes.keys(), key=lambda k: self.active_notes[k]['start_time'])
                self.stop_note(oldest_note)

            # Calculate frequency
            freq = self.note_to_freq(note)
            logger.debug(f"Playing note: {note} at {freq}Hz")

            # Create synth based on sound source
            try:
                if self.current_sound_source == "Waveform":
                    if self.current_waveform == "Sine":
                        synth = Sine(freq=freq, mul=0.8).mix(2)
                    elif self.current_waveform == "Square":
                        synth = LFO(freq=freq, type=2, mul=0.8).mix(2)
                    elif self.current_waveform == "Sawtooth":
                        synth = LFO(freq=freq, type=1, mul=0.8).mix(2)
                    elif self.current_waveform == "Triangle":
                        synth = LFO(freq=freq, type=3, mul=0.8).mix(2)
                    elif self.current_waveform == "PWM":
                        synth = LFO(freq=freq, type=5, mul=0.8).mix(2)
                elif (self.current_sound_source == "Sample" and
                      self.current_sample in self.samples):
                    synth = Osc(table=self.samples[self.current_sample], freq=freq, mul=0.8).mix(2)
                else:
                    logger.warning(f"Invalid sound source or sample not found")
                    return
            except Exception as e:
                logger.error(f"Error creating synth: {str(e)}")
                logger.debug(traceback.format_exc())
                raise SoundGenerationError(f"Failed to create synth: {str(e)}")

            # Create harmonics
            harmonics = Sine(
                freq=[freq * (i + 1) for i in range(4)],
                mul=[1] + [0] * 3
            ).mix(2)

            # Mix main synth and harmonics
            mixed = synth + harmonics

            # Create filter
            filter = Biquad(
                mixed,
                freq=self.filter_cutoff_slider['slider'].value(),
                q=self.filter_q_slider['slider'].value() / 100,
                type=0
            )

            # Create envelope
            env = Adsr(
                attack=self.attack_slider['slider'].value() / 1000,
                decay=self.decay_slider['slider'].value() / 1000,
                sustain=self.sustain_level_slider['slider'].value() / 100,
                release=self.release_slider['slider'].value() / 1000,
                dur=0,
                mul=0.8
            )

            # Apply envelope to filtered signal
            enveloped = filter * env

            # Add effects
            reverb = WGVerb(
                enveloped,
                feedback=0.8,
                cutoff=5000,
                bal=self.reverb_slider['slider'].value() / 100
            ).mix(2)

            delay = Delay(
                reverb,
                delay=self.delay_slider['slider'].value() / 1000,
                feedback=self.delay_slider['slider'].value() / 200
            ).mix(2)

            chorus = Chorus(
                delay,
                depth=self.chorus_slider['slider'].value() / 100,
                feedback=self.chorus_slider['slider'].value() / 200
            ).mix(2)

            distortion = Disto(
                chorus,
                drive=self.distortion_slider['slider'].value() / 50
            ).mix(2)

            # Add LFO modulation
            lfo = Sine(freq=self.lfo_slider['slider'].value(), mul=0.1, add=1)
            lfo_mod = distortion * lfo
            lfo_mod.out()

            # Store all components in the active notes dictionary
            self.active_notes[note] = {
                'synth': synth,
                'harmonics': harmonics,
                'filter': filter,
                'env': env,
                'reverb': reverb,
                'delay': delay,
                'chorus': chorus,
                'distortion': distortion,
                'lfo': lfo,
                'base_freq': freq,
                'start_time': time.time()
            }

            # Start the envelope
            env.play()

            # Update effects
            self.update_volume(self.volume_slider['slider'].value())
            self.update_harmonics(self.harmonics_slider['slider'].value())

            # Update key visual appearance
            if note in self.keys:
                self.keys[note].set_color("lightblue")
        except Exception as e:
            logger.error(f"Error playing note {note}: {str(e)}")
            logger.debug(traceback.format_exc())
            # Don't raise an exception here to avoid interrupting playback

    def release_note(self, note: str) -> None:
        """
        Release a note.

        Args:
            note: The note to release
        """
        try:
            if note in self.active_notes and not self.sustain_indefinite:
                self.active_notes[note]['env'].stop()

                # Reset key appearance
                if note in self.keys:
                    self.keys[note].reset_color()

                logger.debug(f"Released note: {note}")
        except Exception as e:
            logger.error(f"Error releasing note {note}: {str(e)}")
            logger.debug(traceback.format_exc())

    def stop_note(self, note: str) -> None:
        """
        Stop a note completely and remove it from active notes.

        Args:
            note: The note to stop
        """
        try:
            if note in self.active_notes:
                # Stop the envelope
                self.active_notes[note]['env'].stop()

                # Stop all PyoObject components
                for component, value in self.active_notes[note].items():
                    if isinstance(value, PyoObject):
                        value.stop()

                # Remove from active notes
                del self.active_notes[note]

                # Reset key appearance
                if note in self.keys:
                    self.keys[note].reset_color()

                logger.debug(f"Stopped note: {note}")
        except Exception as e:
            logger.error(f"Error stopping note {note}: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_volume(self, value: int) -> None:
        """
        Update volume for all active notes.

        Args:
            value: Volume value (0-100)
        """
        try:
            volume = value / 100
            for note in self.active_notes.values():
                note['synth'].mul = volume

            logger.debug(f"Updated volume to {volume}")
        except Exception as e:
            logger.error(f"Error updating volume: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_harmonics(self, value: int) -> None:
        """
        Update harmonics levels for all active notes.

        Args:
            value: Harmonics level (0-100)
        """
        try:
            # First harmonic is always at full amplitude, others scaled by value
            harmonic_levels = [1] + [value / 100] * 3

            for note in self.active_notes.values():
                note['harmonics'].mul = harmonic_levels

            logger.debug(f"Updated harmonics level to {value/100}")
        except Exception as e:
            logger.error(f"Error updating harmonics: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_reverb(self, value: int) -> None:
        """
        Update reverb level for all active notes.

        Args:
            value: Reverb level (0-100)
        """
        try:
            reverb_level = value / 100
            for note in self.active_notes.values():
                note['reverb'].bal = reverb_level

            logger.debug(f"Updated reverb to {reverb_level}")
        except Exception as e:
            logger.error(f"Error updating reverb: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_delay(self, value: int) -> None:
        """
        Update delay parameters for all active notes.

        Args:
            value: Delay value (0-100)
        """
        try:
            delay_time = value / 1000  # Convert to seconds
            feedback = value / 200     # Scale feedback based on delay

            for note in self.active_notes.values():
                note['delay'].delay = delay_time
                note['delay'].feedback = feedback

            logger.debug(f"Updated delay: time={delay_time}s, feedback={feedback}")
        except Exception as e:
            logger.error(f"Error updating delay: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_chorus(self, value: int) -> None:
        """
        Update chorus parameters for all active notes.

        Args:
            value: Chorus value (0-100)
        """
        try:
            depth = value / 100
            feedback = value / 200

            for note in self.active_notes.values():
                note['chorus'].depth = depth
                note['chorus'].feedback = feedback

            logger.debug(f"Updated chorus: depth={depth}, feedback={feedback}")
        except Exception as e:
            logger.error(f"Error updating chorus: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_distortion(self, value: int) -> None:
        """
        Update distortion level for all active notes.

        Args:
            value: Distortion value (0-100)
        """
        try:
            drive = value / 50

            for note in self.active_notes.values():
                note['distortion'].drive = drive

            logger.debug(f"Updated distortion drive to {drive}")
        except Exception as e:
            logger.error(f"Error updating distortion: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_lfo(self, value: int) -> None:
        """
        Update LFO rate for all active notes.

        Args:
            value: LFO rate in Hz
        """
        try:
            for note in self.active_notes.values():
                note['lfo'].freq = value

            logger.debug(f"Updated LFO rate to {value}Hz")
        except Exception as e:
            logger.error(f"Error updating LFO: {str(e)}")
            logger.debug(traceback.format_exc())

    def note_to_freq(self, note: str) -> float:
        """
        Convert a note name to frequency in Hz.

        Args:
            note: Note name (e.g., "C4")

        Returns:
            Frequency in Hz
        """
        try:
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = int(note[-1])
            semitone = notes.index(note[:-1])

            # A4 = 440Hz, calculate relative to that
            return 440 * (2 ** ((octave - 4) + (semitone - 9) / 12))
        except Exception as e:
            logger.error(f"Error converting note {note} to frequency: {str(e)}")
            logger.debug(traceback.format_exc())
            return 440  # Default to A4 on error

    def keyPressEvent(self, event) -> None:
        """
        Handle keyboard key press events.

        Args:
            event: Key event
        """
        try:
            key = event.key()
            if key in self.key_map and not event.isAutoRepeat():
                self.notePressed.emit(self.key_map[key])
        except Exception as e:
            logger.error(f"Error in keyPressEvent: {str(e)}")
            logger.debug(traceback.format_exc())

    def keyReleaseEvent(self, event) -> None:
        """
        Handle keyboard key release events.

        Args:
            event: Key event
        """
        try:
            key = event.key()
            if key in self.key_map and not event.isAutoRepeat():
                self.noteReleased.emit(self.key_map[key])
        except Exception as e:
            logger.error(f"Error in keyReleaseEvent: {str(e)}")
            logger.debug(traceback.format_exc())

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Args:
            event: Close event
        """
        try:
            # Stop all playing notes
            for note in list(self.active_notes.keys()):
                self.stop_note(note)

            # Stop the server if possible
            if hasattr(self.s, 'stop'):
                self.s.stop()

            logger.info("Piano keyboard window closed")
            event.accept()
        except Exception as e:
            logger.error(f"Error in closeEvent: {str(e)}")
            logger.debug(traceback.format_exc())
            event.accept()  # Accept the event even if there was an error

    # Keyboard mapping from computer keys to notes
    key_map = {
        Qt.Key_A: 'C4', Qt.Key_W: 'C#4', Qt.Key_S: 'D4', Qt.Key_E: 'D#4',
        Qt.Key_D: 'E4', Qt.Key_F: 'F4', Qt.Key_T: 'F#4', Qt.Key_G: 'G4',
        Qt.Key_Y: 'G#4', Qt.Key_H: 'A4', Qt.Key_U: 'A#4', Qt.Key_J: 'B4',
        Qt.Key_K: 'C5', Qt.Key_O: 'C#5', Qt.Key_L: 'D5', Qt.Key_P: 'D#5',
        Qt.Key_Semicolon: 'E5', Qt.Key_Colon: 'F5'
    }


# Test code to run the piano keyboard standalone
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    # Set up logging
    logger.info("Starting piano keyboard in standalone mode")

    try:
        app = QApplication(sys.argv)
        keyboard = PianoKeyboardWindow()
        keyboard.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Fatal error running piano keyboard: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

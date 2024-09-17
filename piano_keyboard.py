from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QCheckBox,
                             QComboBox, QDial, QFileDialog, QGridLayout, QMainWindow, QAction, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from pyo import *
import random
import os
import time
import json

class PianoKey(QPushButton):
    def __init__(self, note, is_black=False, parent=None):
        super().__init__(parent)
        self.note = note
        self.is_black = is_black
        self.setFixedSize(35 if is_black else 55, 160 if is_black else 240)
        self.default_color = "black" if is_black else "white"
        self.setStyleSheet(self.get_style(self.default_color))
        self.setText(note)

    def get_style(self, bg_color):
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

    def set_color(self, color):
        self.setStyleSheet(self.get_style(color))

    def reset_color(self):
        self.setStyleSheet(self.get_style(self.default_color))


class PianoKeyboardWindow(QMainWindow):
    notePressed = pyqtSignal(str)
    noteReleased = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Piano Keyboard Synthesizer")
        self.setGeometry(100, 100, 1400, 700)  # Slightly increased size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.s = Server().boot()
        self.s.start()

        self.create_menu_bar()
        self.create_keyboard()
        self.create_effects_controls()

        self.active_notes = {}
        self.sustain_indefinite = False
        self.polyphony_limit = 8
        self.samples = {}
        self.current_preset = "Default"
        self.current_sound_source = "Waveform"
        self.current_waveform = "Sine"
        self.current_sample = None

    def create_menu_bar(self):
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

    def create_keyboard(self):
        self.keys = {}
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

        self.notePressed.connect(self.play_note)
        self.noteReleased.connect(self.release_note)

    def create_effects_controls(self):
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)

        # Create sliders
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

        for label, min_val, max_val, default_val, connect_func in sliders:
            slider_info = self.create_slider(label, min_val, max_val, default_val, connect_func)
            controls_layout.addLayout(slider_info['layout'])
            setattr(self, f"{label.lower().replace(' ', '_')}_slider", slider_info)

        # Pitch bend wheels
        pitch_bend_layout = QVBoxLayout()
        self.pitch_bend_up = QDial()
        self.pitch_bend_up.setRange(0, 1200)
        self.pitch_bend_up.setValue(0)
        self.pitch_bend_up.valueChanged.connect(self.update_pitch_bend)
        pitch_bend_layout.addWidget(QLabel("Pitch Bend Up"))
        pitch_bend_layout.addWidget(self.pitch_bend_up)

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

    def create_slider(self, label, min_val, max_val, default_val, connect_func):
        layout = QVBoxLayout()
        slider = QSlider(Qt.Vertical)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(connect_func)
        slider.setFixedHeight(150)  # Increased height
        layout.addWidget(QLabel(label))
        layout.addWidget(slider)

        # Add toggle checkbox
        checkbox = QCheckBox("Enable")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, s=slider: s.setEnabled(state == Qt.Checked))
        layout.addWidget(checkbox)

        return {'layout': layout, 'slider': slider, 'checkbox': checkbox}


    def set_waveform(self, waveform):
        self.current_waveform = waveform
        self.current_sound_source = "Waveform"

    def load_sample(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", "Audio Files (*.wav *.mp3)")
        if file_name:
            sample_name = os.path.basename(file_name)
            self.samples[sample_name] = SndTable(file_name)
            action = QAction(sample_name, self)
            action.triggered.connect(lambda checked, s=sample_name: self.set_sample(s))
            self.sample_menu.addAction(action)

    def set_sample(self, sample_name):
        self.current_sample = sample_name
        self.current_sound_source = "Sample"

    def update_pitch_bend(self):
        bend_up = self.pitch_bend_up.value() / 1200  # Convert cents to pitch multiplier
        bend_down = self.pitch_bend_down.value() / 1200
        for note in self.active_notes.values():
            if 'synth' in note:
                note['synth'].freq = note['base_freq'] * (2 ** (bend_up - bend_down))

    def load_preset(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'r') as f:
                preset = json.load(f)
            self.apply_preset(preset)

    def save_preset(self):
        preset_name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and preset_name:
            preset = self.get_current_settings()
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Preset", f"{preset_name}.json", "JSON Files (*.json)")
            if file_name:
                with open(file_name, 'w') as f:
                    json.dump(preset, f)

    def get_current_settings(self):
        settings = {}
        for control_name in dir(self):
            if control_name.endswith('_slider'):
                slider_info = getattr(self, control_name)
                settings[control_name] = {
                    'value': slider_info['slider'].value(),
                    'enabled': slider_info['checkbox'].isChecked()
                }
        settings['waveform'] = self.current_waveform
        settings['sample'] = getattr(self, 'current_sample', None)
        settings['indefinite_sustain'] = self.sustain_indefinite_checkbox.isChecked()
        settings['pitch_bend_up'] = self.pitch_bend_up.value()
        settings['pitch_bend_down'] = self.pitch_bend_down.value()
        return settings

    def apply_preset(self, preset):
        for control_name, control_settings in preset.items():
            if control_name.endswith('_slider'):
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



    def change_sound_source(self, source):
        if source == "Waveform":
            self.waveform_combo.setVisible(True)
            self.sample_combo.setVisible(False)
            self.load_sample_btn.setVisible(False)
        else:
            self.waveform_combo.setVisible(False)
            self.sample_combo.setVisible(True)
            self.load_sample_btn.setVisible(True)


    def update_sustain(self, value):
        for note in self.active_notes.values():
            if 'env' in note:
                note['env'].release = value / 1000

    def update_filter(self, _):
        cutoff = self.filter_cutoff_slider['slider'].value()
        q = self.filter_q_slider['slider'].value() / 100
        for note in self.active_notes.values():
            if 'filter' in note:
                note['filter'].freq = cutoff
                note['filter'].q = q

    def update_adsr(self, _):
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


    def toggle_indefinite_sustain(self, state):
        self.sustain_indefinite = state == Qt.Checked
        if not self.sustain_indefinite:
            for note in list(self.active_notes.keys()):
                if not self.keys[note].isDown():
                    self.stop_note(note)

    def play_note(self, note):
        if note in self.active_notes:
            self.stop_note(note)

        if len(self.active_notes) >= self.polyphony_limit:
            oldest_note = min(self.active_notes.keys(), key=lambda k: self.active_notes[k]['start_time'])
            self.stop_note(oldest_note)

        freq = self.note_to_freq(note)

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
        elif self.current_sound_source == "Sample" and self.current_sample in self.samples:
            synth = Osc(table=self.samples[self.current_sample], freq=freq, mul=0.8).mix(2)
        else:
            print(f"Invalid sound source or sample not found")
            return

        harmonics = Sine(freq=[freq * (i + 1) for i in range(4)], mul=[1] + [0] * 3).mix(2)
        mixed = synth + harmonics

        filter = Biquad(mixed, freq=self.filter_cutoff_slider['slider'].value(), q=self.filter_q_slider['slider'].value() / 100, type=0)

        env = Adsr(
            attack=self.attack_slider['slider'].value() / 1000,
            decay=self.decay_slider['slider'].value() / 1000,
            sustain=self.sustain_level_slider['slider'].value() / 100,
            release=self.release_slider['slider'].value() / 1000,
            dur=0,
            mul=0.8
        )

        enveloped = filter * env

        reverb = WGVerb(enveloped, feedback=0.8, cutoff=5000, bal=self.reverb_slider['slider'].value() / 100).mix(2)
        delay = Delay(reverb, delay=self.delay_slider['slider'].value() / 1000, feedback=self.delay_slider['slider'].value() / 200).mix(2)
        chorus = Chorus(delay, depth=self.chorus_slider['slider'].value() / 100, feedback=self.chorus_slider['slider'].value() / 200).mix(2)
        distortion = Disto(chorus, drive=self.distortion_slider['slider'].value() / 50).mix(2)
        lfo = Sine(freq=self.lfo_slider['slider'].value(), mul=0.1, add=1)
        lfo_mod = distortion * lfo
        lfo_mod.out()

        self.active_notes[note] = {
            'synth': synth, 'harmonics': harmonics, 'filter': filter, 'env': env,
            'reverb': reverb, 'delay': delay, 'chorus': chorus, 'distortion': distortion, 'lfo': lfo,
            'base_freq': freq, 'start_time': time.time()
        }

        env.play()

        self.update_volume(self.volume_slider['slider'].value())
        self.update_harmonics(self.harmonics_slider['slider'].value())

        self.keys[note].set_color("lightblue")

    def release_note(self, note):
        if note in self.active_notes and not self.sustain_indefinite:
            self.active_notes[note]['env'].stop()
            self.keys[note].reset_color()

    def stop_note(self, note):
        if note in self.active_notes:
            self.active_notes[note]['env'].stop()
            for effect in self.active_notes[note].values():
                if isinstance(effect, PyoObject):
                    effect.stop()
            del self.active_notes[note]
            self.keys[note].reset_color()


    def update_volume(self, value):
        for note in self.active_notes.values():
            note['synth'].mul = value / 100

    def update_harmonics(self, value):
        harmonics = [1] + [value / 100] * 3
        for note in self.active_notes.values():
            note['harmonics'].mul = harmonics

    def update_reverb(self, value):
        for note in self.active_notes.values():
            note['reverb'].bal = value / 100

    def update_delay(self, value):
        for note in self.active_notes.values():
            note['delay'].delay = value / 1000
            note['delay'].feedback = value / 200

    def update_chorus(self, value):
        for note in self.active_notes.values():
            note['chorus'].depth = value / 100
            note['chorus'].feedback = value / 200

    def update_distortion(self, value):
        for note in self.active_notes.values():
            note['distortion'].drive = value / 50

    def update_lfo(self, value):
        for note in self.active_notes.values():
            note['lfo'].freq = value

    def note_to_freq(self, note):
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = int(note[-1])
        semitone = notes.index(note[:-1])
        return 440 * (2 ** ((octave - 4) + (semitone - 9) / 12))

    def keyPressEvent(self, event):
        key = event.key()
        if key in self.key_map and not event.isAutoRepeat():
            self.notePressed.emit(self.key_map[key])

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self.key_map and not event.isAutoRepeat():
            self.noteReleased.emit(self.key_map[key])

    key_map = {
        Qt.Key_A: 'C4', Qt.Key_W: 'C#4', Qt.Key_S: 'D4', Qt.Key_E: 'D#4',
        Qt.Key_D: 'E4', Qt.Key_F: 'F4', Qt.Key_T: 'F#4', Qt.Key_G: 'G4',
        Qt.Key_Y: 'G#4', Qt.Key_H: 'A4', Qt.Key_U: 'A#4', Qt.Key_J: 'B4',
        Qt.Key_K: 'C5', Qt.Key_O: 'C#5', Qt.Key_L: 'D5', Qt.Key_P: 'D#5',
        Qt.Key_Semicolon: 'E5', Qt.Key_Colon: 'F5'
    }

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    keyboard = PianoKeyboardWindow()
    keyboard.show()
    sys.exit(app.exec_())

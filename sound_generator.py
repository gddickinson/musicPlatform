import numpy as np
import pyaudio
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
                             QComboBox, QGroupBox, QGridLayout, QScrollArea, QDial, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
import pyqtgraph as pg

from synth_dsp import (  # noqa: F401  (re-exported: the DSP classes used to live here)
    Track, WaveTrack, NoiseTrack, FMSynthTrack, ContinuousNoteTrack, Effect, ReverbEffect, DistortionEffect,
    EQEffect, VibratoEffect, TremoloEffect, ChorusEffect, LowPassFilter, EFFECT_PARAMS)

class AutomatedDial(QDial):
    manualValueChanged = pyqtSignal(int)
    automatedValueChanged = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.automation_active = False
        self.automation_rate = 0
        self.automation_timer = QTimer(self)
        self.automation_timer.timeout.connect(self.update_automated_value)
        self.automation_timer.start(50)

    def set_automation(self, rate):
        self.automation_rate = rate
        self.automation_active = rate != 0

    def update_automated_value(self):
        if self.automation_active:
            value_range = self.maximum() - self.minimum()
            change = int(self.automation_rate * 0.05)
            new_value = self.value() + change

            if new_value > self.maximum():
                new_value = self.minimum() + (new_value - self.maximum() - 1) % value_range
            elif new_value < self.minimum():
                new_value = self.maximum() - (self.minimum() - new_value - 1) % value_range

            super().setValue(new_value)
            self.automatedValueChanged.emit(new_value)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.manualValueChanged.emit(self.value())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.manualValueChanged.emit(self.value())

class TrackControlWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Track Controls")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

    def add_track_controls(self, track_controls):
        self.scroll_layout.addWidget(track_controls)

    def remove_track_controls(self, track_controls):
        self.scroll_layout.removeWidget(track_controls)
        track_controls.deleteLater()

class EnhancedSoundGeneratorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Sound Generator")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.sample_rate = 44100
        self.frames_per_buffer = 1024
        self.tracks = []
        self.track_colors = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
                             QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)]
        self.current_color_index = 0
        self.continuous_note_tracks = {}

        # Waveform plot
        self.plot_widget = pg.PlotWidget()
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setLabel('left', 'Amplitude')
        self.plot_item.setLabel('bottom', 'Time (s)')
        self.plot_item.setYRange(-1, 1)
        self.plot_item.setXRange(0, self.frames_per_buffer / self.sample_rate)
        self.layout.addWidget(self.plot_widget)

        self.waveform_plots = {}
        self.total_plot = self.plot_item.plot(pen='y')

        # Controls
        controls_layout = QHBoxLayout()

        add_wave_btn = QPushButton("Add Wave")
        add_wave_btn.clicked.connect(lambda: self.add_track("wave"))
        controls_layout.addWidget(add_wave_btn)

        add_noise_btn = QPushButton("Add Noise")
        add_noise_btn.clicked.connect(lambda: self.add_track("noise"))
        controls_layout.addWidget(add_noise_btn)

        add_fm_btn = QPushButton("Add FM Synth")
        add_fm_btn.clicked.connect(lambda: self.add_track("fm"))
        controls_layout.addWidget(add_fm_btn)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.toggle_audio)
        controls_layout.addWidget(self.start_btn)

        self.layout.addLayout(controls_layout)

        # Continuous note controls
        self.continuous_note_layout = QVBoxLayout()
        self.layout.addLayout(self.continuous_note_layout)

        # Note buttons for continuous notes
        self.note_buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.note_buttons_layout)
        self.create_note_buttons()

        # Track control window
        self.track_control_window = TrackControlWindow()
        self.track_control_window.show()

        # Audio setup
        self.p = pyaudio.PyAudio()
        self.stream = None

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

    def create_note_buttons(self):
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        for note in notes:
            button = QPushButton(note)
            button.clicked.connect(lambda checked, n=note: self.toggle_continuous_note_track(n))
            self.note_buttons_layout.addWidget(button)


    def toggle_continuous_note_track(self, note):
        if note in self.continuous_note_tracks:
            self.remove_continuous_note_track(note)
        else:
            self.add_continuous_note_track(note)

    def add_continuous_note_track(self, note):
        if note in self.continuous_note_tracks:
            print(f"Continuous note track for {note} already exists.")
            return

        track = ContinuousNoteTrack(note, 4, self.sample_rate)
        self.tracks.append(track)
        self.continuous_note_tracks[note] = track
        self.add_track_controls(track)

        # Update the corresponding button to show it's active
        self.update_note_button_state(note, True)

    def update_note_button_state(self, note, is_active):
        for i in range(self.note_buttons_layout.count()):
            button = self.note_buttons_layout.itemAt(i).widget()
            if button.text() == note:
                button.setStyleSheet("background-color: green;" if is_active else "")
                break


    def add_track_controls(self, track):
        track_controls = TrackControls(track, self.remove_track)
        self.track_control_window.add_track_controls(track_controls)

        track.color = self.track_colors[self.current_color_index]
        self.current_color_index = (self.current_color_index + 1) % len(self.track_colors)

    def remove_track(self, track, track_controls):
        self.tracks.remove(track)
        self.track_control_window.remove_track_controls(track_controls)

        # If it's a continuous note track, remove it from the continuous_note_tracks dictionary
        for note, cont_track in list(self.continuous_note_tracks.items()):
            if cont_track == track:
                del self.continuous_note_tracks[note]
                # Update the corresponding button to show it's inactive
                self.update_note_button_state(note, False)
                break

        # Update the plot
        self.update_plot()

    def add_continuous_note_controls(self, track, note):
        track_controls = ContinuousNoteTrackControls(track, note, self.remove_continuous_note_track)
        self.track_control_window.add_track_controls(track_controls)

    def remove_continuous_note_track(self, note):
        if note in self.continuous_note_tracks:
            track = self.continuous_note_tracks[note]
            self.remove_track(track, track.controls)

            # Update the corresponding button to show it's inactive
            self.update_note_button_state(note, False)

    def add_track(self, track_type):
        if track_type == "wave":
            track = WaveTrack(self.sample_rate)
        elif track_type == "noise":
            track = NoiseTrack(self.sample_rate)
        elif track_type == "fm":
            track = FMSynthTrack(self.sample_rate)
        else:
            return

        self.tracks.append(track)
        track_controls = TrackControls(track, self.remove_track)
        self.track_control_window.add_track_controls(track_controls)

        track.color = self.track_colors[self.current_color_index]
        self.current_color_index = (self.current_color_index + 1) % len(self.track_colors)


    def toggle_audio(self):
        if self.stream is None:
            self.stream = self.p.open(format=pyaudio.paFloat32,
                                      channels=1,
                                      rate=self.sample_rate,
                                      output=True,
                                      frames_per_buffer=self.frames_per_buffer,
                                      stream_callback=self.audio_callback)
            self.stream.start_stream()
            self.start_btn.setText("Stop")
        else:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.start_btn.setText("Start")

    def audio_callback(self, in_data, frame_count, time_info, status):
        output_buffer = np.zeros(frame_count)
        for track in self.tracks:
            output_buffer += track.generate_audio(frame_count)
        return (output_buffer.astype(np.float32), pyaudio.paContinue)

    def update_plot(self):
        self.plot_widget.clear()
        t = np.arange(self.frames_per_buffer) / self.sample_rate
        for track in self.tracks:
            audio_data = track.generate_audio(self.frames_per_buffer)
            self.plot_widget.plot(t, audio_data, pen=pg.mkPen(track.color))


    def closeEvent(self, event):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        self.track_control_window.close()
        event.accept()


class TrackControls(QGroupBox):
    def __init__(self, track, remove_callback):
        super().__init__()
        self.track = track
        self.track.controls = self
        self.remove_callback = remove_callback

        layout = QGridLayout()
        self.setLayout(layout)

        # Common controls
        amp_slider = QSlider(Qt.Horizontal)
        amp_slider.setRange(0, 100)
        amp_slider.setValue(int(track.amplitude * 100))
        amp_slider.valueChanged.connect(lambda v: track.set_amplitude(v / 100))
        layout.addWidget(QLabel("Amplitude:"), 0, 0)
        layout.addWidget(amp_slider, 0, 1)

        # Specific controls based on track type
        if isinstance(track, WaveTrack):
            self.add_wave_track_controls(layout)
        elif isinstance(track, NoiseTrack):
            self.add_noise_track_controls(layout)
        elif isinstance(track, FMSynthTrack):
            self.add_fm_synth_track_controls(layout)
        elif isinstance(track, ContinuousNoteTrack):
            self.add_continuous_note_track_controls(layout)

        # Effects
        self.add_effects_controls(layout)

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_track)
        layout.addWidget(remove_btn, layout.rowCount(), 0, 1, 2)

    def remove_track(self):
        self.remove_callback(self.track, self)

    def add_wave_track_controls(self, layout):
        freq_widget, freq_dial = self.create_automated_dial(20, 2000, int(self.track.frequency), "Frequency")
        freq_dial.valueChanged.connect(self.track.set_frequency)
        layout.addWidget(freq_widget, layout.rowCount(), 0, 1, 2)

        wave_type_combo = QComboBox()
        wave_type_combo.addItems(['sine', 'square', 'sawtooth', 'triangle'])
        wave_type_combo.setCurrentText(self.track.wave_type)
        wave_type_combo.currentTextChanged.connect(self.track.set_wave_type)
        layout.addWidget(QLabel("Wave Type:"), layout.rowCount(), 0)
        layout.addWidget(wave_type_combo, layout.rowCount() - 1, 1)

    def add_noise_track_controls(self, layout):
        noise_type_combo = QComboBox()
        noise_type_combo.addItems(['white', 'pink', 'brown'])
        noise_type_combo.setCurrentText(self.track.noise_type)
        noise_type_combo.currentTextChanged.connect(self.track.set_noise_type)
        layout.addWidget(QLabel("Noise Type:"), layout.rowCount(), 0)
        layout.addWidget(noise_type_combo, layout.rowCount() - 1, 1)

    def add_fm_synth_track_controls(self, layout):
        carrier_widget, carrier_dial = self.create_automated_dial(20, 2000, int(self.track.carrier_freq), "Carrier Freq")
        carrier_dial.valueChanged.connect(self.track.set_carrier_frequency)
        layout.addWidget(carrier_widget, layout.rowCount(), 0, 1, 2)

        mod_widget, mod_dial = self.create_automated_dial(1, 1000, int(self.track.mod_freq), "Mod Freq")
        mod_dial.valueChanged.connect(self.track.set_mod_frequency)
        layout.addWidget(mod_widget, layout.rowCount(), 0, 1, 2)

        index_widget, index_dial = self.create_automated_dial(0, 10, int(self.track.mod_index), "Mod Index")
        index_dial.valueChanged.connect(self.track.set_mod_index)
        layout.addWidget(index_widget, layout.rowCount(), 0, 1, 2)

    def add_continuous_note_track_controls(self, layout):
        octave_combo = QComboBox()
        octave_combo.addItems([str(i) for i in range(1, 9)])
        octave_combo.setCurrentText("4")  # Assuming default octave is 4
        octave_combo.currentTextChanged.connect(lambda text: self.track.set_note(self.track.note, int(text)))
        layout.addWidget(QLabel("Octave:"), layout.rowCount(), 0)
        layout.addWidget(octave_combo, layout.rowCount() - 1, 1)

        harmonics_group = QGroupBox("Harmonics")
        harmonics_layout = QGridLayout()
        harmonics_group.setLayout(harmonics_layout)

        for i in range(5):  # Add controls for 5 harmonics
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100 if i == 0 else 0)
            slider.valueChanged.connect(lambda value, idx=i: self.update_harmonics(idx, value / 100))
            harmonics_layout.addWidget(QLabel(f"Harmonic {i+1}:"), i, 0)
            harmonics_layout.addWidget(slider, i, 1)

        layout.addWidget(harmonics_group, layout.rowCount(), 0, 1, 2)

    def update_harmonics(self, index, value):
        harmonics = self.track.harmonics.copy()
        if index >= len(harmonics):
            harmonics.extend([0] * (index + 1 - len(harmonics)))
        harmonics[index] = value
        self.track.set_harmonics(harmonics)

    def create_automated_dial(self, min_value, max_value, default_value, label):
        dial_layout = QGridLayout()

        dial = AutomatedDial()
        dial.setMinimum(min_value)
        dial.setMaximum(max_value)
        dial.setValue(default_value)
        dial_layout.addWidget(dial, 0, 0, 1, 2)

        dial_label = QLabel(label)
        dial_layout.addWidget(dial_label, 1, 0, 1, 2)

        rate_slider = QSlider(Qt.Horizontal)
        rate_slider.setRange(-1000, 1000)
        rate_slider.setValue(0)
        rate_slider.valueChanged.connect(dial.set_automation)
        dial_layout.addWidget(QLabel("Automation Rate:"), 2, 0)
        dial_layout.addWidget(rate_slider, 2, 1)

        dial_widget = QWidget()
        dial_widget.setLayout(dial_layout)

        return dial_widget, dial

    def add_effects_controls(self, layout):
        effects_group = QGroupBox("Effects")
        effects_layout = QGridLayout()
        effects_group.setLayout(effects_layout)

        effects = EFFECT_PARAMS

        for i, (effect_class, params) in enumerate(effects):
            effect_check = QPushButton(effect_class.__name__)
            effect_check.setCheckable(True)
            effect_check.toggled.connect(lambda checked, ec=effect_class: self.toggle_effect(ec, checked))
            effects_layout.addWidget(effect_check, i, 0)

            for j, (param_name, (min_val, max_val)) in enumerate(params.items()):
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(50)
                slider.valueChanged.connect(lambda value, ec=effect_class, pn=param_name, mi=min_val, ma=max_val:
                                            self.update_effect_param(ec, pn, mi + (ma - mi) * value / 100))
                effects_layout.addWidget(slider, i, j * 2 + 1)
                effects_layout.addWidget(QLabel(param_name), i, j * 2 + 2)

        layout.addWidget(effects_group, layout.rowCount(), 0, 1, 2)

    def toggle_effect(self, effect_class, enabled):
        effect_name = effect_class.__name__
        effect = self.track.get_effect(effect_name)
        if enabled and effect is None:
            new_effect = effect_class()
            self.track.add_effect(new_effect)
        elif not enabled and effect is not None:
            self.track.remove_effect(effect_name)

    def update_effect_param(self, effect_class, param_name, value):
        effect_name = effect_class.__name__
        effect = self.track.get_effect(effect_name)
        if effect:
            setattr(effect, param_name, float(value))
            print(f"Updated {effect_name} {param_name} to {value}")  # Debugging line


class ContinuousNoteTrackControls(TrackControls):
    def __init__(self, track, note, remove_callback):
        super().__init__(track, remove_callback)
        self.note = note

        layout = self.layout()

        # Octave control
        octave_combo = QComboBox()
        octave_combo.addItems([str(i) for i in range(1, 9)])
        octave_combo.setCurrentText("4")
        octave_combo.currentTextChanged.connect(lambda text: track.set_note(note, int(text)))
        layout.addWidget(QLabel("Octave:"), layout.rowCount(), 0)
        layout.addWidget(octave_combo, layout.rowCount() - 1, 1)

        # Harmonics control
        harmonics_group = QGroupBox("Harmonics")
        harmonics_layout = QVBoxLayout()
        harmonic_sliders = []
        for i in range(5):  # Add controls for 5 harmonics
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100 if i == 0 else 0)
            slider.valueChanged.connect(lambda value, idx=i: self.update_harmonics(idx, value / 100))
            harmonics_layout.addWidget(slider)
            harmonics_layout.addWidget(QLabel(f"Harmonic {i+1}"))
            harmonic_sliders.append(slider)
        harmonics_group.setLayout(harmonics_layout)
        layout.addWidget(harmonics_group, layout.rowCount(), 0, 1, 2)

    def update_harmonics(self, index, value):
        harmonics = self.track.harmonics.copy()
        if index >= len(harmonics):
            harmonics.extend([0] * (index + 1 - len(harmonics)))
        harmonics[index] = value
        self.track.set_harmonics(harmonics)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    gui = EnhancedSoundGeneratorGUI()
    gui.show()
    sys.exit(app.exec_())

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import pygame
import os

class DrumMachineGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window properties
        self.setWindowTitle("PyQt Drum Machine")
        self.setGeometry(100, 100, 1200, 600)  # Adjusted window size

        # Main layout
        self.centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.layout = QtWidgets.QVBoxLayout(self.centralWidget)

        # Button grid
        self.grid_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.grid_layout)
        self.buttons = {}
        self.rows = 12  # Number of instruments
        self.cols = 32  # 32 steps in each row
        self.groups = 8  # 8 groups of 4 buttons

        # Colors
        self.unpushed_color = QtGui.QColor(255, 255, 0)
        self.pushed_color = QtGui.QColor(0, 255, 0)

        # Sample names
        self.sample_names = [
            "Kick", "Snare", "Hi-Hat", "Clap", "Tom 1", "Tom 2",
            "Crash", "Ride", "Perc 1", "Perc 2", "FX 1", "FX 2"
        ]



        # Add sample names and buttons
        for i in range(self.rows):
            # Add sample name
            name_label = QtWidgets.QLabel(self.sample_names[i])
            name_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            name_label.setFixedWidth(60)
            self.grid_layout.addWidget(name_label, i, 0)

        # Draw horizontal blocks of 4 buttons at a time across all rows
        for block in range(0, self.cols, 4):
            frame = QtWidgets.QFrame(self)
            frame.setFrameShape(QtWidgets.QFrame.Box)
            frame.setLineWidth(1)
            frame_layout = QtWidgets.QGridLayout(frame)
            frame_layout.setSpacing(2)

            for i in range(self.rows):
                for j in range(4):
                    step = block + j
                    button = QtWidgets.QPushButton("", self)  # Debug: Add coordinates as text
                    button.setFixedSize(25, 25)
                    button.setCheckable(True)
                    button.setStyleSheet(self.get_button_style(False))
                    button.clicked.connect(self.update_button_style)
                    self.buttons[(i, step)] = button
                    frame_layout.addWidget(button, i, j)

                    # Volume Control
                    volume_dial = QtWidgets.QDial()
                    volume_dial.setRange(0, 100)
                    volume_dial.setValue(100)  # Default volume is 100%
                    volume_dial.setFixedSize(25, 25)  # Compact the dials
                    volume_dial.valueChanged.connect(lambda value, row=i: self.update_volume(row, value))
                    self.grid_layout.addWidget(volume_dial, i, self.cols + 1)

                    # Effects Button
                    effects_button = QtWidgets.QPushButton("FX")
                    effects_button.setFixedSize(40, 30)  # Compact the button
                    effects_button.clicked.connect(lambda _, row=i: self.show_effects_window(row))
                    self.grid_layout.addWidget(effects_button, i, self.cols + 2)

            self.grid_layout.addWidget(frame, 0, block // 4 + 1, self.rows, 1)  # Place in grid, span vertically


        # Sample playback using pygame mixer
        pygame.mixer.init()
        self.samples = self.load_samples()

        # Control panel
        self.control_panel = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.control_panel)

        # BPM control
        self.bpm_label = QtWidgets.QLabel("BPM:", self)
        self.bpm_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.bpm_slider.setMinimum(60)
        self.bpm_slider.setMaximum(180)
        self.bpm_slider.setValue(120)
        self.bpm_slider.setFixedWidth(150)  # Compact the slider
        self.bpm_slider.valueChanged.connect(self.update_bpm)
        self.bpm_display = QtWidgets.QLabel("120", self)
        self.control_panel.addWidget(self.bpm_label)
        self.control_panel.addWidget(self.bpm_slider)
        self.control_panel.addWidget(self.bpm_display)

        # Play/Stop button
        self.play_button = QtWidgets.QPushButton("Play", self)
        self.play_button.setFixedWidth(60)  # Compact the play button
        self.play_button.clicked.connect(self.toggle_playback)
        self.control_panel.addWidget(self.play_button)

        # Clear button
        self.clear_button = QtWidgets.QPushButton("Clear", self)
        self.clear_button.setFixedWidth(60)  # Compact the clear button
        self.clear_button.clicked.connect(self.clear_grid)
        self.control_panel.addWidget(self.clear_button)

        # Timer for playback
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_beat)
        self.current_step = 0
        self.playing = False

        # Waveform display
        self.waveform_widget = pg.PlotWidget()
        self.layout.addWidget(self.waveform_widget)
        self.waveform_plot = self.waveform_widget.plot(pen='y')
        self.waveform_widget.setLabel('left', 'Amplitude')
        self.waveform_widget.setLabel('bottom', 'Time')

    def get_button_style(self, is_pushed):
        color = self.pushed_color if is_pushed else self.unpushed_color
        return f"background-color: {color.name()}; border: 1px solid black;"

    def update_button_style(self):
        button = self.sender()
        button.setStyleSheet(self.get_button_style(button.isChecked()))

    def load_samples(self):
        samples = {}
        sample_folder = "samples"  # Make sure this folder exists and contains your sample files
        for i in range(self.rows):
            sample_path = os.path.join(sample_folder, f"sample{i}.wav")
            if os.path.exists(sample_path):
                samples[i] = pygame.mixer.Sound(sample_path)
            else:
                print(f"Warning: Sample file {sample_path} not found.")
        return samples

    def toggle_playback(self):
        if self.playing:
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            self.timer.start(60000 // int(self.bpm_display.text()) // 4)  # 16th note timing
            self.play_button.setText("Stop")
        self.playing = not self.playing

    def update_bpm(self):
        self.bpm_display.setText(str(self.bpm_slider.value()))
        if self.playing:
            self.timer.start(60000 // int(self.bpm_display.text()) // 4)

    def update_beat(self):
        mix_buffer = np.zeros(44100)  # Assuming 1 second of audio at 44.1kHz

        for i in range(self.rows):
            # Check if a button at the current step is pushed
            if self.buttons[(i, self.current_step)].isChecked():
                if i in self.samples:
                    self.samples[i].play()
                    sample_array = pygame.sndarray.array(self.samples[i])

                    # Convert stereo to mono if needed
                    if sample_array.ndim == 2 and sample_array.shape[1] == 2:
                        sample_array = sample_array.sum(axis=1) / 2  # Average the left and right channels

                    # Add the sample to the mix buffer
                    mix_buffer[:len(sample_array)] += sample_array

        # Update waveform display
        self.waveform_plot.setData(mix_buffer)

        # Move to the next step
        self.current_step = (self.current_step + 1) % self.cols

        # Highlight current step
        for i in range(self.rows):
            for j in range(self.cols):
                button = self.buttons[(i, j)]
                if j == self.current_step:
                    button.setStyleSheet(f"{self.get_button_style(button.isChecked())} border: 2px solid red;")
                else:
                    button.setStyleSheet(self.get_button_style(button.isChecked()))


    def clear_grid(self):
        for button in self.buttons.values():
            button.setChecked(False)
            button.setStyleSheet(self.get_button_style(False))

    def update_volume(self, track, value):
        if track in self.samples:
            self.samples[track].set_volume(value / 100)

    def show_effects_window(self, track):
        effects_window = QtWidgets.QWidget()
        effects_window.setWindowTitle(f"Effects for Track {track + 1} ({self.sample_names[track]})")
        layout = QtWidgets.QVBoxLayout()

        reverb_label = QtWidgets.QLabel("Reverb")
        reverb_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        reverb_slider.setRange(0, 100)
        layout.addWidget(reverb_label)
        layout.addWidget(reverb_slider)

        delay_label = QtWidgets.QLabel("Delay")
        delay_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        delay_slider.setRange(0, 100)
        layout.addWidget(delay_label)
        layout.addWidget(delay_slider)

        distortion_label = QtWidgets.QLabel("Distortion")
        distortion_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        distortion_slider.setRange(0, 100)
        layout.addWidget(distortion_label)
        layout.addWidget(distortion_slider)

        apply_button = QtWidgets.QPushButton("Apply Effects")
        apply_button.clicked.connect(lambda: self.apply_effects(track, reverb_slider.value(), delay_slider.value(), distortion_slider.value()))
        layout.addWidget(apply_button)

        effects_window.setLayout(layout)
        effects_window.show()


    def apply_effects(self, track, reverb_value, delay_value, distortion_value):
        # For now, just print the effect values
        print(f"Applying effects to track {track}: Reverb={reverb_value}, Delay={delay_value}, Distortion={distortion_value}")
        # In a full implementation, this function would modify the audio samples with the chosen effects

    def load_sample(self, track):
        # Load a new sample for a track by selecting a file
        file_dialog = QtWidgets.QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Load Sample", "", "Audio Files (*.wav)")
        if file_path:
            self.samples[track] = pygame.mixer.Sound(file_path)
            self.sample_names[track] = os.path.basename(file_path)
            self.grid_layout.itemAtPosition(track, 0).widget().setText(self.sample_names[track])

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    drum_machine = DrumMachineGUI()
    drum_machine.show()
    app.exec_()



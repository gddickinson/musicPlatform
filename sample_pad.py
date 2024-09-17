import os
from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QSlider, QLabel, QDial)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import pyqtgraph as pg
import librosa
import numpy as np

class SampleButton(QPushButton):
    def __init__(self, sample_path=None, parent=None):
        super().__init__(parent)
        self.sample_path = sample_path
        self.setMinimumSize(80, 80)
        self.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
        """)
        self.player = QMediaPlayer()
        self.volume = 100
        if sample_path:
            self.set_sample(sample_path)

    def set_sample(self, sample_path):
        self.sample_path = sample_path
        self.setText(os.path.basename(sample_path) if sample_path else "")
        if sample_path:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(sample_path)))

    def play_sample(self):
        if self.sample_path:
            self.player.setPosition(0)
            self.player.play()

    def set_volume(self, volume):
        self.volume = volume
        self.player.setVolume(volume)

class WaveformViewer(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('w')
        self.setLabel('left', 'Amplitude')
        self.setLabel('bottom', 'Time (s)')
        self.showGrid(x=True, y=True)

    def plot_waveform(self, audio, sr):
        self.clear()
        times = np.arange(len(audio)) / sr
        self.plot(times, audio, pen='b')

class SamplePadWindow(QWidget):
    def __init__(self, rows=4, cols=4):
        super().__init__()
        self.setWindowTitle("Sample Pad")
        self.setGeometry(100, 100, cols * 120, rows * 120 + 200)

        main_layout = QVBoxLayout(self)

        # Grid layout for sample buttons
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        main_layout.addWidget(grid_widget)

        # Waveform viewer
        self.waveform_viewer = WaveformViewer()
        main_layout.addWidget(self.waveform_viewer)

        # Master volume control
        master_volume_layout = QHBoxLayout()
        master_volume_label = QLabel("Master Volume:")
        self.master_volume_slider = QSlider(Qt.Horizontal)
        self.master_volume_slider.setRange(0, 100)
        self.master_volume_slider.setValue(100)
        self.master_volume_slider.valueChanged.connect(self.set_master_volume)
        master_volume_layout.addWidget(master_volume_label)
        master_volume_layout.addWidget(self.master_volume_slider)
        main_layout.addLayout(master_volume_layout)

        # Load samples button
        load_samples_btn = QPushButton("Load Samples")
        load_samples_btn.clicked.connect(self.load_samples_from_folder)
        main_layout.addWidget(load_samples_btn)

        self.buttons = []
        for row in range(rows):
            for col in range(cols):
                button = SampleButton()
                button.clicked.connect(self.play_and_show_sample)
                self.grid_layout.addWidget(button, row, col)
                self.buttons.append(button)

    def load_samples_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Sample Folder")
        if folder:
            samples = [f for f in os.listdir(folder) if f.lower().endswith(('.wav', '.mp3'))]
            for i, sample in enumerate(samples):
                if i < len(self.buttons):
                    self.buttons[i].set_sample(os.path.join(folder, sample))

    def set_master_volume(self, volume):
        for button in self.buttons:
            button.set_volume(volume)

    def play_and_show_sample(self):
        button = self.sender()
        if button.sample_path:
            button.play_sample()
            audio, sr = librosa.load(button.sample_path, sr=None)
            self.waveform_viewer.plot_waveform(audio, sr)

    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            index = key - Qt.Key_1
            if index < len(self.buttons):
                self.buttons[index].play_sample()

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    sample_pad = SamplePadWindow()
    sample_pad.show()
    sys.exit(app.exec_())

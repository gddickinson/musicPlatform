import sys
import numpy as np
import pyaudio
import wave
import io
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QSlider, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

class RecordingStudioGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recording Studio")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Audio setup
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 2
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.stream = None

        # Recording controls
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.toggle_recording)
        self.layout.addWidget(self.record_button)

        self.save_button = QPushButton("Save Recording")
        self.save_button.clicked.connect(self.save_recording)
        self.save_button.setEnabled(False)
        self.layout.addWidget(self.save_button)

        # Playback controls
        self.playback_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_recording)
        self.playback_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_playback)
        self.playback_layout.addWidget(self.stop_button)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.playback_layout.addWidget(self.volume_slider)
        self.playback_layout.addWidget(QLabel("Volume"))

        self.layout.addLayout(self.playback_layout)

        # Waveform display
        self.waveform_plot = pg.PlotWidget()
        self.layout.addWidget(self.waveform_plot)
        self.waveform_plot.setLabel('left', 'Amplitude')
        self.waveform_plot.setLabel('bottom', 'Time')

        # Timer for updating the waveform
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_timer.start(100)  # Update every 100 ms

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self.record_button.setText("Stop Recording")
        self.frames = []

        def callback(in_data, frame_count, time_info, status):
            self.frames.append(in_data)
            return (in_data, pyaudio.paContinue)

        self.stream = self.p.open(format=self.FORMAT,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  input=True,
                                  frames_per_buffer=self.CHUNK,
                                  stream_callback=callback)

        self.stream.start_stream()

    def stop_recording(self):
        self.is_recording = False
        self.record_button.setText("Record")

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        self.save_button.setEnabled(True)

    def save_recording(self):
        if not self.frames:
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Save Audio", "", "WAV Files (*.wav)")
        if filename:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.frames))
            wf.close()

    def play_recording(self):
        if not self.frames:
            return

        def callback(in_data, frame_count, time_info, status):
            data = wf.readframes(frame_count)
            return (data, pyaudio.paContinue)

        wf = wave.open(io.BytesIO(b''.join(self.frames)), 'rb')
        self.playback_stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                           channels=wf.getnchannels(),
                                           rate=wf.getframerate(),
                                           output=True,
                                           stream_callback=callback)

        self.playback_stream.start_stream()

    def stop_playback(self):
        if hasattr(self, 'playback_stream') and self.playback_stream.is_active():
            self.playback_stream.stop_stream()
            self.playback_stream.close()

    def set_volume(self, value):
        if hasattr(self, 'playback_stream'):
            volume = value / 100.0
            self.playback_stream.setVolume(volume)

    def update_waveform(self):
        if self.frames:
            waveform = np.frombuffer(b''.join(self.frames), dtype=np.int16)
            time = np.arange(len(waveform)) / self.RATE
            self.waveform_plot.clear()
            self.waveform_plot.plot(time, waveform)

    def closeEvent(self, event):
        self.stop_playback()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    studio = RecordingStudioGUI()
    studio.show()
    sys.exit(app.exec_())

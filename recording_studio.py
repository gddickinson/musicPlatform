import sys
import numpy as np
import pyaudio
import wave
import soundfile as sf
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QSlider, QFileDialog, QGroupBox, QScrollArea,
                             QMenuBar, QAction, QComboBox, QLineEdit, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
from scipy import signal
import queue

# Import necessary components from piano_keyboard.py
from piano_keyboard import PianoKeyboardWindow, PianoKey


class AudioTrack:
    def __init__(self, name, is_live=False):
        self.name = name
        self.is_live = is_live
        self.audio_data = np.array([])
        self.sample_rate = 44100
        self.volume = 1.0
        self.muted = False
        self.effects = []
        self.buffer = np.zeros(44100)  # 1 second buffer at 44.1kHz

    def apply_effects(self, data):
        for effect in self.effects:
            data = effect.process(data)
        return data

    def generate_audio(self, num_frames):
        # This method should be overridden in subclasses
        return np.zeros(num_frames)

    def update_buffer(self, new_data):
        self.buffer = np.roll(self.buffer, -len(new_data))
        self.buffer[-len(new_data):] = new_data
        #print(f"Buffer updated for {self.name}. Max value: {np.max(np.abs(self.buffer))}")


class PianoTrack(AudioTrack):
    def __init__(self, name):
        super().__init__(name)
        self.piano_keyboard = PianoKeyboardWindow()
        self.piano_keyboard.notePressed.connect(self.on_note_pressed)
        self.piano_keyboard.noteReleased.connect(self.on_note_released)
        self.active_notes = {}
        self.current_frame = 0

    def on_note_pressed(self, note):
        freq = self.piano_keyboard.note_to_freq(note)
        self.active_notes[note] = np.sin(2 * np.pi * freq * np.arange(self.sample_rate) / self.sample_rate)
        #print(f"Note pressed: {note}, Frequency: {freq}")

    def on_note_released(self, note):
        if note in self.active_notes:
            del self.active_notes[note]
        #print(f"Note released: {note}")

    def generate_audio(self, num_frames):
        audio = np.zeros(num_frames)
        for note, note_audio in self.active_notes.items():
            start = self.current_frame % len(note_audio)
            end = start + num_frames
            if end <= len(note_audio):
                audio += note_audio[start:end]
            else:
                audio[:len(note_audio)-start] += note_audio[start:]
                audio[len(note_audio)-start:] += note_audio[:end-len(note_audio)]

        audio = audio * self.volume
        self.update_buffer(audio)
        self.current_frame += num_frames
        #print(f"Generated audio for {self.name}. Max value: {np.max(np.abs(audio))}")
        return audio

class AudioEffect:
    def __init__(self, name):
        self.name = name

    def process(self, data):
        return data

class ReverbEffect(AudioEffect):
    def __init__(self, room_size=0.5, damping=0.5):
        super().__init__("Reverb")
        self.room_size = room_size
        self.damping = damping
        self.buffer = np.zeros(88200)  # 2 seconds buffer at 44.1kHz

    def process(self, data):
        output = np.zeros_like(data)
        for i, sample in enumerate(data):
            self.buffer = np.roll(self.buffer, -1)
            self.buffer[-1] = sample
            reverb = np.sum(self.buffer * self.room_size * np.exp(-np.arange(len(self.buffer)) * self.damping / 44100))
            output[i] = sample + reverb
        return output

class DistortionEffect(AudioEffect):
    def __init__(self, amount=0.5):
        super().__init__("Distortion")
        self.amount = amount

    def process(self, data):
        return np.tanh(data * self.amount) / np.tanh(self.amount)

class TrackWidget(QGroupBox):
    def __init__(self, track, parent=None):
        super().__init__(track.name, parent)
        self.track = track
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Waveform display
        self.waveform_plot = pg.PlotWidget(height=100)
        self.waveform_plot.setLabel('left', 'Amplitude')
        self.waveform_plot.setLabel('bottom', 'Time (s)')
        self.waveform_plot.setYRange(-1, 1)
        self.waveform_item = self.waveform_plot.plot(pen='y')
        layout.addWidget(self.waveform_plot)

        # Volume slider
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.track.volume * 100))
        self.volume_slider.valueChanged.connect(self.update_volume)
        volume_layout.addWidget(self.volume_slider)
        layout.addLayout(volume_layout)

        # Mute button
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self.toggle_mute)
        layout.addWidget(self.mute_button)

        self.setLayout(layout)

        # Timer for updating waveform
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_timer.start(50)  # Update every 50 ms

    def update_volume(self, value):
        self.track.volume = value / 100

    def toggle_mute(self, checked):
        self.track.muted = checked

    def update_waveform(self):
        audio_data = self.track.generate_audio(1024)  # Generate a small chunk of audio
        self.waveform_item.setData(audio_data)
        #print(f"Updating waveform for {self.track.name}. Max value: {np.max(np.abs(audio_data))}")

class RecordingStudioGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Track Recording Studio")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.create_menu_bar()

        # Audio setup
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.is_playing = False

        self.tracks = []
        self.current_time = 0

        # Create track list
        self.track_list_widget = QWidget()
        self.track_list_layout = QVBoxLayout(self.track_list_widget)
        self.track_scroll = QScrollArea()
        self.track_scroll.setWidgetResizable(True)
        self.track_scroll.setWidget(self.track_list_widget)
        self.layout.addWidget(self.track_scroll)

        # Controls layout
        self.controls_layout = QHBoxLayout()
        self.layout.addLayout(self.controls_layout)

        # Add Track buttons
        self.add_track_button = QPushButton("Add Audio Track")
        self.add_track_button.clicked.connect(lambda: self.add_track("audio"))
        self.controls_layout.addWidget(self.add_track_button)

        self.add_piano_track_btn = QPushButton("Add Piano Track")
        self.add_piano_track_btn.clicked.connect(self.add_piano_track)
        self.controls_layout.addWidget(self.add_piano_track_btn)

        # Transport controls
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.toggle_recording)
        self.controls_layout.addWidget(self.record_button)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        self.controls_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        self.controls_layout.addWidget(self.stop_button)

        # Time display
        self.time_display = QLabel("00:00:00")
        self.layout.addWidget(self.time_display)

        # Waveform display
        self.waveform_plot = pg.PlotWidget()
        self.layout.addWidget(self.waveform_plot)

        # Timer for updating UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(50)  # Update every 50 ms

    def process_audio(self):
        for track in self.tracks:
            if not track.muted:
                track.generate_audio(1024)  # Generate a small chunk of audio



    def add_track(self, track_type):
        if track_type == "audio":
            track = AudioTrack(f"Audio Track {len(self.tracks) + 1}")
        else:
            return
        self.tracks.append(track)
        track_widget = TrackWidget(track)
        self.track_list_layout.addWidget(track_widget)

    def add_piano_track(self):
        track_name = f"Piano Track {len(self.tracks) + 1}"
        piano_track = PianoTrack(track_name)
        self.tracks.append(piano_track)
        track_widget = TrackWidget(piano_track)
        self.track_list_layout.addWidget(track_widget)
        piano_track.piano_keyboard.show()
        print(f"Added new piano track: {track_name}")

    def audio_callback(self, in_data, frame_count, time_info, status):
        output_buffer = np.zeros(frame_count)
        for track in self.tracks:
            if not track.muted:
                track_audio = track.generate_audio(frame_count)
                output_buffer += track_audio
        return (output_buffer.astype(np.float32), pyaudio.paContinue)


    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        new_track_action = QAction('New Track', self)
        new_track_action.triggered.connect(self.add_new_track)
        file_menu.addAction(new_track_action)

        load_sample_action = QAction('Load Sample', self)
        load_sample_action.triggered.connect(self.load_sample)
        file_menu.addAction(load_sample_action)

        save_project_action = QAction('Save Project', self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        load_project_action = QAction('Load Project', self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)

        # Edit menu
        edit_menu = menubar.addMenu('Edit')

        undo_action = QAction('Undo', self)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction('Redo', self)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        # View menu
        view_menu = menubar.addMenu('View')

        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

    def add_new_track(self):
        name, ok = QInputDialog.getText(self, 'New Track', 'Enter track name:')
        if ok and name:
            track = AudioTrack(name)
            self.tracks.append(track)
            track_widget = TrackWidget(track)
            self.track_list_layout.addWidget(track_widget)

    def load_sample(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Audio Sample", "", "Audio Files (*.wav *.mp3)")
        if file_path:
            name = file_path.split('/')[-1].split('.')[0]
            track = AudioTrack(name)
            track.audio_data, track.sample_rate = sf.read(file_path)
            self.tracks.append(track)
            track_widget = TrackWidget(track)
            self.track_list_layout.addWidget(track_widget)

    def save_project(self):
        # Implement project saving logic
        pass

    def load_project(self):
        # Implement project loading logic
        pass

    def undo(self):
        # Implement undo logic
        pass

    def redo(self):
        # Implement redo logic
        pass

    def zoom_in(self):
        # Implement zoom in logic
        pass

    def zoom_out(self):
        # Implement zoom out logic
        pass

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
            self.frames.append(np.frombuffer(in_data, dtype=np.float32))
            return (in_data, pyaudio.paContinue)

        try:
            self.stream = self.p.open(format=self.FORMAT,
                                      channels=self.CHANNELS,
                                      rate=self.RATE,
                                      input=True,
                                      frames_per_buffer=self.CHUNK,
                                      stream_callback=callback)

            self.stream.start_stream()
            print("Recording started")
        except OSError as e:
            print(f"Error opening stream: {e}")
            self.is_recording = False
            self.record_button.setText("Record")

    def stop_recording(self):
        if self.is_recording and hasattr(self, 'stream'):
            self.is_recording = False
            self.record_button.setText("Record")

            self.stream.stop_stream()
            self.stream.close()

            audio_data = np.concatenate(self.frames, axis=0)
            track = AudioTrack(f"Recording {len(self.tracks) + 1}")
            track.audio_data = audio_data
            track.sample_rate = self.RATE
            self.tracks.append(track)
            track_widget = TrackWidget(track)
            self.track_list_layout.addWidget(track_widget)
            print("Recording stopped and new track added")

    def toggle_playback(self):
        if not self.is_playing:
            self.start_playback()
        else:
            self.stop_playback()

    def start_playback(self):
        self.is_playing = True
        self.play_button.setText("Pause")

        def callback(in_data, frame_count, time_info, status):
            output_data = np.zeros(frame_count, dtype=np.float32)
            for track in self.tracks:
                if not track.muted:
                    track_audio = track.generate_audio(frame_count)
                    output_data += track_audio

            print(f"Playback callback. Max output value: {np.max(np.abs(output_data))}")
            self.current_time += frame_count
            return (output_data.tobytes(), pyaudio.paContinue)

        self.stream = self.p.open(format=self.FORMAT,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  output=True,
                                  frames_per_buffer=self.CHUNK,
                                  stream_callback=callback)

        self.stream.start_stream()
        print("Playback started")


    def stop_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_button.setText("Play")
            self.stream.stop_stream()
            self.stream.close()

    def stop(self):
        self.stop_playback()
        self.current_time = 0

    def update_ui(self):
        # Update time display
        time_in_seconds = self.current_time / self.RATE
        minutes = int(time_in_seconds // 60)
        seconds = int(time_in_seconds % 60)
        milliseconds = int((time_in_seconds % 1) * 1000)
        self.time_display.setText(f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}")

        # Update waveform display
        self.waveform_plot.clear()
        for i, track in enumerate(self.tracks):
            if len(track.audio_data) > 0:
                time = np.arange(len(track.audio_data)) / track.sample_rate
                self.waveform_plot.plot(time, track.audio_data + i, pen=pg.intColor(i, len(self.tracks)))

        # Add a vertical line to show current playback position
        if self.is_playing:
            self.waveform_plot.addLine(x=self.current_time / self.RATE, pen='r')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    studio = RecordingStudioGUI()
    studio.show()
    sys.exit(app.exec_())

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
from sound_generator import EnhancedSoundGeneratorGUI
from piano_keyboard import PianoKeyboardWindow
from sample_pad import SamplePadWindow
from drum_machine import DrumMachineGUI
from recording_studio import RecordingStudioGUI

class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Production Platform")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create buttons for each component
        self.sound_generator_btn = QPushButton("Sound Generator")
        self.piano_keyboard_btn = QPushButton("Piano Keyboard")
        self.sample_pad_btn = QPushButton("Sample Pad")
        self.drum_machine_btn = QPushButton("Drum Machine")
        self.recording_studio_btn = QPushButton("Recording Studio")

        # Connect buttons to their respective functions
        self.sound_generator_btn.clicked.connect(self.open_sound_generator)
        self.piano_keyboard_btn.clicked.connect(self.open_piano_keyboard)
        self.sample_pad_btn.clicked.connect(self.open_sample_pad)
        self.drum_machine_btn.clicked.connect(self.open_drum_machine)
        self.recording_studio_btn.clicked.connect(self.open_recording_studio)

        # Add buttons to the layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.sound_generator_btn)
        button_layout.addWidget(self.piano_keyboard_btn)
        button_layout.addWidget(self.sample_pad_btn)
        button_layout.addWidget(self.drum_machine_btn)
        button_layout.addWidget(self.recording_studio_btn)

        main_layout.addLayout(button_layout)

        # Initialize component windows
        self.sound_generator_window = None
        self.piano_keyboard_window = None
        self.sample_pad_window = None
        self.drum_machine_window = None
        self.recording_studio_window = None

    def open_sound_generator(self):
        if not self.sound_generator_window:
            self.sound_generator_window = EnhancedSoundGeneratorGUI()
        self.sound_generator_window.show()

    def open_piano_keyboard(self):
        if not self.piano_keyboard_window:
            self.piano_keyboard_window = PianoKeyboardWindow()
        self.piano_keyboard_window.show()

    def open_sample_pad(self):
        if not self.sample_pad_window:
            self.sample_pad_window = SamplePadWindow()
        self.sample_pad_window.show()

    def open_drum_machine(self):
        if not self.drum_machine_window:
            self.drum_machine_window = DrumMachineGUI()
        self.drum_machine_window.show()

    def open_recording_studio(self):
        if not self.recording_studio_window:
            self.recording_studio_window = RecordingStudioGUI()
        self.recording_studio_window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainGUI()
    main_window.show()
    sys.exit(app.exec_())

"""
Drum Machine Module for the Music Production Platform.

This module provides a drum machine component with step sequencer
functionality, sample playback, and visualization.
"""

import os
import traceback
from typing import Dict, List, Optional, Tuple, Union, Any, Set, Callable

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import pygame
import pygame.sndarray

# Import the logger
from logger import get_logger

# Import utility for file dialogs
from file_dialog_utils import FileDialogUtils

# Set up module logger
logger = get_logger(__name__)


class DrumMachineError(Exception):
    """Base exception for drum machine errors."""
    pass


class SampleLoadError(DrumMachineError):
    """Exception raised when loading a sample fails."""
    pass


class SampleDirectoryError(DrumMachineError):
    """Exception raised when there's an issue with the sample directory."""
    pass


class DrumMachineGUI(QtWidgets.QMainWindow):
    """
    Graphical interface for the drum machine component.

    This class provides a step sequencer interface for creating drum patterns
    with multiple instruments, sample loading, and playback controls.

    Attributes:
        rows: Number of instrument rows
        cols: Number of steps in a pattern
        groups: Number of button groups for visual separation
        buttons: Dictionary of buttons indexed by (row, column)
        samples: Dictionary of sound samples indexed by row
        sample_names: List of sample names for each row
        current_step: Current playback position
        playing: Flag indicating if playback is active
    """

    def __init__(self):
        """Initialize the drum machine GUI."""
        super().__init__()
        logger.info("Initializing DrumMachineGUI")

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
        self.buttons: Dict[Tuple[int, int], QtWidgets.QPushButton] = {}
        self.rows: int = 12  # Number of instruments
        self.cols: int = 32  # 32 steps in each row
        self.groups: int = 8  # 8 groups of 4 buttons

        # Colors
        self.unpushed_color = QtGui.QColor(255, 255, 0)
        self.pushed_color = QtGui.QColor(0, 255, 0)

        # Sample names
        self.sample_names: List[str] = [
            "Kick", "Snare", "Hi-Hat", "Clap", "Tom 1", "Tom 2",
            "Crash", "Ride", "Perc 1", "Perc 2", "FX 1", "FX 2"
        ]

        try:
            # Set up the UI components
            self._setup_ui()

            # Initialize sample playback
            self._init_audio()

            logger.debug("DrumMachineGUI initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing DrumMachineGUI: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize the drum machine: {str(e)}"
            )
            raise

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        logger.debug("Setting up UI components")
        try:
            # Add sample names and buttons
            self._setup_pattern_grid()

            # Control panel
            self._setup_control_panel()

            # Waveform display
            self._setup_waveform_display()

            logger.debug("UI components set up successfully")
        except Exception as e:
            logger.error(f"Error setting up UI: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _setup_pattern_grid(self) -> None:
        """Set up the pattern grid with instrument rows and step buttons."""
        logger.debug("Setting up pattern grid")
        try:
            # Add sample names
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
                        button = QtWidgets.QPushButton("", self)
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

            logger.debug("Pattern grid set up successfully")
        except Exception as e:
            logger.error(f"Error setting up pattern grid: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _setup_control_panel(self) -> None:
        """Set up the playback control panel."""
        logger.debug("Setting up control panel")
        try:
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

            # Load Sample button
            self.load_sample_button = QtWidgets.QPushButton("Load Sample", self)
            self.load_sample_button.setFixedWidth(100)
            self.load_sample_button.clicked.connect(self._on_load_sample_clicked)
            self.control_panel.addWidget(self.load_sample_button)

            # Timer for playback
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.update_beat)
            self.current_step = 0
            self.playing = False

            logger.debug("Control panel set up successfully")
        except Exception as e:
            logger.error(f"Error setting up control panel: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _setup_waveform_display(self) -> None:
        """Set up the waveform display."""
        logger.debug("Setting up waveform display")
        try:
            self.waveform_widget = pg.PlotWidget()
            self.layout.addWidget(self.waveform_widget)
            self.waveform_plot = self.waveform_widget.plot(pen='y')
            self.waveform_widget.setLabel('left', 'Amplitude')
            self.waveform_widget.setLabel('bottom', 'Time')
            logger.debug("Waveform display set up successfully")
        except Exception as e:
            logger.error(f"Error setting up waveform display: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _init_audio(self) -> None:
        """Initialize the audio system and load samples."""
        logger.debug("Initializing audio system")
        try:
            # Sample playback using pygame mixer
            pygame.mixer.init()
            self.samples = self.load_samples()
            logger.debug("Audio system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing audio system: {str(e)}")
            logger.debug(traceback.format_exc())
            raise SampleLoadError(f"Failed to initialize audio system: {str(e)}")

    def get_button_style(self, is_pushed: bool) -> str:
        """
        Get the CSS style for a button based on its state.

        Args:
            is_pushed: Whether the button is in the pushed state

        Returns:
            CSS style string for the button
        """
        color = self.pushed_color if is_pushed else self.unpushed_color
        return f"background-color: {color.name()}; border: 1px solid black;"

    def update_button_style(self) -> None:
        """Update the style of a button when its state changes."""
        try:
            button = self.sender()
            if button:
                button.setStyleSheet(self.get_button_style(button.isChecked()))
        except Exception as e:
            logger.error(f"Error updating button style: {str(e)}")
            logger.debug(traceback.format_exc())

    def load_samples(self) -> Dict[int, Optional[pygame.mixer.Sound]]:
        """
        Load all samples from the samples folder.

        Returns:
            Dictionary mapping row indices to loaded sound samples

        Raises:
            SampleDirectoryError: If the samples directory cannot be created
        """
        logger.info("Loading drum samples")
        samples: Dict[int, Optional[pygame.mixer.Sound]] = {}
        sample_folder = "samples"  # Make sure this folder exists and contains your sample files

        # Try to create the samples folder if it doesn't exist
        if not os.path.exists(sample_folder):
            try:
                os.makedirs(sample_folder)
                logger.info(f"Created samples folder: {sample_folder}")
            except Exception as e:
                logger.error(f"Error creating samples folder: {str(e)}")
                logger.debug(traceback.format_exc())
                raise SampleDirectoryError(f"Could not create samples directory: {str(e)}")

        # Load samples for each row
        for i in range(self.rows):
            sample_path = os.path.join(sample_folder, f"sample{i}.wav")
            try:
                if os.path.exists(sample_path):
                    samples[i] = pygame.mixer.Sound(sample_path)
                    logger.debug(f"Loaded sample: {sample_path}")
                else:
                    # Try to find any .wav file with the prefix sample{i}
                    found = False
                    for file in os.listdir(sample_folder):
                        if file.startswith(f"sample{i}") and file.endswith((".wav", ".mp3", ".ogg")):
                            sample_path = os.path.join(sample_folder, file)
                            samples[i] = pygame.mixer.Sound(sample_path)
                            logger.debug(f"Loaded sample: {sample_path}")
                            found = True
                            break

                    if not found:
                        logger.warning(f"Sample file {sample_path} not found.")
                        samples[i] = None
            except Exception as e:
                logger.error(f"Error loading sample {sample_path}: {str(e)}")
                logger.debug(traceback.format_exc())
                samples[i] = None

        logger.info(f"Loaded {sum(1 for s in samples.values() if s is not None)} samples")
        return samples

    def _on_load_sample_clicked(self) -> None:
        """Handle the Load Sample button click."""
        try:
            # Ask which track to load a sample for
            track_names = [f"{i+1}: {self.sample_names[i]}" for i in range(self.rows)]
            track, ok = QtWidgets.QInputDialog.getItem(
                self,
                "Select Track",
                "Choose a track to load a sample for:",
                track_names,
                0,
                False
            )

            if ok and track:
                # Extract track number from selection
                track_index = int(track.split(":")[0]) - 1
                self.load_sample(track_index)
        except Exception as e:
            logger.error(f"Error handling load sample button: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.warning(
                self,
                "Load Sample Error",
                f"Error selecting track: {str(e)}"
            )

    def load_sample(self, track: int) -> None:
        """
        Load a new sample for a track by selecting a file.

        Args:
            track: The track index to load a sample for
        """
        logger.info(f"Loading sample for track {track} ({self.sample_names[track]})")
        try:
            # Use our utility function
            file_path, _ = FileDialogUtils.get_audio_file(
                self,
                title=f"Load Sample for Track {track+1} ({self.sample_names[track]})"
            )

            if file_path:
                try:
                    # Load the sample using pygame mixer
                    self.samples[track] = pygame.mixer.Sound(file_path)

                    # Update the sample name (use just the filename, not the full path)
                    self.sample_names[track] = os.path.basename(file_path)

                    # Update the label
                    label_item = self.grid_layout.itemAtPosition(track, 0)
                    if label_item and label_item.widget():
                        label_item.widget().setText(self.sample_names[track])

                    logger.info(f"Loaded sample: {file_path} for track {track}")
                except Exception as e:
                    logger.error(f"Error loading sample: {str(e)}")
                    logger.debug(traceback.format_exc())
                    # Show error message to the user
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Error Loading Sample",
                        f"Could not load the audio file.\nError: {str(e)}"
                    )
        except Exception as e:
            logger.error(f"Error in load_sample: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.critical(
                self,
                "Error Loading Sample",
                f"An unexpected error occurred.\nError: {str(e)}"
            )

    def toggle_playback(self) -> None:
        """Toggle playback start/stop."""
        try:
            if self.playing:
                self.timer.stop()
                self.play_button.setText("Play")
                logger.debug("Playback stopped")
            else:
                self.timer.start(60000 // int(self.bpm_display.text()) // 4)  # 16th note timing
                self.play_button.setText("Stop")
                logger.debug(f"Playback started at {self.bpm_display.text()} BPM")
            self.playing = not self.playing
        except Exception as e:
            logger.error(f"Error toggling playback: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.warning(
                self,
                "Playback Error",
                f"Error toggling playback: {str(e)}"
            )

    def update_bpm(self) -> None:
        """Update the BPM display and timer rate."""
        try:
            current_bpm = self.bpm_slider.value()
            self.bpm_display.setText(str(current_bpm))
            if self.playing:
                self.timer.start(60000 // current_bpm // 4)
            logger.debug(f"BPM updated to {current_bpm}")
        except Exception as e:
            logger.error(f"Error updating BPM: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_beat(self) -> None:
        """Update the current beat during playback."""
        try:
            mix_buffer = np.zeros(44100)  # Assuming 1 second of audio at 44.1kHz

            for i in range(self.rows):
                # Check if a button at the current step is pushed
                if self.buttons[(i, self.current_step)].isChecked():
                    if i in self.samples and self.samples[i]:
                        self.samples[i].play()
                        try:
                            sample_array = pygame.sndarray.array(self.samples[i])

                            # Convert stereo to mono if needed
                            if sample_array.ndim == 2 and sample_array.shape[1] == 2:
                                sample_array = sample_array.sum(axis=1) / 2  # Average the left and right channels

                            # Add the sample to the mix buffer
                            if len(sample_array) <= len(mix_buffer):
                                mix_buffer[:len(sample_array)] += sample_array
                        except Exception as e:
                            logger.error(f"Error processing sample audio for row {i}: {str(e)}")
                            logger.debug(traceback.format_exc())

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
        except Exception as e:
            logger.error(f"Error updating beat: {str(e)}")
            logger.debug(traceback.format_exc())
            # Stop playback on error to prevent continuous errors
            self.toggle_playback()
            QtWidgets.QMessageBox.warning(
                self,
                "Playback Error",
                f"Error during playback: {str(e)}\nPlayback has been stopped."
            )

    def clear_grid(self) -> None:
        """Clear all buttons in the pattern grid."""
        try:
            for button in self.buttons.values():
                button.setChecked(False)
                button.setStyleSheet(self.get_button_style(False))
            logger.debug("Pattern grid cleared")
        except Exception as e:
            logger.error(f"Error clearing grid: {str(e)}")
            logger.debug(traceback.format_exc())

    def update_volume(self, track: int, value: int) -> None:
        """
        Update the volume for a track.

        Args:
            track: The track index
            value: Volume value (0-100)
        """
        try:
            if track in self.samples and self.samples[track]:
                self.samples[track].set_volume(value / 100)
                logger.debug(f"Updated volume for track {track} to {value}%")
        except Exception as e:
            logger.error(f"Error updating volume for track {track}: {str(e)}")
            logger.debug(traceback.format_exc())

    def show_effects_window(self, track: int) -> None:
        """
        Show the effects window for a track.

        Args:
            track: The track index
        """
        try:
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
            logger.debug(f"Opened effects window for track {track}")
        except Exception as e:
            logger.error(f"Error showing effects window for track {track}: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.warning(
                self,
                "Effects Error",
                f"Error opening effects window: {str(e)}"
            )

    def apply_effects(self, track: int, reverb_value: int, delay_value: int, distortion_value: int) -> None:
        """
        Apply effects to a track.

        Args:
            track: The track index
            reverb_value: Reverb amount (0-100)
            delay_value: Delay amount (0-100)
            distortion_value: Distortion amount (0-100)
        """
        try:
            # For now, just print the effect values
            logger.info(f"Applying effects to track {track}: Reverb={reverb_value}, Delay={delay_value}, Distortion={distortion_value}")
            # In a full implementation, this function would modify the audio samples with the chosen effects
        except Exception as e:
            logger.error(f"Error applying effects to track {track}: {str(e)}")
            logger.debug(traceback.format_exc())
            QtWidgets.QMessageBox.warning(
                self,
                "Effects Error",
                f"Error applying effects: {str(e)}"
            )

    def closeEvent(self, event) -> None:
        """
        Handle the window close event.

        Args:
            event: The close event
        """
        try:
            logger.info("Closing DrumMachineGUI")
            # Stop playback if running
            if self.playing:
                self.toggle_playback()
            event.accept()
        except Exception as e:
            logger.error(f"Error during close: {str(e)}")
            logger.debug(traceback.format_exc())
            event.accept()  # Accept the close event even if there was an error


# Allow this module to be run directly
if __name__ == "__main__":
    import sys

    try:
        app = QtWidgets.QApplication([])
        drum_machine = DrumMachineGUI()
        drum_machine.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

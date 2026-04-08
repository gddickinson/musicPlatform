"""
Main GUI Module for the Music Production Platform.

This module provides the main application window and interface
for accessing the various components of the platform.
"""

import sys
import os
import traceback
from typing import Dict, List, Optional, Tuple, Union, Any, Type

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings

# Import the logger
from logger import get_logger

# Set up module logger
logger = get_logger(__name__)

# Import components
from sound_generator import EnhancedSoundGeneratorGUI
from piano_keyboard import PianoKeyboardWindow
from sample_pad import SamplePadWindow
from drum_machine import DrumMachineGUI
from recording_studio import RecordingStudioGUI


class ComponentError(Exception):
    """Base exception for component-related errors."""
    pass


class ComponentInitError(ComponentError):
    """Exception raised when a component fails to initialize."""
    pass


class ComponentNotFoundError(ComponentError):
    """Exception raised when a component is not found."""
    pass


class MainGUI(QMainWindow):
    """
    Main GUI for the Music Production Platform.

    This class provides the main application window and buttons
    for accessing the various components of the platform.

    Attributes:
        sound_generator_window: Sound generator component window
        piano_keyboard_window: Piano keyboard component window
        sample_pad_window: Sample pad component window
        drum_machine_window: Drum machine component window
        recording_studio_window: Recording studio component window
    """

    def __init__(self):
        """Initialize the main GUI."""
        super().__init__()
        logger.info("Initializing MainGUI")

        # Set window properties
        self.setWindowTitle("Music Production Platform")
        self.setGeometry(100, 100, 800, 600)

        # Initialize component windows
        self.sound_generator_window: Optional[EnhancedSoundGeneratorGUI] = None
        self.piano_keyboard_window: Optional[PianoKeyboardWindow] = None
        self.sample_pad_window: Optional[SamplePadWindow] = None
        self.drum_machine_window: Optional[DrumMachineGUI] = None
        self.recording_studio_window: Optional[RecordingStudioGUI] = None

        # Set up UI
        self._init_ui()

        logger.debug("MainGUI initialized")

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create buttons for each component
        self._create_component_buttons(main_layout)

    def _create_component_buttons(self, layout: QVBoxLayout) -> None:
        """
        Create buttons for each component.

        Args:
            layout: The layout to add buttons to
        """
        button_layout = QHBoxLayout()

        # Sound generator button
        self.sound_generator_btn = QPushButton("Sound Generator")
        self.sound_generator_btn.clicked.connect(self._open_sound_generator)

        # Piano keyboard button
        self.piano_keyboard_btn = QPushButton("Piano Keyboard")
        self.piano_keyboard_btn.clicked.connect(self._open_piano_keyboard)

        # Sample pad button
        self.sample_pad_btn = QPushButton("Sample Pad")
        self.sample_pad_btn.clicked.connect(self._open_sample_pad)

        # Drum machine button
        self.drum_machine_btn = QPushButton("Drum Machine")
        self.drum_machine_btn.clicked.connect(self._open_drum_machine)

        # Recording studio button
        self.recording_studio_btn = QPushButton("Recording Studio")
        self.recording_studio_btn.clicked.connect(self._open_recording_studio)

        # Add buttons to layout
        button_layout.addWidget(self.sound_generator_btn)
        button_layout.addWidget(self.piano_keyboard_btn)
        button_layout.addWidget(self.sample_pad_btn)
        button_layout.addWidget(self.drum_machine_btn)
        button_layout.addWidget(self.recording_studio_btn)

        layout.addLayout(button_layout)

    def _open_sound_generator(self) -> None:
        """Open the sound generator component."""
        try:
            if not self.sound_generator_window:
                logger.info("Opening Sound Generator")
                self.sound_generator_window = EnhancedSoundGeneratorGUI()

            self.sound_generator_window.show()
            logger.debug("Sound Generator opened")
        except Exception as e:
            self._handle_component_error("Sound Generator", e)

    def _open_piano_keyboard(self) -> None:
        """Open the piano keyboard component."""
        try:
            if not self.piano_keyboard_window:
                logger.info("Opening Piano Keyboard")
                self.piano_keyboard_window = PianoKeyboardWindow()

            self.piano_keyboard_window.show()
            logger.debug("Piano Keyboard opened")
        except Exception as e:
            self._handle_component_error("Piano Keyboard", e)

    def _open_sample_pad(self) -> None:
        """Open the sample pad component."""
        try:
            if not self.sample_pad_window:
                logger.info("Opening Sample Pad")
                self.sample_pad_window = SamplePadWindow()

            self.sample_pad_window.show()
            logger.debug("Sample Pad opened")
        except Exception as e:
            self._handle_component_error("Sample Pad", e)

    def _open_drum_machine(self) -> None:
        """Open the drum machine component."""
        try:
            if not self.drum_machine_window:
                logger.info("Opening Drum Machine")
                self.drum_machine_window = DrumMachineGUI()

            self.drum_machine_window.show()
            logger.debug("Drum Machine opened")
        except Exception as e:
            self._handle_component_error("Drum Machine", e)

    def _open_recording_studio(self) -> None:
        """Open the recording studio component."""
        try:
            if not self.recording_studio_window:
                logger.info("Opening Recording Studio")
                self.recording_studio_window = RecordingStudioGUI()

            self.recording_studio_window.show()
            logger.debug("Recording Studio opened")
        except Exception as e:
            self._handle_component_error("Recording Studio", e)

    def _handle_component_error(self, component_name: str, error: Exception) -> None:
        """
        Handle errors that occur when opening components.

        Args:
            component_name: Name of the component
            error: The exception that occurred
        """
        error_msg = f"Error opening {component_name}: {str(error)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())

        QMessageBox.critical(
            self,
            f"{component_name} Error",
            f"An error occurred while opening the {component_name}:\n\n{str(error)}"
        )

    def closeEvent(self, event) -> None:
        """
        Handle the window close event.

        Args:
            event: The close event
        """
        # Close all component windows
        component_windows = [
            self.sound_generator_window,
            self.piano_keyboard_window,
            self.sample_pad_window,
            self.drum_machine_window,
            self.recording_studio_window
        ]

        for window in component_windows:
            if window:
                try:
                    window.close()
                except Exception as e:
                    logger.warning(f"Error closing component window: {str(e)}")

        logger.info("MainGUI closed")
        event.accept()


def start_application() -> None:
    """
    Start the application.

    This function initializes the application, creates the main window,
    and starts the event loop.
    """
    app = QApplication(sys.argv)

    try:
        main_window = MainGUI()
        main_window.show()
        logger.info("Application started")
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Error starting application: {str(e)}")
        logger.debug(traceback.format_exc())

        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Application Error")
        error_dialog.setText("An error occurred while starting the application.")
        error_dialog.setInformativeText(str(e))
        error_dialog.setDetailedText(traceback.format_exc())
        error_dialog.exec_()

        sys.exit(1)


if __name__ == '__main__':
    # Initialize logging
    start_application()

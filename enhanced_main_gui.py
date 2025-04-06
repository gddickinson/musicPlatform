"""
Enhanced Main GUI Module for the Music Production Platform.

This module provides an advanced main interface for the music production
platform with additional features such as project management, preset
management, and mixer integration.
"""

import sys
import os
import traceback
from typing import Dict, List, Optional, Tuple, Union, Any, Type, Callable

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QTabWidget, QSplitter, QMenuBar, QMenu, QAction, QToolBar, QLabel,
    QStatusBar, QDockWidget, QFileDialog, QMessageBox, QDialog, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QIcon, QKeySequence

# Import the logger
from logger import get_logger

# Set up module logger
logger = get_logger(__name__)

# Import components
from piano_keyboard import PianoKeyboardWindow
from sample_pad import SamplePadWindow
from drum_machine import DrumMachineGUI
from sound_generator import EnhancedSoundGeneratorGUI
from recording_studio import RecordingStudioGUI

# Import new components
# Project Manager
from project_manager import Project, ProjectManagerWidget
# Preset Manager
from preset_manager import PresetManagerWidget, PianoPreset, DrumPreset, SoundGeneratorPreset
# Mixer
from mixer import MixerWidget, AudioBus, MixerChannel


class ComponentError(Exception):
    """Base exception for component-related errors."""
    pass


class ComponentInitError(ComponentError):
    """Exception raised when a component fails to initialize."""
    pass


class ComponentNotFoundError(ComponentError):
    """Exception raised when a component is not found."""
    pass


class EnhancedMainGUI(QMainWindow):
    """
    Enhanced main GUI for the music production platform.
    This class integrates all components and provides a unified interface.

    Attributes:
        settings: Application settings
        piano_keyboard: Piano keyboard component
        sample_pad: Sample pad component
        drum_machine: Drum machine component
        sound_generator: Sound generator component
        recording_studio: Recording studio component
        project_manager: Project manager component
        preset_manager: Preset manager component
        mixer: Mixer component
    """

    def __init__(self):
        """Initialize the enhanced main GUI."""
        super().__init__()
        logger.info("Initializing EnhancedMainGUI")

        # Set window properties
        self.setWindowTitle("Music Production Platform")
        self.setGeometry(100, 100, 1200, 800)

        # Load settings
        self.settings = QSettings("MusicProductionPlatform", "App")
        self.loadSettings()

        # Initialize components
        self.piano_keyboard: Optional[PianoKeyboardWindow] = None
        self.sample_pad: Optional[SamplePadWindow] = None
        self.drum_machine: Optional[DrumMachineGUI] = None
        self.sound_generator: Optional[EnhancedSoundGeneratorGUI] = None
        self.recording_studio: Optional[RecordingStudioGUI] = None

        # Initialize project and preset managers
        try:
            self.project_manager = ProjectManagerWidget()
            self.project_manager.projectLoaded.connect(self.loadProject)
            self.project_manager.projectCreated.connect(self.loadProject)
            self.project_manager.projectClosed.connect(self.closeProject)
            logger.debug("Project manager initialized")
        except Exception as e:
            self._handle_component_error("Project Manager", e)
            self.project_manager = None

        try:
            self.preset_manager = PresetManagerWidget()
            self.preset_manager.presetLoaded.connect(self.loadPreset)
            logger.debug("Preset manager initialized")
        except Exception as e:
            self._handle_component_error("Preset Manager", e)
            self.preset_manager = None

        # Initialize mixer
        try:
            self.mixer = MixerWidget()
            logger.debug("Mixer initialized")
        except Exception as e:
            self._handle_component_error("Mixer", e)
            self.mixer = None

        # Set up UI
        self.initUI()

        # Timer for auto-save
        self.autoSaveTimer = QTimer(self)
        self.autoSaveTimer.timeout.connect(self.autoSaveProject)
        self.autoSaveTimer.start(60000)  # Auto-save every minute
        logger.debug("Auto-save timer started")

        logger.info("EnhancedMainGUI initialized")

    def initUI(self) -> None:
        """Initialize the UI components."""
        try:
            # Central widget with tabs
            self.central_widget = QTabWidget()
            self.setCentralWidget(self.central_widget)

            # Components tab
            self.components_tab = QWidget()
            components_layout = QVBoxLayout(self.components_tab)

            # Create buttons for each component
            self._create_component_buttons(components_layout)

            # Add the components tab
            self.central_widget.addTab(self.components_tab, "Components")

            # Add the project manager tab if available
            if self.project_manager:
                self.central_widget.addTab(self.project_manager, "Project Manager")

            # Add the preset manager tab if available
            if self.preset_manager:
                self.central_widget.addTab(self.preset_manager, "Preset Manager")

            # Add the mixer tab if available
            if self.mixer:
                self.central_widget.addTab(self.mixer, "Mixer")

            # Create status bar
            self.statusBar = QStatusBar()
            self.setStatusBar(self.statusBar)
            self.statusBar.showMessage("Ready")

            # Create menu bar
            self.createMenuBar()

            # Create toolbar
            self.createToolBar()

            logger.debug("UI initialized")
        except Exception as e:
            logger.error(f"Error initializing UI: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _create_component_buttons(self, layout: QVBoxLayout) -> None:
        """
        Create buttons for each component.

        Args:
            layout: The layout to add the buttons to
        """
        try:
            # Buttons layout
            button_layout = QHBoxLayout()

            # Create buttons for each component
            self.piano_btn = QPushButton("Piano Keyboard")
            self.piano_btn.clicked.connect(self.open_piano_keyboard)

            self.sample_pad_btn = QPushButton("Sample Pad")
            self.sample_pad_btn.clicked.connect(self.open_sample_pad)

            self.drum_machine_btn = QPushButton("Drum Machine")
            self.drum_machine_btn.clicked.connect(self.open_drum_machine)

            self.sound_generator_btn = QPushButton("Sound Generator")
            self.sound_generator_btn.clicked.connect(self.open_sound_generator)

            self.recording_studio_btn = QPushButton("Recording Studio")
            self.recording_studio_btn.clicked.connect(self.open_recording_studio)

            button_layout.addWidget(self.piano_btn)
            button_layout.addWidget(self.sample_pad_btn)
            button_layout.addWidget(self.drum_machine_btn)
            button_layout.addWidget(self.sound_generator_btn)
            button_layout.addWidget(self.recording_studio_btn)

            layout.addLayout(button_layout)

            # Info label
            info_label = QLabel("Open components using the buttons above. Each component will open in its own window.")
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)

            logger.debug("Component buttons created")
        except Exception as e:
            logger.error(f"Error creating component buttons: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def createMenuBar(self) -> None:
        """Create the application menu bar."""
        try:
            menuBar = self.menuBar()

            # File menu
            fileMenu = menuBar.addMenu("File")

            newAction = QAction("New Project", self)
            newAction.setShortcut(QKeySequence.New)
            newAction.triggered.connect(self._on_new_project)
            fileMenu.addAction(newAction)

            openAction = QAction("Open Project", self)
            openAction.setShortcut(QKeySequence.Open)
            openAction.triggered.connect(self._on_open_project)
            fileMenu.addAction(openAction)

            saveAction = QAction("Save Project", self)
            saveAction.setShortcut(QKeySequence.Save)
            saveAction.triggered.connect(self._on_save_project)
            fileMenu.addAction(saveAction)

            fileMenu.addSeparator()

            exitAction = QAction("Exit", self)
            exitAction.setShortcut(QKeySequence.Quit)
            exitAction.triggered.connect(self.close)
            fileMenu.addAction(exitAction)

            # Edit menu
            editMenu = menuBar.addMenu("Edit")

            undoAction = QAction("Undo", self)
            undoAction.setShortcut(QKeySequence.Undo)
            # undoAction.triggered.connect(self.undo)  # Implement this
            editMenu.addAction(undoAction)

            redoAction = QAction("Redo", self)
            redoAction.setShortcut(QKeySequence.Redo)
            # redoAction.triggered.connect(self.redo)  # Implement this
            editMenu.addAction(redoAction)

            editMenu.addSeparator()

            preferencesAction = QAction("Preferences", self)
            preferencesAction.triggered.connect(self.showPreferences)
            editMenu.addAction(preferencesAction)

            # View menu
            viewMenu = menuBar.addMenu("View")

            componentsAction = QAction("Components", self)
            componentsAction.triggered.connect(lambda: self.central_widget.setCurrentIndex(0))
            viewMenu.addAction(componentsAction)

            projectAction = QAction("Project Manager", self)
            projectAction.triggered.connect(lambda: self._show_tab(1, "Project Manager"))
            viewMenu.addAction(projectAction)

            presetAction = QAction("Preset Manager", self)
            presetAction.triggered.connect(lambda: self._show_tab(2, "Preset Manager"))
            viewMenu.addAction(presetAction)

            mixerAction = QAction("Mixer", self)
            mixerAction.triggered.connect(lambda: self._show_tab(3, "Mixer"))
            viewMenu.addAction(mixerAction)

            # Help menu
            helpMenu = menuBar.addMenu("Help")

            aboutAction = QAction("About", self)
            aboutAction.triggered.connect(self.showAbout)
            helpMenu.addAction(aboutAction)

            documentationAction = QAction("Documentation", self)
            documentationAction.triggered.connect(self.showDocumentation)
            helpMenu.addAction(documentationAction)

            logger.debug("Menu bar created")
        except Exception as e:
            logger.error(f"Error creating menu bar: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def createToolBar(self) -> None:
        """Create the application toolbar."""
        try:
            toolbar = QToolBar("Main Toolbar")
            self.addToolBar(toolbar)

            # Add toolbar actions
            newAction = QAction("New", self)
            newAction.triggered.connect(self._on_new_project)
            toolbar.addAction(newAction)

            openAction = QAction("Open", self)
            openAction.triggered.connect(self._on_open_project)
            toolbar.addAction(openAction)

            saveAction = QAction("Save", self)
            saveAction.triggered.connect(self._on_save_project)
            toolbar.addAction(saveAction)

            toolbar.addSeparator()

            # Add component buttons
            pianoBtnAction = QAction("Piano", self)
            pianoBtnAction.triggered.connect(self.open_piano_keyboard)
            toolbar.addAction(pianoBtnAction)

            drumBtnAction = QAction("Drums", self)
            drumBtnAction.triggered.connect(self.open_drum_machine)
            toolbar.addAction(drumBtnAction)

            sampleBtnAction = QAction("Samples", self)
            sampleBtnAction.triggered.connect(self.open_sample_pad)
            toolbar.addAction(sampleBtnAction)

            synthBtnAction = QAction("Synth", self)
            synthBtnAction.triggered.connect(self.open_sound_generator)
            toolbar.addAction(synthBtnAction)

            recordBtnAction = QAction("Record", self)
            recordBtnAction.triggered.connect(self.open_recording_studio)
            toolbar.addAction(recordBtnAction)

            logger.debug("Toolbar created")
        except Exception as e:
            logger.error(f"Error creating toolbar: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def _on_new_project(self) -> None:
        """Handle the New Project action."""
        try:
            if self.project_manager:
                self.project_manager.create_new_project()
            else:
                self._show_component_unavailable_message("Project Manager")
        except Exception as e:
            self._handle_component_error("Project Manager", e)

    def _on_open_project(self) -> None:
        """Handle the Open Project action."""
        try:
            if self.project_manager:
                self.project_manager.open_project()
            else:
                self._show_component_unavailable_message("Project Manager")
        except Exception as e:
            self._handle_component_error("Project Manager", e)

    def _on_save_project(self) -> None:
        """Handle the Save Project action."""
        try:
            if self.project_manager:
                self.project_manager.save_project()
            else:
                self._show_component_unavailable_message("Project Manager")
        except Exception as e:
            self._handle_component_error("Project Manager", e)

    def _show_tab(self, index: int, tab_name: str) -> None:
        """
        Show a specific tab if it exists.

        Args:
            index: The index of the tab
            tab_name: The name of the tab
        """
        if index < self.central_widget.count():
            self.central_widget.setCurrentIndex(index)
        else:
            self._show_component_unavailable_message(tab_name)

    def _show_component_unavailable_message(self, component_name: str) -> None:
        """
        Show a message indicating a component is unavailable.

        Args:
            component_name: The name of the unavailable component
        """
        self.statusBar.showMessage(f"{component_name} is not available")
        QMessageBox.information(
            self,
            "Component Unavailable",
            f"The {component_name} component is not available.",
            QMessageBox.Ok
        )

    def open_piano_keyboard(self) -> None:
        """Open the piano keyboard component."""
        try:
            if not self.piano_keyboard:
                logger.info("Opening Piano Keyboard")
                self.piano_keyboard = PianoKeyboardWindow()

                # Add to mixer if available
                if self.mixer:
                    piano_bus = self.mixer.add_channel("Piano").bus
                    logger.debug("Added Piano to mixer")

                # If we have an integration panel with MIDI, connect it
                if hasattr(self, 'integration_panel') and self.integration_panel:
                    # This will trigger the MIDI connection to work now that piano exists
                    self.integration_panel.setup_midi_listeners()
                    logger.debug("Set up MIDI listeners for Piano")

            self.piano_keyboard.show()
            self.statusBar.showMessage("Piano Keyboard opened")
            logger.debug("Piano Keyboard opened")
        except Exception as e:
            self._handle_component_error("Piano Keyboard", e)

    def open_sample_pad(self) -> None:
        """Open the sample pad component."""
        try:
            if not self.sample_pad:
                logger.info("Opening Sample Pad")
                self.sample_pad = SamplePadWindow()

                # Add to mixer if available
                if self.mixer:
                    sample_bus = self.mixer.add_channel("Sample Pad").bus
                    logger.debug("Added Sample Pad to mixer")

                    # Connect to mixer (you'll need to implement this in sample_pad.py)
                    # self.sample_pad.audioGenerated.connect(sample_bus.update_buffer)

            self.sample_pad.show()
            self.statusBar.showMessage("Sample Pad opened")
            logger.debug("Sample Pad opened")
        except Exception as e:
            self._handle_component_error("Sample Pad", e)

    def open_drum_machine(self) -> None:
        """Open the drum machine component."""
        try:
            if not self.drum_machine:
                logger.info("Opening Drum Machine")
                self.drum_machine = DrumMachineGUI()

                # Add to mixer if available
                if self.mixer:
                    drum_bus = self.mixer.add_channel("Drum Machine").bus
                    logger.debug("Added Drum Machine to mixer")

                    # Connect to mixer (you'll need to implement this in drum_machine.py)
                    # self.drum_machine.audioGenerated.connect(drum_bus.update_buffer)

            self.drum_machine.show()
            self.statusBar.showMessage("Drum Machine opened")
            logger.debug("Drum Machine opened")
        except Exception as e:
            self._handle_component_error("Drum Machine", e)

    def open_sound_generator(self) -> None:
        """Open the sound generator component."""
        try:
            if not self.sound_generator:
                logger.info("Opening Sound Generator")
                self.sound_generator = EnhancedSoundGeneratorGUI()

                # Add to mixer if available
                if self.mixer:
                    synth_bus = self.mixer.add_channel("Sound Generator").bus
                    logger.debug("Added Sound Generator to mixer")

                    # Connect to mixer (you'll need to implement this in sound_generator.py)
                    # self.sound_generator.audioGenerated.connect(synth_bus.update_buffer)

            self.sound_generator.show()
            self.statusBar.showMessage("Sound Generator opened")
            logger.debug("Sound Generator opened")
        except Exception as e:
            self._handle_component_error("Sound Generator", e)

    def open_recording_studio(self) -> None:
        """Open the recording studio component."""
        try:
            if not self.recording_studio:
                logger.info("Opening Recording Studio")
                self.recording_studio = RecordingStudioGUI()

                # Add to mixer if available
                if self.mixer:
                    recording_bus = self.mixer.add_channel("Recording Studio").bus
                    logger.debug("Added Recording Studio to mixer")

                    # Connect to mixer (you'll need to implement this in recording_studio.py)
                    # self.recording_studio.audioGenerated.connect(recording_bus.update_buffer)

            self.recording_studio.show()
            self.statusBar.showMessage("Recording Studio opened")
            logger.debug("Recording Studio opened")
        except Exception as e:
            self._handle_component_error("Recording Studio", e)

    def _handle_component_error(self, component_name: str, error: Exception) -> None:
        """
        Handle errors that occur when opening components.

        Args:
            component_name: The name of the component
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

        # Update status bar
        self.statusBar.showMessage(f"Error opening {component_name}")

    def loadProject(self, project: Project) -> None:
        """
        Load a project.

        Args:
            project: The project to load
        """
        try:
            self.statusBar.showMessage(f"Loading project: {project.name}")
            logger.info(f"Loading project: {project.name}")

            # Load project settings
            if hasattr(project, 'bpm'):
                self.updateBPM(project.bpm)
                logger.debug(f"Updated BPM to {project.bpm}")

            # Load tracks
            if hasattr(project, 'tracks'):
                for track_data in project.tracks:
                    # Implement loading each track type
                    logger.debug(f"Loading track: {track_data.get('name', 'Unnamed')}")
                    pass

            # Load mixer state
            if hasattr(project, 'mixer_state') and project.mixer_state and self.mixer:
                # Implement loading mixer state
                logger.debug("Loading mixer state")
                pass

            self.statusBar.showMessage(f"Project loaded: {project.name}")
            logger.info(f"Project loaded: {project.name}")
        except Exception as e:
            error_msg = f"Error loading project: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

            self.statusBar.showMessage("Error loading project")
            QMessageBox.critical(
                self,
                "Project Error",
                f"An error occurred while loading the project:\n\n{str(e)}"
            )

    def closeProject(self) -> None:
        """Close the current project."""
        try:
            logger.info("Closing project")
            # Close all component windows
            if self.piano_keyboard:
                self.piano_keyboard.close()
                self.piano_keyboard = None
                logger.debug("Closed Piano Keyboard")

            if self.sample_pad:
                self.sample_pad.close()
                self.sample_pad = None
                logger.debug("Closed Sample Pad")

            if self.drum_machine:
                self.drum_machine.close()
                self.drum_machine = None
                logger.debug("Closed Drum Machine")

            if self.sound_generator:
                self.sound_generator.close()
                self.sound_generator = None
                logger.debug("Closed Sound Generator")

            if self.recording_studio:
                self.recording_studio.close()
                self.recording_studio = None
                logger.debug("Closed Recording Studio")

            # Reset mixer if available
            if self.mixer:
                # Implement mixer reset
                logger.debug("Reset mixer")
                pass

            self.statusBar.showMessage("Project closed")
            logger.info("Project closed")
        except Exception as e:
            error_msg = f"Error closing project: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

            self.statusBar.showMessage("Error closing project")
            QMessageBox.critical(
                self,
                "Project Error",
                f"An error occurred while closing the project:\n\n{str(e)}"
            )

    def loadPreset(self, preset: Any) -> None:
        """
        Load a preset.

        Args:
            preset: The preset to load
        """
        try:
            self.statusBar.showMessage(f"Loading preset: {preset.name}")
            logger.info(f"Loading preset: {preset.name}")

            # Apply preset based on its type
            if preset.preset_type == "piano" and self.piano_keyboard:
                if not self.piano_keyboard:
                    self.open_piano_keyboard()
                preset.apply_to_piano(self.piano_keyboard)
                logger.debug(f"Applied piano preset: {preset.name}")

            elif preset.preset_type == "drum" and self.drum_machine:
                if not self.drum_machine:
                    self.open_drum_machine()
                preset.apply_to_drum_machine(self.drum_machine)
                logger.debug(f"Applied drum preset: {preset.name}")

            elif preset.preset_type == "sound" and self.sound_generator:
                if not self.sound_generator:
                    self.open_sound_generator()
                preset.apply_to_sound_generator(self.sound_generator)
                logger.debug(f"Applied sound generator preset: {preset.name}")

            self.statusBar.showMessage(f"Preset loaded: {preset.name}")
        except Exception as e:
            error_msg = f"Error loading preset: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

            self.statusBar.showMessage("Error loading preset")
            QMessageBox.critical(
                self,
                "Preset Error",
                f"An error occurred while loading the preset:\n\n{str(e)}"
            )

    def updateBPM(self, bpm: float) -> None:
        """
        Update the BPM across all components.

        Args:
            bpm: The new BPM value
        """
        try:
            logger.debug(f"Updating BPM to {bpm}")

            # Update drum machine if available
            if self.drum_machine and hasattr(self.drum_machine, 'bpm_slider'):
                self.drum_machine.bpm_slider.setValue(int(bpm))
                logger.debug(f"Updated Drum Machine BPM to {bpm}")

            # Update other components as needed

            logger.debug(f"BPM updated to {bpm}")
        except Exception as e:
            error_msg = f"Error updating BPM: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def autoSaveProject(self) -> None:
        """Auto-save the current project."""
        try:
            if self.project_manager and self.project_manager.current_project:
                logger.debug("Auto-saving project")
                self.project_manager.save_project()
                self.statusBar.showMessage("Project auto-saved", 3000)  # Show for 3 seconds
        except Exception as e:
            error_msg = f"Error auto-saving project: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def showPreferences(self) -> None:
        """Show the preferences dialog."""
        try:
            # Implement preferences dialog
            logger.debug("Showing preferences dialog")
            QMessageBox.information(self, "Preferences", "Preferences dialog not implemented yet.")
        except Exception as e:
            error_msg = f"Error showing preferences: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def showAbout(self) -> None:
        """Show the about dialog."""
        try:
            logger.debug("Showing about dialog")
            QMessageBox.about(
                self, "About Music Production Platform",
                "Music Production Platform\n\n"
                "A powerful digital audio workstation built with Python and PyQt5.\n\n"
                "Features:\n"
                "- Piano Keyboard\n"
                "- Drum Machine\n"
                "- Sample Pad\n"
                "- Sound Generator\n"
                "- Recording Studio\n"
                "- Mixer\n"
                "- Project Management\n"
                "- Preset Management\n"
            )
        except Exception as e:
            error_msg = f"Error showing about dialog: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def showDocumentation(self) -> None:
        """Show the documentation."""
        try:
            # Implement documentation viewer or open browser to docs
            logger.debug("Showing documentation")
            QMessageBox.information(self, "Documentation", "Documentation not implemented yet.")
        except Exception as e:
            error_msg = f"Error showing documentation: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def loadSettings(self) -> None:
        """Load application settings."""
        try:
            logger.debug("Loading application settings")
            size = self.settings.value("size", self.size())
            pos = self.settings.value("pos", self.pos())

            self.resize(size)
            self.move(pos)
            logger.debug("Application settings loaded")
        except Exception as e:
            error_msg = f"Error loading settings: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def saveSettings(self) -> None:
        """Save application settings."""
        try:
            logger.debug("Saving application settings")
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
            logger.debug("Application settings saved")
        except Exception as e:
            error_msg = f"Error saving settings: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())

    def closeEvent(self, event) -> None:
        """
        Handle application close event.

        Args:
            event: The close event
        """
        try:
            logger.info("Application closing")

            # Ask for confirmation if a project is open
            if self.project_manager and self.project_manager.current_project:
                result = QMessageBox.question(
                    self, "Exit",
                    "Do you want to save your project before exiting?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )

                if result == QMessageBox.Cancel:
                    event.ignore()
                    logger.info("Close canceled")
                    return

                if result == QMessageBox.Yes:
                    self.project_manager.save_project()
                    logger.debug("Project saved before exit")

            # Save settings
            self.saveSettings()

            # Close all component windows
            if self.piano_keyboard:
                self.piano_keyboard.close()
                logger.debug("Piano Keyboard closed")

            if self.sample_pad:
                self.sample_pad.close()
                logger.debug("Sample Pad closed")

            if self.drum_machine:
                self.drum_machine.close()
                logger.debug("Drum Machine closed")

            if self.sound_generator:
                self.sound_generator.close()
                logger.debug("Sound Generator closed")

            if self.recording_studio:
                self.recording_studio.close()
                logger.debug("Recording Studio closed")

            logger.info("Application closed")
            event.accept()
        except Exception as e:
            error_msg = f"Error during application close: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            event.accept()  # Accept the close event even if there was an error


def start_application() -> None:
    """
    Start the application.

    This function initializes the application, creates the main window,
    and starts the event loop.
    """
    app = QApplication(sys.argv)

    try:
        # Set application style
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        # Create and show main window
        main_window = EnhancedMainGUI()
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

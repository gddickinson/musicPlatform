import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                            QTabWidget, QSplitter, QMenuBar, QMenu, QAction, QToolBar, QLabel,
                            QStatusBar, QDockWidget, QFileDialog, QMessageBox, QDialog, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QIcon, QKeySequence

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


class EnhancedMainGUI(QMainWindow):
    """
    Enhanced main GUI for the music production platform.
    This class integrates all components and provides a unified interface.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Production Platform")
        self.setGeometry(100, 100, 1200, 800)

        # Load settings
        self.settings = QSettings("MusicProductionPlatform", "App")
        self.loadSettings()

        # Initialize components
        self.piano_keyboard = None
        self.sample_pad = None
        self.drum_machine = None
        self.sound_generator = None
        self.recording_studio = None

        # Initialize project and preset managers
        self.project_manager = ProjectManagerWidget()
        self.project_manager.projectLoaded.connect(self.loadProject)
        self.project_manager.projectCreated.connect(self.loadProject)
        self.project_manager.projectClosed.connect(self.closeProject)

        self.preset_manager = PresetManagerWidget()
        self.preset_manager.presetLoaded.connect(self.loadPreset)

        # Initialize mixer
        self.mixer = MixerWidget()

        # Set up UI
        self.initUI()

        # Timer for auto-save
        self.autoSaveTimer = QTimer(self)
        self.autoSaveTimer.timeout.connect(self.autoSaveProject)
        self.autoSaveTimer.start(60000)  # Auto-save every minute

    def initUI(self):
        """Initialize the UI components"""
        # Central widget with tabs
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)

        # Components tab
        self.components_tab = QWidget()
        components_layout = QVBoxLayout(self.components_tab)

        # Create buttons for each component
        button_layout = QHBoxLayout()

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

        components_layout.addLayout(button_layout)

        # Info label
        info_label = QLabel("Open components using the buttons above. Each component will open in its own window.")
        info_label.setAlignment(Qt.AlignCenter)
        components_layout.addWidget(info_label)

        # Add the components tab
        self.central_widget.addTab(self.components_tab, "Components")

        # Add the project manager tab
        self.central_widget.addTab(self.project_manager, "Project Manager")

        # Add the preset manager tab
        self.central_widget.addTab(self.preset_manager, "Preset Manager")

        # Add the mixer tab
        self.central_widget.addTab(self.mixer, "Mixer")

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Create menu bar
        self.createMenuBar()

        # Create toolbar
        self.createToolBar()

    def createMenuBar(self):
        """Create the application menu bar"""
        menuBar = self.menuBar()

        # File menu
        fileMenu = menuBar.addMenu("File")

        newAction = QAction("New Project", self)
        newAction.setShortcut(QKeySequence.New)
        newAction.triggered.connect(self.project_manager.create_new_project)
        fileMenu.addAction(newAction)

        openAction = QAction("Open Project", self)
        openAction.setShortcut(QKeySequence.Open)
        openAction.triggered.connect(self.project_manager.open_project)
        fileMenu.addAction(openAction)

        saveAction = QAction("Save Project", self)
        saveAction.setShortcut(QKeySequence.Save)
        saveAction.triggered.connect(self.project_manager.save_project)
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
        projectAction.triggered.connect(lambda: self.central_widget.setCurrentIndex(1))
        viewMenu.addAction(projectAction)

        presetAction = QAction("Preset Manager", self)
        presetAction.triggered.connect(lambda: self.central_widget.setCurrentIndex(2))
        viewMenu.addAction(presetAction)

        mixerAction = QAction("Mixer", self)
        mixerAction.triggered.connect(lambda: self.central_widget.setCurrentIndex(3))
        viewMenu.addAction(mixerAction)

        # Help menu
        helpMenu = menuBar.addMenu("Help")

        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.showAbout)
        helpMenu.addAction(aboutAction)

        documentationAction = QAction("Documentation", self)
        documentationAction.triggered.connect(self.showDocumentation)
        helpMenu.addAction(documentationAction)

    def createToolBar(self):
        """Create the application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Add toolbar actions
        newAction = QAction("New", self)
        newAction.triggered.connect(self.project_manager.create_new_project)
        toolbar.addAction(newAction)

        openAction = QAction("Open", self)
        openAction.triggered.connect(self.project_manager.open_project)
        toolbar.addAction(openAction)

        saveAction = QAction("Save", self)
        saveAction.triggered.connect(self.project_manager.save_project)
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

    def open_piano_keyboard(self):
        """Open the piano keyboard component"""
        if not self.piano_keyboard:
            self.piano_keyboard = PianoKeyboardWindow()

            # Add to mixer
            piano_bus = self.mixer.add_channel("Piano").bus

            # If we have an integration panel with MIDI, connect it
            if hasattr(self, 'integration_panel') and self.integration_panel:
                # This will trigger the MIDI connection to work now that piano exists
                self.integration_panel.setup_midi_listeners()

        self.piano_keyboard.show()
        self.statusBar.showMessage("Piano Keyboard opened")

    def open_sample_pad(self):
        """Open the sample pad component"""
        if not self.sample_pad:
            self.sample_pad = SamplePadWindow()

            # Add to mixer
            sample_bus = self.mixer.add_channel("Sample Pad").bus

            # Connect to mixer (you'll need to implement this in sample_pad.py)
            # self.sample_pad.audioGenerated.connect(sample_bus.update_buffer)

        self.sample_pad.show()
        self.statusBar.showMessage("Sample Pad opened")

    def open_drum_machine(self):
        """Open the drum machine component"""
        if not self.drum_machine:
            self.drum_machine = DrumMachineGUI()

            # Add to mixer
            drum_bus = self.mixer.add_channel("Drum Machine").bus

            # Connect to mixer (you'll need to implement this in drum_machine.py)
            # self.drum_machine.audioGenerated.connect(drum_bus.update_buffer)

        self.drum_machine.show()
        self.statusBar.showMessage("Drum Machine opened")

    def open_sound_generator(self):
        """Open the sound generator component"""
        if not self.sound_generator:
            self.sound_generator = EnhancedSoundGeneratorGUI()

            # Add to mixer
            synth_bus = self.mixer.add_channel("Sound Generator").bus

            # Connect to mixer (you'll need to implement this in sound_generator.py)
            # self.sound_generator.audioGenerated.connect(synth_bus.update_buffer)

        self.sound_generator.show()
        self.statusBar.showMessage("Sound Generator opened")

    def open_recording_studio(self):
        """Open the recording studio component"""
        if not self.recording_studio:
            self.recording_studio = RecordingStudioGUI()

            # Add to mixer
            recording_bus = self.mixer.add_channel("Recording Studio").bus

            # Connect to mixer (you'll need to implement this in recording_studio.py)
            # self.recording_studio.audioGenerated.connect(recording_bus.update_buffer)

        self.recording_studio.show()
        self.statusBar.showMessage("Recording Studio opened")

    def loadProject(self, project):
        """Load a project"""
        self.statusBar.showMessage(f"Loading project: {project.name}")

        # Load project settings
        if hasattr(project, 'bpm'):
            self.updateBPM(project.bpm)

        # Load tracks
        if hasattr(project, 'tracks'):
            for track_data in project.tracks:
                # Implement loading each track type
                pass

        # Load mixer state
        if hasattr(project, 'mixer_state') and project.mixer_state:
            # Implement loading mixer state
            pass

        self.statusBar.showMessage(f"Project loaded: {project.name}")

    def closeProject(self):
        """Close the current project"""
        # Close all component windows
        if self.piano_keyboard:
            self.piano_keyboard.close()
            self.piano_keyboard = None

        if self.sample_pad:
            self.sample_pad.close()
            self.sample_pad = None

        if self.drum_machine:
            self.drum_machine.close()
            self.drum_machine = None

        if self.sound_generator:
            self.sound_generator.close()
            self.sound_generator = None

        if self.recording_studio:
            self.recording_studio.close()
            self.recording_studio = None

        # Reset mixer
        # Implement this

        self.statusBar.showMessage("Project closed")

    def loadPreset(self, preset):
        """Load a preset"""
        self.statusBar.showMessage(f"Loading preset: {preset.name}")

        # Apply preset based on its type
        if preset.preset_type == "piano":
            if not self.piano_keyboard:
                self.open_piano_keyboard()
            preset.apply_to_piano(self.piano_keyboard)

        elif preset.preset_type == "drum":
            if not self.drum_machine:
                self.open_drum_machine()
            preset.apply_to_drum_machine(self.drum_machine)

        elif preset.preset_type == "sound":
            if not self.sound_generator:
                self.open_sound_generator()
            preset.apply_to_sound_generator(self.sound_generator)

        self.statusBar.showMessage(f"Preset loaded: {preset.name}")

    def updateBPM(self, bpm):
        """Update the BPM across all components"""
        if self.drum_machine:
            self.drum_machine.bpm_slider.setValue(int(bpm))

        # Update other components as needed

    def autoSaveProject(self):
        """Auto-save the current project"""
        # Implement auto-save logic
        pass

    def showPreferences(self):
        """Show the preferences dialog"""
        # Implement preferences dialog
        QMessageBox.information(self, "Preferences", "Preferences dialog not implemented yet.")

    def showAbout(self):
        """Show the about dialog"""
        QMessageBox.about(self, "About Music Production Platform",
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
                        "- Preset Management\n")

    def showDocumentation(self):
        """Show the documentation"""
        # Implement documentation viewer or open browser to docs
        QMessageBox.information(self, "Documentation", "Documentation not implemented yet.")

    def loadSettings(self):
        """Load application settings"""
        size = self.settings.value("size", self.size())
        pos = self.settings.value("pos", self.pos())

        self.resize(size)
        self.move(pos)

    def saveSettings(self):
        """Save application settings"""
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

    def closeEvent(self, event):
        """Handle application close event"""
        # Ask for confirmation if a project is open
        if self.project_manager.current_project:
            result = QMessageBox.question(
                self, "Exit",
                "Do you want to save your project before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if result == QMessageBox.Cancel:
                event.ignore()
                return

            if result == QMessageBox.Yes:
                self.project_manager.save_project()

        # Save settings
        self.saveSettings()

        # Close all component windows
        if self.piano_keyboard:
            self.piano_keyboard.close()

        if self.sample_pad:
            self.sample_pad.close()

        if self.drum_machine:
            self.drum_machine.close()

        if self.sound_generator:
            self.sound_generator.close()

        if self.recording_studio:
            self.recording_studio.close()

        event.accept()

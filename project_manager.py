import os
import json
import numpy as np
import pickle
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
                            QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

class Project:
    """
    Represents a music production project, containing all tracks,
    instruments, samples, and session data
    """
    def __init__(self, name, folder_path):
        self.name = name
        self.folder_path = folder_path
        self.sample_files = []  # List of sample files used in the project
        self.tracks = []        # List of track configurations
        self.mixer_state = {}   # Dictionary of mixer settings
        self.bpm = 120.0        # Project tempo
        self.time_signature = (4, 4)  # Time signature as a tuple (beats per bar, beat value)
        self.created_at = None  # Project creation timestamp
        self.modified_at = None # Last modified timestamp
        
    def add_sample(self, file_path):
        """Add a sample file to the project"""
        if os.path.exists(file_path):
            # Copy the file to the project folder
            sample_folder = os.path.join(self.folder_path, "samples")
            if not os.path.exists(sample_folder):
                os.makedirs(sample_folder)
                
            # Get file name
            file_name = os.path.basename(file_path)
            
            # Check if a file with the same name already exists
            if file_name in [os.path.basename(s) for s in self.sample_files]:
                # Generate a unique name
                base, ext = os.path.splitext(file_name)
                i = 1
                while f"{base}_{i}{ext}" in [os.path.basename(s) for s in self.sample_files]:
                    i += 1
                file_name = f"{base}_{i}{ext}"
                
            # Copy file to project folder
            dest_path = os.path.join(sample_folder, file_name)
            import shutil
            shutil.copy2(file_path, dest_path)
            
            # Add to sample list
            self.sample_files.append(dest_path)
            return dest_path
        return None
        
    def save(self):
        """Save the project to disk"""
        import time
        self.modified_at = time.time()
        
        # Make sure project folder exists
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            
        # Create project file
        project_file = os.path.join(self.folder_path, f"{self.name}.daw")
        
        # Create project data dictionary
        project_data = {
            "name": self.name,
            "folder_path": self.folder_path,
            "sample_files": self.sample_files,
            "bpm": self.bpm,
            "time_signature": self.time_signature,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
        
        # Save track data separately since it might be large
        tracks_file = os.path.join(self.folder_path, "tracks.pkl")
        with open(tracks_file, 'wb') as f:
            pickle.dump(self.tracks, f)
            
        # Save mixer state
        mixer_file = os.path.join(self.folder_path, "mixer.json")
        with open(mixer_file, 'w') as f:
            json.dump(self.mixer_state, f)
            
        # Save project data
        with open(project_file, 'w') as f:
            json.dump(project_data, f)
            
        return project_file
        
    @staticmethod
    def load(project_file):
        """Load a project from a project file"""
        if not os.path.exists(project_file):
            return None
            
        try:
            # Load project data
            with open(project_file, 'r') as f:
                project_data = json.load(f)
                
            # Create project object
            project = Project(project_data["name"], project_data["folder_path"])
            project.sample_files = project_data["sample_files"]
            project.bpm = project_data["bpm"]
            project.time_signature = tuple(project_data["time_signature"])
            project.created_at = project_data["created_at"]
            project.modified_at = project_data["modified_at"]
            
            # Load track data
            tracks_file = os.path.join(project.folder_path, "tracks.pkl")
            if os.path.exists(tracks_file):
                with open(tracks_file, 'rb') as f:
                    project.tracks = pickle.load(f)
                    
            # Load mixer state
            mixer_file = os.path.join(project.folder_path, "mixer.json")
            if os.path.exists(mixer_file):
                with open(mixer_file, 'r') as f:
                    project.mixer_state = json.load(f)
                    
            return project
        except Exception as e:
            print(f"Error loading project: {e}")
            return None


class NewProjectDialog(QDialog):
    """
    Dialog for creating a new project
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        
        # Project name field
        self.name_edit = QLineEdit()
        layout.addRow("Project Name:", self.name_edit)
        
        # Project location field
        location_layout = QHBoxLayout()
        self.location_edit = QLineEdit()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_location)
        location_layout.addWidget(self.location_edit)
        location_layout.addWidget(self.browse_btn)
        layout.addRow("Location:", location_layout)
        
        # BPM field
        self.bpm_edit = QLineEdit("120.0")
        layout.addRow("BPM:", self.bpm_edit)
        
        # Time signature fields
        time_sig_layout = QHBoxLayout()
        self.beats_per_bar_edit = QLineEdit("4")
        self.beat_value_edit = QLineEdit("4")
        time_sig_layout.addWidget(self.beats_per_bar_edit)
        time_sig_layout.addWidget(QLabel("/"))
        time_sig_layout.addWidget(self.beat_value_edit)
        layout.addRow("Time Signature:", time_sig_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def browse_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Location")
        if folder:
            self.location_edit.setText(folder)
            
    def get_project_info(self):
        try:
            return {
                "name": self.name_edit.text(),
                "folder_path": os.path.join(self.location_edit.text(), self.name_edit.text()),
                "bpm": float(self.bpm_edit.text()),
                "time_signature": (int(self.beats_per_bar_edit.text()), 
                                  int(self.beat_value_edit.text()))
            }
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", 
                               "Please enter valid numeric values for BPM and time signature.")
            return None


class ProjectManagerWidget(QWidget):
    """
    Widget for managing projects
    """
    projectLoaded = pyqtSignal(object)  # Signal emitted when a project is loaded
    projectCreated = pyqtSignal(object)  # Signal emitted when a new project is created
    projectClosed = pyqtSignal()  # Signal emitted when a project is closed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Project buttons
        buttons_layout = QHBoxLayout()
        
        self.new_project_btn = QPushButton("New Project")
        self.new_project_btn.clicked.connect(self.create_new_project)
        
        self.open_project_btn = QPushButton("Open Project")
        self.open_project_btn.clicked.connect(self.open_project)
        
        self.save_project_btn = QPushButton("Save Project")
        self.save_project_btn.clicked.connect(self.save_project)
        self.save_project_btn.setEnabled(False)
        
        self.close_project_btn = QPushButton("Close Project")
        self.close_project_btn.clicked.connect(self.close_project)
        self.close_project_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.new_project_btn)
        buttons_layout.addWidget(self.open_project_btn)
        buttons_layout.addWidget(self.save_project_btn)
        buttons_layout.addWidget(self.close_project_btn)
        
        layout.addLayout(buttons_layout)
        
        # Project explorer
        self.tab_widget = QTabWidget()
        
        # Files tab
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["Project Files"])
        self.tab_widget.addTab(self.files_tree, "Files")
        
        # Samples tab
        samples_widget = QWidget()
        samples_layout = QVBoxLayout(samples_widget)
        
        self.samples_tree = QTreeWidget()
        self.samples_tree.setHeaderLabels(["Samples"])
        
        samples_buttons = QHBoxLayout()
        self.add_sample_btn = QPushButton("Add Sample")
        self.add_sample_btn.clicked.connect(self.add_sample)
        self.add_sample_btn.setEnabled(False)
        
        self.remove_sample_btn = QPushButton("Remove Sample")
        self.remove_sample_btn.clicked.connect(self.remove_sample)
        self.remove_sample_btn.setEnabled(False)
        
        samples_buttons.addWidget(self.add_sample_btn)
        samples_buttons.addWidget(self.remove_sample_btn)
        
        samples_layout.addWidget(self.samples_tree)
        samples_layout.addLayout(samples_buttons)
        
        self.tab_widget.addTab(samples_widget, "Samples")
        
        # Project info tab
        self.info_widget = QWidget()
        info_layout = QFormLayout(self.info_widget)
        
        self.project_name_label = QLabel("No project loaded")
        self.bpm_label = QLabel("")
        self.time_sig_label = QLabel("")
        self.created_label = QLabel("")
        self.modified_label = QLabel("")
        
        info_layout.addRow("Project:", self.project_name_label)
        info_layout.addRow("BPM:", self.bpm_label)
        info_layout.addRow("Time Signature:", self.time_sig_label)
        info_layout.addRow("Created:", self.created_label)
        info_layout.addRow("Modified:", self.modified_label)
        
        self.tab_widget.addTab(self.info_widget, "Info")
        
        layout.addWidget(self.tab_widget)
        
    def create_new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec_():
            project_info = dialog.get_project_info()
            if project_info:
                # Create project folder
                if not os.path.exists(project_info["folder_path"]):
                    os.makedirs(project_info["folder_path"])
                
                # Create project object
                import time
                project = Project(project_info["name"], project_info["folder_path"])
                project.bpm = project_info["bpm"]
                project.time_signature = project_info["time_signature"]
                project.created_at = time.time()
                project.modified_at = project.created_at
                
                # Create sample folder
                os.makedirs(os.path.join(project.folder_path, "samples"), exist_ok=True)
                
                # Save project
                project.save()
                
                # Set as current project
                self.set_current_project(project)
                
                # Emit signal
                self.projectCreated.emit(project)
                
    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "DAW Project Files (*.daw)")
        if file_path:
            project = Project.load(file_path)
            if project:
                self.set_current_project(project)
                self.projectLoaded.emit(project)
            else:
                QMessageBox.critical(self, "Error", "Failed to load project.")
                
    def save_project(self):
        if self.current_project:
            self.current_project.save()
            self.update_project_info()
            
    def close_project(self):
        if self.current_project:
            # Ask for confirmation if project has unsaved changes
            result = QMessageBox.question(self, "Close Project", 
                                         "Do you want to save your project before closing?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if result == QMessageBox.Cancel:
                return
                
            if result == QMessageBox.Yes:
                self.save_project()
                
            # Clear current project
            self.current_project = None
            
            # Update UI
            self.files_tree.clear()
            self.samples_tree.clear()
            self.project_name_label.setText("No project loaded")
            self.bpm_label.setText("")
            self.time_sig_label.setText("")
            self.created_label.setText("")
            self.modified_label.setText("")
            
            # Disable buttons
            self.save_project_btn.setEnabled(False)
            self.close_project_btn.setEnabled(False)
            self.add_sample_btn.setEnabled(False)
            self.remove_sample_btn.setEnabled(False)
            
            # Emit signal
            self.projectClosed.emit()
            
    def set_current_project(self, project):
        """Set the current project and update the UI"""
        self.current_project = project
        
        # Update UI
        self.update_project_files()
        self.update_project_samples()
        self.update_project_info()
        
        # Enable buttons
        self.save_project_btn.setEnabled(True)
        self.close_project_btn.setEnabled(True)
        self.add_sample_btn.setEnabled(True)
        
    def update_project_files(self):
        """Update the files tree with the project's files"""
        self.files_tree.clear()
        
        if not self.current_project:
            return
            
        # Create root item
        root = QTreeWidgetItem(self.files_tree, [self.current_project.name])
        root.setExpanded(True)
        
        # Add project file
        project_file = os.path.join(self.current_project.folder_path, f"{self.current_project.name}.daw")
        if os.path.exists(project_file):
            QTreeWidgetItem(root, [os.path.basename(project_file)])
            
        # Add samples folder
        samples_folder = os.path.join(self.current_project.folder_path, "samples")
        if os.path.exists(samples_folder):
            samples_item = QTreeWidgetItem(root, ["samples"])
            samples_item.setExpanded(True)
            
            # Add sample files
            for sample_file in self.current_project.sample_files:
                QTreeWidgetItem(samples_item, [os.path.basename(sample_file)])
                
    def update_project_samples(self):
        """Update the samples tree with the project's samples"""
        self.samples_tree.clear()
        
        if not self.current_project:
            return
            
        # Add sample files
        for sample_file in self.current_project.sample_files:
            QTreeWidgetItem(self.samples_tree, [os.path.basename(sample_file)])
            
    def update_project_info(self):
        """Update the project info tab"""
        if not self.current_project:
            self.project_name_label.setText("No project loaded")
            self.bpm_label.setText("")
            self.time_sig_label.setText("")
            self.created_label.setText("")
            self.modified_label.setText("")
            return
            
        # Format timestamps
        import datetime
        created = datetime.datetime.fromtimestamp(self.current_project.created_at) if self.current_project.created_at else "Unknown"
        modified = datetime.datetime.fromtimestamp(self.current_project.modified_at) if self.current_project.modified_at else "Unknown"
        
        # Update labels
        self.project_name_label.setText(self.current_project.name)
        self.bpm_label.setText(str(self.current_project.bpm))
        self.time_sig_label.setText(f"{self.current_project.time_signature[0]}/{self.current_project.time_signature[1]}")
        self.created_label.setText(str(created))
        self.modified_label.setText(str(modified))
        
    def add_sample(self):
        """Add a sample to the project"""
        if not self.current_project:
            return
            
        # Open file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Samples", "", "Audio Files (*.wav *.mp3 *.ogg *.flac)"
        )
        
        if file_paths:
            for file_path in file_paths:
                # Add sample to project
                sample_path = self.current_project.add_sample(file_path)
                if sample_path:
                    # Update UI
                    self.update_project_files()
                    self.update_project_samples()
                    
    def remove_sample(self):
        """Remove selected samples from the project"""
        if not self.current_project:
            return
            
        # Get selected samples
        selected_items = self.samples_tree.selectedItems()
        if not selected_items:
            return
            
        # Confirm removal
        result = QMessageBox.question(
            self, "Remove Samples", 
            f"Are you sure you want to remove {len(selected_items)} sample(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            for item in selected_items:
                sample_name = item.text(0)
                # Find the sample in the project
                for sample_path in list(self.current_project.sample_files):
                    if os.path.basename(sample_path) == sample_name:
                        # Remove from project
                        self.current_project.sample_files.remove(sample_path)
                        # Delete file from disk
                        try:
                            os.remove(sample_path)
                        except OSError:
                            pass
                        break
                        
            # Update UI
            self.update_project_files()
            self.update_project_samples()
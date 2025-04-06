import os
import json
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QFileDialog, QListWidget, QListWidgetItem,
                            QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
                            QComboBox, QInputDialog, QTabWidget, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal

class Preset:
    """Base class for all presets"""
    def __init__(self, name, preset_type):
        self.name = name
        self.preset_type = preset_type
        self.data = {}
        self.tags = []
        self.created_at = None
        self.modified_at = None
        
    def save(self, folder_path):
        """Save preset to a file"""
        import time
        self.modified_at = time.time()
        
        # Create preset folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        # Create preset file path
        file_path = os.path.join(folder_path, f"{self.name}.preset")
        
        # Create preset data
        preset_data = {
            "name": self.name,
            "type": self.preset_type,
            "data": self.data,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(preset_data, f)
            
        return file_path
        
    @staticmethod
    def load(file_path):
        """Load a preset from a file"""
        if not os.path.exists(file_path):
            return None
            
        try:
            # Load preset data
            with open(file_path, 'r') as f:
                preset_data = json.load(f)
                
            # Create preset object
            preset = Preset(preset_data["name"], preset_data["type"])
            preset.data = preset_data["data"]
            preset.tags = preset_data["tags"]
            preset.created_at = preset_data["created_at"]
            preset.modified_at = preset_data["modified_at"]
            
            return preset
        except Exception as e:
            print(f"Error loading preset: {e}")
            return None


class SavePresetDialog(QDialog):
    """Dialog for saving a preset"""
    def __init__(self, preset_type, current_name="", current_tags=None, parent=None):
        super().__init__(parent)
        self.preset_type = preset_type
        self.current_name = current_name
        self.current_tags = current_tags or []
        self.setWindowTitle(f"Save {preset_type} Preset")
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        
        # Preset name field
        self.name_edit = QLineEdit(self.current_name)
        layout.addRow("Preset Name:", self.name_edit)
        
        # Tags field
        self.tags_edit = QLineEdit(", ".join(self.current_tags))
        layout.addRow("Tags (comma separated):", self.tags_edit)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_preset_info(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a preset name.")
            return None
            
        tags = [tag.strip() for tag in self.tags_edit.text().split(",") if tag.strip()]
        
        return {
            "name": name,
            "type": self.preset_type,
            "tags": tags
        }


class PresetWidget(QListWidgetItem):
    """Widget for displaying a preset in a list"""
    def __init__(self, preset, parent=None):
        super().__init__(parent)
        self.preset = preset
        self.setText(preset.name)
        self.setToolTip(f"Type: {preset.preset_type}\nTags: {', '.join(preset.tags)}")


class PresetManagerWidget(QWidget):
    """Widget for managing presets"""
    presetLoaded = pyqtSignal(object)  # Signal emitted when a preset is loaded
    presetSaved = pyqtSignal(object)   # Signal emitted when a preset is saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presets_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")
        self.preset_types = [
            "piano", "drum", "sample", "sound", "effect", "track", "mixer"
        ]
        self.loaded_presets = {}  # Dictionary of loaded presets by type
        self.init_ui()
        self.load_all_presets()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Preset type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Preset Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.preset_types)
        self.type_combo.currentTextChanged.connect(self.filter_presets)
        type_layout.addWidget(self.type_combo)
        
        # Search field
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_presets)
        search_layout.addWidget(self.search_edit)
        
        # Add to layout
        layout.addLayout(type_layout)
        layout.addLayout(search_layout)
        
        # Presets list
        self.presets_list = QListWidget()
        self.presets_list.itemDoubleClicked.connect(self.load_preset)
        layout.addWidget(self.presets_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.load_selected_preset)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_preset)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_preset)
        
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.import_preset)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_preset)
        
        buttons_layout.addWidget(self.load_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.import_btn)
        buttons_layout.addWidget(self.export_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_all_presets(self):
        """Load all presets from the presets folder"""
        # Create presets folder if it doesn't exist
        os.makedirs(self.presets_folder, exist_ok=True)
        
        # Create type folders if they don't exist
        for preset_type in self.preset_types:
            type_folder = os.path.join(self.presets_folder, preset_type)
            os.makedirs(type_folder, exist_ok=True)
            
            # Initialize preset list for this type
            self.loaded_presets[preset_type] = []
            
            # Load presets of this type
            for file_name in os.listdir(type_folder):
                if file_name.endswith(".preset"):
                    file_path = os.path.join(type_folder, file_name)
                    preset = Preset.load(file_path)
                    if preset:
                        self.loaded_presets[preset_type].append(preset)
                        
        # Update UI
        self.filter_presets()
        
    def filter_presets(self):
        """Filter presets based on selected type and search text"""
        self.presets_list.clear()
        
        preset_type = self.type_combo.currentText()
        search_text = self.search_edit.text().lower()
        
        if preset_type not in self.loaded_presets:
            return
            
        for preset in self.loaded_presets[preset_type]:
            # Check if preset matches search text
            if (search_text in preset.name.lower() or
                any(search_text in tag.lower() for tag in preset.tags)):
                # Add to list
                item = PresetWidget(preset, self.presets_list)
                self.presets_list.addItem(item)
                
    def load_preset(self, item):
        """Load the selected preset"""
        preset = item.preset
        self.presetLoaded.emit(preset)
        
    def load_selected_preset(self):
        """Load the selected preset from the list"""
        items = self.presets_list.selectedItems()
        if items:
            self.load_preset(items[0])
            
    def save_preset(self, preset_data=None):
        """Save a new preset or update an existing one"""
        preset_type = self.type_combo.currentText()
        
        # Get preset info
        dialog = SavePresetDialog(preset_type, parent=self)
        if dialog.exec_():
            preset_info = dialog.get_preset_info()
            if preset_info:
                # Create preset object
                import time
                preset = Preset(preset_info["name"], preset_info["type"])
                preset.tags = preset_info["tags"]
                preset.created_at = time.time()
                preset.modified_at = preset.created_at
                
                # Set preset data
                if preset_data is not None:
                    preset.data = preset_data
                else:
                    # Get data from current state (implementation depends on your application)
                    preset.data = self.get_current_state(preset_type)
                    
                # Save preset
                preset_folder = os.path.join(self.presets_folder, preset_type)
                preset.save(preset_folder)
                
                # Add to loaded presets
                self.loaded_presets[preset_type].append(preset)
                
                # Update UI
                self.filter_presets()
                
                # Emit signal
                self.presetSaved.emit(preset)
                
    def get_current_state(self, preset_type):
        """Get the current state of the component to save as a preset"""
        # This method should be overridden or injected by the component
        # For now, return an empty dictionary
        return {}
        
    def delete_preset(self):
        """Delete the selected preset"""
        items = self.presets_list.selectedItems()
        if not items:
            return
            
        preset = items[0].preset
        
        # Confirm deletion
        result = QMessageBox.question(
            self, "Delete Preset", 
            f"Are you sure you want to delete the preset '{preset.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Remove preset file
            preset_folder = os.path.join(self.presets_folder, preset.preset_type)
            preset_file = os.path.join(preset_folder, f"{preset.name}.preset")
            try:
                os.remove(preset_file)
            except OSError:
                pass
                
            # Remove from loaded presets
            self.loaded_presets[preset.preset_type].remove(preset)
            
            # Update UI
            self.filter_presets()
            
    def import_preset(self):
        """Import a preset from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Preset", "", "Preset Files (*.preset)"
        )
        
        if file_path:
            preset = Preset.load(file_path)
            if preset:
                # Check if preset type is valid
                if preset.preset_type not in self.preset_types:
                    QMessageBox.warning(
                        self, "Invalid Preset", 
                        f"The preset type '{preset.preset_type}' is not supported."
                    )
                    return
                    
                # Check if a preset with the same name already exists
                for existing_preset in self.loaded_presets[preset.preset_type]:
                    if existing_preset.name == preset.name:
                        result = QMessageBox.question(
                            self, "Overwrite Preset", 
                            f"A preset with the name '{preset.name}' already exists. Overwrite it?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if result == QMessageBox.No:
                            return
                        else:
                            # Remove existing preset
                            self.loaded_presets[preset.preset_type].remove(existing_preset)
                            break
                            
                # Copy preset to presets folder
                preset_folder = os.path.join(self.presets_folder, preset.preset_type)
                preset.save(preset_folder)
                
                # Add to loaded presets
                self.loaded_presets[preset.preset_type].append(preset)
                
                # Update UI
                self.filter_presets()
            else:
                QMessageBox.warning(self, "Error", "Failed to load preset.")
                
    def export_preset(self):
        """Export selected preset to a file"""
        items = self.presets_list.selectedItems()
        if not items:
            return
            
        preset = items[0].preset
        
        # Get export file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Preset", f"{preset.name}.preset", "Preset Files (*.preset)"
        )
        
        if file_path:
            # Save preset to file
            preset.save(os.path.dirname(file_path))
            

class PianoPreset(Preset):
    """Preset for piano keyboard settings"""
    def __init__(self, name):
        super().__init__(name, "piano")
        
    def apply_to_piano(self, piano_keyboard):
        """Apply preset to a piano keyboard instance"""
        if "waveform" in self.data:
            piano_keyboard.current_waveform = self.data["waveform"]
            
        if "volume" in self.data:
            piano_keyboard.volume_slider["slider"].setValue(int(self.data["volume"] * 100))
            
        if "reverb" in self.data:
            piano_keyboard.reverb_slider["slider"].setValue(int(self.data["reverb"] * 100))
            
        if "delay" in self.data:
            piano_keyboard.delay_slider["slider"].setValue(int(self.data["delay"] * 100))
            
        if "chorus" in self.data:
            piano_keyboard.chorus_slider["slider"].setValue(int(self.data["chorus"] * 100))
            
        if "distortion" in self.data:
            piano_keyboard.distortion_slider["slider"].setValue(int(self.data["distortion"] * 100))
            
        if "attack" in self.data:
            piano_keyboard.attack_slider["slider"].setValue(int(self.data["attack"] * 1000))
            
        if "decay" in self.data:
            piano_keyboard.decay_slider["slider"].setValue(int(self.data["decay"] * 1000))
            
        if "sustain" in self.data:
            piano_keyboard.sustain_level_slider["slider"].setValue(int(self.data["sustain"] * 100))
            
        if "release" in self.data:
            piano_keyboard.release_slider["slider"].setValue(int(self.data["release"] * 1000))
            
    @staticmethod
    def from_piano(piano_keyboard, name):
        """Create a preset from piano keyboard settings"""
        preset = PianoPreset(name)
        preset.data = {
            "waveform": piano_keyboard.current_waveform,
            "volume": piano_keyboard.volume_slider["slider"].value() / 100,
            "reverb": piano_keyboard.reverb_slider["slider"].value() / 100,
            "delay": piano_keyboard.delay_slider["slider"].value() / 100,
            "chorus": piano_keyboard.chorus_slider["slider"].value() / 100,
            "distortion": piano_keyboard.distortion_slider["slider"].value() / 100,
            "attack": piano_keyboard.attack_slider["slider"].value() / 1000,
            "decay": piano_keyboard.decay_slider["slider"].value() / 1000,
            "sustain": piano_keyboard.sustain_level_slider["slider"].value() / 100,
            "release": piano_keyboard.release_slider["slider"].value() / 1000
        }
        return preset


class DrumPreset(Preset):
    """Preset for drum machine settings"""
    def __init__(self, name):
        super().__init__(name, "drum")
        
    def apply_to_drum_machine(self, drum_machine):
        """Apply preset to a drum machine instance"""
        if "pattern" in self.data:
            # Clear current pattern
            drum_machine.clear_grid()
            
            # Set new pattern
            for pos, enabled in self.data["pattern"].items():
                row, col = map(int, pos.split(","))
                button = drum_machine.buttons.get((row, col))
                if button and enabled:
                    button.setChecked(True)
                    button.setStyleSheet(drum_machine.get_button_style(True))
                    
        if "bpm" in self.data:
            drum_machine.bpm_slider.setValue(self.data["bpm"])
            
        if "volumes" in self.data:
            for row, volume in self.data["volumes"].items():
                # Find the volume dial for this row
                for j in range(drum_machine.grid_layout.columnCount()):
                    item = drum_machine.grid_layout.itemAtPosition(int(row), j)
                    if item and isinstance(item.widget(), QDial):
                        item.widget().setValue(int(volume * 100))
                        break
                        
    @staticmethod
    def from_drum_machine(drum_machine, name):
        """Create a preset from drum machine settings"""
        preset = DrumPreset(name)
        
        # Save pattern
        pattern = {}
        for (row, col), button in drum_machine.buttons.items():
            pattern[f"{row},{col}"] = button.isChecked()
            
        # Save volumes
        volumes = {}
        for row in range(drum_machine.rows):
            for j in range(drum_machine.grid_layout.columnCount()):
                item = drum_machine.grid_layout.itemAtPosition(row, j)
                if item and isinstance(item.widget(), QDial):
                    volumes[str(row)] = item.widget().value() / 100
                    break
                    
        preset.data = {
            "pattern": pattern,
            "bpm": drum_machine.bpm_slider.value(),
            "volumes": volumes
        }
        
        return preset


class SoundGeneratorPreset(Preset):
    """Preset for sound generator settings"""
    def __init__(self, name):
        super().__init__(name, "sound")
        
    def apply_to_sound_generator(self, sound_generator):
        """Apply preset to a sound generator instance"""
        if "tracks" not in self.data:
            return
            
        # Remove all existing tracks
        while sound_generator.tracks:
            track = sound_generator.tracks[0]
            sound_generator.remove_track(track, track.controls)
            
        # Add tracks from preset
        for track_data in self.data["tracks"]:
            track_type = track_data.get("type")
            if track_type == "wave":
                track = sound_generator.add_track("wave")
                if "frequency" in track_data:
                    track.set_frequency(track_data["frequency"])
                if "wave_type" in track_data:
                    track.set_wave_type(track_data["wave_type"])
            elif track_type == "noise":
                track = sound_generator.add_track("noise")
                if "noise_type" in track_data:
                    track.set_noise_type(track_data["noise_type"])
            elif track_type == "fm":
                track = sound_generator.add_track("fm")
                if "carrier_freq" in track_data:
                    track.set_carrier_frequency(track_data["carrier_freq"])
                if "mod_freq" in track_data:
                    track.set_mod_frequency(track_data["mod_freq"])
                if "mod_index" in track_data:
                    track.set_mod_index(track_data["mod_index"])
                    
            # Set track volume
            if "amplitude" in track_data:
                track.set_amplitude(track_data["amplitude"])
                
            # Add effects
            if "effects" in track_data:
                for effect_data in track_data["effects"]:
                    effect_name = effect_data.get("name")
                    if effect_name == "Reverb":
                        effect = ReverbEffect(
                            room_size=effect_data.get("room_size", 0.5),
                            damping=effect_data.get("damping", 0.5)
                        )
                        track.add_effect(effect)
                    elif effect_name == "Distortion":
                        effect = DistortionEffect(
                            amount=effect_data.get("amount", 0.5)
                        )
                        track.add_effect(effect)
                        
    @staticmethod
    def from_sound_generator(sound_generator, name):
        """Create a preset from sound generator settings"""
        preset = SoundGeneratorPreset(name)
        
        tracks_data = []
        for track in sound_generator.tracks:
            track_data = {
                "amplitude": track.amplitude
            }
            
            if isinstance(track, WaveTrack):
                track_data["type"] = "wave"
                track_data["frequency"] = track.frequency
                track_data["wave_type"] = track.wave_type
            elif isinstance(track, NoiseTrack):
                track_data["type"] = "noise"
                track_data["noise_type"] = track.noise_type
            elif isinstance(track, FMSynthTrack):
                track_data["type"] = "fm"
                track_data["carrier_freq"] = track.carrier_freq
                track_data["mod_freq"] = track.mod_freq
                track_data["mod_index"] = track.mod_index
                
            # Save effects
            effects_data = []
            for effect in track.effects:
                effect_data = {
                    "name": effect.__class__.__name__
                }
                
                if isinstance(effect, ReverbEffect):
                    effect_data["room_size"] = effect.room_size
                    effect_data["damping"] = effect.damping
                elif isinstance(effect, DistortionEffect):
                    effect_data["amount"] = effect.amount
                    
                effects_data.append(effect_data)
                
            track_data["effects"] = effects_data
            tracks_data.append(track_data)
            
        preset.data = {
            "tracks": tracks_data
        }
        
        return preset
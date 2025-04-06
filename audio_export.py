"""
Audio Export System for the Music Production Platform
Allows exporting compositions as WAV, MP3, and other audio formats
"""

import numpy as np
import soundfile as sf
import os
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QPushButton, QLabel, QProgressBar, QFileDialog, 
                           QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, 
                           QCheckBox, QMessageBox)

class AudioExporter(QObject):
    """Class for exporting audio to various formats"""
    # Define signals
    exportStarted = pyqtSignal()
    exportProgress = pyqtSignal(int)
    exportCompleted = pyqtSignal(str)
    exportError = pyqtSignal(str)
    
    def __init__(self, audio_system=None, routing_matrix=None):
        super().__init__()
        self.audio_system = audio_system
        self.routing_matrix = routing_matrix
        self.sample_rate = 44100
        self.buffer_size = 1024
        self.running = False
        self.export_thread = None
        
    def export_audio(self, file_path, duration, audio_format='wav', bit_depth=16, 
                    sample_rate=44100, channels=2, normalize=True):
        """Export audio to a file"""
        if self.running:
            self.exportError.emit("Export already in progress")
            return False
            
        # Validate parameters
        if duration <= 0:
            self.exportError.emit("Duration must be greater than 0")
            return False
            
        # Check if file exists and can be written
        try:
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
        except Exception as e:
            self.exportError.emit(f"Error creating directory: {str(e)}")
            return False
            
        # Set parameters
        self.sample_rate = sample_rate
        
        # Start export thread
        self.running = True
        self.export_thread = threading.Thread(
            target=self._export_thread,
            args=(file_path, duration, audio_format, bit_depth, channels, normalize)
        )
        self.export_thread.daemon = True
        self.export_thread.start()
        
        return True
        
    def _export_thread(self, file_path, duration, audio_format, bit_depth, channels, normalize):
        """Export thread function"""
        try:
            self.exportStarted.emit()
            
            # Calculate total samples needed
            total_samples = int(duration * self.sample_rate)
            
            # Create buffer to hold all samples
            buffer = np.zeros((total_samples, channels))
            
            # Get audio from the audio system
            samples_collected = 0
            
            while samples_collected < total_samples and self.running:
                # Determine how many samples to collect in this iteration
                samples_to_collect = min(self.buffer_size, total_samples - samples_collected)
                
                # Get audio from the routing matrix or audio system
                if self.routing_matrix and self.routing_matrix.master_node:
                    audio = self.routing_matrix.get_master_output()
                elif self.audio_system:
                    audio = self.audio_system.get_output_audio(samples_to_collect)
                else:
                    # Generate silence if no audio system
                    audio = np.zeros(samples_to_collect)
                    
                # Reshape audio to match channels
                if len(audio.shape) == 1:
                    # Mono to stereo conversion
                    if channels == 2:
                        audio = np.column_stack((audio, audio))
                    else:
                        audio = audio.reshape(-1, 1)
                else:
                    # Reshape/truncate channels as needed
                    audio = audio[:, :channels]
                    
                # Add to buffer
                buffer[samples_collected:samples_collected + len(audio)] = audio
                samples_collected += len(audio)
                
                # Update progress
                progress = int(samples_collected / total_samples * 100)
                self.exportProgress.emit(progress)
                
                # Short sleep to prevent CPU hogging
                time.sleep(0.01)
                
            # Normalize if requested
            if normalize:
                max_val = np.max(np.abs(buffer))
                if max_val > 0:
                    buffer = buffer / max_val * 0.95  # Scale to 95% to avoid clipping
                    
            # Convert bit depth
            if bit_depth == 16:
                subtype = 'PCM_16'
            elif bit_depth == 24:
                subtype = 'PCM_24'
            elif bit_depth == 32:
                subtype = 'FLOAT'
            else:
                subtype = 'PCM_16'  # Default to 16-bit
                
            # Write to file
            sf.write(file_path, buffer, self.sample_rate, subtype=subtype, format=audio_format.upper())
            
            self.exportCompleted.emit(file_path)
            
        except Exception as e:
            self.exportError.emit(f"Export error: {str(e)}")
            
        finally:
            self.running = False
            
    def cancel_export(self):
        """Cancel the export process"""
        if self.running:
            self.running = False
            if self.export_thread:
                self.export_thread.join(timeout=1.0)
                self.export_thread = None
            return True
        return False


class ExportOptionsWidget(QWidget):
    """Widget for configuring export options"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # File format selection
        format_group = QGroupBox("File Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "FLAC", "OGG", "MP3"])
        format_layout.addWidget(self.format_combo)
        
        layout.addWidget(format_group)
        
        # Sample rate selection
        sample_rate_group = QGroupBox("Sample Rate")
        sample_rate_layout = QVBoxLayout(sample_rate_group)
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100 Hz", "48000 Hz", "96000 Hz", "192000 Hz"])
        sample_rate_layout.addWidget(self.sample_rate_combo)
        
        layout.addWidget(sample_rate_group)
        
        # Bit depth selection
        bit_depth_group = QGroupBox("Bit Depth")
        bit_depth_layout = QVBoxLayout(bit_depth_group)
        
        self.bit_depth_combo = QComboBox()
        self.bit_depth_combo.addItems(["16-bit", "24-bit", "32-bit float"])
        bit_depth_layout.addWidget(self.bit_depth_combo)
        
        layout.addWidget(bit_depth_group)
        
        # Channels selection
        channels_group = QGroupBox("Channels")
        channels_layout = QVBoxLayout(channels_group)
        
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["Mono", "Stereo"])
        channels_layout.addWidget(self.channels_combo)
        
        layout.addWidget(channels_group)
        
        # Duration selection
        duration_group = QGroupBox("Duration")
        duration_layout = QGridLayout(duration_group)
        
        duration_layout.addWidget(QLabel("Minutes:"), 0, 0)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 60)
        self.minutes_spin.setValue(3)
        duration_layout.addWidget(self.minutes_spin, 0, 1)
        
        duration_layout.addWidget(QLabel("Seconds:"), 1, 0)
        self.seconds_spin = QDoubleSpinBox()
        self.seconds_spin.setRange(0, 59.99)
        self.seconds_spin.setValue(0)
        self.seconds_spin.setDecimals(2)
        duration_layout.addWidget(self.seconds_spin, 1, 1)
        
        layout.addWidget(duration_group)
        
        # Normalization option
        self.normalize_check = QCheckBox("Normalize audio")
        self.normalize_check.setChecked(True)
        layout.addWidget(self.normalize_check)
        
    def get_export_options(self):
        """Get the current export options"""
        # Get format
        format_map = {
            "WAV": "wav",
            "FLAC": "flac",
            "OGG": "ogg",
            "MP3": "mp3"
        }
        audio_format = format_map[self.format_combo.currentText()]
        
        # Get sample rate
        sample_rate = int(self.sample_rate_combo.currentText().split()[0])
        
        # Get bit depth
        bit_depth_map = {
            "16-bit": 16,
            "24-bit": 24,
            "32-bit float": 32
        }
        bit_depth = bit_depth_map[self.bit_depth_combo.currentText()]
        
        # Get channels
        channels = 1 if self.channels_combo.currentText() == "Mono" else 2
        
        # Get duration
        duration = self.minutes_spin.value() * 60 + self.seconds_spin.value()
        
        # Get normalization
        normalize = self.normalize_check.isChecked()
        
        return {
            "audio_format": audio_format,
            "sample_rate": sample_rate,
            "bit_depth": bit_depth,
            "channels": channels,
            "duration": duration,
            "normalize": normalize
        }


class ExportDialog(QWidget):
    """Dialog for exporting audio"""
    def __init__(self, exporter, parent=None):
        super().__init__(parent)
        self.exporter = exporter
        self.file_path = ""
        self.init_ui()
        
        # Connect signals
        self.exporter.exportStarted.connect(self.export_started)
        self.exporter.exportProgress.connect(self.update_progress)
        self.exporter.exportCompleted.connect(self.export_completed)
        self.exporter.exportError.connect(self.export_error)
        
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("Export Audio")
        self.setGeometry(300, 300, 500, 400)
        
        layout = QVBoxLayout(self)
        
        # Options widget
        self.options_widget = ExportOptionsWidget()
        layout.addWidget(self.options_widget)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        file_layout.addWidget(self.file_path_label)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        layout.addLayout(file_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to export")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_export)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def browse_file(self):
        """Open a file dialog to select the export file"""
        options = self.options_widget.get_export_options()
        file_format = options["audio_format"].upper()
        
        # Add extension filter based on the selected format
        filter_text = f"{file_format} Files (*.{options['audio_format']})"
        
        # Open the save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Audio", "", filter_text
        )
        
        if file_path:
            # Add extension if not present
            if not file_path.endswith("." + options["audio_format"]):
                file_path += "." + options["audio_format"]
                
            self.file_path = file_path
            self.file_path_label.setText(self.file_path)
            
    def start_export(self):
        """Start the export process"""
        if not self.file_path:
            QMessageBox.warning(self, "Export Error", "Please select a file location")
            return
            
        options = self.options_widget.get_export_options()
        
        # Start export
        success = self.exporter.export_audio(
            self.file_path,
            options["duration"],
            options["audio_format"],
            options["bit_depth"],
            options["sample_rate"],
            options["channels"],
            options["normalize"]
        )
        
        if not success:
            self.status_label.setText("Export failed to start")
            
    def cancel_export(self):
        """Cancel the export process"""
        self.exporter.cancel_export()
        self.status_label.setText("Export cancelled")
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
    def export_started(self):
        """Handle export started signal"""
        self.status_label.setText("Exporting...")
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
    def update_progress(self, progress):
        """Handle export progress signal"""
        self.progress_bar.setValue(progress)
        
    def export_completed(self, file_path):
        """Handle export completed signal"""
        self.status_label.setText(f"Export completed: {file_path}")
        self.progress_bar.setValue(100)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Show success message
        QMessageBox.information(
            self, "Export Completed", 
            f"Audio successfully exported to:\n{file_path}"
        )
        
    def export_error(self, error_message):
        """Handle export error signal"""
        self.status_label.setText(f"Export error: {error_message}")
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Show error message
        QMessageBox.critical(
            self, "Export Error", 
            f"An error occurred during export:\n{error_message}"
        )


# The following class implements MIDI file export functionality
class MidiExporter(QObject):
    """Class for exporting MIDI files"""
    # Define signals
    exportStarted = pyqtSignal()
    exportCompleted = pyqtSignal(str)
    exportError = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    def export_midi(self, file_path, tracks=None):
        """
        Export MIDI data to a file
        
        Parameters:
        - file_path: Path to save the MIDI file
        - tracks: List of track data, where each track is a dictionary with:
          - name: Track name
          - notes: List of note events, each is a dict with:
            - note: MIDI note number
            - start_time: Start time in seconds
            - end_time: End time in seconds
            - velocity: Note velocity (0-127)
          - control_changes: List of control change events, each is a dict with:
            - control: MIDI control number
            - time: Time in seconds
            - value: Control value (0-127)
        """
        try:
            import mido
            from mido import Message, MidiFile, MidiTrack, MetaMessage
            
            self.exportStarted.emit()
            
            # Create MIDI file
            mid = MidiFile(type=1)
            
            # Set tempo (default 120 BPM)
            tempo_track = MidiTrack()
            mid.tracks.append(tempo_track)
            
            # Add tempo meta message (120 BPM = 500000 microseconds per quarter note)
            tempo_track.append(MetaMessage('set_tempo', tempo=500000, time=0))
            
            # Process each track
            if tracks:
                for track_data in tracks:
                    # Create track
                    track = MidiTrack()
                    mid.tracks.append(track)
                    
                    # Add track name
                    if 'name' in track_data:
                        track.append(MetaMessage('track_name', name=track_data['name'], time=0))
                        
                    # Add notes
                    if 'notes' in track_data and track_data['notes']:
                        # Sort notes by start time
                        sorted_notes = sorted(track_data['notes'], key=lambda x: x['start_time'])
                        
                        # Convert to delta times
                        last_time = 0
                        for note in sorted_notes:
                            # Convert seconds to ticks (assuming 480 ticks per beat and 120 BPM)
                            start_ticks = int(note['start_time'] * 480 * 2)  # 2 beats per second at 120 BPM
                            duration_ticks = int((note['end_time'] - note['start_time']) * 480 * 2)
                            
                            # Calculate delta time
                            delta_start = start_ticks - last_time
                            
                            # Add note on message
                            track.append(Message('note_on', note=note['note'], 
                                                velocity=note['velocity'], time=delta_start))
                                                
                            # Add note off message
                            track.append(Message('note_off', note=note['note'], 
                                                velocity=0, time=duration_ticks))
                                                
                            # Update last time
                            last_time = start_ticks + duration_ticks
                            
                    # Add control changes
                    if 'control_changes' in track_data and track_data['control_changes']:
                        # Sort control changes by time
                        sorted_cc = sorted(track_data['control_changes'], key=lambda x: x['time'])
                        
                        # Convert to delta times
                        last_time = 0
                        for cc in sorted_cc:
                            # Convert seconds to ticks
                            ticks = int(cc['time'] * 480 * 2)
                            
                            # Calculate delta time
                            delta = ticks - last_time
                            
                            # Add control change message
                            track.append(Message('control_change', control=cc['control'], 
                                                value=cc['value'], time=delta))
                                                
                            # Update last time
                            last_time = ticks
            
            # Save the MIDI file
            mid.save(file_path)
            self.exportCompleted.emit(file_path)
            return True
            
        except Exception as e:
            self.exportError.emit(f"MIDI export error: {str(e)}")
            return False

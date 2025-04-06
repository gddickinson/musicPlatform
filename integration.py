"""
Integration Component for the Music Production Platform
Brings together MIDI controller support, audio routing, and export functionality
"""

import sys
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                           QPushButton, QLabel, QMessageBox, QDialog,
                           QComboBox, QGroupBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

# Import the components we've created
from midi_controller import MidiController, MidiNoteToKeyConverter
from audio_routing import RoutingMatrix, RoutingMatrixWidget
from audio_export import AudioExporter, ExportDialog, MidiExporter

class IntegratedControlPanel(QWidget):
    """
    Control panel that integrates MIDI, routing, and export functionality
    """
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app

        # Initialize components
        self.midi_controller = MidiController()
        self.routing_matrix = RoutingMatrix()
        self.audio_exporter = AudioExporter(routing_matrix=self.routing_matrix)
        self.midi_exporter = MidiExporter()

        # Track components
        self.component_nodes = {}

        # Set up the UI
        self.init_ui()

        # Scan for MIDI devices
        self.update_midi_devices()

        # Set up the main audio path
        self.setup_default_routing()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()

        # MIDI tab
        self.midi_tab = QWidget()
        self.tabs.addTab(self.midi_tab, "MIDI")
        self.setup_midi_tab()

        # Routing tab
        self.routing_tab = QWidget()
        self.tabs.addTab(self.routing_tab, "Routing")
        self.setup_routing_tab()

        # Export tab
        self.export_tab = QWidget()
        self.tabs.addTab(self.export_tab, "Export")
        self.setup_export_tab()

        layout.addWidget(self.tabs)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def setup_midi_tab(self):
        """Set up the MIDI controller tab"""
        layout = QVBoxLayout(self.midi_tab)

        # MIDI device selection
        device_group = QGroupBox("MIDI Devices")
        device_layout = QHBoxLayout(device_group)

        self.midi_device_combo = QComboBox()
        self.midi_device_combo.setMinimumWidth(300)
        device_layout.addWidget(self.midi_device_combo)

        self.refresh_midi_btn = QPushButton("Refresh")
        self.refresh_midi_btn.clicked.connect(self.update_midi_devices)
        device_layout.addWidget(self.refresh_midi_btn)

        self.connect_midi_btn = QPushButton("Connect")
        self.connect_midi_btn.clicked.connect(self.connect_midi_device)
        device_layout.addWidget(self.connect_midi_btn)

        layout.addWidget(device_group)

        # MIDI mapping section
        mapping_group = QGroupBox("MIDI Mapping")
        mapping_layout = QVBoxLayout(mapping_group)

        # Component selector
        component_layout = QHBoxLayout()
        component_layout.addWidget(QLabel("Component:"))
        self.component_combo = QComboBox()
        self.component_combo.addItems(["Piano", "Drums", "Sample Pad", "Sound Generator"])
        component_layout.addWidget(self.component_combo)

        mapping_layout.addLayout(component_layout)

        # Mapping buttons
        button_layout = QHBoxLayout()

        self.learn_midi_btn = QPushButton("Learn MIDI")
        self.learn_midi_btn.clicked.connect(self.start_midi_learn)
        button_layout.addWidget(self.learn_midi_btn)

        self.clear_mapping_btn = QPushButton("Clear Mapping")
        self.clear_mapping_btn.clicked.connect(self.clear_midi_mapping)
        button_layout.addWidget(self.clear_mapping_btn)

        mapping_layout.addLayout(button_layout)

        # MIDI monitor
        monitor_group = QGroupBox("MIDI Monitor")
        monitor_layout = QVBoxLayout(monitor_group)

        self.midi_monitor = QLabel("No MIDI activity")
        monitor_layout.addWidget(self.midi_monitor)

        mapping_layout.addWidget(monitor_group)

        layout.addWidget(mapping_group)

        # Connect MIDI signals
        self.midi_controller.noteOn.connect(self.on_midi_note_on)
        self.midi_controller.noteOff.connect(self.on_midi_note_off)
        self.midi_controller.controlChange.connect(self.on_midi_control_change)

    def setup_routing_tab(self):
        """Set up the audio routing tab"""
        layout = QVBoxLayout(self.routing_tab)

        # Create routing matrix widget
        self.routing_widget = RoutingMatrixWidget(self.routing_matrix)
        layout.addWidget(self.routing_widget)

        # Add controls
        controls_layout = QHBoxLayout()

        self.add_effect_btn = QPushButton("Add Effect")
        self.add_effect_btn.clicked.connect(self.show_add_effect_menu)
        controls_layout.addWidget(self.add_effect_btn)

        self.add_mixer_btn = QPushButton("Add Mixer")
        self.add_mixer_btn.clicked.connect(self.add_mixer)
        controls_layout.addWidget(self.add_mixer_btn)

        self.set_master_btn = QPushButton("Set Master")
        self.set_master_btn.clicked.connect(self.set_master_node)
        controls_layout.addWidget(self.set_master_btn)

        layout.addLayout(controls_layout)

    def setup_export_tab(self):
        """Set up the export tab"""
        layout = QVBoxLayout(self.export_tab)

        # Export audio button
        self.export_audio_btn = QPushButton("Export Audio")
        self.export_audio_btn.clicked.connect(self.show_audio_export_dialog)
        layout.addWidget(self.export_audio_btn)

        # Export MIDI button
        self.export_midi_btn = QPushButton("Export MIDI")
        self.export_midi_btn.clicked.connect(self.show_midi_export_dialog)
        layout.addWidget(self.export_midi_btn)

    def update_midi_devices(self):
        """Update the list of available MIDI devices"""
        self.midi_device_combo.clear()

        ports = self.midi_controller.get_available_ports()
        for port_id, port_name in ports:
            self.midi_device_combo.addItem(port_name, port_id)

        if self.midi_device_combo.count() == 0:
            self.midi_device_combo.addItem("No MIDI devices found")
            self.connect_midi_btn.setEnabled(False)
        else:
            self.connect_midi_btn.setEnabled(True)


    def connect_midi_device(self):
        """Connect to the selected MIDI device"""
        if self.midi_device_combo.count() == 0:
            return

        port_id = self.midi_device_combo.currentData()
        if port_id is not None:
            success = self.midi_controller.connect_to_port(port_id)
            if success:
                self.status_label.setText(f"Connected to MIDI device: {self.midi_device_combo.currentText()}")
                self.connect_midi_btn.setText("Disconnect")
                self.connect_midi_btn.clicked.disconnect()
                self.connect_midi_btn.clicked.connect(self.disconnect_midi_device)

                # Set up global MIDI listeners
                self.setup_midi_listeners()
            else:
                self.status_label.setText(f"Failed to connect to MIDI device")

    def disconnect_midi_device(self):
        """Disconnect from the current MIDI device"""
        self.midi_controller.disconnect()
        self.status_label.setText("Disconnected from MIDI device")
        self.connect_midi_btn.setText("Connect")
        self.connect_midi_btn.clicked.disconnect()
        self.connect_midi_btn.clicked.connect(self.connect_midi_device)

    def on_midi_note_on(self, channel, note, velocity):
        """Handle MIDI note on events"""
        note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
        self.midi_monitor.setText(f"Note On: Channel {channel+1}, Note {note} ({note_name}), Velocity {velocity}")

    def on_midi_note_off(self, channel, note):
        """Handle MIDI note off events"""
        note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
        self.midi_monitor.setText(f"Note Off: Channel {channel+1}, Note {note} ({note_name})")

    def on_midi_control_change(self, channel, control, value):
        """Handle MIDI control change events"""
        self.midi_monitor.setText(f"Control Change: Channel {channel+1}, Control {control}, Value {value}")

    def start_midi_learn(self):
        """Start MIDI learn mode"""
        self.status_label.setText("MIDI Learn mode: Press a key on your MIDI controller...")
        # Implement MIDI learn logic
        # This would listen for the next MIDI message and map it to the selected component function

    def clear_midi_mapping(self):
        """Clear MIDI mappings for the selected component"""
        component = self.component_combo.currentText()
        # Implement clearing logic
        self.status_label.setText(f"MIDI mappings cleared for {component}")

    def show_add_effect_menu(self):
        """Show menu for adding effects"""
        menu = QMenu(self)

        reverb_action = menu.addAction("Reverb")
        reverb_action.triggered.connect(lambda: self.add_effect("Reverb"))

        delay_action = menu.addAction("Delay")
        delay_action.triggered.connect(lambda: self.add_effect("Delay"))

        # Add more effects as needed

        menu.exec_(self.add_effect_btn.mapToGlobal(self.add_effect_btn.rect().bottomLeft()))

    def add_effect(self, effect_type):
        """Add an effect node to the routing matrix"""
        if effect_type == "Reverb":
            node = self.routing_matrix.create_reverb_node()
        elif effect_type == "Delay":
            node = self.routing_matrix.create_delay_node()
        else:
            return

        self.routing_widget.update_ui()
        self.status_label.setText(f"Added {effect_type} effect: {node.name}")

    def add_mixer(self):
        """Add a mixer node to the routing matrix"""
        node = self.routing_matrix.create_mixer_node(f"Mixer_{len(self.routing_matrix.nodes)}")
        self.routing_widget.update_ui()
        self.status_label.setText(f"Added mixer: {node.name}")

    def set_master_node(self):
        """Set the master output node"""
        # Get the selected node from the routing widget
        source_name = self.routing_widget.source_combo.currentText()
        if source_name and source_name in self.routing_matrix.nodes:
            self.routing_matrix.set_master_node(source_name)
            self.status_label.setText(f"Set master output to: {source_name}")

    def show_audio_export_dialog(self):
        """Show the audio export dialog"""
        dialog = ExportDialog(self.audio_exporter)
        dialog.show()

    def show_midi_export_dialog(self):
        """Show the MIDI export dialog"""
        # This would be similar to the audio export dialog
        # For now, just show a message
        QMessageBox.information(self, "MIDI Export",
                               "MIDI export functionality is in development")

    def setup_default_routing(self):
        """Set up the default audio routing"""
        # This would create the initial routing setup
        # For example, creating component nodes for each component
        # and connecting them to a master mixer

        # Example (implement based on actual components):
        # Create master mixer
        master = self.routing_matrix.create_mixer_node("Master", 4)
        self.routing_matrix.set_master_node("Master")

    def add_component_node(self, component, name):
        """Add a component node to the routing matrix"""
        if name in self.component_nodes:
            return self.component_nodes[name]

        node = self.routing_matrix.create_component_node(name, component)
        self.component_nodes[name] = node

        # Connect to the master mixer if available
        if "Master" in self.routing_matrix.nodes:
            # Find the first available input on the master mixer
            master = self.routing_matrix.nodes["Master"]
            for i in range(master.num_inputs):
                if master.input_nodes[i] is None:
                    node.connect_output(master, i)
                    break

        self.routing_widget.update_ui()
        return node




    def connect_midi_to_piano(self):
        """Connect MIDI events to the piano keyboard component"""
        if not hasattr(self.main_app, 'piano_keyboard') or not self.main_app.piano_keyboard:
            print("Piano keyboard not available")
            return False

        # Connect MIDI note on events to piano key presses
        self.midi_controller.noteOn.connect(self.on_midi_note_to_piano)
        self.midi_controller.noteOff.connect(self.on_midi_note_off_piano)

        print("MIDI controller connected to piano keyboard")
        return True

    def on_midi_note_to_piano(self, channel, note, velocity):
        """Handle MIDI note on event for piano keyboard"""
        if not hasattr(self.main_app, 'piano_keyboard') or not self.main_app.piano_keyboard:
            return

        # Convert MIDI note to note name
        note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
        if note_name:
            # Find the corresponding key in the piano keyboard
            if note_name in self.main_app.piano_keyboard.keys:
                # Trigger the note
                self.main_app.piano_keyboard.notePressed.emit(note_name)

    def on_midi_note_off_piano(self, channel, note):
        """Handle MIDI note off event for piano keyboard"""
        if not hasattr(self.main_app, 'piano_keyboard') or not self.main_app.piano_keyboard:
            return

        # Convert MIDI note to note name
        note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
        if note_name:
            # Find the corresponding key in the piano keyboard
            if note_name in self.main_app.piano_keyboard.keys:
                # Release the note
                self.main_app.piano_keyboard.noteReleased.emit(note_name)



    def setup_midi_listeners(self):
        """Set up global MIDI event listeners that work even when components aren't open yet"""

        # Listen for MIDI note events
        self.midi_controller.noteOn.connect(self.handle_global_note_on)
        self.midi_controller.noteOff.connect(self.handle_global_note_off)
        self.midi_controller.controlChange.connect(self.handle_global_control_change)

        print("Global MIDI listeners set up")

    def handle_global_note_on(self, channel, note, velocity):
        """Handle MIDI note on events globally"""
        # Check if piano keyboard is open
        if hasattr(self.main_app, 'piano_keyboard') and self.main_app.piano_keyboard:
            # Convert MIDI note to note name
            note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
            if note_name and note_name in self.main_app.piano_keyboard.keys:
                # Route the event to the piano keyboard
                self.main_app.piano_keyboard.play_note(note_name)

    def handle_global_note_off(self, channel, note):
        """Handle MIDI note off events globally"""
        # Check if piano keyboard is open
        if hasattr(self.main_app, 'piano_keyboard') and self.main_app.piano_keyboard:
            # Convert MIDI note to note name
            note_name = MidiNoteToKeyConverter.midi_to_note_name(note)
            if note_name and note_name in self.main_app.piano_keyboard.keys:
                # Route the event to the piano keyboard
                self.main_app.piano_keyboard.release_note(note_name)

    def handle_global_control_change(self, channel, control, value):
        """Handle MIDI control change events globally"""
        # You can route control changes to various parameters here
        pass





class MidiSetupDialog(QDialog):
    """Dialog for setting up MIDI mappings"""
    def __init__(self, midi_controller, component=None, parent=None):
        super().__init__(parent)
        self.midi_controller = midi_controller
        self.component = component
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("MIDI Setup")
        self.setGeometry(300, 300, 500, 400)

        layout = QVBoxLayout(self)

        # MIDI mapping list
        # This would show current mappings and allow editing

        # Learn button
        self.learn_btn = QPushButton("Learn Next Mapping")
        self.learn_btn.clicked.connect(self.start_learn)
        layout.addWidget(self.learn_btn)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def start_learn(self):
        """Start MIDI learn mode"""
        self.status_label.setText("Press a key or move a control on your MIDI device...")
        # Implement MIDI learn logic



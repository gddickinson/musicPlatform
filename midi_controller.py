"""
MIDI Controller support for the Music Production Platform - Fixed Version
Allows connecting MIDI devices and routing events to different components
"""

import rtmidi
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF, CONTROL_CHANGE
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import threading
import time

class MidiMessage:
    """Class to represent a MIDI message"""
    def __init__(self, message_type, channel, data1, data2=0):
        self.message_type = message_type  # Type of message (note on, note off, etc.)
        self.channel = channel            # MIDI channel (0-15)
        self.data1 = data1                # First data byte (note number, controller number)
        self.data2 = data2                # Second data byte (velocity, controller value)

    @classmethod
    def from_raw_message(cls, raw_message):
        """Create a MidiMessage from a raw MIDI message"""
        if len(raw_message) >= 3:
            status = raw_message[0]
            data1 = raw_message[1]
            data2 = raw_message[2] if len(raw_message) > 2 else 0

            # Extract message type and channel
            message_type = status & 0xF0
            channel = status & 0x0F

            return cls(message_type, channel, data1, data2)
        return None

class MidiController(QObject):
    """Main MIDI controller class"""
    # Define signals
    noteOn = pyqtSignal(int, int, int)  # channel, note, velocity
    noteOff = pyqtSignal(int, int)      # channel, note
    controlChange = pyqtSignal(int, int, int)  # channel, control, value

    def __init__(self):
        super().__init__()
        # Use correct class name: MidiIn instead of RtMidiIn
        self.midi_in = rtmidi.MidiIn()
        self.available_ports = self.midi_in.get_port_count()
        self.connected = False
        self.current_port = -1
        self.running = False
        self.midi_thread = None

        # Keep track of active notes to handle hanging notes
        self.active_notes = set()

        # Dictionary to map MIDI notes to component actions
        self.note_mappings = {}

        # Dictionary to map MIDI controllers to component parameters
        self.controller_mappings = {}

    def get_available_ports(self):
        """Get a list of available MIDI ports"""
        self.available_ports = self.midi_in.get_port_count()
        ports = []

        for i in range(self.available_ports):
            port_name = self.midi_in.get_port_name(i)
            ports.append((i, port_name))

        return ports

    def connect_to_port(self, port_index):
        """Connect to a specific MIDI port"""
        if port_index < 0 or port_index >= self.available_ports:
            print(f"Invalid port index: {port_index}")
            return False

        try:
            # Close existing connection if any
            if self.connected:
                self.midi_in.close_port()

            # Open the selected port
            self.midi_in.open_port(port_index)
            self.current_port = port_index
            self.connected = True

            # Don't ignore sysex, timing, or active sensing messages
            self.midi_in.ignore_types(False, False, False)

            # Start the MIDI processing thread if not already running
            if not self.running:
                self.start_processing()

            port_name = self.midi_in.get_port_name(port_index)
            print(f"Connected to MIDI port: {port_name}")
            return True

        except Exception as e:
            print(f"Error connecting to MIDI port: {e}")
            return False

    def disconnect(self):
        """Disconnect from the current MIDI port"""
        if self.connected:
            self.stop_processing()
            self.midi_in.close_port()
            self.connected = False
            self.current_port = -1
            print("Disconnected from MIDI port")

    def start_processing(self):
        """Start the MIDI processing thread"""
        if self.running:
            return

        self.running = True
        self.midi_thread = threading.Thread(target=self._midi_thread_func)
        self.midi_thread.daemon = True
        self.midi_thread.start()

    def stop_processing(self):
        """Stop the MIDI processing thread"""
        self.running = False
        if self.midi_thread:
            self.midi_thread.join(timeout=1.0)
            self.midi_thread = None

    def _midi_thread_func(self):
        """MIDI processing thread function"""
        while self.running:
            # Check for incoming MIDI messages
            message = self.midi_in.get_message()

            if message:
                # message is a tuple containing (message_data, delta_time)
                message_data, delta_time = message
                self._process_midi_message(message_data)

            time.sleep(0.001)  # Small sleep to prevent high CPU usage

    def _process_midi_message(self, message):
        """Process a MIDI message"""
        midi_msg = MidiMessage.from_raw_message(message)

        if midi_msg:
            # Handle different message types
            if midi_msg.message_type == NOTE_ON and midi_msg.data2 > 0:
                # Note On
                note = midi_msg.data1
                velocity = midi_msg.data2
                channel = midi_msg.channel

                # Add to active notes
                self.active_notes.add((channel, note))

                # Emit signal
                self.noteOn.emit(channel, note, velocity)

                # Check for mappings
                self._check_note_mappings(channel, note, velocity)

            elif midi_msg.message_type == NOTE_OFF or (midi_msg.message_type == NOTE_ON and midi_msg.data2 == 0):
                # Note Off (also handles Note On with velocity 0)
                note = midi_msg.data1
                channel = midi_msg.channel

                # Remove from active notes
                self.active_notes.discard((channel, note))

                # Emit signal
                self.noteOff.emit(channel, note)

            elif midi_msg.message_type == CONTROL_CHANGE:
                # Control Change
                controller = midi_msg.data1
                value = midi_msg.data2
                channel = midi_msg.channel

                # Emit signal
                self.controlChange.emit(channel, controller, value)

                # Check for mappings
                self._check_controller_mappings(channel, controller, value)

    def _check_note_mappings(self, channel, note, velocity):
        """Check if the note is mapped to any action"""
        mapping_key = (channel, note)
        if mapping_key in self.note_mappings:
            # Execute the mapped action
            action = self.note_mappings[mapping_key]
            if callable(action):
                action(velocity)

    def _check_controller_mappings(self, channel, controller, value):
        """Check if the controller is mapped to any parameter"""
        mapping_key = (channel, controller)
        if mapping_key in self.controller_mappings:
            # Get the mapping info
            mapping = self.controller_mappings[mapping_key]
            if 'param' in mapping and 'min_val' in mapping and 'max_val' in mapping:
                # Calculate the mapped value
                param = mapping['param']
                min_val = mapping['min_val']
                max_val = mapping['max_val']

                # Scale the MIDI value (0-127) to the parameter range
                scaled_value = min_val + (max_val - min_val) * (value / 127.0)

                # Apply the value
                if callable(param):
                    param(scaled_value)

    def map_note_to_action(self, channel, note, action):
        """Map a MIDI note to an action"""
        self.note_mappings[(channel, note)] = action

    def unmap_note(self, channel, note):
        """Remove a note mapping"""
        mapping_key = (channel, note)
        if mapping_key in self.note_mappings:
            del self.note_mappings[mapping_key]

    def map_controller_to_parameter(self, channel, controller, param, min_val=0, max_val=1):
        """Map a MIDI controller to a parameter"""
        self.controller_mappings[(channel, controller)] = {
            'param': param,
            'min_val': min_val,
            'max_val': max_val
        }

    def unmap_controller(self, channel, controller):
        """Remove a controller mapping"""
        mapping_key = (channel, controller)
        if mapping_key in self.controller_mappings:
            del self.controller_mappings[mapping_key]

    def all_notes_off(self):
        """Send Note Off for all active notes"""
        for channel, note in list(self.active_notes):
            self.noteOff.emit(channel, note)
        self.active_notes.clear()

    def close(self):
        """Close the MIDI controller"""
        self.all_notes_off()
        self.stop_processing()
        if self.connected:
            self.midi_in.close_port()
            self.connected = False


class MidiNoteToKeyConverter:
    """Helper class to convert MIDI notes to musical note names"""
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    @staticmethod
    def midi_to_note_name(midi_note):
        """Convert a MIDI note number to a note name with octave"""
        if 0 <= midi_note <= 127:
            note_name = MidiNoteToKeyConverter.NOTE_NAMES[midi_note % 12]
            octave = midi_note // 12 - 1  # MIDI octave -1 is octave 0
            return f"{note_name}{octave}"
        return None

    @staticmethod
    def note_name_to_midi(note_name):
        """Convert a note name with octave to a MIDI note number"""
        if not note_name:
            return None

        # Extract note and octave
        if note_name[-1].isdigit():
            note = note_name[:-1]
            octave = int(note_name[-1])
        else:
            note = note_name
            octave = 4  # Default to octave 4

        # Find note index
        try:
            note_index = MidiNoteToKeyConverter.NOTE_NAMES.index(note)
        except ValueError:
            return None

        # Calculate MIDI note
        midi_note = (octave + 1) * 12 + note_index

        if 0 <= midi_note <= 127:
            return midi_note
        return None


# Example usage:
# midi_controller = MidiController()
# available_ports = midi_controller.get_available_ports()
# if available_ports:
#     midi_controller.connect_to_port(0)  # Connect to the first available port
#
# # Map MIDI note 60 (Middle C) to play a sample in a sample pad
# def play_sample(velocity):
#     sample_pad.play_sample(0)
# midi_controller.map_note_to_action(0, 60, play_sample)
#
# # Map MIDI controller 7 (Volume) to control the master volume
# def set_volume(value):
#     mixer.set_master_volume(value)
# midi_controller.map_controller_to_parameter(0, 7, set_volume, 0, 1)

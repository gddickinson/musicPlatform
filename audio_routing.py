"""
Audio Routing System for the Music Production Platform
Allows connecting different audio components to create complex signal chains
"""

import numpy as np
import threading
import queue
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QTimer, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                           QPushButton, QLabel, QSlider, QGroupBox, QGridLayout)
from PyQt5.QtGui import QColor
import pyqtgraph as pg

class AudioNode:
    """Base class for all audio nodes in the routing system"""
    def __init__(self, name, num_inputs=1, num_outputs=1):
        self.name = name
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.input_nodes = [None] * num_inputs
        self.output_nodes = []
        self.enabled = True
        self.muted = False
        self.gain = 1.0
        self.buffer = np.zeros(1024)  # Default buffer size
        self.mutex = QMutex()

    def process(self, buffer_size=1024):
        """Process audio and return output buffer"""
        if not self.enabled or self.muted:
            return np.zeros(buffer_size)

        # Get input audio
        input_buffer = self.get_input_audio(buffer_size)

        # Process audio
        output_buffer = self.process_audio(input_buffer)

        # Apply gain
        output_buffer *= self.gain

        # Store buffer
        with QMutex().locker():
            self.buffer = output_buffer.copy()

        return output_buffer

    def get_input_audio(self, buffer_size):
        """Get audio from input nodes or generate if no inputs"""
        if self.num_inputs == 0:
            # Generate audio if this is a source node
            return self.generate_audio(buffer_size)

        # Mix audio from all input nodes
        input_buffer = np.zeros(buffer_size)

        for i, node in enumerate(self.input_nodes):
            if node:
                node_buffer = node.process(buffer_size)
                input_buffer += node_buffer

        return input_buffer

    def generate_audio(self, buffer_size):
        """Generate audio for source nodes"""
        return np.zeros(buffer_size)

    def process_audio(self, input_buffer):
        """Process audio (to be overridden by subclasses)"""
        return input_buffer

    def connect_output(self, dest_node, input_index=0):
        """Connect this node's output to another node's input"""
        if dest_node and input_index < dest_node.num_inputs:
            # Disconnect any existing node at the input
            if dest_node.input_nodes[input_index]:
                dest_node.input_nodes[input_index].disconnect_from(dest_node)

            # Make the connection
            dest_node.input_nodes[input_index] = self
            if dest_node not in self.output_nodes:
                self.output_nodes.append(dest_node)

            return True
        return False

    def disconnect_from(self, dest_node):
        """Disconnect this node from a destination node"""
        if dest_node in self.output_nodes:
            self.output_nodes.remove(dest_node)

            # Remove this node from dest_node's inputs
            for i, node in enumerate(dest_node.input_nodes):
                if node == self:
                    dest_node.input_nodes[i] = None

            return True
        return False

    def disconnect_all(self):
        """Disconnect this node from all connections"""
        # Disconnect from all outputs
        for node in list(self.output_nodes):
            self.disconnect_from(node)

        # Disconnect all inputs
        for i, node in enumerate(self.input_nodes):
            if node:
                node.disconnect_from(self)
                self.input_nodes[i] = None


class ComponentNode(AudioNode):
    """Audio node that wraps a component (Piano, Drum Machine, etc.)"""
    def __init__(self, name, component, sample_rate=44100):
        super().__init__(name, num_inputs=0, num_outputs=1)  # Source node
        self.component = component
        self.sample_rate = sample_rate

    def generate_audio(self, buffer_size):
        """Get audio from the component"""
        if hasattr(self.component, 'get_audio'):
            return self.component.get_audio(buffer_size)
        elif hasattr(self.component, 'buffer'):
            # If component has a buffer property, use that
            with QMutex().locker():
                if hasattr(self.component.buffer, 'copy'):
                    return self.component.buffer.copy()[:buffer_size]
                return np.array(self.component.buffer[:buffer_size])
        return np.zeros(buffer_size)


class MixerNode(AudioNode):
    """Audio node that mixes multiple inputs into a single output"""
    def __init__(self, name, num_inputs=2):
        super().__init__(name, num_inputs=num_inputs, num_outputs=1)
        self.input_gains = [1.0] * num_inputs
        self.input_mutes = [False] * num_inputs

    def set_input_gain(self, input_index, gain):
        """Set the gain for a specific input"""
        if 0 <= input_index < self.num_inputs:
            self.input_gains[input_index] = gain

    def set_input_mute(self, input_index, muted):
        """Mute/unmute a specific input"""
        if 0 <= input_index < self.num_inputs:
            self.input_mutes[input_index] = muted

    def get_input_audio(self, buffer_size):
        """Get and mix audio from all input nodes with individual gains"""
        mixed_buffer = np.zeros(buffer_size)

        for i, node in enumerate(self.input_nodes):
            if node and not self.input_mutes[i]:
                node_buffer = node.process(buffer_size)
                mixed_buffer += node_buffer * self.input_gains[i]

        return mixed_buffer


class EffectNode(AudioNode):
    """Base class for audio effect nodes"""
    def __init__(self, name, effect_type):
        super().__init__(name, num_inputs=1, num_outputs=1)
        self.effect_type = effect_type
        self.parameters = {}  # Dictionary to hold effect parameters

    def set_parameter(self, param_name, value):
        """Set an effect parameter"""
        if param_name in self.parameters:
            self.parameters[param_name] = value

    def get_parameter(self, param_name):
        """Get an effect parameter"""
        return self.parameters.get(param_name, 0.0)


class DelayNode(EffectNode):
    """Delay effect node"""
    def __init__(self, name="Delay"):
        super().__init__(name, "delay")
        self.parameters = {
            "delay_time": 0.5,  # seconds
            "feedback": 0.5,    # amount of feedback (0-1)
            "mix": 0.5          # dry/wet mix (0-1)
        }
        self.delay_buffer = np.zeros(0)  # Will be resized as needed
        self.buffer_pos = 0
        self.sample_rate = 44100

    def process_audio(self, input_buffer):
        delay_time = self.parameters["delay_time"]
        feedback = self.parameters["feedback"]
        mix = self.parameters["mix"]

        # Make sure delay buffer is large enough
        delay_samples = int(delay_time * self.sample_rate)
        if len(self.delay_buffer) < delay_samples:
            # Resize buffer with zeros
            new_buffer = np.zeros(delay_samples)
            # Copy old data if any
            if len(self.delay_buffer) > 0:
                new_buffer[:len(self.delay_buffer)] = self.delay_buffer
            self.delay_buffer = new_buffer

        # Process each sample
        output_buffer = np.zeros_like(input_buffer)

        for i in range(len(input_buffer)):
            # Read from delay buffer
            delay_idx = (self.buffer_pos - delay_samples) % len(self.delay_buffer)
            delay_sample = self.delay_buffer[delay_idx]

            # Calculate output sample (mix dry and wet signals)
            output_buffer[i] = input_buffer[i] * (1 - mix) + delay_sample * mix

            # Write to delay buffer with feedback
            self.delay_buffer[self.buffer_pos] = input_buffer[i] + delay_sample * feedback

            # Move buffer position
            self.buffer_pos = (self.buffer_pos + 1) % len(self.delay_buffer)

        return output_buffer


class ReverbNode(EffectNode):
    """Simple reverb effect node"""
    def __init__(self, name="Reverb"):
        super().__init__(name, "reverb")
        self.parameters = {
            "room_size": 0.7,    # Size of the reverb space (0-1)
            "damping": 0.5,      # Damping factor (0-1)
            "mix": 0.3           # Dry/wet mix (0-1)
        }
        self.sample_rate = 44100
        self.reverb_buffer = np.zeros(int(self.sample_rate * 2))  # 2 seconds
        self.buffer_pos = 0

    def process_audio(self, input_buffer):
        room_size = self.parameters["room_size"]
        damping = self.parameters["damping"]
        mix = self.parameters["mix"]

        # Process each sample
        output_buffer = np.zeros_like(input_buffer)

        for i in range(len(input_buffer)):
            # Calculate reverb
            reverb_sample = 0

            # Use 8 delay taps for a simple but effective reverb
            for j in range(8):
                # Calculate delay time based on room size
                delay = int(self.sample_rate * 0.02 * (j + 1) * room_size) % len(self.reverb_buffer)

                # Get the delayed sample
                idx = (self.buffer_pos - delay) % len(self.reverb_buffer)

                # Add to reverb with progressive damping
                reverb_sample += self.reverb_buffer[idx] * (1 - damping) ** j

            # Mix dry and wet signals
            output_buffer[i] = input_buffer[i] * (1 - mix) + reverb_sample * mix

            # Update reverb buffer
            self.reverb_buffer[self.buffer_pos] = input_buffer[i]
            self.buffer_pos = (self.buffer_pos + 1) % len(self.reverb_buffer)

        return output_buffer


class RoutingMatrix:
    """Manages all audio nodes and their connections"""
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.nodes = {}  # Dictionary of all nodes
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.master_node = None

    def add_node(self, node):
        """Add a node to the routing matrix"""
        if node.name in self.nodes:
            # Make the name unique
            i = 1
            while f"{node.name}_{i}" in self.nodes:
                i += 1
            node.name = f"{node.name}_{i}"

        self.nodes[node.name] = node
        return node

    def remove_node(self, node_name):
        """Remove a node from the routing matrix"""
        if node_name in self.nodes:
            node = self.nodes[node_name]
            node.disconnect_all()
            del self.nodes[node_name]
            return True
        return False

    def connect_nodes(self, source_name, dest_name, input_index=0):
        """Connect two nodes"""
        if source_name in self.nodes and dest_name in self.nodes:
            source = self.nodes[source_name]
            dest = self.nodes[dest_name]
            return source.connect_output(dest, input_index)
        return False

    def disconnect_nodes(self, source_name, dest_name):
        """Disconnect two nodes"""
        if source_name in self.nodes and dest_name in self.nodes:
            source = self.nodes[source_name]
            dest = self.nodes[dest_name]
            return source.disconnect_from(dest)
        return False

    def set_master_node(self, node_name):
        """Set the master output node"""
        if node_name in self.nodes:
            self.master_node = self.nodes[node_name]
            return True
        return False

    def get_master_output(self):
        """Get the audio output from the master node"""
        if self.master_node:
            return self.master_node.process(self.buffer_size)
        return np.zeros(self.buffer_size)

    def create_component_node(self, name, component):
        """Create and add a node for a component"""
        node = ComponentNode(name, component, self.sample_rate)
        return self.add_node(node)

    def create_mixer_node(self, name, num_inputs=2):
        """Create and add a mixer node"""
        node = MixerNode(name, num_inputs)
        return self.add_node(node)

    def create_delay_node(self, name="Delay"):
        """Create and add a delay effect node"""
        node = DelayNode(name)
        node.sample_rate = self.sample_rate
        return self.add_node(node)

    def create_reverb_node(self, name="Reverb"):
        """Create and add a reverb effect node"""
        node = ReverbNode(name)
        node.sample_rate = self.sample_rate
        return self.add_node(node)


class RoutingMatrixWidget(QWidget):
    """Widget for visualizing and editing the routing matrix"""
    def __init__(self, routing_matrix, parent=None):
        super().__init__(parent)
        self.routing_matrix = routing_matrix
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Controls section
        controls_layout = QHBoxLayout()

        # Source node selector
        source_layout = QVBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        source_layout.addWidget(self.source_combo)
        controls_layout.addLayout(source_layout)

        # Destination node selector
        dest_layout = QVBoxLayout()
        dest_layout.addWidget(QLabel("Destination:"))
        self.dest_combo = QComboBox()
        dest_layout.addWidget(self.dest_combo)
        controls_layout.addLayout(dest_layout)

        # Input index selector
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel("Input:"))
        self.input_combo = QComboBox()
        input_layout.addWidget(self.input_combo)
        controls_layout.addLayout(input_layout)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_selected_nodes)
        controls_layout.addWidget(self.connect_btn)

        # Disconnect button
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_selected_nodes)
        controls_layout.addWidget(self.disconnect_btn)

        layout.addLayout(controls_layout)

        # Graph view
        self.graph_view = RoutingGraphView(self.routing_matrix)
        layout.addWidget(self.graph_view)

        # Node details section
        self.node_details = QGroupBox("Node Details")
        self.node_details_layout = QVBoxLayout(self.node_details)
        layout.addWidget(self.node_details)

        # Update UI
        self.update_ui()

        # Connect signals
        self.source_combo.currentTextChanged.connect(self.source_changed)
        self.dest_combo.currentTextChanged.connect(self.dest_changed)
        self.dest_combo.currentTextChanged.connect(self.update_input_combo)

        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_ui)
        self.refresh_timer.start(1000)  # Update every second

    def update_ui(self):
        """Update the UI with current routing matrix state"""
        # Update node lists
        current_source = self.source_combo.currentText()
        current_dest = self.dest_combo.currentText()

        self.source_combo.clear()
        self.dest_combo.clear()

        for name in sorted(self.routing_matrix.nodes.keys()):
            self.source_combo.addItem(name)
            self.dest_combo.addItem(name)

        # Restore selections if possible
        index = self.source_combo.findText(current_source)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)

        index = self.dest_combo.findText(current_dest)
        if index >= 0:
            self.dest_combo.setCurrentIndex(index)

        # Update input selector
        self.update_input_combo()

        # Update graph view
        self.graph_view.update_graph()

    def update_input_combo(self):
        """Update the input index combo box"""
        self.input_combo.clear()

        dest_name = self.dest_combo.currentText()
        if dest_name in self.routing_matrix.nodes:
            dest_node = self.routing_matrix.nodes[dest_name]
            for i in range(dest_node.num_inputs):
                input_name = f"Input {i+1}"
                if dest_node.input_nodes[i]:
                    input_name += f" ({dest_node.input_nodes[i].name})"
                self.input_combo.addItem(input_name, i)

    def source_changed(self):
        """Handle source node selection change"""
        self.update_node_details(self.source_combo.currentText())

    def dest_changed(self):
        """Handle destination node selection change"""
        self.update_node_details(self.dest_combo.currentText())

    def update_node_details(self, node_name):
        """Update the node details section"""
        # Clear current details
        for i in reversed(range(self.node_details_layout.count())):
            item = self.node_details_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        if not node_name or node_name not in self.routing_matrix.nodes:
            return

        node = self.routing_matrix.nodes[node_name]

        # Add node type label
        type_label = QLabel(f"Type: {node.__class__.__name__}")
        self.node_details_layout.addWidget(type_label)

        # Add gain slider
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        gain_slider = QSlider(Qt.Horizontal)
        gain_slider.setRange(0, 100)
        gain_slider.setValue(int(node.gain * 100))
        gain_slider.valueChanged.connect(lambda v, n=node: setattr(n, 'gain', v / 100))
        gain_layout.addWidget(gain_slider)
        self.node_details_layout.addLayout(gain_layout)

        # Add mute button
        mute_btn = QPushButton("Mute" if not node.muted else "Unmute")
        mute_btn.setCheckable(True)
        mute_btn.setChecked(node.muted)
        mute_btn.toggled.connect(lambda checked, n=node: setattr(n, 'muted', checked))
        self.node_details_layout.addWidget(mute_btn)

        # Add effect parameters if applicable
        if isinstance(node, EffectNode):
            # Add parameter sliders
            params_group = QGroupBox("Effect Parameters")
            params_layout = QGridLayout(params_group)

            for i, (param_name, value) in enumerate(node.parameters.items()):
                # Create label with formatted name
                label = QLabel(param_name.replace('_', ' ').title())
                params_layout.addWidget(label, i, 0)

                # Create slider
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(int(value * 100))
                slider.valueChanged.connect(
                    lambda v, n=node, p=param_name: n.set_parameter(p, v / 100)
                )
                params_layout.addWidget(slider, i, 1)

                # Create value label
                value_label = QLabel(f"{value:.2f}")
                slider.valueChanged.connect(
                    lambda v, l=value_label: l.setText(f"{v/100:.2f}")
                )
                params_layout.addWidget(value_label, i, 2)

            self.node_details_layout.addWidget(params_group)

        # Add mixer input controls if applicable
        if isinstance(node, MixerNode):
            mixer_group = QGroupBox("Mixer Inputs")
            mixer_layout = QGridLayout(mixer_group)

            for i in range(node.num_inputs):
                # Add input label
                input_name = f"Input {i+1}"
                if node.input_nodes[i]:
                    input_name += f" ({node.input_nodes[i].name})"
                mixer_layout.addWidget(QLabel(input_name), i, 0)

                # Add gain slider
                gain_slider = QSlider(Qt.Horizontal)
                gain_slider.setRange(0, 100)
                gain_slider.setValue(int(node.input_gains[i] * 100))
                gain_slider.valueChanged.connect(
                    lambda v, n=node, idx=i: n.set_input_gain(idx, v / 100)
                )
                mixer_layout.addWidget(gain_slider, i, 1)

                # Add mute button
                mute_btn = QPushButton("M")
                mute_btn.setCheckable(True)
                mute_btn.setChecked(node.input_mutes[i])
                mute_btn.toggled.connect(
                    lambda checked, n=node, idx=i: n.set_input_mute(idx, checked)
                )
                mixer_layout.addWidget(mute_btn, i, 2)

            self.node_details_layout.addWidget(mixer_group)

    def connect_selected_nodes(self):
        """Connect the selected source and destination nodes"""
        source_name = self.source_combo.currentText()
        dest_name = self.dest_combo.currentText()
        input_index = self.input_combo.currentData()

        if source_name and dest_name and input_index is not None:
            success = self.routing_matrix.connect_nodes(source_name, dest_name, input_index)
            if success:
                self.update_ui()

    def disconnect_selected_nodes(self):
        """Disconnect the selected source and destination nodes"""
        source_name = self.source_combo.currentText()
        dest_name = self.dest_combo.currentText()

        if source_name and dest_name:
            success = self.routing_matrix.disconnect_nodes(source_name, dest_name)
            if success:
                self.update_ui()


class RoutingGraphView(pg.GraphicsLayoutWidget):
    """Widget for visualizing the routing matrix as a graph"""
    def __init__(self, routing_matrix, parent=None):
        super().__init__(parent)
        self.routing_matrix = routing_matrix
        self.node_items = {}  # Dictionary of node visualization items
        self.connection_items = []  # List of connection visualization items

        # Set up the plot
        self.plot = self.addPlot(title="Audio Routing")
        self.plot.showAxis('left', False)
        self.plot.showAxis('bottom', False)
        self.plot.setAspectLocked(True)

        # Initialize the graph
        self.update_graph()

    def update_graph(self):
        """Update the graph visualization"""
        # Clear the plot
        self.plot.clear()
        self.node_items = {}
        self.connection_items = []

        # Create node visualization
        nodes = list(self.routing_matrix.nodes.values())
        if not nodes:
            return

        # Arrange nodes in a circle
        n = len(nodes)
        radius = 1.0
        for i, node in enumerate(nodes):
            # Calculate position
            angle = 2 * np.pi * i / n
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)

            # Create node item
            item = pg.ScatterPlotItem()
            item.addPoints([x], [y], size=20, brush=pg.mkBrush('b'))

            # Add text label
            text = pg.TextItem(node.name, anchor=(0.5, 0.5))
            text.setPos(x, y + 0.15)

            # Add to plot
            self.plot.addItem(item)
            self.plot.addItem(text)

            # Store in dictionary
            self.node_items[node.name] = (item, text, (x, y))

        # Create connection visualization
        for source_name, source_node in self.routing_matrix.nodes.items():
            for dest_node in source_node.output_nodes:
                # Get positions
                if source_name in self.node_items and dest_node.name in self.node_items:
                    source_pos = self.node_items[source_name][2]
                    dest_pos = self.node_items[dest_node.name][2]

                    # Create connection line
                    line = pg.PlotCurveItem()
                    line.setData([source_pos[0], dest_pos[0]], [source_pos[1], dest_pos[1]],
                                pen=pg.mkPen('r', width=2))

                    # Add to plot
                    self.plot.addItem(line)
                    self.connection_items.append(line)


# Example usage:
# Create a routing matrix
# routing_matrix = RoutingMatrix()
#
# # Add nodes
# piano_node = routing_matrix.create_component_node("Piano", piano_keyboard)
# drum_node = routing_matrix.create_component_node("Drums", drum_machine)
#
# # Add effects
# reverb = routing_matrix.create_reverb_node("Reverb")
# delay = routing_matrix.create_delay_node("Delay")
#
# # Create a mixer
# mixer = routing_matrix.create_mixer_node("Main Mixer", 4)
#
# # Connect nodes
# piano_node.connect_output(reverb)
# reverb.connect_output(mixer, 0)
# drum_node.connect_output(delay)
# delay.connect_output(mixer, 1)
#
# # Set master node
# routing_matrix.set_master_node("Main Mixer")
#
# # Create the widget
# routing_widget = RoutingMatrixWidget(routing_matrix)
# routing_widget.show()

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
                             QSlider, QPushButton, QComboBox, QGridLayout, QSplitter, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
import numpy as np
import pyqtgraph as pg
import queue

class AudioBus:
    """
    Represents an audio routing bus for the mixer
    """
    def __init__(self, name, color=None):
        self.name = name
        self.color = color or QColor(255, 255, 255)
        self.volume = 1.0
        self.muted = False
        self.soloed = False
        self.source_tracks = []
        self.inputs = []
        self.outputs = []
        self.effects = []
        self.buffer = np.zeros(1024)
        
    def add_source(self, track):
        if track not in self.source_tracks:
            self.source_tracks.append(track)
            
    def remove_source(self, track):
        if track in self.source_tracks:
            self.source_tracks.remove(track)
            
    def apply_effects(self, audio):
        result = audio.copy()
        for effect in self.effects:
            result = effect.process(result)
        return result
        
    def process_audio(self, num_frames):
        """Mix all source tracks and apply effects"""
        if self.muted:
            return np.zeros(num_frames)
            
        output = np.zeros(num_frames)
        
        # Mix all source tracks
        for track in self.source_tracks:
            if not track.muted:
                output += track.generate_audio(num_frames)
                
        # Mix all input buses
        for input_bus in self.inputs:
            if not input_bus.muted:
                output += input_bus.process_audio(num_frames)
                
        # Apply effects
        output = self.apply_effects(output)
        
        # Apply volume
        output *= self.volume
        
        # Update internal buffer
        self.buffer = output
        
        return output

class MixerChannel(QGroupBox):
    """
    UI widget representing a single mixer channel
    """
    levelUpdated = pyqtSignal(float)
    
    def __init__(self, name, bus=None, parent=None):
        super().__init__(name, parent)
        self.bus = bus or AudioBus(name)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Volume fader
        self.fader = QSlider(Qt.Vertical)
        self.fader.setRange(0, 100)
        self.fader.setValue(int(self.bus.volume * 100))
        self.fader.valueChanged.connect(self.update_volume)
        
        # Level meter
        self.level_meter = QProgressBar(self)
        self.level_meter.setOrientation(Qt.Vertical)
        self.level_meter.setRange(0, 100)
        self.level_meter.setValue(0)
        self.level_meter.setTextVisible(False)
        self.level_meter.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: 1px solid #555;
            }
            QProgressBar::chunk {
                background-color: #0f0;
            }
        """)
        
        # Mute/Solo buttons
        button_layout = QHBoxLayout()
        self.mute_button = QPushButton("M")
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self.toggle_mute)
        
        self.solo_button = QPushButton("S")
        self.solo_button.setCheckable(True)
        self.solo_button.toggled.connect(self.toggle_solo)
        
        button_layout.addWidget(self.mute_button)
        button_layout.addWidget(self.solo_button)
        
        # Channel name
        self.name_label = QLabel(self.bus.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        
        # Add widgets to layout
        meter_fader_layout = QHBoxLayout()
        meter_fader_layout.addWidget(self.level_meter, 1)
        meter_fader_layout.addWidget(self.fader, 2)
        
        layout.addWidget(self.name_label)
        layout.addLayout(meter_fader_layout)
        layout.addLayout(button_layout)
        
        # Routing section
        routing_box = QGroupBox("Routing")
        routing_layout = QVBoxLayout(routing_box)
        
        self.output_combo = QComboBox()
        self.output_combo.addItem("Main Output")
        routing_layout.addWidget(QLabel("Output"))
        routing_layout.addWidget(self.output_combo)
        
        layout.addWidget(routing_box)
        
        # Timer for updating level meter
        self.level_timer = QTimer()
        self.level_timer.timeout.connect(self.update_level_meter)
        self.level_timer.start(50)  # Update every 50ms
        
    def update_volume(self, value):
        self.bus.volume = value / 100
        
    def toggle_mute(self, checked):
        self.bus.muted = checked
        
    def toggle_solo(self, checked):
        self.bus.soloed = checked
        
    def update_level_meter(self):
        if len(self.bus.buffer) > 0:
            level = np.max(np.abs(self.bus.buffer)) * 100
            self.level_meter.setValue(int(level))
            self.levelUpdated.emit(level)

class MixerWidget(QWidget):
    """
    Main mixer widget that contains all channels and buses
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels = []
        self.buses = []
        self.main_bus = AudioBus("Main Output")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Master volume section
        master_section = QGroupBox("Master")
        master_layout = QVBoxLayout(master_section)
        
        self.master_fader = QSlider(Qt.Vertical)
        self.master_fader.setRange(0, 100)
        self.master_fader.setValue(100)
        self.master_fader.valueChanged.connect(self.update_master_volume)
        
        master_layout.addWidget(self.master_fader)
        
        # Channel area - horizontal scrollable area
        channel_widget = QWidget()
        self.channel_layout = QHBoxLayout(channel_widget)
        
        # Add master channel
        self.master_channel = MixerChannel("Master", self.main_bus)
        self.channel_layout.addWidget(self.master_channel)
        
        # Add some spacing between master and other channels
        spacer = QFrame()
        spacer.setFrameShape(QFrame.VLine)
        spacer.setFrameShadow(QFrame.Sunken)
        self.channel_layout.addWidget(spacer)
        
        # Create a splitter to allow resizing
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(channel_widget)
        splitter.addWidget(master_section)
        splitter.setSizes([700, 100])  # Initial sizes
        
        layout.addWidget(splitter)
        
        # Start the update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_mixer)
        self.update_timer.start(50)  # Update every 50ms
        
    def update_master_volume(self, value):
        self.main_bus.volume = value / 100
        
    def add_channel(self, name, source=None, color=None):
        """Add a new channel to the mixer"""
        bus = AudioBus(name, color)
        channel = MixerChannel(name, bus)
        
        if source:
            bus.add_source(source)
            
        self.buses.append(bus)
        self.channels.append(channel)
        
        # Add to main bus by default
        self.main_bus.inputs.append(bus)
        
        # Add to UI
        self.channel_layout.insertWidget(self.channel_layout.count() - 2, channel)
        
        return channel
        
    def add_bus(self, name, color=None):
        """Add a new bus to the mixer"""
        bus = AudioBus(name, color)
        self.buses.append(bus)
        return bus
        
    def update_mixer(self):
        """Process audio for the main output bus"""
        self.main_bus.process_audio(1024)  # Process 1024 samples
        
    def get_output_audio(self, num_frames):
        """Get the final mixed audio output"""
        return self.main_bus.process_audio(num_frames)


class EffectsRack(QGroupBox):
    """
    Widget for housing and controlling multiple audio effects
    """
    def __init__(self, parent=None):
        super().__init__("Effects Rack", parent)
        self.effects = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Effects list
        self.effects_layout = QVBoxLayout()
        layout.addLayout(self.effects_layout)
        
        # Add effect button
        self.add_effect_btn = QPushButton("Add Effect")
        self.add_effect_btn.clicked.connect(self.show_add_effect_dialog)
        layout.addWidget(self.add_effect_btn)
        
    def show_add_effect_dialog(self):
        # In a real implementation, this would show a dialog to select an effect
        # For now, we'll just add a placeholder effect
        effect_widget = EffectControlWidget("Reverb")
        self.effects_layout.addWidget(effect_widget)
        self.effects.append(effect_widget)
        
class EffectControlWidget(QGroupBox):
    """
    Widget for controlling a single audio effect
    """
    def __init__(self, effect_name, parent=None):
        super().__init__(effect_name, parent)
        self.effect_name = effect_name
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)
        
        # Effect parameters - will vary based on effect type
        if self.effect_name == "Reverb":
            # Room size control
            layout.addWidget(QLabel("Room Size"), 0, 0)
            room_size_slider = QSlider(Qt.Horizontal)
            room_size_slider.setRange(0, 100)
            room_size_slider.setValue(50)
            layout.addWidget(room_size_slider, 0, 1)
            
            # Damping control
            layout.addWidget(QLabel("Damping"), 1, 0)
            damping_slider = QSlider(Qt.Horizontal)
            damping_slider.setRange(0, 100)
            damping_slider.setValue(50)
            layout.addWidget(damping_slider, 1, 1)
            
            # Wet/dry mix
            layout.addWidget(QLabel("Mix"), 2, 0)
            mix_slider = QSlider(Qt.Horizontal)
            mix_slider.setRange(0, 100)
            mix_slider.setValue(50)
            layout.addWidget(mix_slider, 2, 1)
            
        elif self.effect_name == "Delay":
            # Delay time
            layout.addWidget(QLabel("Time"), 0, 0)
            time_slider = QSlider(Qt.Horizontal)
            time_slider.setRange(0, 2000)  # 0-2000ms
            time_slider.setValue(500)
            layout.addWidget(time_slider, 0, 1)
            
            # Feedback
            layout.addWidget(QLabel("Feedback"), 1, 0)
            feedback_slider = QSlider(Qt.Horizontal)
            feedback_slider.setRange(0, 100)
            feedback_slider.setValue(50)
            layout.addWidget(feedback_slider, 1, 1)
            
            # Wet/dry mix
            layout.addWidget(QLabel("Mix"), 2, 0)
            mix_slider = QSlider(Qt.Horizontal)
            mix_slider.setRange(0, 100)
            mix_slider.setValue(50)
            layout.addWidget(mix_slider, 2, 1)
            
        # Bypass button
        self.bypass_btn = QPushButton("Bypass")
        self.bypass_btn.setCheckable(True)
        layout.addWidget(self.bypass_btn, layout.rowCount(), 0, 1, 2)
        
        # Remove button
        self.remove_btn = QPushButton("Remove")
        layout.addWidget(self.remove_btn, layout.rowCount(), 0, 1, 2)


# This class needs to be added to make the code run
class QProgressBar(QWidget):
    """
    Custom progress bar widget for audio level metering
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setMinimumWidth(10)
        self.setMinimumHeight(100)
        self._orientation = Qt.Vertical
        self._range = (0, 100)
        self._text_visible = True
        
    def setValue(self, value):
        self.value = max(self._range[0], min(self._range[1], value))
        self.update()
        
    def setRange(self, minimum, maximum=None):
        if maximum is None:
            minimum, maximum = 0, minimum
        self._range = (minimum, maximum)
        
    def setOrientation(self, orientation):
        self._orientation = orientation
        
    def setTextVisible(self, visible):
        self._text_visible = visible
        
    def paintEvent(self, event):
        import PyQt5.QtGui as QtGui
        painter = QtGui.QPainter(self)
        
        # Draw background
        painter.fillRect(self.rect(), QtGui.QColor("#333"))
        
        # Draw level indicator
        if self._orientation == Qt.Vertical:
            height = int(self.height() * (self.value - self._range[0]) / (self._range[1] - self._range[0]))
            painter.fillRect(0, self.height() - height, self.width(), height, QtGui.QColor("#0f0"))
        else:
            width = int(self.width() * (self.value - self._range[0]) / (self._range[1] - self._range[0]))
            painter.fillRect(0, 0, width, self.height(), QtGui.QColor("#0f0"))
            
        # Draw border
        painter.setPen(QtGui.QColor("#555"))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)

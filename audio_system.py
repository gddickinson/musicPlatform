"""
Audio System Module for the Music Production Platform.

This module provides the core audio processing functionality, including audio blocks,
routing, and effects. It handles real-time audio generation, processing, and playback.
"""

import numpy as np
import pyaudio
import threading
import queue
import time
import traceback
from typing import Dict, List, Optional, Tuple, Union, Callable, Any, Type
from enum import Enum, auto
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QTimer, Qt

# Import the logger
from logger import get_logger

# Set up module logger
logger = get_logger(__name__)


class AudioProcessingError(Exception):
    """Base exception for audio processing errors in the system."""
    pass


class BufferSizeError(AudioProcessingError):
    """Exception raised when there's an issue with buffer sizes."""
    pass


class AudioDeviceError(AudioProcessingError):
    """Exception raised when there's an issue with audio devices."""
    pass


class AudioBlock:
    """
    Base class for all audio processing blocks in the system.

    An AudioBlock represents a node in the audio processing graph that can
    generate or process audio data. Blocks can be connected to create complex
    signal chains.

    Attributes:
        name: Identifier for the block
        inputs: List of input blocks
        outputs: List of output blocks
        muted: Flag indicating if the block is muted
        solo: Flag indicating if the block is soloed
        volume: Volume multiplier for the block output
        bypass: Flag indicating if processing should be bypassed
        buffer: Internal buffer for audio data
        sample_rate: Sample rate in Hz
    """

    def __init__(self, name: str = "AudioBlock"):
        """
        Initialize an audio block.

        Args:
            name: A unique identifier for this audio block
        """
        self.name = name
        self.inputs: List[AudioBlock] = []
        self.outputs: List[AudioBlock] = []
        self.muted: bool = False
        self.solo: bool = False
        self.volume: float = 1.0
        self.bypass: bool = False
        self.buffer: np.ndarray = np.zeros(1024)
        self.sample_rate: int = 44100
        self.mutex = QMutex()

        logger.debug(f"Created AudioBlock: {name}")

    def process(self, buffer_size: int = 1024) -> np.ndarray:
        """
        Process audio and return the result.

        This method gets input from connected blocks, processes it,
        and returns the processed audio data.

        Args:
            buffer_size: Number of samples to process

        Returns:
            Processed audio data as a numpy array

        Raises:
            BufferSizeError: If the buffer size is invalid
        """
        try:
            if buffer_size <= 0:
                raise BufferSizeError(f"Invalid buffer size: {buffer_size}")

            if self.muted:
                return np.zeros(buffer_size)

            # Process inputs
            if self.inputs:
                # Mix all inputs
                mixed = np.zeros(buffer_size)
                for input_block in self.inputs:
                    mixed += input_block.process(buffer_size)
            else:
                # Generate own audio if no inputs
                mixed = self.generate(buffer_size)

            # Apply processing
            if not self.bypass:
                processed = self.process_audio(mixed)
            else:
                processed = mixed

            # Apply volume
            output = processed * self.volume

            # Update internal buffer
            with QMutex().locker():
                self.buffer = output.copy()

            return output

        except Exception as e:
            logger.error(f"Error in {self.name}.process(): {str(e)}")
            logger.debug(traceback.format_exc())
            # Return silence on error
            return np.zeros(buffer_size)

    def generate(self, buffer_size: int) -> np.ndarray:
        """
        Generate audio - override in subclasses that generate sound.

        Args:
            buffer_size: Number of samples to generate

        Returns:
            Generated audio data as a numpy array
        """
        return np.zeros(buffer_size)

    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio - override in subclasses that process audio.

        Args:
            audio: Input audio data to process

        Returns:
            Processed audio data
        """
        return audio

    def connect_to(self, other_block: 'AudioBlock') -> bool:
        """
        Connect this block as input to another block.

        Args:
            other_block: The destination block to connect to

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            if other_block not in self.outputs:
                self.outputs.append(other_block)

            if self not in other_block.inputs:
                other_block.inputs.append(self)

            logger.debug(f"Connected {self.name} to {other_block.name}")
            return True
        except Exception as e:
            logger.error(f"Error connecting {self.name} to {other_block.name}: {str(e)}")
            return False

    def disconnect_from(self, other_block: 'AudioBlock') -> bool:
        """
        Disconnect this block from another block.

        Args:
            other_block: The block to disconnect from

        Returns:
            True if disconnection was successful, False otherwise
        """
        try:
            if other_block in self.outputs:
                self.outputs.remove(other_block)

            if self in other_block.inputs:
                other_block.inputs.remove(self)

            logger.debug(f"Disconnected {self.name} from {other_block.name}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting {self.name} from {other_block.name}: {str(e)}")
            return False

    def disconnect_all(self) -> None:
        """
        Disconnect from all inputs and outputs.
        """
        try:
            # Disconnect from outputs
            for output in list(self.outputs):
                self.disconnect_from(output)

            # Disconnect inputs
            for input_block in list(self.inputs):
                input_block.disconnect_from(self)

            logger.debug(f"Disconnected all connections for {self.name}")
        except Exception as e:
            logger.error(f"Error disconnecting all for {self.name}: {str(e)}")


class SynthBlock(AudioBlock):
    """
    Audio block for synthesizers.

    This block generates audio using oscillators and can handle
    polyphonic note playback.

    Attributes:
        oscillators: List of oscillator configurations
        current_notes: Dictionary mapping note names to frequencies
    """

    def __init__(self, name: str = "Synth"):
        """
        Initialize a synthesizer block.

        Args:
            name: A unique identifier for this synth block
        """
        super().__init__(name)
        self.oscillators: List[Dict[str, Union[str, float]]] = []
        self.current_notes: Dict[str, float] = {}

    def add_oscillator(self, waveform: str = "sine", detune: float = 0.0, volume: float = 1.0) -> None:
        """
        Add an oscillator to the synthesizer.

        Args:
            waveform: Type of waveform (sine, square, sawtooth, triangle)
            detune: Detune amount in cents
            volume: Volume of this oscillator
        """
        try:
            self.oscillators.append({
                "waveform": waveform,
                "detune": detune,
                "volume": volume,
                "phase": 0.0
            })
            logger.debug(f"Added {waveform} oscillator to {self.name} with detune {detune} and volume {volume}")
        except Exception as e:
            logger.error(f"Error adding oscillator to {self.name}: {str(e)}")

    def note_on(self, note_name: str, frequency: float) -> None:
        """
        Trigger a note on.

        Args:
            note_name: Name of the note (e.g., "C4")
            frequency: Frequency of the note in Hz
        """
        try:
            self.current_notes[note_name] = frequency
            logger.debug(f"{self.name}: Note on {note_name} at {frequency} Hz")
        except Exception as e:
            logger.error(f"Error in note_on {note_name}: {str(e)}")

    def note_off(self, note_name: str) -> None:
        """
        Trigger a note off.

        Args:
            note_name: Name of the note to release
        """
        try:
            if note_name in self.current_notes:
                del self.current_notes[note_name]
                logger.debug(f"{self.name}: Note off {note_name}")
        except Exception as e:
            logger.error(f"Error in note_off {note_name}: {str(e)}")

    def generate(self, buffer_size: int) -> np.ndarray:
        """
        Generate audio from oscillators.

        Args:
            buffer_size: Number of samples to generate

        Returns:
            Generated audio data as a numpy array
        """
        try:
            if not self.oscillators or not self.current_notes:
                return np.zeros(buffer_size)

            output = np.zeros(buffer_size)
            t = np.arange(buffer_size) / self.sample_rate

            for note, frequency in self.current_notes.items():
                for osc in self.oscillators:
                    # Apply detune
                    freq = frequency * (2 ** (osc["detune"] / 1200))  # Detune in cents

                    # Generate waveform
                    if osc["waveform"] == "sine":
                        wave = np.sin(2 * np.pi * freq * t + osc["phase"])
                    elif osc["waveform"] == "square":
                        wave = np.sign(np.sin(2 * np.pi * freq * t + osc["phase"]))
                    elif osc["waveform"] == "sawtooth":
                        wave = 2 * ((t * freq + osc["phase"]) % 1) - 1
                    elif osc["waveform"] == "triangle":
                        wave = 2 * np.abs(2 * ((t * freq + osc["phase"]) % 1) - 1) - 1
                    else:
                        wave = np.zeros(buffer_size)

                    # Apply volume and add to output
                    output += wave * osc["volume"]

                    # Update phase
                    osc["phase"] = (osc["phase"] + buffer_size * freq / self.sample_rate) % 1.0

            # Normalize
            if len(self.current_notes) > 0 and len(self.oscillators) > 0:
                output /= len(self.current_notes) * len(self.oscillators)

            return output

        except Exception as e:
            logger.error(f"Error generating audio in {self.name}: {str(e)}")
            logger.debug(traceback.format_exc())
            return np.zeros(buffer_size)


class AudioSystem(QObject):
    """
    Central audio system that manages audio routing, processing, and playback.

    Attributes:
        sample_rate: Sample rate in Hz
        buffer_size: Buffer size in samples
        blocks: Dictionary of audio blocks by name
        master_block: Master output block
    """

    audioProcessed = pyqtSignal(np.ndarray)  # Signal emitted when audio is processed

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        """
        Initialize the audio system.

        Args:
            sample_rate: Sample rate in Hz
            buffer_size: Buffer size in samples
        """
        super().__init__()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.blocks: Dict[str, AudioBlock] = {}
        self.master_block: Optional[AudioBlock] = None
        self.running = False
        self.audio_queue = queue.Queue(maxsize=10)  # Queue for audio blocks

        # PyAudio setup
        try:
            self.pyaudio = pyaudio.PyAudio()
            self.stream: Optional[pyaudio.Stream] = None
            logger.info("Audio system initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize audio system: {str(e)}")
            logger.debug(traceback.format_exc())
            raise AudioDeviceError(f"Could not initialize PyAudio: {str(e)}")

    def add_block(self, block: AudioBlock, name: Optional[str] = None) -> AudioBlock:
        """
        Add an audio block to the system.

        Args:
            block: The audio block to add
            name: Optional custom name for the block

        Returns:
            The added block

        Raises:
            ValueError: If a block with the same name already exists
        """
        try:
            if name is None:
                name = block.name

            # Make sure name is unique
            if name in self.blocks:
                i = 1
                while f"{name}_{i}" in self.blocks:
                    i += 1
                name = f"{name}_{i}"

            block.name = name
            block.sample_rate = self.sample_rate
            self.blocks[name] = block

            logger.info(f"Added block: {name}")
            return block

        except Exception as e:
            logger.error(f"Error adding block {name}: {str(e)}")
            logger.debug(traceback.format_exc())
            raise

    def remove_block(self, name: str) -> bool:
        """
        Remove an audio block from the system.

        Args:
            name: The name of the block to remove

        Returns:
            True if the block was removed, False otherwise
        """
        try:
            if name in self.blocks:
                block = self.blocks[name]
                block.disconnect_all()
                del self.blocks[name]
                logger.info(f"Removed block: {name}")
                return True
            logger.warning(f"Attempted to remove non-existent block: {name}")
            return False
        except Exception as e:
            logger.error(f"Error removing block {name}: {str(e)}")
            return False

    def connect_blocks(self, source_name: str, dest_name: str) -> bool:
        """
        Connect two audio blocks.

        Args:
            source_name: Name of the source block
            dest_name: Name of the destination block

        Returns:
            True if the connection was made, False otherwise
        """
        try:
            if source_name in self.blocks and dest_name in self.blocks:
                source = self.blocks[source_name]
                dest = self.blocks[dest_name]
                source.connect_to(dest)
                logger.info(f"Connected {source_name} to {dest_name}")
                return True
            logger.warning(f"Cannot connect blocks: {source_name} or {dest_name} not found")
            return False
        except Exception as e:
            logger.error(f"Error connecting {source_name} to {dest_name}: {str(e)}")
            return False

    def disconnect_blocks(self, source_name: str, dest_name: str) -> bool:
        """
        Disconnect two audio blocks.

        Args:
            source_name: Name of the source block
            dest_name: Name of the destination block

        Returns:
            True if the connection was removed, False otherwise
        """
        try:
            if source_name in self.blocks and dest_name in self.blocks:
                source = self.blocks[source_name]
                dest = self.blocks[dest_name]
                source.disconnect_from(dest)
                logger.info(f"Disconnected {source_name} from {dest_name}")
                return True
            logger.warning(f"Cannot disconnect blocks: {source_name} or {dest_name} not found")
            return False
        except Exception as e:
            logger.error(f"Error disconnecting {source_name} from {dest_name}: {str(e)}")
            return False

    def set_master_block(self, name: str) -> bool:
        """
        Set the master output block.

        Args:
            name: Name of the block to set as master

        Returns:
            True if successful, False otherwise
        """
        try:
            if name in self.blocks:
                self.master_block = self.blocks[name]
                logger.info(f"Set master block to: {name}")
                return True
            logger.warning(f"Cannot set master block: {name} not found")
            return False
        except Exception as e:
            logger.error(f"Error setting master block to {name}: {str(e)}")
            return False

    def create_default_setup(self) -> None:
        """
        Create a default audio system setup with basic components.
        """
        try:
            # Create master output block
            master = AudioBlock("Master")
            self.add_block(master)
            self.master_block = master

            # Create synth block
            synth = SynthBlock("Synth")
            synth.add_oscillator("sine")
            self.add_block(synth)
            synth.connect_to(master)

            # Create sampler block
            sampler = SamplerBlock("Sampler")
            self.add_block(sampler)
            sampler.connect_to(master)

            # Create effect blocks
            delay = DelayEffect("Delay")
            self.add_block(delay)

            reverb = ReverbEffect("Reverb")
            self.add_block(reverb)

            # Set up effects chain: synth -> delay -> reverb -> master
            synth.disconnect_all()
            synth.connect_to(delay)
            delay.connect_to(reverb)
            reverb.connect_to(master)

            # Also connect sampler directly to master
            sampler.connect_to(master)

            logger.info("Created default audio system setup")
        except Exception as e:
            logger.error(f"Error creating default setup: {str(e)}")
            logger.debug(traceback.format_exc())

    def start(self) -> bool:
        """
        Start audio processing and playback.

        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Attempted to start audio system that is already running")
            return False

        try:
            # Make sure we have a master block
            if not self.master_block:
                if not self.blocks:
                    self.create_default_setup()
                else:
                    # Use the first block as master
                    self.master_block = list(self.blocks.values())[0]
                    logger.info(f"Using {self.master_block.name} as master block")

            # Set up PyAudio callback
            def callback(in_data, frame_count, time_info, status):
                try:
                    # Process audio
                    if self.master_block:
                        output = self.master_block.process(frame_count)

                        # Make sure output is the right size
                        if len(output) < frame_count:
                            output = np.pad(output, (0, frame_count - len(output)))
                        elif len(output) > frame_count:
                            output = output[:frame_count]

                        # Convert to float32
                        output = output.astype(np.float32)

                        # Emit signal with processed audio
                        self.audioProcessed.emit(output)

                        return (output.tobytes(), pyaudio.paContinue)
                    else:
                        # Return silence if no master block
                        return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)
                except Exception as e:
                    logger.error(f"Error in audio callback: {str(e)}")
                    logger.debug(traceback.format_exc())
                    return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)

            # Start stream
            self.stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.buffer_size,
                stream_callback=callback
            )

            self.stream.start_stream()
            self.running = True
            logger.info("Audio system started")
            return True

        except Exception as e:
            logger.error(f"Error starting audio system: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    def stop(self) -> bool:
        """
        Stop audio processing and playback.

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Attempted to stop audio system that is not running")
            return False

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            self.running = False
            logger.info("Audio system stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping audio system: {str(e)}")
            return False

    def get_waveform(self) -> np.ndarray:
        """
        Get the current output waveform.

        Returns:
            The current buffer of audio data
        """
        try:
            if self.master_block:
                return self.master_block.buffer
            else:
                return np.zeros(self.buffer_size)
        except Exception as e:
            logger.error(f"Error getting waveform: {str(e)}")
            return np.zeros(self.buffer_size)

    def close(self) -> None:
        """
        Close the audio system and clean up resources.
        """
        try:
            self.stop()
            self.pyaudio.terminate()
            logger.info("Audio system closed")
        except Exception as e:
            logger.error(f"Error closing audio system: {str(e)}")


# Additional class implementations would follow here,
# including SamplerBlock, DelayEffect, ReverbEffect, etc.
# Each with proper type hints, error handling, and documentation

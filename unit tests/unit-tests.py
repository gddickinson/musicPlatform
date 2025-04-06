"""
Unit tests for the audio_system module.

This module contains comprehensive tests for the audio processing and
routing functionality of the Music Production Platform.
"""

import unittest
import numpy as np
from unittest.mock import MagicMock, patch

# Import the improved audio system module
import audio_system_improved as audio_system
from audio_system_improved import (
    AudioBlock, SynthBlock, AudioSystem,
    AudioProcessingError, BufferSizeError, AudioDeviceError
)


class TestAudioBlock(unittest.TestCase):
    """Test cases for the AudioBlock class."""

    def setUp(self):
        """Set up test fixtures."""
        self.block = AudioBlock("Test Block")

    def test_initialization(self):
        """Test AudioBlock initialization."""
        self.assertEqual(self.block.name, "Test Block")
        self.assertEqual(len(self.block.inputs), 0)
        self.assertEqual(len(self.block.outputs), 0)
        self.assertFalse(self.block.muted)
        self.assertFalse(self.block.solo)
        self.assertEqual(self.block.volume, 1.0)
        self.assertFalse(self.block.bypass)
        self.assertEqual(self.block.sample_rate, 44100)

    def test_process_silence_when_muted(self):
        """Test that a muted block outputs silence."""
        self.block.muted = True
        buffer_size = 1024
        output = self.block.process(buffer_size)

        self.assertEqual(len(output), buffer_size)
        self.assertTrue(np.all(output == 0))

    def test_process_with_volume(self):
        """Test that volume is applied correctly."""
        buffer_size = 1024
        self.block.process_audio = MagicMock(return_value=np.ones(buffer_size))
        self.block.volume = 0.5

        output = self.block.process(buffer_size)

        self.assertEqual(len(output), buffer_size)
        self.assertTrue(np.all(output == 0.5))

    def test_connect_to(self):
        """Test connecting blocks."""
        other_block = AudioBlock("Other Block")

        self.block.connect_to(other_block)

        self.assertIn(other_block, self.block.outputs)
        self.assertIn(self.block, other_block.inputs)

    def test_disconnect_from(self):
        """Test disconnecting blocks."""
        other_block = AudioBlock("Other Block")
        self.block.connect_to(other_block)

        self.block.disconnect_from(other_block)

        self.assertNotIn(other_block, self.block.outputs)
        self.assertNotIn(self.block, other_block.inputs)

    def test_disconnect_all(self):
        """Test disconnecting all connections."""
        blocks = [AudioBlock(f"Block {i}") for i in range(3)]

        # Connect the test block to all other blocks
        for block in blocks:
            self.block.connect_to(block)

        # Connect all other blocks as inputs to the test block
        for block in blocks:
            block.connect_to(self.block)

        self.block.disconnect_all()

        # Check that all connections were removed
        self.assertEqual(len(self.block.outputs), 0)
        self.assertEqual(len(self.block.inputs), 0)
        for block in blocks:
            self.assertNotIn(self.block, block.inputs)
            self.assertNotIn(block, self.block.outputs)

    def test_process_invalid_buffer_size(self):
        """Test handling of invalid buffer sizes."""
        with self.assertRaises(BufferSizeError):
            self.block.process(0)

    def test_bypass_processing(self):
        """Test that bypass mode skips processing."""
        buffer_size = 1024
        input_data = np.ones(buffer_size)

        # Mock the generate method to return the test input
        self.block.generate = MagicMock(return_value=input_data)

        # Mock the process_audio method
        self.block.process_audio = MagicMock(return_value=np.zeros(buffer_size))

        # Enable bypass
        self.block.bypass = True

        # Process should return the input data, not zeros
        output = self.block.process(buffer_size)
        self.assertTrue(np.array_equal(output, input_data))

        # The process_audio method should not have been called
        self.block.process_audio.assert_not_called()


class TestSynthBlock(unittest.TestCase):
    """Test cases for the SynthBlock class."""

    def setUp(self):
        """Set up test fixtures."""
        self.synth = SynthBlock("Test Synth")

    def test_initialization(self):
        """Test SynthBlock initialization."""
        self.assertEqual(self.synth.name, "Test Synth")
        self.assertEqual(len(self.synth.oscillators), 0)
        self.assertEqual(len(self.synth.current_notes), 0)

    def test_add_oscillator(self):
        """Test adding an oscillator."""
        self.synth.add_oscillator("sine", 10.0, 0.8)

        self.assertEqual(len(self.synth.oscillators), 1)
        osc = self.synth.oscillators[0]
        self.assertEqual(osc["waveform"], "sine")
        self.assertEqual(osc["detune"], 10.0)
        self.assertEqual(osc["volume"], 0.8)
        self.assertEqual(osc["phase"], 0.0)

    def test_note_on_off(self):
        """Test note on and note off functionality."""
        note_name = "A4"
        frequency = 440.0

        # Test note on
        self.synth.note_on(note_name, frequency)
        self.assertIn(note_name, self.synth.current_notes)
        self.assertEqual(self.synth.current_notes[note_name], frequency)

        # Test note off
        self.synth.note_off(note_name)
        self.assertNotIn(note_name, self.synth.current_notes)

    def test_generate_no_notes(self):
        """Test generating audio with no active notes."""
        buffer_size = 1024
        audio = self.synth.generate(buffer_size)

        self.assertEqual(len(audio), buffer_size)
        self.assertTrue(np.all(audio == 0))

    def test_generate_no_oscillators(self):
        """Test generating audio with no oscillators."""
        buffer_size = 1024
        self.synth.note_on("A4", 440.0)
        audio = self.synth.generate(buffer_size)

        self.assertEqual(len(audio), buffer_size)
        self.assertTrue(np.all(audio == 0))

    def test_generate_with_sine_oscillator(self):
        """Test generating audio with a sine oscillator."""
        # Add oscillator and note
        self.synth.add_oscillator("sine")
        self.synth.note_on("A4", 440.0)

        # Generate audio
        buffer_size = 1024
        audio = self.synth.generate(buffer_size)

        # Check output properties
        self.assertEqual(len(audio), buffer_size)
        self.assertFalse(np.all(audio == 0))  # Should not be silent
        self.assertTrue(np.all(np.abs(audio) <= 1.0))  # Should be normalized

    def test_generate_multiple_notes(self):
        """Test generating audio with multiple notes."""
        # Add oscillator and notes
        self.synth.add_oscillator("sine")
        self.synth.note_on("A4", 440.0)
        self.synth.note_on("E5", 659.25)

        # Generate audio
        buffer_size = 1024
        audio = self.synth.generate(buffer_size)

        # Check output
        self.assertEqual(len(audio), buffer_size)
        self.assertFalse(np.all(audio == 0))

    def test_generate_different_waveforms(self):
        """Test generating audio with different waveform types."""
        buffer_size = 1024
        self.synth.note_on("A4", 440.0)

        for waveform in ["sine", "square", "sawtooth", "triangle"]:
            # Clear oscillators and add the test waveform
            self.synth.oscillators = []
            self.synth.add_oscillator(waveform)

            # Generate audio
            audio = self.synth.generate(buffer_size)

            # Check output
            self.assertEqual(len(audio), buffer_size)
            self.assertFalse(np.all(audio == 0))


class TestAudioSystem(unittest.TestCase):
    """Test cases for the AudioSystem class."""

    @patch('pyaudio.PyAudio')
    def setUp(self, mock_pyaudio):
        """Set up test fixtures with mocked PyAudio."""
        self.mock_pyaudio = mock_pyaudio
        self.audio_system = AudioSystem()

    def test_initialization(self):
        """Test AudioSystem initialization."""
        self.assertEqual(self.audio_system.sample_rate, 44100)
        self.assertEqual(self.audio_system.buffer_size, 1024)
        self.assertEqual(len(self.audio_system.blocks), 0)
        self.assertIsNone(self.audio_system.master_block)
        self.assertFalse(self.audio_system.running)

    def test_add_block(self):
        """Test adding a block to the system."""
        block = AudioBlock("Test Block")
        result = self.audio_system.add_block(block)

        self.assertEqual(result, block)
        self.assertIn("Test Block", self.audio_system.blocks)
        self.assertEqual(self.audio_system.blocks["Test Block"], block)
        self.assertEqual(block.sample_rate, self.audio_system.sample_rate)

    def test_add_block_with_duplicate_name(self):
        """Test adding a block with a name that already exists."""
        block1 = AudioBlock("Test Block")
        block2 = AudioBlock("Test Block")

        self.audio_system.add_block(block1)
        result = self.audio_system.add_block(block2)

        self.assertEqual(result, block2)
        self.assertIn("Test Block", self.audio_system.blocks)
        self.assertIn("Test Block_1", self.audio_system.blocks)
        self.assertEqual(block2.name, "Test Block_1")

    def test_remove_block(self):
        """Test removing a block from the system."""
        block = AudioBlock("Test Block")
        self.audio_system.add_block(block)

        result = self.audio_system.remove_block("Test Block")

        self.assertTrue(result)
        self.assertNotIn("Test Block", self.audio_system.blocks)

    def test_remove_nonexistent_block(self):
        """Test removing a block that doesn't exist."""
        result = self.audio_system.remove_block("Nonexistent Block")
        self.assertFalse(result)

    def test_connect_blocks(self):
        """Test connecting two blocks."""
        source = AudioBlock("Source")
        dest = AudioBlock("Destination")
        self.audio_system.add_block(source)
        self.audio_system.add_block(dest)

        result = self.audio_system.connect_blocks("Source", "Destination")

        self.assertTrue(result)
        self.assertIn(dest, source.outputs)
        self.assertIn(source, dest.inputs)

    def test_disconnect_blocks(self):
        """Test disconnecting two blocks."""
        source = AudioBlock("Source")
        dest = AudioBlock("Destination")
        self.audio_system.add_block(source)
        self.audio_system.add_block(dest)
        source.connect_to(dest)

        result = self.audio_system.disconnect_blocks("Source", "Destination")

        self.assertTrue(result)
        self.assertNotIn(dest, source.outputs)
        self.assertNotIn(source, dest.inputs)

    def test_set_master_block(self):
        """Test setting the master block."""
        master = AudioBlock("Master")
        self.audio_system.add_block(master)

        result = self.audio_system.set_master_block("Master")

        self.assertTrue(result)
        self.assertEqual(self.audio_system.master_block, master)

    def test_create_default_setup(self):
        """Test creating a default audio system setup."""
        self.audio_system.create_default_setup()

        # Should have created Master, Synth, Sampler, Delay, and Reverb blocks
        self.assertEqual(len(self.audio_system.blocks), 5)
        self.assertIn("Master", self.audio_system.blocks)
        self.assertIn("Synth", self.audio_system.blocks)
        self.assertIn("Sampler", self.audio_system.blocks)
        self.assertIn("Delay", self.audio_system.blocks)
        self.assertIn("Reverb", self.audio_system.blocks)

        # Master block should be set
        self.assertEqual(self.audio_system.master_block, self.audio_system.blocks["Master"])

    @patch('pyaudio.PyAudio')
    def test_start_without_master(self, mock_pyaudio):
        """Test starting the audio system without a master block."""
        # Mock the open method to return a stream with start_stream method
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream

        # Add a block but don't set it as master
        block = AudioBlock("Test Block")
        self.audio_system.add_block(block)

        # Start the system
        result = self.audio_system.start()

        # Should have succeeded and set the block as master
        self.assertTrue(result)
        self.assertEqual(self.audio_system.master_block, block)
        self.assertTrue(self.audio_system.running)

        # Stream should have been started
        mock_stream.start_stream.assert_called_once()

    @patch('pyaudio.PyAudio')
    def test_stop(self, mock_pyaudio):
        """Test stopping the audio system."""
        # Mock the stream
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream

        # Start the system
        self.audio_system.create_default_setup()
        self.audio_system.start()

        # Stop the system
        result = self.audio_system.stop()

        # Should have succeeded
        self.assertTrue(result)
        self.assertFalse(self.audio_system.running)

        # Stream should have been stopped and closed
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()

    def test_get_waveform_without_master(self):
        """Test getting waveform without a master block."""
        # Should return zeros
        waveform = self.audio_system.get_waveform()
        self.assertEqual(len(waveform), self.audio_system.buffer_size)
        self.assertTrue(np.all(waveform == 0))

    def test_get_waveform_with_master(self):
        """Test getting waveform with a master block."""
        # Create a master block with a non-zero buffer
        master = AudioBlock("Master")
        test_buffer = np.ones(self.audio_system.buffer_size)
        master.buffer = test_buffer

        # Add block and set as master
        self.audio_system.add_block(master)
        self.audio_system.set_master_block("Master")

        # Get waveform
        waveform = self.audio_system.get_waveform()

        # Should match the master's buffer
        self.assertTrue(np.array_equal(waveform, test_buffer))

    def test_close(self):
        """Test closing the audio system."""
        # Start and then close
        self.audio_system.create_default_setup()
        self.audio_system.start()
        self.audio_system.close()

        # Should have terminated PyAudio
        self.mock_pyaudio.return_value.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()

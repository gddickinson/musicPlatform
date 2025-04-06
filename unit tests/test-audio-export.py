"""
Unit tests for the audio_export module.

This module contains tests for the audio export functionality
of the Music Production Platform.
"""

import unittest
import numpy as np
import os
import tempfile
from unittest.mock import MagicMock, patch

# Import the improved audio export module
import audio_export_improved as audio_export
from audio_export_improved import (
    AudioExporter, ExportOptionsWidget, ExportDialog, MidiExporter,
    ExportError, ExportFormatError, ExportPathError, ExportProcessError,
    AudioFormat, ExportOptions
)


class TestAudioFormat(unittest.TestCase):
    """Test cases for the AudioFormat enum."""
    
    def test_from_string(self):
        """Test converting strings to AudioFormat."""
        self.assertEqual(AudioFormat.from_string("wav"), AudioFormat.WAV)
        self.assertEqual(AudioFormat.from_string("flac"), AudioFormat.FLAC)
        self.assertEqual(AudioFormat.from_string("ogg"), AudioFormat.OGG)
        self.assertEqual(AudioFormat.from_string("mp3"), AudioFormat.MP3)
        
        # Test case insensitivity
        self.assertEqual(AudioFormat.from_string("WAV"), AudioFormat.WAV)
        
        # Test invalid format
        with self.assertRaises(ExportFormatError):
            AudioFormat.from_string("invalid")
            
    def test_to_string(self):
        """Test converting AudioFormat to string."""
        self.assertEqual(AudioFormat.WAV.to_string(), "wav")
        self.assertEqual(AudioFormat.FLAC.to_string(), "flac")
        self.assertEqual(AudioFormat.OGG.to_string(), "ogg")
        self.assertEqual(AudioFormat.MP3.to_string(), "mp3")
            
    def test_get_sf_format(self):
        """Test getting soundfile format string."""
        self.assertEqual(AudioFormat.WAV.get_sf_format(), "WAV")
        self.assertEqual(AudioFormat.FLAC.get_sf_format(), "FLAC")
        self.assertEqual(AudioFormat.OGG.get_sf_format(), "OGG")
        self.assertEqual(AudioFormat.MP3.get_sf_format(), "MP3")


class TestExportOptions(unittest.TestCase):
    """Test cases for the ExportOptions dataclass."""
    
    def test_initialization(self):
        """Test initialization with default and custom values."""
        # Test with required parameters only
        options = ExportOptions(file_path="/tmp/test.wav", duration=60.0)
        self.assertEqual(options.file_path, "/tmp/test.wav")
        self.assertEqual(options.duration, 60.0)
        self.assertEqual(options.audio_format, AudioFormat.WAV)
        self.assertEqual(options.bit_depth, 16)
        self.assertEqual(options.sample_rate, 44100)
        self.assertEqual(options.channels, 2)
        self.assertTrue(options.normalize)
        
        # Test with all parameters
        options = ExportOptions(
            file_path="/tmp/test.flac",
            duration=30.0,
            audio_format=AudioFormat.FLAC,
            bit_depth=24,
            sample_rate=48000,
            channels=1,
            normalize=False
        )
        self.assertEqual(options.file_path, "/tmp/test.flac")
        self.assertEqual(options.duration, 30.0)
        self.assertEqual(options.audio_format, AudioFormat.FLAC)
        self.assertEqual(options.bit_depth, 24)
        self.assertEqual(options.sample_rate, 48000)
        self.assertEqual(options.channels, 1)
        self.assertFalse(options.normalize)


class TestAudioExporter(unittest.TestCase):
    """Test cases for the AudioExporter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.audio_system = MagicMock()
        self.routing_matrix = MagicMock()
        self.exporter = AudioExporter(
            audio_system=self.audio_system,
            routing_matrix=self.routing_matrix
        )
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
        
    def test_initialization(self):
        """Test AudioExporter initialization."""
        self.assertEqual(self.exporter.audio_system, self.audio_system)
        self.assertEqual(self.exporter.routing_matrix, self.routing_matrix)
        self.assertEqual(self.exporter.sample_rate, 44100)
        self.assertEqual(self.exporter.buffer_size, 1024)
        self.assertFalse(self.exporter.running)
        self.assertIsNone(self.exporter.export_thread)
        
    def test_export_audio_invalid_parameters(self):
        """Test export_audio with invalid parameters."""
        # Test with negative duration
        result = self.exporter.export_audio("/tmp/test.wav", -1.0)
        self.assertFalse(result)
        
        # Test with invalid format
        with patch('audio_export_improved.AudioFormat.from_string', 
                  side_effect=ExportFormatError("Invalid format")):
            result = self.exporter.export_audio("/tmp/test.wav", 60.0, "invalid")
            self.assertFalse(result)
            
    def test_export_audio_already_running(self):
        """Test export_audio when export is already running."""
        self.exporter.running = True
        result = self.exporter.export_audio("/tmp/test.wav", 60.0)
        self.assertFalse(result)
        
    @patch('threading.Thread')
    def test_export_audio_success(self, mock_thread):
        """Test successful audio export initialization."""
        # Create a test file path
        file_path = os.path.join(self.temp_dir.name, "test.wav")
        
        # Mock thread.start to do nothing
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Call export_audio
        result = self.exporter.export_audio(
            file_path=file_path,
            duration=60.0,
            audio_format="wav",
            bit_depth=16,
            sample_rate=44100,
            channels=2,
            normalize=True
        )
        
        # Check result
        self.assertTrue(result)
        self.assertTrue(self.exporter.running)
        self.assertEqual(self.exporter.export_thread, mock_thread_instance)
        
        # Check that thread was started
        mock_thread_instance.start.assert_called_once()
        
    def test_cancel_export_not_running(self):
        """Test cancel_export when no export is running."""
        self.exporter.running = False
        result = self.exporter.cancel_export()
        self.assertFalse(result)
        
    @patch('threading.Thread')
    def test_cancel_export_running(self, mock_thread):
        """Test cancel_export when export is running."""
        # Setup a mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        self.exporter.export_thread = mock_thread_instance
        self.exporter.running = True
        
        # Call cancel_export
        result = self.exporter.cancel_export()
        
        # Check result
        self.assertTrue(result)
        self.assertFalse(self.exporter.running)
        mock_thread_instance.join.assert_called_once()
        
    @patch('soundfile.write')
    @patch('numpy.zeros')
    def test_export_thread(self, mock_zeros, mock_sf_write):
        """Test the _export_thread method."""
        # Create mock audio data
        mock_audio = np.ones(1024)
        mock_zeros.return_value = mock_audio
        
        # Create mock for routing matrix
        self.routing_matrix.get_master_output.return_value = mock_audio
        
        # Set up export options
        options = ExportOptions(
            file_path=os.path.join(self.temp_dir.name, "test.wav"),
            duration=1.0,
            audio_format=AudioFormat.WAV,
            bit_depth=16,
            sample_rate=44100,
            channels=2,
            normalize=True
        )
        
        # Spy on signals
        started_spy = MagicMock()
        progress_spy = MagicMock()
        completed_spy = MagicMock()
        error_spy = MagicMock()
        
        self.exporter.exportStarted.connect(started_spy)
        self.exporter.exportProgress.connect(progress_spy)
        self.exporter.exportCompleted.connect(completed_spy)
        self.exporter.exportError.connect(error_spy)
        
        # Run export thread
        self.exporter._export_thread(options)
        
        # Check signals
        started_spy.assert_called_once()
        self.assertGreater(progress_spy.call_count, 0)
        completed_spy.assert_called_once_with(options.file_path)
        error_spy.assert_not_called()
        
        # Check that soundfile.write was called
        mock_sf_write.assert_called_once()
        

class TestMidiExporter(unittest.TestCase):
    """Test cases for the MidiExporter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.exporter = MidiExporter()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
        
    def test_initialization(self):
        """Test MidiExporter initialization."""
        self.assertIsInstance(self.exporter, MidiExporter)
        
    @patch('mido.MidiFile')
    def test_export_midi(self, mock_midi_file):
        """Test exporting MIDI data."""
        # Create mock MidiFile and track
        mock_midifile_instance = MagicMock()
        mock_midi_file.return_value = mock_midifile_instance
        mock_miditrack = MagicMock()
        mock_midi_file.MidiTrack.return_value = mock_miditrack
        
        # Create test tracks data
        tracks = [
            {
                "name": "Test Track",
                "notes": [
                    {
                        "note": 60,
                        "start_time": 0.0,
                        "end_time": 1.0,
                        "velocity": 100
                    }
                ],
                "control_changes": [
                    {
                        "control": 7,
                        "time": 0.5,
                        "value": 100
                    }
                ]
            }
        ]
        
        # Create a test file path
        file_path = os.path.join(self.temp_dir.name, "test.mid")
        
        # Spy on signals
        started_spy = MagicMock()
        completed_spy = MagicMock()
        error_spy = MagicMock()
        
        self.exporter.exportStarted.connect(started_spy)
        self.exporter.exportCompleted.connect(completed_spy)
        self.exporter.exportError.connect(error_spy)
        
        # Call export_midi
        with patch('mido.Message'):
            with patch('mido.MetaMessage'):
                result = self.exporter.export_midi(file_path, tracks)
        
        # Check result
        self.assertTrue(result)
        started_spy.assert_called_once()
        completed_spy.assert_called_once_with(file_path)
        error_spy.assert_not_called()
        
        # Check that MidiFile.save was called
        mock_midifile_instance.save.assert_called_once_with(file_path)
        

# Run tests if module is executed directly
if __name__ == '__main__':
    unittest.main()

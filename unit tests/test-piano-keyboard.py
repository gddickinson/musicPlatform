"""
Unit tests for the piano_keyboard module.

This module contains tests for the piano keyboard component
of the Music Production Platform.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

# Import the improved piano keyboard module
import piano_keyboard_improved as piano_keyboard
from piano_keyboard_improved import (
    PianoKey, PianoKeyboardWindow, PianoError, SoundGenerationError, PresetError
)


class TestPianoKey(unittest.TestCase):
    """Test cases for the PianoKey class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the QApplication once for all tests."""
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures."""
        self.white_key = PianoKey("C4", is_black=False)
        self.black_key = PianoKey("C#4", is_black=True)
    
    def test_initialization(self):
        """Test PianoKey initialization."""
        # Test white key
        self.assertEqual(self.white_key.note, "C4")
        self.assertFalse(self.white_key.is_black)
        self.assertEqual(self.white_key.default_color, "white")
        self.assertEqual(self.white_key.text(), "C4")
        
        # Test black key
        self.assertEqual(self.black_key.note, "C#4")
        self.assertTrue(self.black_key.is_black)
        self.assertEqual(self.black_key.default_color, "black")
        self.assertEqual(self.black_key.text(), "C#4")
        
        # Test sizes
        self.assertEqual(self.white_key.width(), 55)
        self.assertEqual(self.white_key.height(), 240)
        self.assertEqual(self.black_key.width(), 35)
        self.assertEqual(self.black_key.height(), 160)
    
    def test_get_style(self):
        """Test getting the key style."""
        # Test white key style
        white_style = self.white_key.get_style("white")
        self.assertIn("background-color: white", white_style)
        self.assertIn("color: black", white_style)
        
        # Test black key style
        black_style = self.black_key.get_style("black")
        self.assertIn("background-color: black", black_style)
        self.assertIn("color: white", black_style)
        
        # Test custom color
        custom_style = self.white_key.get_style("red")
        self.assertIn("background-color: red", custom_style)
    
    def test_set_color(self):
        """Test setting the key color."""
        # Test setting color on white key
        self.white_key.set_color("blue")
        style = self.white_key.styleSheet()
        self.assertIn("background-color: blue", style)
        
        # Test setting color on black key
        self.black_key.set_color("green")
        style = self.black_key.styleSheet()
        self.assertIn("background-color: green", style)
    
    def test_reset_color(self):
        """Test resetting the key color."""
        # Change color and then reset for white key
        self.white_key.set_color("blue")
        self.white_key.reset_color()
        style = self.white_key.styleSheet()
        self.assertIn("background-color: white", style)
        
        # Change color and then reset for black key
        self.black_key.set_color("green")
        self.black_key.reset_color()
        style = self.black_key.styleSheet()
        self.assertIn("background-color: black", style)


@patch('piano_keyboard_improved.Server')
@patch('piano_keyboard_improved.Sine')
@patch('piano_keyboard_improved.LFO')
@patch('piano_keyboard_improved.Adsr')
@patch('piano_keyboard_improved.Biquad')
@patch('piano_keyboard_improved.WGVerb')
@patch('piano_keyboard_improved.Delay')
@patch('piano_keyboard_improved.Chorus')
@patch('piano_keyboard_improved.Disto')
class TestPianoKeyboardWindow(unittest.TestCase):
    """Test cases for the PianoKeyboardWindow class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the QApplication once for all tests."""
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures."""
        # Setup will be done in each test due to the mock patches
        pass
    
    def test_initialization(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                           mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test PianoKeyboardWindow initialization."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Test window properties
        self.assertEqual(keyboard.windowTitle(), "Advanced Piano Keyboard Synthesizer")
        
        # Test server initialization
        mock_server.assert_called_once()
        mock_server_instance.boot.assert_called_once()
        mock_server_instance.start.assert_called_once()
        
        # Test initial state
        self.assertEqual(len(keyboard.active_notes), 0)
        self.assertFalse(keyboard.sustain_indefinite)
        self.assertEqual(keyboard.polyphony_limit, 8)
        self.assertEqual(keyboard.current_preset, "Default")
        self.assertEqual(keyboard.current_sound_source, "Waveform")
        self.assertEqual(keyboard.current_waveform, "Sine")
        self.assertIsNone(keyboard.current_sample)
        
        # Test piano keys
        self.assertGreater(len(keyboard.keys), 0)
        self.assertIn("C4", keyboard.keys)
        self.assertIn("C#4", keyboard.keys)
        
        # Clean up
        keyboard.close()
    
    def test_set_waveform(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                         mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test setting the waveform."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Test setting different waveforms
        waveforms = ["Sine", "Square", "Sawtooth", "Triangle", "PWM"]
        for waveform in waveforms:
            keyboard.set_waveform(waveform)
            self.assertEqual(keyboard.current_waveform, waveform)
            self.assertEqual(keyboard.current_sound_source, "Waveform")
        
        # Clean up
        keyboard.close()
    
    def test_note_to_freq(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                         mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test note to frequency conversion."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Test some known frequencies
        notes_and_freqs = [
            ("A4", 440.0),
            ("C4", 261.63),
            ("C5", 523.25),
            ("F#4", 369.99)
        ]
        
        for note, expected_freq in notes_and_freqs:
            actual_freq = keyboard.note_to_freq(note)
            self.assertAlmostEqual(actual_freq, expected_freq, delta=0.1)
        
        # Clean up
        keyboard.close()
    
    def test_play_and_release_note(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                                  mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test playing and releasing a note."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Set up test note
        test_note = "C4"
        
        # Set up mocks for synthesis chain
        mock_synth = MagicMock()
        mock_sine.return_value.mix.return_value = mock_synth
        
        mock_harmonics = MagicMock()
        mock_sine.return_value.mix.return_value = mock_harmonics
        
        mock_filter_instance = MagicMock()
        mock_biquad.return_value = mock_filter_instance
        
        mock_env_instance = MagicMock()
        mock_adsr.return_value = mock_env_instance
        
        mock_reverb_instance = MagicMock()
        mock_wgverb.return_value.mix.return_value = mock_reverb_instance
        
        mock_delay_instance = MagicMock()
        mock_delay.return_value.mix.return_value = mock_delay_instance
        
        mock_chorus_instance = MagicMock()
        mock_chorus.return_value.mix.return_value = mock_chorus_instance
        
        mock_distortion_instance = MagicMock()
        mock_disto.return_value.mix.return_value = mock_distortion_instance
        
        mock_lfo_instance = MagicMock()
        mock_sine.return_value = mock_lfo_instance
        
        # Play a note
        keyboard.play_note(test_note)
        
        # Check that the note was added to active notes
        self.assertIn(test_note, keyboard.active_notes)
        
        # Check that the envelope was started
        mock_env_instance.play.assert_called_once()
        
        # Release the note
        keyboard.release_note(test_note)
        
        # Check that the envelope was stopped
        mock_env_instance.stop.assert_called_once()
        
        # Clean up
        keyboard.close()
    
    def test_update_effects(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                           mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test updating effects parameters."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Set up test note and mocks
        test_note = "C4"
        
        mock_synth = MagicMock()
        mock_sine.return_value.mix.return_value = mock_synth
        
        mock_harmonics = MagicMock()
        mock_sine.return_value.mix.return_value = mock_harmonics
        
        mock_filter_instance = MagicMock()
        mock_biquad.return_value = mock_filter_instance
        
        mock_env_instance = MagicMock()
        mock_adsr.return_value = mock_env_instance
        
        mock_reverb_instance = MagicMock()
        mock_wgverb.return_value.mix.return_value = mock_reverb_instance
        
        mock_delay_instance = MagicMock()
        mock_delay.return_value.mix.return_value = mock_delay_instance
        
        mock_chorus_instance = MagicMock()
        mock_chorus.return_value.mix.return_value = mock_chorus_instance
        
        mock_distortion_instance = MagicMock()
        mock_disto.return_value.mix.return_value = mock_distortion_instance
        
        mock_lfo_instance = MagicMock()
        mock_sine.return_value = mock_lfo_instance
        
        # Play a note to set up active notes
        keyboard.play_note(test_note)
        
        # Setup active notes manually
        keyboard.active_notes[test_note] = {
            'synth': mock_synth,
            'harmonics': mock_harmonics,
            'filter': mock_filter_instance,
            'env': mock_env_instance,
            'reverb': mock_reverb_instance,
            'delay': mock_delay_instance,
            'chorus': mock_chorus_instance,
            'distortion': mock_distortion_instance,
            'lfo': mock_lfo_instance,
            'base_freq': 440.0,
            'start_time': 0
        }
        
        # Test updating volume
        keyboard.update_volume(50)
        mock_synth.mul = 0.5
        
        # Test updating reverb
        keyboard.update_reverb(50)
        mock_reverb_instance.bal = 0.5
        
        # Test updating delay
        keyboard.update_delay(50)
        mock_delay_instance.delay = 0.05
        mock_delay_instance.feedback = 0.25
        
        # Clean up
        keyboard.close()
    
    def test_keyboard_shortcuts(self, mock_disto, mock_chorus, mock_delay, mock_wgverb,
                               mock_biquad, mock_adsr, mock_lfo, mock_sine, mock_server):
        """Test keyboard shortcut handling."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create piano keyboard window
        keyboard = PianoKeyboardWindow()
        
        # Mock the note pressed and released signals
        keyboard.notePressed = MagicMock()
        keyboard.noteReleased = MagicMock()
        
        # Test key press event
        event = MagicMock()
        event.key.return_value = Qt.Key_A  # This should map to C4
        event.isAutoRepeat.return_value = False
        
        keyboard.keyPressEvent(event)
        keyboard.notePressed.emit.assert_called_with("C4")
        
        # Test key release event
        keyboard.keyReleaseEvent(event)
        keyboard.noteReleased.emit.assert_called_with("C4")
        
        # Clean up
        keyboard.close()


if __name__ == '__main__':
    unittest.main()

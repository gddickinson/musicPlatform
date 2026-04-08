"""
Basic smoke tests for the Music Production Platform.

These tests verify that key modules can be imported without errors,
and that basic non-GUI functionality works correctly.
"""

import unittest
import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports(unittest.TestCase):
    """Test that core modules can be imported."""

    def test_import_logger(self):
        """Logger module should import cleanly."""
        import logger
        log = logger.get_logger("test")
        self.assertIsNotNone(log)

    def test_import_audio_system(self):
        """Audio system module should import."""
        import audio_system
        self.assertTrue(hasattr(audio_system, 'AudioSystem'))

    def test_import_audio_routing(self):
        """Audio routing module should import."""
        import audio_routing
        self.assertTrue(hasattr(audio_routing, 'RoutingMatrix'))

    def test_import_mixer(self):
        """Mixer module should import."""
        import mixer

    def test_import_file_dialog_utils(self):
        """File dialog utilities should import."""
        import file_dialog_utils


class TestLogger(unittest.TestCase):
    """Test logger functionality."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a logging.Logger instance."""
        import logging
        from logger import get_logger

        log = get_logger("test_module")
        self.assertIsInstance(log, logging.Logger)

    def test_logger_has_name(self):
        """Logger should have the correct name."""
        from logger import get_logger

        log = get_logger("my_test")
        self.assertEqual(log.name, "my_test")


if __name__ == "__main__":
    unittest.main()

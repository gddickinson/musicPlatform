"""Piano keyboard checks that run without the pyo audio server (offscreen Qt)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PyQt5')


def test_play_note_runs_without_pyo():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import piano_keyboard
    w = piano_keyboard.PianoKeyboardWindow()
    w.play_note('A4')  # without pyo this used to stop at the undefined Biquad (NameError, logged)
    assert 'A4' in w.active_notes
    w.release_note('A4')
    w.close()
    del app

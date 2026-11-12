"""Regression tests for MIDI export (audio_export.MidiExporter, built by midi_export.build_midi)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
mido = pytest.importorskip('mido')
pytest.importorskip('PyQt5')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from audio_export import MidiExporter  # noqa: E402


def export(tmp_path, tracks):
    path = str(tmp_path / 'out.mid')
    errors = []
    ex = MidiExporter()
    ex.exportError.connect(errors.append)
    assert ex.export_midi(path, tracks), errors
    return mido.MidiFile(path)


def absolute(track):
    t, out = 0, []
    for m in track:
        t += m.time
        if not m.is_meta:
            out.append((t, m.type, getattr(m, 'note', getattr(m, 'control', None))))
    return out


def note(n, start, end, vel=100):
    return {'note': n, 'start_time': start, 'end_time': end, 'velocity': vel}


def test_simultaneous_notes_export(tmp_path):
    # two drum hits on the same step used to give a negative delta time and no file
    mid = export(tmp_path, [{'name': 'drums', 'notes': [note(36, 0, 0.125), note(38, 0, 0.125), note(36, 0.5, 0.625)]}])
    ev = absolute(mid.tracks[1])
    assert sorted(e for e in ev if e[1] == 'note_on') == [(0, 'note_on', 36), (0, 'note_on', 38), (480, 'note_on', 36)]
    assert sorted(e for e in ev if e[1] == 'note_off') == [(120, 'note_off', 36), (120, 'note_off', 38),
                                                           (600, 'note_off', 36)]


def test_control_changes_keep_their_time(tmp_path):
    # control changes were appended after all notes, so their times were counted from the last note-off
    mid = export(tmp_path, [{'name': 'x', 'notes': [note(60, 0, 1)], 'control_changes': [{'control': 7, 'time': 0.5, 'value': 10}]}])
    assert absolute(mid.tracks[1]) == [(0, 'note_on', 60), (480, 'control_change', 7), (960, 'note_off', 60)]


def test_track_channel(tmp_path):
    mid = export(tmp_path, [{'name': 'drums', 'channel': 9, 'notes': [note(36, 0, 0.1)]}])
    assert {m.channel for m in mid.tracks[1] if not m.is_meta} == {9}

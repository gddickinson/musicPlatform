"""Regression tests for the drum machine GUI and the drum / sound generator presets (offscreen Qt, dummy audio)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
pytest.importorskip('PyQt5')
pytest.importorskip('pygame')
pytest.importorskip('pyaudio')

from PyQt5.QtWidgets import QApplication, QDial  # noqa: E402

APP = QApplication.instance() or QApplication([])


@pytest.fixture
def drum(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the app is often started from another folder
    import drum_machine
    d = drum_machine.DrumMachineGUI()
    yield d
    d.close()


def test_samples_load_from_the_repo_whatever_the_working_folder(drum, tmp_path):
    assert sum(s is not None for s in drum.samples.values()) == 12
    assert not (tmp_path / 'samples').exists()


def test_one_volume_dial_per_row(drum):
    assert len(drum.findChildren(QDial)) == drum.rows


def test_drum_preset_round_trip(drum):
    from preset_manager import DrumPreset
    drum.buttons[(0, 0)].setChecked(True)
    drum.buttons[(1, 4)].setChecked(True)
    drum.bpm_slider.setValue(97)
    drum.volume_dials[2].setValue(40)
    p = DrumPreset.from_drum_machine(drum, 'x')
    assert p.data['bpm'] == 97 and p.data['volumes']['2'] == pytest.approx(0.4)
    drum.clear_grid()
    drum.bpm_slider.setValue(120)
    drum.volume_dials[2].setValue(100)
    p.apply_to_drum_machine(drum)
    on = sorted(k for k, b in drum.buttons.items() if b.isChecked())
    assert on == [(0, 0), (1, 4)] and drum.bpm_slider.value() == 97 and drum.volume_dials[2].value() == 40


def test_sound_generator_preset_round_trip():
    import sound_generator
    from preset_manager import SoundGeneratorPreset
    from synth_dsp import DistortionEffect, FMSynthTrack, WaveTrack
    g = sound_generator.EnhancedSoundGeneratorGUI()
    w = g.add_track('wave')
    w.set_frequency(330)
    w.set_wave_type('square')
    w.add_effect(DistortionEffect(0.3))
    f = g.add_track('fm')
    f.set_mod_index(5)
    p = SoundGeneratorPreset.from_sound_generator(g, 'y')
    p.apply_to_sound_generator(g)
    assert [type(t) for t in g.tracks] == [WaveTrack, FMSynthTrack]
    w2 = g.tracks[0]
    assert w2.frequency == 330 and w2.wave_type == 'square'
    assert w2.get_effect('DistortionEffect').amount == pytest.approx(0.3)
    assert g.tracks[1].mod_index == 5
    g.close()


def test_sound_generator_preset_with_a_held_note():
    # a held-note track was saved without a type; loading then gave its settings to the previous track (or crashed)
    import sound_generator
    from preset_manager import SoundGeneratorPreset
    from synth_dsp import ContinuousNoteTrack, WaveTrack
    g = sound_generator.EnhancedSoundGeneratorGUI()
    g.add_track('wave').set_amplitude(0.9)
    g.toggle_continuous_note_track('G')
    note = g.continuous_note_tracks['G']
    note.set_amplitude(0.2)
    note.set_note('G', 3)
    note.set_harmonics([1, 0.5])
    p = SoundGeneratorPreset.from_sound_generator(g, 'z')
    p.apply_to_sound_generator(g)
    assert [type(t) for t in g.tracks] == [WaveTrack, ContinuousNoteTrack]
    assert g.tracks[0].amplitude == 0.9
    n = g.tracks[1]
    assert (n.note, n.octave, n.harmonics, n.amplitude) == ('G', 3, [1, 0.5], 0.2)
    g.close()

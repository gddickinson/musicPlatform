"""Regression tests for the sound generator DSP (synth_dsp.py) and its GUI wiring (sound_generator.py).

Each test pins a bug found while porting the DSP to the browser: blocks must join without clicks, the GUI's
parameter changes must take effect, and drawing the scope must not consume audio.
"""
import os
import sys

import numpy as np
import pytest
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import synth_dsp as dsp  # noqa: E402

SR = 44100


def blocks(gen, n, size=1024):
    return np.concatenate([gen(size) for _ in range(n)])


def test_continuous_note_blocks_join_without_a_phase_reset():
    a = dsp.ContinuousNoteTrack('A', 4)
    a.set_harmonics([1.0, 0.5])
    joined = blocks(a.generate_audio, 2)
    t = np.arange(2048) / SR
    whole = 0.5 * (np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t))
    np.testing.assert_allclose(joined, whole, atol=1e-9)


def test_continuous_note_remembers_its_note_for_the_octave_control():
    tr = dsp.ContinuousNoteTrack('C', 4)
    assert tr.note == 'C'
    tr.set_note(tr.note, 5)  # what the GUI's octave combo does
    assert tr.frequency == pytest.approx(440 * 2 ** ((0 - 9) / 12 + 1))


def test_lowpass_cutoff_change_takes_effect():
    f = dsp.LowPassFilter()
    setattr(f, 'cutoff', 100.0)  # what TrackControls.update_effect_param does
    x = np.random.default_rng(1).normal(size=512)
    b, a = signal.butter(1, 100 / (SR / 2), btype='low')
    np.testing.assert_allclose(f(x), signal.lfilter(b, a, x), atol=1e-12)


@pytest.mark.parametrize('make', [dsp.LowPassFilter, dsp.EQEffect])
def test_filters_keep_state_across_blocks(make):
    x = np.random.default_rng(2).normal(size=2048)
    f1, f2 = make(), make()
    np.testing.assert_allclose(np.concatenate([f1(x[:1024]), f1(x[1024:])]), f2(x), atol=1e-12)


@pytest.mark.parametrize('kind,pole', [('pink', 0.9), ('brown', 0.98)])
def test_coloured_noise_keeps_filter_state_across_blocks(kind, pole):
    tr = dsp.NoiseTrack(SR)
    tr.set_noise_type(kind)
    np.random.seed(0)
    joined = blocks(tr.generate_audio, 2)
    np.random.seed(0)
    whole = signal.lfilter([1.0], [1, -pole], np.random.normal(0, 1, 2048)) * tr.amplitude
    np.testing.assert_allclose(joined, whole, atol=1e-12)


def test_distortion_amount_zero_is_clean_not_nan():
    x = np.linspace(-1, 1, 11)
    out = dsp.DistortionEffect(amount=0.0)(x)
    assert np.all(np.isfinite(out))
    np.testing.assert_allclose(out, x)


def test_eq_at_unity_gains_passes_the_signal():
    x = np.random.default_rng(3).normal(size=1024)
    np.testing.assert_allclose(dsp.EQEffect(1.0, 1.0)(x), x, atol=1e-12)


def test_eq_gain_scales_only_its_band():
    x = np.random.default_rng(4).normal(size=1024)
    eq = dsp.EQEffect(2.0, 1.0)
    low = signal.lfilter(eq.low_b, eq.low_a, x)
    np.testing.assert_allclose(eq(x), x + low, atol=1e-12)


def test_chorus_zero_delay_reads_the_current_sample():
    c = dsp.ChorusEffect(rate=1, depth=0.01, mix=0.5)
    c.phase = -np.pi / 2  # LFO at -1 on the first sample: delay 0
    out = c.process(np.ones(4))
    assert out[0] == pytest.approx(1.0)


def test_preview_does_not_advance_the_track():
    tr = dsp.WaveTrack(SR)
    tr.add_effect(dsp.TremoloEffect())
    first = tr.preview(256)
    assert tr.phase == 0 and tr.effects[0].phase == 0
    np.testing.assert_allclose(tr.generate_audio(256), first)


# --- GUI wiring (needs PyQt5 and PyAudio; skipped where they are missing) ---------------------------------------

@pytest.fixture(scope='module')
def gui():
    pytest.importorskip('PyQt5')
    pytest.importorskip('pyaudio')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import sound_generator
    g = sound_generator.EnhancedSoundGeneratorGUI()
    yield g
    g.close()
    del app


def test_scope_redraw_does_not_consume_audio(gui):
    gui.add_track('wave')
    tr = gui.tracks[-1]
    before = tr.phase
    gui.update_plot()
    gui.update_plot()
    assert tr.phase == before


def test_effect_switched_on_uses_the_slider_settings(gui):
    gui.add_track('wave')
    tr = gui.tracks[-1]
    tr.controls.toggle_effect(dsp.LowPassFilter, True)
    # the slider starts at 50 of 0-100 over the 20-20000 Hz range
    assert tr.get_effect('LowPassFilter').cutoff == pytest.approx(20 + (20000 - 20) * 0.5)

"""Regression tests for the sound generator's ReverbEffect (Freeverb-style; reverb_dsp.py).

The old formula summed the last second of samples with weights growing with age: a gain of ~17,000x and 44,100
multiplies per output sample, far too slow for the 1024-frame audio callback.
"""
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synth_dsp import ReverbEffect  # noqa: E402

SR = 44100
rng = np.random.default_rng(0)
SIGNALS = {
    "impulse": np.r_[1.0, np.zeros(SR - 1)],
    "noise": rng.normal(0, 0.3, SR),
    "sine": 0.8 * np.sin(2 * np.pi * 220 * np.arange(SR) / SR),
    "square": np.sign(np.sin(2 * np.pi * 110 * np.arange(SR) / SR)),
    "bursts": np.where((np.arange(SR) // 2205) % 4 == 0, 1.0, 0.0),
}


def run(effect, x, block=1024):
    return np.concatenate([effect(x[i:i + block]) for i in range(0, len(x), block)])


@pytest.mark.parametrize("name", SIGNALS)
@pytest.mark.parametrize("room,damp,mix", [(0.5, 0.5, 0.3), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0), (0.9, 0.2, 0.7)])
def test_output_peak_is_bounded(name, room, damp, mix):
    x = SIGNALS[name]
    y = run(ReverbEffect(room, damp, mix), x)
    assert np.all(np.isfinite(y))
    assert np.max(np.abs(y)) <= ReverbEffect.PEAK_FACTOR * np.max(np.abs(x)) + 1e-12


def test_wet_level_is_about_unity():
    x = SIGNALS["noise"]
    for room in (0.0, 0.5, 1.0):
        y = run(ReverbEffect(room, 0.5, 1.0), x)
        ratio = np.sqrt(np.mean(y[SR // 4:] ** 2)) / np.sqrt(np.mean(x ** 2))
        assert 0.3 < ratio < 2.0, (room, ratio)


def test_dry_signal_passes_unchanged_at_mix_zero():
    x = SIGNALS["sine"]
    np.testing.assert_allclose(run(ReverbEffect(0.5, 0.5, 0.0), x), x, atol=1e-12)


def test_tail_rings_after_an_impulse_longer_for_bigger_rooms():
    tails = []
    for room in (0.1, 0.9):
        y = run(ReverbEffect(room, 0.3, 1.0), SIGNALS["impulse"])
        tails.append(np.sqrt(np.mean(y[SR // 2:] ** 2)))
    assert tails[0] > 0 and tails[1] > 3 * tails[0]


def test_block_size_does_not_matter():
    x = SIGNALS["noise"]
    np.testing.assert_allclose(run(ReverbEffect(0.7, 0.4, 0.5), x, 1024), run(ReverbEffect(0.7, 0.4, 0.5), x, 300),
                               atol=1e-12)


def test_one_second_processes_well_under_real_time():
    x = SIGNALS["noise"]
    eff = ReverbEffect()
    t = time.perf_counter()
    run(eff, x)
    assert time.perf_counter() - t < 0.25

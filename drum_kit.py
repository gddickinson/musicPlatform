"""A synthesised 12-voice drum kit for the drum machine rows (used by the web app; no audio files needed).

The repo's own WAV files (samples/, wav/) carry no stated source or licence, so the web site does not publish them;
it plays this kit instead (and lets you load your own files). Every voice is built from simple, reproducible parts:
swept or fixed sine oscillators (phase by running sum), FM as in synth_dsp.FMSynthTrack, a seeded xorshift32 noise
source, one-pole filters, the brown-noise filter of synth_dsp.NoiseTrack and the TremoloEffect formula, then
exponential decay and peak normalisation to 0.9.

kit_voice(row) -> float array; build_kit() -> list of 12 arrays. The browser port is web/static/drum_kit.js, checked
against this module by tests/fixtures/drum_fixture.json.
"""
import numpy as np

SR = 44100
PEAK = 0.9


def xorshift_noise(seed, n):
    """Uniform noise in [-1, 1) from xorshift32 (13, 17, 5); seed must be non-zero."""
    x = seed & 0xFFFFFFFF
    out = np.empty(n)
    for i in range(n):
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        out[i] = x / 4294967296 * 2 - 1
    return out


def times(dur):
    return np.arange(int(dur * SR)) / SR


def decay(t, tau):
    return np.exp(-t / tau)


def sweep_sine(t, f_end, f_start, tau):
    """Sine whose frequency glides from f_start to f_end with time constant tau (phase = running sum)."""
    freq = f_end + (f_start - f_end) * np.exp(-t / tau)
    phase = np.cumsum(2 * np.pi * freq / SR)
    return np.sin(phase)


def one_pole_lowpass(x, a):
    """y[n] = (1 - a) * x[n] + a * y[n-1]."""
    y = np.empty(len(x))
    prev = 0.0
    b = 1 - a
    for i in range(len(x)):
        prev = b * x[i] + a * prev
        y[i] = prev
    return y


def highpass(x, a):
    return x - one_pole_lowpass(x, a)


def normalise(x):
    return x * (PEAK / np.max(np.abs(x)))


def _kick():
    t = times(0.5)
    body = sweep_sine(t, 48, 160, 0.04) * decay(t, 0.18)
    click = xorshift_noise(1, len(t)) * decay(t, 0.003) * 0.3
    return body + click


def _snare():
    t = times(0.35)
    tone = np.sin(2 * np.pi * 185 * t) * decay(t, 0.08) * 0.5
    rattle = highpass(xorshift_noise(2, len(t)), 0.6) * decay(t, 0.12) * 0.8
    return tone + rattle


def _hihat():
    t = times(0.12)
    return highpass(xorshift_noise(3, len(t)), 0.3) * decay(t, 0.025)


def _clap():
    t = times(0.3)
    noise = highpass(xorshift_noise(4, len(t)), 0.5)
    env = decay(t, 0.1) * 0.6
    for start in (0.0, 0.011, 0.022):
        burst = np.where(t >= start, decay(np.maximum(t - start, 0), 0.006), 0)
        env = env + burst
    return noise * env


def _tom(f_end, f_start, dur, tau_amp):
    t = times(dur)
    return sweep_sine(t, f_end, f_start, 0.08) * decay(t, tau_amp)


def _crash():
    t = times(1.5)
    return highpass(xorshift_noise(7, len(t)), 0.2) * decay(t, 0.6)


def _ride():
    t = times(1.2)
    hiss = highpass(xorshift_noise(8, len(t)), 0.2) * decay(t, 0.5) * 0.4
    bell = np.sin(2 * np.pi * 520 * t + 2 * np.sin(2 * np.pi * 1300 * t)) * decay(t, 0.6) * 0.5
    return hiss + bell


def _cowbell():
    t = times(0.3)
    sq = np.sign(np.sin(2 * np.pi * 540 * t)) + np.sign(np.sin(2 * np.pi * 800 * t))
    return one_pole_lowpass(sq, 0.7) * decay(t, 0.09)


def _rim():
    t = times(0.1)
    return np.sin(2 * np.pi * 900 * t) * decay(t, 0.02) + xorshift_noise(10, len(t)) * decay(t, 0.002) * 0.5


def _zap():
    t = times(0.4)
    return sweep_sine(t, 2000, 200, -0.25 / np.log(0.1)) * decay(t, 0.12)


def _rumble():
    t = times(0.6)
    brown = one_pole_lowpass(xorshift_noise(12, len(t)), 0.98)  # NoiseTrack's brown-noise pole
    tremolo = 1 - 0.8 * (0.5 + 0.5 * np.sin(2 * np.pi * 12 * t))  # TremoloEffect(rate=12, depth=0.8)
    return brown * tremolo * decay(t, 0.25)


VOICES = [_kick, _snare, _hihat, _clap, lambda: _tom(160, 220, 0.5, 0.25), lambda: _tom(110, 150, 0.6, 0.3),
          _crash, _ride, _cowbell, _rim, _zap, _rumble]


def kit_voice(row):
    return normalise(VOICES[row]())


def build_kit():
    return [kit_voice(r) for r in range(len(VOICES))]

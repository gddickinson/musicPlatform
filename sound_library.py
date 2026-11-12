"""Original synthesised sounds for the repo's samples/ and wav/ folders (replacing WAVs of unknown origin).

SOUNDS maps each file path (relative to the repo root, names kept so presets and the drum machine still find them) to a
function returning a mono float array at 44.1 kHz. samples/sample0..11.wav are exactly the drum_kit.py voices that the
web drum machine plays, so the desktop and the web sound the same. Everything is built from drum_kit's parts (seeded
xorshift noise, swept sines, one-pole filters, exponential decays): no recordings. Written by scripts/make_sounds.py
(16-bit mono WAV) and released under the repository's MIT licence (see THIRD_PARTY.md).
"""
import numpy as np

from drum_kit import (SR, decay, highpass, kit_voice, normalise, one_pole_lowpass, sweep_sine, times,
                      xorshift_noise)


def _kick(f_end, f_start, dur, tau, click, seed):
    t = times(dur)
    return sweep_sine(t, f_end, f_start, 0.04) * decay(t, tau) + xorshift_noise(seed, len(t)) * decay(t, 0.003) * click


def _snare(tone_hz, tau_tone, tau_noise, hp, level, dur, seed, flam=0.0):
    t = times(dur)
    hit = (np.sin(2 * np.pi * tone_hz * t) * decay(t, tau_tone) * 0.5
           + highpass(xorshift_noise(seed, len(t)), hp) * decay(t, tau_noise) * 0.8)
    if flam:  # a softer grace hit before the main one
        lag = int(flam * SR)
        hit = np.r_[hit * 0.45, np.zeros(lag)] + np.r_[np.zeros(lag), hit]
    return normalise(hit) * level


def _brush(tau, level, dur, seed, flam=0.0):
    """Brushes/rods: soft band-limited noise with a slow attack."""
    t = times(dur)
    noise = one_pole_lowpass(highpass(xorshift_noise(seed, len(t)), 0.4), 0.5)
    env = (1 - decay(t, 0.004)) * decay(t, tau)
    hit = noise * env
    if flam:
        lag = int(flam * SR)
        hit = np.r_[hit * 0.5, np.zeros(lag)] + np.r_[np.zeros(lag), hit]
    return normalise(hit) * level


def _cymbal(tau, hp, dur, seed, bell=0.0):
    t = times(dur)
    out = highpass(xorshift_noise(seed, len(t)), hp) * decay(t, tau)
    if bell:
        out = out + bell * np.sin(2 * np.pi * 587 * t + 2.5 * np.sin(2 * np.pi * 1411 * t)) * decay(t, tau * 0.7)
    return normalise(out)


def _tambourine():
    t = times(1.0)
    jingles = highpass(xorshift_noise(41, len(t)), 0.15) * decay(t, 0.18)
    shake = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)  # a short shake
    return normalise(jingles * shake)


def _kick_crash():
    a, b = _kick(45, 150, 2.5, 0.25, 0.3, 51), _cymbal(1.0, 0.2, 2.5, 52)
    return normalise(a + 0.6 * b)


def _foghorn():
    t = times(3.0)
    tone = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (87.0, 87.6, 130.5)) / 3  # slightly beating reeds
    swell = np.minimum(t / 0.4, 1) * np.minimum((3.0 - t) / 0.6, 1)
    return normalise(one_pole_lowpass(one_pole_lowpass(tone, 0.85), 0.85) * swell)


def _bass_loop(bpm=150, bars=4):
    """A 4-bar bass line (eighth notes) at 150 BPM: lowpassed square-ish tone with plucky decays."""
    eighth = 60 / bpm / 2
    notes = [40, 40, 52, 40, 43, 40, 47, 45] * 2 + [38, 38, 50, 38, 41, 38, 45, 43] * 2  # MIDI numbers
    n = int(round(eighth * len(notes) * SR * bars / 4))
    out = np.zeros(n)
    t = times(eighth)
    for k, m in enumerate(notes * (bars // 4)):
        f = 440 * 2 ** ((m - 69) / 12)
        tone = np.sign(np.sin(2 * np.pi * f * t)) * 0.6 + np.sin(2 * np.pi * f * t) * 0.4
        start = int(round(k * eighth * SR))
        seg = one_pole_lowpass(tone, 0.8) * decay(t, 0.12)
        out[start:start + len(seg)] += seg[:n - start]
    return normalise(out)


SOUNDS = {f"samples/sample{r}.wav": (lambda r=r: kit_voice(r)) for r in range(12)}
SOUNDS.update({
    "wav/Kick.wav": lambda: normalise(_kick(50, 170, 1.0, 0.2, 0.3, 21)),
    "wav/Kick_Sub.wav": lambda: normalise(_kick(38, 110, 1.5, 0.45, 0.1, 22)),
    "wav/Kick_Crash.wav": _kick_crash,
    "wav/Snare_1.wav": lambda: _snare(190, 0.08, 0.14, 0.6, 0.9, 0.8, 23),
    "wav/Snare_2.wav": lambda: _snare(175, 0.07, 0.11, 0.5, 0.9, 0.7, 24),
    "wav/Snare_Medium1.wav": lambda: _snare(200, 0.06, 0.09, 0.6, 0.7, 0.6, 25),
    "wav/Snare_Medium2.wav": lambda: _snare(210, 0.06, 0.08, 0.6, 0.7, 0.6, 26),
    "wav/Snare_Rods_1.wav": lambda: _brush(0.12, 0.8, 0.8, 27),
    "wav/Snare_Rods_2.wav": lambda: _brush(0.14, 0.8, 0.8, 28),
    "wav/Snare_Rods_Flam.wav": lambda: _brush(0.12, 0.8, 0.8, 29, flam=0.03),
    "wav/Snare_Rods_Lt_1.wav": lambda: _brush(0.07, 0.5, 0.6, 30),
    "wav/Snare_Rods_Lt_2.wav": lambda: _brush(0.08, 0.5, 0.6, 31),
    "wav/Snare_Rods_Med_1.wav": lambda: _brush(0.1, 0.65, 0.7, 32),
    "wav/Snare_Rods_Med_2.wav": lambda: _brush(0.1, 0.65, 0.7, 33),
    "wav/Hat_Closed_1.wav": lambda: _cymbal(0.03, 0.3, 0.3, 34),
    "wav/Hat_Closed_2.wav": lambda: _cymbal(0.04, 0.25, 0.3, 35),
    "wav/Hat_Open_1.wav": lambda: _cymbal(0.35, 0.3, 1.5, 36),
    "wav/Hat_Open_2.wav": lambda: _cymbal(0.45, 0.25, 1.5, 37),
    "wav/Crash_1.wav": lambda: _cymbal(0.9, 0.2, 3.0, 38, bell=0.15),
    "wav/Crash_2.wav": lambda: _cymbal(1.1, 0.18, 3.0, 39, bell=0.1),
    "wav/Tambourine.wav": _tambourine,
    "wav/foghornWAV 2.wav": _foghorn,
    "wav/Bass2 150bpm.wav": _bass_loop,
})

"""Freeverb-style reverb for the sound generator (ReverbEffect, re-exported by synth_dsp.py).

Design (Schroeder/Moorer, with Freeverb's tunings at 44.1 kHz):
- 8 parallel feedback comb filters (delays 1116..1617 samples) with a one-pole low-pass in each loop:
  feedback = 0.7 + 0.28 * room_size, loop damping = 0.4 * damping (Freeverb's scaling).
  Each comb is scaled by sqrt(1 - feedback^2) and the sum by 1/sqrt(8), so white noise keeps about its level.
- 4 Schroeder allpass filters in series (delays 556, 441, 341, 225; gain 0.5): unit gain at every frequency.
- out = (1 - mix) * dry + mix * wet, then a peak guard: values beyond the largest input peak so far (P) are softly
  compressed (tanh knee) so |out| < PEAK_FACTOR * P always. Below P the signal is untouched.

Vectorised: every filter delay is >= 225 samples, so audio is processed in chunks of at most 225 samples in which
each delay line is read from already-written history (numpy slices; the comb's damping is a first-order lfilter with
carried state). One second of audio takes a few milliseconds. The browser port is ReverbEffect in
web/static/synth_engine.js (sample by sample, same arithmetic), checked by tests/fixtures/synth_fixture.json.
"""
import numpy as np
from scipy import signal

COMB_DELAYS = (1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617)
ALLPASS_DELAYS = (556, 441, 341, 225)
ALLPASS_GAIN = 0.5
CHUNK = min(ALLPASS_DELAYS)


class ReverbEffect:
    PEAK_FACTOR = 2.0  # |output| < PEAK_FACTOR x the largest input peak so far

    def __init__(self, room_size=0.5, damping=0.5, mix=0.3):
        self.name = "Reverb"
        self.is_active = True
        self.room_size = float(room_size)
        self.damping = float(damping)
        self.mix = float(mix)
        self.combs = [np.zeros(d) for d in COMB_DELAYS]  # delay line contents, oldest first
        self.comb_zi = [np.zeros(1) for _ in COMB_DELAYS]
        self.allpasses = [np.zeros(d) for d in ALLPASS_DELAYS]
        self.peak = 0.0

    def __call__(self, audio):
        return self.process(audio) if self.is_active else audio

    def _wet_chunk(self, x):
        feedback = 0.7 + 0.28 * min(max(self.room_size, 0.0), 1.0)
        damp = 0.4 * min(max(self.damping, 0.0), 1.0)
        scale = np.sqrt(1 - feedback * feedback)
        n = len(x)
        total = np.zeros(n)
        for k in range(len(self.combs)):
            line = self.combs[k]
            out = line[:n]
            filt, self.comb_zi[k] = signal.lfilter([1 - damp], [1, -damp], out, zi=self.comb_zi[k])
            self.combs[k] = np.concatenate([line[n:], x + feedback * filt])
            total = total + out * scale
        y = total / np.sqrt(len(self.combs))
        for k in range(len(self.allpasses)):
            line = self.allpasses[k]
            delayed = line[:n]
            v = y + ALLPASS_GAIN * delayed
            self.allpasses[k] = np.concatenate([line[n:], v])
            y = delayed - ALLPASS_GAIN * v
        return y

    def process(self, audio):
        x = np.asarray(audio, dtype=float)
        wet = np.concatenate([self._wet_chunk(x[i:i + CHUNK]) for i in range(0, len(x), CHUNK)]) if len(x) else x
        y = (1 - self.mix) * x + self.mix * wet
        peaks = np.maximum.accumulate(np.r_[self.peak, np.abs(x)])[1:]
        self.peak = peaks[-1] if len(peaks) else self.peak
        knee = np.maximum(peaks, 1e-12)
        over = np.abs(y) > knee
        room = (self.PEAK_FACTOR - 1) * knee
        limited = np.sign(y) * (knee + room * np.tanh((np.abs(y) - knee) / room))
        return np.where(over, limited, y)

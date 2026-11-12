"""Qt-free sound generator DSP: the track generators and effects used by sound_generator.py.

Contents:
- Track, WaveTrack, NoiseTrack, FMSynthTrack, ContinuousNoteTrack: block generators (generate_audio(num_frames)).
- Effect, ReverbEffect, DistortionEffect, EQEffect, VibratoEffect, TremoloEffect, ChorusEffect, LowPassFilter.
- EFFECT_PARAMS: the effect classes with the parameter ranges the GUI sliders map 0-100 onto.

Only numpy and scipy are needed, so the web app (web/app.py) and the tests import this module without PyQt5/PyAudio.
The browser port is web/static/synth_engine.js (checked against this module by tests/fixtures/synth_fixture.json).
"""
import numpy as np
from scipy import signal

class Track:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.amplitude = 0.5
        self.color = None
        self.effects = []

    def set_amplitude(self, amplitude):
        self.amplitude = max(0, min(1, amplitude))  # Clamp between 0 and 1

    def add_effect(self, effect):
        self.effects.append(effect)

    def remove_effect(self, effect_name):
        self.effects = [ef for ef in self.effects if ef.__class__.__name__ != effect_name]

    def get_effect(self, effect_name):
        return next((ef for ef in self.effects if ef.__class__.__name__ == effect_name), None)

    def apply_effects(self, audio):
        for effect in self.effects:
            audio = effect(audio)
        return audio

    def generate_audio(self, num_frames):
        raise NotImplementedError("Subclasses must implement generate_audio method")

class WaveTrack(Track):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
        self.frequency = 440
        self.wave_type = 'sine'
        self.phase = 0

    def set_frequency(self, frequency):
        self.frequency = max(20, min(20000, frequency))  # Clamp between 20Hz and 20kHz

    def set_wave_type(self, wave_type):
        if wave_type in ['sine', 'square', 'sawtooth', 'triangle']:
            self.wave_type = wave_type

    def generate_audio(self, num_frames):
        t = (np.arange(num_frames) + self.phase) / self.sample_rate
        if self.wave_type == 'sine':
            audio = np.sin(2 * np.pi * self.frequency * t)
        elif self.wave_type == 'square':
            audio = signal.square(2 * np.pi * self.frequency * t)
        elif self.wave_type == 'sawtooth':
            audio = signal.sawtooth(2 * np.pi * self.frequency * t)
        elif self.wave_type == 'triangle':
            audio = signal.sawtooth(2 * np.pi * self.frequency * t, width=0.5)
        else:
            audio = np.zeros(num_frames)
        self.phase += num_frames
        audio = self.apply_effects(audio)
        return audio * self.amplitude

class NoiseTrack(Track):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
        self.noise_type = 'white'

    def set_noise_type(self, noise_type):
        if noise_type in ['white', 'pink', 'brown']:
            self.noise_type = noise_type

    def generate_audio(self, num_frames):
        if self.noise_type == 'white':
            audio = np.random.normal(0, 1, num_frames)
        elif self.noise_type == 'pink':
            audio = self.pink_noise(num_frames)
        elif self.noise_type == 'brown':
            audio = self.brown_noise(num_frames)
        else:
            audio = np.zeros(num_frames)
        audio = self.apply_effects(audio)
        return audio * self.amplitude

    def pink_noise(self, num_frames):
        white = np.random.normal(0, 1, num_frames)
        return signal.lfilter([1.0], [1, -0.9], white)

    def brown_noise(self, num_frames):
        white = np.random.normal(0, 1, num_frames)
        return signal.lfilter([1.0], [1, -0.98], white)

class FMSynthTrack(Track):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
        self.carrier_freq = 440
        self.mod_freq = 220
        self.mod_index = 2
        self.phase = 0

    def set_carrier_frequency(self, freq):
        self.carrier_freq = max(20, min(20000, freq))

    def set_mod_frequency(self, freq):
        self.mod_freq = max(1, min(5000, freq))

    def set_mod_index(self, index):
        self.mod_index = max(0, min(10, index))

    def generate_audio(self, num_frames):
        t = (np.arange(num_frames) + self.phase) / self.sample_rate
        modulation = np.sin(2 * np.pi * self.mod_freq * t)
        audio = np.sin(2 * np.pi * self.carrier_freq * t + self.mod_index * modulation)
        self.phase += num_frames
        audio = self.apply_effects(audio)
        return audio * self.amplitude

class ContinuousNoteTrack(Track):
    def __init__(self, note, octave, sample_rate=44100):
        super().__init__(sample_rate)
        self.set_note(note, octave)
        self.harmonics = [1.0]  # Fundamental frequency
        self.current_sample = 0

    def set_note(self, note, octave):
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.frequency = 440 * (2 ** ((notes.index(note) - 9) / 12 + (octave - 4)))

    def set_harmonics(self, harmonics):
        self.harmonics = harmonics

    def generate_audio(self, num_frames):
        t = np.arange(num_frames) / self.sample_rate
        audio = np.zeros(num_frames)
        for i, amplitude in enumerate(self.harmonics):
            audio += amplitude * np.sin(2 * np.pi * self.frequency * (i + 1) * t)
        audio = self.apply_effects(audio)
        return audio * self.amplitude


# Effect classes
class Effect:
    def __init__(self, name):
        self.name = name
        self.is_active = True

    def process(self, audio):
        raise NotImplementedError("Subclasses must implement process method")

    def __call__(self, audio):
        if self.is_active:
            return self.process(audio)
        return audio

class ReverbEffect(Effect):
    def __init__(self, room_size=0.5, damping=0.5):
        super().__init__("Reverb")
        self.room_size = float(room_size)
        self.damping = float(damping)
        self.buffer = np.zeros(44100)  # 1 second buffer at 44.1kHz

    def process(self, audio):
        output = np.zeros_like(audio)
        for i, sample in enumerate(audio):
            self.buffer = np.roll(self.buffer, -1)
            self.buffer[-1] = sample
            reverb = np.sum(self.buffer * self.room_size * np.exp(-np.arange(len(self.buffer)) * self.damping / 44100))
            output[i] = sample + reverb
        return output

class DistortionEffect(Effect):
    def __init__(self, amount=0.5):
        super().__init__("Distortion")
        self.amount = float(amount)

    def process(self, audio):
        return np.tanh(audio * self.amount) / np.tanh(self.amount)

class EQEffect(Effect):
    def __init__(self, low_gain=1.0, high_gain=1.0):
        super().__init__("EQ")
        self.low_gain = float(low_gain)
        self.high_gain = float(high_gain)
        self.update_filters()

    def update_filters(self):
        self.low_b, self.low_a = signal.butter(1, 500 / (44100 / 2), btype='lowpass')
        self.high_b, self.high_a = signal.butter(1, 2000 / (44100 / 2), btype='highpass')

    def process(self, audio):
        low = signal.lfilter(self.low_b, self.low_a, audio) * self.low_gain
        high = signal.lfilter(self.high_b, self.high_a, audio) * self.high_gain
        return low + high + audio * (1 - self.low_gain - self.high_gain)

class VibratoEffect(Effect):
    def __init__(self, rate=5, depth=0.005):
        super().__init__("Vibrato")
        self.rate = float(rate)
        self.depth = float(depth)
        self.phase = 0

    def process(self, audio):
        t = np.arange(len(audio)) / 44100
        vibrato = np.sin(2 * np.pi * self.rate * t + self.phase)
        self.phase += 2 * np.pi * self.rate * len(audio) / 44100
        self.phase %= 2 * np.pi
        return np.interp(t + self.depth * vibrato, t, audio)

class TremoloEffect(Effect):
    def __init__(self, rate=5, depth=0.5):
        super().__init__("Tremolo")
        self.rate = float(rate)
        self.depth = float(depth)
        self.phase = 0

    def process(self, audio):
        t = np.arange(len(audio)) / 44100
        tremolo = 1 - self.depth * (0.5 + 0.5 * np.sin(2 * np.pi * self.rate * t + self.phase))
        self.phase += 2 * np.pi * self.rate * len(audio) / 44100
        self.phase %= 2 * np.pi
        return audio * tremolo

class ChorusEffect(Effect):
    def __init__(self, rate=1, depth=0.01, mix=0.5):
        super().__init__("Chorus")
        self.rate = float(rate)
        self.depth = float(depth)
        self.mix = float(mix)
        self.buffer = np.zeros(int(44100 * 0.05))  # 50ms buffer
        self.phase = 0

    def process(self, audio):
        output = np.zeros_like(audio)
        for i, sample in enumerate(audio):
            self.buffer = np.roll(self.buffer, -1)
            self.buffer[-1] = sample

            lfo = np.sin(2 * np.pi * self.rate * i / 44100 + self.phase)
            delay = int(self.depth * 44100 * (1 + lfo))

            if delay < len(self.buffer):
                output[i] = self.mix * self.buffer[-delay] + (1 - self.mix) * sample
            else:
                output[i] = sample

        self.phase += 2 * np.pi * self.rate * len(audio) / 44100
        self.phase %= 2 * np.pi
        return output

class LowPassFilter(Effect):
    def __init__(self, cutoff=1000):
        super().__init__("LowPass")
        self.cutoff = float(cutoff)
        self.update_filter()

    def update_filter(self):
        self.b, self.a = signal.butter(1, self.cutoff / (44100 / 2), btype='low', analog=False)

    def process(self, audio):
        return signal.lfilter(self.b, self.a, audio)


# Effects offered per track by the sound generator GUI, with the parameter ranges its 0-100 sliders map onto.
EFFECT_PARAMS = [
    (ReverbEffect, {"room_size": (0, 1), "damping": (0, 1)}),
    (DistortionEffect, {"amount": (0, 1)}),
    (EQEffect, {"low_gain": (0, 2), "high_gain": (0, 2)}),
    (VibratoEffect, {"rate": (0, 20), "depth": (0, 1)}),
    (TremoloEffect, {"rate": (0, 20), "depth": (0, 1)}),
    (ChorusEffect, {"rate": (0, 5), "depth": (0, 1), "mix": (0, 1)}),
    (LowPassFilter, {"cutoff": (20, 20000)}),
]

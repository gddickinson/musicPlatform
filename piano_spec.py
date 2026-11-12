"""Qt-free settings of the piano keyboard (piano_keyboard.py imports them; the web app serves them).

- SLIDERS: (label, min, max, default) of every synthesis/effect slider, in GUI order.
- WAVEFORMS: menu waveform -> pyo LFO type used by play_note (None: pyo Sine).
- KEY_MAP: computer key -> note; OCTAVES / FIRST_OCTAVE: the on-screen keyboard (C4..B6); POLYPHONY.
- note_to_freq(note): equal temperament, A4 = 440 Hz.
"""
SLIDERS = [
    ("Volume", 0, 100, 80),
    ("Harmonics", 0, 100, 0),
    ("Reverb", 0, 100, 20),
    ("Delay", 0, 100, 0),
    ("Chorus", 0, 100, 0),
    ("Distortion", 0, 100, 0),
    ("LFO", 0, 10, 0),
    ("Sustain", 0, 5000, 500),
    ("Filter Cutoff", 20, 20000, 20000),
    ("Filter Q", 0, 100, 50),
    ("Attack", 1, 1000, 10),
    ("Decay", 1, 1000, 100),
    ("Sustain Level", 0, 100, 70),
    ("Release", 1, 2000, 500),
]
WAVEFORMS = {"Sine": None, "Square": 2, "Sawtooth": 1, "Triangle": 3, "PWM": 5}
KEY_MAP = {
    "a": "C4", "w": "C#4", "s": "D4", "e": "D#4", "d": "E4", "f": "F4", "t": "F#4", "g": "G4",
    "y": "G#4", "h": "A4", "u": "A#4", "j": "B4", "k": "C5", "o": "C#5", "l": "D5", "p": "D#5",
    ";": "E5", ":": "F5",
}
OCTAVES, FIRST_OCTAVE = 3, 4
POLYPHONY = 8
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_to_freq(note):
    """Frequency of a note name such as 'C#4' (A4 = 440 Hz)."""
    octave = int(note[-1])
    semitone = NOTE_NAMES.index(note[:-1])
    return 440 * (2 ** ((octave - 4) + (semitone - 9) / 12))

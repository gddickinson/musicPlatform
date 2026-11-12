"""Qt-free drum machine logic: grid size, step timing, offline rendering and MIDI tracks for a pattern.

Contents:
- ROWS, COLS, SAMPLE_NAMES, BPM_MIN/BPM_MAX/BPM_DEFAULT: the DrumMachineGUI grid and tempo range (the GUI imports them).
- step_interval_ms(bpm): the GUI's QTimer interval per 16th-note step (integer milliseconds, as the desktop uses).
- step_offsets(n_steps, bpm, sr): sample offset of each step when that timer is rendered at sample rate sr.
- render_pattern(pattern, samples, bpm, volumes, loops): the pattern mixed offline (mono float array).
- pattern_to_midi_tracks(pattern, bpm, volumes, loops): tracks for midi_export.build_midi (General MIDI drums).
- example_pattern(), EXAMPLE_VOLUMES: the web page's starter beat (the desktop grid starts empty).
- preset_data(pattern, bpm, volumes) / from_preset_data(data): the DrumPreset "data" dict (preset_manager.py).

A pattern is ROWS lists of COLS 0/1 values; volumes are dial values 0-100 per row (the GUI's QDial range).
The browser port is web/static/drum_engine.js, checked against this module by tests/fixtures/drum_fixture.json.
"""
import numpy as np

ROWS = 12
COLS = 32
SAMPLE_NAMES = ["Kick", "Snare", "Hi-Hat", "Clap", "Tom 1", "Tom 2",
                "Crash", "Ride", "Perc 1", "Perc 2", "FX 1", "FX 2"]
BPM_MIN, BPM_MAX, BPM_DEFAULT = 60, 180, 120
SAMPLE_RATE = 44100

# General MIDI percussion keys used for MIDI export (channel 10, i.e. channel index 9). The desktop rows are free
# sample slots; these are the closest GM sounds to the row names (FX rows: claves and maracas).
GM_NOTES = [36, 38, 42, 39, 48, 45, 49, 51, 56, 37, 75, 70]


def step_interval_ms(bpm):
    """Timer interval of one step, as DrumMachineGUI uses it: 60000 // bpm // 4 (floored to whole ms)."""
    return 60000 // int(bpm) // 4


def step_offsets(n_steps, bpm, sr=SAMPLE_RATE):
    """Sample index at which each of n_steps steps starts (whole samples, floored)."""
    ms = step_interval_ms(bpm)
    return [(k * ms * sr) // 1000 for k in range(n_steps)]


def empty_pattern():
    return [[0] * COLS for _ in range(ROWS)]


# A starter beat for the web page (the desktop app starts with an empty grid): row -> active steps.
EXAMPLE_STEPS = {0: [0, 8, 16, 22, 24], 1: [8, 24], 2: list(range(0, 32, 2)), 3: [30], 6: [0], 8: [6, 14],
                 9: [12, 28], 10: [31]}
EXAMPLE_VOLUMES = [100, 90, 55, 70, 100, 100, 60, 60, 50, 60, 45, 100]


def example_pattern():
    pattern = empty_pattern()
    for row, steps in EXAMPLE_STEPS.items():
        for c in steps:
            pattern[row][c] = 1
    return pattern


def render_pattern(pattern, samples, bpm, volumes=None, loops=1, sr=SAMPLE_RATE):
    """Mix the pattern offline: every active step starts its row's sample, scaled by the row volume (0-100).

    `samples` holds one 1-D float array (or None) per row. The result runs for `loops` passes of the pattern plus
    the longest sample, so the last hits ring out.
    """
    volumes = [100] * ROWS if volumes is None else volumes
    cols = len(pattern[0]) if pattern else COLS
    n_steps = cols * loops
    offsets = step_offsets(n_steps + 1, bpm, sr)
    longest = max((len(s) for s in samples if s is not None), default=0)
    out = np.zeros(offsets[n_steps] + longest)
    for k in range(n_steps):
        step = k % cols
        for row, line in enumerate(pattern):
            s = samples[row] if row < len(samples) else None
            if line[step] and s is not None and volumes[row] > 0:
                start = offsets[k]
                out[start:start + len(s)] += s * (volumes[row] / 100)
    return out


def pattern_to_midi_tracks(pattern, bpm, volumes=None, loops=1, names=None):
    """One General MIDI drum track: each hit is a note one step long, velocity = row volume (1-100)."""
    volumes = [100] * ROWS if volumes is None else volumes
    names = names or SAMPLE_NAMES
    cols = len(pattern[0]) if pattern else COLS
    ms = step_interval_ms(bpm)
    notes = []
    for k in range(cols * loops):
        for row, line in enumerate(pattern):
            if line[k % cols] and volumes[row] > 0:
                notes.append({"note": GM_NOTES[row], "start_time": k * ms / 1000, "end_time": (k + 1) * ms / 1000,
                              "velocity": max(1, min(127, int(volumes[row])))})
    return [{"name": "Drums: " + ", ".join(names[r] for r in range(len(pattern)) if any(pattern[r])),
             "channel": 9, "notes": notes}]


def preset_data(pattern, bpm, volumes):
    """The DrumPreset data dict: {"pattern": {"row,col": bool}, "bpm": int, "volumes": {"row": 0-1}}."""
    return {"pattern": {f"{r},{c}": bool(v) for r, line in enumerate(pattern) for c, v in enumerate(line)},
            "bpm": int(bpm), "volumes": {str(r): v / 100 for r, v in enumerate(volumes)}}


def from_preset_data(data):
    """(pattern, bpm, volumes) from a DrumPreset data dict; missing parts take the GUI defaults."""
    pattern = empty_pattern()
    for pos, on in (data.get("pattern") or {}).items():
        r, c = map(int, pos.split(","))
        if 0 <= r < ROWS and 0 <= c < COLS and on:
            pattern[r][c] = 1
    bpm = min(BPM_MAX, max(BPM_MIN, int(data.get("bpm", BPM_DEFAULT))))
    volumes = [100] * ROWS
    for r, v in (data.get("volumes") or {}).items():
        if 0 <= int(r) < ROWS:
            volumes[int(r)] = int(round(float(v) * 100))
    return pattern, bpm, volumes

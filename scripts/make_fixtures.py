"""Write the Python reference values the browser engines are tested against (node tests in web/static/*.test.mjs).

    python scripts/make_fixtures.py          # writes tests/fixtures/synth_fixture.json and drum_fixture.json
tests/test_fixtures_current.py checks (with a tolerance) that the committed fixtures still match the Python code.
"""
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import drum_engine as de  # noqa: E402
import drum_kit  # noqa: E402
import synth_dsp as dsp  # noqa: E402
from midi_export import build_midi  # noqa: E402
from wav_export import encode_wav  # noqa: E402

OUT = ROOT / "tests" / "fixtures"
BLOCK, NBLOCKS = 512, 3


def r(a):
    return [float(f"{x:.13g}") for x in np.asarray(a, dtype=float)]


def run(track, n=NBLOCKS, changes=None):
    out = []
    for b in range(n):
        if changes and b in changes:
            changes[b](track)
        out.append(track.generate_audio(BLOCK))
    return np.concatenate(out)


def wave(kind, freq=440, amp=0.5):
    t = dsp.WaveTrack(44100)
    t.set_wave_type(kind)
    t.set_frequency(freq)
    t.set_amplitude(amp)
    return t


EFFECTS = {  # name -> (constructor args, list of (class name, kwargs) to chain)
    "distortion": [("DistortionEffect", {"amount": 0.7})],
    "distortion0": [("DistortionEffect", {"amount": 0.0})],
    "eq": [("EQEffect", {"low_gain": 1.5, "high_gain": 0.4})],
    "vibrato": [("VibratoEffect", {"rate": 5.0, "depth": 0.005})],
    "tremolo": [("TremoloEffect", {"rate": 7.0, "depth": 0.6})],
    "chorus": [("ChorusEffect", {"rate": 1.3, "depth": 0.01, "mix": 0.5})],
    "lowpass": [("LowPassFilter", {"cutoff": 800.0})],
    "reverb": [("ReverbEffect", {"room_size": 0.8, "damping": 0.3, "mix": 0.6})],
    "reverb loud": [("ReverbEffect", {"room_size": 1.0, "damping": 0.0, "mix": 1.0})],
    "chain": [("TremoloEffect", {"rate": 3.0, "depth": 0.4}), ("LowPassFilter", {"cutoff": 2500.0}),
              ("DistortionEffect", {"amount": 0.9})],
}


def synth_fixture():
    cases = []
    for kind in ["sine", "square", "sawtooth", "triangle"]:
        cases.append({"name": f"wave {kind}", "track": {"type": "wave", "wave_type": kind, "frequency": 440,
                                                        "amplitude": 0.5}, "out": r(run(wave(kind)))})
    cases.append({"name": "wave sawtooth 1234.5 Hz", "track": {"type": "wave", "wave_type": "sawtooth",
                  "frequency": 1234.5, "amplitude": 0.8}, "out": r(run(wave("sawtooth", 1234.5, 0.8)))})
    for cf, mf, idx in [(440, 220, 2), (300, 77, 7.5)]:
        t = dsp.FMSynthTrack(44100)
        t.set_carrier_frequency(cf)
        t.set_mod_frequency(mf)
        t.set_mod_index(idx)
        cases.append({"name": f"fm {cf}/{mf}/{idx}", "track": {"type": "fm", "carrier_freq": cf, "mod_freq": mf,
                      "mod_index": idx, "amplitude": 0.5}, "out": r(run(t))})
    t = dsp.ContinuousNoteTrack("E", 3)
    t.set_harmonics([1, 0.5, 0, 0.25, 0.1])
    cases.append({"name": "note E3 + harmonics", "track": {"type": "note", "note": "E", "octave": 3,
                  "harmonics": [1, 0.5, 0, 0.25, 0.1], "amplitude": 0.5}, "out": r(run(t))})
    for kind in ["white", "pink", "brown"]:
        t = dsp.NoiseTrack(44100)
        t.set_noise_type(kind)
        np.random.seed(5)
        out = run(t)
        np.random.seed(5)
        white = np.concatenate([np.random.normal(0, 1, BLOCK) for _ in range(NBLOCKS)])
        cases.append({"name": f"noise {kind}", "track": {"type": "noise", "noise_type": kind, "amplitude": 0.5},
                      "white": r(white), "out": r(out)})
    for name, chain in EFFECTS.items():
        t = wave("sawtooth", 330, 0.7)
        for cls, kw in chain:
            t.add_effect(getattr(dsp, cls)(**kw))
        changes = {2: lambda tr: setattr(tr.get_effect("LowPassFilter"), "cutoff", 3000.0)} if name == "lowpass" else None
        cases.append({"name": f"effect {name}", "track": {"type": "wave", "wave_type": "sawtooth", "frequency": 330,
                      "amplitude": 0.7}, "effects": [{"cls": c, **kw} for c, kw in chain],
                      "change_cutoff_at_block": 2 if changes else None, "out": r(run(t, changes=changes))})
    automation = [[v, rate, lo, hi, dsp.automation_step(v, rate, lo, hi)]
                  for v, rate, lo, hi in [(440, 0, 20, 2000), (440, 300, 20, 2000), (1990, 1000, 20, 2000),
                                          (25, -1000, 20, 2000), (5, 19, 0, 10), (9, 40, 0, 10), (1, -60, 0, 10),
                                          (500, -999, 1, 1000)]]
    # long reverb runs (the comb + allpass delays exceed 1563 samples): an impulse, then a saw burst; every 7th sample
    reverb = []
    for params in [{"room_size": 0.8, "damping": 0.3, "mix": 0.6}, {"room_size": 1.0, "damping": 0.0, "mix": 1.0}]:
        x = np.zeros(8 * 1024)
        x[0] = 1.0
        x[3000:4000] = 0.7 * ((np.arange(1000) * 330 / 44100) % 1 * 2 - 1)
        eff = dsp.ReverbEffect(**params)
        y = np.concatenate([eff(x[i:i + 1024]) for i in range(0, len(x), 1024)])
        reverb.append({"params": params, "input": "impulse at 0, 0.7 * 330 Hz saw from 3000 to 4000", "n": len(y),
                       "every7": r(y[::7]), "sumsq": float((y * y).sum())})
    return {"block": BLOCK, "blocks": NBLOCKS, "cases": cases, "automation": automation, "reverb": reverb}


def stats(a):
    a = np.asarray(a, dtype=float)
    idx = np.arange(len(a))
    return {"n": len(a), "sum": float(a.sum()), "sumsq": float((a * a).sum()), "wsum": float((a * idx).sum() / len(a)),
            "head": r(a[:48]), "mid": r(a[len(a) // 2:len(a) // 2 + 48])}


def drum_fixture():
    kit = drum_kit.build_kit()
    pattern = de.example_pattern()
    vols = de.EXAMPLE_VOLUMES
    renders = []
    for bpm, loops in [(120, 1), (97, 2), (180, 1)]:
        audio = de.render_pattern(pattern, kit, bpm, vols, loops)
        wav = encode_wav(audio)
        buf = io.BytesIO()
        build_midi(de.pattern_to_midi_tracks(pattern, bpm, vols, loops)).save(file=buf)
        renders.append({"bpm": bpm, "loops": loops, "audio": stats(audio), "wav_len": len(wav),
                        "wav_sha256": hashlib.sha256(wav).hexdigest(), "midi_hex": buf.getvalue().hex()})
    wav_small = encode_wav(np.array([0.3, -0.2, 0.0, 0.7, -0.7, 1e-6]), normalize=True)
    return {"step_ms": {str(b): de.step_interval_ms(b) for b in range(de.BPM_MIN, de.BPM_MAX + 1)},
            "offsets_97": de.step_offsets(40, 97), "kit": [stats(v) for v in kit], "renders": renders,
            "wav_small_hex": wav_small.hex(), "preset": de.preset_data(pattern, 97, vols),
            "gm_notes": de.GM_NOTES}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in [("synth_fixture.json", synth_fixture()), ("drum_fixture.json", drum_fixture())]:
        (OUT / name).write_text(json.dumps(data, separators=(",", ":")))
        print(f"wrote tests/fixtures/{name} ({(OUT / name).stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()

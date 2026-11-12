"""FastAPI web app for the Music Production Platform: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8167, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below.
Everything comes from the repo's Qt-free modules: drum_engine, drum_kit, synth_dsp, piano_spec, midi_export, wav_export.
"""
import base64
import hashlib
import io
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import drum_engine as de  # noqa: E402
import drum_kit  # noqa: E402
import piano_spec  # noqa: E402
import synth_dsp as dsp  # noqa: E402
from midi_export import build_midi  # noqa: E402
from wav_export import encode_wav  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
SUMMARY = ("A digital audio workstation built with Python and PyQt5: piano keyboard, drum machine, sample pad, "
           "sound generator, recording studio, mixer and project/preset management in one tabbed window.")
WEB_OMITS = {
    "ReverbEffect": "the desktop formula sums a whole second of samples per output sample with weights that grow "
                    "with age (gain of the order of 10,000x and far too slow for real time); left out until fixed.",
}

app = FastAPI(title="Music Production Platform")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Grid, ranges, effects and piano settings, all read from the Python modules the desktop app uses."""
    effects = [{"name": cls.__name__, "params": {k: list(v) for k, v in params.items()},
                "web": cls.__name__ not in WEB_OMITS, "omitted_because": WEB_OMITS.get(cls.__name__)}
               for cls, params in dsp.EFFECT_PARAMS]
    return {
        "title": "Music Production Platform", "summary": SUMMARY,
        "drums": {"rows": de.ROWS, "cols": de.COLS, "names": de.SAMPLE_NAMES, "bpm": [de.BPM_MIN, de.BPM_MAX,
                  de.BPM_DEFAULT], "gm_notes": de.GM_NOTES,
                  "step_ms": {b: de.step_interval_ms(b) for b in (de.BPM_MIN, de.BPM_DEFAULT, de.BPM_MAX)},
                  "kit_lengths_s": [round(len(v) / drum_kit.SR, 3) for v in kit()]},
        "synth": {"track_types": ["wave", "noise", "fm", "note"], "wave_types": ["sine", "square", "sawtooth", "triangle"],
                  "noise_types": ["white", "pink", "brown"], "dials": {k: list(v) for k, v in dsp.DIAL_RANGES.items()},
                  "automation_rate": list(dsp.AUTOMATION_RATE_RANGE), "octaves": list(dsp.NOTE_OCTAVES),
                  "harmonics": dsp.NOTE_HARMONICS, "notes": piano_spec.NOTE_NAMES, "effects": effects},
        "piano": {"sliders": [list(s) for s in piano_spec.SLIDERS], "waveforms": list(piano_spec.WAVEFORMS),
                  "key_map": piano_spec.KEY_MAP, "octaves": piano_spec.OCTAVES, "first_octave": piano_spec.FIRST_OCTAVE,
                  "polyphony": piano_spec.POLYPHONY},
    }


@lru_cache(maxsize=1)
def kit():
    return drum_kit.build_kit()


@app.get("/api/verify")
def verify():
    """Python reference values (the same as tests/fixtures) for the browser to re-check its engines against."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_fixtures
    return {"synth": make_fixtures.synth_fixture(), "drum": make_fixtures.drum_fixture()}


class DrumRender(BaseModel):
    pattern: List[List[int]] = Field(..., description="12 rows of 32 steps (0/1)")
    bpm: int = de.BPM_DEFAULT
    volumes: Optional[List[int]] = None
    loops: int = Field(1, ge=1, le=8)


@app.post("/api/drums/render")
def drums_render(req: DrumRender):
    """Render a pattern with the Python code (kit, mix, WAV and MIDI) so the page can compare the bytes."""
    if len(req.pattern) != de.ROWS or any(len(r) != de.COLS for r in req.pattern):
        raise HTTPException(400, f"pattern must be {de.ROWS} x {de.COLS}")
    if not de.BPM_MIN <= req.bpm <= de.BPM_MAX:
        raise HTTPException(400, f"bpm must be {de.BPM_MIN}-{de.BPM_MAX}")
    vols = req.volumes or [100] * de.ROWS
    wav = encode_wav(de.render_pattern(req.pattern, kit(), req.bpm, vols, req.loops))
    buf = io.BytesIO()
    build_midi(de.pattern_to_midi_tracks(req.pattern, req.bpm, vols, req.loops)).save(file=buf)
    midi = buf.getvalue()
    return {"wav_sha256": hashlib.sha256(wav).hexdigest(), "wav_bytes": len(wav),
            "midi_sha256": hashlib.sha256(midi).hexdigest(), "midi_b64": base64.b64encode(midi).decode()}


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/verify"]

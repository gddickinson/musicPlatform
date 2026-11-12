"""The committed JS-vs-Python fixtures (tests/fixtures/*.json) still match the Python code.

Regenerate with `python scripts/make_fixtures.py` after changing synth_dsp.py, drum_engine.py, drum_kit.py,
midi_export.py or wav_export.py. Numbers are compared with a tolerance (libm differs in the last digit between
platforms); the WAV hash depends on libsndfile, so only its length is compared here.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
pytest.importorskip("mido")
pytest.importorskip("soundfile")

import make_fixtures  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def same(a, b, path="", rtol=1e-9, atol=1e-11):
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            if k != "wav_sha256":
                same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and a and isinstance(a[0], (int, float)) and not isinstance(a[0], bool):
        np.testing.assert_allclose(a, b, rtol=rtol, atol=atol, err_msg=path)
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, f"{path}[{i}]")
    elif isinstance(a, float):
        assert a == pytest.approx(b, rel=rtol, abs=atol), path
    else:
        assert a == b, path


@pytest.mark.parametrize("name,make", [("synth_fixture.json", make_fixtures.synth_fixture),
                                       ("drum_fixture.json", make_fixtures.drum_fixture)])
def test_fixture_current(name, make):
    committed = json.loads((FIX / name).read_text())
    same(json.loads(json.dumps(make())), committed, name)

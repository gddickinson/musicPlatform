"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


def test_info_comes_from_the_python_modules():
    import drum_engine
    import piano_spec
    j = client.get("/api/info").json()
    assert j["drums"]["names"] == drum_engine.SAMPLE_NAMES and j["drums"]["cols"] == 32
    assert [s[0] for s in j["piano"]["sliders"]] == [s[0] for s in piano_spec.SLIDERS]
    assert all(e["web"] for e in j["synth"]["effects"]) and len(j["synth"]["effects"]) == 7


def test_drums_render_matches_the_fixture():
    import json
    fx = json.loads((ROOT / "tests" / "fixtures" / "drum_fixture.json").read_text())
    import drum_engine
    r = fx["renders"][1]
    j = client.post("/api/drums/render", json={"pattern": drum_engine.example_pattern(), "bpm": r["bpm"],
                                               "volumes": drum_engine.EXAMPLE_VOLUMES, "loops": r["loops"]}).json()
    assert j["wav_bytes"] == r["wav_len"]
    import base64
    assert base64.b64decode(j["midi_b64"]).hex() == r["midi_hex"]


def test_drums_render_rejects_bad_input():
    assert client.post("/api/drums/render", json={"pattern": [[0] * 32] * 3}).status_code == 400
    assert client.post("/api/drums/render", json={"pattern": [[0] * 32] * 12, "bpm": 500}).status_code == 400

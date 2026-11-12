"""The committed WAVs in samples/ and wav/ are the original synthesised sounds of sound_library.py (and nothing else)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sf = pytest.importorskip("soundfile")

from sound_library import SOUNDS  # noqa: E402


def test_every_wav_is_generated():
    on_disk = {p.relative_to(ROOT).as_posix() for d in ("samples", "wav") for p in (ROOT / d).glob("*.wav")}
    assert on_disk == set(SOUNDS)


@pytest.mark.parametrize("rel", sorted(SOUNDS))
def test_wav_matches_the_generator(rel):
    data, sr = sf.read(str(ROOT / rel))
    want = SOUNDS[rel]()
    assert sr == 44100 and data.ndim == 1 and len(data) == len(want)
    assert np.max(np.abs(data - want)) <= 2 / 32768  # 16-bit quantisation


def test_drum_samples_are_the_web_kit():
    import drum_kit
    for r in range(12):
        data, _ = sf.read(str(ROOT / f"samples/sample{r}.wav"))
        assert np.max(np.abs(data - drum_kit.kit_voice(r))) <= 2 / 32768

"""Write the original synthesised sounds of sound_library.py into samples/ and wav/ (16-bit mono, 44.1 kHz).

    python scripts/make_sounds.py
tests/test_sounds.py checks that the committed files are what this script writes.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import soundfile as sf  # noqa: E402

from sound_library import SOUNDS, SR  # noqa: E402


def main():
    total = 0
    for rel, make in SOUNDS.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), make(), SR, subtype="PCM_16")
        total += path.stat().st_size
    print(f"wrote {len(SOUNDS)} sounds, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

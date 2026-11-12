# Third-party material

This repository's own code is under the MIT licence in `LICENSE`.

## Sounds in `samples/` and `wav/`

All 35 WAV files are **original sounds synthesised from scratch** for this repository by `sound_library.py`
(written by `scripts/make_sounds.py`: numpy, seeded noise, oscillators and simple filters; no recorded samples) and
are released under the same MIT licence as the code. `samples/sample0.wav` ... `sample11.wav` are the drum kit of
`drum_kit.py`, the same sounds the web drum machine plays.

They replaced, on 2026-11-12, WAV files of unknown origin and without a stated licence (a drum kit, a fog horn and a
150 BPM bass loop). The file names were kept so presets and the drum machine still find them. The old files were
also purged from the git history on 2026-11-12 (history rewrite), so the repository no longer contains them.

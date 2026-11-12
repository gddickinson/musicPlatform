"""Qt-free WAV encoding with the AudioExporter's conventions (audio_export.py).

- to_channels(audio, channels): mono (n,) -> (n, channels) by repeating, as AudioExporter does for stereo.
- normalize_buffer(buffer): scale so the peak is 0.95 (AudioExporter's normalize option; silence is unchanged).
- encode_wav(audio, sr, channels, normalize, subtype): the WAV file bytes written with soundfile (PCM_16 default).
The browser writes the same bytes in web/static/wav_writer.js (16-bit as libsndfile 1.2: rint(x * 2**31) >> 16, clipped;
checked by tests/fixtures/drum_fixture.json).
"""
import io

import numpy as np

PEAK = 0.95


def to_channels(audio, channels=2):
    audio = np.asarray(audio, dtype=float)
    if audio.ndim == 1:
        return np.column_stack([audio] * channels) if channels > 1 else audio.reshape(-1, 1)
    return audio[:, :channels]


def normalize_buffer(buffer):
    max_val = np.max(np.abs(buffer)) if buffer.size else 0
    return buffer / max_val * PEAK if max_val > 0 else buffer


def encode_wav(audio, sr=44100, channels=2, normalize=True, subtype='PCM_16'):
    import soundfile as sf
    buf = to_channels(audio, channels)
    if normalize:
        buf = normalize_buffer(buf)
    out = io.BytesIO()
    sf.write(out, buf, sr, subtype=subtype, format='WAV')
    return out.getvalue()

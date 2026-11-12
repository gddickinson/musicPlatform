// WAV bytes as wav_export.encode_wav / AudioExporter write them: mono repeated to stereo, peak normalised to 0.95,
// 16-bit PCM with libsndfile 1.2's conversion (to 32-bit: rint(x * 2^31), clipped; then >> 16), canonical
// 44-byte header.
function roundHalfEven(v) {
  const f = Math.floor(v), d = v - f;
  return d > 0.5 || (d === 0.5 && f % 2 !== 0) ? f + 1 : f;
}
export function toPcm16(x) {
  const v = Math.max(-2147483648, Math.min(2147483647, x * 2147483648));
  return Math.floor(roundHalfEven(v) / 65536);
}

export function encodeWav(audio, { sr = 44100, channels = 2, normalize = true } = {}) {
  let peak = 0;
  for (const v of audio) peak = Math.max(peak, Math.abs(v));
  const n = audio.length, bytes = new ArrayBuffer(44 + n * channels * 2), dv = new DataView(bytes);
  const str = (o, s) => [...s].forEach((ch, i) => dv.setUint8(o + i, ch.charCodeAt(0)));
  str(0, 'RIFF'); dv.setUint32(4, 36 + n * channels * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, channels, true); dv.setUint32(24, sr, true);
  dv.setUint32(28, sr * channels * 2, true); dv.setUint16(32, channels * 2, true); dv.setUint16(34, 16, true);
  str(36, 'data'); dv.setUint32(40, n * channels * 2, true);
  let o = 44;
  for (let i = 0; i < n; i++) {
    const x = normalize && peak > 0 ? audio[i] / peak * 0.95 : audio[i];
    const s = toPcm16(x);
    for (let c = 0; c < channels; c++) { dv.setInt16(o, s, true); o += 2; }
  }
  return new Uint8Array(bytes);
}

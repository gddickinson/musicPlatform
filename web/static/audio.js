// Shared WebAudio helpers: one AudioContext at 44.1 kHz, created only after a user click (browsers block autoplay),
// Float64 -> AudioBuffer conversion and a small oscilloscope drawer.
let ctx = null;

export function audioContext() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    try { ctx = new AC({ sampleRate: 44100 }); } catch { ctx = new AC(); }
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

export function toBuffer(ac, data, sr = 44100) {
  const buf = ac.createBuffer(1, Math.max(1, data.length), sr);
  buf.getChannelData(0).set(data);
  return buf;
}

// Decode a user's audio file to mono at the context rate (stereo averaged, as the desktop drum machine does).
export async function decodeMono(ac, file) {
  const buf = await ac.decodeAudioData(await file.arrayBuffer());
  const out = new Float64Array(buf.length);
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) out[i] += d[i] / buf.numberOfChannels;
  }
  return out;
}

// Draw one or more traces; yRange 'auto' scales to the largest peak.
export function drawScope(canvas, traces, { colors = ['#ff4fd8', '#26e0ff', '#ffcf3f', '#7dff8a', '#b38bff', '#ff8f5a'],
  yRange = 1 } = {}) {
  const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth || 600, h = canvas.clientHeight || 140;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  const g = canvas.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  g.strokeStyle = 'rgba(148,163,198,.25)';
  g.beginPath(); g.moveTo(0, h / 2); g.lineTo(w, h / 2); g.stroke();
  let peak = yRange;
  if (yRange === 'auto') { peak = 1e-9; for (const t of traces) for (const v of t) peak = Math.max(peak, Math.abs(v)); }
  traces.forEach((t, k) => {
    if (!t || !t.length) return;
    g.strokeStyle = colors[k % colors.length]; g.lineWidth = 1.2; g.beginPath();
    const stepPx = w / t.length;
    for (let i = 0; i < t.length; i++) {
      const x = i * stepPx, y = h / 2 - (t[i] / peak) * (h / 2 - 4);
      if (i) g.lineTo(x, y); else g.moveTo(x, y);
    }
    g.stroke();
  });
}

export async function sha256hex(bytes) {
  const d = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
}

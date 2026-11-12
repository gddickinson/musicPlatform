// Subtle animated background: a slowly scrolling step grid with a few lit cells. Static under prefers-reduced-motion.
export function drawBackground(canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const lit = Array.from({ length: 40 }, (_, i) => ({ c: (i * 7) % 32, r: (i * 5) % 12 }));
  const draw = t => {
    const w = canvas.width = innerWidth, h = canvas.height = innerHeight, s = 34;
    ctx.clearRect(0, 0, w, h);
    const shift = (t * 0.01) % s;
    ctx.strokeStyle = 'rgba(38,224,255,.10)';
    for (let x = -shift; x < w; x += s) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += s) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    for (const { c, r } of lit) {
      ctx.fillStyle = r % 3 ? 'rgba(255,79,216,.22)' : 'rgba(255,207,63,.2)';
      ctx.fillRect(c * s - shift + 4, r * s * 2 + 4, s - 8, s - 8);
    }
  };
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { draw(0); return; }
  const loop = t => { draw(t); setTimeout(() => requestAnimationFrame(loop), 80); };
  requestAnimationFrame(loop);
}

// MIDI file bytes as midi_export.build_midi + mido's MidiFile.save write them: format 1, 480 ticks per beat, a tempo
// track (120 BPM), one track per entry; events at absolute ticks (note-offs, then control changes, then note-ons at
// the same tick), running status as mido writes it (a repeated status byte is left out), end-of-track added.
const TPS = 960;  // ticks per second at 120 BPM

function vlq(n) {
  const out = [n & 0x7f];
  while ((n >>= 7)) out.unshift((n & 0x7f) | 0x80);
  return out;
}
function trackEvents(t) {
  const ch = t.channel ?? 0, ev = [];
  for (const n of t.notes || []) {
    const start = Math.trunc(n.start_time * TPS), dur = Math.trunc((n.end_time - n.start_time) * TPS);
    ev.push([start, 2, [0x90 | ch, n.note, n.velocity]]);
    ev.push([start + dur, 0, [0x80 | ch, n.note, 0]]);
  }
  for (const c of t.control_changes || []) ev.push([Math.trunc(c.time * TPS), 1, [0xb0 | ch, c.control, c.value]]);
  return ev.map((e, i) => [...e, i]).sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[3] - b[3]);
}
function chunk(type, data) {
  const len = data.length;
  return [...type].map(c => c.charCodeAt(0)).concat([len >>> 24, (len >> 16) & 255, (len >> 8) & 255, len & 255], data);
}
export function buildMidi(tracks = []) {
  const head = chunk('MThd', [0, 1, 0, tracks.length + 1, 0x01, 0xe0]);
  const tempo = chunk('MTrk', [0, 0xff, 0x51, 3, 0x07, 0xa1, 0x20, 0, 0xff, 0x2f, 0]);
  const body = tracks.map(t => {
    const d = [];
    if (t.name !== undefined) {
      const name = [...t.name].map(c => c.charCodeAt(0) & 0xff);
      d.push(0, 0xff, 0x03, ...vlq(name.length), ...name);
    }
    let last = 0, running = null;
    for (const [tick, , msg] of trackEvents(t)) {
      d.push(...vlq(tick - last), ...(msg[0] === running ? msg.slice(1) : msg));
      running = msg[0]; last = tick;
    }
    d.push(0, 0xff, 0x2f, 0);
    return chunk('MTrk', d);
  });
  return new Uint8Array(head.concat(tempo, ...body));
}

"""Qt-free MIDI file building for audio_export.MidiExporter (and the web app).

build_midi(tracks) returns a mido.MidiFile: format 1, 480 ticks per beat, a tempo track at 120 BPM (so 960 ticks per
second), then one track per entry of `tracks`:
    {"name": str, "channel": 0-15 (optional, default 0),
     "notes": [{"note", "start_time", "end_time", "velocity"}],   # times in seconds
     "control_changes": [{"control", "time", "value"}]}
Events are placed at absolute ticks and then delta-encoded, so chords and control changes keep their times. At the
same tick note-offs come first, then control changes, then note-ons. The browser port is web/static/midi_writer.js.
"""
TICKS_PER_BEAT = 480
TICKS_PER_SECOND = TICKS_PER_BEAT * 2  # 120 BPM
TEMPO_US = 500000


def track_events(track_data):
    """(tick, order, message kwargs) for one track, sorted by time."""
    channel = int(track_data.get('channel', 0))
    events = []
    for n in track_data.get('notes') or []:
        start = int(n['start_time'] * TICKS_PER_SECOND)
        duration = int((n['end_time'] - n['start_time']) * TICKS_PER_SECOND)
        events.append((start, 2, dict(type='note_on', note=n['note'], velocity=n['velocity'], channel=channel)))
        events.append((start + duration, 0, dict(type='note_off', note=n['note'], velocity=0, channel=channel)))
    for cc in track_data.get('control_changes') or []:
        events.append((int(cc['time'] * TICKS_PER_SECOND), 1,
                       dict(type='control_change', control=cc['control'], value=cc['value'], channel=channel)))
    events.sort(key=lambda e: (e[0], e[1]))  # stable: equal events keep their input order
    return events


def build_midi(tracks=None):
    """The MidiFile for `tracks` (mido is imported here so this module loads without it)."""
    from mido import Message, MetaMessage, MidiFile, MidiTrack

    mid = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage('set_tempo', tempo=TEMPO_US, time=0))
    for track_data in tracks or []:
        track = MidiTrack()
        mid.tracks.append(track)
        if 'name' in track_data:
            track.append(MetaMessage('track_name', name=track_data['name'], time=0))
        last = 0
        for tick, _, msg in track_events(track_data):
            kind = msg.pop('type')
            track.append(Message(kind, time=tick - last, **msg))
            last = tick
    return mid

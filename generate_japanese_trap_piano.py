#!/usr/bin/env python3
"""
Generate a MIDI file for a Japanese-style piano arpeggio + chord progression (BPM 130).
Creates 'japanese_trap_piano.mid' in the current directory.
Tries pretty_midi first, falls back to mido.
"""

from pathlib import Path
from math import ceil

OUT_PATH = Path("japanese_trap_piano.mid")

BPM = 130
BEAT_DURATION = 60.0 / BPM  # seconds per quarter note
TPB = 480  # ticks per beat (for mido fallback)

# NOTE_MAP: base mapping for octave 4 (C4=60)
NOTE_MAP = {
    'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64, 'F': 65, 'F#': 66,
    'G': 67, 'G#': 68, 'A': 69, 'A#': 70, 'B': 71
}

def note_to_midi(note: str) -> int:
    """Convert note string like 'A3' or 'C#4' to MIDI number."""
    # parse name and octave
    if len(note) == 2:
        name = note[0]
        octave = int(note[1])
    elif len(note) == 3:
        name = note[0:2]  # includes accidental
        octave = int(note[2])
    else:
        raise ValueError("Unsupported note format: " + note)
    base = NOTE_MAP[name]  # for octave 4
    semitone_offset = (octave - 4) * 12
    return base + semitone_offset

# Chord voicings (names -> list of notes as strings)
CHORDS = {
    "Am7": ["A3","C4","E4","G4"],
    "Dm7": ["D3","F3","A3","C4"],
    "Em7": ["E3","G3","B3","D4"],
    "Cmaj7": ["C3","E3","G3","B3"],
    "Am9": ["A3","C4","E4","G4","B4"],
    "Dm9": ["D3","F3","A3","C4","E4"],
    "G13": ["G2","B2","E3","F3"],
    "Fmaj7": ["F3","A3","C4","E4"],
    "G": ["G3","B3","D4"],
    "Cmaj9": ["C3","E3","G3","B3","D4"],
}

# convert to MIDI numbers
CHORDS_MIDI = {name: [note_to_midi(n) for n in notes] for name, notes in CHORDS.items()}

# Sequence structure: (chord_name, bars)
STRUCTURE = [
    ("Am7", 1.0), ("Dm7", 1.0), ("Em7", 1.0), ("Cmaj7", 1.0),  # Intro
    ("Am9", 1.0), ("Dm9", 1.0), ("G13", 1.0), ("Cmaj7", 1.0),  # Verse
    ("Fmaj7", 1.0), ("G", 1.0), ("Em7", 1.0), ("Am9", 1.0),     # Chorus
    ("Fmaj7", 1.0), ("Em7", 1.0), ("Dm7", 1.0), ("Cmaj9", 1.0)  # Bridge
]

ARPEGGIO_DIVS = 8  # number of arpeggio notes per bar (8 = 8th notes)
VELOCITY_LEFT = 60
VELOCITY_RIGHT = 85

# Try pretty_midi first (preferred for nicer timing)
try:
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    piano_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
    piano = pretty_midi.Instrument(program=piano_program)
    time = 0.0

    for chord_name, bars in STRUCTURE:
        notes = CHORDS_MIDI.get(chord_name, [])
        duration = bars * 4 * BEAT_DURATION

        # Left hand: sustained root one octave lower
        if notes:
            root = notes[0] - 12
            piano.notes.append(pretty_midi.Note(velocity=VELOCITY_LEFT, pitch=root, start=time, end=time+duration))

        # Right hand: broken arpeggio spanning the bar(s)
        if notes:
            total_notes = int(ARPEGGIO_DIVS * bars)
            note_length = (bars * 4 * BEAT_DURATION) / total_notes
            for i in range(total_notes):
                tone = notes[i % len(notes)]
                start = time + i * note_length
                end = start + note_length * 0.95
                piano.notes.append(pretty_midi.Note(velocity=VELOCITY_RIGHT, pitch=tone, start=start, end=end))

        time += duration

    pm.instruments.append(piano)
    pm.write(str(OUT_PATH))
    print(f"SUCCESS: MIDI written to {OUT_PATH}")

except Exception as e_pretty:
    # fallback to mido if pretty_midi not available
    try:
        import mido
        from mido import Message, MidiFile, MidiTrack, MetaMessage

        mid = MidiFile(ticks_per_beat=TPB)
        track = MidiTrack()
        mid.tracks.append(track)
        tempo = int(mido.bpm2tempo(BPM))
        track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
        # Program change -> Acoustic Grand Piano (program 0)
        track.append(Message('program_change', program=0, time=0))

        def sec_to_ticks(sec):
            beats = sec / BEAT_DURATION
            return int(round(beats * TPB))

        for chord_name, bars in STRUCTURE:
            notes = CHORDS_MIDI.get(chord_name, [])
            duration_ticks = sec_to_ticks(bars * 4 * BEAT_DURATION)

            # left hand root
            if notes:
                root = notes[0] - 12
                track.append(Message('note_on', note=root, velocity=VELOCITY_LEFT, time=0))
                track.append(Message('note_off', note=root, velocity=0, time=duration_ticks))

            # right hand arpeggio
            if notes:
                total_notes = int(ARPEGGIO_DIVS * bars)
                note_ticks = sec_to_ticks((bars * 4 * BEAT_DURATION) / total_notes)
                for i in range(total_notes):
                    tone = notes[i % len(notes)]
                    track.append(Message('note_on', note=tone, velocity=VELOCITY_RIGHT, time=0))
                    track.append(Message('note_off', note=tone, velocity=0, time=note_ticks))

        mid.save(str(OUT_PATH))
        print(f"SUCCESS (mido): MIDI written to {OUT_PATH}")

    except Exception as e_mido:
        print("FAILED: could not generate MIDI in this environment.")
        print("pretty_midi error:", e_pretty)
        print("mido error:", e_mido)
        print("\nTo run locally, install packages and re-run:")
        print("  pip install pretty_midi")
        print("or (fallback) pip install mido")

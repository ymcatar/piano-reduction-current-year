import music21

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)

def highlight(noteOrChord, color):
    if isNote(noteOrChord):
        noteOrChord.style.color = color
    elif isChord(noteOrChord):
        for note in noteOrChord._notes: # undocumented music21 API, might break for future version
            highlight(note, color)
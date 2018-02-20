import music21

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)
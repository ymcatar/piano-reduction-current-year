import music21

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
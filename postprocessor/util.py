import math
import music21
import numpy as np

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def construct_vector(offset, notes):
    # construct the vector
    pitches = sorted(math.trunc(n.note.pitch.ps) for n in notes if not n.deleted)
    vector = [0] * 97
    for item in pitches:
        if item in range(12, 97):
            vector[item] = 1
    return vector

def construct_piano_roll(measures):
    piano_roll = np.zeros((len(measures), 97))
    for i, measure in enumerate(measures):
        offset, notes = measure
        notes = sorted((n for n in notes if not n.deleted), key=lambda n: n.note.pitch.ps)
        piano_roll[i,:] = construct_vector(offset, notes)
    return piano_roll

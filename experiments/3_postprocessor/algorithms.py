import music21
import numpy as np
from collections import defaultdict
from util import isNote, isChord

# Constants
MAX_CONCURRENT_NOTE = 4
MAX_PITCH_STEP_CHANGE = 8

class PostProcessorAlgorithms(object):

    @staticmethod
    def concurrent_notes(group_tuple):
        offset, group = group_tuple
        notes = [n for n in group if isNote(n.note)]

        # highlight all time instance with note playing >= MAX_CONCURRENT_NOTE
        if len(notes) >= MAX_CONCURRENT_NOTE:
            return [notes]

        return []

    @staticmethod
    # FIXME: probably a bad fix musically, refine later
    def fix_concurrent_notes(group):
        pitches = list(set(n.note.name for n in group))
        if len(pitches) == 3: # see if they forms a triad
            chord = music21.chord.Chord(pitches)
            if chord.isTriad():
                for n in group:
                    n.highlight('#0000ff')



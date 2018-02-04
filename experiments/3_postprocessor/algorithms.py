import music21
import numpy as np
from collections import defaultdict
from util import isNote, isChord

# Constants
MAX_CONCURRENT_NOTE = 5
MAX_PITCH_STEP_CHANGE = 8


class PostProcessorAlgorithms(object):

    @staticmethod
    def detect_triad(group_tuple):
        offset, group = group_tuple
        notes = [n for n in group if isNote(n.note)]
        pitches = list(n + '4' for n in set(n.note.name for n in notes))

        chord = music21.chord.Chord(pitches)

        if len(pitches) == 3:  # a possible triad
            if chord.isTriad():
                print('triad: ', chord)
                for n in group:
                    n.highlight('#0000ff')
                return [notes]

        return []

    @ staticmethod
    def fix_triad(notes):
        pass
        # print(notes)

    @staticmethod
    def detect_too_many_concurrent_notes(group_tuple):
        offset, group = group_tuple
        notes = [n for n in group if isNote(n.note)]

        # highlight all time instance with note playing >= MAX_CONCURRENT_NOTE
        if len(notes) >= MAX_CONCURRENT_NOTE:
            return [notes]

        return []

    @staticmethod
    # FIXME: probably a bad fix musically, refine later
    def fix_too_many_concurrent_notes(notes):
        pitches = defaultdict(lambda: [])
        for note in notes:
            pitches[note.note.name].append(note)

        # remove notes in unisons by keeping the higher one
        for name, note_list in pitches.items():
            note_list = sorted(note_list, key=lambda n: n.note.pitch.ps, reverse=True)
            if len(note_list) >= 2:
                for note in note_list[1:-1]:
                    # note.highlight('red')
                    note.remove()

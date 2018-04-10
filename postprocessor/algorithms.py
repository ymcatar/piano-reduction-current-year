import music21
import numpy as np
from collections import defaultdict
from util import isNote, isChord

# Constants
MAX_CONCURRENT_NOTE = 5
MAX_PITCH_STEP_CHANGE = 8


class PostProcessorAlgorithms(object):

    @staticmethod
    def repeated_note(groups):

        offset, group = groups[0]
        notes = [n for n in group if isNote(n.note)]
        ps_map = defaultdict(lambda: [])

        for n in notes:
            ps_map[(n.note.duration.quarterLength, n.note.pitch.ps)].append(n)

        for ps, notes in ps_map.items():
            if len(notes) > 1:
                for note in notes[1:]:
                    note.deleted = True

    # @staticmethod
    # def detect_triad(group_tuple):
    #     offset, group = group_tuple
    #     notes = [n for n in group if isNote(n.note)]
    #     pitches = list(n + '4' for n in set(n.note.name for n in notes))

    #     chord = music21.chord.Chord(pitches)

    #     if len(pitches) == 3:  # a possible triad
    #         if chord.isTriad():
    #             for n in group:
    #                 n.highlight('#0000ff')
    #             return [notes]

    #     return []

    # @ staticmethod
    # def fix_triad(notes):
    #     # print('triad:', notes)
    #     pass

    # @staticmethod
    # def detect_too_many_concurrent_notes(group_tuple):
    #     offset, group = group_tuple
    #     notes = [n for n in group if isNote(n.note)]

    #     # highlight all time instance with note playing >= MAX_CONCURRENT_NOTE
    #     if len(notes) >= MAX_CONCURRENT_NOTE:
    #         return [notes]

    #     return []

    # @staticmethod
    # # FIXME: probably a bad fix musically, refine later
    # def fix_too_many_concurrent_notes(notes):
    #     pitches = defaultdict(lambda: [])
    #     for note in notes:
    #         pitches[note.note.name].append(note)

    #     # remove notes in unisons by keeping the higher one
    #     for name, note_list in pitches.items():
    #         note_list = sorted(note_list, key=lambda n: n.note.pitch.ps, reverse=True)
    #         if len(note_list) >= 2:
    #             # only keep the lowest and the highest
    #             for note in note_list[1:-1]:
    #                 note.remove()

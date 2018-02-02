#!/usr/vin/env python3

import math
import music21
import numpy as np
from collections import defaultdict
from copy import deepcopy
from operator import itemgetter

# relative import
from util import isNote, isChord
from algorithms import PostProcessorAlgorithms
from note_wrapper import NoteWrapper

# algorithm set

ALGORITHMS_BY_MEASURE_GROUP = [
]

ALGORITHMS_BY_MEASURE = [
    # (PostProcessorAlgorithms.large_hand_movement, PostProcessorAlgorithms.fix_large_hand_movement)
]

ALGORITHMS_BY_OFFSET_GROUPED_NOTES = [
    # (PostProcessorAlgorithms.concurrent_notes, PostProcessorAlgorithms.fix_concurrent_notes)
]

# https://assets.key-notes.com/natural_hand_position.png
FINGER_DEFAULT_POSITION = {
    'L': {          # 5, 4, 3, 2, 1
        'C#': 2,
        'D': 1,
        'D#': 2,
        'E': 5,     # natural
        'F': 5,
        'F#': 4,    # natural
        'G': 5,
        'G#': 3,    # natural
        'A': 1,
        'A#': 2,    # natural
        'B': 1,
        'C': 1      # natural
    },
    'R': {          # 1, 2, 3, 4, 5
        'C#': 4,
        'D': 5,
        'D#': 4,
        'E': 1,     # natural
        'F': 1,
        'F#': 3,    # natural
        'G': 1,
        'G#': 4,    # natural
        'A': 5,
        'A#': 4,    # natural
        'B': 5,
        'C': 5      # natural
    }
}

class PostProcessor(object):

    def __init__(self, score):

        self.score = score

        # get all measures from the score
        self.measures = list(self.score.recurse(skipSelf=True).getElementsByClass('Measure'))
        for measure in self.measures:
            measure.removeByClass([
                music21.layout.PageLayout,
                music21.layout.SystemLayout,
                music21.layout.StaffLayout])

        # group measures with the same offset together
        self.grouped_measures = defaultdict(lambda: [])
        for measure in self.measures:
           self.grouped_measures[str(measure.offset)].append(measure)

        # group notes starting at the same time instance together
        self.offset_grouped_notes = defaultdict(lambda: [])
        for _, group in self.grouped_measures.items():
            for measure in group:
                offset_map = measure.offsetMap()
                for item in offset_map:
                    offset = measure.offset + item.offset
                    if isChord(item.element):
                        for note in item.element._notes:
                            note = NoteWrapper(note, offset, self.score, item.element)
                            self.offset_grouped_notes[offset].append(note)
                    else: # note or rest
                        note = NoteWrapper(item.element, offset, self.score)
                        self.offset_grouped_notes[offset].append(note)

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    # def perform_staff_assignment(self, offset, notes, prev=None):

    #     octaves = list(set(n.note.octave for n in notes))

    #     if not prev: # is the first time instance, apply staff assignment

    #         left_notes, right_notes = [], []

    #         if len(octaves) == 0: # no notes => do nothing
    #             return None

    #         elif len(octaves) == 1: # only one octave => assign to either one
    #             if octaves[0] >= 4: # >= middle C octave
    #                 # assign to right hand
    #                 right_notes = list(n for n in notes)
    #             else:
    #                 # assign to left hand
    #                 left_notes = list(n for n in notes)
    #         elif len(octaves) == 2: # two octaves => assign lower one to left, assign higher one to right
    #             lower_octave, higher_octave = min(octaves), max(octaves)
    #             # if only a small number of notes and they are close together, assign to same hand
    #             if len(notes) <= 3 and higher_octave - lower_octave == 1:
    #                 if (higher_octave + lower_octave) // 2 >= 4:
    #                     # assign to right hand
    #                     right_notes = list(n for n in notes)
    #                 else:
    #                     # assign to left hand
    #                     left_notes = list(n for n in notes)
    #             else:
    #                 left_notes = list(n for n in notes if n.note.octave == lower_octave)
    #                 right_notes = list(n for n in notes if n.note.octave == higher_octave)

    #         else:
    #             median = np.median(list(n.note.pitch.ps for n in notes))
    #             left_notes = list(n for n in notes if n.note.pitch.ps < median)
    #             remaining_notes = list(n for n in notes if n.note.pitch.ps == median)
    #             right_notes = list(n for n in notes if n.note.pitch.ps > median)

    #             max_left_note = max(n.note.pitch.ps for n in left_notes)
    #             min_right_note = min(n.note.pitch.ps for n in right_notes)

    #             if median - max_left_note < min_right_note - median:
    #                 left_notes += remaining_notes
    #             else:
    #                 right_notes += remaining_notes

    #         left_notes = sorted(left_notes, key=lambda n:n.note.pitch.ps)
    #         right_notes = sorted(right_notes, key=lambda n: n.note.pitch.ps)

    def apply(self):
        pass
        # self.apply_each(ALGORITHMS_BY_MEASURE, self.measures)
        # self.apply_each(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        # self.apply_each(ALGORITHMS_BY_OFFSET_GROUPED_NOTES, self.offset_grouped_notes)

    def apply_each(self, algorithms, source):
        source = source.items() if isinstance(source, dict) else source
        for item in source:
            for algorithm in algorithms:
                detect_func, fix_func = algorithm
                self.sites[detect_func.__name__] += detect_func(item)
                # for site in self.sites[detect_func.__name__]:
                    # fix_func(site)

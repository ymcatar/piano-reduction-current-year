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
]

ALGORITHMS_BY_OFFSET_GROUPED_NOTES = [
    (PostProcessorAlgorithms.detect_triad,
     PostProcessorAlgorithms.fix_triad),
    (PostProcessorAlgorithms.detect_too_many_concurrent_notes,
     PostProcessorAlgorithms.fix_too_many_concurrent_notes)
]


class PostProcessor(object):

    def __init__(self, score):

        self.score = deepcopy(score)
        self.score = score.toSoundingPitch()
        self.score = self.score.voicesToParts()

        # get all measures from the score
        self.measures = list(self.score.recurse(
            skipSelf=True).getElementsByClass('Measure'))

        for measure in self.measures:
            measure.removeByNotOfClass([
                music21.note.Note,
                music21.note.Rest,
                music21.chord.Chord
            ])

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
                            wappedNote = NoteWrapper(
                                note, offset, self.score, item.element)
                            self.offset_grouped_notes[offset].append(
                                wappedNote)
                    else:  # note or rest
                        note = NoteWrapper(item.element, offset, self.score)
                        self.offset_grouped_notes[offset].append(note)

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    def apply(self):
        self.apply_each(ALGORITHMS_BY_MEASURE, self.measures)
        self.apply_each(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        self.apply_each(ALGORITHMS_BY_OFFSET_GROUPED_NOTES,
                        self.offset_grouped_notes)

    def apply_each(self, algorithms, source):
        source = source.items() if isinstance(source, dict) else source
        for item in source:
            for algorithm in algorithms:
                detect_func, fix_func = algorithm
                self.sites[detect_func.__name__] += detect_func(item)
                for site in self.sites[detect_func.__name__]:
                    fix_func(site)

    def retribute_to_two_staffs(self):
        left_hand = music21.stream.Part()
        right_hand = music21.stream.Part()

        left_hand.insert(0, music21.instrument.fromString('Piano'))
        right_hand.insert(0, music21.instrument.fromString('Piano'))

        left_hand.insert(0, music21.clef.BassClef())
        right_hand.insert(0, music21.clef.TrebleClef())

        # naively assigning everything to right hand
        inserted_offset = defaultdict(lambda: False)
        for offset, group in self.offset_grouped_notes.items():
            for noteWrapper in group:
                if not noteWrapper.deleted and isNote(noteWrapper.note):
                    right_hand.insertIntoNoteOrChord(offset, noteWrapper.note)
                    inserted_offset[offset] = True
                elif noteWrapper.note.isRest and not inserted_offset[offset]:
                    right_hand.insertIntoNoteOrChord(offset, noteWrapper.note)

        result = music21.stream.Score()
        result.insert(0, right_hand)
        result.insert(0, left_hand)

        staff_group = music21.layout.StaffGroup(
            [right_hand, left_hand], name='Piano', abbreviation='Pno.',
            symbol='brace')
        staff_group.barTogether = 'yes'

        result.insert(0, staff_group)

        return result

    def show(self):
        self.score.show()

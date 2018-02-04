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

        self.score = score
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

    def show(self):
        self.score.show()

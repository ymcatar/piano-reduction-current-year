#!/usr/vin/env python3

import math
import music21
import numpy as np
from collections import defaultdict
from copy import deepcopy
from operator import itemgetter

# relative import
from util import isNote, isChord, chunks
from algorithms import PostProcessorAlgorithms
from hand_assignment import HandAssignmentAlgorithm
from note_wrapper import NoteWrapper
from multipart_reducer import MultipartReducer

# algorithm set

ALGORITHMS_HAND_ASSIGNMENT = [
    (HandAssignmentAlgorithm.start, None)
]

# ALGORITHMS_BY_MEASURE_GROUP = [
# ]

# ALGORITHMS_BY_MEASURE = [
# ]

# ALGORITHMS_BY_ONSET = [
#     (PostProcessorAlgorithms.detect_triad,
#      PostProcessorAlgorithms.fix_triad),
#     (PostProcessorAlgorithms.detect_too_many_concurrent_notes,
#      PostProcessorAlgorithms.fix_too_many_concurrent_notes)
# ]

RIGHT_HAND = 1
LEFT_HAND = 2

class PostProcessor(object):

    def __init__(self, score):

        self.score = deepcopy(score)
        self.score = self.score.toSoundingPitch()
        self.score = self.score.voicesToParts()

        # get all measures from the score
        self.measures = list(self.score.recurse(
            skipSelf=True).getElementsByClass('Measure'))

        # group measures with the same offset together
        self.grouped_measures = defaultdict(lambda: [])
        for measure in self.measures:
            self.grouped_measures[str(measure.offset)].append(measure)

        # group notes starting at the same time instance together
        self.grouped_onsets = defaultdict(lambda: [])
        for _, group in self.grouped_measures.items():
            for measure in group:
                measure = measure.stripTies(retainContainers=True, inPlace=True)
                offset_map = measure.offsetMap()
                for item in offset_map:
                    offset = measure.offset + item.offset
                    if isChord(item.element):
                        for note in item.element._notes:
                            wappedNote = NoteWrapper(note, offset, item.element)
                            self.grouped_onsets[offset].append(
                                wappedNote)
                    elif isNote(item.element):  # note or rest
                        note = NoteWrapper(item.element, offset)
                        self.grouped_onsets[offset].append(note)

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    def apply(self):
        # hand assignment
        self.apply_each(ALGORITHMS_HAND_ASSIGNMENT, self.grouped_onsets, partition_size=8)

        # self.apply_each(ALGORITHMS_BY_MEASURE, self.measures)
        # self.apply_each(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        # self.apply_each(ALGORITHMS_BY_ONSET, self.grouped_onsets)

    def apply_each(self, algorithms, source, partition_size=1):
        source = list(source.items()) if isinstance(source, dict) else source
        source = chunks(source, partition_size)
        for item in source:
            for algorithm in algorithms:
                detect_func, fix_func = algorithm
                # item = [j for i in item for j in i]
                self.sites[detect_func.__name__] += detect_func(item)
                if fix_func is not None:
                    for site in self.sites[detect_func.__name__]:
                        fix_func(site)

    def generate_piano_score(self):
        reducer = MultipartReducer(self.score)
        return reducer.reduce()

    def show(self):
        self.score.show()

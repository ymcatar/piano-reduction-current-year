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

# ALGORITHMS_BY_MEASURE_GROUP = [
# ]

# ALGORITHMS_BY_MEASURE = [
# ]

ALGORITHMS_BY_ONSET = [
    PostProcessorAlgorithms.repeated_note
]

RIGHT_HAND = 1
LEFT_HAND = 2

class PostProcessor(object):

    def __init__(self, score):

        # prepare hand assignment object
        self.hand_assignment = HandAssignmentAlgorithm()

        # prepare score
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

    def apply(self):

        # preprocess
        # self.apply_each(ALGORITHMS_BY_MEASURE, self.measures)
        # self.apply_each(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        self.apply_each(ALGORITHMS_BY_ONSET, self.grouped_onsets)

        # hand assignment
        pipeline = [
            self.hand_assignment.preassign,
            self.hand_assignment.assign,
            self.hand_assignment.postassign
        ]

        self.apply_each(pipeline, self.grouped_onsets, partition_size=8)


    def apply_each(self, algorithms, source, partition_size=1):
        source = list(source.items()) if isinstance(source, dict) else source
        source = chunks(source, partition_size)
        for item in source:
            for algorithm in algorithms:
                algorithm(item)

    def generate_piano_score(self):
        reducer = MultipartReducer(self.score)
        return reducer.reduce()

    def show(self):
        self.score.show()

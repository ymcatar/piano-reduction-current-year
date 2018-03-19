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

class PostProcessor(object):

    def __init__(self, score, verbose=False):

        self.verbose = verbose

        # prepare hand assignment object
        self.hand_assignment = HandAssignmentAlgorithm(verbose=self.verbose)

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
                            self.grouped_onsets[offset].append(wappedNote)
                    elif isNote(item.element):  # note or rest
                        note = NoteWrapper(item.element, offset)
                        self.grouped_onsets[offset].append(note)

    def apply(self):
        self.apply_each(PostProcessorAlgorithms.repeated_note, self.grouped_onsets)
        self.apply_each(self.hand_assignment.preassign, self.grouped_onsets)
        self.apply_each(self.hand_assignment.assign, self.grouped_onsets, partition_size=-1)
        self.apply_each(self.hand_assignment.postassign, self.grouped_onsets)

    def apply_each(self, algorithm, source, partition_size=1):
        source = list(source.items()) if isinstance(source, dict) else source
        source = [source] if partition_size == -1 else chunks(source, partition_size)
        for item in source:
            algorithm(item)

    def generate_piano_score(self):
        reducer = MultipartReducer(self.score)
        return reducer.reduce()

    def show(self):
        self.score.show()

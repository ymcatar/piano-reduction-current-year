#!/usr/vin/env python3

import music21
from collections import defaultdict

# relative import
from util import isNote, isChord
from algorithms import PostProcessorAlgorithms

# algorithm set

ALGORITHMS_BY_MEASURE_GROUP = [
]

ALGORITHMS_BY_MEASURE = [
    (PostProcessorAlgorithms.large_hand_movement, PostProcessorAlgorithms.fix_large_hand_movement)
]

ALGORITHMS_BY_OFFSET_GROUPED_NOTES = [
    (PostProcessorAlgorithms.concurrent_notes, PostProcessorAlgorithms.fix_concurrent_notes)
]

class PostProcessor(object):

    def __init__(self, score):

        self.score = score

        # get all measures from the score
        self.measures = list(self.score.recurse(skipSelf=True).getElementsByClass('Measure'))
        for measure in self.measures:
            measure.removeByClass(
                [music21.layout.PageLayout, music21.layout.SystemLayout]
            )

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
                    self.offset_grouped_notes[measure.offset + item.offset].append(item.element)

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    def apply(self):
        self.applyEach(ALGORITHMS_BY_MEASURE, self.measures)
        self.applyEach(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        self.applyEach(ALGORITHMS_BY_OFFSET_GROUPED_NOTES, self.offset_grouped_notes)

    def applyEach(self, algorithms, source):
        source = source.items() if isinstance(source, dict) else source
        for item in source:
            for algorithm in algorithms:
                detect_func, fix_func = algorithm
                self.sites[detect_func.__name__] += detect_func(item)
                # for site in self.sites[detect_func.__name__]:
                    # fix_func(site)

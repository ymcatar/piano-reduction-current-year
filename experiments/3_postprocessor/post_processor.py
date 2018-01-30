#!/usr/vin/env python3

import music21
from collections import defaultdict

# relative import
from util import isNote, isChord
from algorithms import PostProcessorAlgorithms

# algorithm set

ALGORITHMS_BY_MEASURE_GROUP = [
    (PostProcessorAlgorithms.concurrent_notes, PostProcessorAlgorithms.fix_concurrent_notes)
]

class PostProcessor(object):

    def __init__(self, score):

        # get all measures from the score
        self.measures = list(score.recurse().getElementsByClass('Measure'))

        # group measures with the same offset together
        self.grouped_measures = defaultdict(lambda: [])
        for measure in self.measures:
           self.grouped_measures[str(measure.offset)].append(measure)

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    def apply(self):
        for _, group in self.grouped_measures.items():
            for algorithms in ALGORITHMS_BY_MEASURE_GROUP:
                detect_func, fix_func = algorithms
                self.sites[detect_func.__name__] += detect_func(group)
                for site in self.sites[detect_func.__name__]:
                    fix_func(site)

import itertools
import music21

import numpy as np

from copy import deepcopy
from termcolor import colored
from collections import defaultdict

from util import print_vector, get_number_of_cluster

class PatternAnalyzer(object):

    def __init__(self, piano_roll, config):

        self.piano_roll = piano_roll
        self.config = config

        self.patterns = {}

    def print_piano_roll(self, piano_roll=None):

        if piano_roll is None:
            piano_roll = self.piano_roll

        for i, row in enumerate(piano_roll):
            print_vector(row, i)

    def highlight_pattern(self, patterns):

        new_piano_roll = deepcopy(self.piano_roll)
        for pattern in patterns:
            for item in pattern:
                i, j = item
                new_piano_roll[i,j] = 2
        return new_piano_roll

    def run(self):

        # triad chord pattern
        self.patterns['triads'] = self.detect_triads()
        # too many notes within the same row
        self.patterns['clusters'] = self.detect_clusters()

        # self.print_piano_roll(self.highlight_pattern(self.patterns['triads']))
        self.print_piano_roll(self.highlight_pattern(self.patterns['clusters']))

    def detect_triads(self):
        results = []
        for i, vector in enumerate(self.piano_roll):
            # look at 3 notes at a time
            notes = [ n for n, is_active in enumerate(vector) if is_active ]
            for triplet in itertools.combinations(notes, 3):
                # can be optimzed
                first, second, third = list(music21.note.Note(ps=ps) for ps in triplet)
                first_interval = music21.interval.Interval(first, second)
                second_interval = music21.interval.Interval(first, third)
                if first_interval.name in ('M3', 'm3') and second_interval.name in ('P5', 'd5', 'a5'):
                    results.append(tuple((i, j) for j in triplet))
        return results

    def detect_clusters(self):
        results = []
        for i, vector in enumerate(self.piano_roll):
            if get_number_of_cluster(vector, self.config['max_hand_span']) > 2:
                results.append(tuple((i, j) for j, is_active in enumerate(vector) if is_active))
        return results


piano_roll = np.load('result.npy')

config = {}
config['max_hand_span'] = 7

analyzer = PatternAnalyzer(piano_roll, config)
analyzer.run()
# analyzer.print_piano_roll()
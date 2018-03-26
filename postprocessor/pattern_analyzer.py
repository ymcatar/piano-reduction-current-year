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
        # broken chord pattern
        self.patterns['broken_chords'] = self.detect_broken_chords()
        # too many notes within the same row
        self.patterns['clusters'] = self.detect_clusters()
        # run of notes being hit repeatedly
        self.patterns['repeats'] = self.detect_repeats()
        # diagonal
        self.patterns['diagonals_left'] = self.detect_diagonals(direction=-1)
        self.patterns['diagonals_right'] = self.detect_diagonals(direction=+1)

        # self.print_piano_roll(self.highlight_pattern(self.patterns['triads']))
        # self.print_piano_roll(self.highlight_pattern(self.patterns['broken_chords']))
        # self.print_piano_roll(self.highlight_pattern(self.patterns['clusters']))
        # self.print_piano_roll(self.highlight_pattern(self.patterns['repeats']))
        # self.print_piano_roll(self.highlight_pattern(self.patterns['diagonals_left']))
        self.print_piano_roll(self.highlight_pattern(self.patterns['diagonals_right']))

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

    def detect_repeats(self):
        results = []
        for j, column in enumerate(self.piano_roll.T):
            for group in itertools.groupby(range(len(column)), key=lambda n: column[n]):
                is_active, items = group
                items = list(items)
                if int(is_active) == 1 and len(items) >= self.config['min_repeat_len']:
                    results.append(tuple((i, j) for i in items))
        return results

    def detect_diagonals(self, direction=+1):

        """direction: -1 = towards bottom left; +1 = towards bottom right"""
        assert direction in (-1, 1)

        search_space = list(itertools.product(
            range(1, self.config['max_diagonal_skip'] + 1),
            range(1, self.config['max_diagonal_dist'] + 1)))

        if direction == -1:
            for key, value in enumerate(search_space):
                x, y = value
                search_space[key] = (x, -y)

        height, width = self.piano_roll.shape

        length_2_diagonal = defaultdict(lambda: set())
        for i, vector in enumerate(self.piano_roll):
            for j, is_active in enumerate(vector):
                if is_active:
                    for x, y in search_space:
                        if 0 <= i + x < height and 0 <= j + y < width and self.piano_roll[i + x, j + y]:
                            length_2_diagonal[(i, j)].add((i + x, j + y))

        def get_all_diagonals(start):
            if len(length_2_diagonal[start]) == 0:
                return []
            value = []
            for end in length_2_diagonal[start]:
                temp = get_all_diagonals(end)
                if len(temp) == 0:
                    value.append([end])
                else:
                    for t in temp:
                        value.append([end] + t)
            return value

        results = []
        for start, values in deepcopy(length_2_diagonal).items():
            diagonals = get_all_diagonals(start)
            for d in diagonals:
                d = [start] + d
                if len(d) >= self.config['min_diagonal_len']:
                    results.append(d)

        return results

    def detect_broken_chords(self):
        # TODO
        results = []
        return results

# piano_roll = np.load('result.npy')

# config = {}
# config['max_hand_span'] = 7         # maximum size of a cluster
# config['min_repeat_len'] = 3        # minimum length of a vertical line
# config['min_diagonal_len'] = 4      # minimum length of a diagonal
# config['max_diagonal_dist'] = 3     # maximum allowed distance between consecutive notes within a diagonal
# config['max_diagonal_skip'] = 2     # maximum size of gap allowed within a diagonal

# analyzer = PatternAnalyzer(piano_roll, config)
# analyzer.run()

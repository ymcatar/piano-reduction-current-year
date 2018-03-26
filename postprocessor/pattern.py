import music21

import numpy as np

from termcolor import colored
from collections import defaultdict

from util import print_vector

class PatternAnalyzer(object):

    def __init__(self, piano_roll):
        self.piano_roll = piano_roll
        self.patterns = {}

    def print_piano_roll(self):
        for i, row in enumerate(piano_roll):
            print_vector(row, i)

    def run(self):
        self.patterns['triads'] = self.detect_triads()
        self.print_piano_roll()

    def detect_triads(self):
        for i, vector in enumerate(piano_roll):
            # generate pitch class statistics for each row
            pitches = defaultdict(lambda: [])
            for ps, is_active in enumerate(vector):
                if is_active:
                    pitch = music21.pitch.Pitch(ps = ps)
                    pitches[pitch.name].append(ps)
            #

piano_roll = np.load('result.npy')

analyzer = PatternAnalyzer(piano_roll)
analyzer.run()
# analyzer.print_piano_roll()
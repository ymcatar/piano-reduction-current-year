import music21

import numpy as np

from termcolor import colored
from collections import defaultdict

class PatternAnalyzer(object):

    def __init__(self, piano_roll):
        self.piano_roll = piano_roll

    def print_vector(self, i):

        def value_to_block(value):
            if value == 0:
                return '▒'
            elif value == 1:
                return '█'
            else:
                return colored('█', 'red')

        message = '{:s} {:s}'.format(
            '{:2d}'.format(i).zfill(3), # leftpad literally cures cancer
            ''.join(value_to_block(i) for i in self.piano_roll[i][12:])
        )

        print(message)

    def print_piano_roll(self):
        for i, row in enumerate(piano_roll):
            self.print_vector(i)

    def run(self):
        self.detect_triads()

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
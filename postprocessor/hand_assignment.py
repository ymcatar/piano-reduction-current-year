import math
import music21
import numpy as np

from collections import defaultdict
from termcolor import colored
class HandAssignmentAlgorithm(object):

    def __init__(self, max_hand_span=7, verbose=False):

        self.config = {}
        self.config['max_hand_span'] = max_hand_span

        self.verbose = verbose

    def preassign(self, measures):

        # concerning octaves ---------------------------------------------------

        problematic = {}

        # mark all problematic frames
        for i, item in enumerate(measures):
            offset, notes = item
            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            num_cluster = self.get_number_of_cluster(notes)
            problematic[i] = (num_cluster > 2)

        # resolve a frame if the frames before and after that frame are both okay
        for i, measure in enumerate(measures):

            if not problematic[i]:
                continue

            offset, notes = measure

            # perform pitch class statistics
            pitches = defaultdict(lambda: [])
            for n in notes:
                if not n.deleted:
                    pitches[n.note.pitch.pitchClass].append(n)

            pitches = sorted(pitches.items(), key=lambda n: len(n[1]), reverse=True)
            print(pitches)



    def assign(self, measures):

        # util functions
        def print_vector(offset, notes, vector):
            cluster_count = self.get_number_of_cluster(notes)
            message = '{:s} {:s} ({:d}) {:s}'.format(
                '{:.2f}'.format(offset).zfill(6), # leftpad literally cures cancer
                ''.join('█' if i == 1 else '▒' for i in vector[12:]),
                cluster_count,
                ', '.join(n.note.pitch.name for n in notes)
            )
            if cluster_count > 2:
                print(colored(message, 'red'))
            else:
                print(message)

        for i, measure in enumerate(measures):
            offset, notes = measure
            notes = sorted((n for n in notes if not n.deleted), key=lambda n: n.note.pitch.ps)
            pitches = sorted(math.trunc(i.note.pitch.ps) for i in notes)
            vector = [0] * 97
            for item in pitches:
                if item in range(12, 97):
                    vector[item] = 1
            if self.verbose:
                print_vector(offset, notes, vector)

        # # Cherry's algorithm, placeholder for now
        # for offset, notes in measures:

        #     notes = [n for n in notes if not n.deleted]
        #     notes = sorted(notes, key=lambda n: n.note.pitch.ps)
        #     ps_median = np.median(list(n.note.pitch.ps for n in notes))

        #     left_hand_notes = [n for n in notes if n.note.pitch.ps <= ps_median]
        #     right_hand_notes = [n for n in notes if n.note.pitch.ps > ps_median]

        #     if len(left_hand_notes) > 5:
        #         left_hand_notes = left_hand_notes[:5]

        #     if len(right_hand_notes) > 5:
        #         right_hand_notes = right_hand_notes[:5]

        #     for i, note in enumerate(left_hand_notes):
        #         note.hand = 'L'
        #         note.finger = 5 - i

        #     for i, note in enumerate(right_hand_notes):
        #         note.hand = 'R'
        #         note.finger = i + 1

    def postassign(self, measures):

        pass

    def get_number_of_cluster(self, notes, verbose=False):

        max_cluster_size = 2 * self.config['max_hand_span'] - 1
        notes = sorted(notes, key=lambda n: n.note.pitch.ps)
        ps_list = [n.note.pitch.ps for n in notes]

        if len(ps_list) == 1: # only one note => trivially one cluster
            if verbose: print(ps_list)
            return 1

        if ps_list[-1] - ps_list[0] <= max_cluster_size: # all notes are close together
            if verbose: print(ps_list)
            return 1

        # greedily expand the left cluster until it is impossible
        for i, item in enumerate(ps_list):
            if item - ps_list[0] > max_cluster_size:
                if verbose: print(str(ps_list[:i]) + ' | ', end='')
                return 1 + self.get_number_of_cluster(notes[i:], verbose=verbose)


    def cost(self, measures):

        # print(measures)
        return 0



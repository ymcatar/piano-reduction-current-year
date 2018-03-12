import math
import music21
import numpy as np

from collections import defaultdict
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
        # changed = True
        # while changed: # repeat until converge
        #     changed = False
        #     for i, item in enumerate(measures):
        #         if not problematic[i]:
        #             continue

        #         reference = []
        #         if i != 0: reference += measures[i - 1][1]
        #         if i != len(measures) - 1: reference += measures[i + 1][1]

        #         offset, curr_frame = item

    def assign(self, measures):

        # util functions
        def print_vector(notes, vector):
            print('{:s} ({:d})'.format(
                ''.join('█' if i == 1 else '▒' for i in vector),
                self.get_number_of_cluster(notes)
            ))

        for measure in measures:
            offset, notes = measure
            pitches = sorted(math.trunc(i.note.pitch.ps) for i in notes)
            vector = [0] * 96
            for item in pitches:
                vector[item] = 1
            if self.verbose:
                print_vector(notes, vector)

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



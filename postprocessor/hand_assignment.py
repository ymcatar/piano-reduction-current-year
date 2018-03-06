import music21
import numpy as np

from collections import defaultdict
class HandAssignmentAlgorithm(object):

    def __init__(self, max_hand_span=7):

        self.config = {}
        self.config['max_hand_span'] = max_hand_span

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
        changed = True
        while changed: # repeat until converge
            changed = False
            for i, item in enumerate(measures):
                if not problematic[i]:
                    continue

                reference = []
                if i != 0: reference += measures[i - 1][1]
                if i != len(measures) - 1: reference += measures[i + 1][1]

                offset, curr_frame = item

                # count = 0
                # while count < len(curr_frame) and self.get_number_of_cluster(curr_frame) > 2:

                #     # min distance from each note in current frame to any notes in either prev/next frame
                #     distances = defaultdict(lambda: [])
                #     for a in curr_frame:
                #         for b in reference:
                #             distances[a].append(b.note.pitch.ps - a.note.pitch.ps)

                #     # move the outlier up/down to the larger cluster
                #     outlier = max(distances, key=lambda n: min(abs(i) for i in distances[n]))
                #     left = [abs(n) for n in distances[outlier] if n < 0]
                #     right = [abs(n) for n in distances[outlier] if n > 0]
                #     movement = 12 if sum(left, 0) / len(left) < sum(right, 0) / len(right) else -12
                #     outlier.note.transpose(movement, inPlace=True)
                #     print(offset, 'loop')
                #     count += 1

    def assign(self, measures):

        # Cherry's algorithm, placeholder for now
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            ps_median = np.median(list(n.note.pitch.ps for n in notes))

            left_hand_notes = [n for n in notes if n.note.pitch.ps <= ps_median]
            right_hand_notes = [n for n in notes if n.note.pitch.ps > ps_median]

            if len(left_hand_notes) > 5:
                left_hand_notes = left_hand_notes[:5]

            if len(right_hand_notes) > 5:
                right_hand_notes = right_hand_notes[:5]

            for i, note in enumerate(left_hand_notes):
                note.hand = 'L'
                note.finger = 5 - i

            for i, note in enumerate(right_hand_notes):
                note.hand = 'R'
                note.finger = i + 1

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



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
            measures[i] = (offset, notes) # put back the sorted list to measures
            num_cluster = self.get_number_of_cluster(notes)
            problematic[i] = (num_cluster > 2)

        # try to resolve all problematic frame
        for i, measure in enumerate(measures):
            if not problematic[i]:
                continue

            fixed = False
            offset, notes = measure

            # if the lowest notes all have the same pitch class,
            # keep removing the lowest until two clusters remain or all related notes except the lowest are deleted
            target_class = notes[0].note.pitch.pitchClass
            for i, n in enumerate(notes[1:]):
                if n.note.pitch.pitchClass == target_class:
                    n.deleted = True
                    if self.get_number_of_cluster(notes) <= 2:
                        break

            # move on if attempt to fix succeeded
            if self.get_number_of_cluster(notes) <= 2:
                continue

            # attempts to move the lowest note up
            # (if the lowest and second lowest notes are > an octave apart)
            # notes = [n for n in notes if not n.deleted]
            # while notes[1].note.pitch.ps - notes[0].note.pitch.ps >= 12:
                # notes[0].note.transpose(music21.interval.Interval(+12), inPlace=True)
                # if self.get_number_of_cluster(notes) <= 2:
                    # break

            # attempts to move the lowest group of notes up an octave if they are > an octave apart
            notes = [n for n in notes if not n.deleted]
            note_distances = []
            for i, n in enumerate(notes):
                if n != notes[-1]:
                    note_distances.append((notes[i + 1].note.pitch.ps - n.note.pitch.ps, i))
            note_distances = sorted(note_distances, key=lambda i: (-i[0], i[1]))

            for distance, index in note_distances:
                if distance < 12.0:
                    break
                distance = math.trunc(distance)
                distance = distance - distance % 12
                for i in range(0, index + 1):
                    notes[i].note.transpose(music21.interval.Interval(distance), inPlace=True)
                if self.get_number_of_cluster(notes) <= 2:
                    continue

            # move on if attempt to fix succeeded
            if self.get_number_of_cluster(notes) <= 2:
                continue

            # FIXME: what else can I do? => remove the frame for now
            notes = [n for n in notes if not n.deleted]
            for n in notes:
                n.deleted = True

    def assign(self, measures):

        # util functions
        def print_vector(offset, notes):
            # construct the vector
            pitches = sorted(math.trunc(n.note.pitch.ps) for n in notes if not n.deleted)
            vector = [0] * 97
            for item in pitches:
                if item in range(12, 97):
                    vector[item] = 1
            # print it out
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
            if self.verbose:
                print_vector(offset, notes)

        # Cherry's algorithm, placeholder for now
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            ps_median = np.median(list(n.note.pitch.ps for n in notes))

            left_hand_notes = [n for n in notes if n.note.pitch.ps <= ps_median]
            right_hand_notes = [n for n in notes if n.note.pitch.ps > ps_median]

            # if len(left_hand_notes) > 5:
                # print(offset, 'too many left hand notes')
                # left_hand_notes = left_hand_notes[:5]

            # if len(right_hand_notes) > 5:
                # print(offset, 'too many right hand notes')
                # right_hand_notes = right_hand_notes[:5]

            for i, note in enumerate(left_hand_notes):
                note.hand = 'L'
                # note.finger = 5 - i

            for i, note in enumerate(right_hand_notes):
                note.hand = 'R'
                # note.finger = i + 1

    def postassign(self, measures):

        pass

    def get_number_of_cluster(self, notes, verbose=False):

        max_cluster_size = 2 * self.config['max_hand_span'] - 1
        notes = [n for n in notes if not n.deleted]

        if len(notes) == 0:
            return 0

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



import math
import music21
import numpy as np

from collections import defaultdict
from termcolor import colored
from util import construct_piano_roll, construct_vector, print_vector, get_number_of_cluster_from_notes

from pattern_analyzer import PatternAnalyzer
class HandAssignmentAlgorithm(object):

    def __init__(self, max_hand_span=7, verbose=False):

        self.config = {}
        self.config['max_hand_span'] = max_hand_span    # maximum size of a cluster
        self.config['min_repeat_len'] = 3               # minimum length of a vertical line
        self.config['min_diagonal_len'] = 4             # minimum length of a diagonal
        self.config['max_diagonal_dist'] = 3            # maximum allowed distance between consecutive notes within a diagonal
        self.config['max_diagonal_skip'] = 2            # maximum size of gap allowed within a diagonal

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
            num_cluster = get_number_of_cluster_from_notes(notes, self.config['max_hand_span'])
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
            for i, n in enumerate(notes):
                if i != 0 and n.note.pitch.pitchClass == target_class:
                    notes[i - 1].deleted = True
                    if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
                        break

            # move on if attempt to fix succeeded
            if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
                continue

            # attempts to move the lowest note up
            # (if the lowest and second lowest notes are > an octave apart)
            # notes = [n for n in notes if not n.deleted]
            # while notes[1].note.pitch.ps - notes[0].note.pitch.ps >= 12:
                # notes[0].note.transpose(music21.interval.Interval(+12), inPlace=True)
                # if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
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
                if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
                    continue

            # move on if attempt to fix succeeded
            if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
                continue

            # FIXME: what else can I do? => remove the frame for now
            # notes = [n for n in notes if not n.deleted]
            # for n in notes:
                # n.deleted = True

    def assign(self, measures):

        piano_roll = construct_piano_roll(measures)

        # if self.verbose:
            # for i, row in enumerate(piano_roll):
                # offset, notes = measures[i]
                # print_vector(piano_roll[i,:], i, notes, self.config['max_hand_span'])

        analyzer = PatternAnalyzer(piano_roll, self.config)
        analyzer.run()

        # Cherry's algorithm (revised)
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)

            ps_median = 60 # np.median(list(n.note.pitch.ps for n in notes))

            left_hand_notes = [n for n in notes if n.note.pitch.ps < ps_median]
            right_hand_notes = [n for n in notes if n.note.pitch.ps > ps_median]

            # assign the median to whatever closer
            median_note = [n for n in notes if n.note.pitch.ps == ps_median]
            if len(median_note) > 0:
                highest_left_notes = max(n.note.pitch.ps for n in notes)
                lowest_right_notes = min(n.note.pitch.ps for n in notes)
                if median_note[0].note.pitch.ps - lowest_right_notes < highest_left_notes - median_note[0].note.pitch.ps:
                    left_hand_notes += median_note
                else:
                    right_hand_notes += median_note

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


    def cost(self, measures):

        # print(measures)
        return 0



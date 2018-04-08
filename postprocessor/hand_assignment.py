import math
import curses
import music21
import traceback
import numpy as np

from copy import deepcopy
from termcolor import colored
from collections import defaultdict
from random import randint, shuffle

from util import \
    construct_piano_roll, construct_vector, str_vector, \
    get_number_of_cluster_from_notes

from pattern_analyzer import PatternAnalyzer
from hand_assignment_visualizer import HandAssignmentVisualizer

MIDDLE_C = 60


class HandAssignment(object):
    def __init__(self, max_hand_span=7, verbose=False):

        self.config = {}

        # maximum size of a cluster
        self.config['max_hand_span'] = max_hand_span

        # minimum length of a vertical line
        self.config['min_repeat_len'] = 3

        # minimum length of a diagonal
        self.config['min_diagonal_len'] = 4

        # maximum allowed distance between consecutive notes within a diagonal
        self.config['max_diagonal_dist'] = 3

        # maximum size of gap allowed within a diagonal
        self.config['max_diagonal_skip'] = 2

        self.verbose = verbose

        if self.verbose:
            self.visualizer = HandAssignmentVisualizer(self)
        else:
            self.visualizer = None

    def preassign(self, measures):

        # concerning octaves ---------------------------------------------------
        problematic = {}

        # mark all problematic frames
        for i, item in enumerate(measures):
            offset, notes = item
            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            measures[i] = (offset,
                           notes)  # put back the sorted list to measures
            num_cluster = get_number_of_cluster_from_notes(
                notes, self.config['max_hand_span'])
            problematic[i] = (num_cluster > 2)

        # try to resolve all problematic frame
        for i, measure in enumerate(measures):
            if not problematic[i]:
                continue

            offset, notes = measure

            # if the lowest notes all have the same pitch class,
            # keep removing the lowest until two clusters remain
            # or all related notes except the lowest are deleted
            target_class = notes[0].note.pitch.pitchClass
            for i, n in enumerate(notes):
                if i != 0 and n.note.pitch.pitchClass == target_class:
                    notes[i - 1].deleted = True
                    if get_number_of_cluster_from_notes(
                            notes, self.config['max_hand_span']) <= 2:
                        break

            # move on if attempt to fix succeeded
            if get_number_of_cluster_from_notes(
                    notes, self.config['max_hand_span']) <= 2:
                continue

            # attempts to move the lowest note up
            # (if the lowest and second lowest notes are > an octave apart)
            # notes = [n for n in notes if not n.deleted]
            # while notes[1].note.pitch.ps - notes[0].note.pitch.ps >= 12:
            # notes[0].note.transpose(music21.interval.Interval(+12), inPlace=True)
            # if get_number_of_cluster_from_notes(notes, self.config['max_hand_span']) <= 2:
            # break

            # attempts to move the lowest group of notes up an octave
            # if they are > an octave apart
            notes = [n for n in notes if not n.deleted]
            note_distances = []
            for i, n in enumerate(notes):
                if n != notes[-1]:
                    note_distances.append(
                        (notes[i + 1].note.pitch.ps - n.note.pitch.ps, i))
            note_distances = sorted(
                note_distances, key=lambda i: (-i[0], i[1]))

            for distance, index in note_distances:
                if distance < 12.0:
                    break
                distance = math.trunc(distance)
                distance = distance - distance % 12
                for i in range(0, index + 1):
                    notes[i].note.transpose(
                        music21.interval.Interval(distance), inPlace=True)
                if get_number_of_cluster_from_notes(
                        notes, self.config['max_hand_span']) <= 2:
                    continue

            # move on if attempt to fix succeeded
            if get_number_of_cluster_from_notes(
                    notes, self.config['max_hand_span']) <= 2:
                continue

            # FIXME: what else can I do? => remove the frame for now
            # notes = [n for n in notes if not n.deleted]
            # for n in notes:
            # n.deleted = True

    def split_to_hands(self, notes):
        '''split a list of notes to left hand part and right hand part'''

        ps_list = sorted(list(n.note.pitch.ps for n in notes))

        left_hand_notes = []
        right_hand_notes = []

        max_note_distance = 2 * self.config['max_hand_span'] - 1
        # all notes are close together => assign to same hand
        if ps_list[-1] - ps_list[0] <= max_note_distance:
            if ps_list[0] < MIDDLE_C:
                left_hand_notes = notes
            else:
                right_hand_notes = notes
        else:
            # greedily expand the left cluster until it is impossible
            for i, item in enumerate(ps_list):
                if item - ps_list[0] <= max_note_distance:
                    left_hand_notes.append(notes[i])
                else:
                    right_hand_notes.append(notes[i])

        return left_hand_notes, right_hand_notes

    def assign(self, measures):

        # piano_roll = construct_piano_roll(measures)
        # analyzer = PatternAnalyzer(piano_roll, self.config)
        # analyzer.run()

        # used to give an naive assignment
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)

            left_hand_notes, right_hand_notes = self.split_to_hands(notes)

            if len(left_hand_notes) > 5:
                print(offset, 'too many left hand notes')
                left_hand_notes = left_hand_notes[:5]

            if len(right_hand_notes) > 5:
                print(offset, 'too many right hand notes')
                right_hand_notes = right_hand_notes[:5]

            for i, note in enumerate(reversed(left_hand_notes)):
                note.hand = 'L'
                note.finger = i + 1

            for i, note in enumerate(right_hand_notes):
                note.hand = 'R'
                note.finger = i + 1

        try:

            self.global_optimize(measures)

        except Exception as e:

            if self.visualizer is not None:
                self.visualizer.end_screen()

            traceback.print_exc()
            exit(1)

    def postassign(self, measures):

        pass

    def cost_model(self, prev, curr, next):

        # record where the fingers are
        prev_fingers, curr_fingers = {}, {}

        for n in prev:
            if n.hand and n.finger:
                finger = n.finger if n.hand == 'L' else n.finger + 5
                prev_fingers[finger] = n

        for n in curr:
            if n.hand and n.finger:
                finger = n.finger if n.hand == 'L' else n.finger + 5
                curr_fingers[finger] = n

        # record finger position change
        total_movement = 0
        total_new_placement = 0

        for finger in range(1, 11):

            # current finger are in both prev & curr frame => movement cost
            if finger in prev_fingers and finger in curr_fingers:
                prev_ps = prev_fingers[finger].note.pitch.ps
                curr_ps = curr_fingers[finger].note.pitch.ps
                total_movement += abs(curr_ps - prev_ps)

            # current finger are only in current frame => new placement cost
            if finger not in prev_fingers and finger in curr_fingers:

                search_range = range(1, 6) \
                    if finger in range(1, 6) else range(6, 11)

                prev = [
                    n.note.pitch.ps for key, n in prev_fingers.items()
                    if key in search_range
                ]

                curr_ps = curr_fingers[finger].note.pitch.ps

                if len(prev) == 0:
                    prev_ps = curr_ps
                else:
                    prev_ps = np.median(prev)

                total_new_placement += abs(curr_ps - prev_ps)

        # total cost
        return total_movement + total_new_placement

    def get_cost_array(self, notes):

        costs = []
        for triplet in zip(notes, notes[1:], notes[2:]):
            prev_item, curr_item, next_item = triplet
            prev_offset, prev_frame = prev_item
            curr_offset, curr_frame = curr_item
            next_offset, next_frame = next_item
            cost = self.cost_model(prev_frame, curr_frame, next_frame)
            costs.append(cost)
        return costs

    def get_total_cost(self, notes):

        costs = self.get_cost_array(notes)
        return sum(costs, 0)

    def global_optimize(self, measures):

        if self.verbose:
            self.visualizer.init_screen()

        hasStopped = False

        count = 0

        while count < 10 and not hasStopped:

            count += 1
            WINDOW_SIZE = 10

            for i in range(len(measures) - WINDOW_SIZE):

                window = measures[i:i + WINDOW_SIZE]

                costs = self.get_cost_array(window)

                max_cost_index = max(
                    range(len(costs)), key=lambda n: costs[n]) + i

                # optimize the assignment
                prev_offset, prev_frame = measures[max_cost_index - 1]
                curr_offset, curr_frame = measures[max_cost_index]
                next_offset, next_frame = measures[max_cost_index + 1]

                self.local_optimize(measures, max_cost_index, prev_frame,
                                    curr_frame, next_frame)

                if self.verbose:
                    if self.visualizer.print_fingering(
                            measures, highlight=curr_offset):
                        hasStopped = True
                        break

            if not self.verbose:
                print('Optimizing piano score - pass', count, '...')

        if self.verbose:
            self.visualizer.end_screen()

        return 0

    def local_optimize(self, measures, index, prev, curr, next):

        # save the current row assignment
        copy = deepcopy(measures[index])
        prev_total_cost = self.get_total_cost(measures)

        for i in range(10):

            # FIXME: naive random
            fingers = list(range(1, 10))
            shuffle(fingers)

            for i, n in enumerate(curr[:min(len(curr), 9)]):
                if 1 <= fingers[i] <= 5:
                    n.hand = 'L'
                    n.finger = fingers[i]
                elif 6 <= fingers[i] <= 10:
                    n.hand = 'R'
                    n.finger = fingers[i] - 5

            # if total cost is lowered
            if self.get_total_cost(measures) > prev_total_cost:
                measures[index] = copy  # revert
            else:
                break

        if i == 10:

            # no finger assignment could lower the cost => remove notes
            for n in curr:
                n.hand = None
                n.finger = None

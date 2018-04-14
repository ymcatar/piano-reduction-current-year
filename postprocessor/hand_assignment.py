import math
import curses
import logging
import music21
import traceback
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

from collections import defaultdict
from algorithms import PostProcessorAlgorithms
from itertools import combinations
from random import randint, shuffle
from expiringdict import ExpiringDict

from util import \
    construct_piano_roll, construct_vector, str_vector, \
    get_number_of_cluster_from_notes, split_to_hands

from pattern_analyzer import PatternAnalyzer
from hand_assignment_cost_model import cost_model, get_cost_array, get_total_cost, get_windowed_cost
from hand_assignment_visualizer import HandAssignmentVisualizer

sns.set()


class HandAssignment(object):

    def __init__(self, max_hand_span=7, verbose=False, show_plot=False):

        # configure logger

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        fmt = '%(asctime)s %(levelname)s: %(message)s'
        formatter = logging.Formatter(fmt, datefmt='%H:%M:%S')
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

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
        self.show_plot = show_plot

        if self.verbose:
            self.visualizer = HandAssignmentVisualizer(self)
        else:
            self.visualizer = None

    def preassign(self, measures):

        PostProcessorAlgorithms.repeated_note(measures)

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

        self.preassign_initial_assignment(measures)

    def preassign_initial_assignment(self, measures):

        piano_roll = construct_piano_roll(measures)
        analyzer = PatternAnalyzer(piano_roll, self.config)
        analyzer.run()

        # used to give an naive assignment
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)

            left_hand_notes, right_hand_notes = split_to_hands(
                notes, self.config['max_hand_span'])

            if len(left_hand_notes) > 5:
                self.logger.info('too many left hand notes at ' + str(offset))
                left_hand_notes = left_hand_notes[:5]

            if len(right_hand_notes) > 5:
                self.logger.info('too many right hand notes at ' + str(offset))
                right_hand_notes = list(reversed(right_hand_notes))
                right_hand_notes = right_hand_notes[:5]
                right_hand_notes = list(reversed(right_hand_notes))

            for i, note in enumerate(reversed(left_hand_notes)):
                note.hand = 'L'
                note.finger = i + 1

            for i, note in enumerate(right_hand_notes):
                note.hand = 'R'
                note.finger = i + 1

    def assign(self, measures):

        try:

            self.assign_global_optimize(measures)

        except Exception:

            if self.visualizer is not None:
                self.visualizer.end_screen()

            traceback.print_exc()
            exit(1)

    def assign_global_optimize(self, measures):

        # optimization cache
        cache = ExpiringDict(max_len=1000, max_age_seconds=100)

        if self.verbose:
            self.visualizer.init_screen()

        has_stopped = False

        count = 0

        if self.show_plot:
            plt.ion()

        while not has_stopped:

            count += 1

            self.logger.info('=== Pass ' + str(count) + ' ===')

            costs = list((v, k + 1)
                         for k, v in enumerate(get_cost_array(measures)))

            costs = sorted(costs, reverse=True)
            mean = np.mean(list(i[0] for i in costs))
            sd = np.std(list(i[0] for i in costs))

            if self.show_plot:
                sns.distplot(list(i[0] for i in costs), hist=False)
                plt.ylim(0, 0.2)
                plt.draw()
                plt.pause(0.001)

            self.logger.info('> Mean: {:f} / S.D.: {:f}'.format(mean, sd))

            for i, item in enumerate(costs):
                cost, index = item
                costs[i] = ((cost - mean) / sd, index)

            costs = [i for i in costs if i[0] >= 1.0]

            some_succeeded = False

            for _, max_cost_index in costs:

                # optimize the assignment
                prev_offset, prev_frame = measures[max_cost_index - 1]
                curr_offset, curr_frame = measures[max_cost_index]
                next_offset, next_frame = measures[max_cost_index + 1]

                cache_key = str_vector(
                    construct_vector(curr_frame), max_cost_index)

                if cache_key not in cache:
                    result = self.assign_local_optimize(measures, max_cost_index,
                                                        prev_frame, curr_frame,
                                                        next_frame)
                    some_succeeded |= result
                    if not result:
                        cache[cache_key] = False
                # else:
                    # print('cache hit')

                if self.verbose:
                    if self.visualizer.print_fingering(
                            measures, highlight=curr_offset):
                        has_stopped = True
                        break

            if not some_succeeded:

                self.logger.info('No more optimization needed/possible.')
                has_stopped = True
                break

        if self.verbose:
            self.visualizer.end_screen()

        return 0

    def assign_local_optimize(self, measures, index, prev, curr, next):

        def get_assignment_object(frame):
            hands, fingers = {}, {}
            offset, notes = frame
            for n in notes:
                hands[n] = n.hand
                fingers[n] = n.finger
            return hands, fingers

        def set_assignment_object(frame, hands, fingers):
            offset, notes = frame
            for n in notes:
                n.hand = hands[n]
                n.finger = fingers[n]
            return (offset, notes)

        # backup the current assignment
        original_frame_cost = cost_model(
            prev, curr, next, max_hand_span=self.config['max_hand_span'])
        original_cost = get_total_cost(measures)
        original_assignment = get_assignment_object(measures[index])

        # try to reassign fingers
        left_hand_notes, right_hand_notes = split_to_hands(
            curr, self.config['max_hand_span'])

        best_assignment = None
        best_cost = original_frame_cost

        # loop through all possible finger assignment
        # FIXME: handle frame with only left hand notes / right hand notes

        has_found = False

        for lefts in combinations(range(1, 6), len(left_hand_notes)):

            if has_found:
                break

            for rights in combinations(range(1, 6), len(right_hand_notes)):

                # print(lefts, rights)

                for i, n in enumerate(left_hand_notes):
                    n.hand = 'L'
                    n.finger = lefts[i]

                for i, n in enumerate(right_hand_notes):
                    n.hand = 'R'
                    n.finger = rights[i]

                # evaluate if the new assignment is better
                curr_cost = get_windowed_cost(measures, index)

                if curr_cost < best_cost:
                    best_assignment = get_assignment_object(measures[index])
                    best_cost = curr_cost
                    has_found = True
                    break

        # if total cost is lowered
        if best_assignment is not None and best_cost < original_cost:

            measures[index] = set_assignment_object(measures[index],
                                                    *best_assignment)

            new_frame_cost = cost_model(
                prev, curr, next, max_hand_span=self.config['max_hand_span'])
            self.logger.info(
                'Optimization succeed\t({:d})\t{:3.0f} => {:3.0f}, by reassigning fingers'.
                format(index, original_frame_cost, new_frame_cost))

            return True

        else:

            if best_cost is not None:
                # revert
                measures[index] = set_assignment_object(
                    measures[index], *original_assignment)

            # cannot improve the finger assignment anymore
            # => remove one note that lead to highest decrease in cost
            notes = [
                n for n in curr if not n.deleted and n.hand and n.finger
            ]

            notes = sorted(notes, key=lambda n: n.note.pitch.ps)

            if len(notes) >= 3:

                lowest_cost = original_frame_cost
                lowest_deletion = None

                # FIXME: might want to preserve bassline + highest note

                for n in notes[1:-1]:
                    n.deleted = True
                    new_cost = cost_model(
                        prev, curr, next, max_hand_span=self.config['max_hand_span'])
                    if new_cost < lowest_cost:
                        lowest_cost = new_cost
                        lowest_deletion = n
                    n.deleted = False

                if lowest_deletion is not None:
                    lowest_deletion.deleted = True
                    lowest_deletion.hand = None
                    lowest_deletion.finger = None

                    new_frame_cost = cost_model(
                        prev, curr, next, max_hand_span=self.config['max_hand_span'])

                    self.logger.info(
                        'Optimization succeed \t({:d})\t{:3.0f} => {:3.0f}, deleting {:s}.'.
                        format(index, original_frame_cost, new_frame_cost,
                               str(lowest_deletion)))
                    return True
                else:
                    self.logger.info(
                        'Optimization failed \t({:d})\t{:3.0f}'.format(
                            index, original_frame_cost))
                    return False

            else:

                self.logger.info(
                    'Optimization failed \t({:d})\t{:3.0f}'.format(
                        index, original_frame_cost))

                return False

        return False

    def postassign(self, measures):

        PostProcessorAlgorithms.repeated_note(measures)

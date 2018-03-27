import math
import curses
import music21
import numpy as np

from random import randint, shuffle
from collections import defaultdict
from termcolor import colored
from util import construct_piano_roll, construct_vector, str_vector, get_number_of_cluster_from_notes

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

        if self.verbose:
            self.stdscr = None
            self.stdscr_height = None

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

        # analyzer = PatternAnalyzer(piano_roll, self.config)
        # analyzer.run()

        # Cherry's algorithm (revised): used to give an initial assignment
        for offset, notes in measures:

            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)

            ps_median = np.median(list(n.note.pitch.ps for n in notes))

            left_hand_notes = [n for n in notes if n.note.pitch.ps < ps_median]
            right_hand_notes = [n for n in notes if n.note.pitch.ps > ps_median]

            # assign the median to whatever closer
            median_note = [n for n in notes if n.note.pitch.ps == ps_median]
            if len(median_note) > 0:
                highest_left_notes = max(n.note.pitch.ps for n in left_hand_notes) if len(left_hand_notes) else 0
                lowest_right_notes = min(n.note.pitch.ps for n in right_hand_notes) if len(right_hand_notes) else 0
                if median_note[0].note.pitch.ps - lowest_right_notes < highest_left_notes - median_note[0].note.pitch.ps:
                    left_hand_notes += median_note
                else:
                    right_hand_notes += median_note

            left_hand_notes = sorted(left_hand_notes, key=lambda n: n.note.pitch.ps)
            right_hand_notes = sorted(right_hand_notes, key=lambda n: n.note.pitch.ps)

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

        self.optimize_fingering(measures)

    def postassign(self, measures):

        pass

    def cost_model(self, prev, curr, next):

        # record where the fingers are
        prev_fingers, curr_fingers, next_fingers = {}, {}, {}
        for n in prev:
            if n.hand and n.finger:
                finger = n.finger if n.hand == 'L' else n.finger + 5
                prev_fingers[finger] = n
        for n in curr:
            if n.hand and n.finger:
                finger = n.finger if n.hand == 'L' else n.finger + 5
                curr_fingers[finger] = n
        for n in next:
            if n.hand and n.finger:
                finger = n.finger if n.hand == 'L' else n.finger + 5
                next_fingers[finger] = n

        # record finger position change
        total_movement = 0
        total_new_placement = 0
        for finger in range(1, 11):
            # current finger are in both curr & next frame => movement cost
            if finger in curr_fingers and finger in next_fingers:
                curr_ps = curr_fingers[finger].note.pitch.ps
                next_ps = next_fingers[finger].note.pitch.ps
                total_movement += abs(next_ps - curr_ps)
            # current finger are only in current frame => new placement cost
            if finger not in prev_fingers and finger in curr_fingers:
                total_new_placement += 1

        # total cost
        return total_movement + total_new_placement

    def optimize_fingering(self, measures):

        if self.verbose:
            self.init_screen()

        while True:

            items = [i[1] for i in measures]

            # optimize fingering
            costs = []
            for prev_frame, curr_frame, next_frame in zip(items, items[1:], items[2:]):
                cost = self.cost_model(prev_frame, curr_frame, next_frame)
                costs.append(cost)

            max_cost_index = max(range(len(costs)), key=lambda n: costs[n])

            if self.verbose:
                if self.print_fingering(measures):
                    break

        if self.verbose:
            self.end_screen()

        return 0

    # output releated methods

    def init_screen(self):

        self.prev_notes = {}
        self.start_line = 0
        self.stdscr = curses.initscr()
        self.stdscr_height = self.stdscr.getmaxyx()[0]
        self.stdscr_width = self.stdscr.getmaxyx()[1]

        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        curses.noecho() # disable screen echoing
        curses.cbreak() # accept key press
        curses.curs_set(0) # hide the cursoe

        self.stdscr.keypad(True) # accept directional key

    def end_screen(self):

        curses.endwin()
        self.stdscr.keypad(False)

        curses.curs_set(2)
        curses.nocbreak()
        curses.echo()

        self.stdscr = None
        self.start_line = 0
        self.prev_notes = {}

    def print_fingering(self, measures):

        self.stdscr.clear()

        is_changed = True

        while True:

            if is_changed:

                for i, item in enumerate(measures[self.start_line:self.start_line + self.stdscr_height]):

                    offset, notes = item

                    cost = None
                    if item != measures[0] and item != measures[-1]: # has previous & next frame
                        cost = self.cost_model(
                            measures[self.start_line + i - 1][1],
                            notes,
                            measures[self.start_line + i + 1][1])

                    message = self.str_frame(offset, notes).ljust(self.stdscr_width - 10)

                    if offset in self.prev_notes and self.prev_notes[offset] != str(notes):
                        self.stdscr.addstr(i, 0, message, curses.color_pair(1))
                        self.prev_notes[offset] = str(notes)
                    else:
                        self.stdscr.addstr(i, 0, message)

                    if cost is not None:
                        self.stdscr.addstr(i, self.stdscr_width - 10, '<{:.0f}>'.format(cost).ljust(5))

            isChanged = False

            try:
                key = self.stdscr.getkey()
                if key == 'KEY_UP':
                    if self.start_line > 0:
                        self.start_line -= 1
                    is_changed = True
                elif key == 'KEY_DOWN':
                    if self.start_line < len(measures) - self.stdscr_height:
                        self.start_line += 1
                    is_changed = True
                elif key == 'KEY_RIGHT':
                    break
                elif key == 'q':
                    return True

            except KeyboardInterrupt:
                return True

            except Exception as e:
                # No input
                pass

            self.stdscr.refresh()

        return False

    def str_frame(self, offset, notes):

        vector = [0] * 97
        for n in notes:
            if not n.deleted:
                if n.hand and n.finger:
                    vector[math.trunc(n.note.pitch.ps)] = n.finger if n.hand == 'L' else 5 + n.finger
                else:
                    vector[math.trunc(n.note.pitch.ps)] = 11

        def value_to_func(value):
            value = int(value)
            if value == 0:
                return ' '
            elif 1 <= value <= 5:
                return str(['①', '②', '③', '④', '⑤'][value - 1])
            elif 6 <= value <= 10:
                return str(['❶', '❷', '❸', '❹', '❺'][value - 6])
            elif value == 11:
                quit()
                return '-'

        return str_vector(
            vector, offset, notes=notes,
            max_hand_span=self.config['max_hand_span'],
            func=value_to_func)

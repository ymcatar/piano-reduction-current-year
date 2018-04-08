import math
import curses
import signal
import traceback

from util import str_vector


class HandAssignmentVisualizer(object):
    def __init__(self, context):

        self.context = context
        self.stdscr = None
        self.stdscr_height = None
        self.start_line = 0

    def init_screen(self):

        self.start_line = 0
        self.stdscr = curses.initscr()
        self.stdscr_height = self.stdscr.getmaxyx()[0]
        self.stdscr_width = self.stdscr.getmaxyx()[1]

        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        curses.noecho()  # disable screen echoing
        curses.cbreak()  # accept key press
        curses.curs_set(0)  # hide the cursoe

        self.stdscr.keypad(True)  # accept directional key

        def on_exit(a, b):
            self.end_screen()
            exit(1)

        signal.signal(signal.SIGINT, on_exit)

    def end_screen(self):

        curses.echo()  # disable screen echoing
        curses.nocbreak()  # accept key press
        curses.curs_set(2)  # hide the cursoe
        curses.endwin()

        self.stdscr = None
        self.start_line = 0

    def print_fingering(self, measures, highlight=None):

        is_changed = True

        if highlight is not None:
            offsets = [offset for offset, notes in measures]
            self.start_line = offsets.index(highlight) - self.stdscr_height // 2
            self.start_line = max(0, self.start_line)
            self.start_line = min(len(measures), self.start_line)

        while True:

            if is_changed:

                is_changed = False
                self.stdscr.clear()

                for i, item in enumerate(measures[
                        self.start_line:self.start_line + self.stdscr_height]):

                    offset, notes = item

                    cost = None
                    if item != measures[0] and item != measures[-1]:
                        cost = self.context.cost_model(
                            measures[self.start_line + i - 1][1], notes,
                            measures[self.start_line + i + 1][1])

                    message = self.str_frame(
                        offset, notes).ljust(self.stdscr_width - 10)

                    if offset == highlight:
                        self.stdscr.addstr(i, 0, message, curses.color_pair(1))
                    else:
                        self.stdscr.addstr(i, 0, message)

                    if cost is not None:
                        if offset == highlight:
                            self.stdscr.addstr(
                                i, self.stdscr_width - 10,
                                '<{:.0f}>'.format(cost).ljust(5),
                                curses.color_pair(1))
                        else:
                            self.stdscr.addstr(
                                i, self.stdscr_width - 10,
                                '<{:.0f}>'.format(cost).ljust(5))

                self.stdscr.refresh()

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
            except Exception as e:
                # No input
                pass

        return False

    def str_frame(self, offset, notes):

        vector = [0] * 97
        for n in notes:
            if not n.deleted and n.hand and n.finger:
                vector[math.trunc(
                    n.note.pitch.ps
                )] = n.finger if n.hand == 'L' else 5 + n.finger
            else:
                vector[math.trunc(n.note.pitch.ps)] = 11

        def value_to_func(value):
            value = int(value)
            if value == 0:
                return ' '
            elif 1 <= value <= 5:
                return str(['a', 'b', 'c', 'd', 'e'][value - 1])
            elif 6 <= value <= 10:
                return str(['1', '2', '3', '4', '5'][value - 6])
            elif value == 11:
                return '-'

        return str_vector(
            vector,
            offset,
            notes=notes,
            max_hand_span=self.context.config['max_hand_span'],
            func=value_to_func)

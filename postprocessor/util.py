import math
import music21
import numpy as np

from termcolor import colored

MIDDLE_C = 60


def isNote(item):
    return isinstance(item, music21.note.Note)


def isChord(item):
    return isinstance(item, music21.chord.Chord)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def construct_vector(notes):
    pitches = sorted(
        math.trunc(n.note.pitch.ps) for n in notes if not n.deleted)
    vector = [0] * 97
    for item in pitches:
        if item in range(12, 97):
            vector[item] = 1
    return vector


def construct_piano_roll(measures):
    piano_roll = np.zeros((len(measures), 97))
    for i, measure in enumerate(measures):
        offset, notes = measure
        notes = sorted(
            (n for n in notes if not n.deleted), key=lambda n: n.note.pitch.ps)
        piano_roll[i, :] = construct_vector(notes)
    return piano_roll


def str_vector(vector, offset, notes=None, max_hand_span=7, func=None):

    def value_to_block(value):
        if value == 0:
            return '▒'
        elif value == 1:
            return '█'
        else:
            return colored('█', 'blue')

    if func is None:
        func = value_to_block

    cluster_count = get_number_of_cluster(vector, max_hand_span)
    cluster_count = '(' + str(cluster_count) + ')'

    message = '{:s} {:s} {:s}'.format(
        '{:.2f}'.format(offset).zfill(6), ''.join(
            func(i) for i in vector[12:]), cluster_count)

    if notes is not None:
        notes = [n for n in notes if not n.deleted]
        message += ' '
        message += ', '.join(n.note.pitch.name for n in notes)

    return message


def get_number_of_cluster(vector, max_hand_span):

    max_cluster_size = 2 * max_hand_span - 1
    ps_list = [
        i for i, is_active in enumerate(vector)
        if int(is_active) not in (0, 11)
    ]

    if len(ps_list) == 0:  # no note => trivially no cluster
        return 0

    if len(ps_list) == 1:  # only one note => trivially one cluster
        return 1

    # all notes are close together
    if ps_list[-1] - ps_list[0] <= max_cluster_size:
        return 1

    # greedily expand the left cluster until it is impossible
    for i, item in enumerate(ps_list):
        if item - ps_list[0] > max_cluster_size:
            return 1 + get_number_of_cluster(vector[item:], max_hand_span)


def get_number_of_cluster_from_notes(notes, max_hand_span):
    vector = construct_vector(notes)
    return get_number_of_cluster(vector, max_hand_span)


def split_to_hands(notes, max_hand_span):
    '''split a list of notes to left hand part and right hand part'''

    notes = [n for n in notes if not n.deleted]

    # no notes in current frame
    if len(notes) == 0:
        return [], []

    ps_list = sorted(list(n.note.pitch.ps for n in notes))

    left_hand_notes = []
    right_hand_notes = []

    # all notes are close together => assign to same hand
    if ps_list[-1] - ps_list[0] <= max_hand_span:
        if ps_list[0] < MIDDLE_C:
            left_hand_notes = notes
        else:
            right_hand_notes = notes
    else:
        # greedily expand the left cluster until it is impossible
        for i, item in enumerate(ps_list):
            if item - ps_list[0] <= max_hand_span:
                left_hand_notes.append(notes[i])
            else:
                right_hand_notes.append(notes[i])

    return left_hand_notes, right_hand_notes


def get_note_dist(a, b):

    first = music21.note.Note(ps=a)
    second = music21.note.Note(ps=b)
    interval = music21.interval.Interval(first, second)
    return abs(interval.semitones) / 2.0
import math
import music21
import numpy as np

from termcolor import colored

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def construct_vector(notes):
    pitches = sorted(math.trunc(n.note.pitch.ps) for n in notes if not n.deleted)
    vector = [0] * 97
    for item in pitches:
        if item in range(12, 97):
            vector[item] = 1
    return vector

def construct_piano_roll(measures):
    piano_roll = np.zeros((len(measures), 97))
    for i, measure in enumerate(measures):
        offset, notes = measure
        notes = sorted((n for n in notes if not n.deleted), key=lambda n: n.note.pitch.ps)
        piano_roll[i,:] = construct_vector(notes)
    return piano_roll

def print_vector(vector, offset, notes=None, max_hand_span=7):

    def value_to_block(value):
        if value == 0:
            return '▒'
        elif value == 1:
            return '█'
        else:
            return colored('█', 'blue')

    cluster_count = get_number_of_cluster(vector, max_hand_span)
    message = '{:s} {:s} ({:d})'.format(
        '{:.2f}'.format(offset).zfill(6),
        ''.join(value_to_block(i) for i in vector[12:]),
        cluster_count
    )

    if notes is not None:
        notes = [n for n in notes if not n.deleted]
        message += ' '
        message += ', '.join(n.note.pitch.name for n in notes)

    if cluster_count > 2:
        print(colored(message, 'red'))
    else:
        print(message)

def get_number_of_cluster(vector, max_hand_span):

    max_cluster_size = 2 * max_hand_span - 1
    ps_list = [i for i, is_active in enumerate(vector) if int(is_active) == 1]

    if len(ps_list) == 0: # no note => trivially no cluster
        return 0

    if len(ps_list) == 1: # only one note => trivially one cluster
        return 1

    if ps_list[-1] - ps_list[0] <= max_cluster_size: # all notes are close together
        return 1

    # greedily expand the left cluster until it is impossible
    for i, item in enumerate(ps_list):
        if item - ps_list[0] > max_cluster_size:
            return 1 + get_number_of_cluster(vector[item:], max_hand_span)

def get_number_of_cluster_from_notes(notes, max_hand_span):
    vector = construct_vector(notes)
    return get_number_of_cluster(vector, max_hand_span)
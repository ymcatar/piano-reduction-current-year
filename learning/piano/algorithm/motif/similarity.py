#!/usr/bin/env python3

import music21
import os
import sys
import editdistance
from intervaltree import Interval, IntervalTree

from .algorithms import MotifAnalyzerAlgorithms


def normalize_sequences(first, second):
    results = []
    mapping = {}
    curr_index = 0
    for character in first + second:
        if character not in mapping:
            mapping[character] = chr(ord('a') + curr_index)
            curr_index += 1
        results.append(mapping[character])
    return ''.join(results[:len(first)]), ''.join(results[len(first):])


# most = > 50%
def most_has_overlap(first, second):
    first_intervals = [Interval(*i) for i in first]
    second_intervals = [Interval(*i) for i in second]

    count = 0
    tree = IntervalTree(first_intervals)
    for interval in second_intervals:
        if tree.search(*interval):
            count += 1
    if count / (len(second_intervals) * 2) > 0.5:
        return True

    count = 0
    tree = IntervalTree(second_intervals)
    for interval in first_intervals:
        if tree.search(*interval):
            count += 1
    if count / (len(first_intervals) * 2) > 0.5:
        return True

    return False

# determine similarity of notegram groups
def get_dissimilarity(first, second):
    first_offsets = [(notegram.get_note_offset_by_index(
        0), notegram.get_note_offset_by_index(-1)) for notegram in first]

    second_offsets = [(notegram.get_note_offset_by_index(
        0), notegram.get_note_offset_by_index(-1)) for notegram in second]

    if most_has_overlap(first_offsets, second_offsets):
        return 0 # must merge

    # get a single notegram to represent the whole group
    first_note_list = first[0].get_note_list()
    second_note_list = second[0].get_note_list()
    diff_in_len = abs(len(first_note_list) - len(second_note_list))

    sequence_func_list = [
        (MotifAnalyzerAlgorithms.note_sequence_func, 1),
        (MotifAnalyzerAlgorithms.rhythm_sequence_func, 1),
        (MotifAnalyzerAlgorithms.note_contour_sequence_func, 2),
        (MotifAnalyzerAlgorithms.notename_transition_sequence_func, 2),
        (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, 2),
    ]

    score = []
    for item in sequence_func_list:
        sequence_func, multplier = item
        first_sequence = sequence_func(first_note_list)
        second_sequence = sequence_func(second_note_list)
        first_sequence, second_sequence = normalize_sequences(
            first_sequence, second_sequence)
        score.append((editdistance.eval(
            first_sequence, second_sequence)) * multplier)

    # remove the top dissimilar feature, not a good idea it seems
    # score.remove(max(score))

    # return sum((i for i in score), 0) # Manhatten distance
    # return 1.0 / sum((1.0 / (i + 1) for i in score), 0.0)
    return sum((i ** 2 for i in score), 0)  # squared sum
    # return sum((i ** 0.5 for i in score), 0) ** 2  # variation of Euclidean distance

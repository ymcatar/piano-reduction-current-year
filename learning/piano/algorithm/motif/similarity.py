#!/usr/bin/env python3

import music21
import os
import sys
import editdistance

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

def get_dissimilarity(first, second):
    # get a single notegram to represent the whole group
    first_note_list = first[0].get_note_list()
    second_note_list = second[0].get_note_list()
    diff_in_len = abs(len(first_note_list) - len(second_note_list))

    sequence_func_list = [
        (MotifAnalyzerAlgorithms.note_sequence_func, 1),
        (MotifAnalyzerAlgorithms.rhythm_sequence_func, 1),
        (MotifAnalyzerAlgorithms.note_contour_sequence_func, 1),
        (MotifAnalyzerAlgorithms.notename_transition_sequence_func, 1),
        (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, 1),
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

    # return sum((i ** 2 for i in score), 0) # squared sum
    return 1.0 / sum((1.0 / (i + 1) for i in score), 0)

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

RHYTHM_SEQUENCE_FUNC_LIST = [
    (MotifAnalyzerAlgorithms.rhythm_sequence_func, 1),
    (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, 3),
]

PITCH_SEQUENCE_FUNC_LIST = [
    (MotifAnalyzerAlgorithms.note_sequence_func, 1),
    (MotifAnalyzerAlgorithms.note_contour_sequence_func, 2),
    (MotifAnalyzerAlgorithms.notename_transition_sequence_func, 3),
]

ALL_SEQUENCE_FUNC_LIST = RHYTHM_SEQUENCE_FUNC_LIST + PITCH_SEQUENCE_FUNC_LIST

def get_dissimilarity(first, second, sequence_func_list=ALL_SEQUENCE_FUNC_LIST):
    score = []
    for item in sequence_func_list:
        sequence_func, multplier = item
        first_sequence = sequence_func(first)
        second_sequence = sequence_func(second)
        first_sequence, second_sequence = normalize_sequences(
            first_sequence, second_sequence)
        score.append(editdistance.eval(
            first_sequence, second_sequence) * multplier)

    # remove the top dissimilar feature, not a good idea it seems
    # score.remove(max(score))

    # return sum((i for i in score), 0) # Manhatten distance
    return sum((i ** 2 for i in score), 0)  # squared sum
    # return sum((i ** 0.5 for i in score), 0) ** 2  # variation of Euclidean distance

# def score_to_notegram(score):
#     notegram = []
#     for note in score.recurse().getElementsByClass(('Note', 'Rest')):
#         notegram.append(note)
#     return notegram

# first = music21.converter.parse("tinynotation: 4/4 b4 b b ebw")
# second = music21.converter.parse("tinynotation: 4/4 b8 b b eb4")

# first_notegram = score_to_notegram(first)
# second_notegram = score_to_notegram(second)

# print(
#     get_dissimilarity(first_notegram, second_notegram)
# )

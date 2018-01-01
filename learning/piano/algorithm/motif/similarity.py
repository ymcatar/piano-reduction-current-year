#!/usr/bin/env python3

import music21
import numpy as np
import os
import sys
from Bio import pairwise2

from .algorithms import MotifAnalyzerAlgorithms

def align_sequences(first, second):
    first, second = normalize_sequences(first, second)
    # no gap penalty, if match add 1 else 0
    results = pairwise2.align.globalxx(first, second, one_alignment_only=True)[0]
    return (len(results[0]) - results[2]) / len(results[0])

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


sequence_func_list = [
    (MotifAnalyzerAlgorithms.note_sequence_func, 1),
    (MotifAnalyzerAlgorithms.rhythm_sequence_func, 1),
    (MotifAnalyzerAlgorithms.note_contour_sequence_func, 1),
    (MotifAnalyzerAlgorithms.notename_transition_sequence_func, 2),
    (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, 2),
]


def get_dissimilarity(first, second):
    # get a single notegram to represent the whole group
    first_note_list = first[0].get_note_list()
    second_note_list = second[0].get_note_list()

    score = []
    for item in sequence_func_list:
        sequence_func, multplier = item
        first_sequence = sequence_func(first_note_list)
        second_sequence = sequence_func(second_note_list)
        score.append(align_sequences(first_sequence, second_sequence) * multplier)

    # return sum((i ** 2 for i in score), 0) # squared sum
    return 1.0 / sum((1.0 / (i + 1) for i in score), 0) - 0.2


def get_dissimilarity_matrix(notegram_group_list):
    sequences_list = []
    for group in notegram_group_list:
        note_list = group[0].get_note_list()
        sequences_list.append([fn(note_list) for fn, _ in sequence_func_list])

    multipliers = np.array([m for _, m in sequence_func_list])

    n = len(notegram_group_list)
    D = np.zeros((n, n))

    for i, iseqs in enumerate(sequences_list):
        for j, jseqs in enumerate(sequences_list):
            if j > i:
                break
            scores = [align_sequences(iseq, jseq) for iseq, jseq in zip(iseqs, jseqs)]
            # "Smoothed" harmonic mean
            D[i, j] = 1.0 / np.sum(1.0 / (multipliers * scores + 1.0)) - 0.2

    D = D + D.T - np.diag(np.diag(D))

    return D

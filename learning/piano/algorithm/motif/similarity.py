#!/usr/bin/env python3

import numpy as np

from .algorithms import MotifAnalyzerAlgorithms
from .alignment import align_sequences, align_one_to_many

sequence_func_list = [
    (MotifAnalyzerAlgorithms.note_sequence_func, 1),
    (MotifAnalyzerAlgorithms.rhythm_sequence_func, 1),
    (MotifAnalyzerAlgorithms.note_contour_sequence_func, 2),
    (MotifAnalyzerAlgorithms.notename_transition_sequence_func, 1),
    (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, 1),
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


def get_dissimilarity_matrix(notegram_group_list, vectorize=True):
    n = len(notegram_group_list)

    scores = np.zeros((len(sequence_func_list), n, n))

    for k, (func, multiplier) in enumerate(sequence_func_list):
        seqs = [func(group[0].get_note_list()) for group in notegram_group_list]

        if vectorize:
            jseqs = seqs[:]
            while len(jseqs) > 1:
                i = len(jseqs) - 1
                iseq = jseqs.pop()
                scores[k, i, 0:i] = align_one_to_many(iseq, jseqs) * multiplier
        else:
            for i, iseq in enumerate(seqs):
                for j, jseq in enumerate(seqs):
                    if j > i:
                        break
                    scores[k, i, j] = align_sequences(iseq, jseq) * multiplier

    # Smoothed harmonic mean
    D = 1.0 / np.sum(1.0 / (scores + 1.0), axis=0) - 0.2
    D = D + D.T - np.diag(np.diag(D))

    return D

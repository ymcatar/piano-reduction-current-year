#!/usr/bin/env python3

import music21
import math
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN
from intervaltree import Interval, IntervalTree

from termcolor import colored

from .notegram import Notegram
from .similarity import get_dissimilarity

LOWER_N = 3
UPPER_N = 4

DBSCAN_EPS = 50
DBSCAN_MIN_SAMPLES = 1

OVERLAP_THRESHOLD = 0.8

def is_rest(note):
    return note is None or \
        isinstance(note, music21.note.Rest) or \
        (isinstance(note, music21.note.Note) and
         (float(note.duration.quarterLength) < 1e-2 or note.name == 'rest'))


def is_intervals_overlapping(first, second):
    first_intervals = [Interval(*i) for i in first]
    second_intervals = [Interval(*i) for i in second]

    count = 0
    tree = IntervalTree(first_intervals)
    for interval in second_intervals:
        if tree.search(*interval):
            count += 1
    if count / len(second_intervals) > OVERLAP_THRESHOLD:
        return True

    count = 0
    tree = IntervalTree(second_intervals)
    for interval in first_intervals:
        if tree.search(*interval):
            count += 1
    if count / len(first_intervals) > OVERLAP_THRESHOLD:
        return True

    return False


class MotifAnalyzer(object):
    def __init__(self, score):
        self.score = score

        self.notegram_groups = defaultdict(lambda: [])
        self.score_by_notegram_group = defaultdict(lambda: 0)

        self.algorithms = []

        self.initialize()

    def load_notegrams_by_part(self, part):
        measures = list(part.getElementsByClass('Measure'))

        vids = set(str(v.id) for measure in measures for v in measure.voices)
        vids.add('1')  # Default voice

        result = []

        for vid in sorted(vids):
            note_list = []
            vid_list = []
            for measure in measures:
                if measure.voices:
                    voice = next(
                        (v for v in measure.voices if str(v.id) == vid), None)
                    real_vid = vid
                else:
                    voice = measure
                    real_vid = '1'

                if voice is not None:
                    for n in voice.notesAndRests:
                        offset = measure.offset + n.offset
                        if isinstance(n, music21.chord.Chord):
                            # Use only the highest-pitched note
                            note_list.append((offset,
                                              max(n,
                                                  key=lambda i: i.pitch.ps)))
                        else:
                            note_list.append((offset, n))
                        vid_list.append(real_vid)

            for n in range(LOWER_N, UPPER_N):
                notegram_it = zip(*[note_list[i:] for i in range(n)])
                vid_it = zip(*[vid_list[i:] for i in range(n)])
                for notegram, vidgram in zip(notegram_it, vid_it):
                    if vid not in vidgram:
                        continue

                    # reject notegram starting with a rest
                    if is_rest(notegram[0][1]):
                        continue

                    # reject notegram containing >= half rest
                    if any((is_rest(n[1]) and n[1].duration.quarterLength -
                            (2.0 - 1e-2) > 0.0) for n in notegram):
                        continue

                    temp = Notegram(
                        list(i[1] for i in notegram),
                        list(i[0] for i in notegram))

                    result.append(temp)

        return result

    def initialize(self):
        self.notegram_groups = defaultdict(lambda: [])
        self.score_by_notegram_group = defaultdict(lambda: 0)
        for part in self.score.recurse().getElementsByClass('Part'):
            for notegram in self.load_notegrams_by_part(part):
                self.notegram_groups[str(notegram)].append(notegram)

    def add_algorithm(self, algorithm_tuple):
        self.algorithms.append(algorithm_tuple)

    def get_first_notegram_from_group(self, notegram_group):
        return self.notegram_groups[notegram_group][0]

    def run(self, sequence_func, score_func, threshold=0, multiplier=1):
        freq_by_sequence = defaultdict(lambda: 0)
        sequence_by_notegram_group = {}
        score_to_add_by_notegram_group = {}

        for notegram_group, _ in self.notegram_groups.items():
            sequence = tuple(
                sequence_func(
                    self.get_first_notegram_from_group(notegram_group)
                    .get_note_list()))
            freq_by_sequence[sequence] += 1
            sequence_by_notegram_group[notegram_group] = sequence

        for notegram_group, sequence in sequence_by_notegram_group.items():
            notegram = self.get_first_notegram_from_group(notegram_group)
            group_size = len(self.notegram_groups[notegram_group])
            score = score_func(notegram.get_note_list(), sequence,
                               freq_by_sequence[sequence]) * group_size
            if score >= threshold:
                score_to_add_by_notegram_group[notegram_group] = score

        total_score_to_add = sum(score_to_add_by_notegram_group.values())

        if abs(total_score_to_add) > 1e-6:
            for notegram_group, _ in sequence_by_notegram_group.items():
                if notegram_group in score_to_add_by_notegram_group:
                    self.score_by_notegram_group[notegram_group] = \
                        self.score_by_notegram_group[notegram_group] + \
                        score_to_add_by_notegram_group[notegram_group] / \
                        total_score_to_add * \
                        multiplier * \
                        len(score_to_add_by_notegram_group)

    def run_all(self):
        self.score_by_notegram_group = defaultdict(lambda: 0)
        for algorithm in self.algorithms:
            self.run(*algorithm)

    def get_top_motif_cluster(self, verbose=False):
        notegram_group_by_score = defaultdict(lambda: [])
        for notegram_group, score in self.score_by_notegram_group.items():
            notegram_group_by_score[score].append(notegram_group)

        results = []

        # retrieve the top 10% scoring notegram groups
        top_n_scoring_notegram_groups = []
        for i in range(0, math.trunc(len(notegram_group_by_score) / 10)):
            max_score = max(k for k, v in notegram_group_by_score.items())
            top_n_scoring_notegram_groups += notegram_group_by_score.pop(
                max_score)

        # create the distance matrix for top n notegram groups
        actual_cluster_init_n = len(top_n_scoring_notegram_groups)

        distance_matrix = np.zeros((actual_cluster_init_n,
                                    actual_cluster_init_n))

        top_scoring_notegram_groups_list = [
            self.notegram_groups[i] for i in top_n_scoring_notegram_groups
        ]

        for i, ni in enumerate(top_scoring_notegram_groups_list):
            for j, nj in enumerate(top_scoring_notegram_groups_list):
                if i == j:
                    continue
                if j > i:
                    break
                distance_matrix[i, j] = get_dissimilarity(ni, nj)

        distance_matrix = distance_matrix + \
            distance_matrix.T - np.diag(np.diag(distance_matrix))

        if verbose:
            print(distance_matrix)
            print("-----------------------\n")

        weights = [self.score_by_notegram_group[i]
                   for i in top_n_scoring_notegram_groups]

        model = DBSCAN(metric='precomputed', eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
        db = model.fit(distance_matrix, sample_weight=weights)

        notegram_group_by_label = defaultdict(lambda: [])
        for i, label in enumerate(db.labels_):
            if label == -1:
                continue
            notegram_group_by_label[label].append(
                top_n_scoring_notegram_groups[i])

        total_score_by_label = defaultdict(lambda: 0)
        for label, notegram_groups in notegram_group_by_label.items():
            for notegram_group in notegram_groups:
                total_score_by_label[label] += len(notegram_group)

        # for printing out clustering result
        if verbose:
            for group in set(i for i in db.labels_) - {-1}:
                for label, notegram_group in zip(
                        db.labels_, top_n_scoring_notegram_groups):
                    if label == group:
                        print(str(label) + '\t' + notegram_group)
            print("-----------------------\n")

        if len(total_score_by_label) > 0:
            largest_cluster = set(
                str(i) for i in notegram_group_by_label[max(
                    total_score_by_label, key=total_score_by_label.get)])
        else:
            largest_cluster = set()

        # expand cluster by considering overlapping
        notegram_group_queue = list(largest_cluster)
        group_to_add = set()
        notegram_group_visited = set()

        while len(notegram_group_queue) > 0:

            curr_notegram_group = notegram_group_queue.pop(0)

            if curr_notegram_group in notegram_group_visited:
                continue

            notegram_group_visited.add(curr_notegram_group)

            in_group = self.notegram_groups[curr_notegram_group]

            for out_label in top_n_scoring_notegram_groups:

                if out_label in largest_cluster or out_label in group_to_add:
                    continue

                out_group = self.notegram_groups[out_label]

                in_offsets = [(notegram.get_note_offset_by_index(
                    0), notegram.get_note_offset_by_index(-1)) for notegram in in_group]
                out_offsets = [(notegram.get_note_offset_by_index(
                    0), notegram.get_note_offset_by_index(-1)) for notegram in out_group]

                if is_intervals_overlapping(in_offsets, out_offsets):
                    notegram_group_queue.append(out_label)
                    group_to_add.add(out_label)

        if verbose:
            for i in largest_cluster:
                print(i)
            for i in group_to_add:
                print(colored(i, 'red'))

        return list(largest_cluster) + list(group_to_add)

    def highlight_notegram_group(self, notegram_group, color):
        for value in self.notegram_groups[notegram_group]:
            for note in value.get_note_list():
                note.style.color = color
                # if note.lyric is None:
                #     note.lyric = '1'
                # else:
                #     note.lyric = str(int(note.lyric) + 1)

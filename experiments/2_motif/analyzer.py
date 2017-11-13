#!/usr/bin/env python3

import music21
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN

from notegram import Notegram
from similarity import get_similarity

LOWER_N = 4
UPPER_N = 5

CLUTSER_INIT_N = 100


class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
        self.score.toSoundingPitch()

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
                            note_list.append(
                                (offset, max(n, key=lambda i: i.pitch.ps)))
                        else:
                            note_list.append((offset, n))
                        vid_list.append(real_vid)

            for n in range(LOWER_N, UPPER_N):
                notegram_it = zip(*[note_list[i:] for i in range(n)])
                vid_it = zip(*[vid_list[i:] for i in range(n)])
                for notegram, vidgram in zip(notegram_it, vid_it):
                    if vid not in vidgram:
                        continue
                    if any(n[1].name == 'rest' or
                           float(n[1].duration.quarterLength) < 1e-2
                           for n in notegram):
                        continue

                    temp = Notegram(list(i[1] for i in notegram), list(
                        i[0] for i in notegram))
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

    def run(self, sequence_func, score_func, threshold=0, multipier=1):
        freq_by_sequence = defaultdict(lambda: 0)
        sequence_by_notegram_group = {}
        score_to_add_by_notegram_group = {}

        for notegram_group, _ in self.notegram_groups.items():
            sequence = tuple(
                sequence_func(self.get_first_notegram_from_group(
                    notegram_group).get_note_list())
            )
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
                        multipier * \
                        len(score_to_add_by_notegram_group)

    def run_all(self):
        self.score_by_notegram_group = defaultdict(lambda: 0)
        for algorithm in self.algorithms:
            self.run(*algorithm)

    def get_top_motif_cluster(self):  # TODO: add clustering
        notegram_group_by_score = defaultdict(lambda: [])
        for notegram_group, score in self.score_by_notegram_group.items():
            notegram_group_by_score[score].append(notegram_group)

        results = []

        # retrieve the top scoring 100 notegram groups
        top_n_scoring_notegram_groups = []
        for i in range(0, min(len(notegram_group_by_score), CLUTSER_INIT_N)):
            max_score = max(k for k, v in notegram_group_by_score.items())
            top_n_scoring_notegram_groups += notegram_group_by_score.pop(
                max_score)

        # create the distance matrix for top n notegram groups
        actual_cluster_init_n = len(top_n_scoring_notegram_groups)
        top_n_scoring_group_notegrams = [self.get_first_notegram_from_group(
            i) for i in top_n_scoring_notegram_groups]

        distance_matrix = np.zeros(
            (actual_cluster_init_n, actual_cluster_init_n))

        for i, ni in enumerate(top_n_scoring_group_notegrams):
            for j, nj in enumerate(top_n_scoring_group_notegrams):
                if i == j:
                    continue
                if j > i:
                    break
                distance_matrix[i, j] = get_similarity(
                    ni.get_note_list(), nj.get_note_list())

        distance_matrix = distance_matrix + \
            distance_matrix.T - np.diag(np.diag(distance_matrix))

        # print(distance_matrix)

        model = DBSCAN(metric='precomputed', eps=5, min_samples=3)
        db = model.fit(distance_matrix)

        notegram_group_by_label = defaultdict(lambda: [])
        for i, label in enumerate(db.labels_):
            if label == -1:
                continue
            notegram_group_by_label[label].append(
                top_n_scoring_group_notegrams[i])

        total_score_by_label = defaultdict(lambda: 0)
        for label, notegram_groups in notegram_group_by_label.items():
            for notegram_group in notegram_groups:
                total_score_by_label[label] += \
                    self.score_by_notegram_group[str(notegram_group)]

        # # for printing out clustering result
        # for group in set(i for i in db.labels_) - {-1}:
        #     for label, notegram_group in zip(db.labels_, top_n_scoring_group_notegrams):
        #         if label == group:
        #             print(str(label) + '\t\t' + str(notegram_group))

        return list(str(i) for i in notegram_group_by_label[
            max(total_score_by_label, key=total_score_by_label.get)
        ])

    def highlight_noteidgram_group(self, notegram_group, color):
        for value in self.notegram_groups[notegram_group]:
            for note in value.get_note_list():
                note.style.color = color
                if note.lyric is None:
                    note.lyric = '1'
                else:
                    note.lyric = str(int(note.lyric) + 1)

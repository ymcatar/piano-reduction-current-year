#!/usr/bin/env python3

import music21
from collections import defaultdict

from notegram import Notegram

LOWER_N = 3
UPPER_N = 4

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
        self.score.toSoundingPitch()

        # resolve note unique id back to note object
        self.notegrams = []
        self.notegram_map = {}
        self.score_by_notegram = defaultdict(lambda: 0)

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
                    voice = next((v for v in measure.voices if str(v.id) == vid), None)
                    real_vid = vid
                else:
                    voice = measure
                    real_vid = '1'

                if voice is not None:
                    for n in voice.notesAndRests:
                        offset = measure.offset + n.offset
                        if isinstance(n, music21.chord.Chord):
                            # Use only the highest-pitched note
                            note_list.append((offset, max(n, key=lambda i: i.pitch.ps)))
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

                    temp = Notegram(list(i[1] for i in notegram), list(i[0] for i in notegram))
                    self.notegram_map[temp] = temp
                    result.append(temp)

        return result

    def initialize(self):
        self.notegrams = []
        self.score_by_notegram = defaultdict(lambda: 0)
        for part in self.score.recurse().getElementsByClass('Part'):
            self.notegrams += self.load_notegrams_by_part(part)

    def add_algorithm(self, algorithm_tuple):
        self.algorithms.append(algorithm_tuple)

    def run(self, sequence_func, score_func, threshold = 0, multipier = 1):
        freq_by_sequence = defaultdict(lambda: 0)
        sequence_by_notegram = {}
        score_to_add_by_notegram = {}

        for notegram in self.notegrams:
            sequence = tuple(sequence_func(notegram.get_note_list()))
            freq_by_sequence[sequence] += 1
            sequence_by_notegram[notegram] = sequence

        for notegram_id, sequence in sequence_by_notegram.items():
            notegram = self.notegram_map[notegram_id]
            score = score_func(notegram.get_note_list(), sequence, freq_by_sequence[sequence])
            if score >= threshold:
                score_to_add_by_notegram[notegram] = score

        total_score_to_add = sum(score_to_add_by_notegram.values())

        if abs(total_score_to_add) > 1e-6:
            for notegram_id, _ in sequence_by_notegram.items():
                notegram = self.notegram_map[notegram_id]
                if notegram in score_to_add_by_notegram:
                    self.score_by_notegram[notegram] = \
                        self.score_by_notegram[notegram] + \
                        score_to_add_by_notegram[notegram] / \
                        total_score_to_add * \
                        multipier * \
                        len(score_to_add_by_notegram)

    def run_all(self):
        self.score_by_notegram = defaultdict(lambda: 0)
        for algorithm in self.algorithms:
            self.run(*algorithm)

    def get_top_distinct_score_motifs(self, top_count = 1):
        notegram_by_score = defaultdict(lambda: [])
        for notegram, score in self.score_by_notegram.items():
            notegram_by_score[score].append(notegram)

        results = []
        for i in range(0, min(len(notegram_by_score), top_count)):
            max_score = max(k for k, v in notegram_by_score.items())
            results.append(notegram_by_score.pop(max_score))

        return results

    def highlight_noteidgram(self, notegram, color):
        for note in notegram.get_note_list():
            note.style.color = color
            if note.lyric is None:
                note.lyric = '1'
            else:
                note.lyric = str(int(note.lyric) + 1)

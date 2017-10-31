#!/usr/bin/env python3

import music21
import os
import sys

from algorithms import MotifAnalyzerAlgorithms

LOWER_N = 3
UPPER_N = 4

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
        self.score.toSoundingPitch()

        # resolve note unique id back to note object
        self.note_map = {}

        self.noteidgrams = []
        self.score_by_noteidgram = {}

        self.initialize()

    def load_notegrams_by_part_id(self, part):
        # TODO: support multiple voice
        note_list = [item for item in part.recurse().getElementsByClass(('Note', 'Rest'))]
        result = [[i for i in zip(*[note_list[i:] for i in range(n)])] for n in range(LOWER_N, UPPER_N)]
        return sum(result, []) # flatten the list

    def noteidgram_to_notegram(self, noteidgram):
        return tuple(self.note_map[i] for i in list(noteidgram))

    def notegram_to_noteidgram(self, notegram):
        for note in list(notegram):
            self.note_map[id(note)] = note
        return tuple(id(i) for i in list(notegram))

    def initialize(self):
        self.noteidgrams = []
        self.score_by_noteidgram = {}
        for part in self.score.recurse().getElementsByClass('Part'):
            self.noteidgrams = self.noteidgrams + [self.notegram_to_noteidgram(i) for i in self.load_notegrams_by_part_id(part)]

    def start_run(self, sequence_func, score_func, threshold = 0, multipier = 1):
        freq_by_sequence = {}
        sequence_by_noteidgram = {}

        for noteidgram in self.noteidgrams:
            notegram = self.noteidgram_to_notegram(noteidgram)
            sequence = tuple(sequence_func(notegram))
            if sequence not in freq_by_sequence:
                freq_by_sequence[sequence] = 0
            freq_by_sequence[sequence] = freq_by_sequence[sequence] + 1
            sequence_by_noteidgram[noteidgram] = sequence

        for noteidgram, sequence in sequence_by_noteidgram.items():
            notegram = self.noteidgram_to_notegram(noteidgram)
            score = score_func(notegram, sequence, freq_by_sequence[sequence])
            if score >= threshold:
                if noteidgram not in self.score_by_noteidgram:
                    self.score_by_noteidgram[noteidgram] = 0
                self.score_by_noteidgram[noteidgram] = self.score_by_noteidgram[noteidgram] + score * multipier

    def get_top_motifs(self, top_count = 1):
        results = []
        temp_score_by_noteidgram = self.score_by_noteidgram.copy()
        for i in range(0, min(len(self.score_by_noteidgram), top_count)):
            noteidgram = max(temp_score_by_noteidgram, key=temp_score_by_noteidgram.get)
            temp_score_by_noteidgram.pop(noteidgram)
            results.append(noteidgram)
        return results

    def highlight_noteidgram(self, noteidgram, color):
        notegram = self.noteidgram_to_notegram(noteidgram)
        for note in notegram:
            note.style.color = color


if len(sys.argv) != 3:
    print("Usage: $0 [path of the input MusicXML file] [output path]")
    exit()

analyzer = MotifAnalyzer(sys.argv[1])

analyzer.start_run(
    MotifAnalyzerAlgorithms.note_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = -1,
    multipier = 1
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.notename_transition_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = -1,
    multipier = 1
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.rhythm_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = -1,
    multipier = 1
)

motifs = analyzer.get_top_motifs(top_count = 50)

for motif_noteidgram in motifs:
    analyzer.highlight_noteidgram(motif_noteidgram, '#FF0000')
    print(
        str(analyzer.score_by_noteidgram[motif_noteidgram]) +
        '\t\t' +
        str(MotifAnalyzerAlgorithms.note_sequence_func(analyzer.noteidgram_to_notegram(motif_noteidgram)))
    )

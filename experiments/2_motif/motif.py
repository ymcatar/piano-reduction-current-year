#!/usr/bin/env python3

import music21
import os
import sys

from algorithms import MotifAnalyzerAlgorithms

LOWER_N = 2
UPPER_N = 10

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

    def get_top_distinct_score_motifs(self, top_count = 1):
        noteidgram_by_score = {}
        for noteidgram, score in self.score_by_noteidgram.items():
            if score not in noteidgram_by_score:
                noteidgram_by_score[score] = []
            noteidgram_by_score[score] = noteidgram_by_score[score] + [noteidgram]

        results = []
        for i in range(0, min(len(noteidgram_by_score), top_count)):
            max_score = max(k for k, v in noteidgram_by_score.items())
            results.append(noteidgram_by_score.pop(max_score))

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
    threshold = 0,
    multipier = 0.2
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.notename_transition_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = 0,
    multipier = 0.4
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.note_transition_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = 0,
    multipier = 0.1
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.rhythm_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = 0,
    multipier = 0.1
)

analyzer.start_run(
    MotifAnalyzerAlgorithms.rhythm_transition_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func,
    threshold = 0,
    multipier = 0.2
)

motifs = analyzer.get_top_distinct_score_motifs(top_count = 30)

# colors = ['#D50000', '#6200EA', '#2962FF']

print('#\t\tScore\t\tSequence')
print('-\t\t-----\t\t--------')
for motif_noteidgram_list in motifs:
    print(
        str(len(motif_noteidgram_list)) +
        '\t\t' +
        str('{0:.2f}'.format(analyzer.score_by_noteidgram[motif_noteidgram_list[0]])) +
        '\t\t' +
        str(list(zip(
            MotifAnalyzerAlgorithms.note_sequence_func(analyzer.noteidgram_to_notegram(motif_noteidgram_list[0])),
            MotifAnalyzerAlgorithms.rhythm_sequence_func(analyzer.noteidgram_to_notegram(motif_noteidgram_list[0]))
        )))
    )

# analyzer.score.show()
#!/usr/bin/env python3

import music21
import os
import sys
from matplotlib import cm, colors

from algorithms import MotifAnalyzerAlgorithms

LOWER_N = 3
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

    def load_notegrams_by_part(self, part):
        # TODO: support multiple voice
        note_list = [item for item in part.recurse().getElementsByClass(('Note', 'Rest'))]
        result = [[i for i in zip(*[note_list[i:] for i in range(n)])] for n in range(LOWER_N, UPPER_N)]
        result = sum(result, []) # flatten the list
        result = [notegram for notegram in result if not any(
            (isinstance(note, music21.note.Rest) or
            note.name == 'rest' or
            note.duration.quarterLength - 0.0 < 1e-2) for note in notegram
        )]
        return result

    def noteidgram_to_notegram(self, noteidgram):
        return tuple(self.note_map[i] for i in list(noteidgram))

    def notegram_to_noteidgram(self, notegram):
        for note in notegram:
            self.note_map[id(note)] = note
        return tuple(id(i) for i in notegram)

    def initialize(self):
        self.noteidgrams = []
        self.score_by_noteidgram = {}
        for part in self.score.recurse().getElementsByClass('Part'):
            self.noteidgrams = self.noteidgrams + [self.notegram_to_noteidgram(i) for i in self.load_notegrams_by_part(part)]

    def start_run(self, sequence_func, score_func, threshold = 0, multipier = 1):
        freq_by_sequence = {}
        sequence_by_noteidgram = {}
        score_to_add_by_noteidgram = {}

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
                score_to_add_by_noteidgram[noteidgram] = score

        total_score_to_add = sum(score_to_add_by_noteidgram.values())

        for noteidgram, _ in sequence_by_noteidgram.items():
            if noteidgram in score_to_add_by_noteidgram:
                self.score_by_noteidgram[noteidgram] = \
                    self.score_by_noteidgram[noteidgram] + \
                    score_to_add_by_noteidgram[noteidgram] / \
                    total_score_to_add * \
                    multipier * \
                    len(score_to_add_by_noteidgram)

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
            if note.lyric is None:
                note.lyric = '1'
            else:
                note.lyric = str(int(note.lyric) + 1)


if len(sys.argv) != 4:
    print("Usage: $0 [path of the input MusicXML file] [output path] [top count]")
    exit()

filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]
output_path = sys.argv[2]
top_count = int(sys.argv[3])

m = cm.ScalarMappable(colors.Normalize(vmin=0, vmax=top_count+1), 'hsv')
colors = ['#{:02X}{:02X}{:02X}'.format(*(int(x*255) for x in color[:3])) for color in m.to_rgba(range(top_count))]

analyzer = MotifAnalyzer(sys.argv[1])

algorithms = [
    (MotifAnalyzerAlgorithms.note_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 5),
    (MotifAnalyzerAlgorithms.rhythm_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 5),
    (MotifAnalyzerAlgorithms.note_contour_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 10),
    (MotifAnalyzerAlgorithms.notename_transition_sequence_func, MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 8),
    (MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 5)
]

for algorithm in algorithms:
    analyzer.start_run(*algorithm)

motifs = analyzer.get_top_distinct_score_motifs(top_count = top_count)

print('#\t\tScore\t\tSequence')
print('-\t\t-----\t\t--------')
for i in range(0, len(motifs)):
    motif_noteidgram_list = motifs[i]
    for motif_noteidgram in motif_noteidgram_list:
        analyzer.highlight_noteidgram(motif_noteidgram, colors[i])
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

analyzer.score.write('musicxml', os.path.join(output_path, filename + '.xml'))
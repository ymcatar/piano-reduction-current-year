#!/usr/bin/env python3

import os
import sys

from matplotlib import cm, colors

from analyzer import MotifAnalyzer
from algorithms import MotifAnalyzerAlgorithms

if len(sys.argv) != 4:
    print("Usage: $0 [path of the input MusicXML file] [output path] [top count]")
    exit()

filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]
output_path = sys.argv[2]
top_count = int(sys.argv[3])

m = cm.ScalarMappable(colors.Normalize(vmin=0, vmax=top_count+1), 'hsv')
colors = ['#{:02X}{:02X}{:02X}'.format(*(int(x*255) for x in color[:3])) for color in m.to_rgba(range(top_count))]

analyzer = MotifAnalyzer(sys.argv[1])

analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 5))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 5))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_contour_sequence_func, MotifAnalyzerAlgorithms.simple_note_score_func, 0, 10))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.notename_transition_sequence_func, MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 8))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_transition_sequence_func, MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 5))

analyzer.run_all()
motifs = analyzer.get_top_distinct_score_motifs(top_count = top_count)

print('#\t\tScore\t\tSequence')
print('-\t\t-----\t\t--------')
for i in range(0, len(motifs)):
    motif_notegram_list = motifs[i]
    for motif_noteidgram in motif_notegram_list:
        analyzer.highlight_noteidgram(motif_noteidgram, colors[i])
    print(
        str(len(motif_notegram_list)) +
        '\t\t' +
        str('{0:.2f}'.format(analyzer.score_by_notegram[motif_notegram_list[0]])) +
        '\t\t' +
        str(motif_notegram_list[0])
    )

# analyzer.score.write('musicxml', os.path.join(output_path, filename + '.xml'))
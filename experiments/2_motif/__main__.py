#!/usr/bin/env python3

import os
import sys

from analyzer import MotifAnalyzer
from algorithms import MotifAnalyzerAlgorithms

if len(sys.argv) != 3:
    print("Usage: $0 [path of the input MusicXML file] [output path]")
    exit()

filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]
output_path = sys.argv[2]

analyzer = MotifAnalyzer(sys.argv[1])

analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_sequence_func,
                        MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 5))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_sequence_func,
                        MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 5))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_contour_sequence_func,
                        MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 10))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.notename_transition_sequence_func,
                        MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 8))
analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_transition_sequence_func,
                        MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 5))

# for key, value in analyzer.notegram_groups.items():
# print(key)
# print(len(analyzer.notegram_groups))

analyzer.run_all()
motifs = analyzer.get_top_motif_cluster()

# highlight in file
for notegram_group in motifs:
    analyzer.highlight_noteidgram_group(notegram_group, '#ff0000')

analyzer.score.write('musicxml', os.path.join(output_path, filename + '.xml'))

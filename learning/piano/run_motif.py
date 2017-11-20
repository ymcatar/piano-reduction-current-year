#!/usr/bin/env python3

import os
import sys
import music21
import argparse


from algorithm.motif.analyzer import MotifAnalyzer
from algorithm.motif.algorithms import MotifAnalyzerAlgorithms

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
parser.add_argument(
    "-o", "--output", help="output folder path")

args = parser.parse_args()

filename = os.path.splitext(os.path.basename(args.input))[0]
output_path = args.output

analyzer = MotifAnalyzer(music21.converter.parse(args.input))

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

analyzer.run_all()
motifs = analyzer.get_top_motif_cluster(verbose=True)

# highlight in file
for notegram_group in motifs:
    analyzer.highlight_notegram_group(notegram_group, '#ff0000')

if args.output:
    analyzer.score.write('musicxml', os.path.join(
        output_path, filename + '.xml'))
else:
    analyzer.score.show()

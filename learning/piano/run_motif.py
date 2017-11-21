#!/usr/bin/env python3

import os
import sys
import music21
import argparse


from algorithm.motif.analyzer import MotifAnalyzer
from algorithm.motif.algorithms import MotifAnalyzerAlgorithms

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
parser.add_argument("-o", "--output", help="output folder path")
parser.add_argument("-p", "--print-only", help="print the result only", action='store_true')

args = parser.parse_args()

filename = os.path.splitext(os.path.basename(args.input))[0]
output_path = args.output

analyzer = MotifAnalyzer(music21.converter.parse(args.input))
analyzer.run_all()

motifs = analyzer.get_top_motif_cluster(verbose=True)

# highlight in file
for notegram_group in motifs:
    analyzer.highlight_notegram_group(notegram_group, '#ff0000')

if not args.print_only:
    if args.output:
        analyzer.score.write('musicxml', os.path.join(
            output_path, filename + '.xml'))
    else:
        analyzer.score.show()

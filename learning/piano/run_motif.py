#!/usr/bin/env python3

import os
import sys
import math
import music21
import argparse

from .algorithm.motif.analyzer import MotifAnalyzer
from .algorithm.motif.algorithms import MotifAnalyzerAlgorithms

# from matplotlib import cm, colors

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
parser.add_argument("-o", "--output", help="output folder path")
parser.add_argument("-n", "--no-output",
                    help="print the result only", action='store_true')
parser.add_argument(
    "-p", "--pdf", help="output pdf instead of MusicXML", action='store_true')

args = parser.parse_args()

filename = os.path.splitext(os.path.basename(args.input))[0]
output_path = args.output

print("============================================================")
print(filename + '\n\n')

analyzer = MotifAnalyzer(music21.converter.parse(args.input))
clusters = analyzer.cluster(verbose=True)

# m = cm.ScalarMappable(colors.Normalize(vmin=0, vmax=len(clusters)), 'hsv')
# rgba_list = m.to_rgba(range(len(clusters)))
# colors = []

# for rgba in rgba_list:
#     rgba = [math.ceil(val * 255.0) for val in rgba]
#     colors.append('#{0:02x}{1:02x}{2:02x}'.format(*rgba[:3]))

# highlight in file
i = 0
for label, cluster in clusters.items():
    for notegram_group in cluster:
        analyzer.highlight_notegram_group(notegram_group, label)
    i += 1

print('\n--- cluster size ---')
for label, cluster in clusters.items():
    count = sum((len(analyzer.notegram_groups[notegram_group]) for notegram_group in cluster), 0)
    print('cluster', label + ':', count)

if not args.no_output:
    if args.output and not args.pdf:
        analyzer.score.write('musicxml', os.path.join(
            output_path, filename + '.xml'))
    elif args.pdf:
        analyzer.score.show('musicxml.pdf')
    else:
        analyzer.score.show()

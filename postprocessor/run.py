#!/usr/vin/env python3

import argparse
import music21

# relative import
from post_processor import PostProcessor

parser = argparse.ArgumentParser()

parser.add_argument("input", help="path of the input MusicXML file")

parser.add_argument(
    "-v",
    "--visualization",
    help="show the piano fingering visualization",
    action='store_true')

parser.add_argument(
    "-p",
    "--plot",
    help="show plot",
    action='store_true')

parser.add_argument(
    "-i",
    "--intermediate",
    help="display the intermediate score in musescore",
    action='store_true')

parser.add_argument(
    "-r",
    "--reduced",
    help="display the reduced score in musescore",
    action='store_true')

parser.add_argument("--verbose", help="verbose mode", action='store_true')

args = parser.parse_args()

score = music21.converter.parse(args.input)

post_processor = PostProcessor(score, verbose=args.verbose, show_plot=args.plot)
post_processor.apply()

if args.visualization:
    from visualizer import Visualizer
    results = Visualizer(post_processor.score)

if args.intermediate:
    post_processor.show()

if args.reduced:
    results = post_processor.generate_piano_score()
    results.show()

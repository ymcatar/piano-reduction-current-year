#!/usr/vin/env python3

import argparse
import music21

# relative import
from post_processor import PostProcessor

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
args = parser.parse_args()

score = music21.converter.parse(args.input)

post_processor = PostProcessor(score)
post_processor.apply()

score.show()
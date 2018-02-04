#!/usr/vin/env python3

import argparse
import music21

# relative import
from post_processor import PostProcessor

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
parser.add_argument("-n", "--no-output", help="disable opening in Musescore after finish", action='store_true')
args = parser.parse_args()

score = music21.converter.parse(args.input)

post_processor = PostProcessor(score)
post_processor.apply()

if not args.no_output:
    results = post_processor.retribute_to_two_staffs()
    results.show()
#!/usr/bin/env python3

import os
import sys
import math
import music21
import argparse
import scipy.misc
import numpy as np
import random

# constants
PIANO_PS_MIN = 21
PIANO_PS_MAX = 108
QUANTUM = 16
NUM_MEASURES = 100
MAX_NOTE_NUM_PER_PART = 5

# color scale
from matplotlib import cm, colors
m = cm.ScalarMappable(colors.Normalize(vmin=PIANO_PS_MIN, vmax=PIANO_PS_MAX), 'hot')
colors = m.to_rgba(range(PIANO_PS_MAX - PIANO_PS_MIN + 1))

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
parser.add_argument("-o", "--output", help="output png path")
args = parser.parse_args()

score = music21.converter.parse(args.input)
score = score.stripTies()
parts = list(i for i in score.recurse().getElementsByClass('Part'))

img = None
filled = None
i = 0

for part in parts:
    measures = list(part.recurse().getElementsByClass(('Measure')))
    measures_len = min(NUM_MEASURES, len(measures))

    # the first part
    if i == 0:
        width = math.ceil(measures_len * float(QUANTUM)) + measures_len
        height = len(parts) * MAX_NOTE_NUM_PER_PART
        img = np.full((height, width, 3), 0)
        filled = np.zeros((height, width), dtype=np.int)

    j = 0

    for measure in measures[:measures_len]:
        duration = measure.duration.quarterLength
        offsetMap = measure.offsetMap()
        for note in offsetMap:
            if isinstance(note.element, music21.note.Note):
                lower = math.floor(note.offset * float(QUANTUM) / duration) # replace with time signature
                upper = math.floor(note.endTime * float (QUANTUM) / duration) # replace with time signature
                color = colors[math.floor(note.element.pitch.ps - 21.0)]
                for k in range(lower, upper):
                    if filled[i, j+k] > MAX_NOTE_NUM_PER_PART:
                        break
                    print(filled[i, j+k])
                    img[i * MAX_NOTE_NUM_PER_PART + filled[i, j+k], j+k][0] = color[0] * 255
                    img[i * MAX_NOTE_NUM_PER_PART + filled[i, j+k], j+k][1] = color[1] * 255
                    img[i * MAX_NOTE_NUM_PER_PART + filled[i, j+k], j+k][2] = color[2] * 255
                    filled[i, j+k] += 1

        j += QUANTUM

    i += 1

display_img = np.kron(img, np.ones((4,4,1)))

if not args.output:
    scipy.misc.imshow(display_img)
else:
    scipy.misc.imsave(args.output, display_img)

#!/usr/bin/env python3

import os
import sys
import math
import music21
import argparse
import scipy.misc
import numpy as np
import random

# color scale
from matplotlib import cm, colors
# piano pitch class range: 21 - 108
m = cm.ScalarMappable(colors.Normalize(vmin=21, vmax=108), 'hsv')
colors = m.to_rgba(range(88))

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")

args = parser.parse_args()

score = music21.converter.parse(args.input)
score = score.quantize()

# for part in score.recurse().getElementsByClass('Part'):
#     measures = list(part.getElementsByClass('Measure'))
#     print(measures)

QUANTUM = 16

img = None

parts = list(i for i in score.recurse().getElementsByClass('Part'))

for i in range(len(parts)):
    part = parts[i]
    measures = list(part.recurse().getElementsByClass(('Measure')))

    # the first part
    if i == 0:
        width = math.ceil(len(measures) * float(QUANTUM)) + len(measures)
        height = len(parts) * 2
        img = np.zeros((height, width, 3), dtype=np.uint8)

    j = 0

    for measure in measures:
        duration = measure.duration.quarterLength
        offsetMap = measure.offsetMap()
        for note in offsetMap:
            if note.voiceIndex is None and isinstance(note.element, music21.note.Note):
                lower = math.floor(note.offset * float(QUANTUM) / duration) # replace with time signature
                upper = math.floor(note.endTime * float (QUANTUM) / duration) # replace with time signature

                color = colors[math.floor(note.element.pitch.ps - 21.0)]

                for k in range(lower, upper):
                    img[i*2, j+k][0] = color[0] * 255
                    img[i*2, j+k][1] = color[1] * 255
                    img[i*2, j+k][2] = color[2] * 255
    
        j += QUANTUM + 1

display_img = np.kron(img, np.ones((4,4,1)))

# scipy.misc.imsave('after.png', display_img)
scipy.misc.imshow(display_img)
# score.plot('pianoroll')

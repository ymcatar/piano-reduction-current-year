#!/usr/bin/env python3

import music21
import os

xml_path = os.getcwd() + '/sample/'
targetXml = '1b.xml'

result = music21.converter.parse(xml_path + targetXml)

chords = result.chordify()

for c in chords.recurse().getElementsByClass('Chord'):
    c.closedPosition(forceOctave=4, inPlace=True)

prev = None
for c in chords.recurse().getElementsByClass('Chord'):
    rn = str(
        music21.roman.romanNumeralFromChord(c, music21.key.Key('C')).figure)
    if rn != prev:
        c.addLyric(rn)
    prev = rn

chords.show()

# detect modulation
for m in chords.getElementsByClass('Measure'):
    k = m.analyze('key')
    print(m.number, k)

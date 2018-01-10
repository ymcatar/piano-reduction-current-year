#!/usr/vin/env python3

import os
import sys
import math
import music21
import argparse
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument("input", help="path of the input MusicXML file")
args = parser.parse_args()

score = music21.converter.parse(args.input)

MAX_CONCURRENT_NOTE = 4

def isNote(item):
    return isinstance(item, music21.note.Note)

def isChord(item):
    return isinstance(item, music21.chord.Chord)

def highlight(noteOrChord, color):
    if isNote(noteOrChord):
        noteOrChord.style.color = color
    elif isChord(noteOrChord):
        for note in noteOrChord._notes:
            highlight(note, color)

def fix_too_many_notes(noteOrChordList):
    note_num = 0
    name_with_octave_map = defaultdict(lambda: [])
    name_map = defaultdict(lambda: [])
    for noteOrChord in noteOrChordList:
        if isNote(noteOrChord):
            note_num += 1
            name_with_octave_map[noteOrChord.pitch.nameWithOctave].append(noteOrChord)
            name_map[noteOrChord.pitch.name].append(noteOrChord)
        elif isChord(noteOrChord):
            for note in noteOrChord._notes:
                note_num += 1
                name_with_octave_map[note.pitch.nameWithOctave].append(note)
                name_map[note.pitch.name].append(note)
    # remove duplicate notes with same pitch + octave
    for _, items in name_with_octave_map.items():
        if len(items) > 1:
            for item in items[1:]:
                note_num -= 1
                # score.remove(item)
                highlight(item, 'blue')
    # remove notes with same pitch class
    for _, items in name_map.items():
        while len(items) > 1 and note_num > MAX_CONCURRENT_NOTE:
            # delete at most (n - 1) notes
            # score.remove(items.pop(0))
            highlight(items.pop(0), 'blue')
            note_num -= 1

# group measures with the same offset together
measures = list(score.recurse().getElementsByClass('Measure'))
grouped_measures = defaultdict(lambda: [])
for measure in measures:
    grouped_measures[str(measure.offset)].append(measure)

# detect chord and convert all of them into notes => not a good idea
# for measure in score.recurse().getElementsByClass('Measure'):
#     for chord in score.recurse().getElementsByClass('Chord'):
#         for note in chord._notes:
#             chord.remove(note)
#             measure.insert(chord.offset, note)
#         measure.remove(chord, recurse=True)

for _, group in grouped_measures.items():
    merged_offset_map = defaultdict(lambda: [])
    for measure in group:
        offset_map = measure.offsetMap()
        for item in offset_map:
            merged_offset_map[item.offset].append(item.element)
    # determine the number of notes playing at each time instance
    num_of_notes_at_offset = defaultdict(lambda: 0)
    for offset, notes in merged_offset_map.items():
        for noteOrChord in notes:
            if isNote(noteOrChord):
                num_of_notes_at_offset[offset] += 1
            elif isChord(noteOrChord):
                num_of_notes_at_offset[offset] += noteOrChord.chordTablesAddress.cardinality
    # highlight all time instance with note playing >= 4
    for offset, count in num_of_notes_at_offset.items():
        if count >= 4:
            for noteOrChord in merged_offset_map[offset]:
                highlight(noteOrChord, 'red')
            # attempt to fix
            fix_too_many_notes(merged_offset_map[offset])
        else:
            del merged_offset_map[offset]

score.show()


#!/usr/bin/env python3

import music21
import os
import sys
from matplotlib import cm, colors


LOWER_N = 3
UPPER_N = 10

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
        self.score.toSoundingPitch()

        # resolve note unique id back to note object
        self.note_map = {}

        self.noteidgrams = []

        self.initialize()

    def load_notegrams_by_part_id(self, part):
        # TODO: support multiple voice
        note_list = [item for item in part.recurse().getElementsByClass(('Note', 'Rest'))]
        result = [[i for i in zip(*[note_list[i:] for i in range(n)])] for n in range(LOWER_N, UPPER_N)]
        result = sum(result, []) # flatten the list
        result = [notegram for notegram in result if not any(
            (isinstance(note, music21.note.Rest) or
            note.name == 'rest' or
            note.duration.quarterLength - 0.0 < 1e-2) for note in notegram
        )]
        return result

    def noteidgram_to_notegram(self, noteidgram):
        return tuple(self.note_map[i] for i in list(noteidgram))

    def notegram_to_noteidgram(self, notegram):
        for note in list(notegram):
            self.note_map[id(note)] = note
        return tuple(id(i) for i in list(notegram))

    def initialize(self):
        self.noteidgrams = []
        self.score_by_noteidgram = {}
        for part in self.score.recurse().getElementsByClass('Part'):
            self.noteidgrams = self.noteidgrams + [self.notegram_to_noteidgram(i) for i in self.load_notegrams_by_part_id(part)]

    def highlight_noteidgram(self, noteidgram, color):
        notegram = self.noteidgram_to_notegram(noteidgram)
        for note in notegram:
            note.style.color = color
            if note.lyric is None:
                note.lyric = '1'
            else:
                note.lyric = str(int(note.lyric) + 1)


if len(sys.argv) != 4:
    print("Usage: $0 [path of the input MusicXML file] [output path] [top count]")
    exit()

filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]
output_path = sys.argv[2]
top_count = int(sys.argv[3])

m = cm.ScalarMappable(colors.Normalize(vmin=0, vmax=top_count+1), 'hsv')
colors = ['#{:02X}{:02X}{:02X}'.format(*(int(x*255) for x in color[:3])) for color in m.to_rgba(range(top_count))]

analyzer = MotifAnalyzer(sys.argv[1])

print(analyzer.noteidgrams)

# analyzer.score.write('musicxml', os.path.join(output_path, filename + '.xml'))
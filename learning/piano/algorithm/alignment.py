from .base import ReductionAlgorithm
from ..music.chord import Chord
from ..music.note import Note

import music21

class SimpleAlignment(object):

    def __init__(self):
        super(SimpleAlignment, self).__init__()

    def alignScores(self, sampleInput, sampleOutput):
        existence = set()

        for part in sampleOutput.score:
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                existence.add((mid, noteObj.offset, ch_note.nameWithOctave))
                        elif isinstance(noteObj, Note):
                            existence.add((mid, noteObj.offset, noteObj.nameWithOctave))
                    mid = mid + 1

        for part in sampleInput.score:
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                mark = 0
                                key = (mid, noteObj.offset, ch_note.nameWithOctave)
                                if key in existence:
                                    mark = 1
                                ch_note.align = mark
                        elif isinstance(noteObj, Note):
                            mark = 0
                            key = (mid, noteObj.offset, noteObj.nameWithOctave)
                            if key in existence:
                                mark = 1
                            noteObj.align = mark
                    mid = mid + 1
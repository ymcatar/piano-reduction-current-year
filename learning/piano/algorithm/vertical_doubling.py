from .base import ReductionAlgorithm
from ..music.note import Note
from ..music.chord import Chord

import music21

class VerticalDoubling(ReductionAlgorithm):

    _type = 'doubling'

    def __init__(self, parts=[]):
        super(VerticalDoubling, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        notes = dict()

        parts = (self.parts and [self.parts] or [range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if mid not in notes:
                        notes[mid] = dict()
                    for noteObj in measure.notes:
                        if noteObj.offset not in notes[mid]:
                            notes[mid][noteObj.offset] = dict()
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                if ch_note.name not in notes[mid][noteObj.offset]:
                                    notes[mid][noteObj.offset][ch_note.name] = []
                                notes[mid][noteObj.offset][ch_note.name].append(ch_note)
                        elif isinstance(noteObj, Note):
                            if noteObj.name not in notes[mid][noteObj.offset]:
                                notes[mid][noteObj.offset][noteObj.name] = []
                            notes[mid][noteObj.offset][noteObj.name].append(noteObj)
                    mid = mid + 1

        for mid in notes:
            for offset in notes[mid]:
                for pitch in notes[mid][offset]:
                    if len(notes[mid][offset][pitch]) > 1:
                        for noteObj in notes[mid][offset][pitch]:
                            noteObj.addMark(self.key, len(notes[mid][offset][pitch]))


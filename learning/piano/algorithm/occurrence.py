from .base import ReductionAlgorithm
from ..music.chord import Chord
from ..music.note import Note

import music21

class Occurrence(ReductionAlgorithm):

    _type = 'occurrence'

    def __init__(self, parts=[]):
        super(Occurrence, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                notes = dict()
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if mid not in notes:
                        notes[mid] = dict()
                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                if ch_note.name not in notes[mid]:
                                    notes[mid][ch_note.name] = []
                                notes[mid][ch_note.name].append(ch_note)
                        elif isinstance(noteObj, Note):
                            if noteObj.name not in notes[mid]:
                                notes[mid][noteObj.name] = []
                            notes[mid][noteObj.name].append(noteObj)
                    mid = mid + 1

                for mid in notes:
                    max_cnt_pitch = 0
                    bonus_pitch = []
                    for pitch in notes[mid]:
                        if len(notes[mid][pitch]) >= max_cnt_pitch:
                            if len(notes[mid][pitch]) > max_cnt_pitch:
                                max_cnt_pitch = len(notes[mid][pitch])
                                bonus_pitch = []
                            bonus_pitch.append(pitch)
                    if max_cnt_pitch > 1:
                        for pitch in bonus_pitch:
                            for noteObj in notes[mid][pitch]:
                                noteObj.addMark(self.key, 1)
from .base import ReductionAlgorithm
from ..music.rest import Rest
from ..music.not_rest import NotRest

import music21


class EntranceEffect(ReductionAlgorithm):

    _type = 'entrance'

    def __init__(self, parts=[]):
        super(EntranceEffect, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = self.parts or range(0, len(scoreObj.score))

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                rested = 1
                lastOnsetNote = None
                lastOnsetMeasureOffset = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, Rest):
                            rested = 1
                        elif isinstance(noteObj, NotRest):
                            if rested:
                                lastOnsetNote = noteObj
                                lastOnsetMeasureOffset = measure.offset
                                rested = 0
                            noteObj.addMark(self.key, float(
                                noteObj.offset - lastOnsetNote.offset + measure.offset - lastOnsetMeasureOffset))

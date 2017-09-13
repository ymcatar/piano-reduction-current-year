from .base import ReductionAlgorithm
from ..music.rest import Rest
from ..music.not_rest import NotRest

import music21


class OnsetAfterRest(ReductionAlgorithm):

    _type = 'onset'

    def __init__(self, parts=[]):
        super(OnsetAfterRest, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [
                 range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                rested = 1
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, Rest):
                            rested = 1
                        elif isinstance(noteObj, NotRest):
                            if rested:
                                noteObj.addMark(self.key, 1)
                                rested = 0

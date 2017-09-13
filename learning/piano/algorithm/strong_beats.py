from .base import ReductionAlgorithm

import music21


class StrongBeats(ReductionAlgorithm):

    _type = 'beat'

    def __init__(self, division=1, parts=[]):
        super(StrongBeats, self).__init__(parts=parts)
        self.division = division

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [
                 range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        mul = round(noteObj.offset / self.division)
                        if abs(self.division * mul - noteObj.offset) < 1e-3:
                            noteObj.addMark(self.key, 1)

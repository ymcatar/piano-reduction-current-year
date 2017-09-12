from .base import ReductionAlgorithm

class OffsetValue(ReductionAlgorithm):

    _type = 'offset'
    def __init__(self, parts=[]):
        super(OffsetValue, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        noteObj.addMark(self.key, noteObj.offset)

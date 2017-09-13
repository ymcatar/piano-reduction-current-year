from .base import ReductionAlgorithm

import music21


class ActiveRhythm(ReductionAlgorithm):

    _type = 'active'

    def __init__(self, division=1, parts=[]):
        super(ActiveRhythm, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        rhythm = dict()
        parts = (self.parts and [self.parts] or [
                 range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if mid not in rhythm:
                        rhythm[mid] = (0, [])

                    length = len(measure.notes)
                    if length == rhythm[mid][0]:
                        rhythm[mid] = (length, rhythm[mid][1] + [measure])
                    elif length > rhythm[mid][0]:
                        rhythm[mid] = (length, [measure])
                    mid = mid + 1

        for part in scoreObj.score:
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    mark = 0
                    if measure in rhythm[mid][1]:
                        mark = 1
                    for noteObj in measure.notes:
                        noteObj.addMark(self.key, mark)
                    mid = mid + 1

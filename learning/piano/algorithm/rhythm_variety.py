from .base import ReductionAlgorithm
from ..music.rest import Rest
from ..music.not_rest import NotRest

import music21


class RhythmVariety(ReductionAlgorithm):

    _type = 'rhythm'

    def __init__(self, parts=[]):
        super(RhythmVariety, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        # not tested yet
        parts = (self.parts and [self.parts] or [
                 range(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                previous_note = None
                previous_duration = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, Rest) and isinstance(previous_note, NotRest):
                            previous_note.addMark(self.key, 1)
                        if previous_note is None or isinstance(previous_note, Rest) or noteObj.duration.quarterLength != previous_duration:
                            noteObj.addMark(self.key, 1)
                            if isinstance(previous_note, NotRest):
                                previous_note.addMark(self.key, 1)
                        previous_note = noteObj
                        previous_duration = noteObj.duration.quarterLength

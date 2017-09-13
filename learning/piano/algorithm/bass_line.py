from .base import ReductionAlgorithm
from ..music.chord import Chord

import music21
import numpy


class BassLine(ReductionAlgorithm):

    _type = 'bass'

    @property
    def allKeys(self):
        return [self.key] + ['{}_{!s}'.format(self.key, pitchClass)
                             for pitchClass in range(0, 12)]

    def __init__(self, parts=[]):
        super(BassLine, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = self.parts or range(0, len(scoreObj.score))

        bass = []

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if len(bass) < (mid + 1):
                        bass.append((1024, None))

                    ps = []
                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                ps.append(ch_note.ps)
                        else:
                            ps.append(noteObj.ps)
                    if len(ps) > 0:
                        median = numpy.median(ps)
                        if median < bass[mid][0]:
                            bass[mid] = (median, measure)
                    mid = mid + 1

        for bassPart in bass:
            if bassPart[1] is not None:
                for noteObj in bassPart[1].notes:
                    noteObj.addMark(self.key, 1)

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    bassPart = bass[mid][1]

                    for noteObj in measure.notes:
                        bassObj = None
                        for bassNote in bassPart.notes:
                            if noteObj.offset - bassNote.offset > -1e-4:  # noteObj.offset >= baseeNote.offset
                                if bassObj is None:
                                    bassObj = bassNote
                                if bassNote.offset > bassObj.offset:  # bassNote.offset > bassObj.offset
                                    bassObj = bassNote
                        if bassObj is not None:
                            entry = [0 for x in range(0, 12)]
                            entry[bassObj.pitchClass] = 1
                            for pitchClass in range(0, 12):
                                noteObj.addMark(
                                    self.key + '_' + str(pitchClass), entry[pitchClass])
                    mid = mid + 1

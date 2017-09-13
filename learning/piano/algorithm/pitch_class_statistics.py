from .base import ReductionAlgorithm
from ..music.chord import Chord

import music21
import numpy


class PitchClassStatistics(ReductionAlgorithm):

    _type = 'pitch'

    @property
    def allKeys(self):
        return (
            ['{}_{!s}_{!s}'.format(self.key, delta, pitchClass)
             for pitchClass in range(0, 12)
             for delta in range(-self.before, self.after + 1)] +
            ['{}_{!s}'.format(self.key, pitchClass)
             for pitchClass in range(0, 12)])

    def __init__(self, parts=[], before=0, after=0):
        super(PitchClassStatistics, self).__init__(parts=parts)
        self.before = before
        self.after = after

    def createMarkingsOn(self, scoreObj):
        parts = self.parts or range(0, len(scoreObj.score))

        stat = []

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):

                    while len(stat) < (mid + 1):
                        stat.append([0 for x in range(0, 12)])

                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                pitchClass = ch_note.pitchClass
                                stat[mid][pitchClass] = stat[mid][pitchClass] + 1
                        else:
                            pitchClass = noteObj.pitchClass
                            stat[mid][pitchClass] = stat[mid][pitchClass] + 1

                    mid = mid + 1

        # FF failed, normalization did not change the result
        mid = 0
        for measure in stat:
            norm = numpy.linalg.norm(measure)
            stat[mid] = [x / norm for x in measure]
            mid = mid + 1

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):

                    measure_stat = dict()
                    for x in range(max(0, mid - self.before), min(len(stat), mid + self.after + 1)):
                        delta = x - mid
                        measure_stat[delta] = stat[x]

                    for noteObj in measure.notes:
                        if isinstance(noteObj, Chord):
                            for ch_note in noteObj:
                                for pitchClass in range(0, 12):
                                    ch_note.addMark(
                                        '{}_{!s}'.format(self.key, pitchClass),
                                        int(ch_note.pitchClass == pitchClass))
                        else:
                            for pitchClass in range(0, 12):
                                noteObj.addMark(
                                    '{}_{!s}'.format(self.key, pitchClass),
                                    int(noteObj.pitchClass == pitchClass))

                        for delta in measure_stat:
                            for pitchClass in range(0, 12):
                                noteObj.addMark(
                                    '{}_{!s}_{!s}'.format(self.key, delta, pitchClass),
                                    measure_stat[delta][pitchClass])

                    mid = mid + 1

# implementation of all algorithms

import random
import music21
import score
import note
import numpy

class ReductionAlgorithm(object):
    '''
    Base class of all parameters, each contains a list of labels to allow multiple markings by one parameter
    '''

    _type = 'unknown'

    @property
    def type(self):
        return _type

    @property
    def allKeys(self):
        return [ self.key ]

    @property
    def key(self):
        return str(self._key) + '_' + str(self.__class__._type)

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def parts(self):
        return self._parts

    def __init__(self, parts=[]):
        super(ReductionAlgorithm, self).__init__()
        self._key = '!'
        self._parts = parts

    def createMarkingsOn(self, score):
        pass

# END: class ReductionAlgorithm(object)
# ------------------------------------------------------------------------------

class OnsetAfterRest(ReductionAlgorithm):

    _type = 'onset'

    def __init__(self, parts=[]):
        super(OnsetAfterRest, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                rested = 1
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, note.Rest):
                            rested = 1
                        elif isinstance(noteObj, note.NotRest):
                            if rested:
                                noteObj.addMark(self.key, 1)
                                rested = 0

# END: class OnsetAfterRest(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class StrongBeats(ReductionAlgorithm):

    _type = 'beat'

    def __init__(self, division=1, parts=[]):
        super(StrongBeats, self).__init__(parts=parts)
        self.division = division

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        mul = round(noteObj.offset / self.division)
                        if abs(self.division * mul - noteObj.offset) < 1e-3:
                            noteObj.addMark(self.key, 1)

# END: class StrongBeats(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class RhythmVariety(ReductionAlgorithm):

    _type = 'rhythm'

    def __init__(self, parts=[]):
        super(RhythmVariety, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        # not tested yet
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                previous_note = None
                previous_duration = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, note.Rest) and isinstance(previous_note, note.NotRest):
                            previous_note.addMark(self.key, 1)
                        if previous_note is None or isinstance(previous_note, note.Rest) or noteObj.duration.quarterLength != previous_duration:
                            noteObj.addMark(self.key, 1)
                            if isinstance(previous_note, note.NotRest):
                                previous_note.addMark(self.key, 1)
                        previous_note = noteObj
                        previous_duration = noteObj.duration.quarterLength


# END: class RhythmVariety(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class ActiveRhythm(ReductionAlgorithm):

    _type = 'active'

    def __init__(self, division=1, parts=[]):
        super(ActiveRhythm, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        rhythm = dict()
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if not rhythm.has_key(mid):
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

# END: class ActiveRhythm(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class SustainedRhythm(ReductionAlgorithm):

    _type = 'sustained'

    def __init__(self, division=1, parts=[]):
        super(SustainedRhythm, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        rhythm = dict()
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if not rhythm.has_key(mid):
                        rhythm[mid] = (2036, [])

                    length = len(measure.notes)
                    if length == rhythm[mid][0]:
                        rhythm[mid] = (length, rhythm[mid][1] + [measure])
                    elif length < rhythm[mid][0]:
                        rhythm[mid] = (length, [measure])
                    mid = mid + 1

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    mark = 0
                    if measure in rhythm[mid][1]:
                        mark = 1
                    for noteObj in measure.notes:
                        noteObj.addMark(self.key, mark)
                    mid = mid + 1

# END: class SustainedRhythm(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class VerticalDoubling(ReductionAlgorithm):

    _type = 'doubling'

    def __init__(self, parts=[]):
        super(VerticalDoubling, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        notes = dict()

        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
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
                        if isinstance(noteObj, note.Chord):
                            for ch_note in noteObj:
                                if ch_note.name not in notes[mid][noteObj.offset]:
                                    notes[mid][noteObj.offset][ch_note.name] = []
                                notes[mid][noteObj.offset][ch_note.name].append(ch_note)
                        elif isinstance(noteObj, note.Note):
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


# END: class VerticalDoubling(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class Occurrence(ReductionAlgorithm):

    _type = 'occurrence'

    def __init__(self, parts=[]):
        super(Occurrence, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                notes = dict()
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    if mid not in notes:
                        notes[mid] = dict()
                    for noteObj in measure.notes:
                        if isinstance(noteObj, note.Chord):
                            for ch_note in noteObj:
                                if ch_note.name not in notes[mid]:
                                    notes[mid][ch_note.name] = []
                                notes[mid][ch_note.name].append(ch_note)
                        elif isinstance(noteObj, note.Note):
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


# END: class Occurrence(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class PitchClassStatistics(ReductionAlgorithm):

    _type = 'pitch'

    @property
    def allKeys(self):
        return [ self.key + '_' + str(delta) + '_' + str(pitchClass) for pitchClass in xrange(0, 12) for delta in xrange(-self.before, self.after + 1) ] + [ self.key + '_' + str(pitchClass) for pitchClass in xrange(0, 12) ]

    def __init__(self, parts=[], before=0, after=0):
        super(PitchClassStatistics, self).__init__(parts=parts)
        self.before = before
        self.after = after

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]

        stat = []

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):

                    while len(stat) < (mid + 1):
                        stat.append([ 0 for x in xrange(0, 12) ])

                    for noteObj in measure.notes:
                        if isinstance(noteObj, note.Chord):
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
            stat[mid] = [ x / norm for x in measure ]
            mid = mid + 1

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):

                    measure_stat = dict()
                    for x in xrange(max(0, mid - self.before), min(len(stat), mid + self.after + 1)):
                        delta = x - mid
                        measure_stat[delta] = stat[x]

                    for noteObj in measure.notes:
                        if isinstance(noteObj, note.Chord):
                            for ch_note in noteObj:
                                for pitchClass in xrange(0, 12):
                                    ch_note.addMark(self.key + '_' + str(pitchClass), ((ch_note.pitchClass == pitchClass) and [1] or [0])[0])
                        else:
                            for pitchClass in xrange(0, 12):
                                noteObj.addMark(self.key + '_' + str(pitchClass), ((noteObj.pitchClass == pitchClass) and [1] or [0])[0])

                        for delta in measure_stat:
                            for pitchClass in xrange(0, 12):
                                noteObj.addMark(self.key + '_' + str(delta) + '_' + str(pitchClass), measure_stat[delta][pitchClass])

                    mid = mid + 1


# END: class PitchClassStatistics(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class BassLine(ReductionAlgorithm):

    _type = 'bass'

    @property
    def allKeys(self):
        return [ self.key ] + [ self.key + '_' + str(pitchClass) for pitchClass in xrange(0, 12) ]

    def __init__(self, parts=[]):
        super(BassLine, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]

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
                        if isinstance(noteObj, note.Chord):
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
                            if noteObj.offset - bassNote.offset > -1e-4: # noteObj.offset >= baseeNote.offset
                                if bassObj is None:
                                    bassObj = bassNote
                                if bassNote.offset > bassObj.offset: # bassNote.offset > bassObj.offset
                                    bassObj = bassNote
                        if bassObj is not None:
                            entry = [ 0 for x in xrange(0, 12) ]
                            entry[bassObj.pitchClass] = 1
                            for pitchClass in xrange(0, 12):
                                noteObj.addMark(self.key + '_' + str(pitchClass), entry[pitchClass])
                    mid = mid + 1


# END: class BassPart(ReductionAlgorithm)
# ------------------------------------------------------------------------------


class OffsetValue(ReductionAlgorithm):

    _type = 'offset'
    def __init__(self, parts=[]):
        super(OffsetValue, self).__init__(parts=parts)

    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [xrange(0, len(scoreObj.score))])[0]
        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        noteObj.addMark(self.key, noteObj.offset)

# END: class OffsetValue(ReductionAlgorithm)
# ------------------------------------------------------------------------------

class EntranceEffect(ReductionAlgorithm):

    _type = 'entrance'

    def __init__(self, parts=[]):
        super(EntranceEffect, self).__init__(parts=parts)
    
    def createMarkingsOn(self, scoreObj):
        parts = (self.parts and [self.parts] or [ xrange(0, len(scoreObj.score)) ])[0]

        for pid in parts:
            part = scoreObj.score[pid]
            for voice in part.voices:
                rested = 1
                lastOnsetNote = None
                lastOnsetMeasureOffset = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, note.Rest):
                            rested = 1
                        elif isinstance(noteObj, note.NotRest):
                            if rested:
                                lastOnsetNote = noteObj
                                lastOnsetMeasureOffset = measure.offset
                                rested = 0
                            noteObj.addMark(self.key, float(noteObj.offset - lastOnsetNote.offset + measure.offset - lastOnsetMeasureOffset))

# END: class EntranceEffect(ReductionAlgorithm)
# ------------------------------------------------------------------------------


class SimpleAlignment(object):

    def __init__(self):
        super(SimpleAlignment, self).__init__()

    def alignScores(self, sampleInput, sampleOutput):
        existence = set()

        for part in sampleOutput.score:
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        if isinstance(noteObj, note.Chord):
                            for ch_note in noteObj:
                                existence.add((mid, noteObj.offset, ch_note.nameWithOctave))
                        elif isinstance(noteObj, note.Note):
                            existence.add((mid, noteObj.offset, noteObj.nameWithOctave))
                    mid = mid + 1

        for part in sampleInput.score:
            for voice in part.voices:
                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        if isinstance(noteObj, note.Chord):
                            for ch_note in noteObj:
                                mark = 0
                                key = (mid, noteObj.offset, ch_note.nameWithOctave)
                                if key in existence:
                                    mark = 1
                                ch_note.align = mark
                        elif isinstance(noteObj, note.Note):
                            mark = 0
                            key = (mid, noteObj.offset, noteObj.nameWithOctave)
                            if key in existence:
                                mark = 1
                            noteObj.align = mark
                    mid = mid + 1

# END: class Alignment(object)
# ------------------------------------------------------------------------------

from music21 import chord, clef, duration as duration_, layout, note, stream
import numpy as np


class PostProcessor(object):
    def generate_piano_score(self, score_obj, reduced=True, playable=True,
                             measures=None):
        leftRest = []
        leftHand = []

        rightRest = []
        rightHand = []

        measureLength = []
        measureOffset = []
        signature = []

        for part in score_obj.score.parts:
            for mid, measure in enumerate(part.getElementsByClass(stream.Measure)):
                while len(leftRest) < mid + 1:
                    leftRest.append([])
                while len(leftHand) < mid + 1:
                    leftHand.append([])

                while len(rightRest) < mid + 1:
                    rightRest.append([])
                while len(rightHand) < mid + 1:
                    rightHand.append([])

                while len(measureLength) < mid + 1:
                    measureLength.append(0)
                while len(measureOffset) < mid + 1:
                    measureOffset.append(0)
                measureOffset[mid] = measure.offset

                while len(signature) < mid + 1:
                    signature.append((None, None))
                signature[mid] = (measure.keySignature,
                                  measure.timeSignature)
                for voice in measure.voices:
                    restList = []
                    noteList = []
                    notePs = []

                    for noteObj in voice.notesAndRests:
                        measureLength[mid] = max(
                            measureLength[mid], noteObj.offset + noteObj.quarterLength)

                        if isinstance(noteObj, note.Rest):
                            restList.append(
                                (noteObj.offset, noteObj.offset + noteObj.quarterLength))
                        elif isinstance(noteObj, chord.Chord):
                            for ch_note in noteObj:
                                if ch_note.editorial.misc['align'] >= 0.5 or not reduced:
                                    notePs.append(ch_note.ps)
                                    noteList.append(
                                        (noteObj.offset, ch_note.nameWithOctave, ch_note.tie))
                        elif isinstance(noteObj, note.Note):
                            if noteObj.editorial.misc['align'] >= 0.5 or not reduced:
                                notePs.append(noteObj.ps)
                                noteList.append(
                                    (noteObj.offset, noteObj.nameWithOctave, noteObj.tie))

                    if len(noteList) > 0:
                        median = np.median(notePs)

                        if median < 60:
                            leftRest[mid].append(restList)
                            leftHand[mid].extend(noteList)
                        else:
                            rightRest[mid].append(restList)
                            rightHand[mid].extend(noteList)

                    mid = mid + 1

        leftStaff = stream.Part()
        rightStaff = stream.Part()

        leftTie = dict()
        rightTie = dict()

        for mid in range(0, len(leftHand)):
            if measures is None or mid in measures:
                rightMeasure = self._createMeasure(
                    notes=rightHand[mid], rests=rightRest[mid],
                    tieRef=rightTie, measureLength=measureLength[mid],
                    playable=playable, mid=None)
                leftMeasure = self._createMeasure(
                    notes=leftHand[mid], rests=leftRest[mid], tieRef=leftTie,
                    measureLength=measureLength[mid], playable=playable,
                    mid=None)

                if mid == 0:
                    rightMeasure.clef = clef.TrebleClef()
                    leftMeasure.clef = clef.BassClef()

                rightMeasure.keySignature = signature[mid][0]
                rightMeasure.timeSignature = signature[mid][1]

                leftMeasure.keySignature = signature[mid][0]
                leftMeasure.timeSignature = signature[mid][1]

                leftStaff.insert(measureOffset[mid], leftMeasure)
                rightStaff.insert(measureOffset[mid], rightMeasure)

        result = stream.Score()

        result.insert(0, rightStaff)
        result.insert(0, leftStaff)

        staffGroup = layout.StaffGroup(
            [rightStaff, leftStaff], name='Marimba', abbreviation='Mba.',
            symbol='brace')
        staffGroup.barTogether = 'yes'

        result.insert(0, staffGroup)

        return result

    def _createMeasure(self, notes=[], rests=[], tieRef=dict(),
                       measureLength=0, playable=True, mid=None):
        result = stream.Measure()

        _notes = dict()
        for noteTuple in notes:
            if noteTuple[0] not in _notes:
                _notes[noteTuple[0]] = []
            _notes[noteTuple[0]].append((noteTuple[1], noteTuple[2]))

        _rests = dict()
        for restList in rests:
            for restTuple in restList:
                if restTuple[0] not in _rests:
                    _rests[restTuple[0]] = 0
                _rests[restTuple[0]] = _rests[restTuple[0]] + 1
                if restTuple[1] not in _rests:
                    _rests[restTuple[1]] = 0
                _rests[restTuple[1]] = _rests[restTuple[1]] - 1

        realNotes = []
        restCount = 0
        restStart = -1

        for offset in _rests:
            restCount = restCount + _rests[offset]
            if restStart == -1 and restCount == len(rests):
                restStart = offset
            elif restStart != -1 and restCount != len(rests):
                realNotes.append([restStart, 0, []])
                restStart = -1

        for offset in _notes:
            realNotes.append([offset, 0, _notes[offset]])

        realNotes = sorted(realNotes)

        if len(realNotes) > 0:
            first_note = realNotes[0]
            if len(first_note[2]) == 0:
                first_note[1] = first_note[1] + first_note[0]
                first_note[0] = 0
            elif abs(first_note[0]) > 1e-4:
                realNotes.append([0, first_note[0], []])

        realNotes = sorted(realNotes)

        if len(realNotes) > 1:
            for nid in range(0, len(realNotes) - 1):
                realNotes[nid][1] = realNotes[nid + 1][0] - realNotes[nid][0]
            realNotes[len(realNotes) - 1][1] = measureLength - \
                (realNotes[len(realNotes) - 1][0])

        ps = []
        for noteTuple in sorted(realNotes):
            _notes = noteTuple[2]

            if len(_notes) > 0:
                for _pitch in _notes:
                    if _pitch[1] is None or _pitch[1].type == 'start':
                        ps.append(note.Note(_pitch[0]).ps)

        median = 60
        if len(ps) > 0:
            median = np.median(ps)
        # print median, ps

        if mid == 4:
            print(sorted(realNotes))
            print(realNotes)

        for noteTuple in sorted(realNotes):
            offset = noteTuple[0]
            duration = noteTuple[1]
            _notes = noteTuple[2]

            pitch = set()
            if len(_notes) > 0:
                for _pitch in _notes:
                    if _pitch[1] is None or _pitch[1].type == 'start':
                        pitch.add(_pitch[0])

            pitch = list(pitch)
            insertNote = None

            if len(pitch) > 1:

                ch_notes = []

                ch_max_ps = 0
                ch_max_note = None
                ch_min_ps = 1024
                ch_min_note = None

                for p in pitch:
                    noteObj = note.Note(
                        p, duration=duration_.Duration(duration))
                    ch_notes.append(noteObj)
                    if noteObj.ps > ch_max_ps:
                        ch_max_ps = noteObj.ps
                        ch_max_note = noteObj
                    if noteObj.ps < ch_min_ps:
                        ch_min_ps = noteObj.ps
                        ch_min_note = noteObj

                if playable:

                    while ch_max_ps - ch_min_ps > 12:
                        if median > 60:
                            ch_min_note.octave = ch_min_note.pitch.implicitOctave + 1
                        else:
                            ch_max_note.octave = ch_max_note.pitch.implicitOctave - 1

                        ch_max_ps = 0
                        ch_max_note = None
                        ch_min_ps = 1024
                        ch_min_note = None
                        for noteObj in ch_notes:
                            if noteObj.ps > ch_max_ps:
                                ch_max_ps = noteObj.ps
                                ch_max_note = noteObj
                            if noteObj.ps < ch_min_ps:
                                ch_min_ps = noteObj.ps
                                ch_min_note = noteObj

                insertNote = chord.Chord(ch_notes)
                insertNote.duration = duration_.Duration(duration)
            elif len(pitch) == 1:
                insertNote = note.Note(
                    pitch[0], duration=duration_.Duration(duration))
            else:
                insertNote = note.Rest(
                    duration=duration_.Duration(duration))

            if mid == 4:
                print(insertNote, offset, duration, insertNote.quarterLength)
            if duration > 1e-2:
                result.insert(offset, insertNote)

        if not result.notesAndRests:
            result.insert(0, note.Rest(
                duration=duration_.Duration(measureLength)))

        if mid == 4:
            result.show('text')

        return result

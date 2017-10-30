from music21 import (chord, clef, duration as duration_, instrument, key,
                     layout, note, meter, stream)
from .algorithm.base import iter_notes
import numpy as np
from itertools import count


LEFT_HAND = 1
RIGHT_HAND = 2


def default_keep_func(n):
    return n.editorial.misc['align'] >= 0.5


class PostProcessor(object):
    def generate_piano_score(self, score_obj, reduced=True, playable=True,
                             measures=None):
        if reduced:
            keep_func = default_keep_func
        else:
            keep_func = lambda n: True

        self.assign_hands(score_obj, keep_func=keep_func)

        # Must be run before processing measures, so that key signatures will
        # agree.
        score_obj.score.toWrittenPitch(inPlace=True)

        HANDS = [LEFT_HAND, RIGHT_HAND]
        parts = [stream.Part(), stream.Part()]

        measure_offset = 0

        for i in count(0):
            bar = score_obj.score.measure(i, collect=(), gatherSpanners=False)
            measures = bar.recurse(skipSelf=False).getElementsByClass('Measure')
            if not measures:
                # Measure 0 is the pickup (partial) measure and may not exist
                if i == 0: continue
                else: break

            bar_length = measures[0].barDuration.quarterLength

            for hand, part in zip(HANDS, parts):
                key_signature, time_signature = None, None
                notes, rest_sets = [], []

                for p in bar.parts:
                    rests = []
                    for elem in p.recurse(skipSelf=False):
                        if isinstance(elem, key.KeySignature):
                            key_signature = elem

                        elif isinstance(elem, meter.TimeSignature):
                            time_signature = elem

                        elif isinstance(elem, note.Note):
                            if elem.editorial.misc.get('hand') == hand:
                                notes.append((
                                    elem.offset,
                                    elem.nameWithOctave,
                                    elem.tie))

                        elif isinstance(elem, chord.Chord):
                            for n in elem:
                                if elem.editorial.misc.get('hand') == hand:
                                    notes.append((
                                        elem.offset,
                                        n.nameWithOctave,
                                        n.tie))

                        elif isinstance(elem, note.Rest):
                            rests.append((
                                elem.offset,
                                elem.offset + elem.duration.quarterLength))

                        else:
                            # Ignore other stuff by default
                            pass

                    rest_sets.append(rests)

                out_measure = self._createMeasure(
                    notes=notes, rests=rest_sets,
                    measureLength=bar_length)

                if key_signature:
                    out_measure.insert(0, key_signature)
                if time_signature:
                    out_measure.insert(0, time_signature)

                part.insert(measure_offset, out_measure)

            measure_offset += bar_length

        clefs = [
            clef.BassClef(),
            clef.TrebleClef()
            ]

        for part, clef_ in zip(parts, clefs):
            # Set the instrument to piano
            piano = instrument.fromString('Piano')
            part.insert(0, piano)
            part.insert(0, clef_)

        result = stream.Score()

        result.insert(0, parts[1])  # Right hand
        result.insert(0, parts[0])  # Left hand

        staff_group = layout.StaffGroup(
            [parts[1], parts[0]], name='Piano', abbreviation='Pno.',
            symbol='brace')
        staff_group.barTogether = 'yes'

        result.insert(0, staff_group)

        return result

    def assign_hands(self, score_obj, keep_func=default_keep_func,
                     threshold=60):
        for bar in score_obj.by_bar:
            for measure in bar.recurse(
                    skipSelf=False).getElementsByClass(stream.Measure):
                for voice in measure.voices:
                    pss = [n.pitch.ps for n in iter_notes(measure, recurse=True)
                           if keep_func(n)]

                    if pss:
                        median = np.median(pss)

                        hand = RIGHT_HAND if median >= 60 else LEFT_HAND

                        for n in iter_notes(measure, recurse=True):
                            if keep_func(n):
                                n.editorial.misc['hand'] = hand

    def _createMeasure(self, notes=[], rests=[], tieRef=dict(),
                       measureLength=0, playable=True):
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
                        ps.append(note.Note(_pitch[0]).pitch.ps)

        median = 60
        if len(ps) > 0:
            median = np.median(ps)
        # print median, ps

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
                    if noteObj.pitch.ps > ch_max_ps:
                        ch_max_ps = noteObj.pitch.ps
                        ch_max_note = noteObj
                    if noteObj.pitch.ps < ch_min_ps:
                        ch_min_ps = noteObj.pitch.ps
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
                            if noteObj.pitch.ps > ch_max_ps:
                                ch_max_ps = noteObj.pitch.ps
                                ch_max_note = noteObj
                            if noteObj.pitch.ps < ch_min_ps:
                                ch_min_ps = noteObj.pitch.ps
                                ch_min_note = noteObj

                insertNote = chord.Chord(ch_notes)
                insertNote.duration = duration_.Duration(duration)
            elif len(pitch) == 1:
                insertNote = note.Note(
                    pitch[0], duration=duration_.Duration(duration))
            else:
                insertNote = note.Rest(
                    duration=duration_.Duration(duration))

            if duration > 1e-2:
                result.insert(offset, insertNote)

        if not result.notesAndRests:
            result.insert(0, note.Rest(
                duration=duration_.Duration(measureLength)))

        return result

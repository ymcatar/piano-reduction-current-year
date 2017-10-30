from music21 import (chord, clef, duration as duration, instrument, key,
                     layout, note, meter, stream)
from .algorithm.base import iter_notes
import numpy as np
from itertools import count
from collections import defaultdict


LEFT_HAND = 1
RIGHT_HAND = 2


def default_keep_func(n):
    return n.editorial.misc['align'] >= 0.5


class PostProcessor(object):
    def generate_piano_score(self, score_obj, reduced=True, playable=True,
                             assign_hands=True):
        if assign_hands:
            keep_func = default_keep_func if reduced else lambda n: True
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
                                    elem.offset, elem.pitch.ps, elem.tie))

                        elif isinstance(elem, chord.Chord):
                            for n in elem:
                                if elem.editorial.misc.get('hand') == hand:
                                    notes.append((
                                        elem.offset, n.pitch.ps, n.tie))

                        elif isinstance(elem, note.Rest):
                            rests.append((
                                elem.offset,
                                elem.offset + elem.duration.quarterLength))

                        else:
                            # Ignore other stuff by default
                            pass

                    rest_sets.append(rests)

                out_measure = self._create_measure(
                    notes=notes, rest_sets=rest_sets, measure_length=bar_length)

                if key_signature:
                    out_measure.insert(key_signature)
                if time_signature:
                    out_measure.insert(time_signature)

                part.insert(measure_offset, out_measure)

            measure_offset += bar_length

        clefs = [clef.BassClef(), clef.TrebleClef()]
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

    def _create_measure(self, notes=[], rest_sets=[], tieRef=dict(),
                       measure_length=0, playable=True):
        # list of [offset, quarter length, list of (ps, tie)]
        out_notes = []

        # Add all notes to output
        notes_by_offset = defaultdict(lambda: [])
        for offset, pitch, tie in notes:
            notes_by_offset[offset].append((pitch, tie))

        for offset, notes in notes_by_offset.items():
            out_notes.append([offset, 0, notes])

        # Find the change in the number of occurring notes at each offset
        rest_diffs = defaultdict(lambda: 0)
        for rests in rest_sets:
            for start, end in rests:
                rest_diffs[start] += 1
                rest_diffs[end] -= 1

        # Find durations where all voices are silent and add them to output
        rest_count = 0
        rest_start = None
        for offset, diff in sorted(rest_diffs.items()):
            rest_count += diff
            if rest_start is None and rest_count == len(rests):
                rest_start = offset
            elif rest_start is not None and rest_count != len(rests):
                out_notes.append([rest_start, 0, []])
                rest_start = None

        out_notes = sorted(out_notes)

        if out_notes:
            # Add a rest at the measure start if there is a gap
            offset, length, notes = first_note = out_notes[0]
            if not notes:
                first_note[1] = first_note[1] + first_note[0]
                first_note[0] = 0
            elif abs(offset) > 1e-4:
                out_notes.insert(0, [0, offset, []])

            # Change the end of each note to the start of next note
            for nid in range(0, len(out_notes) - 1):
                this_note, next_note = out_notes[nid:nid+2]
                this_note[1] = next_note[0] - this_note[0]
            out_notes[-1][1] = measure_length - out_notes[-1][0]

        pss = set()
        for _, _, notes in out_notes:
            if len(notes) > 0:
                for ps, tie in notes:
                    if tie is None or tie.type == 'start':
                        pss.add(ps)
        median = np.median(list(pss)) if pss else 60

        result = stream.Measure()
        for offset, length, notes in out_notes:
            pss = set()
            for ps, tie in notes:
                if tie is None or tie.type == 'start':
                    pss.add(ps)

            pss = set(pss)
            note_to_insert = None

            if len(pss) > 1:
                if playable:
                    # Transform chords to playable ones
                    max_ps, min_ps = max(pss), min(pss)
                    while max(pss) - min(pss) > 12:
                        if median > 60:
                            pss.add(min_ps + 13)
                            pss.remove(min_ps)
                        else:
                            pss.add(max_ps - 13)
                            pss.remove(max_ps)
                        max_ps, min_ps = max(pss), min(pss)

                chord_notes = []
                for ps in pss:
                    n = note.Note(ps, duration=duration.Duration(length))
                    chord_notes.append(n)

                note_to_insert = chord.Chord(
                    chord_notes, duration=duration.Duration(length))

            elif len(pss) == 1:
                note_to_insert = note.Note(
                    list(pss)[0], duration=duration.Duration(length))

            else:
                note_to_insert = note.Rest(duration=duration.Duration(length))

            if length > 1e-2:
                result.insert(offset, note_to_insert)

        if not result.notesAndRests:
            result.insert(0, note.Rest(
                duration=duration.Duration(measure_length)))

        return result

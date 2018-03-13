#!/usr/bin/env python3

import music21
import numpy as np

from collections import defaultdict
from itertools import count

RIGHT_HAND = 'R'
LEFT_HAND = 'L'


class MultipartReducer(object):

    def __init__(self, score):
        self.score = score

    def reduce(self):

        HANDS = [LEFT_HAND, RIGHT_HAND]
        parts = [music21.stream.Part(), music21.stream.Part()]

        measure_offset = 0
        for i in count(0):

            bar = self.score.measure(i, collect=(), gatherSpanners=False)
            measures = bar.recurse(skipSelf=False).getElementsByClass('Measure')

            if not measures:
                # Measures is the pickup (partial) measure and may not exist
                if i == 0:
                    continue
                else:
                    break

            bar_length = measures[0].barDuration.quarterLength
            for hand, part in zip(HANDS, parts):

                key_signature, time_signature = None, None
                notes, rest_sets, tie_sets = [], [], []

                for p in bar.parts:
                    rests = []

                    for elem in p.recurse(skipSelf=False):

                        # ignore the note if it is marked as deleted
                        if elem.editorial.misc.get('deleted'):
                            continue

                        if isinstance(elem, music21.key.KeySignature):
                            key_signature = elem

                        elif isinstance(elem, music21.meter.TimeSignature):
                            time_signature = elem

                        elif isinstance(elem, music21.note.Note):
                            if elem.editorial.misc.get('hand') == hand:
                                notes.append((
                                    elem.offset,
                                    elem.pitch,
                                    elem.duration,
                                    elem.tie))

                        elif isinstance(elem, music21.chord.Chord):
                            for n in elem:
                                if elem.editorial.misc.get('hand') == hand:
                                    notes.append((
                                        elem.offset,
                                        n.pitch,
                                        n.duration,
                                        n.tie))

                        else:
                            # Ignore other stuff by default
                            pass

                out_measure = self._create_measure(
                    notes=notes,
                    measure_length=bar_length)

                if key_signature:
                    out_measure.insert(key_signature)

                if time_signature:
                    out_measure.insert(time_signature)

                part.insert(measure_offset, out_measure)

            measure_offset += bar_length

        clefs = [music21.clef.BassClef(), music21.clef.TrebleClef()]
        for part, clef_ in zip(parts, clefs):
            # Set the instrument to piano
            piano = music21.instrument.fromString('Piano')
            part.insert(0, piano)
            part.insert(0, clef_)

        result = music21.stream.Score()
        result.insert(0, parts[1])  # Right hand
        result.insert(0, parts[0])  # Left hand

        staff_group = music21.layout.StaffGroup(
            [parts[1], parts[0]], name='Piano', abbreviation='Pno.',
            symbol='brace')
        staff_group.barTogether = 'yes'

        result.insert(0, staff_group)

        return result

    def _create_measure(self, notes=[], measure_length=0):

        result = music21.stream.Measure()

        offset_map = defaultdict(lambda: defaultdict(lambda: []))
        tie_map = defaultdict(lambda: [])

        for offset, pitch, duration, ties in notes:
            offset_map[offset][duration.quarterLength].append(pitch)
            if ties:
                tie_map[note].append(ties)

        # merge notes with same offset and duration into a single chord
        for offset_item in offset_map.values():
            for duration, duration_item in offset_item.items():
                if len(duration_item) == 1:
                    offset_item[duration] = duration_item[0]
                else:
                    offset_item[duration] = music21.chord.Chord(duration_item)

        print(offset_map)

        return result

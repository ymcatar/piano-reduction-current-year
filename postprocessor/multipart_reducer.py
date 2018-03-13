#!/usr/bin/env python3

import music21
import numpy as np

from collections import defaultdict
from itertools import count
from intervaltree import IntervalTree

RIGHT_HAND = 'R'
LEFT_HAND = 'L'

# util function to find any gap within a given interval tree
def find_slient_interval(intervals, start, end):
    # there is no note within the interval
    if len(intervals) == 0:
        return [(start, end)]
    # base case
    if start >= end:
        return []
    # if the entire interval have no item, return (start, end)
    items = intervals[start:end]
    if len(items) == 0:
        return [(start, end)]
    # detect if there is gap between start & first item / last item & end
    results = []
    min_start = intervals.begin()
    max_end = intervals.end()
    if start != min_start and start < min_start:
        results.append((start, min_start))
        start = min_start
    if end != max_end and max_end < end:
        results.append((max_end, end))
        end = max_end
    # catch the remaining gaps recursively
    for item in items:
        item_start, _, _ = item
        results += find_slient_interval(intervals, start, item_start)
    return results

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
                                notes.append(elem)

                        elif isinstance(elem, music21.chord.Chord):
                            for n in elem:
                                if elem.editorial.misc.get('hand') == hand:
                                    notes.append(elem)

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

        # no note within the measure?
        if len(notes) == 0:
            return result

        offset_map = defaultdict(lambda: defaultdict(lambda: []))
        tie_map = defaultdict(lambda: [])

        for n in notes:
            offset_map[n.offset][n.duration.quarterLength].append(n.pitch)
            if n.tie:
                tie_map[id(n)].append(n.tie)

        # merge notes with same offset and duration into a single chord
        for offset_item in offset_map.values():
            for duration, duration_item in offset_item.items():
                if len(duration_item) == 1:
                    offset_item[duration] = duration_item[0]
                else:
                    offset_item[duration] = music21.chord.Chord(duration_item)

        offset_map = dict(offset_map)
        for key in offset_map.keys():
            offset_map[key] = dict(offset_map[key])

        # construct an interval for all the note intervals
        intervals = IntervalTree()
        for start in offset_map.keys():
            for duration in offset_map[start].keys():
                if duration > 0.0:
                    intervals.addi(start, start + duration, offset_map[start][duration])

        # find out all the time intervals with no active note playing
        # slient_intervals = find_slient_interval(intervals, 0.0, measure_length)
        # for start, end in slient_intervals:
            # intervals.addi(start, end, music21.note.Rest(quarterLength=(end-start)))

        # add all the notes to the measure
        voices = defaultdict(lambda: [])
        current_voice = 0

        while len(intervals) > 0:
            prev_end = None
            temp_intervals = intervals.copy()
            for item in intervals:
                start, end, elem = item
                if prev_end is None or end >= prev_end:
                    if isinstance(elem, music21.pitch.Pitch):
                        elem = music21.note.Note(elem, quarterLength=(end-start))
                    voices[current_voice].append((start, elem))
                    temp_intervals.remove(item)
                    prev_end = end
            intervals = temp_intervals
            current_voice += 1

        for key in voices.keys():
            temp = IntervalTree()
            for note in voices[0]:
                start, elem = note
                temp.addi(start, start + elem.duration.quarterLength, elem)
            rests = find_slient_interval(temp, 0, measure_length)
            for item in rests:
                start, end = item
                voices[key].append((start, music21.note.Rest(quarterLength=(end-start))))
            voices[key] = sorted(voices[key], key=lambda i: i[0])

        for note in voices[0]:
            start, elem = note
            elem.offset = start
            if start + elem.quarterLength > measure_length:
                elem.quarterLength = measure_length - start
            result.insert(elem)

        print(list((i[1].offset, i[1].offset + i[1].quarterLength) for i in voices[0]))

        return result

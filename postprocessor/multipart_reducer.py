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

    intervals = sorted(intervals, key=lambda n: n[0])  # sort by starting time
    results = []

    curr_start = 0.0
    for item in intervals:
        item_start, item_end, _ = item
        if item_start - curr_start >= 1e-4:  # curr_start < start
            results.append((curr_start, item_start))
        curr_start = item_end

    if end - curr_start >= 1e-4:  # curr_start < end
        results.append((curr_start, end))

    return results


class MultipartReducer(object):
    def __init__(self, score, max_hand_span=7):

        self.score = score
        self.max_hand_span = max_hand_span

    def reduce(self):

        HANDS = [LEFT_HAND, RIGHT_HAND]
        parts = [music21.stream.Part(), music21.stream.Part()]

        measure_offset = 0

        key_signature, time_signature = None, None
        signature_just_changed = False

        for i in count(0):

            bar = self.score.measure(i, collect=(), gatherSpanners=False)
            measures = bar.recurse(
                skipSelf=False).getElementsByClass('Measure')

            if not measures:
                # Measures is the pickup (partial) measure and may not exist
                if i == 0:
                    continue
                else:
                    break

            bar_length = measures[0].barDuration.quarterLength

            for hand, part in zip(HANDS, parts):

                notes = []

                for p in bar.parts:

                    for elem in p.recurse(skipSelf=False):

                        # ignore the note if it is marked as deleted
                        if elem.editorial.misc.get('deleted'):
                            continue

                        if isinstance(elem, music21.key.KeySignature):
                            key_signature = elem
                            signature_just_changed = True

                        elif isinstance(elem, music21.meter.TimeSignature):
                            time_signature = elem
                            bar_length = elem.barDuration.quarterLength
                            signature_just_changed = True

                        elif isinstance(elem, music21.note.Note):
                            if 'hand' not in elem.editorial.misc:
                                continue
                            if hand == LEFT_HAND and elem.pitch.ps < 60:
                                notes.append(elem)
                            elif hand == RIGHT_HAND and elem.pitch.ps >= 60:
                                notes.append(elem)

                        elif isinstance(elem, music21.chord.Chord):
                            for n in elem:
                                if 'hand' not in n.editorial.misc:
                                    continue
                                if hand == LEFT_HAND and n.pitch.ps < 60:
                                    notes.append(n)
                                elif hand == RIGHT_HAND and n.pitch.ps >= 60:
                                    notes.append(n)

                        else:
                            # Ignore other stuff by default
                            pass

                out_measure = self._create_measure(
                    notes=notes, measure_length=bar_length)

                if signature_just_changed and time_signature:
                    out_measure.insert(time_signature)
                    signature_just_changed = False

                if key_signature:
                    out_measure.insert(key_signature)

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
            [parts[1], parts[0]],
            name='Piano',
            abbreviation='Pno.',
            symbol='brace')
        staff_group.barTogether = 'yes'

        result.insert(0, staff_group)

        return result

    def _create_measure(self, notes=[], measure_length=4.0):

        result = music21.stream.Measure()

        # no note within the measure?
        if len(notes) == 0:
            return result

        offset_map = defaultdict(lambda: defaultdict(lambda: []))
        tie_map = {}

        for n in notes:
            offset_map[n.offset][n.duration.quarterLength].append(n.pitch)
            if n.tie:
                tie_map[(n.offset, n.duration.quarterLength,
                         n.pitch.ps)] = n.tie

        # merge notes with same offset and duration into a single chord

        for offset, offset_item in offset_map.items():

            for duration, pitches in offset_item.items():

                if len(pitches) == 1:
                    offset_item[duration] = music21.note.Note(pitches[0])
                    if (offset, duration, pitches[0].ps) in tie_map:
                        offset_item[duration].tie = tie_map[(offset, duration,
                                                             pitches[0].ps)]
                else:
                    pitches = list(set(pitches))
                    offset_item[duration] = music21.chord.Chord(pitches)
                    # check if all notes in chord have the same kind of tie
                    valid = True
                    prev_tie = None
                    for pitch in pitches:
                        index = (offset, duration, pitch.ps)
                        if index not in tie_map:
                            valid = False
                            break
                        if prev_tie is None:
                            prev_tie = tie_map[index]
                        if prev_tie.type != tie_map[index].type:
                            valid = False
                            break
                    if valid:
                        offset_item[duration].tie = tie_map[index]

                offset_item[duration].duration.quarterLength = duration

        offset_map = dict(offset_map)
        for key in offset_map.keys():
            offset_map[key] = dict(offset_map[key])

        # construct an interval for all the note intervals
        intervals = IntervalTree()
        for start in offset_map.keys():
            for duration in offset_map[start].keys():
                if duration > 0.0:
                    intervals.addi(start, start + duration,
                                   offset_map[start][duration])

        # add all the notes to the measure
        voices = defaultdict(lambda: [])
        current_voice = 0

        intervals = sorted(intervals, key=lambda n: (n[0], n[1]))

        while len(intervals) > 0:
            prev_end = None
            temp_intervals = intervals.copy()
            for item in intervals:
                start, end, elem = item
                if prev_end is None or start >= prev_end:
                    voices[current_voice].append((start, end, elem))
                    temp_intervals.remove(item)
                    prev_end = end
            intervals = temp_intervals
            current_voice += 1

        rests_length_in_voice = {}

        for key in voices.keys():

            temp = IntervalTree()

            for note in voices[key]:
                start, end, elem = note
                temp.addi(start, end, elem)

            rests = find_slient_interval(temp, 0, measure_length)
            rests_length_in_voice[key] = sum((b - a for a, b in rests), 0)

            for item in rests:
                start, end = item
                voices[key].append(
                    (start, end,
                     music21.note.Rest(quarterLength=(end - start))))

            voices[key] = sorted(voices[key], key=lambda i: i[0])

        # probably too many voices

        if len(voices) > 1:

            offset_map = defaultdict(lambda: [])
            for key, notes in voices.items():
                for i, item in enumerate(notes):
                    start, end, n = item
                    offset_map[start].append((key, n.duration.quarterLength, n,
                                              i))

            if len(voices) > 2:
                excess_voices = sorted(
                    ((v, k) for k, v in rests_length_in_voice.items()),
                    reverse=True)[:len(voices) - 2]
                excess_voices = set(i[1] for i in excess_voices)
            else:
                excess_voices = set(k
                                    for k, v in rests_length_in_voice.items()
                                    if v >= measure_length / 2.0)

            for key in excess_voices:

                while len(voices[key]) > 0:

                    # pop a note from the excess voice
                    start, end, n1 = voices[key].pop()
                    if isinstance(n1, music21.note.Rest):
                        continue

                    duration = n1.duration.quarterLength

                    # see if there are notes with the same start in other voices
                    candidates = [
                        i for i in offset_map[start]
                        if i[0] not in excess_voices and i[0] != key
                    ]

                    if len(candidates) > 0:

                        # find the best match
                        best = min(
                            candidates, key=lambda n: abs(n[1] - duration))

                        best_key, _, n2, index = best
                        _, new_end, _ = voices[best_key][index]

                        notes = []

                        if isinstance(n1, music21.note.Note):
                            notes = [n1]
                        elif isinstance(n1, music21.chord.Chord):
                            notes = n1._notes

                        for n in notes:

                            if isinstance(n2, music21.chord.Chord):
                                # print('added to chord', n)
                                pitches = [n.pitch
                                           ] + [n.pitch for n in n2._notes]
                                voices[best_key][index] = (
                                    start, new_end,
                                    music21.chord.Chord(pitches))

                            elif not n2.isRest:  # a note
                                # replace the note with a chord
                                # print('added to note', n)
                                voices[best_key][index] = (start, new_end,
                                                           music21.chord.Chord(
                                                               [
                                                                   n.pitch,
                                                                   n2.pitch
                                                               ]))

                            elif n2.isRest:
                                # fill the rest
                                # print('added to rest', n)
                                voices[best_key][index] = (start, new_end,
                                                           music21.note.Note(
                                                               n.pitch))

                    else:

                        pass
                        # no good candidate => look for potential rest
                        # print(n1)

        if len(voices) <= 4:
            for i, v in enumerate(voices.values()):
                voice = music21.stream.Voice(id=i)
                for note in v:
                    start, end, elem = note
                    elem.offset = start
                    elem.quarterLength = end - start
                    voice.insert(start, elem)
                voice.makeAccidentals(useKeySignature=True)
                result.insert(0, voice)
        else:
            # FIXME
            print('There are too many voices. Ignoring ...', len(voices))

        return result

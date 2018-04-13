#!/usr/bin/env python3

import music21
import numpy as np

from copy import deepcopy
from collections import defaultdict
from itertools import count, combinations
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

    def add_notes_to(self, target, noteOrChord):

        notes = []

        if isinstance(noteOrChord, music21.note.Note):
            notes = [noteOrChord]
        elif isinstance(noteOrChord, music21.chord.Chord):
            notes = noteOrChord._notes

        for note in notes:

            new_elem = None

            if isinstance(target, music21.chord.Chord):
                # no need to add if it is already in the score
                if note.pitch.ps in list(_n.pitch.ps for _n in target._notes):
                    new_elem = target
                else:
                    # print('added to chord', note)
                    pitches = [note.pitch] + [n.pitch for n in target._notes]
                    new_elem = music21.chord.Chord(pitches)

            elif isinstance(target,
                            music21.note.Note) and not target.isRest:  # a note
                # no need to add if it is already in the score
                if note.pitch.ps == target.pitch.ps:
                    new_elem = target
                else:
                    # replace the note with a chord
                    # print('added to note', note)
                    new_elem = music21.chord.Chord([note.pitch, target.pitch])

            elif isinstance(target, music21.note.Rest):
                # fill the rest
                # print('added to rest', note)
                new_elem = music21.note.Note(note.pitch)

            new_elem.duration.quarterLength = target.duration.quarterLength
            target = new_elem

        return target

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

            # record all the notes/chord/time,key signature, etc

            for hand, part in zip(HANDS, parts):

                notes = []

                for p in bar.parts:

                    for elem in p.recurse(skipSelf=False):

                        # ignore the note if it is marked as deleted
                        if elem.editorial.misc.get('deleted') is True:
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
                            # FIXME: can optimize
                            if hand == LEFT_HAND and elem.pitch.ps < 60:
                                notes.append(elem)
                            elif hand == RIGHT_HAND and elem.pitch.ps >= 60:
                                notes.append(elem)

                        elif isinstance(elem, music21.chord.Chord):
                            for n in elem:
                                if 'hand' not in n.editorial.misc:
                                    continue
                                # FIXME: can optimize
                                if hand == LEFT_HAND and n.pitch.ps < 60:
                                    notes.append(n)
                                elif hand == RIGHT_HAND and n.pitch.ps >= 60:
                                    notes.append(n)

                        else:
                            # Ignore other stuff by default
                            pass

                out_measure = self._create_measure(
                    notes=notes, measure_length=bar_length, index=i)

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

    # FIXME: tuplets are weird

    def _create_measure(self, notes=[], measure_length=4.0, index=0.0):

        result = music21.stream.Measure()

        notes = [
            n for n in notes if n.editorial.misc.get('deleted') is not True
        ]

        # no note within the measure?
        if len(notes) == 0:
            return result

        # record all the pitches starting at different onsets

        offset_map = defaultdict(lambda: defaultdict(lambda: []))
        tie_map = {}
        tuplet_map = {}

        for n in notes:
            offset_map[n.offset][n.duration.quarterLength].append(n.pitch)
            if n.tie:
                tie_map[(n.offset, n.duration.quarterLength,
                         n.pitch.ps)] = n.tie
            if n.duration.tuplets:
                tuplet_map[(n.offset, n.duration.quarterLength,
                            n.pitch.ps)] = n.duration.tuplets

        # merge notes with same offset and duration into a single chord

        for offset, offset_item in offset_map.items():

            for duration, pitches in offset_item.items():

                if len(pitches) == 1:
                    offset_item[duration] = music21.note.Note(pitches[0])
                    # add back tie if any
                    if (offset, duration, pitches[0].ps) in tie_map:
                        offset_item[duration].tie = tie_map[(offset, duration,
                                                             pitches[0].ps)]
                    # add back tuplet if any
                    if (offset, duration, pitches[0].ps) in tuplet_map:
                        offset_item[duration].tuplet = tuplet_map[(
                            offset, duration, pitches[0].ps)]
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

                offset_item[duration].articulations = []  # strip articulation
                offset_item[duration].duration.quarterLength = duration

                notes = offset_item[duration]._notes if isinstance(
                    offset_item[duration],
                    music21.chord.Chord) else [offset_item[duration]]

                for n in notes:
                    if (offset, duration, n.pitch.ps) in tuplet_map:
                        offset_item[duration].tuplets = None

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

        # delete tie if the tie is covering some notes

        if len(tie_map) > 0:

            for key, value in tie_map.items():

                offset, duration, ps = key
                matches = intervals.search(offset, offset + duration)

                tied_note = None
                should_delete = False

                for m in matches:
                    start, end, noteOrChord = m
                    notes = noteOrChord._notes if isinstance(
                        noteOrChord, music21.chord.Chord) else [noteOrChord]
                    pss = [n.pitch.ps for n in notes]
                    if ps in pss and start == offset and \
                            abs(offset + duration - end) < 1e-2:
                        tied_note = m
                    else:
                        # the tie is covering some notes
                        should_delete = True

                if should_delete and tied_note:
                    start, end, elem = tied_note
                    elem.tie = None
                    new_duration = elem.duration.quarterLength
                    new_end = min(start + new_duration, measure_length)
                    intervals.removei(*tied_note)
                    intervals.addi(start, new_end, elem)

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
                                    if v >= measure_length * 0.5)

            for key in excess_voices:

                items = [i for i in voices[key]]
                del voices[key]

                for start, end, n1 in items:

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

                        for _n in notes:
                            voices[best_key][index] = (start, new_end,
                                                       self.add_notes_to(
                                                           n2, _n))

                    else:

                        # te add a new voice now for that note instead
                        # later it will be fixed in optimize_measure()
                        voices[key].append((start, end, n1))

        for i, v in enumerate(voices.values()):
            voice = music21.stream.Voice(id=i)
            for note in v:
                start, end, elem = note
                elem.offset = start
                elem.quarterLength = end - start
                voice.insert(start, elem)
            voice.makeAccidentals(useKeySignature=True)
            result.insert(0, voice)

        return self.optimize_measure(result, index=index)

    def optimize_measure(self, measure, index=0.0):

        voices = list(measure.recurse().getElementsByClass('Voice'))
        voice_offset_sets = defaultdict(lambda: set())
        voice_offset_rest_sets = defaultdict(lambda: set())
        voice_offset_map = defaultdict(lambda: {})

        for key, v in enumerate(voices):
            curr_offset = 0.0
            voice_offset_sets[key] = set()
            voice_offset_rest_sets[key] = set()
            for n in v.recurse().getElementsByClass(('Note', 'Chord', 'Rest')):
                if isinstance(n, music21.note.Rest):
                    voice_offset_rest_sets[key].add(curr_offset)
                    voice_offset_map[key][curr_offset] = n
                else:
                    voice_offset_sets[key].add(curr_offset)
                    voice_offset_map[key][curr_offset] = n
                curr_offset += n.duration.quarterLength

        # len(voices) should be at most 2 so this is fine
        for a, b in combinations(range(len(voices)), 2):
            if len(voice_offset_sets[a]) > len(voice_offset_sets[b]):
                a, b = b, a
            first_set = voice_offset_sets[a]
            second_set = voice_offset_sets[b].union(voice_offset_rest_sets[b])
            if first_set <= second_set:
                for offset, n1 in voice_offset_map[a].items():
                    if offset in voice_offset_map[b]:
                        n2 = voice_offset_map[b][offset]
                        new_elem = self.add_notes_to(n2, n1)
                        voices[a].remove(n1)
                        voices[b].remove(n2)
                        voices[b].insert(n2.offset, new_elem)
                        voice_offset_map[b][offset] = new_elem
                measure.remove(voices[a])
                try:
                    del voice_offset_sets[a]
                    del voice_offset_rest_sets[a]
                    del voice_offset_map[a]
                except KeyError:
                    pass

        # FIXME: merge as many notes as possible

        return measure

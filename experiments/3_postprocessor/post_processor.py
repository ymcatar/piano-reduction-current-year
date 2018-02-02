#!/usr/vin/env python3

import music21
from collections import defaultdict
from copy import deepcopy
from operator import itemgetter

# relative import
from util import isNote, isChord
from algorithms import PostProcessorAlgorithms
from note_wrapper import NoteWrapper

# algorithm set

ALGORITHMS_BY_MEASURE_GROUP = [
]

ALGORITHMS_BY_MEASURE = [
    # (PostProcessorAlgorithms.large_hand_movement, PostProcessorAlgorithms.fix_large_hand_movement)
]

ALGORITHMS_BY_OFFSET_GROUPED_NOTES = [
    # (PostProcessorAlgorithms.concurrent_notes, PostProcessorAlgorithms.fix_concurrent_notes)
]

class PostProcessor(object):

    def __init__(self, score):

        self.score = score

        # get all measures from the score
        self.measures = list(self.score.recurse(skipSelf=True).getElementsByClass('Measure'))
        for measure in self.measures:
            measure.removeByClass([
                music21.layout.PageLayout,
                music21.layout.SystemLayout,
                music21.layout.StaffLayout])

        # group measures with the same offset together
        self.grouped_measures = defaultdict(lambda: [])
        for measure in self.measures:
           self.grouped_measures[str(measure.offset)].append(measure)

        # group notes starting at the same time instance together
        self.offset_grouped_notes = defaultdict(lambda: [])
        for _, group in self.grouped_measures.items():
            for measure in group:
                offset_map = measure.offsetMap()
                for item in offset_map:
                    offset = measure.offset + item.offset
                    if isChord(item.element):
                        for note in item.element._notes:
                            note = NoteWrapper(note, offset, self.score, item.element)
                            self.offset_grouped_notes[offset].append(note)
                    else: # note or rest
                        note = NoteWrapper(item.element, offset, self.score)
                        self.offset_grouped_notes[offset].append(note)

        # perform finger assignment
        assert self.offset_grouped_notes is not None
        prev_assignment = None
        for offset, group in self.offset_grouped_notes.items():
            # get and sort all the notes in the current time instance by pitch step
            notes = [i for i in group if isNote(i.note)]
            notes = sorted(notes, key=lambda i: i.note.pitch.ps)
            curr_assignment = self.perform_finger_assignment(offset, notes, prev=prev_assignment)
            # print(offset, curr_assignment)
            prev_assignment = curr_assignment

        # dictionary to store all the problematic sites
        self.sites = defaultdict(lambda: [])

    def perform_finger_assignment(self, offset, notes, prev=None):

        octaves = list(set(n.note.octave for n in notes))

        if not prev: # is the first time instance, apply Cherry's staff assignment
            if len(octaves) == 1: # only one octave => assign to either one
                if octaves[0] >= 4: # >= middle C octave
                    # assign to right hand
                    print('right:', notes)
                else:
                    print('left:', notes)
            elif len(octaves) == 2: # two octaves => assign lower one to left, assign higher one to right
                lower_octave, higher_octave = min(octaves), max(octaves)
                print('left:', list(n for n in notes if n.note.octave == lower_octave))
                print('right:', list(n for n in notes if n.note.octave == higher_octave))
            else: # maybe it is impossible
                pass

        print(offset, list(n.note.pitch.ps for n in notes))

    def apply(self):
        pass
        # self.apply_each(ALGORITHMS_BY_MEASURE, self.measures)
        # self.apply_each(ALGORITHMS_BY_MEASURE_GROUP, self.grouped_measures)
        # self.apply_each(ALGORITHMS_BY_OFFSET_GROUPED_NOTES, self.offset_grouped_notes)

    def apply_each(self, algorithms, source):
        source = source.items() if isinstance(source, dict) else source
        for item in source:
            for algorithm in algorithms:
                detect_func, fix_func = algorithm
                self.sites[detect_func.__name__] += detect_func(item)
                # for site in self.sites[detect_func.__name__]:
                    # fix_func(site)

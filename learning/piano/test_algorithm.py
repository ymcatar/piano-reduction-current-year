from music21 import converter, note, stream
import pytest
from . import algorithm
from .algorithm.base import get_markings, iter_notes
from .score import ScoreObject
from .alignment import align_scores

import numpy as np


binary_algorithms = [
    (algorithm.OnsetAfterRest(), 'onset_after_rest'),
    (algorithm.StrongBeats(), 'strong_beats'),
    (algorithm.ActiveRhythm(), 'active_rhythm'),
    (algorithm.SustainedRhythm(), 'sustained_rhythm'),
    (algorithm.RhythmVariety(), 'rhythm_variety'),
    (algorithm.VerticalDoubling(), 'vertical_doubling'),
    (algorithm.Occurrence(), 'pitch_occurrence'),
    (algorithm.BassLine(), 'bass_line'),
    ]


@pytest.mark.parametrize('algo,output_name', binary_algorithms)
def test_binary_algorithms(algo, output_name):
    input = converter.parse('learning/piano/test_sample/algorithm_input.xml')
    # Each sample output has notes with value 1 marked as red
    output = converter.parse(
        'learning/piano/test_sample/algorithm_{}.xml'.format(output_name))

    s = ScoreObject(input)
    input = s._score
    algo.create_markings_on(s)

    alignment = align_scores(input, output)

    for measure in input.recurse().getElementsByClass(stream.Measure):
        for n in iter_notes(measure.recurse()):
            if isinstance(n, note.NotRest):
                assert len(alignment[n]) == 1
                assert algo.key in get_markings(n), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + n.offset)

                is_red = alignment[n][0].style.color == '#FF0000'
                actual = get_markings(n)[algo.key]
                assert actual == is_red, \
                    'Note {!r} at {} should be marked {} but is marked {}' \
                    .format(n, measure.offset + n.offset, is_red, actual)


continuous_algorithms = [
    (algorithm.EntranceEffect(), 'entrance_effect'),
    (algorithm.OffsetValue(), 'offset_value'),
    ]


@pytest.mark.parametrize('algo,output_name', continuous_algorithms)
def test_continuous_algorithms(algo, output_name):
    input = converter.parse('learning/piano/test_sample/algorithm_input.xml')
    # Each sample output has some notes with its value written as lyric
    output = converter.parse(
        'learning/piano/test_sample/algorithm_{}.xml'.format(output_name))

    s = ScoreObject(input)
    input = s._score
    algo.create_markings_on(s)

    alignment = align_scores(input, output)

    for measure in input.recurse().getElementsByClass(stream.Measure):
        for n in iter_notes(measure.recurse()):
            if isinstance(n, note.NotRest):
                assert len(alignment[n]) == 1
                assert algo.key in get_markings(n), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + n.offset)

                value = alignment[n][0].lyric
                if value:
                    expected = float(value)
                    actual = get_markings(n)[algo.key]
                    assert actual == expected, \
                        'Note {!r} at {} should be marked {} but is marked {}' \
                        .format(n, measure.offset + n.offset, expected, actual)


def test_pitch_class_statistics():
    input = converter.parse('learning/piano/test_sample/algorithm_input.xml')
    algo = algorithm.PitchClassStatistics()

    s = ScoreObject(input)
    input = s._score
    algo.create_markings_on(s)

    expecteds = {
        #     C  C# D  D# E  F  F# G  G# A  A# B
        0.0: [0, 0, 6, 0, 0, 5, 0, 1, 0, 3, 0, 0],
        2.0: [0, 2, 0, 0, 2, 0, 0, 0, 3, 3, 0, 0],
        4.0: [0, 3, 1, 0, 3, 1, 0, 1, 0, 4, 0, 0],
        6.0: [0, 3, 4, 0, 0, 2, 0, 0, 0, 1, 0, 0]
        }

    for offset, histogram in expecteds.items():
        norm = np.linalg.norm(histogram)
        expecteds[offset] = [x / norm for x in histogram]

    for measure in input.recurse().getElementsByClass(stream.Measure):
        for n in iter_notes(measure.recurse()):
            if isinstance(n, note.NotRest):
                markings = get_markings(n)
                assert all(k in markings for k in algo.all_keys), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + n.offset)

                actual = [markings[k] for k in algo.all_keys]
                expected = expecteds[measure.offset]
                assert actual == expected, \
                    'Note {!r} at {} should be marked {} but is marked {}' \
                    .format(n, measure.offset + n.offset, expected, actual)

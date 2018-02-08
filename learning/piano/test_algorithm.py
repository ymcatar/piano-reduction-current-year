from music21 import converter, note, stream
import pytest
from . import algorithm
from .algorithm.base import get_markings, iter_notes, iter_notes_with_offset
from .score import ScoreObject
from .alignment import align_all_notes

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
    s = ScoreObject.from_file('learning/piano/test_sample/algorithm_input.xml')
    input = s.score
    # Each sample output has notes with value 1 marked as red
    output = converter.parse(
        'learning/piano/test_sample/algorithm_{}.xml'.format(output_name))

    algo.run(s)
    alignment = align_all_notes(input, output)

    for measure in input.recurse(
            skipSelf=False).getElementsByClass(stream.Measure):
        for n, offset in iter_notes_with_offset(measure, recurse=True):
            if isinstance(n, note.NotRest):
                assert len(alignment[n]) == 1
                assert algo.key in get_markings(n), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + offset)

                is_red = alignment[n][0].style.color == '#FF0000'
                actual = get_markings(n)[algo.key]
                assert actual == is_red, \
                    'Note {!r} at {} should be marked {} but is marked {}' \
                    .format(n, measure.offset + offset, is_red, actual)


continuous_algorithms = [
    (algorithm.EntranceEffect(), 'entrance_effect'),
    (algorithm.OffsetValue(), 'offset_value'),
    ]


@pytest.mark.parametrize('algo,output_name', continuous_algorithms)
def test_continuous_algorithms(algo, output_name):
    s = ScoreObject.from_file('learning/piano/test_sample/algorithm_input.xml')
    input = s.score
    # Each sample output has some notes with its value written as lyric
    output = converter.parse(
        'learning/piano/test_sample/algorithm_{}.xml'.format(output_name))

    algo.run(s)
    alignment = align_all_notes(input, output)

    for measure in input.recurse(
            skipSelf=False).getElementsByClass(stream.Measure):
        for n, offset in iter_notes_with_offset(measure, recurse=True):
            if isinstance(n, note.NotRest):
                assert len(alignment[n]) == 1
                assert algo.key in get_markings(n), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + offset)

                value = alignment[n][0].lyric
                if value:
                    expected = float(value)
                    actual = get_markings(n)[algo.key]
                    assert actual == expected, \
                        'Note {!r} at {} should be marked {} but is marked {}' \
                        .format(n, measure.offset + offset, expected, actual)


def test_pitch_class_statistics():
    s = ScoreObject.from_file('learning/piano/test_sample/algorithm_input.xml')
    input = s.score

    algo = algorithm.PitchClassStatistics()
    algo.run(s)

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

    for measure in input.recurse(
            skipSelf=False).getElementsByClass(stream.Measure):
        for n in iter_notes(measure, recurse=True):
            if isinstance(n, note.NotRest):
                markings = get_markings(n)
                assert all(k in markings for k in algo.all_keys), \
                    'Note {!r} at {} should be marked but is not marked' \
                    .format(n, measure.offset + offset)

                actual = [markings[k] for k in algo.all_keys]
                expected = expecteds[measure.offset]
                assert actual == expected, \
                    'Note {!r} at {} should be marked {} but is marked {}' \
                    .format(n, measure.offset + offset, expected, actual)

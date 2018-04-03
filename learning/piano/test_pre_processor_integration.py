import numpy as np
import os
from unittest.mock import Mock
from .algorithm.base import FeatureAlgorithm, get_markings
from .alignment.base import AlignmentMethod
from .pre_processor import BottomUpPreProcessor
from .score import ScoreObject


class PitchSpace(FeatureAlgorithm):
    def run(self, input_score_obj):
        for n in input_score_obj:
            get_markings(n)[self.key] = n.pitch.ps


class DummySequences(FeatureAlgorithm):
    @property
    def all_keys(self):
        return [self.key + '_ascending', self.key + 'descending']

    def run(self, input_score_obj):
        for i, n in enumerate(input_score_obj):
            get_markings(n)[self.all_keys[0]] = i
            get_markings(n)[self.all_keys[1]] = -i


class AlignDummy(AlignmentMethod):
    def run(self, input_score_obj, output_score_obj, extra=False):
        for n in input_score_obj:
            get_markings(n)['align'] = True


X = np.array([
    list(range(60, 60+13)),  # PitchSpace
    list(range(13)),  # DummySequences_ascending
    [-i for i in range(13)],  # DummySequences_descending
    ]).T
y = np.ones((13, 1))  # AlignDummy

path = 'learning/piano/test_sample/chromatic_scale.xml'


def test_pre_process_from_file():
    pre = BottomUpPreProcessor(algorithms=[PitchSpace(), DummySequences()], alignment=AlignDummy())

    # Input only
    for i in range(2):
        d = pre.process_path_pair(path, None)
        assert np.all(d.X == X)
        assert d.y is None

    # Input and output
    for i in range(2):
        d = pre.process_path_pair(path, path)
        assert np.all(d.X == X)
        assert np.all(d.y == y)


def test_pre_process_from_object():
    pre = BottomUpPreProcessor(algorithms=[PitchSpace(), DummySequences()], alignment=AlignDummy())

    # Input only
    s = ScoreObject.from_file(path)
    d = pre.process_score_obj_pair(s, None)

    assert np.all(d.X == X)
    assert d.y is None
    assert d.input

    # Input and output
    s = ScoreObject.from_file(path)
    d = pre.process_score_obj_pair(s, s)

    assert np.all(d.X == X)
    assert np.all(d.y == y)
    assert d.input

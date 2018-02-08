import numpy as np
import os
from unittest.mock import Mock
from .algorithm.base import ReductionAlgorithm, get_markings
from .alignment.base import AlignmentMethod
from .dataset import CACHE_DIR, DatasetEntry
from .reducer import Reducer
from .score import ScoreObject


class PitchSpace(ReductionAlgorithm):
    def run(self, input_score_obj):
        for n in input_score_obj:
            get_markings(n)[self.key] = n.pitch.ps


class DummySequences(ReductionAlgorithm):
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
cache_path = CACHE_DIR + '/chromatic_scale.hdf5'


def test_dataset_entry_from_file():
    reducer = Reducer(algorithms=[PitchSpace(), DummySequences()], alignment=AlignDummy())
    try:
        os.remove(cache_path)
    except OSError:
        pass

    # Input only
    for i in range(2):
        d = DatasetEntry(path_pair=(path, None))
        d.ensure_scores_loaded = Mock(wraps=d.ensure_scores_loaded)
        d.load(reducer, use_cache=True)
        assert np.all(d.X == X)
        assert d.y is None
        if i == 0:
            d.ensure_scores_loaded.assert_called()  # since no cache available
        else:
            d.ensure_scores_loaded.assert_not_called()  # since cache used

    # Input and output
    for i in range(2):
        d = DatasetEntry(path_pair=(path, path))
        d.ensure_scores_loaded = Mock(wraps=d.ensure_scores_loaded)
        d.load(reducer, use_cache=True)
        assert np.all(d.X == X)
        assert np.all(d.y == y)
        if i == 0:
            d.ensure_scores_loaded.assert_called()  # since no cache available
        else:
            d.ensure_scores_loaded.assert_not_called()  # since cache used

    # Iput only
    d = DatasetEntry(path_pair=(path, None))
    d.ensure_scores_loaded = Mock(wraps=d.ensure_scores_loaded)
    d.load(reducer, use_cache=True)
    d.ensure_scores_loaded.assert_not_called()  # since cache used
    assert np.all(d.X == X)
    assert d.y is None

    # keep_scores
    d = DatasetEntry(path_pair=(path, None))
    d.ensure_scores_loaded = Mock(wraps=d.ensure_scores_loaded)
    d.load(reducer, use_cache=True, keep_scores=True)
    d.ensure_scores_loaded.assert_called()
    assert np.all(d.X == X)
    assert d.y is None
    assert d.input_score_obj

    # Ensures the cache was indeed created
    os.remove(cache_path)


def test_dataset_entry_from_object():
    reducer = Reducer(algorithms=[PitchSpace(), DummySequences()], alignment=AlignDummy())
    try:
        os.remove(cache_path)
    except OSError:
        pass

    # Input only
    for use_cache in (False, True):
        s = ScoreObject.from_file(path)
        d = DatasetEntry(score_obj_pair=(s, None))
        d.load(reducer, use_cache=use_cache)

        assert np.all(d.X == X)
        assert d.y is None
        assert d.input_score_obj

    # Input and output
    for use_cache in (False, True):
        s = ScoreObject.from_file(path)
        d = DatasetEntry(score_obj_pair=(s, s))
        d.load(reducer, use_cache=use_cache)

        assert np.all(d.X == X)
        assert np.all(d.y == y)
        assert d.input_score_obj
        assert not os.path.exists(cache_path)

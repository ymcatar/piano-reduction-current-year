from .alignment import mark_alignment
from .algorithm.base import get_markings, iter_notes

from collections.abc import Sequence
import numpy as np


class Reducer(object):
    def __init__(self, algorithms):
        self._algorithms = algorithms

        # Set the key for each algorithm
        for i, algo in enumerate(self.algorithms):
            algo.key_prefix = str(i)

        self._all_keys = sorted(
            key for algo in self.algorithms for key in algo.all_keys)

    @property
    def algorithms(self):
        return self._algorithms

    @property
    def all_keys(self):
        return self._all_keys

    def iter_notes(self, input_score_objs):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]

        for score_obj in input_score_objs:
            yield from iter_notes(score_obj.score, recurse=True)

    def create_markings_on(self, input_score_objs):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]

        for score_obj in input_score_objs:
            for algo in self.algorithms:
                algo.create_markings_on(score_obj)

        note_count = sum(1 for _ in self.iter_notes(input_score_objs))
        X = np.zeros((note_count, len(self.all_keys)), dtype='float')
        for i, n in enumerate(self.iter_notes(input_score_objs)):
            markings = get_markings(n)
            X[i, :] = np.fromiter((markings[k] for k in self.all_keys),
                                  dtype='float', count=len(self.all_keys))
        return X

    def create_alignment_markings_on(self, input_score_objs, output_score_objs):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]
        if not isinstance(output_score_objs, Sequence):
            output_score_objs = [output_score_objs]

        for input, output in zip(input_score_objs, output_score_objs):
            mark_alignment(input.score, output.score)

        note_count = sum(1 for _ in self.iter_notes(input_score_objs))
        y = np.fromiter((n.editorial.misc['align']
                         for n in self.iter_notes(input_score_objs)),
                        dtype='float', count=note_count)
        return y

    def predict_from(self, model, input_score_objs, X=None):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]

        if X is None:
            X = self.create_markings_on(input_score_objs)
        y = model.predict(X)

        for i, n in enumerate(self.iter_notes(input_score_objs)):
            n.editorial.misc['align'] = y[i]

        return y

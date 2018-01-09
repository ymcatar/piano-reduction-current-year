from .alignment import get_alignment_func
from .algorithm.base import get_markings, iter_notes

from collections.abc import Sequence
import importlib
import numpy as np

from scoreboard import writer as writerlib


def import_symbol(path):
    module, symbol = path.rsplit('.', 1)
    return getattr(importlib.import_module(module), symbol)


class Reducer(object):
    def __init__(self, algorithms, alignment):
        '''
        Arguments:
            algorithms: List of Algorithm objects or (class.path, args, kwargs)
                tuple.
            alignment: Name of the alignment method.
        '''
        if all(isinstance(a, tuple) for a in algorithms):
            # Only create this if the args are indeed serializable
            self.reducer_args = {
                'algorithms': algorithms,
                'alignment': alignment
                }

        self._algorithms = []
        for algo in algorithms:
            if isinstance(algo, tuple):
                path, args, kwargs = algo
                self._algorithms.append(import_symbol(path)(*args, **kwargs))
            else:
                self._algorithms.append(algo)

        # Set the key for each algorithm
        for i, algo in enumerate(self.algorithms):
            algo.key_prefix = str(i)

        self._all_keys = sorted(
            key for algo in self.algorithms for key in algo.all_keys)

        self.alignment = alignment
        self.alignment_func = get_alignment_func(alignment)
        self.label_type = self.alignment_func.label_type

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
            X[i, :] = np.fromiter((markings.get(k, 0) for k in self.all_keys),
                                  dtype='float', count=len(self.all_keys))
        return X

    def create_alignment_markings_on(self, input_score_objs, output_score_objs):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]
        if not isinstance(output_score_objs, Sequence):
            output_score_objs = [output_score_objs]

        for input, output in zip(input_score_objs, output_score_objs):
            self.alignment_func(input.score, output.score)

        note_count = sum(1 for _ in self.iter_notes(input_score_objs))
        y = np.fromiter((n.editorial.misc[self.label_type]
                         for n in self.iter_notes(input_score_objs)),
                        dtype='uint8', count=note_count)
        return y

    def predict_from(self, model, input_score_objs, X=None):
        if not isinstance(input_score_objs, Sequence):
            input_score_objs = [input_score_objs]

        if X is None:
            X = self.create_markings_on(input_score_objs)

        y_proba = model.predict(X)
        if self.label_type == 'align':
            y = np.squeeze(y_proba, axis=1)
        elif self.label_type == 'hand':
            y = np.argmax(y_proba, axis=1)
        else:
            raise NotImplementedError()

        for i, n in enumerate(self.iter_notes(input_score_objs)):
            n.editorial.misc['align'] = y[i]

        return y_proba

    def add_features_to_writer(self, writer):
        for algo in self.algorithms:
            help = algo.__doc__ or algo.create_markings_on.__doc__
            help = help.strip()
            dtype = getattr(algo, 'dtype', 'bool')
            if dtype == 'float':
                writer.add_feature(writerlib.FloatFeature(
                    algo.key, getattr(algo, dtype, getattr(algo, 'range')),
                    help=help))
            else:
                writer.add_feature(writerlib.BoolFeature(
                    algo.key, help=help))

        if self.label_type == 'align':
            writer.add_feature(writerlib.BoolFeature(
                'align', help='Whether the note should be kept.'))
        elif self.label_type == 'hand':
            legend = {
                '#0000FF': 'Upper staff',
                '#00FF00': 'Lower staff',
                '#000000': 'Discarded',
                }
            writer.add_feature(writerlib.CategoricalFeature(
                'align', legend, '#000000',
                help='Which staff the note should be kept in.'))

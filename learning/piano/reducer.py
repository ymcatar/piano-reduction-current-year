from .dataset import DatasetEntry
from .util import ensure_algorithm, dump_algorithm

import importlib
import numpy as np

from scoreboard import writer as writerlib


def import_symbol(path):
    module, symbol = path.rsplit('.', 1)
    return getattr(importlib.import_module(module), symbol)


class Reducer(object):
    '''
    Represents a particular configuration of the piano reduction system.
    '''
    def __init__(self, algorithms, alignment, contractions=[]):
        '''
        Arguments:
            algorithms: List of Algorithm objects or (class.path, args, kwargs)
                tuple.
            alignment: Name of the alignment method.
        '''

        self._algorithms = []
        for algo in algorithms:
            self._algorithms.append(ensure_algorithm(algo))

        # Set the key for each algorithm
        for i, algo in enumerate(self.algorithms):
            algo.key_prefix = str(i)

        self._all_keys = sorted(
            key for algo in self.algorithms for key in algo.all_keys)

        self.alignment = ensure_algorithm(alignment)
        self.label_type = self.alignment.key

        self.contractions = [ensure_algorithm(algo) for algo in contractions]

        self.args = (
            [], {
                'algorithms': [dump_algorithm(algo) for algo in self.algorithms],
                'alignment': dump_algorithm(self.alignment),
                'contractions': [dump_algorithm(algo) for algo in self.contractions],
            })

    @property
    def algorithms(self):
        return self._algorithms

    @property
    def all_keys(self):
        return self._all_keys

    def create_markings_on(self, score_obj, use_cache=False):
        d = DatasetEntry(score_obj_pair=(score_obj, None))
        d.load(self, use_cache=use_cache)
        return d.X

    def create_contractions(self, score_obj, use_cache=False):
        raise NotImplementedError()  # TODO

    def create_alignment_markings_on(self, input_score_obj, output_score_obj, extra=False,
                                     use_cache=False):
        d = DatasetEntry(score_obj_pair=(input_score_obj, output_score_obj))
        d.load(self, use_cache=use_cache, extra=extra)
        return d.y

    def predict_from(self, model, score_obj, X=None, mapping=None):
        if X is None:
            X = self.create_markings_on(score_obj)

        y_proba = model.predict(X)
        if self.label_type == 'align':
            y = np.squeeze(y_proba, axis=1)
        elif self.label_type == 'hand':
            y = np.argmax(y_proba, axis=1)
        else:
            raise NotImplementedError()

        score_obj.annotate(y, self.label_type, mapping=mapping)

        return y_proba

    @property
    def features(self):
        features = []

        for algo in self.algorithms:
            help = algo.__doc__ or algo.create_markings_on.__doc__
            help = help.strip()
            dtype = getattr(algo, 'dtype', 'bool')
            if dtype == 'float':
                features.append(writerlib.FloatFeature(
                    algo.key, getattr(algo, dtype, getattr(algo, 'range')),
                    help=help))
            else:
                features.append(writerlib.BoolFeature(algo.key, help=help))

        # Note: These are predictions!
        if self.label_type == 'align':
            features.append(writerlib.BoolFeature(
                'align', help='Whether the note should be kept.'))
        elif self.label_type == 'hand':
            legend = {
                '#0000FF': ('Upper staff', 1),
                '#00FF00': ('Lower staff', 2),
                '#000000': ('Discarded', 0),
                }
            features.append(writerlib.CategoricalFeature(
                'hand', legend, '#000000',
                help='Which staff the note should be kept in.'))

        return features

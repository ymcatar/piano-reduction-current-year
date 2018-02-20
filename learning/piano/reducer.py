from .util import ensure_algorithm, dump_algorithm

import numpy as np

from scoreboard import writer as writerlib


class Reducer(object):
    '''
    Represents a particular configuration of the piano reduction system.
    '''
    def __init__(self, algorithms, alignment, contractions=[], structures=[]):
        '''
        Each algorithm is either specified by an *Algorithm instance, or a tuple
        (class.path, args, kwargs).
        Arguments:
            algorithms: List of algorithms.
                tuple.
            alignment: Alignment algorithm.
            contractions: List of contraction algorithms.
            structures: List of structure algorithms.
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
        self.structures = [ensure_algorithm(algo) for algo in structures]

        self.args = {
            'algorithms': [dump_algorithm(algo) for algo in self.algorithms],
            'alignment': dump_algorithm(self.alignment),
            'contractions': [dump_algorithm(algo) for algo in self.contractions],
            'structures': [dump_algorithm(algo) for algo in self.structures],
        }

    @property
    def algorithms(self):
        return self._algorithms

    @property
    def all_keys(self):
        return self._all_keys

    def predict_from(self, model, score_obj, X, mapping=None, structured=False):
        if structured:
            y_proba = model.predict_structured(X)
        else:
            y_proba = model.predict(X)
        if self.label_type == 'align':
            y = np.squeeze(y_proba, axis=1)
        elif self.label_type == 'hand':
            y = np.argmax(y_proba, axis=1)
        else:
            raise NotImplementedError()

        score_obj.annotate(mapping.unmap_matrix(y), self.label_type)

        return y_proba

    @property
    def input_features(self):
        features = []

        for algo in self.algorithms:
            if list(algo.all_keys) != [algo.key]:
                # Multi-key features not supported yet
                continue
            feature = writerlib.guess_feature(algo)
            features.append(feature)

        return features

    @property
    def structure_features(self):
        features = []

        for algo in self.contractions:
            sub = writerlib.guess_feature(algo)
            feature = writerlib.StructureFeature(
                sub.name, sub, directed=True, help=sub.help, group='contractions')
            features.append(feature)

        for algo in self.structures:
            sub = writerlib.guess_feature(algo)
            feature = writerlib.StructureFeature(
                sub.name, sub, help=sub.help, group='structures')
            features.append(feature)

        return features

    @property
    def output_features(self):
        features = []

        if self.label_type == 'align':
            features.append(writerlib.FloatFeature(
                'align', range=[0.0, 1.0],
                help='How likely the note should be kept.', group='output'))
        elif self.label_type == 'hand':
            legend = {
                0: ('#000000', 'Discarded'),
                1: ('#3333FF', 'Upper staff'),
                2: ('#33FF33', 'Lower staff'),
                }
            features.append(writerlib.CategoricalFeature(
                'hand', legend, '#000000',
                help='Which staff the note should be kept in.', group='output'))

        return features

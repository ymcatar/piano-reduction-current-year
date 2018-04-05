from collections import defaultdict
import copy
import logging
import numpy as np
import os
from .score import ScoreObject
from .util import dump_algorithm, ensure_algorithm
from .contraction import ContractionMapping
from scoreboard import writer as writerlib


class PreProcessedEntry:
    '''
    A struct class to contain the pre-processing result. Additional fields may
    be added to accommodate extra data.
    '''
    def __init__(self, X=None, y=None):
        self.X = X
        self.y = y
        self.name = '<Untitled>'


class PreProcessedList:
    def __init__(self, entries):
        self.entries = list(entries)
        self.X = [entry.X for entry in self.entries]
        self.y = [entry.y for entry in self.entries]

    @property
    def __repr__(self):
        return repr((self.X, self.y))


class BasePreProcessor:
    '''
    Base class for pre-processors. Pre-processors take XML paths or ScoreObject
    instances as input and convert them to a dataset suitable for parameter
    learning and prediction.
    '''
    def __init__(self):
        self.args = [], {}
        self.label_type = None

    def process_path_pair(self, in_path, out_path, **kwargs):
        input = ScoreObject.from_file(in_path)
        output = ScoreObject.from_file(out_path) if out_path else None
        return self.process_score_obj_pair(input, output, name=os.path.basename(in_path))

    def process_score_obj_pair(self, input, output, **kwargs):
        '''
        Convert the given ScoreObject pair into a PreProcessedEntry.
        '''
        raise NotImplementedError()

    def process(self, path_pairs, **kwargs):
        result = []
        for pair in path_pairs:
            if type(pair) == str:
                in_path, _, out_path = pair.partition(':')
            else:
                in_path, out_path = pair
            result.append(self.process_path_pair(in_path, out_path))
        return PreProcessedList(result)

    def post_predict(self, y_proba):
        '''
        Transform the labels of the dataset to the format specified by
        self.label_type.

        Returns: (y_pred, y_proba)
            y_pred: int ndarray of shape (n, 1) or (n, 3)
                The predicted label for each note.
            y_proba: float ndarray of shape (n, 1) or (n, 3)
                The probability vector for each note.
        '''

        if self.label_type == 'align':
            if y_proba.ndim == 1:
                y_proba = y_proba[:, np.newaxis]
            if y_proba.shape[1] == 2:
                y_proba = y_proba[:, 1:2]
            assert y_proba.shape[1] == 1
            y_pred = y_proba.flatten() >= 0.5

        elif self.label_type == 'hand':
            assert y_proba.shape[1] == 3
            y_pred = np.argmax(y_proba, axis=1)

        else:
            raise ValueError('label_type must be align or hand')

        return y_pred, y_proba


class BottomUpPreProcessor(BasePreProcessor):
    def __init__(self, algorithms, alignment):
        super().__init__()
        self.algorithms = [ensure_algorithm(algo) for algo in algorithms]

        for i, algo in enumerate(self.algorithms):
            algo.key_prefix = str(i)
        self.all_keys = [key for algo in self.algorithms for key in algo.all_keys]

        self.alignment = ensure_algorithm(alignment)
        self.label_type = self.alignment.key

        self.args[1].update({
            'algorithms': [dump_algorithm(algo) for algo in self.algorithms],
            'alignment': dump_algorithm(self.alignment),
            })

    def process_score_obj_pair(self, input, output, extra=False, name=None):
        ret = PreProcessedEntry()
        ret.len = len(input)
        if name:
            ret.name = name

        # Features
        X = np.empty((ret.len, len(self.all_keys)), dtype='float')
        for algo in self.algorithms:
            logging.info('Evaluating feature {}'.format(type(algo).__name__))
            algo.run(input)

            for i, key in enumerate(algo.all_keys):
                X[:, self.all_keys.index(key)] = \
                    input.extract(key, dtype='float', default=0)
        ret.X = X

        # Labels
        if output:
            logging.info('Evaluating alignment {}'.format(type(self.alignment).__name__))
            self.alignment.run(input, output, extra=extra)
            y = input.extract(self.alignment.key, dtype='int')
            y = y[:, np.newaxis]
            ret.y = y

        ret.input = input
        ret.output = output

        return ret

    @property
    def input_features(self):
        features = []
        for algo in self.algorithms:
            features.extend(writerlib.guess_features(algo))

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


class ContractingPreProcessor(BottomUpPreProcessor):
    def __init__(self, algorithms, alignment, contractions=[]):
        super().__init__(algorithms, alignment)
        self.contractions = [ensure_algorithm(algo) for algo in contractions]
        self.args[1]['contractions'] = \
            [dump_algorithm(algo) for algo in self.contractions]

    def process_score_obj_pair(self, input, output, **kwargs):
        parent = super().process_score_obj_pair(input, output, **kwargs)
        ret = copy.copy(parent)
        ret.parent = parent

        # Contractions
        ret.contractions = {}
        all_contractions = []
        for algo in self.contractions:
            logging.info('Evaluating contraction {}'.format(type(algo).__name__))
            contr = list(algo.run(input))
            ret.contractions[algo.key] = [(edge, ()) for edge in contr]
            all_contractions.extend(contr)

        ret.mapping = ContractionMapping(all_contractions, parent.len)
        ret.len = ret.mapping.output_size
        if ret.len != parent.len:
            logging.info('Contractions: {} notes => {} notes'.format(parent.len, ret.len))

        # Contract features and labels
        ret.X = ret.mapping.map_matrix(parent.X)
        if output:
            ret.y = ret.mapping.map_matrix(parent.y)

        return ret

    @property
    def structure_features(self):
        features = []

        for algo in self.contractions:
            sub = writerlib.guess_feature(algo)
            feature = writerlib.StructureFeature(
                sub.name, sub, directed=True, help=sub.help, group='contractions')
            features.append(feature)

        return features


class StructuralPreProcessor(ContractingPreProcessor):
    def __init__(self, algorithms, alignment, contractions=[], structures=[]):
        super().__init__(algorithms, alignment, contractions)
        self.structures = [ensure_algorithm(algo) for algo in structures]
        self.args[1]['structures'] = \
            [dump_algorithm(algo) for algo in self.structures]

    def process_score_obj_pair(self, input, output, **kwargs):
        parent = super().process_score_obj_pair(input, output, **kwargs)
        ret = copy.copy(parent)
        ret.parent = parent
        ret.features = parent.X  # Renamed

        # Structures
        n_edge_features = sum(a.n_features for a in self.structures)

        ret.structures = {}
        all_structures = defaultdict(lambda: np.zeros(n_edge_features, dtype='float'))
        d = 0
        for algo in self.structures:
            logging.info('Evaluating structure {}'.format(type(algo).__name__))
            ret.structures[algo.key] = list(algo.run(input))
            for edge, features in ret.structures[algo.key]:
                all_structures[tuple(sorted(edge))][d:d + algo.n_features] = features
            d += algo.n_features

        all_structures = ret.mapping.map_structure(all_structures)

        E = np.empty((len(all_structures), 2), dtype='int')
        F = np.empty((len(all_structures), n_edge_features), dtype='float')
        for i, (k, v) in enumerate(all_structures.items()):
            E[i], F[i] = k, v

        ret.E, ret.F = E, F
        ret.X = (ret.features, E, F)

        return ret

    @property
    def structure_features(self):
        features = super().structure_features

        for algo in self.structures:
            sub = writerlib.guess_feature(algo)
            feature = writerlib.StructureFeature(
                sub.name, sub, help=sub.help, group='structures')
            features.append(feature)

        return features

from collections import defaultdict
from collections.abc import Sequence
import hashlib
import h5py
import json
import logging
import numpy as np
import os
import os.path
from .score import ScoreObject
from .util import dump_algorithm
from .contraction import ContractionMapping


DEFAULT_SAMPLES = [
    'sample/input/i_0000_Beethoven_op18_no1-4.xml:sample/output/o_0000_Beethoven_op18_no1-4.xml',
    'sample/input/i_0001_Spring_sonata_I.xml:sample/output/o_0001_Spring_sonata_I.xml',
    'sample/input/i_0002_Beethoven_Symphony_No5_Mov1.xml:sample/output/o_0002_Beethoven_Symphony_No5_Mov1.xml',
    'sample/input/i_0003_Beethoven_Symphony_No7_Mov2.xml:sample/output/o_0003_Beethoven_Symphony_No7_Mov2.xml',
    'sample/input/i_0004_Mozart_Symphony_No25.xml:sample/output/o_0004_Mozart_Symphony_No25.xml',
    'sample/input/i_0005_Mozart_Symphony_No40.xml:sample/output/o_0005_Mozart_Symphony_No40.xml',
    'sample/input/i_0006_Dvorak_New_World_Symphony_No9_Mov2.xml:sample/output/o_0006_Dvorak_New_World_Symphony_No9_Mov2.xml',
    'sample/input/i_0007_Tchaikovsky_nutcracker_march.xml:sample/output/o_0007_Tchaikovsky_nutcracker_march.xml'
    ]


CROSSVAL_SAMPLES = [
    'sample/input/i_0002_Beethoven_Symphony_No5_Mov1.xml:sample/output/o_0002_Beethoven_Symphony_No5_Mov1.xml',
    'sample/input/i_0003_Beethoven_Symphony_No7_Mov2.xml:sample/output/o_0003_Beethoven_Symphony_No7_Mov2.xml',
    'sample/input/i_0004_Mozart_Symphony_No25.xml:sample/output/o_0004_Mozart_Symphony_No25.xml',
    'sample/input/i_0005_Mozart_Symphony_No40.xml:sample/output/o_0005_Mozart_Symphony_No40.xml',
    'sample/input/i_0006_Dvorak_New_World_Symphony_No9_Mov2.xml:sample/output/o_0006_Dvorak_New_World_Symphony_No9_Mov2.xml',
    'sample/input/i_0007_Tchaikovsky_nutcracker_march.xml:sample/output/o_0007_Tchaikovsky_nutcracker_march.xml'
    ]


class DatasetEntry:
    '''
    Class that handles loading of an input score or an input-output score pair.
    To load an input score only, set the output part of the path_pair or
    score_obj_pair to be None.
    '''
    def __init__(self, path_pair=None, score_obj_pair=None):
        self.X = None
        self.y = None
        self.contractions = {}
        self.structures = {}
        assert (path_pair is None) != (score_obj_pair is None), \
            'exactly one of path_pair and score_obj_pair must be provided!'

        if score_obj_pair:
            self.input_score_obj, self.output_score_obj = score_obj_pair
            self.in_path = self.out_path = None
        else:
            self.in_path, self.out_path = path_pair
            self.input_score_obj = self.output_score_obj = None

    @property
    def loaded(self):
        return self.X is not None

    @property
    def has_output(self):
        return bool(self.output_score_obj or self.out_path)

    @property
    def _name(self):
        if self.in_path:
            return os.path.basename(self.in_path)
        else:
            return '<{}>'.format(self.input_score_obj.score.metadata.title or 'Score')

    def _load_marking(self, reducer, algo):
        logging.info('Evaluating {}'.format(type(algo).__name__))
        algo.run(self.input_score_obj)
        ds = np.hstack(
            self.input_score_obj.extract(key, dtype='float', default=0)[:, np.newaxis]
            for key in algo.all_keys)

        for i, key in enumerate(algo.all_keys):
            self.X[:, reducer.all_keys.index(key)] = ds[:, i]

    def _load_contraction(self, reducer, algo):
        logging.info('Evaluating contraction {}'.format(type(algo).__name__))
        ds = list(algo.run(self.input_score_obj))
        self.contractions[algo.key] = [((r[0], r[1]), ()) for r in ds]

        return ds

    def _load_structure(self, reducer, algo):
        logging.info('Evaluating structure {}'.format(type(algo).__name__))
        # Concatenate to simplify caching
        ds = np.stack([np.concatenate(x, axis=0)
                       for x in algo.run(self.input_score_obj)])
        self.structures[algo.key] = [((int(r[0]), int(r[1])), r[2:]) for r in ds]

        return ds

    def _load_alignment_marking(self, reducer, algo, *, extra=False):
        logging.info('Evaluating alignment')
        algo.run(self.input_score_obj, self.output_score_obj, extra=extra)
        ds = self.input_score_obj.extract(algo.key, dtype='int')

        self.y[:, 0] = ds

    def load(self, reducer, extra=False):
        logging.info('Loading {}'.format(self._name))
        if not self.input_score_obj:
            self.input_score_obj = ScoreObject.from_file(self.in_path)
            if self.has_output:
                self.output_score_obj = ScoreObject.from_file(self.out_path)

        n = len(self.input_score_obj)

        contractions = [
            c for algo in reducer.contractions
            for c in self._load_contraction(reducer, algo)]
        self.mapping = ContractionMapping(contractions, n)
        self.len = self.mapping.output_size
        if self.len != n:
            logging.info('Contractions: {} notes => {} notes'.format(n, self.len))

        self.X = np.empty((n, len(reducer.all_keys)), dtype='float')
        for algo in reducer.algorithms:
            self._load_marking(reducer, algo)
        self.X = self.mapping.map_matrix(self.X)

        n_edge_features = sum(a.n_features for a in reducer.structures)
        features = {}
        d = 0
        structure = defaultdict(lambda: np.zeros(n_edge_features, dtype='float'))
        for algo in reducer.structures:
            data = self._load_structure(reducer, algo)
            for row in data:
                edge, features = row[:2].astype('int'), row[2:]
                structure[tuple(sorted(edge))][d:d + algo.n_features] = features
            d += algo.n_features
        structure = self.mapping.map_structure(structure)
        self.E = np.empty((len(structure), 2), dtype='int')
        self.F = np.empty((len(structure), n_edge_features), dtype='float')
        for i, (k, v) in enumerate(structure.items()):
            self.E[i] = k
            self.F[i] = v

        if self.has_output:
            self.y = np.empty((n, 1), dtype='int')
            self._load_alignment_marking(reducer, reducer.alignment, extra=extra)
            self.y = self.mapping.map_matrix(self.y)

class Dataset:
    def __init__(self, reducer, paths=None, entries=None):
        if entries:
            assert not paths
            self.entries = entries
        else:
            if paths is None:
                paths = DEFAULT_SAMPLES
            self.entries = [DatasetEntry(p.split(':', 1)) for p in paths]

        self.reducer = reducer

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        entries = self.entries[index]

        return Dataset(self.reducer, entries=entries)

    def get_matrices(self, structured=False):
        Xys = [self.load(i, structured=structured) for i in range(len(self))]
        Xs = [X for X, _ in Xys]
        ys = [y for _, y in Xys]

        if not structured:
            X = np.vstack(Xs)
            y = np.vstack(ys)
            return X, y
        else:
            return Xs, ys

    def split_dataset(self, index):
        '''
        Split the dataset into training and validation sets, where scores at
        `index` are put into the validation set.
        '''
        if isinstance(index, Sequence):
            indices = set(index)
        else:
            indices = {index}

        for i in range(len(self)):
            self.load(i)

        train_entries = [e for i, e in enumerate(self.entries) if i not in indices]
        valid_entries = [e for i, e in enumerate(self.entries) if i in indices]

        return (Dataset(self.reducer, entries=train_entries),
                Dataset(self.reducer, entries=valid_entries))

    def load(self, index, structured=False):
        entry = self.entries[index]
        if not entry.loaded:
            entry.load(self.reducer)

        if not structured:
            return entry.X, entry.y
        else:
            return (entry.X, entry.E, entry.F), entry.y

    def find_index(self, paths):
        for i, entry in enumerate(self.entries):
            if '{}:{}'.format(entry.in_path, entry.out_path) == paths:
                return i
        raise IndexError('Sample "{}" does not exist'.format(paths))

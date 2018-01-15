'''
Handles the caching of note features generated by the Reducer.

The cache must be cleared manually when the algorithms themselves are changed.
'''

from collections.abc import Sequence
import hashlib
import h5py
import json
import logging
import numpy as np
import os
import os.path
from .score import ScoreObject
from .alignment import get_alignment_func


CACHE_DIR = 'sample/cache'


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


def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            hasher.update(block)
    return hasher.hexdigest()


def describe_algorithm(algo):
    args = ['algorithm', type(algo).__module__ + '.' + type(algo).__qualname__, *algo.args]
    return json.dumps(args, sort_keys=True)


def describe_alignment(alignment):
    return json.dumps(['alignment', alignment], sort_keys=True)


def set_in_cache(cache, description, value):
    # Since dataset names have limited length, we use the attrs dict to index
    # the dataset name for each description
    if description in cache.attrs:
        key = cache.attrs[description]
        cache[key][:] = value
    else:
        serial = 0
        while any(i == 'cache:{}'.format(serial) for i in cache.attrs.values()):
            serial += 1
        key = 'cache:{}'.format(serial)
        cache.attrs[description] = key
        cache[key] = value


class DatasetEntry:
    def __init__(self, path_pair):
        self.path_pair = path_pair
        self.X = None
        self.y = None
        self.input_score_obj = None
        self.output_score_obj = None

    @property
    def loaded(self):
        return self.X is not None

    def _load_marking(self, reducer, algo, use_cache=True, cache=None):
        description = describe_algorithm(algo)
        if cache and use_cache and description in cache.attrs:
            logging.info('Using cache for {}'.format(type(algo).__name__))
            ds = cache[cache.attrs[description]]
        else:
            self.ensure_scores_loaded()
            algo.create_markings_on(self.input_score_obj)
            ds = np.hstack(
                self.input_score_obj.extract('markings', key, dtype='float', default=0)
                    [:, np.newaxis]
                for key in algo.all_keys)
            if cache:
                set_in_cache(cache, description, ds)

        for i, key in enumerate(algo.all_keys):
            self.X[:, reducer.all_keys.index(key)] = ds[:, i]

    def _load_alignment_marking(self, reducer, alignment, use_cache=True, cache=None):
        description = describe_alignment(alignment)
        if cache and use_cache and description in cache.attrs:
            logging.info('Using cache for alignment')
            ds = cache[cache.attrs[description]]
        else:
            self.ensure_scores_loaded()
            fn = get_alignment_func(alignment)
            fn(self.input_score_obj.score, self.output_score_obj.score)
            ds = self.input_score_obj.extract(fn.label_type, dtype='uint8')
            if cache:
                set_in_cache(cache, description, ds)

        self.y[:, 0] = ds

    def ensure_scores_loaded(self):
        if self.input_score_obj:
            return
        logging.info('Loading score')
        self.input_score_obj = ScoreObject.from_file(self.path_pair[0])
        self.output_score_obj = ScoreObject.from_file(self.path_pair[1])

    def load(self, reducer, use_cache=False, keep_scores=False):
        logging.info('Loading {}'.format(os.path.basename(self.path_pair[0])))

        cache_attrs = {
            'input_sha256': hash_file(self.path_pair[0]),
            'output_sha256': hash_file(self.path_pair[1]),
            }
        cache_path = (
            CACHE_DIR + '/' + os.path.basename(self.path_pair[0]).rsplit('.', 1)[0] + '.hdf5')

        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        with h5py.File(cache_path, 'a') as f:
            if not all(f.attrs.get(k) == v for k, v in cache_attrs.items()) or 'len' not in f.attrs:
                logging.info('Invalidating all cache')
                # Invalidate all cache
                for k, v in f.attrs.items():
                    if k.startswith('cache:'):
                        del f.attrs[k]
                        del f[v]

            if 'len' in f.attrs:
                n = f.attrs['len']
            else:
                self.ensure_scores_loaded()
                f.attrs['len'] = n = len(self.input_score_obj)

            self.X = np.empty((n, len(reducer.all_keys)), dtype='float')
            self.y = np.empty((n, 1), dtype='uint8')

            for algo in reducer.algorithms:
                self._load_marking(reducer, algo, use_cache=use_cache, cache=f)
            self._load_alignment_marking(reducer, reducer.alignment, use_cache=use_cache, cache=f)

            if keep_scores:
                self.ensure_scores_loaded()

        if not keep_scores:
            # Allow garbage collection
            self.input_score_obj = None
            self.output_score_obj = None


class Dataset:
    def __init__(self, reducer, paths=None, use_cache=False, keep_scores=False):
        if paths is None:
            paths = DEFAULT_SAMPLES
        self.reducer = reducer
        self.entries = [DatasetEntry(p.split(':', 1)) for p in paths]
        self.use_cache = use_cache
        self.keep_scores = keep_scores

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        if not isinstance(index, slice):
            index = slice(index, index + 1)

        for i in range(index.start or 0, index.stop or len(self), index.step or 1):
            self.load(i)

        return (np.vstack([e.X for e in self.entries[index]]),
                np.vstack([e.y for e in self.entries[index]]))

    def get_all(self):
        return self[:]

    def split_dataset(self, index):
        '''
        Split the dataset into training and validation sets, where scores at
        `index` are put into the validation set.

        Returns X_train, y_train, X_valid, y_valid
        '''
        if isinstance(index, Sequence):
            indices = set(index)
        else:
            indices = {index}

        for i in range(len(self)):
            self.load(i)

        train_entries = [e for i, e in enumerate(self.entries) if i not in indices]
        valid_entries = [e for i, e in enumerate(self.entries) if i in indices]

        X_train = np.vstack([e.X for e in train_entries])
        y_train = np.vstack([e.y for e in train_entries])
        X_valid = np.vstack([e.X for e in valid_entries])
        y_valid = np.vstack([e.y for e in valid_entries])

        return X_train, y_train, X_valid, y_valid

    def load(self, index):
        entry = self.entries[index]
        if entry.loaded:
            return entry.X, entry.y

        in_path, out_path = entry.path_pair
        entry.load(self.reducer, use_cache=self.use_cache,
                   keep_scores=self.keep_scores)
        return entry.X, entry.y

    def find_index(self, paths):
        for i in range(len(self)):
            if ':'.join(self.entries[i].path_pair) == paths:
                return i
        raise IndexError('Sample "{}" does not exist'.format(paths))

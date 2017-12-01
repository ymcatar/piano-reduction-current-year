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


CACHE_DIR = 'sample/cache'

def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            hasher.update(block)
    return hasher.hexdigest()


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

    def load(self, reducer, use_cache=False, keep_scores=False):
        loaded_from_cache = False
        if use_cache:
            cache_attrs = {
                'input_sha256': hash_file(self.path_pair[0]),
                'output_sha256': hash_file(self.path_pair[1]),
                'reducer_args': json.dumps(reducer.reducer_args, sort_keys=True),
                }
            cache_path = (
                CACHE_DIR + '/' + os.path.basename(self.path_pair[0]).rsplit('.', 1)[0] + '.hdf5')

            try:
                with h5py.File(cache_path, 'r') as f:
                    if all(f.attrs[k] == v for k, v in cache_attrs.items()):
                        logging.info('Using cache for {}'.format(
                            os.path.basename(self.path_pair[0])))
                        # Use cache
                        self.X = np.array(f['X'])
                        self.y = np.array(f['y'])

                        loaded_from_cache = True
            except OSError:
                pass

        if not loaded_from_cache or keep_scores:
            logging.info('Loading {}'.format(os.path.basename(self.path_pair[0])))
            sample_in = ScoreObject.from_file(self.path_pair[0])
            sample_out = ScoreObject.from_file(self.path_pair[1])

            if keep_scores:
                self.input_score_obj = sample_in
                self.output_score_obj = sample_out

        if not loaded_from_cache:
            self.X = reducer.create_markings_on(sample_in)
            self.y = reducer.create_alignment_markings_on(sample_in, sample_out)
            self.y = self.y[:, np.newaxis]

        if use_cache and not loaded_from_cache:
            if not os.path.exists(CACHE_DIR):
                os.mkdir(CACHE_DIR)
            with h5py.File(cache_path, 'w') as f:
                f.attrs.update(cache_attrs)

                f['X'] = self.X
                f['y'] = self.y


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

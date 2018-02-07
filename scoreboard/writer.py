import binascii
from collections import defaultdict
import copy
import datetime
from fractions import Fraction
from itertools import product
import json
import logging
import music21
import os
import numpy as np


class BaseFeature:
    def __init__(self, name, dtype, default=None, help=''):
        self.name = name
        self.dtype = dtype
        self.default = default
        self.help = help


class BoolFeature(BaseFeature):
    def __init__(self, name, default=False, help=''):
        super().__init__(name, dtype='bool', default=default, help=help)


class FloatFeature(BaseFeature):
    def __init__(self, name, range=None, default=0.0, help=''):
        '''
        range: A pair (low, high) representing the range of values it can take.
            Set any of it to None to indicate unbounded.
        '''
        super().__init__(name, dtype='float', default=default, help=help)
        self.range = range or (None, None)


class CategoricalFeature(BaseFeature):
    def __init__(self, name, legend, default, help=''):
        '''
        legend: A dict mapping label to tuple (#XXXXXX, label).
        '''
        super().__init__(name, dtype='categorical', default=default, help=help)
        self.legend = legend
    ...


def generate_colours():
    '''
    Generate unique colours to colour each note.
    '''
    for rgb in product(range(1, 51, 2), repeat=3):
        yield '#{:02X}{:02X}{:02X}'.format(*rgb)


def iter_notes(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes, including those
    inside a chord.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, music21.chord.Chord):
            for n2 in n:
                yield n2
        else:
            yield n


class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Fraction):
            return float(obj)
        else:
            return super().default(obj)


class LogWriter:
    '''
    A log and score aggregator that produces data which can be read by
    Scoreboard.
    '''
    def __init__(self, log_dir, run=None):
        self.run = run or \
            str(binascii.b2a_hex(os.urandom(4)), 'ascii')

        self.dir = os.path.join(log_dir, self.run)
        os.mkdir(self.dir)

        self.colour_it = generate_colours()

        self.timestamp = int(datetime.datetime.now().timestamp())
        self.scores = []
        self.features = {}

        self.score_instances = {}

    def add_feature(self, feature):
        self.features[feature.name] = feature

    def add_features(self, features):
        for feature in features:
            self.add_feature(feature)

    def add_score(self, name, score):
        score = copy.deepcopy(score)
        self.score_instances[name] = score

        for n in iter_notes(score, recurse=True):
            n.style.color = next(self.colour_it)

        feature_data = defaultdict(list)
        for n in iter_notes(score, recurse=True):
            feature_data[n.style.color] = {
                **n.editorial.misc,
                '_pitch': n.pitch.nameWithOctave,
                '_pitch_class': n.pitch.name,
                '_ps': n.pitch.ps,
                '_duration': n.duration.quarterLength,
                }

        score.write('musicxml', fp=os.path.join(self.dir, name + '.xml'))
        with open(os.path.join(self.dir, name + '.json'), 'w') as f:
            json.dump(feature_data, f, indent=2, cls=MyJSONEncoder)

        self.scores.append({
            'name': name,
            'xml': name + '.xml',
            'featureData': name + '.json'
            })

    def get_metadata(self):
        return {
            'timestamp': self.timestamp,
            'scores': self.scores,
            'features': [f.__dict__ for f in self.features.values()]
            }

    def finalize(self):
        # Determine bounds for float features
        for feature in self.features.values():
            if isinstance(feature, FloatFeature):
                low, high = feature.range
                def values():
                    yield feature.default
                    yield from (
                        n.editorial.misc.get(feature.name, feature.default)
                        for score in self.score_instances.values()
                        for n in iter_notes(score, recurse=True))
                if low is None:
                    low = min(values())
                if high is None:
                    high = max(values())
                feature.range = low, high

        metadata = self.get_metadata()
        with open(os.path.join(self.dir, 'index.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

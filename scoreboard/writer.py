import binascii
from collections import defaultdict
import copy
import datetime
from fractions import Fraction
from itertools import chain, product
import json
import logging
from matplotlib import cm, colors
import music21
import os
import textwrap
import numpy as np


class BaseFeature:
    def __init__(self, name, dtype, default=None, help='', group=None):
        self.name = name
        self.dtype = dtype
        self.default = default
        self.help = help
        self.group = group


class BoolFeature(BaseFeature):
    def __init__(self, name, default=False, help='', group=None):
        super().__init__(name, dtype='bool', default=default, help=help,
                         group=group)


class TextFeature(BaseFeature):
    def __init__(self, name, default='', help='', group=None):
        super().__init__(name, dtype='text', default=default, help=help,
                         group=group)


class FloatFeature(BaseFeature):
    def __init__(self, name, range=None, default=0.0, help='', group=None):
        '''
        range: A pair (low, high) representing the range of values it can take.
            Set any of it to None to indicate unbounded.
        '''
        super().__init__(name, dtype='float', default=default, help=help,
                         group=group)
        self.range = range or (None, None)


class CategoricalFeature(BaseFeature):
    def __init__(self, name, legend, default, help='', group=None):
        '''
        legend: A dict mapping label to tuple (#XXXXXX, label).
        '''
        super().__init__(name, dtype='categorical', default=default, help=help,
                         group=group)
        self.legend = legend


class StructureFeature(BaseFeature):
    def __init__(self, name, feature, directed=False, help='', group=None):
        self.feature = feature
        self.directed = directed
        super().__init__(name, dtype='structure', help=help, group=group)

    def json(self):
        return {**self.__dict__, 'feature': self.feature.__dict__}


def generate_colours():
    '''
    Generate unique colours to colour each note.
    '''
    for rgb in product(range(1, 121, 1), repeat=3):
        yield '#{:02X}{:02X}{:02X}'.format(*rgb)


def iter_notes_with_offset(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes with the offset
    value, including those inside a chord.

    Note that Notes inside a chord always have an offset value of 0.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, music21.chord.Chord):
            for n2 in n:
                yield n2, n.offset
        else:
            yield n, n.offset


class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Fraction):
            return float(obj)
        else:
            return super().default(obj)


pitch_class_colours = [
    '#{:02X}{:02X}{:02X}'.format(*(int(i * 255) for i in rgba[:3]))
    for rgba in cm.ScalarMappable(colors.Normalize(0, 12), cm.hsv).to_rgba(range(12))
    ]


default_features = [
    TextFeature('_pitch', group='intrinsic'),
    CategoricalFeature('_pitch_class', {
            n: (c, n)
            for c, ns in zip(pitch_class_colours, [
                ['B#', 'C'],
                ['C#', 'D-'],
                ['D'],
                ['D#', 'E-'],
                ['E', 'F-'],
                ['E#', 'F'],
                ['F#', 'G-'],
                ['G'],
                ['G#', 'A-'],
                ['A'],
                ['A#', 'B-'],
                ['B', 'C-'],
                ]) for n in ns}, '#000000', group='intrinsic'),
    FloatFeature('_ps', range=(21, 108), group='intrinsic'),
    FloatFeature('_duration', range=(0, 8), group='intrinsic'),
    TextFeature('_offset', group='intrinsic'),
    ]


class LogWriter:
    '''
    A log and score aggregator that produces data which can be read by
    Scoreboard.
    '''
    def __init__(self, log_dir, run=None, title=None):
        self.run = run or \
            str(binascii.b2a_hex(os.urandom(4)), 'ascii')

        self.dir = os.path.join(log_dir, self.run)
        os.mkdir(self.dir)

        self.colour_it = generate_colours()

        self.timestamp = int(datetime.datetime.now().timestamp())
        self.title = title
        self.flavours = []
        self.features = {}
        self.structure_features = {}

        self.score_indices = {}
        self.score_data = {}

    def add_feature(self, feature):
        if feature.dtype == 'structure':
            self.structure_features[feature.name] = feature
        else:
            self.features[feature.name] = feature

    def add_features(self, features):
        for feature in features:
            self.add_feature(feature)

    def add_score(self, name, score, structure_data=None, flavour=True, **kwargs):
        score = copy.deepcopy(score)

        note_colours = []
        for n, _ in iter_notes_with_offset(score, recurse=True):
            n.style.color = next(self.colour_it)
            note_colours.append(n.style.color)

        notes = defaultdict(list)
        for measure in score.recurse(skipSelf=False).getElementsByClass(music21.stream.Measure):
            for n, offset in iter_notes_with_offset(measure, recurse=True):
                notes[n.style.color] = {
                    **n.editorial.misc,
                    '_pitch': n.pitch.nameWithOctave,
                    '_pitch_class': n.pitch.name,
                    '_ps': n.pitch.ps,
                    '_duration': n.duration.quarterLength,
                    '_offset': measure.offset + offset,
                    }

        structures = {}
        if structure_data:
            for feat, data in structure_data.items():
                structures[feat] = {}
                for (u, v), f in data:
                    structures[feat][note_colours[u] + ':' + note_colours[v]] = f

        self.score_data[name] = {
            'notes': notes,
            'structures': structures,
            }
        self.score_indices[name] = {
            'score': score,
            **kwargs
            }

        if flavour:
            self.add_flavour([name], **kwargs)

    def add_flavour(self, names, **kwargs):
        '''
        Create a combined view of multiple scores.
        '''

        # Compute metadata
        indices = [self.score_indices[n] for n in names]
        name = '_'.join(names)
        title = ' + '.join(idx.get('title', n) for n, idx in zip(names, indices))
        help = kwargs.get('help')
        if not help:
            help = '\n'.join(idx.get('title', n) + ': ' + idx.get('help', '')
                             for n, idx in zip(names, indices))

        # Combine scores
        score = music21.stream.Score()
        score.metadata = (self.score_indices[names[0]]['score'].metadata or
            music21.metadata.Metadata(title='', composer=''))

        for n in names:
            index = self.score_indices[n]
            parts = index['score'].parts
            group_name = index.get('title', n)

            # Rename parts to indicate their group
            for part in parts:
                # Backup the original part name
                if not 'partName' in part.editorial.misc:
                    part.editorial.misc['partName'] = part.partName
                abbrev = part.partAbbreviation or part.editorial.misc.get('partName')
                if not abbrev:
                    inst = part.getInstrument()
                    if inst:
                        abbrev = inst.instrumentAbbreviation or inst.instrumentName or '?'
                part.partName = '({}) {}'.format(group_name, abbrev)
                score.insert(0, part)

            # Add a brace for clarity
            sg = music21.layout.StaffGroup(list(parts), name=group_name, symbol='brace')
            score.insert(0, sg)

        score.write('musicxml', fp=os.path.join(self.dir, name + '.xml'))

        # Write feature data
        datas = [self.score_data[n] for n in names]
        out = {
            'notes': dict(p for data in datas for p in data['notes'].items()),
            'structures': dict(p for data in datas for p in data['structures'].items()),
            }
        with open(os.path.join(self.dir, name + '.json'), 'w') as f:
            json.dump(out, f, indent=2, cls=MyJSONEncoder)

        self.flavours.append({
            'name': name,
            'xml': name + '.xml',
            'featureData': name + '.json',
            'title': title,
            'help': help,
            })

    def get_metadata(self):
        return {
            'timestamp': self.timestamp,
            'title': self.title or '',
            'scores': self.flavours,
            'features': [f.__dict__ for f in self.features.values()],
            'structureFeatures': [f.json() for f in self.structure_features.values()]
            }

    def finalize(self):
        self.add_features(default_features)
        # Determine bounds for float features
        all_features = chain(
            self.features.values(),
            (f.feature for f in self.structure_features.values()))
        for feature in all_features:
            if isinstance(feature, FloatFeature):
                low, high = feature.range

                def values():
                    yield feature.default
                    yield from (
                        n.editorial.misc.get(feature.name, feature.default)
                        for idx in self.score_indices.values()
                        for n, _ in iter_notes_with_offset(idx['score'], recurse=True))
                if low is None:
                    low = min(values())
                if high is None:
                    high = max(values())
                feature.range = low, high

        metadata = self.get_metadata()
        with open(os.path.join(self.dir, 'index.json'), 'w') as f:
            json.dump(metadata, f, indent=2)


def guess_feature(algo):
    if getattr(algo, 'feature', None):
        return algo.feature

    help = algo.__doc__ or algo.run.__doc__ or ''
    help = textwrap.dedent(help).strip()
    dtype = getattr(algo, 'dtype', 'bool')
    if dtype == 'float':
        return FloatFeature(
            algo.key, getattr(algo, dtype, getattr(algo, 'range')),
            help=help, group='input')
    else:
        return BoolFeature(algo.key, help=help, group='input')


def guess_features(algo):
    if getattr(algo, 'features', None):
        return algo.features

    features = []
    for key in algo.all_keys:
        feature = guess_feature(algo)
        feature.name = key
        features.append(feature)

    return features

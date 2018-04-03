from .base import FeatureAlgorithm, get_markings
from ..util import ensure_algorithm, dump_algorithm
from scoreboard import writer

from itertools import combinations


class ProductTerms(FeatureAlgorithm):
    '''
    Create AND terms with up to `degree` atoms. For example, inputs x_1, x_2,
    x_3 with degree 2 outputs x_1, x_2, x_3, x_1*x_2, x_2*x_3, x_1*x_3.
    '''
    def __init__(self, algos, degree=2):
        self.algos = [ensure_algorithm(a) for a in algos]
        self.degree = degree
        self._key_prefix = '?'

    @property
    def key_prefix(self):
        return self._key_prefix

    @key_prefix.setter
    def key_prefix(self, value):
        self._key_prefix = value
        for i, algo in enumerate(self.algos):
            algo.key_prefix = '{}_{}'.format(value, i)

        self.base_keys = []
        for algo in self.algos:
            self.base_keys.extend(algo.all_keys)
        self.composite_key_defs = {}
        for d in range(2, self.degree+1):
            for factors in combinations(self.base_keys, d):
                facs = [f[f.index('_')+1:] for f in factors]
                key = self.key_prefix + '_' + '_And_'.join(facs)
                self.composite_key_defs[key] = factors
        self.composite_keys = list(self.composite_key_defs.keys())

    @property
    def all_keys(self):
        return [*self.base_keys, *self.composite_keys]

    def run(self, score_obj):
        for algo in self.algos:
            algo.run(score_obj)

        for key, factors in self.composite_key_defs.items():
            for n in score_obj:
                value = get_markings(n).get(factors[0], 0)
                for f in factors[1:]:
                    value *= get_markings(n).get(f, 0)
                get_markings(n)[key] = value

    @property
    def args(self):
        algos = [dump_algorithm(a) for a in self.algos]
        return [], {'algos': algos, 'degree': self.degree}

    @property
    def features(self):
        features = []
        for algo in self.algos:
            for key in algo.all_keys:
                feature = writer.guess_feature(algo)
                feature.name = key
                features.append(feature)

        for key, factors in self.composite_key_defs.items():
            feature = writer.BoolFeature(key, help=' AND '.join(factors), group='input')
            features.append(feature)

        return features

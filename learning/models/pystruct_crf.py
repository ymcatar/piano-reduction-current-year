from collections import namedtuple
from itertools import product
import numpy as np
from .base import BaseModel
from pystruct.learners import NSlackSSVM
from pystruct.models import EdgeFeatureGraphCRF
import h5py


Variable = namedtuple('Variable', ['id', 'name'])


class MyGraphCRF(EdgeFeatureGraphCRF):
    '''
    A PyStruct Model class that chooses proper dimensions according to a Reducer
    object, and implements parameter tying.
    '''
    def __init__(self, reducer):
        n_states = 3 if reducer.label_type == 'hand' else 2
        n_edge_features = sum(a.n_features for a in reducer.structures)

        self.pairwise_variables = []
        pairwise_indices = []

        for algo in reducer.structures:
            def var_fn(name=None):
                name = '{}_{}'.format(algo.key, name or str(len(self.pairwise_variables)))
                var = Variable(id=len(self.pairwise_variables), name=name)
                self.pairwise_variables.append(var)
                return var

            var_mats = algo.get_weights(reducer.label_type, var_fn)

            if not isinstance(var_mats[0][0], list):
                var_mats = [var_mats]
            assert (len(var_mats), len(var_mats[0]), len(var_mats[0][0])) == \
                (algo.n_features, n_states, n_states), 'get_weights returned wrong dimensions'

            pairwise_indices.append([[[i.id for i in row] for row in mat] for mat in var_mats])

        self.pairwise_indices = np.concatenate(pairwise_indices)

        super().__init__(
            n_states=n_states, n_features=len(reducer.all_keys),
            n_edge_features=n_edge_features, inference_method='ad3')

    def get_unary_weights(self, w):
        return w[:self.n_states * self.n_features].reshape(self.n_features, self.n_states)

    def get_pairwise_weights(self, w):
        edge_weights = np.asarray(w[self.n_states * self.n_features:])
        return edge_weights[self.pairwise_indices]

    def _set_size_joint_feature(self):
        self.size_joint_feature = self.n_states * self.n_features + len(self.pairwise_variables)

    def _get_pairwise_potentials(self, x, w):
        self._check_size_w(w)
        self._check_size_x(x)
        edge_features = self._get_edge_features(x)
        pairwise = self.get_pairwise_weights(w).reshape(self.n_edge_features, -1)
        return np.dot(edge_features, pairwise).reshape(
            edge_features.shape[0], self.n_states, self.n_states)

    def joint_feature(self, x, y):
        vec = super().joint_feature(x, y)
        unaries = vec[:self.n_states * self.n_features]

        edge_features = vec[self.n_states * self.n_features:].reshape(
            self.n_edge_features, self.n_states, self.n_states)
        pairwise = np.zeros(len(self.pairwise_variables), dtype='float')
        for i in product(*(range(i) for i in self.pairwise_indices.shape)):
            pairwise[self.pairwise_indices[i]] += edge_features[i]

        return np.concatenate([unaries, pairwise])


class PyStructCRF(BaseModel):
    '''
    Implements a CRF model with PyStruct.

    There are unary and pairwise potentials. Note that pairwise potentials are
    directed.
    '''
    def __init__(self, reducer):
        super().__init__(reducer)
        self.model = MyGraphCRF(reducer)
        self.learner = NSlackSSVM(self.model, max_iter=250, verbose=1, C=1.0)

    def fit_structured(self, X, y):
        y = [i.flatten() for i in y]
        self.learner.fit(X, y)

    def evaluate_structured(self, X, y):
        y = [i.flatten() for i in y]
        return 1 - self.learner.score(X, y)

    def predict_structured(self, X):
        # For compatibility with non-graphical models, we generate
        # probabilistic predictions rather than just the final label.
        y_pred = self.learner.predict([X])[0]
        y_proba = np.zeros((len(y_pred), self.model.n_states), dtype='float')
        y_proba[np.arange(len(y_pred)), y_pred] = 1.0
        return y_proba

    def save(self, fp):
        with h5py.File(fp, 'w') as f:
            f['w'] = self.learner.w

    def load(self, fp):
        with h5py.File(fp, 'r') as f:
            self.learner.w = np.asarray(f['w'])

    def describe_weights(self):
        w = self.learner.w
        items = []
        # Unary features
        mat = self.model.get_unary_weights(w)
        mat = mat[:, 1:] - mat[:, 0:1]  # Weights relative to class 0
        items.extend(zip(self.reducer.all_keys, mat))

        # Sort weights
        items.sort(key=lambda i: -np.mean(i[1]))

        # Edge features
        mat = self.model.get_pairwise_weights(w)
        i = 0
        for algo in self.reducer.structures:
            for j in range(algo.n_features):
                items.append(('{}_{}'.format(algo.key, j), mat[i, :, :]))
                i += 1

        assert i == self.model.n_edge_features

        return items

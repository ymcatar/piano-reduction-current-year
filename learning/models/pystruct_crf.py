import numpy as np
from .base import BaseModel
from pystruct.learners import NSlackSSVM
from pystruct.models import EdgeFeatureGraphCRF
import h5py


class PyStructCRF(BaseModel):
    '''
    Implements a CRF model with PyStruct.

    There are unary and pairwise potentials. Note that pairwise potentials are
    directed.
    '''
    def __init__(self, reducer):
        super().__init__(reducer)

        n_states = 3 if reducer.label_type == 'hand' else 2
        n_edge_features = sum(a.n_features for a in reducer.structures)
        self.model = EdgeFeatureGraphCRF(
            n_states=n_states, n_features=len(reducer.all_keys),
            n_edge_features=n_edge_features, inference_method='max-product')

        self.learner = NSlackSSVM(self.model, max_iter=100, verbose=1, C=0.1)

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
        n_features = self.model.n_features
        n_states = self.model.n_states
        items = []
        # Unary features
        mat = w[:n_features * n_states].reshape(n_features, n_states)
        items.extend(zip(self.reducer.all_keys, mat))

        # Sort weights descendingly by their mean absolute value
        items.sort(key=lambda i: -np.mean(np.abs(i[1])))

        # Edge features
        i = n_features * n_states
        for algo in self.reducer.structures:
            for j in range(algo.n_features):
                mat = w[i:i + n_states**2].reshape(n_states, n_states)
                items.append(('{}_{}'.format(algo.key, j), mat))
                i += algo.n_features * n_states**2

        assert i == len(w)

        return items

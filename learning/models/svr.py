from collections import defaultdict
import numpy as np
from sklearn.svm import LinearSVC
from .base import BaseModel
from ..piano import algorithm, alignment, contraction, structure


class SupportVectorRegression(BaseModel):
    def __init__(self, reducer):
        super().__init__(reducer)
        assert reducer.label_type == 'align'
        assert type(reducer.algorithms[0]) == algorithm.OffsetValue
        assert type(reducer.algorithms[1]) == algorithm.OutputCountEstimate
        self.model = LinearSVC(loss='hinge')

    def fit_structured(self, X, y):
        X,y = self.convert_training_data(X, y)
        self.model.fit(X, y)

    def evaluate_structured(self, X, y):
        X, y = self.convert_training_data(X, y)
        y_pred = self.model.predict(X)
        return np.mean(y != y_pred)

    def predict_structured(self, X):
        X = X[0]
        utility = self.model.decision_function(X[:, 2:])
        onsets = defaultdict(lambda: {'count': 0, 'items': []})
        for i, (x, u) in enumerate(zip(X, utility)):
            onsets[x[0]]['count'] = x[1]
            onsets[x[0]]['items'].append((u, i))

        y = np.zeros(len(X), dtype='float')
        for data in onsets.values():
            data['items'].sort(key=lambda ui: -ui[0])
            output_count = int(round(data['count']))
            for i in range(min(output_count, len(data['items']))):
                y[data['items'][i][1]] = 1.0

        return y[:, np.newaxis]

    def convert_training_data(self, Xs, ys):
        features, labels = [], []
        for (X, _, _), y in zip(Xs, ys):
            onsets = defaultdict(lambda: ([], []))
            for x, y_ in zip(X, y):
                onsets[x[0]][int(y_)].append(x[2:])
            for discards, keeps in onsets.values():
                for k in keeps:
                    for d in discards:
                        # Partial ordering: k >= d and not (d >= k)
                        features.append(k - d)
                        labels.append(1)
                        features.append(d - k)
                        labels.append(0)

        features = np.asarray(features)
        labels = np.asarray(labels)

        return features, labels

    def save(self, fp):
        '''
        Save the model parameters to the given file object.
        '''
        # column vectors
        w = np.concatenate([self.model.coef_.flatten(), self.model.intercept_])
        with open(fp, 'wb') as f:
            np.save(f, w, allow_pickle=False)

    def load(self, fp):
        '''
        Load the model parameters from the given file object.
        '''
        with open(fp, 'rb') as f:
            w = np.load(f, allow_pickle=False)
        # column vectors
        self.model.coef_ = w[np.newaxis, :-1]
        self.model.intercept_ = w[-1]


reducer_args = {
    'algorithms': [
        algorithm.OffsetValue(),
        algorithm.OutputCountEstimate(),
        algorithm.ActiveRhythm(),
        algorithm.BassLine(),
        algorithm.OnsetAfterRest(),
        algorithm.RhythmVariety(),
        algorithm.SustainedRhythm(),
        algorithm.VerticalDoubling(),
        algorithm.Motif(),
        algorithm.Harmony(sub_keys=('base', '3rd', '5th', 'dissonance')),
        algorithm.HighestPitchInRhythm(),
        ],
    'alignment': alignment.AlignMinOctaveMatching(use_hand=False),
    'contractions': [
        contraction.ContractTies(),
        contraction.ContractByPitchOnset(),
        ],
    'structures': [],
    }

Model = SupportVectorRegression


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

import pickle
from .base import BaseModel


class WrappedSklearnModel(BaseModel):
    def __init__(self, Model, reducer, *args, **kwargs):
        self.reducer = reducer
        self.model = Model(*args, **kwargs)

    def fit(self, X, Y):
        if len(Y.shape) == 2 and Y.shape[1] == 1:
            Y = Y[:, 0]

        return self.model.fit(X, Y)

    def evaluate(self, X, Y):
        if len(Y.shape) == 2 and Y.shape[1] == 1:
            Y = Y[:, 0]

        return self.model.score(X, Y)

    def predict(self, X):
        result = self.model.predict_proba(X)

        # If the model is binary, output only the probabilities for the
        # positive class.
        if len(result.shape) == 2:
            return result[:, 1:2]

        return result

    def describe(self):
        return type(self.model).__name__

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self.model, f)

    def load(self, filename):
        with open(filename, 'rb') as f:
            self.model = pickle.load(f)


MultinomialLogistic = functools.partial(
    WrappedSklearnModel,
    functools.partial(
        LogisticRegression, multi_class='multinomial', solver='sag',
        max_iter=1000)
    )

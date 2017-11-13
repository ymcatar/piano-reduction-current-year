from .base import BaseModel


class WrappedSklearnModel(BaseModel):
    def __init__(self, Model, reducer, *args, **kwargs):
        self.reducer = reducer
        self.model = Model(*args, **kwargs)

    def fit(self, X, Y):
        return self.model.fit(X, Y)

    def evaluate(self, X, Y):
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

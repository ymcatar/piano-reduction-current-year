import numpy as np


class BaseModel(object):
    def __init__(self, pre_processor):
        self.pre_processor = pre_processor

    def fit(self, X, y):
        '''
        Train the model using the provided sample data.
        '''
        raise NotImplementedError()

    def evaluate(self, X, y):
        '''
        Evaluate the model using the provided sample data. The metric is
        model-specific.
        '''
        raise NotImplementedError()

    def predict(self, X):
        '''
        Predict using the model.

        Returns a 2D array, in each each value correponds to the probability of
        a predicted class.
        '''
        raise NotImplementedError()

    def fit_structured(self, X, y):
        real_X = np.vstack([nodes for nodes, _, _ in X])
        real_y = np.vstack(list(y))
        self.fit(real_X, real_y)

    def evaluate_structured(self, X, y):
        real_X = np.vstack([nodes for nodes, _, _ in X])
        real_y = np.vstack(list(y))
        return self.evaluate(real_X, real_y)

    def predict_structured(self, X):
        real_X, _, _ = X
        return self.predict(real_X)

    def describe(self):
        '''
        Returns a short description of the model.
        '''
        return type(self).__name__

    def describe_weights(self):
        '''
        Returns a list of (key, value) pairs for the model weights.
        '''
        return NotImplemented  # Optional

    def save(self, fp):
        '''
        Save the model parameters to the given file object.
        '''
        raise NotImplementedError()

    def load(self, fp):
        '''
        Load the model parameters from the given file object.
        '''
        raise NotImplementedError()

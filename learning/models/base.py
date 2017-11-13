class BaseModel(object):
    def __init__(self, reducer):
        self.reducer = reducer

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

    def describe(self):
        '''
        Returns a short description of the model.
        '''
        return type(self).__name__

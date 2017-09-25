from test import dataset, target, reducer

import numpy as np

from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier


# Training data
X = dataset['input']
y = dataset['target']

# Compatibility class for classifying test data
class ModelWrapper:
    def __init__(self, model):
        '''
        model: An sklearn classifier model.
        '''
        self.model = model

    def activate(self, inputs):
        '''
        input: A tuple containing the input features.

        Returns: a 1D array containing the single output label
        '''
        X_test = np.array(inputs)[np.newaxis,:]

        return self.model.predict(X_test)[:]

print('training model')

model_name = 'rforest'
if model_name == 'svm':
    # Support vector machine
    model = LinearSVC()
    model.fit(X, y)
    print('>> training accuracy =', model.score(X, y))

elif model_name == 'logistic':
    model = LogisticRegression()
    model.fit(X, y)
    print('>> training accuracy =', model.score(X, y))

elif model_name == 'dtree':
    model = DecisionTreeClassifier(max_depth=7)
    model.fit(X, y)
    print('>> training accuracy =', model.score(X, y))

elif model_name == 'rforest':
    model = RandomForestClassifier()
    model.fit(X, y)
    print('>> training accuracy =', model.score(X, y))


print('generating score')
target.classify(network=ModelWrapper(model), reducer=reducer)
final_result = target.generatePianoScore(reduced=True, playable=True)
final_result.show('musicxml')

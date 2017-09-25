import os
import sys
sys.path.insert(0, os.getcwd())

from learning.test import dataset, target, reducer

import os
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

OUTPUT_PREFIX = os.path.dirname(__file__) + '/output/'
os.makedirs(OUTPUT_PREFIX, exist_ok=True)

def evaluate(model, filename):
    target.classify(network=ModelWrapper(model), reducer=reducer)
    final_result = target.generatePianoScore(reduced=True, playable=True)
    final_result.write('musicxml', OUTPUT_PREFIX + filename)
    print()
    print('[{}] Training accuracy = {}'.format(filename, model.score(X, y)))


print('>>> Support vector machine')
model = LinearSVC()
model.fit(X, y)
evaluate(model, 'svm.xml')

print('>>> Logistic regression')
model = LogisticRegression()
model.fit(X, y)
evaluate(model, 'logistic.xml')

print('>>> Decision tree')
model = DecisionTreeClassifier(max_depth=7)
model.fit(X, y)
evaluate(model, 'dtree.xml')

print('>>> Random forest')
model = RandomForestClassifier()
model.fit(X, y)
evaluate(model, 'rforest.xml')

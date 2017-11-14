import tensorflow as tf
import tflearn
from .base import BaseModel


class LogisticModel(tflearn.DNN, BaseModel):
    def __init__(self, reducer):
        self.reducer = reducer

        n_features = len(reducer.all_keys)

        # Create network here
        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 1, activation='sigmoid')
        net = tflearn.regression(net, optimizer='adam', loss='binary_crossentropy')

        tflearn.DNN.__init__(self, net)


class NNModel(tflearn.DNN, BaseModel):
    def __init__(self, reducer):
        self.reducer = reducer

        n_features = len(reducer.all_keys)

        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 2 * n_features, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='sigmoid')

        optimizer = tflearn.optimizers.Adam(learning_rate=1e-4)
        net = tflearn.regression(net, optimizer=optimizer, loss='binary_crossentropy')

        tflearn.DNN.__init__(self, net)

    def fit(self, X, Y):
        super().fit(X, Y, n_epoch=100)


class WeightedObjectiveNNModel(tflearn.DNN, BaseModel):
    def __init__(self, reducer):
        self.reducer = reducer

        n_features = len(reducer.all_keys)

        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 2 * n_features, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='sigmoid')

        optimizer = tflearn.optimizers.Adam(learning_rate=1e-4)
        def loss(y_pred, y_true):
            return tflearn.objectives.weighted_crossentropy(y_pred, y_true, 0.7)
        net = tflearn.regression(net, optimizer=optimizer, loss=loss)

        tflearn.DNN.__init__(self, net)

    def fit(self, X, Y):
        super().fit(X, Y, n_epoch=100)

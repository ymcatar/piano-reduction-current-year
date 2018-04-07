import tensorflow as tf
import tflearn
from .tf import TflearnModel


class NN(TflearnModel):
    def __init__(self, pre_processor):
        n_features = len(pre_processor.all_keys)
        tf.reset_default_graph()

        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 2 * n_features, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='sigmoid')

        optimizer = tflearn.optimizers.Adam(learning_rate=1e-4)
        net = tflearn.regression(net, optimizer=optimizer, loss='binary_crossentropy')

        super().__init__(pre_processor, net)

    def fit(self, X, Y):
        super().fit(X, Y, n_epoch=10, shuffle=True)


class NNWeightedObjective(TflearnModel):
    def __init__(self, pre_processor):
        n_features = len(pre_processor.all_keys)
        tf.reset_default_graph()

        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 2 * n_features, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='sigmoid')

        optimizer = tflearn.optimizers.Adam(learning_rate=1e-4)

        def loss(y_pred, y_true):
            return tflearn.objectives.weighted_crossentropy(y_pred, y_true, 0.7)
        net = tflearn.regression(net, optimizer=optimizer, loss=loss)

        super().__init__(pre_processor, net)

    def fit(self, X, Y):
        super().fit(X, Y, n_epoch=100)

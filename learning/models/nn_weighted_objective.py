import tensorflow as tf
import tflearn
from .tf import TflearnModel
from ..piano import algorithm
from ..piano.alignment.pitch_class_onset import AlignPitchClassOnset


class NNWeightedObjective(TflearnModel):
    def __init__(self, reducer):
        n_features = len(reducer.all_keys)
        tf.reset_default_graph()

        net = tflearn.input_data(dtype=tf.float32, shape=[None, n_features])
        net = tflearn.fully_connected(net, 2 * n_features, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='sigmoid')

        optimizer = tflearn.optimizers.Adam(learning_rate=1e-4)

        def loss(y_pred, y_true):
            return tflearn.objectives.weighted_crossentropy(y_pred, y_true, 0.7)
        net = tflearn.regression(net, optimizer=optimizer, loss=loss)

        super().__init__(reducer, net)

    def fit(self, X, Y):
        super().fit(X, Y, n_epoch=100)


reducer_args = {
    'algorithms': [
        algorithm.ActiveRhythm(),
        algorithm.BassLine(),
        algorithm.EntranceEffect(),
        algorithm.Occurrence(),
        algorithm.OnsetAfterRest(),
        algorithm.PitchClassStatistics(),
        algorithm.RhythmVariety(),
        algorithm.StrongBeats(division=0.5),
        algorithm.SustainedRhythm(),
        algorithm.VerticalDoubling(),
        algorithm.Motif(),
        algorithm.Harmony(),
        ],
    'alignment': AlignPitchClassOnset(),
    }


Model = NNWeightedObjective


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

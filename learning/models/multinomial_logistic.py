import functools
from .sk import WrappedSklearnModel
from sklearn.linear_model import LogisticRegression
from ..piano import algorithm
from ..piano.alignment.min_octave_hand import AlignMinOctaveHand


class MultinomialLogistic(WrappedSklearnModel):
    def __init__(self, *args, **kwargs):
        Model = functools.partial(
            LogisticRegression, multi_class='multinomial', solver='sag',
            max_iter=5000)
        super().__init__(Model, *args, **kwargs)


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
    'alignment': AlignMinOctaveHand(),
    }


Model = MultinomialLogistic


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

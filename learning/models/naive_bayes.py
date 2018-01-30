import functools
from .sk import WrappedSklearnModel
from sklearn.naive_bayes import MultinomialNB

from ..piano import algorithm
from ..piano.alignment.min_octave_hand import AlignMinOctaveHand


class NaiveBayes(WrappedSklearnModel):
    def __init__(self, *args, **kwargs):
        Model = functools.partial(MultinomialNB)
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


Model = NaiveBayes


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

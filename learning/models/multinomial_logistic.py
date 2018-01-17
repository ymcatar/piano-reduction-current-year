import functools
from .sk import WrappedSklearnModel
from sklearn.linear_model import LogisticRegression


class MultinomialLogistic(WrappedSklearnModel):
    def __init__(self, *args, **kwargs):
        Model = functools.partial(
            LogisticRegression, multi_class='multinomial', solver='sag',
            max_iter=1000)
        super().__init__(Model, *args, **kwargs)


reducer_args = {
    'algorithms': [
        ('learning.piano.algorithm.ActiveRhythm', [], {}),
        ('learning.piano.algorithm.BassLine', [], {}),
        ('learning.piano.algorithm.EntranceEffect', [], {}),
        ('learning.piano.algorithm.Occurrence', [], {}),
        ('learning.piano.algorithm.OnsetAfterRest', [], {}),
        ('learning.piano.algorithm.PitchClassStatistics', [], {}),
        ('learning.piano.algorithm.RhythmVariety', [], {}),
        ('learning.piano.algorithm.StrongBeats', [], {'division': 0.5}),
        ('learning.piano.algorithm.SustainedRhythm', [], {}),
        ('learning.piano.algorithm.VerticalDoubling', [], {}),
        ('learning.piano.algorithm.Motif', [], {}),
        ('learning.piano.algorithm.Harmony', [], {}),
        ],
    'alignment': ('learning.piano.min_octave_hand.AlignMinOctaveHand', [], {}),
    }


Model = MultinomialLogistic


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

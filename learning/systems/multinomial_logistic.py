import functools
from ..system import PianoReductionSystem
from ..piano.pre_processor import StructuralPreProcessor
from ..piano import algorithm, alignment
from ..models.sk import WrappedSklearnModel
from sklearn.linear_model import LogisticRegression


class MultinomialLogistic(WrappedSklearnModel):
    def __init__(self, *args, **kwargs):
        Model = functools.partial(
            LogisticRegression, multi_class='multinomial', solver='sag',
            max_iter=5000)
        super().__init__(Model, *args, **kwargs)


system = PianoReductionSystem(
    name='multinomial_logistic',
    pre_processor=StructuralPreProcessor(
        algorithms=[
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
        alignment=alignment.AlignMinOctaveHand(),
        ),
    Model=MultinomialLogistic,
    )


if __name__ == '__main__':
    system.run_cli()

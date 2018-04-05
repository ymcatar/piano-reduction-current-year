import functools
from ..system import PianoReductionSystem
from ..piano.pre_processor import StructuralPreProcessor
from ..piano import algorithm, alignment
from ..models.sk import WrappedSklearnModel
from sklearn.naive_bayes import GaussianNB

class NaiveBayes(WrappedSklearnModel):
    def __init__(self, *args, **kwargs):
        Model = functools.partial(GaussianNB)
        super().__init__(Model, *args, **kwargs)


system = PianoReductionSystem(
    name='naive_bayes',
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
    Model=NaiveBayes,
    )


if __name__ == '__main__':
    system.run_cli()

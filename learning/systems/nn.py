from ..system import PianoReductionSystem
from ..piano.pre_processor import StructuralPreProcessor
from ..piano import algorithm, alignment
from ..models.nn import NN


system = PianoReductionSystem(
    name='nn',
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
        alignment=alignment.AlignPitchClassOnset(),
        ),
    Model=NN,
    )


if __name__ == '__main__':
    system.run_cli()

from ..system import PianoReductionSystem
from ..piano.pre_processor import StructuralPreProcessor
from ..piano import algorithm, alignment, contraction, structure
from ..models.pystruct_crf import PyStructCRF


system = PianoReductionSystem(
    name='pairwise_crf',
    pre_processor=StructuralPreProcessor(
        algorithms=[
            algorithm.ActiveRhythm(),
            algorithm.BassLine(),
            algorithm.OnsetAfterRest(),
            algorithm.RhythmVariety(),
            algorithm.SustainedRhythm(),
            algorithm.VerticalDoubling(),
            algorithm.Motif(),
            algorithm.Harmony(sub_keys=('base', '3rd', '5th', 'dissonance')),
            algorithm.OutputCountEstimate(),
            algorithm.HighestPitchInRhythm(),
            ],
        alignment=alignment.AlignMinOctaveMatching(),
        contractions=[
            contraction.ContractTies(),
            contraction.ContractByPitchOnset(),
            ],
        structures=[
            structure.OnsetNotes(),
            structure.OnsetBadIntervalNotes(),
            structure.OnsetDurationVaryingNotes(),
            structure.AdjacentNotes(),
            ],
        ),
    Model=PyStructCRF,
    )


if __name__ == '__main__':
    system.run_cli()

from ..system import PianoReductionSystem
from ..piano.onset_chain import OnsetChainPreProcessor, OnsetChainModel
from ..piano import algorithm, alignment, contraction


system = PianoReductionSystem(
    name='onset_chain',
    pre_processor=OnsetChainPreProcessor(
        algorithms=[
            algorithm.ActiveRhythm(),
            algorithm.BassLine(),
            algorithm.OnsetAfterRest(),
            algorithm.RhythmVariety(),
            algorithm.SustainedRhythm(),
            algorithm.VerticalDoubling(),
            algorithm.Motif(),
            algorithm.Harmony(sub_keys=('base', '3rd', '5th', 'dissonance')),
            algorithm.HighestPitchInRhythm(),
            ],
        alignment=alignment.AlignMinOctaveMatching(use_hand=False),
        contractions=[
            contraction.ContractTies(),
            contraction.ContractByPitchOnset(),
            ],
        ),
    Model=OnsetChainModel,
    )


if __name__ == '__main__':
    system.run_cli()

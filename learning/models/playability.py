from ..piano import algorithm, alignment, contraction, structure
from .pystruct_crf import PyStructCRF


reducer_args = {
    'algorithms': [
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
    'alignment': alignment.AlignMinOctaveMatching(),
    'contractions': [
        contraction.ContractTies(),
        contraction.ContractByPitchOnset(),
        ],
    'structures': [
        structure.OnsetNotes(),
        structure.OnsetBadIntervalNotes(),
        structure.OnsetDurationVaryingNotes(),
        structure.AdjacentNotes(),
        ],
    }

Model = PyStructCRF


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

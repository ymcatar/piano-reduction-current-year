from ..piano import algorithm, alignment, contraction, structure
from .pystruct_crf import PyStructCRF


reducer_args = {
    'algorithms': [
        algorithm.ActiveRhythm(),
        algorithm.BassLine(),
        algorithm.Occurrence(),
        algorithm.OnsetAfterRest(),
        algorithm.RhythmVariety(),
        algorithm.StrongBeats(division=1.0),
        algorithm.SustainedRhythm(),
        algorithm.VerticalDoubling(),
        algorithm.Motif(),
        algorithm.Harmony(),
        algorithm.OutputCountEstimate(),
        ],
    'alignment': alignment.AlignMinOctaveMatching(),
    'contractions': [
        contraction.ContractTies(),
        contraction.ContractByPitchOnset(),
        ],
    'structures': [
        structure.OnsetNotes(),
        structure.OnsetBadIntervalNotes(),
        structure.AdjacentNotes(),
        ],
    }

Model = PyStructCRF


if __name__ == '__main__':
    import sys
    from ..cli import run_model_cli

    run_model_cli(sys.modules[__name__])

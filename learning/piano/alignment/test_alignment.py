from music21 import converter
from ..algorithm.base import iter_notes
from .alignment import align_all_notes


def test_align_all_notes():
    # In the samples, black notes have no correponding notes; colored notes
    # correspond to each other.

    # Measure 1: Test matching chord notes
    # Measure 2: Test matching across voices
    # Measure 3: Test grace notes are matched
    # Measure 4: Test pitch space mismatch
    # Measure 5: Test slightly different durations are not matched
    scores = [
        converter.parse('learning/piano/test_sample/alignment_a.xml'),
        converter.parse('learning/piano/test_sample/alignment_b.xml'),
        ]

    alignments = [align_all_notes(scores[0], scores[1])]
    alignments.append(alignments[0].reverse)

    for score, alignment in zip(scores, alignments):
        for i, n in enumerate(iter_notes(score.flat)):
            color = n.style.color or '#000000'
            if color == '#000000':
                assert alignment[n] == []
            else:
                assert len(alignment[n]) == 1
                other_color = alignment[n][0].style.color or '#000000'
                assert other_color == color

        assert i + 1 >= 10  # Make sure we are checking something

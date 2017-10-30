from .score import ScoreObject
from music21 import interval, pitch


def test_instrument_transposition():
    s = ScoreObject.from_file(
        'learning/piano/test_sample/score_instrument_transposition.xml')
    score = s.score

    written_to_sounding = {
        'Clarinets in B♭': interval.Interval('-M2'),
        'Horns in F': interval.Interval('-P5'),
        'Trumpets in B♭': interval.Interval('-M2'),
        'Contrabasses': interval.Interval('-P8'),
        }

    for name, int_ in written_to_sounding.items():
        expected = pitch.Pitch('C4').transpose(int_)

        # Horns in F has 2 parts
        parts = [p for p in score.parts
                 if p.getElementsByClass('Instrument')[0].partName == name]
        assert parts
        for part in parts:
            assert part.recurse(skipSelf=False).notes[0].pitch == expected, \
                'Transposition incorrect for ' + name

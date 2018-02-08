from .score import ScoreObject
from .structure import SimultaneousNotes


def test_simulateneous_notes():
    s = ScoreObject.from_file('learning/piano/test_sample/algorithm_input_small.xml')
    structure = dict(SimultaneousNotes().run(s))
    assert set(tuple(sorted(i)) for i in structure.keys()) == {
        (0, 9),
        (0, 15),
        (9, 15),

        (1, 9),
        (1, 15),
        (9, 15),

        (2, 15),
        (3, 15),

        (4, 10),
        (5, 11),
        (6, 12),
        (7, 13),

        (8, 14),
        (8, 16),
        (14, 16),

        (8, 14),
        (8, 17),
        (14, 17),
        }

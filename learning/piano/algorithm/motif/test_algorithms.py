import music21

from .algorithms import MotifAnalyzerAlgorithms


def score_to_note_list(score):
    return [i for i in score.recurse().getElementsByClass(('Note', 'Rest'))]


def test_note_sequence_func():

    case1 = music21.converter.parse('tinyNotation: 4/4 C4 D8 E16 F2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.note_sequence_func(case1) == ['C', 'D', 'E', 'F']

    case2 = music21.converter.parse('tinyNotation: 4/4 C4 r8 r8 F2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.note_sequence_func(case2) == ['C', 'R', 'F']

    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D8~ D8 F2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.note_sequence_func(case3) == ['C', 'D', 'F']

def test_notename_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 F#2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.notename_sequence_func(case1) == ['C', 'D', 'E', 'F']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.notename_sequence_func(case2) == ['C', 'R', 'F']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D-8~ D-8 F-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.notename_sequence_func(case3) == ['C', 'D', 'F']

def test_rhythm_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 F#2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.rhythm_sequence_func(case1) == ['1.0', '0.5', '0.2', '1.0']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.rhythm_sequence_func(case2) == ['1.0', '1.0', '1.0']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D-8~ D-8 F-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.rhythm_sequence_func(case3) == ['1.0', '1.0', '1.0']

def test_notename_transition_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 F#2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.notename_transition_sequence_func(case1) == ['1', '1', '1']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.notename_transition_sequence_func(case2) == ['NR', 'RN']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D-8~ D-8 F-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.notename_transition_sequence_func(case3) == ['1', '2']

def test_note_contour_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 a2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.note_contour_sequence_func(case1) == ['=', '<', '<']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.note_contour_sequence_func(case2) == ['NR', 'RN']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D-8~ D-8 B-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.note_contour_sequence_func(case3) == ['<', '>']

def test_note_transition_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 G2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.note_transition_sequence_func(case1) == ['0.0', '3.0', '3.0']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.note_transition_sequence_func(case2) == ['NR', 'RN']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 d-8~ d-8 B-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.note_transition_sequence_func(case3) == ['13.0', '-3.0']


def test_rhythm_transition_sequence_func():
    # typical case
    case1 = music21.converter.parse('tinyNotation: 4/4 C#4 D-8 E16 G2')
    case1 = score_to_note_list(case1)
    assert MotifAnalyzerAlgorithms.rhythm_transition_sequence_func(case1) == ['0.5', '0.5', '4.0']
    # merging rests
    case2 = music21.converter.parse('tinyNotation: 4/4 C#4 r8 r8 F#2')
    case2 = score_to_note_list(case2)
    assert MotifAnalyzerAlgorithms.rhythm_transition_sequence_func(case2) == ['1.0', '1.0']
    # merging across tie
    case3 = music21.converter.parse('tinyNotation: 4/4 C4 D-8~ D-8 B-2')
    case3 = score_to_note_list(case3)
    assert MotifAnalyzerAlgorithms.rhythm_transition_sequence_func(case3) == ['1.0', '1.0']

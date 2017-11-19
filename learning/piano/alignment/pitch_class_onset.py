import textwrap
from ..algorithm.base import iter_notes
from .alignment import align_all_notes


def pitch_class_onset_key_func(n, offset, precision):
    # On making matches, only consider offset and pitch class, but not
    # duration and octave
    return (int(offset * precision), n.pitch.pitchClass)


def same_duration(n, m, precision=1024):
    return int(n.duration.quarterLength * precision) == \
        int(m.duration.quarterLength * precision)


def same_pitch(n, m):
    return n.pitch == m.pitch


def align_pitch_class_onset(input_score, output_score):
    '''
    Match notes using pitch class and onset values only, ignoring duration and
    octave.
    '''
    alignment = align_all_notes(input_score, output_score, ignore_parts=True,
                                key_func=pitch_class_onset_key_func)

    for n in iter_notes(input_score, recurse=True):
        if any(same_duration(i, n) and same_pitch(i, n)
               for i in alignment[n]):
            align_type = 'all'
        elif any(same_pitch(i, n) for i in alignment[n]):
            align_type = 'pitch space'
        elif alignment[n]:
            align_type = 'pitch class'
        else:
            align_type = None
        n.editorial.misc['align_type'] = align_type
        n.editorial.misc['align'] = bool(align_type)
    return input_score

align_pitch_class_onset.label_type = 'align'


def annotate_pitch_class_onset(input_score, output_score):
    align_pitch_class_onset(input_score, output_score)
    align_pitch_class_onset(output_score, input_score)

    FORWARD_COLORS = {
        'all': '#0000FF',
        'pitch space': '#0099FF',
        'pitch class': '#00CCFF'
    }
    for n in iter_notes(input_score, recurse=True):
        n.style.color = FORWARD_COLORS.get(n.editorial.misc['align_type'],
                                           '#000000')
    BACKWARD_COLORS = {
        'all': '#000000',
        'pitch space': '#FF9900',
        'pitch class': '#EEEE00'
    }
    for n in iter_notes(output_score, recurse=True):
        n.style.color = BACKWARD_COLORS.get(n.editorial.misc['align_type'],
                                            '#FF0000')

    description = textwrap.dedent('''\
        [Original]
        Blue = Used directly
        Cyan = Used with octave transposition
        Light blue  = Used with duration change

        [Reduced]
        Black = Kept directly
        Yellow = Kept with octave transposition
        Orange = Kept with duration change
        Red = Fabricated by arranger
        ''')

    return description

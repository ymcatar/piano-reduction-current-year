from .alignment import align_all_notes
from .base import AlignmentMethod
from scoreboard import writer


def pitch_class_onset_key_func(n, offset, precision):
    # On making matches, only consider offset and pitch class, but not
    # duration and octave
    return (int(offset * precision), n.pitch.pitchClass)


def same_duration(n, m, precision=1024):
    return int(n.duration.quarterLength * precision) == \
        int(m.duration.quarterLength * precision)


def same_pitch(n, m):
    return n.pitch == m.pitch


class AlignPitchClassOnset(AlignmentMethod):
    all_keys = ['align_type', 'rev_align_type', 'align']
    key = 'align'

    def run(self, input_score_obj, output_score_obj, extra=False):
        '''
        Match notes using pitch class and onset values only, ignoring duration
        and octave.
        '''

        input_score = input_score_obj.score
        output_score = output_score_obj.score
        alignment = align_all_notes(input_score, output_score, ignore_parts=True,
                                    key_func=pitch_class_onset_key_func)

        for n in input_score_obj:
            if any(same_duration(i, n) and same_pitch(i, n)
                   for i in alignment[n]):
                align_type = 'all'
            elif any(same_pitch(i, n) for i in alignment[n]):
                align_type = 'pitch class'
            elif alignment[n]:
                align_type = 'pitch space'
            else:
                align_type = None
            n.editorial.misc['align_type'] = align_type
            n.editorial.misc['align'] = bool(align_type)

        if extra:
            self.run(output_score_obj, input_score_obj, extra=False)
            for n in output_score_obj:
                n.editorial.misc['rev_align_type'] = \
                    n.editorial.misc['align_type'] or 'fabricated'
                del n.editorial.misc['align_type']
                del n.editorial.misc['align']

    features = [
        writer.CategoricalFeature(
            'align_type',
            {
                'all': ('#0000FF', 'Used directly'),
                'pitch space': ('#0099FF', 'Used with octave transposition'),
                'pitch class': ('#00CCFF', 'Used with duration change'),
                'discarded': ('#000000', 'Discarded'),
                },
            '#000000',
            help='How the note is kept',
            group='alignment'
            ),
        writer.CategoricalFeature(
            'rev_align_type',
            {
                'all': ('#000000', 'Kept directly'),
                'pitch space': ('#FF9900', 'Kept with octave transposition'),
                'pitch class': ('#EEEE00', 'Kept with duration change'),
                'fabricated': ('#FF0000', 'Fabricated by arranger'),
                },
            '#000000',
            help='Where the note comes from',
            group='alignment'
            ),
        ]

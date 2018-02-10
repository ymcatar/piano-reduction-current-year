from .alignment import align_all_notes
from .base import AlignmentMethod
from scoreboard import writer


def pitch_onset_key_func(n, offset, precision):
    # On making matches, only consider offset and pitch, but not duration
    return (int(offset * precision), n.pitch.ps)


class AlignDifference(AlignmentMethod):
    all_keys = ['extra', 'missing']
    key = 'missing'

    def run(self, input_score_obj, output_score_obj, extra=False):
        '''
        A direct diff'ing of two scores, except that durations are not
        considered.

        Should be used for visualization only.
        '''

        input_score = input_score_obj.score
        output_score = output_score_obj.score
        alignment = align_all_notes(input_score, output_score,
                                    key_func=pitch_onset_key_func)

        for n in input_score_obj:
            n.editorial.misc['difference'] = '-' if not alignment[n] else ''

        if extra:
            alignment = align_all_notes(output_score, input_score,
                                        key_func=pitch_onset_key_func)
            for n in output_score_obj:
                n.editorial.misc['difference'] = '+' if not alignment[n] else ''

    features = [
        writer.CategoricalFeature(
            'difference',
            {
                '-': ('#FF0000', 'Missing'),
                '+': ('#33FF33', 'Extra'),
                '': ('#000000', 'Match'),
                },
            '#000000',
            help='Difference bewteen sample and generated scores',
            group='alignment'),
        ]

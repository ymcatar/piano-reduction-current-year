from ..algorithm.base import iter_notes_with_offset
from .base import AlignmentMethod

from collections import defaultdict
import numpy as np
import scipy.optimize

from scoreboard import writer


class AlignMinOctaveMatching(AlignmentMethod):
    all_keys = ['justified', 'hand']
    key = 'hand'

    def run(self, input_score_obj, output_score_obj, extra=False):
        '''
        Assign hands by formulating a min-weight matching on pitches. The cost
        of aligning two pitches is given by square of their octave difference.

        Note that pitch matches are one-to-one, but a pitch may be shared by
        multiple notes in the input score.
        '''
        assert len(output_score_obj.score.parts) == 2, \
            'Output score does not have exactly 2 parts!'

        for n in input_score_obj.notes:
            n.editorial.misc['hand'] = 0
        for n in output_score_obj.notes:
            n.editorial.misc['justified'] = False

        for in_bar, out_bar in zip(input_score_obj.by_bar, output_score_obj.by_bar):
            # For each offset and pitch, index notes by octaves
            in_note_map = defaultdict(lambda: defaultdict(list))
            for n, offset in iter_notes_with_offset(in_bar, recurse=True):
                in_note_map[(offset, n.pitch.name)][int(n.pitch.ps) // 12].append(n)

            out_note_map = defaultdict(lambda: defaultdict(list))
            for part_idx, part in enumerate(out_bar.parts):
                for n, offset in iter_notes_with_offset(part, recurse=True):
                    out_note_map[(offset, n.pitch.name)][int(n.pitch.ps) // 12] \
                        .append((n, part_idx + 1))

            for (offset, pitch_name), out_notes in out_note_map.items():
                in_notes = in_note_map[(offset, pitch_name)]
                if not in_notes:
                    continue

                in_octaves = np.asarray(list(in_notes.keys()))
                out_octaves = np.asarray(list(out_notes.keys()))

                C = np.abs(out_octaves[:, np.newaxis] - in_octaves[np.newaxis, :])
                C **= 2

                out_ind, in_ind = scipy.optimize.linear_sum_assignment(C)

                for out_i, in_i in zip(out_ind, in_ind):
                    in_octave = in_octaves[in_i]
                    out_octave = out_octaves[out_i]

                    out_part = out_notes[out_octave][0][1]

                    for n, _ in out_notes[out_octave]:
                        n.editorial.misc['justified'] = True
                    for n in in_notes[in_octave]:
                        n.editorial.misc['hand'] = out_part

    features = [
        writer.CategoricalFeature(
            'hand',
            {
                0: ('#000000', 'Discarded'),
                1: ('#3333FF', 'Upper staff'),
                2: ('#33FF33', 'Lower staff'),
                },
            '#000000',
            help='Which staff the note is kept in, determined with MinOctaveMatching.',
            group='alignment'
            ),
        writer.CategoricalFeature(
            'justified',
            {
                'true': ('#000000', 'Justified'),
                'false': ('#FF0000', 'Unjustified'),
                },
            '#000000',
            help='Which the output note is justified by some input note label.',
            group='alignment'
            ),
        ]

from ..algorithm.base import iter_notes
from .pitch_class_onset import pitch_class_onset_key_func
from .alignment import align_all_notes
from .base import AlignmentMethod

from collections import Counter
from music21 import stream

from scoreboard import writer


RIGHT_HAND = 1
LEFT_HAND = 2


class AlignMinOctaveHand(AlignmentMethod):
    all_keys = ['feasible hands', 'justified', 'hand']
    key = 'hand'

    def run(self, input_score_obj, output_score_obj, extra=False):
        '''
        Assign hands using the following precedence rules:

        1.  Choose the one with the least octave-transposed note.
        2.  Choose the one feasible for the most notes in the same voice-measure.
        3.  Choose the right hand.
        '''
        HANDS = [RIGHT_HAND, LEFT_HAND]

        input_score = input_score_obj.score
        output_score = output_score_obj.score

        assert len(output_score.parts) == 2, \
            'Output score does not have exactly 2 parts!'

        output_part_scores = []
        alignments = []
        for part in output_score.parts:
            part_score = output_score.cloneEmpty('extract_part')
            part_score.insert(0, part)
            output_part_scores.append(part_score)
            alignments.append(
                align_all_notes(input_score, part_score, ignore_parts=True,
                                key_func=pitch_class_onset_key_func))

        for n in iter_notes(output_score, recurse=True):
            n.editorial.misc['justified'] = False

        for measure in (input_score.recurse(skipSelf=True)
                .getElementsByClass(stream.Measure)):
            for voice in measure.voices or [measure]:
                votes = Counter()
                for n in iter_notes(voice):
                    feasible_map = {}
                    for alignment, hand in zip(alignments, HANDS):
                        if alignment[n]:
                            feasible_map[hand] = min(
                                abs(i.pitch.octave - n.pitch.octave)
                                for i in alignment[n])

                    feasible_hands = list(feasible_map.keys())
                    n.editorial.misc['feasible_hands'] = feasible_hands
                    n.editorial.misc['align'] = bool(feasible_hands)

                    optimal_value = (
                        min(feasible_map.values()) if feasible_map else None)
                    optimal_hands = [k for k, v in feasible_map.items()
                                     if v == optimal_value]
                    if not optimal_hands:
                        n.editorial.misc['hand'] = 0
                    elif len(optimal_hands) == 1:
                        n.editorial.misc['hand'] = optimal_hands[0]
                        for i in alignments[HANDS.index(optimal_hands[0])][n]:
                            i.editorial.misc['justified'] = True
                    else:
                        # Will be assigned later by majority vote
                        pass

                    votes.update(feasible_hands)

                if votes[RIGHT_HAND] == votes[LEFT_HAND]:
                    votes[RIGHT_HAND] += 1

                majority_hand = max(votes, key=votes.get)

                for n in iter_notes(voice):
                    misc = n.editorial.misc
                    if 'hand' not in misc:
                        misc['hand'] = majority_hand
                        for i in alignments[HANDS.index(majority_hand)][n]:
                            i.editorial.misc['justified'] = True

    features = [
        writer.CategoricalFeature(
            'hand',
            {
                0: ('#000000', 'Discarded'),
                1: ('#3333FF', 'Upper staff'),
                2: ('#33FF33', 'Lower staff'),
                },
            '#000000',
            help='Which staff the note is kept in, determined with MinOctaveHand.',
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

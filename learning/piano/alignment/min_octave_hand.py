from ..algorithm.base import iter_notes
from .pitch_class_onset import pitch_class_onset_key_func
from .alignment import align_all_notes

from collections import Counter
import textwrap
from music21 import stream


RIGHT_HAND = 1
LEFT_HAND = 2


def align_min_octave_hand(input_score, output_score):
    '''
    Assign hands using the following precedence rules:

    1.  Choose the one with the least octave-transposed note.
    2.  Choose the one feasible for the most notes in the same voice-measure.
    3.  Choose the right hand.
    '''
    HANDS = [RIGHT_HAND, LEFT_HAND]

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

    return input_score


def annotate_min_octave_hand(input_score, output_score):
    align_min_octave_hand(input_score, output_score)
    rev = align_all_notes(output_score, input_score, ignore_parts=True,
                          key_func=pitch_class_onset_key_func)

    FORWARD_COLORS = {
        LEFT_HAND: '#009900',
        RIGHT_HAND: '#0000FF'
        }
    for n in iter_notes(input_score, recurse=True):
        n.style.color = FORWARD_COLORS.get(n.editorial.misc['hand'],
                                           '#000000')
        if len(n.editorial.misc['feasible_hands']) == 2:
            n.lyric = '*'

    for n in iter_notes(output_score, recurse=True):
        if n.editorial.misc.get('justified', False):
            n.style.color = '#000000'
        elif rev[n]:
            n.style.color = '#9900FF'
        else:
            n.style.color = '#FF0000'

    description = textwrap.dedent('''\
        [Original]
        Blue = Right hand
        Green = Left hand
        * = Both hands feasible

        [Reduced]
        Red = Unjustified by colouring and impossible
        Purple = Unjustified by colouring but possible
        ''')

    return description

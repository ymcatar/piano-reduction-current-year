from ..algorithm.base import iter_notes, iter_notes_with_offset

from collections import defaultdict
from music21 import stream


class Alignment:
    '''
    A dict-like object that allows looking up the corresponding notes. By
    default, this looks up the corresponding right note given the left note.

        alignment[left note] = list of right notes

        alignment.reverse[right note] = list of left notes
    '''
    def __init__(self, left_lookup, right_lookup, reverse=None):
        self.left_lookup = left_lookup
        self.right_lookup = right_lookup

        self.reverse = (reverse if reverse is not None else
                        Alignment(right_lookup, left_lookup, reverse=self))

    def __getitem__(self, key):
        return self.left_lookup[id(key)]

    def __len__(self):
        return len(self.left_lookup)

    def __repr__(self):
        return '<%s at %#x>' % (type(self).__name__, id(self))

    def get(self, key, default=None):
        return self.left_lookup.get(id(key, default))

    def __contains__(self, key):
        return id(key) in self.left_lookup


def default_key_func(n, offset, precision):
    return (int(offset * precision),
            int(n.duration.quarterLength * precision),
            n.pitch.ps)


def align_all_notes(left_score, right_score, precision=1024,
                    key_func=default_key_func, ignore_parts=False):
    '''
    Aligns each note in the left score with the corresponding note in the
    right score, if any.

    left_score, right_score: The input Score objects. It is required that each
        Note object inside the Score be unique (only appears once).
    precision: Offset and duration values are quantized to the nearest
        1/precision quarter length.

    Returns: an Alignment object.
    '''

    # index[part index][measure index][key] = list(notes)
    # where key is determined by key_Func
    scores = [left_score, right_score]
    indices = [defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
               for _ in range(2)]

    # Build the Note object index
    for score, index in zip(scores, indices):
        for i, part in enumerate(score.parts):
            if ignore_parts:
                i = 0
            # Note that we explicitly don't care whether the notes are in the
            # corresponding voice, but only the corresponding score. This is
            # because putting the note in a different voice still gives a
            # similarly looking score -- so the voice number is not informative.
            for mi, measure in enumerate(part.getElementsByClass(stream.Measure)):
                # Recurse on voices
                for n, offset in iter_notes_with_offset(measure, recurse=True):
                    key = key_func(n, offset, precision)
                    index[i][mi][key].append(n)

    # For each score, look up the other Note object index
    lookups = [{} for _ in range(2)]
    for score, other_index, lookup in zip(scores, reversed(indices), lookups):
        for i, part in enumerate(score.parts):
            if ignore_parts:
                i = 0
            for mi, measure in enumerate(part.getElementsByClass(stream.Measure)):
                # Recurse on voices
                for n, offset in iter_notes_with_offset(measure, recurse=True):
                    key = key_func(n, offset, precision)
                    assert id(n) not in lookups, 'Note object not unique!'
                    lookup[id(n)] = other_index[i][mi][key]

    return Alignment(*lookups)



from collections import defaultdict
import math
from music21 import chord, note, stream
from .algorithm.base import iter_notes_with_offset


class StructureAlgorithm:
    '''
    Base class for a feature constructor involving 2 notes.

    The corresponding potential function is given by

        phi(y_C) = exp(weight^T * feature(y_C))

    where y_C is the edge.
    '''
    def __init__(self):
        # The *args and **kwargs that can be used to reconstruct this algorithm
        self.args = [], {}

    @property
    def n_features():
        raise NotImplementedError()

    def run(self, score_obj):
        '''
        Returns an iterator of (edge, features), where
        -   `edge` is a pair with the indices of the two endpoints, and
        -   `features` is a length-n_features vector with the edge features.
        '''
        raise NotImplementedError()

    def get_weights(self, label_type, var_fn):
        '''
        Returns a weight variable matrix, where entries are "variables" created
        using `var_fn`.

        Entries with the same value will be tied.
        '''
        if label_type == 'align':
            n_dims = 2
        elif label_type == 'hand':
            n_dims = 3
        else:
            raise NotImplementedError()

        return [[var_fn() for _ in range(n_dims)] for _ in range(n_dims)]

    @property
    def key(self):
        return type(self).__name__


def get_repelling_weights(self, label_type, var_fn, use_different=True):
    nothing = var_fn('no_effect')
    same = var_fn('same')

    if label_type == 'align':
        return [
            [nothing, nothing],
            [nothing, same],
            ]
    elif label_type == 'hand':
        different = var_fn('different') if use_different else nothing
        return [
            [nothing, nothing, nothing],
            [nothing, same, different],
            [nothing, different, same],
            ]
    else:
        raise NotImplementedError()


def get_hand_only_repelling_weights(self, label_type, var_fn):
    return get_repelling_weights(self, label_type, var_fn, use_different=False)


class SimultaneousNotes(StructureAlgorithm):
    '''
    Connects notes that occur simultaneously.
    '''
    n_features = 1

    def run(self, score_obj):
        for bar in score_obj.by_bar:
            begins_by_offset = defaultdict(set)
            ends_by_offset = defaultdict(set)
            for n, offset in iter_notes_with_offset(bar, recurse=True):
                begins_by_offset[offset].add(score_obj.index(n))
                ends_by_offset[offset + n.duration.quarterLength].add(score_obj.index(n))

            offsets = set(begins_by_offset.keys())
            offsets.update(ends_by_offset.keys())
            offsets = sorted(offsets)

            active_notes = set()
            for offset in offsets:
                for n in ends_by_offset[offset]:
                    for i in active_notes:
                        if i != n:
                            # Some edges may be duplicated, but this is fine
                            yield (n, i), (1,)

                active_notes -= ends_by_offset[offset]
                active_notes.update(begins_by_offset[offset])

    get_weights = get_repelling_weights


class OnsetNotes(StructureAlgorithm):
    '''
    Connects notes at the same onset.
    '''
    n_features = 1

    def run(self, score_obj):
        for offset, notes in score_obj.iter_offsets():
            for u in notes:
                for v in notes:
                    if u != v:
                        yield (score_obj.index(u), score_obj.index(v)), (1,)

    get_weights = get_repelling_weights


class OnsetBadIntervalNotes(StructureAlgorithm):
    '''
    Connects notes at the same onset with "bad" intervals.
    '''
    n_features = 1

    def run(self, score_obj):
        BAD_INTERVALS = (1, 2, 6, 10, 11)

        for offset, notes in score_obj.iter_offsets():
            for u in notes:
                for v in notes:
                    if (u != v and (int(u.pitch.ps) - int(v.pitch.ps) + 12) % 12 in BAD_INTERVALS):
                        yield (score_obj.index(u), score_obj.index(v)), (1,)

    get_weights = get_repelling_weights


class OnsetDurationVaryingNotes(StructureAlgorithm):
    '''
    Connects notes at the same onset with different durations.
    '''
    n_features = 1

    def run(self, score_obj):
        for offset, notes in score_obj.iter_offsets():
            for u in notes:
                for v in notes:
                    if (u != v and u.duration.quarterLength != v.duration.quarterLength):
                        d1, d2 = sorted((u.duration.quarterLength, v.duration.quarterLength))
                        if d1 == 0.0:  # e.g. grace note
                            continue
                        log_ratio = math.log2(d2/d1)
                        yield (score_obj.index(u), score_obj.index(v)), (log_ratio,)

    get_weights = get_repelling_weights


class AdjacentNotes(StructureAlgorithm):
    '''
    Connects notes that occur one after another.
    '''
    n_features = 3

    def run(self, score_obj):
        for voices in score_obj.voices_by_part:
            last_notes = []
            for voice in voices:
                for measure in voice.getElementsByClass(stream.Measure):
                    for n in measure.notesAndRests:
                        if isinstance(n, note.Rest):
                            last_notes = []
                        elif isinstance(n, note.NotRest):
                            if isinstance(n, chord.Chord):
                                notes = list(n)
                                notes.sort(key=lambda n: -n.pitch.ps)
                            else:
                                notes = [n]

                            # Heuristic: Top-pitch note is linked to
                            # top-pitch note, etc.
                            for u, v in zip(notes, last_notes):
                                if v.duration.quarterLength == 0.0:  # Grace note
                                    continue
                                log_d = math.log2(v.duration.quarterLength)
                                yield (score_obj.index(u), score_obj.index(v)), (1, log_d, log_d**2,)

                            last_notes = notes

    def get_weights(self, *args, **kwargs):
        return [get_hand_only_repelling_weights(self, *args, **kwargs) for _ in range(3)]

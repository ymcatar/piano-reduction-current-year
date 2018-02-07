from collections import defaultdict
from .algorithm.base import iter_notes_with_offset


class StructureAlgorithm:
    '''
    Base class for a feature constructor involving 2 notes.

    The corresponding potential function is given by

        phi(y_C) = exp(weight^T * feature(y_C))

    where y_C is the edge.
    '''

    @property
    def n_features():
        raise NotImplementedError()

    def create(self, score_obj):
        '''
        Returns an iterator of (edge, features), where
        -   `edge` is a pair with the indices of the two endpoints, and
        -   `features` is a length-n_features vector with the edge features.
        '''
        raise NotImplementedError()

    @property
    def args(self):
        return ([], {})


class SimultaneousNotes(StructureAlgorithm):
    '''
    Connects notes that occur simultaneously.
    '''
    n_features = 1

    def create(self, score_obj):
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

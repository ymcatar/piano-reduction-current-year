from .base import BaseEdgeAlgorithm, iter_notes_with_offset
from collections import defaultdict
import numpy as np


class SimultaneousNotes(BaseEdgeAlgorithm):
    '''
    Edge feature for two notes occurring simultaneously.
    '''
    n_features = 1

    def create_features(self, score_obj):
        for bar in score_obj.by_bar:
            begins_by_offset = defaultdict(set)
            ends_by_offset = defaultdict(set)
            for n, offset in iter_notes_with_offset(bar, recurse=True):
                begins_by_offset[offset].append(n.id)
                ends_by_offset[offset + n.duration.quarterLength].append(n.id)

            offsets = sorted(
                set(begins_by_offset.keys()) + set(ends_by_offset.keys()))

            active_notes = set()
            for offset in offsets:
                for n in ends_by_offset[offset]:
                    for i in active_notes:
                        yield (sorted(n, i), (1,))

                active_notes -= ends_by_offset[offset]
                active_notes += begins_by_offset[offset]

    def get_default_weight(self):
        weight = np.zeros((3, 3, 1))
        # TODO
        return weight

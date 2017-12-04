from .base import ReductionAlgorithm, get_markings, iter_notes_with_offset


class OffsetValue(ReductionAlgorithm):
    def __init__(self):
        super(OffsetValue, self).__init__()

    dtype = 'float'
    range = (0.0, None)

    def create_markings_on(self, score_obj):
        for n, offset in iter_notes_with_offset(score_obj._score, recurse=True):
            get_markings(n)[self.key] = offset

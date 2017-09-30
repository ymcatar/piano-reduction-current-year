from .base import ReductionAlgorithm, get_markings, iter_notes


class OffsetValue(ReductionAlgorithm):
    _type = 'offset'

    def __init__(self):
        super(OffsetValue, self).__init__()

    def create_markings_on(self, score_obj):
        for n in iter_notes(score_obj._score.recurse()):
            get_markings(n)[self.key] = n.offset

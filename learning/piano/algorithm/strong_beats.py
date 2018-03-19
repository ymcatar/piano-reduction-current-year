from .base import FeatureAlgorithm, get_markings, iter_notes_with_offset


class StrongBeats(FeatureAlgorithm):
    def __init__(self, division=1):
        super(StrongBeats, self).__init__()
        self.division = division  # in terms of quarter length

    dtype = 'bool'

    def run(self, score_obj):
        '''
        Each note whose onset occurs at an integral multiple of the defined
        division is marked.
        '''
        for n, offset in iter_notes_with_offset(score_obj._score, recurse=True):
            # Note that here, % is a flcf), recurse=Trueoating point operation
            get_markings(n)[self.key] = offset % self.division < 1e-3

    @property
    def args(self):
        return [], {'division': self.division}

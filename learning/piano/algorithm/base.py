from music21 import chord


class FeatureAlgorithm(object):
    '''
    Base class for a feature constructor involving a single note. Each feature
    constructor can create mulitple markings.
    '''

    def __init__(self):
        # To be determined by the reducer
        self.key_prefix = '!'

        # The *args and **kwargs that can be used to reconstruct this algorithm
        self.args = [], {}

    @property
    def all_keys(self):
        # Key(s) of the markings created by this algorithm
        return [self.key]

    @property
    def key(self):
        # Generate a default main key, for convenience
        return str(self.key_prefix) + '_' + str(type(self).__name__)

    def run(self, score_obj):
        raise NotImplementedError()


def get_markings(n):
    return n.editorial.misc


def set_marking_in_general_note(n, key, value):
    if isinstance(n, chord.Chord):
        for i in n:
            get_markings(i)[key] = value
    else:
        get_markings(n)[key] = value


# Deprecated. Please import from learning.piano.util
from ..util import iter_notes, iter_notes_with_offset

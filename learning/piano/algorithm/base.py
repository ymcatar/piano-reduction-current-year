from music21 import chord


class ReductionAlgorithm(object):
    '''
    Base class for a feature constructor involving a single note. Each feature
    constructor can create mulitple markings.
    '''

    def __init__(self):
        # To be determined by the reducer
        self.key_prefix = '!'

    @property
    def all_keys(self):
        # Key(s) of the markings created by this algorithm
        return [self.key]

    @property
    def key(self):
        # Generate a default main key, for convenience
        return str(self.key_prefix) + '_' + str(self.__class__.__name__)

    def create_markings_on(self, score_obj):
        raise NotImplementedError()


def get_markings(n):
    return n.editorial.misc.setdefault('markings', {})


def iter_notes(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes, including those
    inside a chord.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, chord.Chord):
            for n2 in n:
                yield n2
        else:
            yield n


def iter_notes_with_offset(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes with the offset
    value, including those inside a chord.

    Note that Notes inside a chord always have an offset value of 0.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, chord.Chord):
            for n2 in n:
                yield n2, n.offset
        else:
            yield n, n.offset


def set_marking_in_general_note(n, key, value):
    if isinstance(n, chord.Chord):
        for i in n:
            get_markings(i)[key] = value
    else:
        get_markings(n)[key] = value

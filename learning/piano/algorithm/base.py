from music21 import chord


class ReductionAlgorithm(object):
    '''
    Base class of all parameters, each contains a list of labels to allow
    multiple markings by one parameter
    '''

    _type = 'unknown'

    @property
    def type(self):
        return self.__class__._type

    @property
    def all_keys(self):
        return [self.key]

    @property
    def key(self):
        return str(self._key) + '_' + str(self.__class__._type)

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def parts(self):
        return self._parts

    def __init__(self):
        super(ReductionAlgorithm, self).__init__()
        self._key = '!'

    def createMarkingsOn(self, score):
        pass


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

import music21

# a method that wraps the notes object properly so note in chord can be properly deleted


class NoteWrapper(object):
    def __init__(self, note, offset, chord=None):

        self.note = note
        self.offset = offset
        self.chord = chord  # set to a chord if the note belongs to a chord

        if 'deleted' not in self.note.editorial.misc:
            self.deleted = False

        if 'hand' not in self.note.editorial.misc:
            self.hand = None

        if 'finger' not in self.note.editorial.misc:
            self.finger = None

    @property
    def is_from_chord(self):
        return self.chord is not None

    @property
    def deleted(self):
        return self.note.editorial.misc.get('deleted')

    @deleted.setter
    def deleted(self, value):
        assert value in (False, True)
        self.note.editorial.misc['deleted'] = value

    @property
    def hand(self):
        return self.note.editorial.misc['hand']

    @hand.setter
    def hand(self, value):
        assert value in ('L', 'R', None)
        self.note.editorial.misc['hand'] = value

    @property
    def finger(self):
        return self.note.editorial.misc['finger']

    @finger.setter
    def finger(self, value):
        assert value in (1, 2, 3, 4, 5, None)
        self.note.editorial.misc['finger'] = value

    def highlight(self, color):
        self.note.style.color = color

    def __repr__(self):
        state = 'DeletedNoteWrapper' if self.deleted else 'NoteWrapper'
        assignment = ' {:s}{:d}'.format(
            self.hand, self.finger) if self.hand and self.finger else ''
        return '<{:s} {:s}{:s}>'.format(state, self.note.nameWithOctave,
                                        assignment)

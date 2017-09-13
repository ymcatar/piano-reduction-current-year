from .not_rest import NotRest

import music21


class Note(NotRest, music21.note.Note):
    def __init__(self, ref):
        super(Note, self).__init__(ref)

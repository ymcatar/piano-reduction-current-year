import music21

# a method that wraps the notes object properly so note in chord can be properly deleted

class NoteWrapper(object):

    def __init__(self, note, offset, score, src_chord=None):

        self.note = note
        self.offset = offset
        self.score = score
        self.src_chord = src_chord
        self.deleted = False

    @property
    def is_from_chord(self):
        return self.src_chord is not None

    def highlight(self, color):
        self.note.style.color = color

    def remove(self):
        self.deleted = True

    def __repr__(self):
        return str(self.note)

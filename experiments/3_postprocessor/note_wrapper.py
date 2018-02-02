import music21

# a method that wraps the notes object properly so note in chord can be properly deleted

class NoteWrapper(object):

    def __init__(self, note, offset, score, src_chord=None):

        self.note = note
        self.offset = offset
        self.score = score
        self.src_chord = src_chord

        self.hand = None
        self.finger = None

    @property
    def is_from_chord(self):
        return self.src_chord is not None

    def highlight(self, color):
        self.note.style.color = color

    def remove(self):
        if self.is_from_chord:
            self.src_chord.remove(self.note)
        else:
            self.highlight('#00ff00')
            # how to delete a note properly?

    # hand = 'L' or 'R'
    # finger = [1, 5] => thumb, index, middle, ring, pinky
    def assign_finger(self, hand, finger):
        assert hand == 'L' or hand == 'R'
        assert finger in range(1, 6)

        self.hand = hand
        self.finger = finger

        if hand == 'L':
            if finger == 1:
                self.highlight('#e6194b') # red
            elif finger == 2:
                self.highlight('#3cb44b') # green
            elif finger == 3:
                self.highlight('#ffe119') # yellow
            elif finger == 4:
                self.highlight('#0082c8') # Blue
            elif finger == 5:
                self.highlight('#f58231') # orange
        else:
            if finger == 1:
                self.highlight('#911eb4') # purple
            elif finger == 2:
                self.highlight('#46f0f0') # cyan
            elif finger == 3:
                self.highlight('#f032e6') # magenta
            elif finger == 4:
                self.highlight('#d2f53c') # lime
            elif finger == 5:
                self.highlight('#fabebe') # pink

    def __repr__(self):
        return str(self.note)
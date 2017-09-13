from .general_note import GeneralNote

import music21


class NotRest(GeneralNote, music21.note.NotRest):
    def __init__(self, ref):
        super(NotRest, self).__init__(ref)
        self.tie_previous = None

    @property
    def align(self):
        if self.tie_previous is not None:
            return self.tie_previous.align
        return self._align

    @align.setter
    def align(self, align):
        if self.tie_previous is None:
            self._align = align

from .general_note import GeneralNote

import music21

class Rest(GeneralNote, music21.note.Rest):
    def __init__(self, ref):
        if isinstance(ref, music21.note.NotRest):
            rest = music21.note.Rest()
            rest.duration = ref.duration
            rest.quarterLength = ref.quarterLength
            rest.offset = ref.offset
            super(Rest, self).__init__(rest)
        else:
            super(Rest, self).__init__(ref)
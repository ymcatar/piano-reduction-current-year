from .base import ReductionAlgorithm, set_marking_in_general_note

from music21 import stream, note


class OnsetAfterRest(ReductionAlgorithm):
    _type = 'onset'

    def __init__(self):
        super(OnsetAfterRest, self).__init__()

    def create_markings_on(self, score_obj):
        '''
        In each voice, each note occurring immediately after a rest is marked.
        '''
        for voices in score_obj.voices_by_part:
                rested = 1
                for voice in voices:
                    for measure in voice.getElementsByClass(stream.Measure):
                        for n in measure.notesAndRests:
                            if isinstance(n, note.Rest):
                                rested = 1
                            elif isinstance(n, note.NotRest):
                                set_marking_in_general_note(n, self.key, rested)
                                if rested:
                                    rested = 0

from .base import FeatureAlgorithm, set_marking_in_general_note

from music21 import stream, note


class OnsetAfterRest(FeatureAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        In each voice, each note occurring immediately after a rest is marked.
        '''
        for voices in score_obj.voices_by_part:
                rested = True
                for voice in voices:
                    for measure in voice.getElementsByClass(stream.Measure):
                        for n in measure.notesAndRests:
                            if isinstance(n, note.Rest):
                                rested = True
                            elif isinstance(n, note.NotRest):
                                set_marking_in_general_note(n, self.key, rested)
                                if rested:
                                    rested = False

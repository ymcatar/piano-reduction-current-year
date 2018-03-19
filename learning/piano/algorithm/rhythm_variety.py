from .base import FeatureAlgorithm, set_marking_in_general_note

from music21 import note


class RhythmVariety(FeatureAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        In each voice, each note that
        -   is adjacent to a rest, or
        -   has a different duration than one of the adjacent notes
        is marked.
        '''
        for voices in score_obj.voices_by_part:
            for voice in voices:
                last_note = None
                last_duration = 0.0
                for n in voice.recurse(skipSelf=False).notesAndRests:
                    set_marking_in_general_note(n, self.key, False)

                    # This also marks rests as a side effect, although this
                    # does not serve any purpose.

                    # Note/Chord -> Rest
                    if (isinstance(last_note, note.NotRest) and
                            isinstance(n, note.Rest)):
                        set_marking_in_general_note(last_note, self.key, True)
                    # Rest -> Note/Chord
                    elif not last_note or isinstance(last_note, note.Rest):
                        set_marking_in_general_note(n, self.key, True)
                    # Note/Chord -> Note/Chord
                    elif (isinstance(last_note, note.NotRest) and
                            n.duration.quarterLength != last_duration):
                        set_marking_in_general_note(n, self.key, True)
                        set_marking_in_general_note(last_note, self.key, True)

                    last_note = n
                    last_duration = n.duration.quarterLength

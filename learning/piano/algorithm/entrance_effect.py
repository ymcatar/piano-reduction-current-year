from .base import FeatureAlgorithm, set_marking_in_general_note

from music21 import note, stream


class EntranceEffect(FeatureAlgorithm):
    dtype = 'float'
    range = (0.0, None)

    def run(self, score_obj):
        '''
        The entrance effect value for a note is given by the offset to the
        previous rest in the same *voice*, in quarter lengths.
        '''
        for voices in score_obj.voices_by_part:
            for voice in voices:
                rested = True
                last_offset = 0.0
                for measure in voice.getElementsByClass(stream.Measure):
                    for n in measure.notesAndRests:
                        if isinstance(n, note.Rest):
                            rested = True
                        elif isinstance(n, note.NotRest):
                            if rested:
                                last_offset = measure.offset + n.offset
                                rested = False
                            set_marking_in_general_note(
                                n, self.key,
                                measure.offset + n.offset - last_offset)

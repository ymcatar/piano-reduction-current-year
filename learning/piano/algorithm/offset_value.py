from music21 import stream
from .base import FeatureAlgorithm, get_markings, iter_notes_with_offset


class OffsetValue(FeatureAlgorithm):
    dtype = 'float'
    range = (0.0, None)

    def run(self, score_obj):
        for measure in score_obj.score.recurse(skipSelf=True).getElementsByClass(stream.Measure):
            for n, offset in iter_notes_with_offset(measure, recurse=True):
                get_markings(n)[self.key] = measure.offset + offset

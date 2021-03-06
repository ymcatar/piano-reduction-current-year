from .base import FeatureAlgorithm, get_markings, iter_notes

from music21 import stream
from collections import Counter


class Occurrence(FeatureAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        For each measure in each voice, the notes with the pitch class(es) that
        appears the most are marked, unless the max frequency is <= 1.
        '''
        for bar in score_obj.by_bar:
            measures = bar.recurse(skipSelf=False).getElementsByClass(stream.Measure)
            for measure in measures:
                for voice in measure.voices or [measure]:
                    counter = Counter(n.name for n in iter_notes(voice))
                    counter.setdefault('C', 0)  # so that max doesn't fail
                    max_freq = max(counter.values())

                    if max_freq > 1:
                        pitch_classes = {ps for ps, freq in counter.items()
                                         if freq == max_freq}
                    else:
                        pitch_classes = set()
                    for n in iter_notes(voice):
                        get_markings(n)[self.key] = n.name in pitch_classes

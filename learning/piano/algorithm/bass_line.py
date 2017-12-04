from .base import ReductionAlgorithm, get_markings, iter_notes

from music21 import stream
import numpy as np


class BassLine(ReductionAlgorithm):
    def __init__(self):
        super(BassLine, self).__init__()

    dtype = 'bool'

    def create_markings_on(self, score_obj):
        '''
        In each bar, the part with the lowest median pitch space is marked.
        '''
        for bar in score_obj.by_bar:
            best_median, best_measures = float('inf'), set()
            for measure in bar.recurse(
                    skipSelf=False).getElementsByClass(stream.Measure):
                pss = [n.pitch.ps for n in iter_notes(measure, recurse=True)]
                if not pss:
                    pss = [float('inf')]
                median = np.median(pss)

                if median < best_median:
                    best_median, best_measures = median, {measure}
                elif median == best_median:
                    best_measures.add(measure)

            for measure in bar.recurse(
                    skipSelf=False).getElementsByClass(stream.Measure):
                mark = measure in best_measures
                for n in iter_notes(measure, recurse=True):
                    get_markings(n)[self.key] = mark

from .base import ReductionAlgorithm, get_markings, iter_notes

import numpy as np
from collections import Counter


PITCH_CLASSES = list(range(12))


class PitchClassStatistics(ReductionAlgorithm):
    @property
    def all_keys(self):
        return ['{}_{!s}'.format(self.key, pc) for pc in PITCH_CLASSES]

    def run(self, score_obj):
        '''
        In each bar, a histogram of the pitch classes is constructed.
        '''
        for bar in score_obj.by_bar:
            counter = Counter(
                n.pitch.pitchClass for n in iter_notes(bar, recurse=True))

            histogram = [counter[i] for i in PITCH_CLASSES]

            # Normalize the histogram
            norm = np.linalg.norm(histogram)
            norm = norm or 1  # Avoid division by zero
            histogram = [x / norm for x in histogram]

            marks = dict(zip(self.all_keys, histogram))

            for n in iter_notes(bar, recurse=True):
                get_markings(n).update(marks)

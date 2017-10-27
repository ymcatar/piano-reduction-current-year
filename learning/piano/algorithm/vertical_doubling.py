from .base import ReductionAlgorithm, get_markings, iter_notes

from collections import Counter, defaultdict


class VerticalDoubling(ReductionAlgorithm):
    def __init__(self):
        super(VerticalDoubling, self).__init__()

    def create_markings_on(self, score_obj):
        '''
        In each offset, notes with a pitch class that appears at least twice is
        marked.
        '''
        for bar in score_obj.by_bar:
            # counters[offset][pitch_class] =
            #   no. of times pitch_class occurs at offset
            counters = defaultdict(lambda: Counter())
            for n in iter_notes(bar, recurse=True):
                counters[n.offset][n.name] += 1

            pitch_classes = {}
            for offset, counter in counters.items():
                pitch_classes[offset] = {pc for pc, freq in counter.items()
                                         if freq >= 2}

            for n in iter_notes(bar, recurse=True):
                get_markings(n)[self.key] = n.name in pitch_classes[n.offset]

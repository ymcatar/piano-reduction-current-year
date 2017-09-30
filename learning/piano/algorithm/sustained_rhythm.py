from .base import ReductionAlgorithm, get_markings, iter_notes

from music21 import stream


class SustainedRhythm(ReductionAlgorithm):
    _type = 'sustained'

    def __init__(self, division=1):
        super(SustainedRhythm, self).__init__()

    def create_markings_on(self, score_obj):
        '''
        In each bar, the non-empty part(s) with the least number of notes is
        marked.
        '''
        for bar in score_obj.by_bar:
            best_note_count, best_measures = 10 ** 9, set()

            # Each part has only one measure
            for measure in bar.recurse().getElementsByClass(stream.Measure):
                count = sum(1 for _ in iter_notes(measure.recurse()))
                if not count:
                    continue
                if count < best_note_count:
                    best_note_count, best_measures = count, {measure}
                elif count == best_note_count:
                    best_measures.add(measure)

            for measure in bar.recurse().getElementsByClass(stream.Measure):
                mark = measure in best_measures
                for n in iter_notes(measure.recurse()):
                    get_markings(n)[self.key] = mark

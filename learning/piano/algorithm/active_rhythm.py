from .base import ReductionAlgorithm, get_markings, iter_notes

from music21 import stream


class ActiveRhythm(ReductionAlgorithm):
    _type = 'active'

    def __init__(self):
        super(ActiveRhythm, self).__init__()

    def create_markings_on(self, score_obj):
        '''
        In each bar, the part(s) with the most number of notes is marked.
        '''
        for bar in score_obj.by_bar:
            best_note_count, best_measures = 0, set()

            # Each part has only one measure
            for measure in bar.recurse(
                    skipSelf=False).getElementsByClass(stream.Measure):
                count = sum(1 for _ in iter_notes(measure, recurse=True))
                if count > best_note_count:
                    best_note_count, best_measures = count, {measure}
                elif count == best_note_count:
                    best_measures.add(measure)

            for measure in bar.recurse(
                    skipSelf=False).getElementsByClass(stream.Measure):
                mark = measure in best_measures
                for n in iter_notes(measure, recurse=True):
                    get_markings(n)[self.key] = mark

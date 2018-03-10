from .base import FeatureAlgorithm, get_markings, iter_notes


class PitchDistance(FeatureAlgorithm):
    dtype = 'float'
    range = (0.0, None)

    def run(self, score_obj):
        '''
        The distance from middle C.
        '''
        for n in iter_notes(score_obj._score, recurse=True):
            get_markings(n)[self.key] = abs(n.pitch.ps - 60)

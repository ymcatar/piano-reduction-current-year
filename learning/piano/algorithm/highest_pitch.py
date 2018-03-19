from .base import FeatureAlgorithm, get_markings


class HighestPitch(FeatureAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        The highest pitch note at every offset.
        '''
        for offset, notes in score_obj.iter_offsets():
            highest_ps = max(n.pitch.ps for n in notes)
            for n in notes:
                get_markings(n)[self.key] = n.pitch.ps == highest_ps

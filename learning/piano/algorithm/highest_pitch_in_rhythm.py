from .base import FeatureAlgorithm, get_markings
from collections import defaultdict


class HighestPitchInRhythm(FeatureAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        The highest pitch note of a duration at every offset.
        '''
        for offset, notes in score_obj.iter_offsets():
            note_map = defaultdict(list)
            for n in notes:
                note_map[n.duration.quarterLength].append(n)
            for ns in note_map.values():
                highest_ps = max(n.pitch.ps for n in ns)
                for n in ns:
                    get_markings(n)[self.key] = n.pitch.ps == highest_ps

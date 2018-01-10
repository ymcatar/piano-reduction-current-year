#!/usr/bin/env python3

from ..base import ReductionAlgorithm, get_markings
from .analyzer import MotifAnalyzer

from music21 import stream
import numpy as np


class Motif(ReductionAlgorithm):
    def __init__(self):
        super(Motif, self).__init__()

    def create_markings_on(self, score_obj):
        '''
        For each score, find out the motif and mark it
        '''
        analyzer = MotifAnalyzer(score_obj.score)

        clusters = analyzer.cluster()

        for label, cluster in clusters.items():
            count = sum((len(analyzer.notegram_groups[notegram_group]) for notegram_group in cluster), 0)
            for notegram_group in cluster:
                for notegram in analyzer.notegram_groups[notegram_group]:
                    for note in notegram.get_note_list():
                        get_markings(note)[self.key] = count



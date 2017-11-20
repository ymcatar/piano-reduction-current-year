#!/usr/bin/env python3

from ..base import ReductionAlgorithm, get_markings
from .analyzer import MotifAnalyzer
from .algorithms import MotifAnalyzerAlgorithms

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

        analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_sequence_func,
                                MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 1))
        analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_sequence_func,
                                MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 1))
        analyzer.add_algorithm((MotifAnalyzerAlgorithms.note_contour_sequence_func,
                                MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 1))
        analyzer.add_algorithm((MotifAnalyzerAlgorithms.notename_transition_sequence_func,
                                MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 1))
        analyzer.add_algorithm((MotifAnalyzerAlgorithms.rhythm_transition_sequence_func,
                                MotifAnalyzerAlgorithms.entropy_note_score_func, 0, 1))

        analyzer.run_all()
        motifs = analyzer.get_top_motif_cluster()

        for notegram_group in motifs:
            for notegram in analyzer.notegram_groups[notegram_group]:
                for note in notegram.get_note_list():
                    get_markings(note)[self.key] = 1

import music21
import math
import numpy as np
import re

class MotifAnalyzerAlgorithms(object):

    @staticmethod
    def note_sequence_func(note_list):
        results = []
        for curr_note in note_list:
            if curr_note is None:
                continue
            elif curr_note.name == 'rest':
                results.append('R')
            else:
                results.append(curr_note.name)
        return results

    @staticmethod
    def rhythm_sequence_func(note_list):
        results = []
        for curr_note in note_list:
            if curr_note is None:
                continue
            elif curr_note.name == 'rest':
                results.append('R')
            else:
                results.append(str(curr_note.duration.quarterLength))
        return results

    @staticmethod
    def notename_transition_sequence_func(note_list):
        results = []
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i-1:i+1]
            if prev_note is None or curr_note is None:
                continue
            elif prev_note.name == 'rest' or curr_note.name == 'rest':
                continue
            else:
                prev_is_rest = isinstance(prev_note, music21.note.Rest)
                curr_is_rest = isinstance(curr_note, music21.note.Rest)
                if not prev_is_rest and not curr_is_rest:
                    curr_note_name = re.sub('[^A-G]', '', curr_note.name)
                    prev_note_name = re.sub('[^A-G]', '', prev_note.name)
                    results.append(str(ord(curr_note_name) - ord(prev_note_name)))
        return results

    @staticmethod
    def simple_note_score_func(notegram, sequence, freq):
        score = (len(sequence) ** 0.5) * freq
        if 'R' in sequence:
            score = -1
        return score

    @staticmethod
    def entropy_note_score_func(notegram, sequence, freq):
        probabilities = {item: sequence.count(item) / len(sequence) for item in list(sequence)}
        probs = np.array(list(probabilities.values()))
        score = - probs.dot(np.log2(probs)) * freq
        # if sequence contain 'rest', give a low score
        if 'R' in sequence:
            score = -1
        return score
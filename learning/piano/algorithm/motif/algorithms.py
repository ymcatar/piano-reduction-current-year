#!/usr/bin/env python3

import music21
import math
import numpy as np
import re

def is_rest(note):
    return isinstance(note, music21.note.Rest) or (
        isinstance(note, music21.note.Note) and \
        (note.name == 'rest' or float(note.duration.quarterLength) < 1e-2)
    )

class MotifAnalyzerAlgorithms(object):

    @staticmethod
    def note_sequence_func(note_list):
        results = []
        for curr_note in note_list:
            if is_rest(curr_note):
                results.append('R')
            else:
                results.append(curr_note.name)
        return results

    @staticmethod
    def notename_sequence_func(note_list):
        results = []
        for curr_note in note_list:
            if is_rest(curr_note):
                results.append('R')
            else:
                results.append(re.sub('[^A-G]', '', curr_note.name))
        return results

    @staticmethod
    def rhythm_sequence_func(note_list):
        results = []
        for curr_note in note_list:
            results.append(str(float(curr_note.duration.quarterLength)))
        # last note rhythm might sustain => replace with 1
        if len(results) > 0:
            results[-1] = '1.0'
        return results

    @staticmethod
    def notename_transition_sequence_func(note_list):
        results = []
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if is_rest(prev_note) and not is_rest(curr_note):
                results.append('RN')
            elif not is_rest(prev_note) and is_rest(curr_note):
                results.append('NR')
            elif not is_rest(prev_note) and not is_rest(curr_note):
                curr_note_name = re.sub('[^A-G]', '', curr_note.name)
                prev_note_name = re.sub('[^A-G]', '', prev_note.name)
                results.append(str(ord(curr_note_name) - ord(prev_note_name)))
        return results

    @staticmethod
    def note_contour_sequence_func(note_list):
        results = []
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if is_rest(prev_note) and not is_rest(curr_note):
                results.append('RN')
            elif not is_rest(prev_note) and is_rest(curr_note):
                results.append('NR')
            elif not is_rest(prev_note) and not is_rest(curr_note):
                if prev_note.pitch.ps == curr_note.pitch.ps:
                    results.append('=')
                elif prev_note.pitch.ps < curr_note.pitch.ps:
                    results.append('<')
                else:
                    results.append('>')
        return results

    @staticmethod
    def note_transition_sequence_func(note_list):
        results = []
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if is_rest(prev_note) and not is_rest(curr_note):
                    results.append('<')
            elif not is_rest(prev_note) and is_rest(curr_note):
                results.append('>')
            elif not is_rest(prev_note) and not is_rest(curr_note):
                results.append(str(curr_note.pitch.ps - prev_note.pitch.ps))
        return results

    @staticmethod
    def rhythm_transition_sequence_func(note_list):
        results = []
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if is_rest(prev_note) and not is_rest(curr_note):
                results.append('<')
            elif not is_rest(prev_note) and is_rest(curr_note):
                results.append('>')
            elif not is_rest(prev_note) and not is_rest(curr_note):
                curr_note_length = curr_note.duration.quarterLength
                if i == len(note_list) - 1:  # last note
                    curr_note_length = 1  # expand the last note to quarter note
                results.append('{0:.2f}'.format(
                    float(curr_note_length / prev_note.duration.quarterLength)))
        return results

    @staticmethod
    def freq_score_func(notegram, sequence, freq):
        return freq

    @staticmethod
    def simple_note_score_func(notegram, sequence, freq):
        score = len(sequence) * (freq ** 0.5)
        return score

    @staticmethod
    def distance_entropy_score_func(notegram, sequence, freq):
        score = 0
        sequence = [int(i) for i in sequence]
        distances = [(i - j) for i in sequence for j in sequence if i != j]
        probabilities = {item: distances.count(
            item) / len(distances) for item in distances}
        probs = np.array(list(probabilities.values()))
        score = - probs.dot(np.log2(probs)) * freq * len(sequence)
        return score

    @staticmethod
    def entropy_note_score_func(notegram, sequence, freq):
        probabilities = {item: sequence.count(
            item) / len(sequence) for item in list(sequence)}
        probs = np.array(list(probabilities.values()))
        score = - probs.dot(np.log2(probs)) * freq * len(sequence)
        return score

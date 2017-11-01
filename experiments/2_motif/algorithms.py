import music21
import math
import numpy as np
import re

class MotifAnalyzerAlgorithms(object):

    @staticmethod
    def note_sequence_func(note_list):
        results = []
        for curr_note in note_list: # ignore the last note
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
        # last note rhythm might sustain => replace with 1
        results[-1] = 1
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
                else:
                    results.append('R')
        return results

    @staticmethod
    def note_transition_sequence_func(note_list):
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
                    results.append(str(curr_note.pitch.ps - prev_note.pitch.ps))
                else:
                    results.append('R')
        return results

    @staticmethod
    def rhythm_transition_sequence_func(note_list):
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
                    if prev_note.duration.quarterLength - 0.0 < 1e-2:
                        results.append('R')
                    else:
                        curr_note_length = curr_note.duration.quarterLength
                        if i == len(note_list) - 1: # last note
                            curr_note_length = 1 # expand the last note to quarter note
                        results.append('{0:.2f}'.format(float(curr_note_length / prev_note.duration.quarterLength)))
                else:
                    results.append('R')
        return results

    @staticmethod
    def freq_score_func(notegram, sequence, freq):
        return freq

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
        score = - probs.dot(np.log2(probs)) * freq * len(sequence)
        # if sequence contain 'rest', give a low score
        for note in notegram:
            if note is not None and note.name == 'rest':
                score = -1
        return score
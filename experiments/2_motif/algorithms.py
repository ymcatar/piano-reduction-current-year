#!/usr/bin/env python3

import music21
import math
import numpy as np
import re

# static_var decorator
def static_var(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate

class MotifAnalyzerAlgorithms(object):

    @staticmethod
    @static_var("note_list_length", 3)
    def note_sequence_func(note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return []
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return []
        # use the note name as the sequence character
        new_item = curr_note.name
        if curr_note.name == 'rest':
            new_item = 'R'
        return [(new_item, [curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def note_transition_sequence_func(note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return []
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return []
        # record the transition of note
        new_item = None
        prev_is_rest = isinstance(prev_note, music21.note.Rest)
        curr_is_rest = isinstance(curr_note, music21.note.Rest)
        if not prev_is_rest and not curr_is_rest:
            new_item = str(curr_note.pitch.ps - prev_note.pitch.ps)
        else:
            new_item = 'R'
        return [(new_item, [prev_note, curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def notename_transition_sequence_func(note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return []
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return []
        # record the transition of note
        new_item = None
        prev_is_rest = isinstance(prev_note, music21.note.Rest)
        curr_is_rest = isinstance(curr_note, music21.note.Rest)
        if not prev_is_rest and not curr_is_rest:
            curr_note_name = re.sub('[^A-G]', '', curr_note.name)
            prev_note_name = re.sub('[^A-G]', '', prev_note.name)
            new_item = str(ord(curr_note_name) - ord(prev_note_name))
        else:
            new_item = 'R'
        return [(new_item, [prev_note, curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def rhythm_sequence_func(note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return []
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note is not None and next_note.name == 'rest':
            return []
        # use the note duration length as the sequence character
        new_item = str(curr_note.duration.quarterLength)
        return [(new_item, [curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def rhythm_transition_sequence_func(note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return []
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return []
        # record the transition of note
        new_item = None
        prev_is_rest = isinstance(prev_note, music21.note.Rest)
        curr_is_rest = isinstance(curr_note, music21.note.Rest)
        if not prev_is_rest and not curr_is_rest:
            if prev_note.duration.quarterLength - 0.0 < 1e-2:
                new_item = 'R'
            else:
                new_item = '{0:.2f}'.format(curr_note.duration.quarterLength / prev_note.duration.quarterLength)
        else:
            new_item = 'R'
        return [(new_item, [prev_note, curr_note])]

    @staticmethod
    def simple_note_score_func(ngram, freq, maps):
        ngram_chars = ngram.split(';')
        score = freq * math.sqrt(len(ngram_chars))
        # extreme: motif should not have a Rest
        if 'R' in ngram_chars:
            score = -1
        return score

    @staticmethod
    def entropy_note_score_func(ngram, freq, maps):
        ngram_chars = ngram.split(';')
        probabilities = { item: ngram_chars.count(item) / len(ngram_chars) for item in ngram_chars}
        probs = np.array(list(probabilities.values()))
        score = - probs.dot(np.log2(probs)) * freq * math.sqrt(len(ngram_chars))

        if 'R' in ngram_chars:
            score = -1

        return score
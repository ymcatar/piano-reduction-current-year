#!/usr/bin/env python3

import music21
import math
import numpy as np
import re
from copy import deepcopy
from expiringdict import ExpiringDict

def has_across_tie_to_next_note(curr_note, next_note):
    if curr_note is None or next_note is None:
        return False
    if curr_note.tie is None or next_note.tie is None:
        return False
    if curr_note.tie.type in ('start', 'continue'):
        if next_note.tie.type in ('continue', 'stop'):
            if curr_note.pitch.ps == next_note.pitch.ps:
                return True
    return False

def merge_nearby_rest(note_list):
    results = []
    i = 0
    while i < len(note_list):
        if note_list[i].isRest:
            total_rest_len = note_list[i].quarterLength
            while i + 1 < len(note_list) and note_list[i + 1].isRest:
                i += 1
                total_rest_len += note_list[i].quarterLength
            results.append(music21.note.Rest(quarterLength=total_rest_len))
        else:
            results.append(note_list[i])
        i += 1
    return results

def convert_chord_to_highest_note(note_list):
    results = []
    for noteOrChord in note_list:
        if isinstance(noteOrChord, music21.chord.Chord):
            results.append(music21.note.Note(
                noteOrChord.bass(),
                quarterLength=noteOrChord.duration.quarterLength))
        else:
            results.append(noteOrChord)
    return results

def merge_across_tie(note_list):
    results = []
    i = 0
    while i < len(note_list):
        if i + 1 < len(note_list) and has_across_tie_to_next_note(note_list[i], note_list[i + 1]):
            results.append(music21.note.Note(
                note_list[i].name, quarterLength=note_list[i].quarterLength + note_list[i + 1].quarterLength))
            i += 1
        else:
            results.append(note_list[i])
        i += 1
    return results

def fix_probably_sustained_last_note(note_list):
    if note_list[-1].duration.quarterLength - (1.0 - 1e-2) >= 0.0:
        note_list[-1] = music21.note.Note(
            note_list[-1].name, quarterLength=1.0)
    return note_list

def preprocess_note_list(note_list):
    if id(note_list) in preprocess_note_list.cache:
        # print('cache hit')
        return preprocess_note_list.cache.get(id(note_list))

    note_list = convert_chord_to_highest_note(note_list)
    note_list = merge_nearby_rest(note_list)
    note_list = merge_across_tie(note_list)
    note_list = fix_probably_sustained_last_note(note_list)

    preprocess_note_list.cache[id(note_list)] = note_list
    # print('cache miss')

    return note_list

preprocess_note_list.cache = ExpiringDict(max_len=1000, max_age_seconds=1)

class MotifAnalyzerAlgorithms(object):

    @staticmethod
    def note_sequence_func(note_list):
        results = []
        note_list = preprocess_note_list(note_list)
        for curr_note in note_list:
            if curr_note.isRest:
                results.append('R')
            else:
                results.append(curr_note.name)
        return results

    @staticmethod
    def notename_sequence_func(note_list):
        results = MotifAnalyzerAlgorithms.note_sequence_func(note_list)
        return [re.sub('[^A-GR]', '', i) for i in results]

    @staticmethod
    def rhythm_sequence_func(note_list):
        results = []
        note_list = preprocess_note_list(note_list)
        for curr_note in note_list:
            results.append('{0:.1f}'.format(
                float(curr_note.duration.quarterLength)))
        return results

    @staticmethod
    def note_vector_sequence_func(index):
        def func(note_list):
            results = []
            note_list = preprocess_note_list(note_list)
            if index >= len(note_list) or note_list[index].isRest:
                return []
            reference = note_list[index]
            for curr_note in note_list:
                if curr_note == reference:
                    results.append('*')
                elif curr_note.isRest:
                    results.append('R')
                else:
                    results.append(str(curr_note.pitch.ps - reference.pitch.ps))
            return results
        return func

    @staticmethod
    def rhythm_vector_sequence_func(index):
        def func(note_list):
            results = []
            note_list = preprocess_note_list(note_list)
            if index >= len(note_list):
                return []
            reference = note_list[index]
            for curr_note in note_list:
                if curr_note == reference:
                    results.append('*')
                else:
                    results.append('{0:.1f}'.format(
                        float(curr_note.duration.quarterLength / reference.duration.quarterLength)
                    ))
            return results
        return func

    @staticmethod
    def rhythm_reverse_vector_sequence_func(note_list):
        return list(reversed(MotifAnalyzerAlgorithms.rhythm_vector_sequence_func(reversed(note_list))))

    @staticmethod
    def notename_transition_sequence_func(note_list):
        results = []
        note_list = preprocess_note_list(note_list)
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if prev_note.isRest and not curr_note.isRest:
                results.append('RN')
            elif not prev_note.isRest and curr_note.isRest:
                results.append('NR')
            elif not prev_note.isRest and not curr_note.isRest:
                curr_note_name = re.sub('[^A-G]', '', curr_note.name)
                prev_note_name = re.sub('[^A-G]', '', prev_note.name)
                results.append(str(ord(curr_note_name) - ord(prev_note_name)))
        return results

    @staticmethod
    def note_contour_sequence_func(note_list):
        results = []
        note_list = preprocess_note_list(note_list)
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if prev_note.isRest and not curr_note.isRest:
                results.append('RN')
            elif not prev_note.isRest and curr_note.isRest:
                results.append('NR')
            elif not prev_note.isRest and not curr_note.isRest:
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
        note_list = preprocess_note_list(note_list)
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            if prev_note.isRest and not curr_note.isRest:
                results.append('RN')
            elif not prev_note.isRest and curr_note.isRest:
                results.append('NR')
            elif not prev_note.isRest and not curr_note.isRest:
                results.append(str(curr_note.pitch.ps - prev_note.pitch.ps))
        return results

    @staticmethod
    def rhythm_transition_sequence_func(note_list):
        results = []
        note_list = preprocess_note_list(note_list)
        for i in range(1, len(note_list)):
            prev_note, curr_note = note_list[i - 1:i + 1]
            curr_note_length = curr_note.duration.quarterLength
            results.append('{0:.1f}'.format(
                float(curr_note_length / prev_note.duration.quarterLength)))
        return results

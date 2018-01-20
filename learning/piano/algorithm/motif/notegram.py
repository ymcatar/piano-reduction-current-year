#!/usr/bin/env python3

from .algorithms import MotifAnalyzerAlgorithms, preprocess_note_list, convert_chord_to_highest_note

def nice_note_sequence_func(note_list):
    results = []
    for curr_note in note_list:
        string = None 
        if curr_note.isRest:
            string = 'R'
        else:
            string = curr_note.name
        if curr_note.tie is not None:
            string += '~'
        results.append(string)
    return results

def nice_rhythm_sequence_func(note_list):
    results = []
    for curr_note in note_list:
        results.append('{0:.1f}'.format(float(curr_note.duration.quarterLength)))
    return results

class Notegram(object):

    def __init__(self, note_list, offset):
        if len(note_list) != len(offset):
            raise ValueError(
                'Length of note_list mismatches with length of offset')
        self.note_list = note_list
        self.offset = offset

    def __len__(self):
        return len(self.note_list)

    def __hash__(self):
        return id(self)

    def __str__(self):  # this determines how notegram are grouped together
        note_list = self.note_list
        note_list = preprocess_note_list(note_list)
        return ';'.join(i[0] + ',' + i[1] for i in zip(
            MotifAnalyzerAlgorithms.note_sequence_func(note_list),
            MotifAnalyzerAlgorithms.rhythm_sequence_func(note_list)
        ))

    def to_nice_string(self):
        note_list = convert_chord_to_highest_note(self.note_list)
        return '; '.join(i[0].rjust(3) + ', ' + i[1] for i in zip(
            nice_note_sequence_func(note_list),
            nice_rhythm_sequence_func(note_list)
        ))

    def get_note_list(self):
        return self.note_list

    def get_note_by_index(self, index):
        if index >= len(self):
            raise ValueError('Invalid note index')
        return self.note_list[index]

    def get_note_offset_by_index(self, index):
        if index >= len(self):
            raise ValueError('Invalid note index')
        return self.offset[index]

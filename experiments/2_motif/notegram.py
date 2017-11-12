#!/usr/bin/env python3

from algorithms import MotifAnalyzerAlgorithms

class Notegram(object):

    def __init__(self, note_list, offset):
        if len(note_list) != len(offset):
            raise ValueError('Length of note_list mismatches with length of offset')
        self.note_list = note_list
        self.offset = offset

    def __len__(self):
        return len(self.note_list)

    def __hash__(self):
        return id(self)

    def __str__(self):
        return str(list(zip(
            MotifAnalyzerAlgorithms.note_sequence_func(self.note_list),
            MotifAnalyzerAlgorithms.rhythm_sequence_func(self.note_list)
        )))

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
#!/usr/bin/env python3

import music21
import os

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)

    @staticmethod
    def note_func(result, curr_note):
        curr_is_note = isinstance(curr_note, music21.note.Note)
        new_item = curr_note.name
        if new_item == 'rest':
            new_item = 'R'
        return result + [(new_item, curr_note)] \
             if new_item is not None else result

    @staticmethod
    def rhythm_func(result, curr_note):
        curr_is_note = isinstance(curr_note, music21.note.Note)
        new_item = str(curr_note.duration.quarterLength)
        return result + [(new_item, curr_note)] \
            if new_item is not None else result

    @staticmethod
    def test_func(result, curr_note):
        curr_is_note = isinstance(curr_note, music21.note.Note)
        new_item = curr_note.name
        if new_item == 'rest':
            new_item = 'R'
        new_item = new_item + str(curr_note.duration.quarterLength)
        return result + [(new_item, curr_note)] \
            if new_item is not None else result

    def to_string(self, partId, func):
        curr_part = self.score.getElementById(partId)
        result = []
        for curr_note in curr_part.recurse().getElementsByClass(('Note', 'Rest')):
            result = func(result, curr_note)
        return result

analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')

for part in analyzer.score.recurse().getElementsByClass('Part'):
    string = analyzer.to_string(part.id, MotifAnalyzer.test_func)
    print(' '.join(item[0] for item in string))
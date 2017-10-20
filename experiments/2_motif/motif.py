#!/usr/bin/env python3

import music21
import os

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)

    @staticmethod
    def note_func(result, prev_note, curr_note, next_note):
        curr_is_note = isinstance(curr_note, music21.note.Note)
        new_item = curr_note.name
        if new_item == 'rest':
            new_item = 'R'
        return result + [(new_item, curr_note)] \
             if new_item is not None else result

    @staticmethod
    def rhythm_func(result, prev_note, curr_note, next_note):
        curr_is_note = isinstance(curr_note, music21.note.Note)
        new_item = str(curr_note.duration.quarterLength)
        return result + [(new_item, curr_note)] \
            if new_item is not None else result

    @staticmethod
    def test_func(result, prev_note, curr_note, next_note):
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

        iterator = curr_part.recurse().getElementsByClass(('Note', 'Rest'))

        prev_note = iterator[0]
        next_note = iterator[1]
        for i in range(0, len(iterator) - 1):
            curr_note = iterator[i]
            result = func(result, prev_note, curr_note, next_note)
            prev_note = curr_note
            curr_note = next_note
            next_note = iterator[i + 1]
        return result

    def generate_all_ngrams(self, length, tokens):
        results = {}
        ngram_temp = []
        curr = 0
        while True:
            if len(ngram_temp) == length:
                result = '_'.join(ngram_temp)
                if result in results:
                    results[result] = results[result] + 1
                else:
                    results[result] = 1
                ngram_temp.pop()
            else:
                if curr >= len(tokens):
                    break
                ngram_temp.append(tokens[curr][0])
                curr = curr + 1
        return results


analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')

for part in analyzer.score.recurse().getElementsByClass('Part'):
    string = analyzer.to_string(part.id, MotifAnalyzer.test_func)
    # print(string)
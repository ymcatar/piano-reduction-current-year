#!/usr/bin/env python3

import music21
import os

# static_var decorator
def static_var(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)

    @staticmethod
    @static_var("note_list_length", 3)
    def note_func(result, note_list):
        prev_note, curr_note, next_note = note_list
        if prev_note is None or next_note is None:
            return result

        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note is not None and next_note.name == 'rest':
            return result

        new_item = curr_note.name
        if curr_note.name == 'rest':
            new_item = 'R'

        return result + [(new_item, [curr_note])]

    def to_sequence(self, partId, func):
        curr_part = self.score.getElementById(partId)
        result = []

        curr_ngram = [ item for item in curr_part.recurse().getElementsByClass(('Note', 'Rest')) ]

        while len(curr_ngram) >= func.note_list_length:
            result = func(result, curr_ngram[0:func.note_list_length])
            curr_ngram.pop(0)

        # tail case
        while len(curr_ngram) != 0 and len(curr_ngram) < func.note_list_length:
            curr_ngram.append(None)

        while len(curr_ngram) != 0 and curr_ngram[0] is not None:
            result = func(result, curr_ngram[0:func.note_list_length])
            curr_ngram.pop(0)
            curr_ngram.append(None)

        return result

    def generate_all_ngrams(self, length, sequence):
        curr_ngram, all_ngrams = ([], {})
        curr_map, all_maps = ([], {})

        curr = 0
        while True:
            if len(curr_ngram) == length:
                frozen_ngram = ';'.join(curr_ngram)
                if frozen_ngram in all_ngrams:
                    all_ngrams[frozen_ngram] = all_ngrams[frozen_ngram] + 1
                    all_maps[frozen_ngram] = all_maps[frozen_ngram] + curr_map
                else:
                    all_ngrams[frozen_ngram] = 1
                    all_maps[frozen_ngram] = []
                curr_ngram.pop(0)
                curr_map.pop(0)
            else:
                if curr >= len(sequence):
                    break
                character, note_list = sequence[curr]
                curr_ngram.append(character)
                curr_map.append(note_list)
                curr = curr + 1

        return all_ngrams, all_maps

analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')

sequence = []
for part in analyzer.score.recurse().getElementsByClass('Part'):
    sequence = sequence + analyzer.to_sequence(part.id, MotifAnalyzer.note_func)

ngrams, maps = analyzer.generate_all_ngrams(4, sequence)

maximum_ngram = max(ngrams, key=ngrams.get)

for ngram_grouped_notes in maps[maximum_ngram]:
    for ngram_note in ngram_grouped_notes:
        ngram_note.style.color = '#FF0000'

analyzer.score.show()
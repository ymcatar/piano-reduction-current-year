#!/usr/bin/env python3

import music21
import os

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)

    @staticmethod
    def note_func(result, prev_note, curr_note, next_note):
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

        curr_trigram = [ item for item in curr_part.recurse().getElementsByClass(('Note', 'Rest')) ]

        while len(curr_trigram) >= 3:
            prev_note, curr_note, next_note = curr_trigram[0:3]
            result = func(result, prev_note, curr_note, next_note)
            curr_trigram.pop(0)

        # tail case
        if len(curr_trigram) == 2:
            result = func(result, curr_trigram[0], curr_trigram[1], None)
        elif len(curr_trigram) == 1:
            result = func(result, curr_trigram[0], None, None)

        return result

    def generate_all_ngrams(self, length, sequence):
        curr_ngram, all_ngrams = ([], {})

        curr = 0
        while True:
            if len(curr_ngram) == length:
                frozen_ngram = ';'.join(curr_ngram)
                if frozen_ngram in all_ngrams:
                    all_ngrams[frozen_ngram] = all_ngrams[frozen_ngram] + 1
                else:
                    all_ngrams[frozen_ngram] = 1
                curr_ngram.pop(0)
            else:
                if curr >= len(sequence):
                    break
                character, note_list = sequence[curr]
                curr_ngram.append(character)
                curr = curr + 1

        return all_ngrams

analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')

sequence = []
for part in analyzer.score.recurse().getElementsByClass('Part'):
    sequence = sequence + analyzer.to_sequence(part.id, MotifAnalyzer.note_func)

ngrams = analyzer.generate_all_ngrams(4, sequence)

maximum_ngram = max(ngrams, key=ngrams.get)

print(maximum_ngram)

# for ngram_grouped_notes in ngrams_to_note[maximum_ngram]:
#     for ngram_notes in ngram_grouped_notes:
#         ngram_notes.style.color = '#FF0000'

# analyzer.score.show()
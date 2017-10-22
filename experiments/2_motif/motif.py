#!/usr/bin/env python3

import music21
import os
import math
import numpy as np

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
    def note_sequence_func(result, note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return result
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return result
        # use the note name as the sequence character
        new_item = curr_note.name
        if curr_note.name == 'rest':
            new_item = 'R'
        return result + [(new_item, [curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def note_transition_sequence_func(result, note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return result
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note.name == 'rest':
            return result
        # record the transition of note
        new_item = None
        prev_is_rest = isinstance(prev_note, music21.note.Rest)
        curr_is_rest = isinstance(curr_note, music21.note.Rest)
        if not prev_is_rest and not curr_is_rest:
            new_item = str(curr_note.pitch.ps - prev_note.pitch.ps)
        else:
            new_item = 'R'
        return result + [(new_item, [prev_note, curr_note])]

    @staticmethod
    @static_var("note_list_length", 3)
    def rhythm_sequence_func(result, note_list):
        prev_note, curr_note, next_note = note_list
        # we process iff the reading frame all have notes
        if prev_note is None or curr_note is None or next_note is None:
            return result
        # merge rest together as a single rest
        if curr_note.name == 'rest' and next_note is not None and next_note.name == 'rest':
            return result
        # use the note duration length as the sequence character
        new_item = str(curr_note.duration.quarterLength)
        return result + [(new_item, [curr_note])]

    @staticmethod
    def simple_note_score_func(ngram, freq):
        ngram_chars = ngram.split(';')
        score = freq * len(ngram_chars)
        # if the ngram only have one unique character
        if ngram_chars.count(ngram_chars[0]) == len(ngram_chars):
            score = score * len(ngram_chars) / 2
        # # motif should not start/end with Rest
        # elif ngram_chars[0] == 'R' or ngram_chars[-1] == 'R':
        #     return -1
        # extreme: motif should not have a Rest
        if 'R' in ngram_chars:
            score = -1

        return score

    @staticmethod
    def entropy_note_score_func(ngram, freq):
        ngram_chars = ngram.split(';')
        probabilities = { item: ngram_chars.count(item) / len(ngram_chars) for item in ngram_chars}
        probs = np.array(list(probabilities.values()))
        score = - probs.dot(np.log2(probs)) * freq

        if 'R' in ngram_chars:
            score = -1

        return score

    def to_sequence(self, part_id, sequence_func):
        curr_ngram = [
            item for item in self.score.getElementById(part_id)  \
            .recurse().getElementsByClass(('Note', 'Rest')) \
        ]

        result = []

        while len(curr_ngram) >= sequence_func.note_list_length:
            result = sequence_func(result, curr_ngram[0:sequence_func.note_list_length])
            curr_ngram.pop(0)

        # tail case
        while len(curr_ngram) != 0 and len(curr_ngram) < sequence_func.note_list_length:
            curr_ngram.append(None)
        # populate None until all Note passed to sequence_func
        while len(curr_ngram) != 0 and curr_ngram[0] is not None:
            result = sequence_func(result, curr_ngram[0:sequence_func.note_list_length])
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

    def score_all_ngrams(self, all_ngrams, score_func):
        for key, value in all_ngrams.items():
            all_ngrams[key] = score_func(key, value)
        return all_ngrams

    def analyze_top_motif(self, max_count, sequence_func, score_func):
        sequence = []
        for part in self.score.recurse().getElementsByClass('Part'):
            sequence = sequence + self.to_sequence(part.id, sequence_func)

        ngrams, maps = ({}, {})

        for i in range(3, 10):
            curr_ngrams, curr_maps = self.generate_all_ngrams(i, sequence)
            curr_ngrams = self.score_all_ngrams(curr_ngrams, score_func)

            ngrams = { **ngrams, **curr_ngrams }
            maps = { ** maps, ** curr_maps }

        max_ngrams = []
        temp_ngrams = ngrams.copy()
        for i in range(0, max_count):
            curr_max_ngram = max(temp_ngrams, key=temp_ngrams.get)
            temp_ngrams.pop(curr_max_ngram)
            max_ngrams.append((ngrams[curr_max_ngram], curr_max_ngram, maps[curr_max_ngram]))

        return max_ngrams


analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')
max_grams = analyzer.analyze_top_motif(
    10,
    MotifAnalyzer.note_transition_sequence_func,
    MotifAnalyzer.entropy_note_score_func
)

print('\n'.join(str(item[0]) + ' ' + item[1] for item in max_grams))

# for max_gram in max_grams:
#     score, sequence, notes = max_gram
#     for grouped_note in notes:
#         for note in grouped_note:
#             note.style.color = '#FF0000'

# analyzer.score.show()
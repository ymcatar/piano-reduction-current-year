#!/usr/bin/env python3

import music21
import os
import sys

from algorithms import MotifAnalyzerAlgorithms

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
        self.note_map = {}

    def to_sequence(self, part_id, sequence_func):
        curr_ngram = [
            item for item in self.score.getElementById(part_id)  \
            .recurse().getElementsByClass(('Note', 'Rest')) \
        ]

        result = []

        while len(curr_ngram) >= sequence_func.note_list_length:
            new_items = sequence_func(curr_ngram[0:sequence_func.note_list_length])
            for key, item in enumerate(new_items):
                character, note_list = item
                for note in note_list:
                    if id(note) not in self.note_map:
                        self.note_map[id(note)] = note
                new_items[key] = (character, [ id(note) for note in note_list ])
            result.extend(new_items)
            curr_ngram.pop(0)

        # tail case
        while len(curr_ngram) != 0 and len(curr_ngram) < sequence_func.note_list_length:
            curr_ngram.append(None)

        # tail case: populate None until all Note passed to sequence_func
        while len(curr_ngram) != 0 and curr_ngram[0] is not None:
            new_items = sequence_func(curr_ngram[0:sequence_func.note_list_length])
            for key, item in enumerate(new_items):
                character, note_list = item
                for note in note_list:
                    if id(note) not in self.note_map:
                        self.note_map[id(note)] = note
                new_items[key] = (character, [ id(note) for note in note_list ])
            result.extend(new_items)
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

    def score_ngrams(self, ngrams, maps, score_func):
        for key, value in ngrams.items():
            ngrams[key] = score_func(key, value, maps[key])
        return ngrams


    def analyze_top_motif(self, max_count, sequence_func, score_func):
        sequence = []
        for part in self.score.recurse().getElementsByClass('Part'):
            sequence = sequence + self.to_sequence(part.id, sequence_func)

        ngrams, maps = ({}, {})

        for i in range(3, 10):

            curr_ngrams, curr_maps = self.generate_all_ngrams(i, sequence)
            curr_ngrams = self.score_ngrams(curr_ngrams, curr_maps, score_func)

            ngrams = { **ngrams, **curr_ngrams }
            maps = { ** maps, ** curr_maps }

        max_ngrams = []
        temp_ngrams = ngrams.copy()
        for i in range(0, max_count):
            curr_max_ngram = max(temp_ngrams, key=temp_ngrams.get)
            temp_ngrams.pop(curr_max_ngram)
            max_ngrams.append((ngrams[curr_max_ngram], curr_max_ngram, maps[curr_max_ngram]))

        return max_ngrams

if len(sys.argv) != 3:
    print("Usage: $0 [path of the input MusicXML file] [output path]")
    exit()

sequence_funcs = {
    'noteSequence': MotifAnalyzerAlgorithms.note_sequence_func,
    'rhythmSequence': MotifAnalyzerAlgorithms.rhythm_sequence_func,
    'noteTransitionSequence': MotifAnalyzerAlgorithms.note_transition_sequence_func,
    'rhythmTransitionSequence': MotifAnalyzerAlgorithms.rhythm_transition_sequence_func
}

score_funcs = {
    'simpleNote': MotifAnalyzerAlgorithms.simple_note_score_func,
    'entropyNote': MotifAnalyzerAlgorithms.entropy_note_score_func
}

output_path = sys.argv[2]
filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]

for curr_sequence_func_name, curr_sequence_func in sequence_funcs.items():
    for curr_score_func_name, curr_score_func in score_funcs.items():
        analyzer = MotifAnalyzer(sys.argv[1])
        max_grams = analyzer.analyze_top_motif(
            1,
            curr_sequence_func,
            curr_score_func
        )
        print('\n'.join(str(item[0]) + '\t\t' + item[1] for item in max_grams))

        for max_gram in max_grams:
            _, _, motif_note_ids = max_gram
            for grouped_note_ids in motif_note_ids:
                for note_id in grouped_note_ids:
                    analyzer.note_map[note_id].style.color = '#FF0000'

        analyzer.score.write(
            'musicxml',
            os.path.join(
                output_path,
                filename + '_' + curr_sequence_func_name + '_' + curr_score_func_name + '.xml'
            )
        )

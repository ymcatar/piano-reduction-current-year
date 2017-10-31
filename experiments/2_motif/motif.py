#!/usr/bin/env python3

import os
import sys
import music21

from algorithms import MotifAnalyzerAlgorithms

class MotifAnalyzer(object):

    def __init__(self, filepath):
        self.filepath = filepath

        self.score = music21.converter.parse(filepath)
        self.score.toSoundingPitch()

        self.note_map = {}
        self.ngrams = {}
        self.maps = {}

        self.func_list = []

    def add_func(self, sequence_func, score_func):
        self.func_list.append((sequence_func, score_func))

    def to_sequence(self, part_id, sequence_func):
        curr_ngram = [
            item for item in self.score.getElementById(part_id)  \
            .recurse().getElementsByClass(('Note', 'Rest')) \
        ]

        result = []

        if len(curr_ngram) % sequence_func.note_list_length != 0:
            for i in range(len(curr_ngram) % sequence_func.note_list_length, sequence_func.note_list_length):
                curr_ngram.append(None)

        while len(curr_ngram) >= sequence_func.note_list_length:
            new_items = sequence_func(curr_ngram[0:sequence_func.note_list_length])
            for key, item in enumerate(new_items):
                character, note_list = item
                for note in note_list:
                    self.note_map[id(note)] = note
                new_items[key] = (character, [ id(note) for note in note_list ])
            result.extend(new_items)
            curr_ngram.pop(0)

        return result

    def generate_all_ngrams(self, length, sequence):
        curr_ngram, all_ngrams = ([], {})
        curr_map, all_maps = ([], {})

        curr = 0
        while curr < len(sequence):
            if len(curr_ngram) == length:
                frozen_ngram = ';'.join(curr_ngram)
                if frozen_ngram in all_ngrams:
                    all_ngrams[frozen_ngram] = all_ngrams[frozen_ngram] + 1
                    all_maps[frozen_ngram].append(curr_map)
                else:
                    all_ngrams[frozen_ngram] = 1
                    all_maps[frozen_ngram] = [curr_map]
                curr_ngram.pop(0)
                curr_map.pop(0)
            else:
                character, note_list = sequence[curr]
                curr_ngram.append(character)
                curr_map = curr_map + note_list
                curr = curr + 1

        return all_ngrams, all_maps

    def score_ngrams(self, ngrams, maps, score_func):
        for key, value in ngrams.items():
            ngrams[key] = score_func(key, value, maps[key])
        return ngrams

    def generate_all_motifs(self):
        assert len(self.func_list) != 0

        self.ngrams = {}
        self.maps = {}

        sequence = []

        # first iteration: using the first (sequence_func, score_func) pair
        first_sequence_func, first_score_func = self.func_list[0]
        for part in self.score.recurse().getElementsByClass('Part'):
            sequence = sequence + self.to_sequence(part.id, first_sequence_func)

        for i in range(3, 10):
            curr_ngrams, curr_maps = self.generate_all_ngrams(i, sequence)
            curr_ngrams = self.score_ngrams(
                curr_ngrams,
                curr_maps,
                first_score_func
            )
            self.ngrams = {** self.ngrams, ** curr_ngrams}
            self.maps = {** self.maps, ** curr_maps}

        # remaining iteration: remaining (sequence_func, score_func) pairs
        # for curr_func_pair in self.func_list[1:]:
            # curr_sequence_func, curr_score_func = curr_func_pair

    def get_top_motifs(self, max_count):
        max_ngrams = []
        temp_ngrams = self.ngrams.copy()
        for i in range(0, max_count):
            curr_max_ngram = max(temp_ngrams, key=temp_ngrams.get)
            temp_ngrams.pop(curr_max_ngram)
            max_ngrams.append(
                (self.ngrams[curr_max_ngram], curr_max_ngram, self.maps[curr_max_ngram])
            )
        return max_ngrams

if len(sys.argv) != 3:
    print("Usage: $0 [path of the input MusicXML file] [output path]")
    exit()

output_path = sys.argv[2]
filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]

analyzer = MotifAnalyzer(sys.argv[1])

analyzer.add_func(
    MotifAnalyzerAlgorithms.note_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func
)

analyzer.add_func(
    MotifAnalyzerAlgorithms.notename_transition_sequence_func,
    MotifAnalyzerAlgorithms.entropy_note_score_func
)

analyzer.generate_all_motifs()
max_ngrams = analyzer.get_top_motifs(5)

print('\n'.join(str(item[0]) + '\t\t' + item[1] for item in max_ngrams))

# for max_gram in max_ngrams:
#     _, _, motif_note_ids = max_gram
#     for grouped_note_ids in motif_note_ids:
#         for note_id in grouped_note_ids:
#             analyzer.note_map[note_id].style.color = '#FF0000'

# analyzer.score.write(
#     'musicxml',
#     os.path.join(
#         output_path,
#         filename + '_' + curr_sequence_func_name + '_' + curr_score_func_name + '.xml'
#     )
# )
#!/usr/bin/env python3

import music21
import os

class MotifAnalyzer(object):
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.score = music21.converter.parse(filepath)
    
    def generate_part_step(self, partId, func):
        curr_part = self.score.getElementById(partId)
        prev_note = None
        result = []
        for note in curr_part.recurse().getElementsByClass(('Note', 'Rest')):
            result = func(result, prev_note, note)
            prev_note = note
        return result

    def generate_part_interval_step(self, partId):
        def intervalFunc(result, prev_note, curr_note):
            prev_is_note = isinstance(prev_note, music21.note.Note)
            curr_is_note = isinstance(curr_note, music21.note.Note)
            new_item = None
            if prev_is_note and curr_is_note:
                if prev_note.pitch == curr_note.pitch:
                    new_item = '='
                else:
                    new_item = '<' if prev_note.pitch < curr_note.pitch else '>'
            elif prev_is_note:
                new_item = 'N'
            elif curr_is_note:
                new_item = 'R'
            return result + [(new_item, prev_note, curr_note)] \
                if new_item is not None else result
        return self.generate_part_step(partId, intervalFunc)
    
    def get_motif_from_step(self, step):
        max_result = []
        for length in range(3, 8):
            temp_kmers = {}
            for i in range(0, len(step) - length):
                index = list(map(lambda i: i[0], step[i:i+length]))

                # if list only have R and N, unlikely to be motif => remove
                if len([i for i in index if i != 'R' and i != 'N']) == 0:
                    continue
                
                index = ','.join(index)
                if index not in temp_kmers:
                    temp_kmers[index] = []
                temp_kmers[index].append(i)

            maximum = 0
            maximum_indices = []
            for pattern, indices in temp_kmers.items():
                if len(indices) * len(pattern) / 2 == maximum: # do this to favour longer motiff
                    maximum_indices = maximum_indices + indices
                elif len(indices) * len(pattern) / 2 > maximum:
                    maximum_indices = indices
                    maximum = len(indices) * len(pattern) / 2
            max_result.append((length, maximum, maximum_indices))

        result = max_result[0]
        for item in max_result:
            length, freq, indices = item
            if freq > result[1]:
                result = item
        
        length, freq, indices = result
        return (length, indices)
            
            
        
analyzer = MotifAnalyzer(os.getcwd() + '/sample/Beethoven_5th_Symphony_Movement_1.xml')

for part in analyzer.score.recurse().getElementsByClass('Part'):
    step = analyzer.generate_part_interval_step(part.id)
    motif_length, motif_indices = analyzer.get_motif_from_step(step)

    motiffs = ([ [ step[j] for j in range(i, i + motif_length) ] for i in motif_indices ])
    result = []
    for motif in motiffs:
        temp = [ motif[0][1] ]
        for i in motif:
            temp.append(i[2])
        result.append(temp)

    for motif in result:
        for note in motif:
            note.style.color = '#FF0000'

analyzer.score.show()
    


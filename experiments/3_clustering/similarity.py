import music21
import os
import sys

from Bio import pairwise2

def score_to_notegram(score):
  notegram = []
  for note in score.recurse().getElementsByClass(('Note', 'Rest')):
    notegram.append(note)
  return notegram

def normalize_sequences(first, second):
  results = []
  mapping = {}
  curr_index = 0
  for character in first + second:
    if character not in mapping:
      mapping[character] = chr(ord('a') + curr_index)
      curr_index += 1
    results.append(mapping[character])
  return ''.join(results[:len(first)]), ''.join(results[len(first):])

def align_sequences(first, second):
  first, second = normalize_sequences(first, second)
  score = pairwise2.align.globalms(first, second, 2, -1, -0.5, -0.1, score_only = True)
  return score

def note_sequence_func(note_list):
  results = []
  for curr_note in note_list:
    results.append(curr_note.name)
  return results

def rhythm_sequence_func(note_list):
  results = []
  for curr_note in note_list:
    results.append(str(curr_note.duration.quarterLength))
  # last note rhythm might sustain => replace with 1
  # if len(results) > 0:
  #   results[-1] = '1.0'
  return results

def get_similarity(first, second):
  sequence_func_list = [
    note_sequence_func,
    rhythm_sequence_func
  ]
  score = 0.0
  for sequence_func in sequence_func_list:
    first_sequence = sequence_func(first)
    second_sequence = sequence_func(second)
    score += align_sequences(first_sequence, second_sequence)
  return score

# first = music21.converter.parse("tinynotation: 4/4 b4 b b ebw")
# second = music21.converter.parse("tinynotation: 4/4 b8 b b eb4")

# first_notegram = score_to_notegram(first)
# second_notegram = score_to_notegram(second)

# print(
#   get_similarity(first_notegram, second_notegram)
# )
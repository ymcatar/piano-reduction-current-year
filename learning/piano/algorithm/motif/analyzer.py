#!/usr/bin/env python3

import music21
import math
import numpy as np

from collections import defaultdict
from sklearn.cluster import DBSCAN, SpectralClustering, AgglomerativeClustering
from intervaltree import Interval, IntervalTree

from termcolor import colored

from .notegram import Notegram
from .similarity import get_dissimilarity_matrix

NGRAM_SIZE = 4

OVERLAP_THRESHOLD = 0.5
Z_SCORE_THRESHOLD = 2

MIN_CLUSTER_SIZE = 10

def has_across_tie_to_next_note(curr_note, next_note):
    if curr_note is None or next_note is None:
        return False
    if not isinstance(curr_note, music21.note.Note) or not isinstance(next_note, music21.note.Note):
        return False
    if curr_note.tie is None or next_note.tie is None:
        return False
    if curr_note.tie.type in ('start', 'continue'):
        if next_note.tie.type in ('continue', 'stop'):
            if curr_note.pitch.ps == next_note.pitch.ps:
                return True
    return False

uninteresting_notes = set()

def is_notegram_unintersting(notegram):
    is_interesting = True
    notesAndRests = list(n[1] for n in notegram)
    # check if any note is marked as uninteresting previously
    if any(id(n) in uninteresting_notes for n in notesAndRests):
        is_interesting = False
    else:
        notes = list(n for n in notesAndRests if isinstance(n, music21.note.Note))
        rhythms = [n.duration.quarterLength for n in notesAndRests]
        pitches = [n.pitch.ps for n in notes if n.isRest is True]
        # see if both equal rhythm and equal pitch
        if len(set(rhythms)) == 1 and len(set(pitches)) == 1:
            is_interesting = False
        else:
            # check if they can form a common chord
            note_names = set(n.name for n in notes)
            if len(set(rhythms)) == 1 and len(note_names) >= 3:
                # form the chord and see if they are major/minor triad
                chord = music21.chord.Chord(note_names)
                chord = music21.chord.Chord.sortAscending(chord, inPlace=False)
                if any([
                    chord.isTriad(),
                    chord.isAugmentedSixth(),
                    chord.isAugmentedTriad(),
                    chord.isDiminishedSeventh(),
                    chord.isDiminishedTriad(),
                    chord.isDominantSeventh(),
                    chord.isFrenchAugmentedSixth(),
                    chord.isGermanAugmentedSixth(),
                    chord.isHalfDiminishedSeventh(),
                    chord.isItalianAugmentedSixth(),
                    chord.isSeventh(),
                    chord.isSwissAugmentedSixth() 
                ]):
                    # print(chord.commonName) 
                    is_interesting = False
    
    if is_interesting:
        return False
    else:
        for note in notesAndRests:
            uninteresting_notes.add(id(note))
        return True

class MotifAnalyzer(object):

    def __init__(self, score):
        self.score = score

        # preprocess the score
        self.score.toSoundingPitch(inPlace=True)
        for measure in self.score.recurse(skipSelf=True).getElementsByClass(music21.stream.Measure):
            measure.removeByClass(
                [music21.layout.PageLayout, music21.layout.SystemLayout])

        self.notegram_groups = defaultdict(lambda: [])

        self.notegram_groups = defaultdict(lambda: [])
        for part in self.score.recurse().getElementsByClass('Part'):
            for notegram in self.load_notegrams_by_part(part):
                self.notegram_groups[str(notegram)].append(notegram)

        self.init_num_of_cluster = math.ceil(len(self.notegram_groups) / 10) # what should this be?

    def load_notegrams_by_part(self, part):

        measures = list(part.getElementsByClass('Measure'))

        vids = set(str(v.id) for measure in measures for v in measure.voices)
        vids.add('1')  # Default voice

        result = []
        for vid in sorted(vids):
            note_list = []
            vid_list = []
            for measure in measures:
                if measure.voices:
                    voice = next(
                        (v for v in measure.voices if str(v.id) == vid), None)
                    real_vid = vid
                else:
                    voice = measure
                    real_vid = '1'

                if voice is not None:
                    for n in voice.notesAndRests:
                        offset = measure.offset + n.offset
                        note_list.append((offset, n))
                        vid_list.append(real_vid)

            notegram_it = zip(*[note_list[i:] for i in range(NGRAM_SIZE)])
            vid_it = zip(*[vid_list[i:] for i in range(NGRAM_SIZE)])

            for notegram, vidgram in zip(notegram_it, vid_it):

                if vid not in vidgram:
                    continue

                # reject notegram if starting with a tie
                if notegram[0][1].tie is not None and notegram[0][1].tie.type in ('continue', 'stop'):
                    continue

                # reject notegram containing a rest
                if any(n[1].isRest for n in notegram):
                    continue

                # reject notegram containing >= quarter rest
                if any((note[1].isRest and note[1].duration.quarterLength -
                        (1.0 - 1e-2) >= 0.0) for note in notegram):
                    continue

                # reject notegram with note of 0 length (it should have been a Rest)
                if any((note[1].duration.quarterLength < 1e-2) for note in notegram):
                    continue

                if is_notegram_unintersting(notegram):
                    continue

                # if the notegram contain notes with tie, add more note at the end to make up for it
                across_tie_count = 0
                for _, curr_note in notegram:
                    if has_across_tie_to_next_note(curr_note, curr_note.next(('Rest', 'Note'))):
                        across_tie_count += 1

                notegram = list(notegram)
                curr_offset, curr_note = notegram[0]
                last_offset, last_note = notegram[-1]
                last_note = last_note.next(('Rest', 'Note'))
                # add one more note for one tie added
                while across_tie_count > 0:
                    across_tie_count -= 1
                    if isinstance(last_note, music21.note.Note):
                        last_offset += last_note.quarterLength
                        notegram.append((last_offset, last_note))
                        if has_across_tie_to_next_note(last_note, last_note.next(('Rest', 'Note'))):
                            across_tie_count += 1
                        last_note = last_note.next(('Rest', 'Note'))
                    else:
                        break

                notegram = tuple(notegram)

                result.append(Notegram(
                    list(i[1] for i in notegram),
                    list(i[0] for i in notegram)))

        return result

    def is_clusters_overlapping(self, first, second):
        first = sum((self.notegram_groups[i] for i in first), [])
        second = sum((self.notegram_groups[i] for i in second), [])

        if len(first) > len(second):
            first, second = second, first

        first = [(notegram.get_note_offset_by_index(
            0), notegram.get_note_offset_by_index(-1))
            for notegram in first]

        second = [(notegram.get_note_offset_by_index(
            0), notegram.get_note_offset_by_index(-1))
            for notegram in second]

        first_intervals = [Interval(*i) for i in first]
        second_intervals = [Interval(*i) for i in second]

        if len(first_intervals) > len(second_intervals):
            first_intervals, second_intervals = second_intervals, first_intervals

        count = 0
        tree = IntervalTree(second_intervals)
        for interval in first_intervals:
            if tree.search(*interval):
                count += 1

        return count / len(first_intervals) >= OVERLAP_THRESHOLD

    def cluster(self, verbose=False):
        notegram_group_list = [i for _, i in self.notegram_groups.items()]
        distance_matrix = get_dissimilarity_matrix(notegram_group_list)

        if verbose:
            print(distance_matrix)
            print("-----------------------\n")

        models = AgglomerativeClustering(n_clusters=self.init_num_of_cluster, affinity='precomputed', linkage='complete')
        db = models.fit(distance_matrix)

        notegram_group_by_label = defaultdict(lambda: [])
        for i, label in enumerate(db.labels_):
            if label == -1:
                continue
            notegram_group_by_label[label].append(self.notegram_groups[i])

        clusters = defaultdict(lambda: [])

        for group in set(i for i in db.labels_) - {-1}:
            for label, notegram_group in zip(db.labels_, self.notegram_groups):
                if label == group:
                    clusters[str(label)].append(notegram_group)

        num_of_group_in_cluster = defaultdict(lambda: 0)
        for label, cluster in clusters.items():
            for notegram_group in cluster:
                num_of_group_in_cluster[label] += len(self.notegram_groups[notegram_group])
        
        sd = np.std(np.array(list(i for _, i in num_of_group_in_cluster.items())))
        mean = sum((i for _, i in num_of_group_in_cluster.items()), 0) / len(num_of_group_in_cluster)

        if verbose:
            for label, cluser in clusters.items():
                print(label, ':', (num_of_group_in_cluster[label] - mean) / sd)

        clusters = { label: cluster for label, cluster in clusters.items() if num_of_group_in_cluster[label] >= MIN_CLUSTER_SIZE and (num_of_group_in_cluster[label] - mean) / sd >= Z_SCORE_THRESHOLD }

        # merge overlapping clusters together
        queue = list(clusters.keys())

        while len(queue) > 0:
            first_label = queue.pop(0)
            for second_label in queue:
                if self.is_clusters_overlapping(clusters[first_label], clusters[second_label]):
                    if verbose:
                        print('Merging cluster', first_label, 'and', second_label)
                    clusters[first_label] += clusters[second_label]
                    del clusters[second_label]
                    queue.remove(second_label)
                    queue.append(first_label)
                    break

        new_clusters = {}
        i = 0
        for _, cluster in clusters.items():
            new_clusters[str(i)] = cluster
            i += 1

        if verbose:
            for label, cluster in new_clusters.items():
                print('\n\n~~~ cluster [' + label + '] ~~~\n')
                for notegram_group in cluster:
                    print(str(len(self.notegram_groups[notegram_group])).ljust(4), self.notegram_groups[notegram_group][0].to_nice_string())

        return new_clusters

    def highlight_notegram_group(self, notegram_group, label):
        label_index = int(label)
        first_label = '(' + label + ')'
        label = '[' + label + ']'
        for value in self.notegram_groups[notegram_group]:
            note_list = value.get_note_list()
            for i, note in enumerate(note_list):
                note.style.color = 'red'
                item = [i for i, lyric in enumerate(note.lyrics) if lyric.text == label or lyric.text == first_label]
                if len(note.lyrics) != 0 and len(item) != 0:
                    note.lyrics.pop(item[0])
                note.insertLyric(first_label if i == 0 else label, label_index)
                    

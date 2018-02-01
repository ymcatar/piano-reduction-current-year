import music21
from collections import defaultdict
from util import isNote, isChord

# Constants
MAX_CONCURRENT_NOTE = 4
MAX_PITCH_STEP_CHANGE = 8

class PostProcessorAlgorithms(object):

    @staticmethod
    def concurrent_notes(group_tuple):
        offset, group = group_tuple
        num_of_notes = 0

        # determine the number of notes playing at each time instance
        for noteOrChord in group:
            if isNote(noteOrChord):
                num_of_notes += 1
            elif isChord(noteOrChord):
                num_of_notes += noteOrChord.chordTablesAddress.cardinality

        # highlight all time instance with note playing >= MAX_CONCURRENT_NOTE
        # if num_of_notes >= MAX_CONCURRENT_NOTE:
            # for noteOrChord in group:
                # highlight(noteOrChord, 'red')

        return group

    @staticmethod
    # FIXME: probably a bad fix musically, refine later
    def fix_concurrent_notes(group):
        note_num = 0
        name_with_octave_map = defaultdict(lambda: [])
        name_map = defaultdict(lambda: [])
        for noteOrChord in group:
            if isNote(noteOrChord):
                note_num += 1
                name_with_octave_map[noteOrChord.pitch.nameWithOctave].append(noteOrChord)
                name_map[noteOrChord.pitch.name].append(noteOrChord)
            elif isChord(noteOrChord):
                for note in noteOrChord._notes:
                    note_num += 1
                    name_with_octave_map[note.pitch.nameWithOctave].append(note)
                    name_map[note.pitch.name].append(note)
        # remove duplicate notes with same pitch + octave
        for _, items in name_with_octave_map.items():
            if len(items) > 1:
                for item in items[1:]:
                    note_num -= 1
                    # score.remove(item)
                    highlight(item, 'blue')
        # remove notes with same pitch class
        for _, items in name_map.items():
            while len(items) > 1 and note_num > MAX_CONCURRENT_NOTE:
                # delete at most (n - 1) notes
                # score.remove(items.pop(0))
                highlight(items.pop(0), 'blue')
                note_num -= 1

    @staticmethod
    # FIXME: need some sort of "finger assignment"
    def large_hand_movement(measure):
        sites = []
        notes = list(measure.recurse().getElementsByClass(('Rest', 'Note', 'Chord')))
        note_pairs = list((notes[i], notes[i+1]) for i, _ in enumerate(notes[:-1]))
        for (first, last) in note_pairs:
            first_notes = first._notes if isChord(first) else [first] if isNote(first) else []
            last_notes = last._notes if isChord(last) else [last] if isNote(last) else []
            min_pair = None
            min_val = None
            for x in first_notes:
                for y in last_notes:
                    if min_val is None or abs(x.pitch.ps - y.pitch.ps) < min_val:
                        min_pair = [x, y]
                        min_val = abs(x.pitch.ps - y.pitch.ps)

        if min_val is not None and min_val >= MAX_PITCH_STEP_CHANGE:
            sites.append(min_pair)

        for pair in sites:
            first, last = pair
            # highlight(first, '#00ff00')
            # highlight(last, '#00ff00')

        return sites

    @staticmethod
    def fix_large_hand_movement(measure):
        pass
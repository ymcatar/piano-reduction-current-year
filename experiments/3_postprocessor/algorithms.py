import music21
from collections import defaultdict
from util import isNote, isChord, highlight

# Constants
MAX_CONCURRENT_NOTE = 4

class PostProcessorAlgorithms(object):

    @staticmethod
    def concurrent_notes(group):

        merged_offset_map = defaultdict(lambda: [])
        sites = []

        for measure in group:
            offset_map = measure.offsetMap()
            for item in offset_map:
                merged_offset_map[item.offset].append(item.element)

            # determine the number of notes playing at each time instance
            num_of_notes_at_offset = defaultdict(lambda: 0)
            for offset, notes in merged_offset_map.items():
                for noteOrChord in notes:
                    if isNote(noteOrChord):
                        num_of_notes_at_offset[offset] += 1
                    elif isChord(noteOrChord):
                        num_of_notes_at_offset[offset] += noteOrChord.chordTablesAddress.cardinality

            # highlight all time instance with note playing >= MAX_CONCURRENT_NOTE
            for offset, count in num_of_notes_at_offset.items():
                if count >= MAX_CONCURRENT_NOTE:
                    sites.append(merged_offset_map[offset])
                    for noteOrChord in merged_offset_map[offset]:
                        highlight(noteOrChord, 'red')
                    # attempt to fix
                    # ...
                else:
                    del merged_offset_map[offset]

        return sites

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


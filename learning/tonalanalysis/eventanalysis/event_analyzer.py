import math
import music21
import os
from .event import *
from .chord_flow import FlowState


def remove_identical(list):
    """remove any duplicated elements within a list"""
    seen = set()
    seen_add = seen.add
    return [x for x in list if not (x in seen or seen_add(x))]

class EventAnalyzer:

    @property
    def score(self):
        return self._score

    @property
    def event(self):
        return self._event

    @property
    def event_mod(self):
        return self._event_mod

    @property
    def number_of_measures(self):
        return self._number_of_measures

    @property
    def chord_data(self):
        return self._chord_data

    @property
    def recognized(self):
        return self._recognized

    @property
    def event_container(self):
        return self._event_container

    @property
    def flow_state(self):
        return self._flow_state

    @property
    def measures_data(self):
        return self._measures_data

    def __init__(self, score, flow):
        self._event = []
        self._event_mod = []
        self._recognized = []
        self._score = score
        self._number_of_measures = len(self._score.getElementsByClass(music21.stream.Part)[0].getElementsByClass(music21.stream.Measure))
        self._chord_data = MusicManager.get_instance().make_chord_database()
        self._event_container = EventContainer()
        self._flow_state = flow
        self._measures_data = []
        self._modulations = []

    def analyze(self):
        for i in range(1,self._number_of_measures+1):
            measure = self._score.measure(i).flat.notes

            # build a list of offset numbers
            event_group = []
            for note in measure:
                event_group.append(note.offset)
            corr_group = remove_identical(event_group)
            print("{} {}".format(i, corr_group))

            # extract notes from measures to build a list of events sorted by offset
            single_measure = []
            for offset in corr_group:
                # building a single event
                single_event = []
                for note_obj in self._score.measure(i).flat.notes.getElementsByOffset(offset, mustBeginInSpan=True):
                    if isinstance(note_obj, music21.chord.Chord):
                        for note in note_obj:
                            single_event.append(note.name)
                    else:
                        single_event.append(note_obj.name)
                # append the single event without any duplicated notes
                single_measure.append(remove_identical(single_event))

            # for each events, add pitch classes from 1 event before and 1 event after within the measure
            step2_event = []
            for j in range(len(single_measure)):
                step2 = []
                if len(single_measure) == 1:
                    step2 = single_measure[j]
                else:
                    if j == 0:
                        step2 += single_measure[j]
                        step2 += single_measure[j+1]
                    elif j == len(single_measure) - 1:
                        step2 += single_measure[j]
                        step2 += single_measure[j-1]
                    else:
                        step2 += single_measure[j+1]
                        step2 += single_measure[j]
                        step2 += single_measure[j-1]
                step2_event.append(remove_identical(step2))

            # try matching chords
            parsed = []
            parsed.append(len(corr_group))
            for event in step2_event:
                matched = False
                partial_matched = False
                for chord in self._chord_data:
                    if set(event) == set(chord):
                        matched = True
                        parsed.append(''.join(event))
                        break
                if not matched:
                    for chord in self._chord_data:
                        if set(event) <= set(chord):
                            partial_matched = True
                            parsed.append(''.join(chord))
                            break
                if not matched and not partial_matched:
                    parsed.append([])

            # correction


            # append all results
            self._recognized.append(parsed)
            self._event_mod.append(step2_event)
            self._event.append(single_measure)

        # print(self._recognized)

        for n in range(len(self._recognized)):
            incline = 1
            # print("n: ", n)
            for i in range(0,int(math.ceil(math.log(self._recognized[n][0],2)))):
                # print("i: ", i)
                for j in range(0,self._recognized[n][0],incline*2):
                    if(len(self._recognized[n]) > j+1+incline):
                        temp = []
                        if((not self._recognized[n][j+1]) and (self._recognized[n][j+1+incline])):
                            temp = self._recognized[n][j+1+incline]
                        if ((self._recognized[n][j+1]) and (not self._recognized[n][j+1+incline])):
                            temp = self._recognized[n][j+1]
                        # print(j+1, j+incline+1, temp)
                        # print(self._recognized[n][j+1], self._recognized[n][j+incline+1])
                        if (temp):
                            for k in range(0,incline*2):
                                if(len(self._recognized[n])> j+k+1):
                                    self._recognized[n][j+k+1] = temp
                            # print(k)
                incline = incline*2

    def set_measure_by_data(self, measure_data):
        # To improve speed on data input by setting the measure_data and number of measure
        self._measures_data = measure_data
        self._number_of_measures = len(measure_data)

    def set_measure_by_score(self, scoreObj):
        measure_data = {}
        for part in scoreObj.score:
            for voice in part.voices:
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    for noteObj in measure.notes:
                        if measure.measureNumber not in measure_data:
                            measure_data[measure.measureNumber] = []
                        measure_data[measure.measureNumber].append(noteObj)
        self.set_measure_by_data(measure_data)

    def analyze_oo(self, num_of_flow = 4, tolerance = -0.5):
        global_index = 0
        for i in range(1, self._number_of_measures + 1):
            measure = []
            if(self._measures_data == []):
                measure = self._score.measure(i).flat.notes
            else:
                measure = self._measures_data[i-1]
            # build a list of offset numbers
            dict = {}
            corr_group = []
            for note_obj in measure:
                key = note_obj.offset
                if key not in dict:
                    dict[key] = []
                    corr_group.append(note_obj.offset)
                if isinstance(note_obj, music21.chord.Chord):
                    for note in note_obj:
                        dict[key].append((note.name, note.octave, note.duration.quarterLength))
                        if note.duration.quarterLength == 2.0:
                            half_key = note_obj.offset + 1.0
                            if half_key not in dict:
                                dict[half_key] = []
                                corr_group.append(half_key)
                            dict[half_key].append((note.name, note.octave, 1.0))
                else:
                    dict[key].append((note_obj.name, note_obj.octave, note_obj.duration.quarterLength))
                    if note_obj.duration.quarterLength == 2.0:
                        half_key = note_obj.offset + 1.0
                        if half_key not in dict:
                            dict[half_key] = []
                            corr_group.append(half_key)
                        dict[half_key].append((note_obj.name, note_obj.octave, 1.0))
            event_group = EventGroup()
            event_group.measure = i
            event_group.number_of_events = len(corr_group)
            corr_group.sort()
            # extract notes from measures to build a list of events sorted by offset
            for corr in corr_group:
                single_event = []
                for key in dict:
                    if key > corr:
                        continue
                    for note in dict[key]:
                        if(note[2]+key > corr):
                            single_event.append((note[0],note[1]))
                bass_note = self.find_bass_note(single_event)
                # append the single event without any duplicated notes
                event = Event(single_event, bass_note, corr, corr_group.index(corr), global_index, event_group,self.event_container)
                event_group.events.append(event)
                global_index = global_index + 1
            self.event_container.event_groups.append(event_group)

        for event_group in self.event_container.event_groups:
            event_group.acoustic_lasting()
            event_group.exact_match(self._flow_state)
            event_group.match_candidates()
            event_group.match_partial(self._flow_state)
            event_group.match_candidates()
        self.eliminate_no_out_chord()


        self._modulations = self._flow_state.get_modulations(self, num_of_flow, tolerance)
        for event_group in self.event_container.event_groups:
            event_group.select_chord(self._modulations)
            event_group.resolve_seventh(self._flow_state)
            event_group.resolve_dissonance()
            event_group.resolve_seventh(self._flow_state)
            event_group.resolve_inversion()

        self._modulations = self._flow_state.get_modulations(self, num_of_flow, tolerance)
        self.fix_modulation_format()

    def get_all_modulations(self):
        return self._modulations

    def find_bass_note(self, note_tuple):
        return EventGroup.find_bass_note(note_tuple)

    def sort_single_event_notes(self, single_event):
        return EventGroup.sort_single_event_notes(single_event)

    def eliminate_no_out_chord(self):
        events = self.event_container.events
        before = events[-1]
        if before.matched_chord == []:

            previous = before.find_previous_chord()
            if previous == -1:
            # Return if no unempty previous chord
                return

            previous = before.global_index - previous
            before = events[previous]

        exist_list = before.matched_chord

        for after in reversed(events[:-2]):
            if after.matched_chord != []:
                if self.flow_state.unequal_matched_chord_event(after, before):

                    before._matched_chord = []
                    for chord in exist_list:
                        before._matched_chord.append(before.resolve_base_chord(chord))

                    exist_list = []
                    all_flow_results = self.flow_state.get_event_all_flow_results(after, before)
                    for flow in all_flow_results:
                        if flow[1] != {}:
                            exist_list.append(flow[0].split(','))
                    before = after

                else:
                    after._matched_chord = []
                    for chord in exist_list:
                        after._matched_chord.append(after.resolve_base_chord(chord))

    def fix_modulation_format(self):
        """ Fix modulation format to fit postprocessor"""
        if self._modulations is None:
            self._modulations = []
            return

        output = []
        for modulation in self._modulations:
            key = modulation[2].split(',')
            quality = True if key[1] == 'Major' else False
            output.append([modulation[0], modulation[1], key[0], modulation[5], modulation[6], quality])
        self._modulations = output

    def print_out(self):
        # print(self._event)
        # print(self._event_mod)
        print(self._recognized)


# Unit test main method
if __name__ == "__main__":
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_scores/SQ-Original-fixed.xml")
    s = music21.converter.parse(file_path)
    f = FlowState()
    event_analyzer = EventAnalyzer(s, f)
    event_analyzer.analyze_oo()
    event_analyzer.event_container.display()

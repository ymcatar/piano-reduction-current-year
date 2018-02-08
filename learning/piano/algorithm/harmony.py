from .base import ReductionAlgorithm, get_markings
from ...tonalanalysis.eventanalysis.chord_flow import FlowState
from ...tonalanalysis.eventanalysis.event_analyzer import EventAnalyzer

from music21 import chord, stream


_flow_state = None


def get_flow_state():
    global _flow_state
    if not _flow_state:
        _flow_state = FlowState()
    return _flow_state
    ...


class Harmony(ReductionAlgorithm):
    dtype = 'bool'

    def run(self, score_obj):
        '''
        Use the results of tonal analysis to mark dissonance.

        It is called "Harmony" since it should eventually mark all features from
        harmonic analysis.
        '''
        score = score_obj.score
        event = EventAnalyzer(score, get_flow_state())

        # Prepare Measure Data for EventAnalyzer
        event.set_measure_by_score(score_obj)

        # Start Event Analyze
        event.analyze_oo()

        # Mark Dissonance
        for part in score.parts:
            for midx, measure in enumerate(part.getElementsByClass(stream.Measure)):
                for voice in measure.voices:
                    current_event_group = event.event_container.event_groups[midx]
                    if not current_event_group.events:
                        continue
                    i = 0
                    for n in voice.notes:
                        # Some indices might not be used, since each voice
                        # may not have notes onset at all events.
                        while current_event_group.events[i].offset != n.offset:
                            i = i + 1

                        current_note = current_event_group.events[i]
                        if isinstance(n, chord.Chord):
                            for j in n:
                                get_markings(j)[self.key] = \
                                    j.pitch.name in current_note.dissonance
                        else:
                            get_markings(n)[self.key] = \
                                n.pitch.name in current_note.dissonance

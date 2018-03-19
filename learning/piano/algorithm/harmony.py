from .base import FeatureAlgorithm, get_markings
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


class Harmony(FeatureAlgorithm):
    dtype = 'bool'
    @property
    def all_keys(self):
        return ['{}_{!s}'.format(self.key, s) for s in self.sub_keys]

    def __init__(self, *, sub_keys=('dissonance',)):
        assert set(sub_keys) <= {'base', '3rd', '5th', 'dissonance'}
        self.sub_keys = sub_keys

    def run(self, score_obj):
        '''
        Use the results of tonal analysis to mark dissonance and chord notes.
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
                for voice in measure.voices or [measure]:
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
                        notes = iter(n) if isinstance(n, chord.Chord) else [n]
                        if not current_note.matched_chord:
                            continue
                        mc = current_note.matched_chord[0]
                        # Workaround for bug where tonal analyzer marks
                        # everything as dissonance
                        if not any(p in current_note.corrected_pitch_classes for p in mc):
                            continue
                        for j in notes:
                            for pitch, sk in zip(mc, ('base', '3rd', '5th')):
                                if sk in self.sub_keys:
                                    get_markings(j)[self.key + '_' + sk] = \
                                        j.pitch.name == pitch
                            if 'dissonance' in self.sub_keys:
                                get_markings(j)[self.key + '_dissonance'] = \
                                    j.pitch.name in current_note.dissonance

    @property
    def args(self):
        return [], {'sub_keys': self.sub_keys}

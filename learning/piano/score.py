import music21
from music21 import meter, note, stream
import numpy
from collections import defaultdict
from itertools import count


def _group_by_voices(part):
    '''
    Given a part, return all voices each as a Stream of measures.

    Normally, Music21 puts voices under measures, but sometimes we want to
    iterate a voice across the piece.
    '''
    voices = defaultdict(lambda: stream.Voice())

    for m in part.getElementsByClass(stream.Measure):
        for measure_voice in m.voices:
            voice_measure = m.cloneEmpty(derivationMethod='group_by_voices')
            voice_measure.mergeElements(measure_voice)
            voices[measure_voice.id].insert(m.offset, voice_measure)

    for vid, voice in voices.items():
        voice.id = vid

    return sorted(voices.values(), key=lambda v: v.id)


class ScoreObject(object):
    @property
    def score(self):
        return self._score

    def __init__(self, score):
        '''
        Preprocess the score. The input hierarchy is:

            Stream -> Part -> Measure (maybe -> Voice)

        When there is only one voice in the measure, the Voice object may not
        exist. We rectify this by requiring Voice objects under the measure.
        If a voice does not exist in a certain measure, we create a Voice filled
        with rests.
        '''
        def preprocess_measure(measure, vids):
            result = measure.cloneEmpty(derivationMethod='preprocess')

            vids_in_measure = list(v.id for v in measure.voices)

            if not vids_in_measure:
                voice = stream.Voice(id='1')
                voice.mergeAttributes(measure)
                for elem in measure:
                    if isinstance(elem, note.GeneralNote):
                        voice.insert(elem)
                    else:
                        # Things like TimeSignature, MetronomeMark, etc.
                        result.insert(elem)
                result.insert(0, voice)
            else:
                result.mergeElements(measure)
                for vid in vids.difference(vids_in_measure):
                    voice = stream.Voice(id=vid)
                    voice.insert(0, note.Rest(measure.highestTime))

            return result

        def preprocess_part(part):
            result = part.cloneEmpty(derivationMethod='preprocess')

            # Find all voices ids
            vids = {1}
            for m in part.getElementsByClass(stream.Measure):
                for v in m.voices:
                    vids.add(v.id)

            for elem in part:
                if isinstance(elem, stream.Measure):
                    result.insert(elem.offset, preprocess_measure(elem, vids))
                else:
                    result.insert(elem)
            return result

        result = score.cloneEmpty(derivationMethod='preprocess')
        for elem in score:
            if isinstance(elem, stream.Part):
                result.insert(elem.offset, preprocess_part(elem))
            else:
                result.insert(elem)

        self.original_score = score
        self._score = result

        # .measures also collects the context information, e.g. time signature,
        # to each measure. Each item is a score.
        self.by_bar = []
        for i in count(0):
            subscore = result.measure(i)
            # Measure 0 is the pickup (partial) measure and may not exist
            if i > 0 and not subscore.recurse(skipSelf=False).getElementsByClass('Measure'):
                break
            self.by_bar.append(subscore)

        self.voices_by_part = []
        for part in result.parts:
            self.voices_by_part.append(_group_by_voices(part))

    def merge(self, parts=[], reduced=True, measures=None):
        result = music21.stream.Part()
        for pid in parts:
            part = self.score[pid]
            partPs = []

            for voice in part.voices:
                retVoice = music21.stream.Voice()

                mid = 0
                for measure in voice.getElementsByClass(music21.stream.Measure):
                    retMeasure = music21.stream.Measure()
                    notes = []
                    lastNote = None

                    retMeasure.timeSignature = measure.timeSignature
                    retMeasure.keySignature = measure.keySignature

                    for noteObj in measure.notesAndRests:
                        if isinstance(noteObj, music21.note.Rest):
                            if isinstance(lastNote, music21.note.Rest):
                                lastNote.duration = music21.duration.Duration(
                                    lastNote.quarterLength + noteObj.quarterLength)
                            else:
                                lastNote = music21.note.Rest(music21.note.Rest(
                                    duration=music21.duration.Duration(noteObj.quarterLength)))
                                lastNote.duration = music21.duraiton.Duration(
                                    noteObj.quarterLength)
                                notes.append(lastNote)
                        else:
                            if isinstance(noteObj, music21.chord.Chord):
                                chords = []
                                for ch_note in noteObj:
                                    if ch_note.align >= 0.5 or not reduced:
                                        chords.append(ch_note.nameWithOctave)
                                if len(chords) == 0:
                                    if isinstance(lastNote, music21.note.Rest):
                                        lastNote.duration = music21.duration.Duration(
                                            lastNote.quarterLength + noteObj.quarterLength)
                                    else:
                                        lastNote = music21.note.Rest(music21.note.Rest(
                                            duration=music21.duration.Duration(noteObj.quarterLength)))
                                        lastNote.duration = music21.duraiton.Duration(
                                            noteObj.quarterLength)
                                        notes.append(lastNote)
                                else:
                                    if len(chords) == 1:
                                        lastNote = music21.note.Note(music21.note.Note(
                                            chords[0], duration=music21.duration.Duration(noteObj.quarterLength)))
                                        lastNote.duration = music21.duraiton.Duration(
                                            noteObj.quarterLength)
                                        notes.append(lastNote)
                                    else:
                                        lastNote = music21.note.Chord(music21.chord.Chord(
                                            chords, duration=music21.duration.Duration(noteObj.quarterLength)))
                                        lastNote.duration = music21.duraiton.Duration(
                                            noteObj.quarterLength)
                                        notes.append(lastNote)
                            else:
                                if isinstance(noteObj, music21.note.Note) and (noteObj.align >= 0.5 or not reduced):
                                    lastNote = music21.note.Note(music21.note.Note(
                                        noteObj.nameWithOctave, duration=music21.duration.Duration(noteObj.quarterLength)))
                                    lastNote.duration = music21.duraiton.Duration(
                                        noteObj.quarterLength)
                                    lastNote.tie = noteObj.tie
                                    notes.append(lastNote)
                                else:
                                    if isinstance(lastNote, music21.note.GeneralNote):
                                        lastNote.duration = music21.duration.Duration(
                                            lastNote.quarterLength + noteObj.quarterLength)
                                    else:
                                        lastNote = music21.note.Rest(music21.note.Rest(
                                            duration=music21.duration.Duration(noteObj.quarterLength)))
                                        lastNote.duration = music21.duraiton.Duration(
                                            noteObj.quarterLength)
                                        notes.append(lastNote)
                    for nt in notes:
                        retMeasure.append(nt)
                        if isinstance(nt, music21.chord.Chord):
                            for noteObj in nt:
                                partPs.append(noteObj.ps)
                        elif isinstance(nt, music21.note.Note):
                            partPs.append(nt.ps)

                    if measures is None or mid in measures:
                        retVoice.append(retMeasure)
                    mid = mid + 1

                result.insert(0, retVoice)

            median = numpy.median(partPs)

            clef = music21.clef.TrebleClef()
            if median < 60:
                clef = music21.clef.BassClef()

            for voice in result.voices:
                voice.measure(1).clef = clef
        return result

    # END: def merge(self, parts, reduced)
    # --------------------------------------------------------------------------

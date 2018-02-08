from music21 import converter, layout, note, stream
from collections import defaultdict
from itertools import zip_longest
import logging
import numpy as np
from .algorithm.base import iter_notes


logger = logging.getLogger('learning.piano.score')
logger.setLevel(logging.WARNING)

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

    return sorted(voices.values(), key=lambda v: str(v.id))


class ScoreObject(object):
    '''
    Represents a preprocessed musical score that can be used for the piano
    reduction system. This also defines a standardized way to convert the score
    into matrix representations.
    '''
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

            vids_in_measure = set(str(v.id) for v in measure.voices)

            if not vids_in_measure:
                voice = stream.Voice(id='1')
                voice.mergeAttributes(measure)
                for elem in measure:
                    if isinstance(elem, note.GeneralNote):
                        voice.insert(elem)
                    else:
                        # Things like TimeSignature, MetronomeMark, etc.
                        if elem.offset == 0:
                            result.insert(elem)
                        else:
                            voice.insert(elem)
                result.insert(0, voice)
                vids_in_measure.add('1')
            else:
                result.mergeElements(measure)

            for vid in vids.difference(vids_in_measure):
                voice = stream.Voice(id=vid)
                rest = note.Rest(duration=measure.barDuration)
                rest.hideObjectOnPrint = True
                voice.insert(0, rest)
                result.insert(0, voice)

            # Remove page breaks so that it doesn't mess with our output layout
            result.removeByClass([layout.PageLayout, layout.SystemLayout])

            return result

        def preprocess_part(part):
            result = part.cloneEmpty(derivationMethod='preprocess')

            # Find all voices ids
            vids = {'1'}
            for m in part.getElementsByClass(stream.Measure):
                for v in m.voices:
                    vids.add(str(v.id))

            for elem in part:
                if isinstance(elem, stream.Measure):
                    result.insert(elem.offset, preprocess_measure(elem, vids))
                else:
                    result.insert(elem)
            return result

        logger.info('Group voice')
        result = score.cloneEmpty(derivationMethod='preprocess')
        for elem in score:
            if isinstance(elem, stream.Part):
                result.insert(elem.offset, preprocess_part(elem))
            else:
                result.insert(elem)

        logger.info('Instrument transposition')
        # Remove instrument transposition
        result.toSoundingPitch(inPlace=True)

        self.original_score = score
        self._score = result

        logger.info('Bar indexing')
        # Group each bar into a Score => Part -> Measure object.
        self.by_bar = []
        iters = [part.getElementsByClass(stream.Measure)
                 for part in result.parts]
        for i, measures in enumerate(zip_longest(*iters)):
            assert all(measures), 'Measures missing at index {}'.format(i)
            bar = result.cloneEmpty(derivationMethod='by_bar')
            for part, m in zip(result.parts, measures):
                p = part.cloneEmpty(derivationMethod='by_bar')
                p.insert(0, m)
                bar.insert(0, p)
            self.by_bar.append(bar)

        logger.info('Voice grouping')
        self.voices_by_part = []
        for part in result.parts:
            self.voices_by_part.append(_group_by_voices(part))

        self._len = sum(1 for _ in self)

        self._index = {}
        for i, n in enumerate(self.notes):
            self._index[id(n)] = i

        logger.info('Done')

    @property
    def score(self):
        return self._score

    @classmethod
    def from_file(cls, fp, *args, **kwargs):
        '''
        Create a ScoreObject from a file. Uses music21.converter.parseFile to
        do so.
        '''
        score = converter.parseFile(fp, *args, **kwargs)

        # Make sure the file is not something else, e.g. an Opus
        assert isinstance(score, stream.Score), 'File is not a single score!'

        return cls(score)

    def __iter__(self):
        # deprecated
        return self.notes

    def __len__(self):
        return self._len

    @property
    def notes(self):
        '''
        Return an iterator that yields the list of note objects in the order
        used in the matrix representation.
        '''
        return iter_notes(self.score, recurse=True)

    def extract(self, key, dtype, **kwargs):
        '''
        Extract the corresponding vector from an annotation in a score.

        default: The default value to use if the key does not exist in a Note.
        '''
        # We use kwargs for default so that we can distinguish None and unspecified
        out = np.empty(len(self), dtype=dtype)

        for i, n in enumerate(self):
            try:
                out[i] = n.editorial.misc[key]
            except KeyError:
                if 'default' in kwargs:
                    out[i] = kwargs['default']
                else:
                    raise

        return out

    def annotate(self, vector, key, mapping=None):
        '''
        Annotate the given vector to the score.
        '''
        if mapping is None:
            assert len(vector) == len(self)
            mapping = range(len(vector))
        for i, n in zip(mapping, self):
            n.editorial.misc[key] = vector[i]

    def index(self, n):
        '''
        Returns the index of a note.
        '''
        return self._index[id(n)]

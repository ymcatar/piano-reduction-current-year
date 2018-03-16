from music21 import converter, layout, stream
from collections import defaultdict
import copy
from itertools import zip_longest
import logging
import numpy as np
from .util import iter_notes, iter_notes_with_offset


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
        for measure_voice in m.voices or [m]:
            voice_measure = m.cloneEmpty(derivationMethod='group_by_voices')
            voice_measure.mergeElements(measure_voice)
            if isinstance(measure_voice, stream.Measure):
                vid = '1'
            else:
                vid = str(measure_voice.id)
            voices[vid].insert(m.offset, voice_measure)

    for vid, voice in voices.items():
        voice.id = vid

    return sorted(voices.values(), key=lambda v: v.id)


class ScoreObject(object):
    '''
    Represents a preprocessed musical score that can be used for the piano
    reduction system. This also defines a standardized way to convert the score
    into matrix representations.
    '''
    def __init__(self, score):
        '''
        Preprocess the score.
        '''
        result = copy.deepcopy(score)

        logger.info('Layout clean-up')
        for measure in score.recurse(skipSelf=False).getElementsByClass(stream.Measure):
            # Remove page breaks so that it doesn't mess with our output layout
            measure.removeByClass([layout.PageLayout, layout.SystemLayout])

        logger.info('Instrument transposition')
        # Remove instrument transposition
        for part in result.parts:
            if part.atSoundingPitch == False:  # atSoundingPitch can be 'unknown'
                part.toSoundingPitch(inPlace=True)

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
            bar.offset = measures[0].offset
            for part, m in zip(result.parts, measures):
                p = part.cloneEmpty(derivationMethod='by_bar')
                p.insert(0, m)
                bar.insert(0, p)
            self.by_bar.append(bar)

        logger.info('Voice indexing')
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

    def iter_offsets(self):
        for bar in self.by_bar:
            note_map = defaultdict(list)
            for n, offset in iter_notes_with_offset(bar, recurse=True):
                note_map[offset].append(n)
            for offset, notes in sorted(note_map.items()):
                yield bar.offset + offset, notes

    def extract(self, key, dtype, **kwargs):
        '''
        Extract the corresponding vector from an annotation in a score.

        default: The default value to use if the key does not exist in a Note.
        '''
        # We use kwargs for default so that we can distinguish None and unspecified
        out = np.empty(len(self), dtype=dtype)

        for i, n in enumerate(self.notes):
            try:
                out[i] = n.editorial.misc[key]
            except KeyError:
                if 'default' in kwargs:
                    out[i] = kwargs['default']
                else:
                    raise

        return out

    def annotate(self, vector, key):
        '''
        Annotate the given vector to the score.
        '''
        for v, n in zip(vector, self.notes):
            n.editorial.misc[key] = v

    def index(self, n):
        '''
        Returns the index of a note.
        '''
        return self._index[id(n)]

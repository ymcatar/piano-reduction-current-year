import datetime
import textwrap
from .alignment import Alignment, align_all_notes, default_key_func
from .pitch_class_onset import (
    align_pitch_class_onset, annotate_pitch_class_onset,
    pitch_class_onset_key_func)
from .min_octave_hand import (
    align_min_octave_hand, annotate_min_octave_hand, LEFT_HAND, RIGHT_HAND)


ALIGNMENT_METHODS = [
    'pitch_class_onset',
    'min_octave_hand',
    ]

DEFAULT_ALIGNMENT_METHOD = 'pitch_class_onset'


def get_alignment_func(method):
    align_func = globals().get('align_' + method)
    assert align_func, 'Alignment method "{}" not found'.format(method)

    return align_func


def align_scores(input_score, output_score,
                 method=DEFAULT_ALIGNMENT_METHOD):
    align_func = get_alignment_func(method)
    align_func(input_score, output_score)


def align_and_annotate_scores(input_score, output_score,
                              method=DEFAULT_ALIGNMENT_METHOD):
    annotate_func = globals().get('annotate_' + method)
    assert annotate_func, 'Alignment method "{}" not found'.format(method)

    description = annotate_func(input_score, output_score)

    description += textwrap.dedent('''\

        Alignment method: {}
        Generated at {}
        '''.format(method, datetime.datetime.now().isoformat()))

    return description


def add_alignment_features_to_writer(writer,
                                     method=DEFAULT_ALIGNMENT_METHOD):
    features = getattr(globals().get('align_' + method), 'features', [])
    for feature in features:
        writer.add_feature(feature)

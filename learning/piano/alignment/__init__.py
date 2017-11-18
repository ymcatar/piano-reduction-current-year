import datetime
import textwrap
from .alignment import Alignment, align_all_notes, default_key_func
from .pitch_class_onset import (
    align_pitch_class_onset, annotate_pitch_class_onset,
    pitch_class_onset_key_func)


ALIGNMENT_METHODS = [
    'pitch_class_onset',
    ]

DEFAULT_ALIGNMENT_METHOD = 'pitch_class_onset'


def align_scores(input_score, output_score,
                 method=DEFAULT_ALIGNMENT_METHOD):
    align_func = globals().get('align_' + method)
    assert align_func, 'Alignment method "{}" not found'.format(method)

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

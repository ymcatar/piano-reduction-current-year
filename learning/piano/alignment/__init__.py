from .alignment import Alignment, align_all_notes, default_key_func
from .base import AlignmentMethod
from .pitch_class_onset import AlignPitchClassOnset
from .min_octave_hand import LEFT_HAND, RIGHT_HAND, AlignMinOctaveHand
from .min_octave_matching import AlignMinOctaveMatching

DEFAULT_ALIGNMENT_METHOD = 'learning.piano.alignment.pitch_class_onset.AlignPitchClassOnset'

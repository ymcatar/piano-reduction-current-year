import textwrap
import numpy as np
from sklearn import metrics
from .piano.algorithm.base import iter_notes
from .piano.alignment import align_all_notes


class ModelMetrics:
    '''
    Model metrics evaluate the model based on its probabilistic predictions.
    '''
    def __init__(self, pre_processor, y_proba, y_test, keys=None):
        self.keys = keys = keys or self.ALL
        self.names = {}

        # Calculate the predictions in multi-class and binary forms.
        y_test_bin = y_test != 0

        if pre_processor.label_type == 'align':
            y_pred_bin = y_pred = y_proba >= 0.5
            y_proba_bin = y_proba
        elif pre_processor.label_type == 'hand':
            y_pred = np.argmax(y_proba, axis=1)
            y_proba_bin = np.sum(y_proba[:, 1:], axis=1)
            y_pred_bin = y_proba_bin >= 0.5
        else:
            raise NotImplementedError()

        def add(key, name, value):
            self.names[key] = name
            setattr(self, key, value)

        if 'accuracy' in keys:
            add('accuracy', 'Accuracy',
                metrics.accuracy_score(y_test, y_pred))
        if 'bin_accuracy' in keys:
            add('bin_accuracy', '(0-1) Accuracy',
                metrics.accuracy_score(y_test_bin, y_pred_bin))
        if 'bin_roc_score' in keys:
            add('bin_roc_score', '(0-1) ROC AUC',
                metrics.roc_auc_score(y_test_bin, y_proba_bin))
        if 'confusion_matrix' in keys:
            add('confusion_matrix', 'Confusion matrix',
                metrics.confusion_matrix(y_test, y_pred))
        if 'bin_confusion_matrix' in keys:
            add('bin_confusion_matrix', '(0-1) Confusion matrix',
                metrics.confusion_matrix(y_test_bin, y_pred_bin))

    ALL = [
        'accuracy',
        'bin_accuracy',
        'bin_roc_score',
        'confusion_matrix',
        'bin_confusion_matrix',
        ]

    def format(self):
        out = []
        for key in self.keys:
            name = self.names[key]
            value = getattr(self, key)
            if isinstance(value, float):
                out.append('{:35} {:>13.4f}'.format(name, value))
            else:
                out.append(name)
                out.append(textwrap.indent('{!r}'.format(value), ' ' * 32))

        out.append('')
        out.append('Note: These metrics do not account for fabricated notes!')

        return '\n'.join(out)

    def __getitem__(self, keys):
        if isinstance(keys, str):
            return getattr(self, keys)
        else:
            return [getattr(self, key) for key in keys]


def pitch_space_offset_key_func(n, offset, precision):
    return (int(offset * precision), n.pitch.ps)


def pitch_class_offset_key_func(n, offset, precision):
    return (int(offset * precision), n.pitch.pitchClass)


class ScoreMetrics:
    '''
    Score metrics evaluate the model based on the generated score.
    '''
    def __init__(self, pre_processor, gen_score, test_score, keys=None):
        self.keys = keys = keys or self.ALL
        self.names = {}

        def calc_e2e_accuracy(gen_score, test_score, alignment):
            def not_tie_continue(n):
                return n.tie is None or n.tie.type == 'start'

            gen_size = sum(not_tie_continue(n) for n in iter_notes(gen_score, recurse=True))
            test_size = sum(not_tie_continue(n) for n in iter_notes(test_score, recurse=True))
            matching_size = sum(not_tie_continue(n) and bool(alignment[n])
                                for n in iter_notes(gen_score, recurse=True))

            total = test_size + gen_size - matching_size
            return matching_size / total if total else 0

        def add(key, name, value):
            self.names[key] = name
            setattr(self, key, value)

        if 'e2e_accuracy' in keys:
            # This establishes a maximal matching between two scores.
            # Note that this also considers staff correspondence.
            alignment = align_all_notes(gen_score, test_score,
                                        key_func=pitch_space_offset_key_func)
            add('e2e_accuracy', 'End-to-end accuracy',
                calc_e2e_accuracy(gen_score, test_score, alignment))

        if 'bin_e2e_accuracy' in keys:
            # This ignores staff correspondence. The result is not a real
            # matching since pitches may duplicate across two staves.
            alignment = align_all_notes(gen_score, test_score, ignore_parts=True,
                                        key_func=pitch_space_offset_key_func)
            add('bin_e2e_accuracy', '(0-1) End-to-end accuracy',
                calc_e2e_accuracy(gen_score, test_score, alignment))

        if 'pc_e2e_accuracy' in keys:
            # This further ignores octave.
            alignment = align_all_notes(gen_score, test_score, ignore_parts=True,
                                        key_func=pitch_class_offset_key_func)
            add('pc_e2e_accuracy', 'Pitch Class 0-1 End-to-end accuracy',
                calc_e2e_accuracy(gen_score, test_score, alignment))

    ALL = [
        'e2e_accuracy',
        'bin_e2e_accuracy',
        'pc_e2e_accuracy',
        ]

    def format(self):
        out = []
        for key in self.keys:
            name = self.names[key]
            value = getattr(self, key)
            if isinstance(value, float):
                out.append('{:35} {:>13.4f}'.format(name, value))
            else:
                out.append(name)
                out.append(textwrap.indent('{!r}'.format(value), ' ' * 32))

        return '\n'.join(out)

    def __getitem__(self, keys):
        if isinstance(keys, str):
            return getattr(self, keys)
        else:
            return [getattr(self, key) for key in keys]

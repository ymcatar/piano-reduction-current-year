import textwrap
import numpy as np
from sklearn import metrics


ALL_METRICS = [
    'accuracy',
    'bin_accuracy',
    'bin_precision',
    'bin_recall',
    'bin_roc_score',
    'confusion_matrix',
    'bin_confusion_matrix',
    ]


class ModelMetrics:
    '''
    Model metrics evaluate the model based on its probabilistic predictions.
    '''
    def __init__(self, reducer, y_proba, y_test, keys=ALL_METRICS):
        self.keys = keys
        self.names = {}

        # Calculate the predictions in multi-class and binary forms.
        y_test_bin = y_test != 0

        if reducer.label_type == 'align':
            y_pred_bin = y_pred = y_proba >= 0.5
            y_proba_bin = y_proba
        elif reducer.label_type == 'hand':
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
        if 'bin_precision' in keys:
            add('bin_precision', '(0-1) Precision, TP/(TP+FP)',
                metrics.precision_score(y_test_bin, y_pred_bin))
        if 'bin_recall' in keys:
            add('bin_recall', '(0-1) Recall, TP/(TP+FN)',
                metrics.recall_score(y_test_bin, y_pred_bin))
        if 'bin_roc_score' in keys:
            add('bin_roc_score', '(0-1) ROC AUC',
                metrics.roc_auc_score(y_test_bin, y_proba_bin))
        if 'confusion_matrix' in keys:
            add('confusion_matrix', 'Confusion matrix',
                metrics.confusion_matrix(y_test, y_pred))
        if 'bin_confusion_matrix' in keys:
            add('bin_confusion_matrix', '(0-1) Confusion matrix',
                metrics.confusion_matrix(y_test_bin, y_pred_bin))

    def format(self):
        out = []
        for key in self.keys:
            name = self.names[key]
            value = getattr(self, key)
            if isinstance(value, float):
                out.append('{:31} {:>13.4f}'.format(name, value))
            else:
                out.append(name)
                out.append(textwrap.indent('{!r}'.format(value), ' ' * 32))

        out.append('')
        out.append('Note: These metrics do not account for fabricated notes!')

        return '\n'.join(out)

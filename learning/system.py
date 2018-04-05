import datetime
import functools
import json
import logging
import sys
import textwrap
from music21 import expressions
from pprint import pformat, pprint
import numpy as np
from .piano.alignment.difference import AlignDifference
from .piano.contraction_writing import create_contracted_score_obj
from .piano.score import ScoreObject
from .piano.pre_processor import PreProcessedEntry, PreProcessedList
from .piano.post_processor import PostProcessor
from .piano.util import dump_algorithm, ensure_algorithm, load_algorithm, import_symbol
from .models.sk import WrappedSklearnModel
from .metrics import ModelMetrics, ScoreMetrics
from . import config
from scoreboard.writer import LogWriter
import scoreboard.writer as writerlib


def add_description_to_score(score, description):
    te = expressions.TextExpression(description)
    te.style.absoluteY = -60
    te.style.fontSize = 8
    score.parts[-1].measure(-1).insert(0, te)


class PianoReductionSystem:
    def __init__(self, *, name, pre_processor, Model):
        assert isinstance(Model, (type, str)), 'Model must be a type or str'
        if isinstance(Model, str):
            Model = import_symbol(Model)
        elif not isinstance(Model, type):
            raise TypeError('Model must be a type or str')

        class_path = Model.__module__ + '.' + Model.__qualname__
        if class_path.startswith('sklearn'):
            # Wrap sklearn models automagically
            Model = functools.partial(WrappedSklearnModel, Model)

        self.name = name
        self.pre_processor = ensure_algorithm(pre_processor)
        self.Model = Model
        self.model = Model(self.pre_processor)

        self.args = [], {
            'name': self.name,
            'pre_processor': dump_algorithm(self.pre_processor),
            'Model': class_path,
            }

    def train(self, entries):
        entries = self._ensure_entries(entries)
        logging.info('Reading sample scores')

        logging.info('Feature set:\n' +
                     textwrap.indent('\n'.join(self.pre_processor.all_keys), '-   '))
        logging.info('Training ML model')

        self.model.fit_structured(entries.X, entries.y)
        metric = self.model.evaluate_structured(entries.X, entries.y)
        logging.info('Training metric = {}'.format(metric))

        logging.info('Done training')

    def save(self, filename):
        logging.info('Saving model to {}'.format(filename))
        self.model.save(filename)

        metadata = {
            'system': dump_algorithm(self)
            }
        with open(filename + '.metadata', 'w') as f:
            json.dump(metadata, f)

    @classmethod
    def load(cls, filename):
        logging.info('Loading model from {}'.format(filename))
        with open(filename + '.metadata', 'r') as f:
            metadata = json.load(f)

        logging.info('Initializing model')
        system = load_algorithm(metadata['system'])

        logging.info('Loading model parameters')
        system.model.load(filename)

        return system

    def get_default_save_file(self):
        return 'trained/' + self.name + '.model'

    def reduce(self, entry):
        entry = self._ensure_entry(entry)
        target = entry.input

        logging.info('Predicting')

        y_proba = self.model.predict_structured(entry.X)
        if self.pre_processor.label_type == 'align':
            y_pred = y_proba.flatten() >= 0.5
        elif self.pre_processor.label_type == 'hand':
            y_pred = np.argmax(y_proba, axis=1)
        else:
            raise NotImplementedError()
        target.annotate(entry.mapping.unmap_matrix(y_pred), self.pre_processor.label_type)

        post_processor = PostProcessor()
        gen_score = post_processor.generate_piano_score(
            target, reduced=True, playable=True, label_type=self.pre_processor.label_type)

        return gen_score, y_proba, y_pred

    def evaluate(self, entry, gen_score, y_proba, y_pred, train=False):
        target = entry.input
        y_test = entry.y

        title = '{}/{}/{}'.format(
            self.name, 'training' if train else 'reduction', entry.name)
        writer = LogWriter(config.LOG_DIR, title=title)
        logging.info('Log directory: {}'.format(writer.dir))
        writer.add_features(self.pre_processor.input_features)
        writer.add_features(self.pre_processor.structure_features)
        writer.add_features(self.pre_processor.output_features)

        target.annotate(
            entry.mapping.parents != np.arange(len(entry.mapping.parents)),
            'contracted')
        writer.add_feature(writerlib.BoolFeature(
            'contracted', help='Whether the note is contracted to some other note', group='input'))

        if entry.output:
            mmetrics = ModelMetrics(self.pre_processor, y_proba, y_test)
            logging.info('Model metrics\n' + mmetrics.format())

            smetrics = ScoreMetrics(self.pre_processor, gen_score, entry.output.score)
            logging.info('Score metrics\n' + smetrics.format())

            # Wrongness marking
            correction = [str(t) if t != p else '' for t, p in zip(y_test.flatten(), y_pred)]
            target.annotate(entry.mapping.unmap_matrix(correction), 'correction')
            writer.add_feature(writerlib.TextFeature(
                'correction', help='The correct label, if wrong', group='output'))

        description = textwrap.dedent('''\
            Command: {}
            Model: {}
            Generated at: {}
            ''').format(' '.join(sys.argv[:]),
                        self.model.describe(),
                        datetime.datetime.now().isoformat())
        add_description_to_score(gen_score, description)
        description += '\nReducer arguments:\n' + pformat(self.pre_processor.args, width=100)

        gen_obj = ScoreObject(gen_score)
        gen_score = gen_obj.score

        if entry.output:
            differ = AlignDifference()
            writer.add_features(differ.features)
            differ.run(entry.output, gen_obj, extra=True)

        structure_data = {**entry.contractions, **entry.structures}
        writer.add_score('orig', target.score, title='Orig.',
                         structure_data={**entry.contractions, **entry.structures},
                         flavour=False)
        writer.add_score('gen', gen_score, title='Gen. Red.')
        writer.add_flavour(['orig', 'gen'], help=description)

        # Generate a contracted score
        contracted_obj, c_structure_data = create_contracted_score_obj(entry, structure_data)
        writer.add_score('contr', contracted_obj.score, structure_data=c_structure_data,
                         flavour=False, title='Contr.')

        if entry.output:
            writer.add_flavour(['contr', 'gen'], help=description)
            writer.add_score('ex', entry.output.score, title='Ex. Red.', flavour=False)
            writer.add_flavour(['ex', 'gen'], help=description)

        writer.finalize()

        logging.info('Done {}'.format(entry.name))

        if entry.output:
            return mmetrics, smetrics
        else:
            return None

    def show(self, entry):
        entry = self._ensure_entry(entry)

        logging.info('Writing data')
        title = '{}/features/{}'.format(self.name, entry.name)
        writer = LogWriter(config.LOG_DIR, title=title)
        logging.info('Log directory: {}'.format(writer.dir))
        writer.add_features(self.pre_processor.input_features)
        writer.add_features(self.pre_processor.structure_features)

        writer.add_score('orig', entry.input.score,
                         structure_data={**entry.contractions, **entry.structures},
                         title='Orig.', flavour=not entry.output)
        if entry.output:
            writer.add_features(self.pre_processor.alignment.features)
            entry.output.score.toWrittenPitch(inPlace=True)
            writer.add_score('ex', entry.output.score, title='Ex. Red.')
            writer.add_flavour(['orig', 'ex'])

        writer.finalize()

        logging.info('Done')

    def info(self):
        print('Model: {}'.format(self.model.describe()))
        print('Reducer arguments:')
        pprint(self.pre_processor.args)
        weights = self.model.describe_weights()
        if weights is not NotImplemented:
            print('Weights:')
            print('\n'.join('{:<32}{}'.format(k, v) for k, v in weights))

    def run_cli(self):
        from .cli import SystemCLI
        SystemCLI(self).run()

    def _ensure_entry(self, entry):
        if not isinstance(entry, PreProcessedEntry):
            logging.info('Loading score')
            entry = self.pre_processor.process_path_pair(*entry)
        return entry

    def _ensure_entries(self, entries):
        if not isinstance(entries, PreProcessedList):
            logging.info('Loading scores')
            entries = self.pre_processor.process(entries)
        return entries

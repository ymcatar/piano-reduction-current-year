import argparse
from collections import defaultdict
import copy
import datetime
import functools
import importlib
import json
import logging
import os.path
import sys
import textwrap
import time
from music21 import expressions
from pprint import pformat, pprint
import numpy as np
from tabulate import tabulate
from .piano.alignment import align_all_notes
from .piano.alignment.difference import AlignDifference
from .piano.contraction import IndexMapping
from .piano.reducer import Reducer
from .piano.score import ScoreObject
from .piano.contraction_writing import create_contracted_score_obj
from .piano.pre_processor import StructuralPreProcessor
from .piano.post_processor import PostProcessor
from .models.base import BaseModel
from .models.sk import WrappedSklearnModel
from .metrics import ModelMetrics, ScoreMetrics
from . import config
from scoreboard.writer import LogWriter
import scoreboard.writer as writerlib


def configure_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = '%(asctime)s %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt, datefmt='%H:%M:%S')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)


def add_description_to_score(score, description):
    te = expressions.TextExpression(description)
    te.style.absoluteY = -60
    te.style.fontSize = 8
    score.parts[-1].measure(-1).insert(0, te)


def create_reducer_and_model(module):
    reducer = StructuralPreProcessor(**module.reducer_args)

    Model = module.Model
    if type(Model) == type and not issubclass(Model, BaseModel):
        # Wrap sklearn models automagically
        Model = functools.partial(WrappedSklearnModel, Model)

    return reducer, Model(reducer)


def get_module_name(module):
    return os.path.splitext(os.path.basename(module.__file__))[0]


def get_dotted_module_path(module):
    tail = get_module_name(module)
    if module.__package__:
        return module.__package__ + '.' + tail
    else:
        return tail


def get_default_save_file(module):
    return 'trained/' + get_module_name(module) + '.model'


def save(model, module, filename):
    logging.info('Saving model to {}'.format(filename))
    model.save(filename)

    metadata = {
        'module': get_dotted_module_path(module),
        }
    with open(filename + '.metadata', 'w') as f:
        json.dump(metadata, f)


def load(filename):
    with open(filename + '.metadata', 'r') as f:
        metadata = json.load(f)

    logging.info('Initializing model')
    module = importlib.import_module(metadata['module'])
    reducer, model = create_reducer_and_model(module)

    logging.info('Loading model parameters')
    model.load(filename)

    return reducer, model


def train(module, sample=None, save_to=None):
    logging.info('Initializing model')
    reducer, model = create_reducer_and_model(module)

    logging.info('Reading sample scores')
    ds = reducer.process(sample)

    logging.info('Feature set:\n' +
                 textwrap.indent('\n'.join(reducer.all_keys), '-   '))
    logging.info('Training ML model')

    model.fit_structured(ds.X, ds.y)
    metric = model.evaluate_structured(ds.X, ds.y)
    logging.info('Training metric = {}'.format(metric))

    output = save_to or get_default_save_file(module)
    save(model, module, output)

    logging.info('Done training')

    return reducer, model


def command_train(args, *, module, **kwargs):
    train(module=module, sample=args.sample, save_to=args.output)


def command_reduce(args, *, module, **kwargs):
    if args.train:
        # Train model in place
        reducer, model = train(module=module, sample=args.sample, save_to=args.model)
    else:
        model = args.model or get_default_save_file(module)
        reducer, model = load(model)

    results = []
    for f in args.file:
        result = reduce_score(module, reducer, model, f, output=args.output,
                              no_output=args.no_output, train=args.train)
        if result:
            results.append((os.path.basename(f), *result))

    if len(results) > 1:
        logging.info('=' * 60)
        _, mmetrics, smetrics = results[0]
        mkeys = [k for k in mmetrics.keys if isinstance(mmetrics[k], float)]
        skeys = [k for k in smetrics.keys if isinstance(smetrics[k], float)]
        headers = ['File', *mkeys, *skeys]

        rows = [[name] + mmetrics[mkeys] + smetrics[skeys]
                for name, mmetrics, smetrics in results]
        average = np.mean(np.asarray([row[1:] for row in rows], dtype='float'), axis=0)
        rows.append(['(Average performance)'] + average.tolist())

        print(tabulate(rows, headers=headers))


def reduce_score(module, reducer, model, path_pair, *, output=None,
                 no_output=False, train=False):
    in_path, _, out_path = path_pair.partition(':')
    logging.info('Reading score {}'.format(in_path))
    target_entry = reducer.process_path_pair(in_path, out_path)
    target = target_entry.input
    target_out = target_entry.output

    X_test = target_entry.X
    y_test = target_entry.y
    logging.info('Predicting')

    y_proba = model.predict_structured(X_test)
    if reducer.label_type == 'align':
        y_pred = y_proba.flatten() >= 0.5
    elif reducer.label_type == 'hand':
        y_pred = np.argmax(y_proba, axis=1)
    else:
        raise NotImplementedError()
    target.annotate(target_entry.mapping.unmap_matrix(y_pred), reducer.label_type)

    post_processor = PostProcessor()
    result = post_processor.generate_piano_score(
        target, reduced=True, playable=True, label_type=reducer.label_type)

    writer_features = []

    target.annotate(
        target_entry.mapping.parents != np.arange(len(target_entry.mapping.parents)),
        'contracted')
    writer_features.append(writerlib.BoolFeature(
        'contracted', help='Whether the note is contracted to some other note', group='input'))

    if y_test is not None:
        mmetrics = ModelMetrics(reducer, y_proba, y_test)
        logging.info('Model metrics\n' + mmetrics.format())

        smetrics = ScoreMetrics(reducer, result, target_out.score)
        logging.info('Score metrics\n' + smetrics.format())

        # Wrongness marking
        correction = [str(t) if t != p else '' for t, p in zip(y_test.flatten(), y_pred)]
        target.annotate(target_entry.mapping.unmap_matrix(correction), 'correction')
        writer_features.append(writerlib.TextFeature(
            'correction', help='The correct label, if wrong', group='output'))

    description = textwrap.dedent('''\
        Command: {}
        Model: {}
        Generated at: {}
        ''').format(' '.join(sys.argv[:]),
                    model.describe(),
                    datetime.datetime.now().isoformat())
    add_description_to_score(result, description)
    description += '\nReducer arguments:\n' + pformat(reducer.args, width=100)

    if no_output:
        pass
    elif output:
        logging.info('Writing output')
        result.write(fp=output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')

    title = '{}/{}/{}'.format(get_module_name(module),
                              'training' if train else 'reduction',
                              os.path.basename(in_path))
    writer = LogWriter(config.LOG_DIR, title=title)
    logging.info('Log directory: {}'.format(writer.dir))
    writer.add_features(reducer.input_features)
    writer.add_features(reducer.structure_features)
    writer.add_features(reducer.output_features)
    writer.add_features(writer_features)

    result_obj = ScoreObject(result)
    result = result_obj.score

    if target_out:
        differ = AlignDifference()
        writer.add_features(differ.features)
        differ.run(target_out, result_obj, extra=True)

    structure_data = {**target_entry.contractions, **target_entry.structures}
    writer.add_score('orig', target.score, title='Orig.',
                     structure_data={**target_entry.contractions, **target_entry.structures},
                     flavour=False)
    writer.add_score('gen', result, title='Gen. Red.')
    writer.add_flavour(['orig', 'gen'], help=description)

    # Generate a contracted score
    contracted_obj, c_structure_data = create_contracted_score_obj(target_entry, structure_data)
    writer.add_score('contr', contracted_obj.score, structure_data=c_structure_data,
                     flavour=False, title='Contr.')

    if target_out:
        writer.add_flavour(['contr', 'gen'], help=description)
        writer.add_score('ex', target_out.score, title='Ex. Red.', flavour=False)
        writer.add_flavour(['ex', 'gen'], help=description)

    writer.finalize()

    logging.info('Done {}'.format(in_path))

    if target_out:
        return mmetrics, smetrics
    else:
        return None


def command_show(args, module, **kwargs):
    reducer = StructuralPreProcessor(**module.reducer_args)

    logging.info('Reading score')
    in_path, _, out_path = args.file.partition(':')
    target_entry = reducer.process_path_pair(in_path, out_path)
    sample_in = target_entry.input
    sample_out = target_entry.output

    logging.info('Writing data')
    title = '{}/features/{}'.format(get_module_name(module), os.path.basename(in_path))
    writer = LogWriter(config.LOG_DIR, title=title)
    logging.info('Log directory: {}'.format(writer.dir))
    writer.add_features(reducer.input_features)
    writer.add_features(reducer.structure_features)

    writer.add_score('orig', sample_in.score,
                     structure_data={**target_entry.contractions, **target_entry.structures},
                     title='Orig.', flavour=not out_path)
    if out_path:
        writer.add_features(reducer.alignment.features)
        sample_out.score.toWrittenPitch(inPlace=True)
        writer.add_score('ex', sample_out.score, title='Ex. Red.')
        writer.add_flavour(['orig', 'ex'])

    writer.finalize()

    logging.info('Done')


def command_info(args, **kwargs):
    model = args.model or get_default_save_file(kwargs['module'])
    reducer, model = load(model)

    print('Model: {}'.format(model.describe()))
    print('Reducer arguments:')
    pprint(reducer.args)
    weights = model.describe_weights()
    if weights is not NotImplemented:
        print('Weights:')
        print('\n'.join('{:<32}{}'.format(k, v) for k, v in weights))


def command_crossval(args, module, **kwargs):
    assert False, 'BROKEN'
    start = time.time()
    logging.info('Initializing reducer')
    reducer, model = create_reducer_and_model(module)

    logging.info('Reading sample scores')
    dataset = reducer.process(paths=CROSSVAL_SAMPLES)

    all_metrics = defaultdict(list)
    metric_names = {}

    logging.info('Starting cross-validation')
    for i in range(len(dataset)):
        logging.info('Fold {}: {!r}'.format(i, dataset.entries[i].in_path))
        logging.info('-' * 60)
        train_dataset, valid_dataset = dataset.split_dataset(i)
        X_train, y_train = train_dataset.get_matrices()
        X_valid, y_valid = valid_dataset.get_matrices()

        logging.info('Training')
        model.fit(X_train, y_train)

        target_in = dataset.entries[i].input_score_obj
        target_out = dataset.entries[i].output_score_obj

        logging.info('Predicting')
        y_proba = reducer.predict_from(model, target_in, X=X_valid,
                                       mapping=dataset.entries[i].C)

        post_processor = PostProcessor()
        result = post_processor.generate_piano_score(
            target_in, reduced=True, playable=True, label_type=reducer.label_type)

        metrics = ModelMetrics(reducer, y_proba, y_valid)
        for key in metrics.keys:
            all_metrics[key].append(getattr(metrics, key))
        metric_names.update(metrics.names)
        logging.info('Model metrics\n' + metrics.format())

        metrics = ScoreMetrics(reducer, result, target_out.score)
        for key in metrics.keys:
            all_metrics[key].append(getattr(metrics, key))
        metric_names.update(metrics.names)
        logging.info('Score metrics\n' + metrics.format())

    logging.info('=' * 60)
    out = []
    csv = [args.name]
    for key, values in all_metrics.items():
        name = metric_names[key]
        avg = np.mean(values)
        out.append('{:35} {:>13.4f}'.format(name, avg))
        csv.append(str(avg))
    logging.info('Cross-validated metrics (by averaging)\n' + '\n'.join(out))
    print(','.join('"{}"'.format(i) for i in csv))

    logging.info('Time elapsed: {}s'.format(time.time() - start))


def main(args, **kwargs):
    if args.command == 'train':
        command_train(args, **kwargs)
    elif args.command == 'reduce':
        command_reduce(args, **kwargs)
    elif args.command == 'show':
        command_show(args, **kwargs)
    elif args.command == 'info':
        command_info(args, **kwargs)
    elif args.command == 'crossval':
        command_crossval(args, **kwargs)
    else:
        raise NotImplementedError()


def run_model_cli(module):
    configure_logger()

    parser = argparse.ArgumentParser(description='Piano Reduction System')

    parser.add_argument('--sample', '-S', action='append',
                        help='A sample file pair, separated by a colon (:). '
                             'If unspecified, the default set of samples will '
                             'be used.')
    subparsers = parser.add_subparsers(dest='command', help='Command')
    subparsers.required = True

    train_parser = subparsers.add_parser('train', help='Train model')
    reduce_parser = subparsers.add_parser('reduce', help='Reduce score')

    train_parser.add_argument('--output', '-o', help='Output to file')

    reduce_parser.add_argument(
        'file', nargs='+',
        help='Input files. Optionally specify an input-output pairs to '
             'evaluate test metrics.')
    reduce_parser.add_argument('--output', '-o', help='Output to file')
    reduce_parser.add_argument('--model', '-m', help='Model file')
    reduce_parser.add_argument('--no-output', '-s', action='store_true',
                               help='Disable score output')
    reduce_parser.add_argument('--train', action='store_true',
                               help='Train the model in place')

    show_parser = subparsers.add_parser('show', help='Show features in Scoreboard')
    show_parser.add_argument(
        'file', help='Input file. Optionally specify an input-output pair '
                     'to show alignment features.')

    info_parser = subparsers.add_parser('info', help='Describe trained model')
    info_parser.add_argument('--model', '-m', help='Model file')

    crossval_parser = subparsers.add_parser(
        'crossval', help='Evaluate model using cross validation')
    crossval_parser.add_argument('name', help='Description of this run',
                                 nargs='?', default='Model')

    # Merge "a : b" into "a:b" for convenience of bash auto-complete
    argv = sys.argv[:]
    try:
        dash_dash = argv.index('--')
    except ValueError:
        dash_dash = len(argv)
    while True:
        try:
            i = argv.index(':')
        except ValueError:
            break
        if i <= 0 and i >= dash_dash - 1:
            break
        argv[i-1] = argv[i-1] + ':' + argv[i+1]
        del argv[i:i+2]

    args = parser.parse_args(argv[1:])
    ret = main(args, module=module)
    sys.exit(ret)

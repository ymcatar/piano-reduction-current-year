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
from .piano.alignment import align_all_notes
from .piano.alignment.difference import AlignDifference
from .piano.contraction import IndexMapping
from .piano.dataset import Dataset, DatasetEntry, CROSSVAL_SAMPLES, clear_cache
from .piano.reducer import Reducer
from .piano.score import ScoreObject
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
    reducer = Reducer(**module.reducer_args)

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


def train(args, module, save_model=False, **kwargs):
    logging.info('Initializing model')
    reducer, model = create_reducer_and_model(module)

    logging.info('Reading sample scores')
    dataset = Dataset(reducer, paths=args.sample,
                      use_cache=getattr(args, 'cache', False))
    if getattr(args, 'validation', False):
        train_dataset, _ = dataset.split_dataset(dataset.find_index(args.file))
        X, y = train_dataset.get_matrices(structured=True)
    else:
        X, y = dataset.get_matrices(structured=True)

    logging.info('Feature set:\n' +
                 textwrap.indent('\n'.join(reducer.all_keys), '-   '))
    logging.info('Training ML model')

    model.fit_structured(X, y)
    logging.info('Training metric = {}'.format(model.evaluate_structured(X, y)))

    if save_model:
        output = args.output or get_default_save_file(module)
        save(model, module, output)

    logging.info('Done training')

    return reducer, model


def command_train(args, **kwargs):
    train(args, save_model=True, **kwargs)


def command_reduce(args, **kwargs):
    if args.validation:
        # Train model in place
        reducer, model = train(args, **kwargs)
        assert not args.model, 'Model file cannot be used in validation mode'
    else:
        model = args.model or get_default_save_file(kwargs['module'])
        reducer, model = load(model)

    logging.info('Reading score')
    in_path, _, out_path = args.file.partition(':')
    target_entry = DatasetEntry((in_path, out_path))
    target_entry.load(reducer, keep_scores=True)
    target = target_entry.input_score_obj
    target_out = target_entry.output_score_obj

    X_test = (target_entry.X, target_entry.E, target_entry.F)
    y_test = target_entry.y
    logging.info('Predicting')

    y_proba = reducer.predict_from(model, target, X=X_test,
                                   mapping=target_entry.mapping, structured=True)

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
        metrics = ModelMetrics(reducer, y_proba, y_test)
        logging.info('Model metrics\n' + metrics.format())

        metrics = ScoreMetrics(reducer, result, target_out.score)
        logging.info('Score metrics\n' + metrics.format())

        # Wrongness marking
        y_pred = np.argmax(y_proba, axis=1)
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

    if args.no_output:
        pass
    elif args.output:
        logging.info('Writing output')
        result.write(fp=args.output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')

    writer = LogWriter(config.LOG_DIR)
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

    writer.add_score('orig', target.score, title='Orig.',
                     structure_data={**target_entry.contractions, **target_entry.structures},
                     flavour=False)
    writer.add_score('gen', result, title='Gen. Red.', flavour=False)
    writer.add_flavour(['orig', 'gen'], help=description)

    # Generate a contracted score
    target2 = ScoreObject(copy.deepcopy(target.score))
    def keep_func(n):
        return not target_entry.mapping.is_contracted(target2.index(n))
    contracted = post_processor.generate_piano_score(target2, playable=False, keep_func=keep_func)
    contracted_obj = ScoreObject(contracted)
    contracted = contracted_obj.score

    # Attach markings
    def key_func(n, offset, precision):
        return (int(offset * precision), n.pitch.ps)
    alignment = align_all_notes(contracted, target.score, ignore_parts=True, key_func=key_func)

    mapping = [None] * len(target_entry.X)  # From contracted index to contracted score index
    for i, n in enumerate(contracted_obj.notes):
        for m in alignment[n]:  # We hope the alignment is one-to-one
            mapping[target_entry.mapping[target.index(m)]] = i
    mapping = IndexMapping(mapping, output_size=len(contracted_obj))
    for i, key in enumerate(reducer.all_keys):
        contracted_obj.annotate(mapping.map_matrix(target_entry.X[:, i], default=0), key)
    contracted_obj.annotate(mapping.map_matrix(target_entry.y.flatten(), default=0),
                            reducer.alignment.key)

    structure_data = {k: list(mapping.map_structure(target_entry.mapping.map_structure(dict(v))).items())
                      for k, v in target_entry.structures.items()}
    writer.add_score('contr', contracted, structure_data=structure_data, flavour=False,
                     title='Contr.')

    if target_out:
        writer.add_flavour(['contr', 'gen'], help=description)
        writer.add_score('ex', target_out.score, title='Ex. Red.', flavour=False)
        writer.add_flavour(['ex', 'gen'], help=description)

    writer.finalize()

    logging.info('Done')


def command_show(args, module, **kwargs):
    reducer = Reducer(**module.reducer_args)

    logging.info('Reading score')
    in_path, _, out_path = args.file.partition(':')
    target_entry = DatasetEntry((in_path, out_path))
    target_entry.load(reducer, keep_scores=True)
    sample_in = target_entry.input_score_obj
    sample_out = target_entry.output_score_obj

    logging.info('Writing data')
    writer = LogWriter(config.LOG_DIR)
    logging.info('Log directory: {}'.format(writer.dir))
    writer.add_features(reducer.input_features)
    writer.add_features(reducer.structure_features)

    writer.add_score('orig', sample_in.score,
                     structure_data={**target_entry.contractions, **target_entry.structures},
                     title='Orig.', flavour=not out_path)
    if out_path:
        writer.add_features(reducer.alignment.features)
        sample_out.score.toWrittenPitch(inPlace=True)
        writer.add_score('ex', sample_out.score, title='Ex. Red.', flavour=False)
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
    start = time.time()
    logging.info('Initializing reducer')
    reducer, model = create_reducer_and_model(module)

    logging.info('Reading sample scores')
    dataset = Dataset(reducer, use_cache=True, keep_scores=True, paths=CROSSVAL_SAMPLES)
    dataset.get_matrices()

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
    elif args.command == 'clear-cache':
        clear_cache(args.substring)
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

    for subparser in [train_parser, reduce_parser]:
        subparser.add_argument('--cache', '-c', action='store_true',
                               help='Use preprocessing cache')

    train_parser.add_argument('--output', '-o', help='Output to file')

    reduce_parser.add_argument(
        'file', help='Input file. Optionally specify an input-output pair '
                     'to evaluate test metrics.')
    reduce_parser.add_argument('--output', '-o', help='Output to file')
    reduce_parser.add_argument('--model', '-m', help='Model file')
    reduce_parser.add_argument('--no-output', '-s', action='store_true',
                               help='Disable score output')
    reduce_parser.add_argument(
        '--validation', action='store_true',
        help='Perform train-validate evaluation, i.e. train on all samples '
             'except the target score and test on the target score.')

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

    clear_cache_parser = subparsers.add_parser(
        'clear-cache', help='Clear feature cache')
    clear_cache_parser.add_argument('substring', nargs='?')

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

import argparse
from collections import defaultdict
import datetime
import functools
import importlib
import json
import logging
import os.path
import sys
import textwrap
import time
from music21 import chord, expressions, layout
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib import colors
import numpy as np
from .piano.alignment import (LEFT_HAND, RIGHT_HAND)
from .piano.dataset import Dataset, DatasetEntry, CROSSVAL_SAMPLES, clear_cache
from .piano.reducer import Reducer
from .piano.score import ScoreObject
from .piano.post_processor import PostProcessor
from .models.base import BaseModel
from .models.sk import WrappedSklearnModel
from .metrics import ModelMetrics, ScoreMetrics
from . import config
from scoreboard.writer import LogWriter


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


def merge_reduced_to_original(original, reduced):
    # Add braces for clarity
    group = layout.StaffGroup(list(original.parts), name='Original',
                              abbreviation='Orig.', symbol='brace')
    original.insert(0, group)

    # Merge reduced parts
    original.mergeElements(reduced.parts)

    # More braces
    group = layout.StaffGroup(list(reduced.parts), name='Reduced',
                              abbreviation='Red.', symbol='brace')
    original.insert(0, group)


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

    logging.info('Reading input score')
    in_path, _, out_path = args.file.partition(':')
    target_entry = DatasetEntry((in_path, out_path))
    target_entry.load(reducer, keep_scores=True)
    target = target_entry.input_score_obj
    target_out = target_entry.output_score_obj

    X_test = (target_entry.X, target_entry.E, target_entry.F)
    y_test = target_entry.y
    logging.info('Predicting')

    y_proba = reducer.predict_from(model, target, X=X_test, mapping=target_entry.C, structured=True)

    post_processor = PostProcessor()
    result = post_processor.generate_piano_score(
        target, reduced=True, playable=True, label_type=reducer.label_type)

    if y_test is not None:
        metrics = ModelMetrics(reducer, y_proba, y_test)
        logging.info('Model metrics\n' + metrics.format())

        metrics = ScoreMetrics(reducer, result, target_out.score)
        logging.info('Score metrics\n' + metrics.format())

    if args.heat:
        logging.info('Displaying heat map')

        aligns = [n.editorial.misc['align'] for n in target]
        mappable = cm.ScalarMappable(colors.Normalize(0, 1), cm.GnBu)
        mappable.set_array(aligns)
        rgbas = mappable.to_rgba(aligns)

        # Show the distribution and a colorbar
        _, _, patches = plt.hist(aligns, range=(0, 1), bins=10)
        # Set the colour of each bar
        cs = mappable.to_rgba(np.linspace(0.05, 0.95, 10))
        for c, p in zip(cs, patches):
            plt.setp(p, 'facecolor', c)
        plt.title('Distribution of y')
        plt.colorbar(mappable)

        # Annotate on the score
        for n, rgba in zip(target, rgbas):
            n.style.color = '#{:02X}{:02X}{:02X}'.format(
                *(int(i * 256) for i in rgba[:3]))

        if args.label:
            for n in target.score.recurse().notes:
                if isinstance(n, chord.Chord):
                    n.lyric = '/'.join(
                        '{:.2f}'.format(i.editorial.misc['align']) for i in n)
                else:
                    n.lyric = '{:.2f}'.format(n.editorial.misc['align'])

        if args.type != 'combined':
            target.score.show('musicxml')

    if args.type == 'combined':
        target.score.toWrittenPitch(inPlace=True)

        COLORS = {
            LEFT_HAND: '#009900',
            RIGHT_HAND: '#0000FF'
            }

        # Combine scores
        if not args.heat:
            for n in target:
                if reducer.label_type == 'align':
                    n.style.color = ('#0000FF' if n.editorial.misc['align'] >= 0.5
                                     else '#000000')
                elif reducer.label_type == 'hand':
                    n.style.color = COLORS.get(n.editorial.misc['hand'], '#000000')

        merge_reduced_to_original(target.score, result)

        description = textwrap.dedent('''\
            Original score compared to reduced score.
            Blue notes indicate the notes that are kept.
            Model: {}
            Generated at {}
            '''.format(model.describe(),
                       datetime.datetime.now().isoformat()))
        add_description_to_score(target.score, description)

        result = target.score
    else:
        description = textwrap.dedent('''\
            Reduced score.
            Model: {}
            Generated at {}
            '''.format(model.describe(), datetime.datetime.now().isoformat()))
        add_description_to_score(result, description)

    writer = LogWriter(config.LOG_DIR)
    logging.info('Log directory: {}'.format(writer.dir))
    writer.add_features(reducer.features)
    writer.add_score('combined', result)
    writer.finalize()

    if args.no_output:
        pass
    elif args.output:
        logging.info('Writing output')
        result.write(fp=args.output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')

    if args.heat:
        plt.show()

    logging.info('Done')


def command_show(args, module, **kwargs):
    reducer = Reducer(**module.reducer_args)

    logging.info('Reading files')
    in_path, _, out_path = args.file.partition(':')
    sample_in = ScoreObject.from_file(in_path)
    sample_out = ScoreObject.from_file(out_path) if out_path else None

    logging.info('Creating markings')
    reducer.create_markings_on(sample_in)
    if out_path:
        reducer.create_alignment_markings_on(sample_in, sample_out, extra=True)

    logging.info('Writing data')
    writer = LogWriter(config.LOG_DIR)
    logging.info('Log directory: {}'.format(writer.dir))
    writer.add_features(reducer.features)
    if out_path:
        writer.add_features(reducer.alignment.features)
        sample_out.score.toWrittenPitch(inPlace=True)
        merge_reduced_to_original(sample_in.score, sample_out.score)
        writer.add_score('combined', sample_in.score)
    else:
        writer.add_score('input', sample_in.score)
    writer.finalize()

    logging.info('Done')


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
        y_proba = reducer.predict_from(model, target_in, X=X_valid, mapping=dataset.entries[i].C)

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
    elif args.command == 'crossval':
        command_crossval(args, **kwargs)
    elif args.command == 'clear-cache':
        clear_cache(args.substring)
    else:
        raise NotImplementedError()


def run_model_cli(module):
    configure_logger()

    parser = argparse.ArgumentParser(description='Piano Reduction System')

    parser.add_argument('--sample', '-S', nargs='*',
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
    reduce_parser.add_argument('--type', '-t', help='Output type',
                               choices=['reduced', 'combined'],
                               default='combined')
    reduce_parser.add_argument('--heat', action='store_true',
                               help='Output heat map')
    reduce_parser.add_argument('--label', action='store_true',
                               help='Add labels in heat map')
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

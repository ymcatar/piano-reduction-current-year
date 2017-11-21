import argparse
import datetime
import functools
import importlib
import json
import logging
import os.path
import sys
import textwrap
from music21 import chord, expressions, layout
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib import colors
import numpy as np
from sklearn import metrics
from .piano.alignment import (
    align_and_annotate_scores, ALIGNMENT_METHODS, DEFAULT_ALIGNMENT_METHOD,
    LEFT_HAND, RIGHT_HAND)
from .piano.algorithm.base import get_markings
from .piano.dataset import load_pairs
from .piano.reducer import Reducer
from .piano.score import ScoreObject
from .piano.post_processor import PostProcessor
from .models.base import BaseModel
from .models.sk import WrappedSklearnModel


DEFAULT_SAMPLES = [
    'sample/input/i_0000_Beethoven_op18_no1-4.xml:sample/output/o_0000_Beethoven_op18_no1-4.xml',
    'sample/input/i_0001_Spring_sonata_I.xml:sample/output/o_0001_Spring_sonata_I.xml',
    # 'sample/input/i_0002_Beethoven_Symphony_No5_Mov1.xml:sample/output/o_0002_Beethoven_Symphony_No5_Mov1.xml',
    'sample/input/i_0003_Beethoven_Symphony_No7_Mov2.xml:sample/output/o_0003_Beethoven_Symphony_No7_Mov2.xml',
    'sample/input/i_0004_Mozart_Symphony_No25.xml:sample/output/o_0004_Mozart_Symphony_No25.xml',
    'sample/input/i_0005_Mozart_Symphony_No40.xml:sample/output/o_0005_Mozart_Symphony_No40.xml',
    'sample/input/i_0006_Dvorak_New_World_Symphony_No9_Mov2.xml:sample/output/o_0006_Dvorak_New_World_Symphony_No9_Mov2.xml',
    'sample/input/i_0007_Tchaikovsky_nutcracker_march.xml:sample/output/o_0007_Tchaikovsky_nutcracker_march.xml'
    ]


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


def import_symbol(path):
    module, symbol = path.rsplit('.', 1)
    return getattr(importlib.import_module(module), symbol)


def create_reducer_and_model(module):
    reducer_args = dict(module.reducer_args)
    reducer_args['algorithms'] = [
        import_symbol(path)(*args, **kwargs)
        for path, args, kwargs in reducer_args['algorithms']]
    reducer = Reducer(**reducer_args)

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
    sample_paths = args.sample or DEFAULT_SAMPLES
    in_paths, out_paths = [], []
    for paths in sample_paths:
        in_path, out_path = paths.split(':')
        in_paths.append(in_path)
        out_paths.append(out_path)

    X, y = load_pairs(in_paths, out_paths, reducer, module.reducer_args,
                      use_cache=getattr(args, 'cache', False))

    logging.info('Feature set:\n' +
                 textwrap.indent('\n'.join(reducer.all_keys), '-   '))
    logging.info('Training ML model')

    model.fit(X, y)
    logging.info('Training metric = {}'.format(model.evaluate(X, y)))

    if save_model:
        output = args.output or get_default_save_file(module)
        save(model, module, output)

    logging.info('Done training')

    return reducer, model


def command_train(args, **kwargs):
    train(args, save_model=True, **kwargs)


def command_reduce(args, **kwargs):
    sample_paths = args.sample or DEFAULT_SAMPLES
    model = args.model or get_default_save_file(kwargs['module'])
    reducer, model = load(model)

    logging.info('Reading input score')
    in_path, _, out_path = args.file.partition(':')
    target = ScoreObject.from_file(in_path)
    target_out = ScoreObject.from_file(out_path) if out_path else None

    logging.info('Extracting features for input score')
    X_test = reducer.create_markings_on(target)
    y_test = (reducer.create_alignment_markings_on(target, target_out)
              if out_path else None)
    logging.info('Predicting')

    y_proba = reducer.predict_from(model, target, X=X_test)

    # We also calculate metrics for the binary keep/no keep prediction, so that
    # binary vs. multi-class models can be somewhat compared.
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

    if out_path:
        eval_title = 'Evaluation on {}'.format(in_path.rpartition('/')[2])
        logging.info('')
        logging.info(eval_title)
        logging.info('=' * len(eval_title))

        evals = [
            ('Accuracy',  metrics.accuracy_score(y_test, y_pred)),
            ('(0-1) Accuracy',  metrics.accuracy_score(y_test_bin, y_pred_bin)),
            ('(0-1) Precision, TP/(TP+FP)', metrics.precision_score(y_test_bin, y_pred_bin)),
            ('(0-1) Recall, TP/(TP+FN)', metrics.recall_score(y_test_bin, y_pred_bin)),
            ('(0-1) ROC AUC', metrics.roc_auc_score(y_test_bin, y_proba_bin)),
            ]
        for name, value in evals:
            logging.info('{:31} {:>13.4f}'.format(name, value))

        confusion = metrics.confusion_matrix(y_test, y_pred)
        logging.info('Confusion matrix\n{!r}'.format(confusion))

        confusion = metrics.confusion_matrix(y_test_bin, y_pred_bin)
        logging.info('{:31} TN{:>4} FP{:>4}'.format(
            '(0-1) Confusion matrix', *confusion[0, :]))
        logging.info('{:31} FN{:>4} TP{:>4}'.format('', *confusion[1, :]))

        logging.info('Note: This does not account for fabricated notes!')
        logging.info('')

    post_processor = PostProcessor()
    result = post_processor.generate_piano_score(target, reduced=True,
                                                 playable=True)

    if args.heat:
        logging.info('Displaying heat map')

        aligns = [n.editorial.misc['align'] for n in reducer.iter_notes(target)]
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
        for n, rgba in zip(reducer.iter_notes(target), rgbas):
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
            for n in reducer.iter_notes(target):
                if reducer.label_type == 'align':
                    n.style.color = ('#0000FF' if n.editorial.misc['align'] >= 0.5
                                     else '#000000')
                elif reducer.label_type == 'hand':
                    n.style.color = COLORS.get(n.editorial.misc['hand'], '#000000')

        merge_reduced_to_original(target.score, result)

        description = textwrap.dedent('''\
            Original score compared to reduced score.
            Blue notes indicate the notes that are kept.
            Model: {} ({} samples)
            Generated at {}
            '''.format(model.describe(), len(sample_paths),
                       datetime.datetime.now().isoformat()))
        add_description_to_score(target.score, description)

        result = target.score
    else:
        description = textwrap.dedent('''\
            Reduced score.
            Model: {} ({} samples)
            Generated at {}
            '''.format(model.describe(), len(sample_paths),
                       datetime.datetime.now().isoformat()))
        add_description_to_score(result, description)

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


def command_inspect(args, **kwargs):
    logging.info('Reading files')
    in_path, out_path = args.files.split(':')
    sample_in = ScoreObject.from_file(in_path)
    sample_out = ScoreObject.from_file(out_path)

    logging.info('Aligning scores')

    description = align_and_annotate_scores(sample_in.score, sample_out.score,
                                            method=args.alignment)
    result = sample_in.score

    merge_reduced_to_original(sample_in.score, sample_out.score)

    add_description_to_score(sample_in.score, description)

    logging.info(description)

    if args.output:
        logging.info('Writing output')
        result.write(fp=args.output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')


def command_show(args, **kwargs):
    Algorithm = import_symbol(args.algorithm)
    algorithm = Algorithm()
    reducer = Reducer(
        algorithms=[algorithm],
        alignment='pitch_class_onset')

    logging.info('Reading file')
    sample_in = ScoreObject.from_file(args.file)

    logging.info('Creating markings')
    reducer.create_markings_on(sample_in)

    for n in reducer.iter_notes(sample_in):
        n.style.color = (
            '#0000FF' if get_markings(n).get(algorithm.key, 0) else '#000000')

    logging.info('Displaying output')
    sample_in.score.show('musicxml')


def main(args, **kwargs):
    if args.command == 'train':
        command_train(args, **kwargs)
    elif args.command == 'reduce':
        command_reduce(args, **kwargs)
    elif args.command == 'inspect':
        command_inspect(args, **kwargs)
    elif args.command == 'show':
        command_show(args, **kwargs)
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

    reduce_parser = subparsers.add_parser('reduce', help='Reduce score')
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

    inspect_parser = subparsers.add_parser('inspect',
                                           help='Inspect sample pair')
    inspect_parser.add_argument(
        '--alignment', '-a', help='Alignment method',
        choices=ALIGNMENT_METHODS, default=DEFAULT_ALIGNMENT_METHOD)
    inspect_parser.add_argument(
        'files', help='Input file pair, separated by a colon (:).')
    inspect_parser.add_argument('--output', '-o', help='Output to file')

    show_parser = subparsers.add_parser('show', help='Show feature in input')
    show_parser.add_argument('file', help='Input file')
    show_parser.add_argument('algorithm', help='Algorithm')

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

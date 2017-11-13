import argparse
import datetime
import functools
import importlib
import json
import logging
import sys
import textwrap
from music21 import chord, expressions, layout
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib import colors
import numpy as np
from .piano.alignment import mark_alignment
from .piano.reducer import Reducer
from .piano.score import ScoreObject
from .piano.post_processor import PostProcessor
from .models.base import BaseModel
from .models.sk import WrappedSklearnModel


DEFAULT_SAMPLES = [
    'sample/input/i_0000_Beethoven_op18_no1-4.xml:sample/output/o_0000_Beethoven_op18_no1-4.xml',
    'sample/input/i_0001_Spring_sonata_I.xml:sample/output/o_0001_Spring_sonata_I.xml',
    'sample/input/i_0002_Beethoven_Symphony_No5_Mov1.xml:sample/output/o_0002_Beethoven_Symphony_No5_Mov1.xml',
    'sample/input/i_0003_Beethoven_Symphony_No7_Mov2.xml:sample/output/o_0003_Beethoven_Symphony_No7_Mov2.xml',
    'sample/input/i_0004_Mozart_Symphony_No25.xml:sample/output/o_0004_Mozart_Symphony_No25.xml',
    'sample/input/i_0005_Mozart_Symphony_No40.xml:sample/output/o_0005_Mozart_Symphony_No40.xml',
    'sample/input/i_0006_Dvorak_New_World_Symphony_No9_Mov2.xml:sample/output/o_0006_Dvorak_New_World_Symphony_No9_Mov2.xml',
    # 'sample/input/i_0007_Tchaikovsky_nutcracker_march.xml:sample/output/i_0007_Tchaikovsky_nutcracker_march.xml'
    ]

# (path.to.Class, args, kwargs)
DEFAULT_ALGORITHMS = [
    ('learning.piano.algorithm.ActiveRhythm', [], {}),
    ('learning.piano.algorithm.BassLine', [], {}),
    ('learning.piano.algorithm.EntranceEffect', [], {}),
    ('learning.piano.algorithm.Occurrence', [], {}),
    ('learning.piano.algorithm.OnsetAfterRest', [], {}),
    ('learning.piano.algorithm.PitchClassStatistics', [], {}),
    ('learning.piano.algorithm.RhythmVariety', [], {}),
    ('learning.piano.algorithm.StrongBeats', [], {'division': 0.5}),
    ('learning.piano.algorithm.SustainedRhythm', [], {}),
    ('learning.piano.algorithm.VerticalDoubling', [], {}),
    ]

DEFAULT_MODEL = 'learning.models.nn.NNModel'

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


def create_reducer_and_model(algorithms, model_str):
    algorithm_objs = [import_symbol(path)(*args, **kwargs)
                      for path, args, kwargs in algorithms]
    reducer = Reducer(algorithms=algorithm_objs)
    Model = import_symbol(model_str)
    if not issubclass(Model, BaseModel):
        # Wrap sklearn models automagically
        Model = functools.partial(WrappedSklearnModel, Model)

    return reducer, Model(reducer)


def save(reducer, model, filename, algorithms, model_str):
    logging.info('Saving model to {}'.format(filename))
    model.save(filename)

    metadata = {
        'algorithms': algorithms,
        'model_str': model_str,
        }
    with open(filename + '.metadata', 'w') as f:
        json.dump(metadata, f)


def load(filename):
    with open(filename + '.metadata', 'r') as f:
        metadata = json.load(f)

    logging.info('Initializing model')
    reducer, model = create_reducer_and_model(
        metadata['algorithms'], metadata['model_str'])

    logging.info('Loading model parameters')
    model.load(filename)

    return reducer, model


def train(args, model_str, save_model=False):
    logging.info('Reading sample scores')
    sample_paths = args.sample or DEFAULT_SAMPLES
    sample_in = []
    sample_out = []
    for paths in sample_paths:
        in_path, out_path = paths.split(':')
        sample_in.append(ScoreObject.from_file(in_path))
        sample_out.append(ScoreObject.from_file(out_path))

    logging.info('Extracting features for sample scores')
    reducer, model = create_reducer_and_model(DEFAULT_ALGORITHMS, model_str)

    X = reducer.create_markings_on(sample_in)
    y = reducer.create_alignment_markings_on(sample_in, sample_out)
    y = y[:, np.newaxis]

    logging.info('Feature set:\n' +
                 textwrap.indent('\n'.join(reducer.all_keys), '-   '))
    logging.info('Training ML model')

    model.fit(X, y)
    logging.info('Training metric = {}'.format(model.evaluate(X, y)))

    if save_model:
        save(reducer, model, args.output, algorithms=DEFAULT_ALGORITHMS,
             model_str=model_str)

    logging.info('Done training')

    return reducer, model


def command_train(args):
    train(args, model_str=args.model, save_model=True)


def command_reduce(args):
    sample_paths = args.sample or DEFAULT_SAMPLES
    if args.model:
        reducer, model = load(args.model)
    else:
        reducer, model = train(args, model_str=DEFAULT_MODEL)

    logging.info('Reading input score')
    target = ScoreObject.from_file(args.file)

    logging.info('Extracting features for input score')
    X_test = reducer.create_markings_on(target)
    logging.info('Predicting')
    reducer.predict_from(model, target, X=X_test)

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

        # Combine scores
        if not args.heat:
            for n in reducer.iter_notes(target):
                n.style.color = ('#0000FF' if n.editorial.misc['align'] >= 0.5
                                 else '#000000')

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

    if args.output:
        logging.info('Writing output')
        result.write(fp=args.output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')

    if args.heat:
        plt.show()

    logging.info('Done')


def command_inspect(args):
    reducer = Reducer(algorithms=[])

    logging.info('Reading files')
    in_path, out_path = args.files.split(':')
    sample_in = ScoreObject.from_file(in_path)
    sample_out = ScoreObject.from_file(out_path)

    logging.info('Aligning scores')
    mark_alignment(sample_in.score, sample_out.score)
    mark_alignment(sample_out.score, sample_in.score)

    FORWARD_COLORS = {
        'all': '#0000FF',
        'pitch space': '#0099FF',
        'pitch class': '#00CCFF'
    }
    for n in reducer.iter_notes(sample_in):
        n.style.color = FORWARD_COLORS.get(n.editorial.misc['align_type'],
                                           '#000000')
    BACKWARD_COLORS = {
        'all': '#000000',
        'pitch space': '#FF9900',
        'pitch class': '#EEEE00'
    }
    for n in reducer.iter_notes(sample_out):
        n.style.color = BACKWARD_COLORS.get(n.editorial.misc['align_type'],
                                            '#FF0000')

    result = sample_in.score

    merge_reduced_to_original(sample_in.score, sample_out.score)

    description = textwrap.dedent('''\
        [Original]
        Blue = Used directly
        Cyan = Used with octave transposition
        Light blue  = Used with duration change

        [Reduced]
        Black = Kept directly
        Yellow = Kept with octave transposition
        Orange = Kept with duration change
        Red = Fabricated by arranger

        Generated at {}
        '''.format(datetime.datetime.now().isoformat()))
    add_description_to_score(sample_in.score, description)

    if args.output:
        logging.info('Writing output')
        result.write(fp=args.output)
    else:
        logging.info('Displaying output')
        result.show('musicxml')


def main(args):
    if args.command == 'train':
        command_train(args)
    elif args.command == 'reduce':
        command_reduce(args)
    elif args.command == 'inspect':
        command_inspect(args)


if __name__ == '__main__':
    configure_logger()

    parser = argparse.ArgumentParser(description='Piano Reduction System')

    parser.add_argument('--sample', '-s', nargs='*',
                        help='A sample file pair, separated by a colon (:). '
                             'If unspecified, the default set of samples will '
                             'be used.')
    subparsers = parser.add_subparsers(dest='command', help='Command')
    subparsers.required = True

    train_parser = subparsers.add_parser('train', help='Train model')
    reduce_parser = subparsers.add_parser('reduce', help='Reduce score')

    for subparser in [train_parser, reduce_parser]:
        subparser.add_argument('--model', '-m', default=DEFAULT_MODEL,
                               help='Model class')

    train_parser.add_argument('--output', '-o', required=True,
                              help='Output to file')

    reduce_parser = subparsers.add_parser('reduce', help='Reduce score')
    reduce_parser.add_argument('file', help='Input file')
    reduce_parser.add_argument('--output', '-o', help='Output to file')
    reduce_parser.add_argument('--type', '-t', help='Output type',
                               choices=['reduced', 'combined'],
                               default='combined')
    reduce_parser.add_argument('--heat', action='store_true',
                               help='Output heat map')
    reduce_parser.add_argument('--label', action='store_true',
                               help='Add labels in heat map')
    reduce_parser.add_argument('--model', '-m', help='Model file')

    inspect_parser = subparsers.add_parser('inspect',
                                           help='Inspect sample pair')
    inspect_parser.add_argument(
        'files', help='Input file pair, separated by a colon (:).')
    inspect_parser.add_argument('--output', '-o', help='Output to file')

    args = parser.parse_args()
    ret = main(args)
    sys.exit(ret)

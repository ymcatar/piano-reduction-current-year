import argparse
from collections import defaultdict
import logging
import sys
import time
import numpy as np
from tabulate import tabulate
from .piano.post_processor import PostProcessor
from .metrics import ModelMetrics, ScoreMetrics
from .system import PianoReductionSystem


def configure_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = '%(asctime)s %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt, datefmt='%H:%M:%S')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)


class SystemCLI:
    def __init__(self, system):
        self.system = system

    def command_train(self, args):
        self.system.train(args.sample)
        self.system.save(args.output or self.system.get_default_save_file())

    def command_reduce(self, args):
        if args.train:
            # Train model in place
            self.system.train(args.sample)
            self.system.save(args.model or self.system.get_default_save_file())
        else:
            self.system = PianoReductionSystem.load(
                args.model or self.system.get_default_save_file())

        results = []
        for f in args.file:
            in_path, _, out_path = f.partition(':')
            entry = self.system.pre_processor.process_path_pair(in_path, out_path)
            logging.info('Reducing {}'.format(entry.name))

            gen_score, y_proba, y_pred = self.system.reduce(entry)

            if args.no_output:
                pass
            elif args.output:
                logging.info('Writing output')
                gen_score.write(fp=args.output)
            else:
                logging.info('Displaying output')
                gen_score.show('musicxml')

            is_train = args.train and f in args.sample
            result = self.system.evaluate(entry, gen_score, y_proba, y_pred, train=is_train,
                                          log=not args.no_log)
            if result:
                results.append((entry.name, *result))

        # Tabulate the results
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

    def command_show(self, args):
        in_path, _, out_path = args.file.partition(':')
        self.system.show((in_path, out_path))

    def command_info(self, args):
        self.system = PianoReductionSystem.load(
            args.model or self.system.get_default_save_file())
        self.system.info()

    def command_crossval(self, args):
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

    def main(self, args):
        if args.command == 'train':
            self.command_train(args)
        elif args.command == 'reduce':
            self.command_reduce(args)
        elif args.command == 'show':
            self.command_show(args)
        elif args.command == 'info':
            self.command_info(args)
        elif args.command == 'crossval':
            self.command_crossval(args)
        else:
            raise NotImplementedError()

    def run(self):
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
        reduce_parser.add_argument('--no-log', action='store_true',
                                   help='Disable scoreboard output')

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
        ret = self.main(args)
        sys.exit(ret)

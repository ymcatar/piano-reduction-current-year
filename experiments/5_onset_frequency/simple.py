import os
import sys
sys.path.insert(0, os.getcwd())

from collections import defaultdict, Counter
import sys

import numpy as np
from matplotlib import pyplot as plt
from sklearn.externals.joblib import Parallel, delayed
from sklearn.linear_model import LinearRegression

from learning.piano.score import ScoreObject
from learning.piano.algorithm.base import iter_notes_with_offset


def iter_offsets(obj):
    for bar in obj.by_bar:
        note_map = defaultdict(list)
        for n, offset in iter_notes_with_offset(bar, recurse=True):
            note_map[offset].append(n)
        for offset, notes in note_map.items():
            yield bar.offset + offset, notes


def extract(in_notes, out_notes):
    count = len(in_notes)
    # Note: Grace notes have 0 duration
    min_duration = float(min(n.duration.quarterLength for n in in_notes
                             if n.duration.quarterLength > 0))
    if len(in_notes) >= len(out_notes):
        return xbasis(count, min_duration), len(out_notes)
    else:
        return None


def xbasis(count, min_duration):
    return np.stack([1/count, np.log2(min_duration)], axis=-1)


def compute(paths):
    in_path, out_path = paths.split(':', 1)
    objs = [ScoreObject.from_file(path) for path in [in_path, out_path]]

    in_map, out_map = [dict(iter_offsets(obj)) for obj in objs]

    data = (extract(in_map[offset], out_map.get(offset, [])) for offset in in_map)
    data = [i for i in data if i is not None]

    tally = Counter((1/x[0], y) for x, y in data)
    xy = np.asarray(list(tally.keys()))
    x, y = xy[:, 0], xy[:, 1]
    s = np.asarray(list(tally.values())) * 5

    xb = np.asarray([x for x, _ in data])
    yb = np.asarray([y for _, y in data])
    model = LinearRegression()
    model.fit(xb, yb)
    score = model.score(xb, yb)

    return x, y, s, model, score


def main():
    results = Parallel(n_jobs=2, verbose=3)(delayed(compute)(paths) for paths in sys.argv[1:])
    for i, (x, y, s, model, score) in enumerate(results):
        plt.figure()
        plt.scatter(x, y, s=s)
        xlim = (0, 20)
        plt.xlim(xlim)
        plt.ylim((0, 8))
        plt.title('Note frequencies at all onsets')
        plt.xlabel('Original note count')
        plt.ylabel('Reduced note count')

        xspace = np.linspace(xlim[0]+0.01, xlim[1], xlim[1] * 5)
        for min_duration in [0.25, 0.5, 1.0, 2.0]:
            yspace = model.predict(xbasis(xspace, np.ones_like(xspace) * min_duration))
            plt.plot(xspace, yspace, label=str(min_duration))

        plt.legend()

        print('Run {}: Coef {} Intercept {} R^2 {}'.format(
            i+1, model.coef_, model.intercept_, score))

    plt.show()


if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: {} <input file:output file> [...]'.format(sys.argv[0]))
        sys.exit(1)

    main()

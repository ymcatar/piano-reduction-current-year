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


def xbasis(x):
    return np.stack([1./x], axis=1)


def compute(paths):
    in_path, out_path = paths.split(':', 1)
    objs = [ScoreObject.from_file(path) for path in [in_path, out_path]]

    in_map, out_map = [dict(iter_offsets(obj)) for obj in objs]

    data = ((len(in_map[offset]), len(out_map.get(offset, []))) for offset in in_map)
    data = ((x, y) for x, y in data if x >= y)

    tally = Counter(data)

    xy = np.asarray(list(tally.keys()))
    x, y = xy[:, 0], xy[:, 1]
    s = np.asarray(list(tally.values())) * 5

    xb = xbasis(x)
    model = LinearRegression()
    model.fit(xb, y)
    score = model.score(xb, y)

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
        plt.plot(xspace, model.predict(xbasis(xspace)), 'r')

        print('Run {}: Coef {} Intercept {} R^2 {}'.format(
            i+1, model.coef_, model.intercept_, score))

    plt.show()


if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: {} <input file:output file> [...]'.format(sys.argv[0]))
        sys.exit(1)

    main()

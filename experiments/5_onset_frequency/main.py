import os
import sys
sys.path.insert(0, os.getcwd())

from collections import defaultdict
import warnings
warnings.filterwarnings(action='ignore', module='scipy', message='^internal gelsd')

import numpy as np
from matplotlib import pyplot as plt
import scipy.special
from sklearn.externals.joblib import Parallel, delayed
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from learning.piano.score import ScoreObject
from learning.piano.algorithm.base import iter_notes_with_offset


USE_PITCH = True
USE_RATE = True
PLOT_NOTE_COUNT = False

BLUR_RADIUS = 4.0  # Standard deviation of Gaussian filter
BLUR_SIZE = 5  # Size of Gaussian filter in sigmas


def iter_offsets(obj):
    for bar in obj.by_bar:
        note_map = defaultdict(list)
        for n, offset in iter_notes_with_offset(bar, recurse=True):
            note_map[offset].append(n)
        for offset, notes in note_map.items():
            yield bar.offset + offset, notes


def extract_onset(in_notes, out_notes, offset):
    # Note: Grace notes have 0 duration
    if USE_PITCH:
        in_count = len(set(n.pitch.ps for n in in_notes))
        out_count = len(set(n.pitch.ps for n in out_notes))
    else:
        in_count = len(in_notes)
        out_count = len(out_notes)

    if in_count < out_count:
        out_count = in_count
        # return None

    return in_count, offset, out_count


def gaussian_pdf(x, sigma):
    return np.exp(-0.5 * (x/sigma)**2) / np.sqrt(2 * np.pi) / sigma


def gaussian_cdf(x, sigma):
    return 0.5 * (1 + scipy.special.erf(x / sigma / np.sqrt(2)))


def gaussian(x1, x2, sigma):
    return gaussian_cdf(x2, sigma) - gaussian_cdf(x1, sigma)
    # return 0.5 * (gaussian_pdf(x1, sigma) + gaussian_pdf(x2, sigma)) * (x2-x1)


def window_at(seq, offsets, durations, index, radius):
    '''Get the continuous window centred at the start of seq[i].'''
    centre = offsets[index]
    result = []
    for j in reversed(range(0, index)):
        if offsets[j] + durations[j] - centre <= -radius:
            break
        result.append((seq[j], (max(-radius, offsets[j] - centre), offsets[j] + durations[j] - centre)))
    result.reverse()

    for j in range(index, len(seq)):
        if offsets[j] - centre >= radius:
            break
        result.append((seq[j], (offsets[j] - centre, min(radius, offsets[j] + durations[j] - centre))))

    return result


def gaussian_filter(seq, offsets, durations, *, sigma):
    result = np.empty_like(seq)
    for i in range(len(seq)):
        win = window_at(seq, offsets, durations, i, BLUR_SIZE * sigma)
        result[i] = sum(x * gaussian(l, r, sigma) for x, (l, r) in win)
    return result


def median_filter(seq, offsets, durations, *, radius):
    result = np.empty_like(seq)
    for i in range(len(seq)):
        total = 0
        for x, (l, r) in window_at(seq, offsets, durations, i, radius):
            total += r - l
            if total >= radius:
                break
        result[i] = x

    return result


def seq2basis(data):
    data = np.asarray(data)
    in_count = data[:, 0]
    offsets = data[:, 1]
    out_count = data[:, 2]

    out_count[out_count == 0] = 1  # Must not be 0 sice we will take log

    durations = np.empty_like(in_count)
    durations[:-1] = offsets[1:] - offsets[:-1]
    durations[-1] = 4.0  # Assume a value for simplicity

    if USE_RATE:
        in_count /= durations
        out_count /= durations

    # Decompose in_count into base * detail
    base = gaussian_filter(in_count, offsets, durations, sigma=BLUR_RADIUS)
    assert np.all(base != 0) and np.all(~np.isnan(base))
    base += 0.01  # Smoothing term
    detail = in_count / base
    assert np.all(detail != 0) and np.all(~np.isnan(detail))

    x = np.stack([np.log(base), np.log(detail)], axis=1)  # For learning
    z = np.stack([in_count, base, durations], axis=1)  # For visualization
    return x, out_count, offsets, z


def compute(paths):
    in_path, out_path = paths.split(':', 1)
    objs = [ScoreObject.from_file(path) for path in [in_path, out_path]]

    in_map, out_map = [dict(iter_offsets(obj)) for obj in objs]

    data = (extract_onset(in_map[offset], out_map.get(offset, []), offset) for offset in in_map)
    data = [i for i in data if i is not None]
    data.sort(key=lambda i: i[1])  # sort by offset
    data = seq2basis(data)

    x, y, o, z = data
    try:
        model = LinearRegression()
        model.fit(x, np.log(y))
    except:
        print('Error in:', paths, file=sys.stderr)
        raise

    return x, y, o, z, model


def main():
    n_jobs = 1 if len(sys.argv[1:]) == 1 else 2
    results = Parallel(n_jobs=n_jobs, verbose=3)(delayed(compute)(paths) for paths in sys.argv[1:])
    for i, (x, y, o, z, model) in enumerate(results):
        ypred = np.exp(model.predict(x))
        # Always evaluate r^2 score w.r.t. note count
        score = r2_score(y * z[:, 2], ypred * z[:, 2])

        print('Run {}: Coef {} Intercept {} R^2 {}'.format(
            i+1, model.coef_, model.intercept_, score))

        # Sequence plot
        scaler = z[:, 2] if PLOT_NOTE_COUNT else 1
        style = dict(linewidth=0.5, drawstyle='steps-pre')
        plt.figure(figsize=(12,4))
        plt.plot(o, z[:, 0] * scaler, label='Original', color='C0', **style)
        plt.plot(o, z[:, 1] * scaler, label='Base', color='C4', linewidth=0.5)
        plt.plot(o, y * scaler, label='Reduced', color='C1', **style)
        plt.plot(o, ypred * scaler, '--', label='Predicted', color='C2', **style)
        plt.title('Note frequency sequences')
        plt.xlabel('Time (QL)')
        plt.ylabel('Note count' if PLOT_NOTE_COUNT else 'Note rate')
        plt.legend()
        plt.tight_layout()

    plt.show()


if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: {} <input file:output file> [...]'.format(sys.argv[0]))
        sys.exit(1)

    main()

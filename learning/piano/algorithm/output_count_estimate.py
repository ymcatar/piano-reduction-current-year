from .base import FeatureAlgorithm, get_markings

import numpy as np
import scipy.special


BLUR_RADIUS = 4.0  # Standard deviation of Gaussian filter
BLUR_SIZE = 5  # Size of Gaussian filter in sigmas


def window_at(seq, offsets, durations, index, radius):
    '''Get the continuous window centred at the start of seq[i].'''
    centre = offsets[index]
    result = []
    for j in reversed(range(0, index)):
        if offsets[j] + durations[j] - centre <= -radius:
            break
        result.append(
            (seq[j], (max(-radius, offsets[j] - centre), offsets[j] + durations[j] - centre)))
    result.reverse()

    for j in range(index, len(seq)):
        if offsets[j] - centre >= radius:
            break
        result.append(
            (seq[j], (offsets[j] - centre, min(radius, offsets[j] + durations[j] - centre))))

    return result


def gaussian_cdf(x, sigma):
    return 0.5 * (1 + scipy.special.erf(x / sigma / np.sqrt(2)))


def gaussian_filter(seq, offsets, durations, *, sigma):
    result = np.empty_like(seq)
    for i in range(len(seq)):
        win = window_at(seq, offsets, durations, i, BLUR_SIZE * sigma)
        result[i] = sum(x * (gaussian_cdf(r, sigma) - gaussian_cdf(l, sigma)) for x, (l, r) in win)
    return result


class OutputCountEstimate(FeatureAlgorithm):
    dtype = 'float'
    range = (0.0, None)

    def run(self, score_obj):
        it = list(score_obj.iter_offsets())
        offsets = np.asarray([offset for offset, _ in it])
        notes_list = [notes for _, notes in it]

        durations = np.empty_like(offsets)
        durations[:-1] = offsets[1:] - offsets[:-1]
        durations[-1] = 4.0  # Assume a value for simplicity

        in_counts = np.asarray(
            [len({n.pitch.ps for n in notes}) for notes in notes_list], dtype='float')
        in_rates = in_counts / durations

        base = gaussian_filter(in_rates, offsets, durations, sigma=BLUR_RADIUS)
        base += 0.01  # Smoothing term
        detail = in_rates / base

        # Determined by experiment 5: onset frequency analysis
        out_rates = 1.61 * base**0.545 * detail**0.759
        out_counts = out_rates * durations

        for notes, out_count in zip(notes_list, out_counts):
            for n in notes:
                get_markings(n)[self.key] = out_count

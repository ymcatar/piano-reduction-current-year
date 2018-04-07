import cython
import numpy as np
from numpy cimport uint32_t


def packbits(matrix, dtype='uint32'):
    assert matrix.shape[1] <= 32
    # Lower indices are less significant
    sig = (1 << np.arange(matrix.shape[1], dtype=dtype))[np.newaxis, :]

    return np.sum(matrix.astype(dtype) * sig, axis=1).astype(dtype)


def get_horizontal_potentials(self, prev, Y_prev, Y_curr, w):
    # Convert to bit vectors for efficiency
    y1 = packbits(Y_prev)
    y2 = packbits(Y_curr)
    return np.asarray(get_horizontal_potentials_impl(self, prev, y1, y2, w))


cdef double[:, :] get_horizontal_potentials_impl(
        object self, object prev, uint32_t[:] y1, uint32_t[:] y2, double[:] w):
    cdef double[:, :] U = np.zeros((len(y1), len(y2)), dtype='double')

    cdef uint32_t i, j, k

    cdef double duration = self.offset - prev.offset
    if duration == 0.0:  # Grace notes
        duration = 0.25

    arr = np.asarray(self.voice_edges, dtype='int32')
    if arr.ndim == 1:
        arr = arr[:, np.newaxis]
    cdef int[:, :] voice_edges = arr

    cdef double w_onset, w_voice
    w_onset, w_voice = w[self.n_note_features+1:]

    # Disable bounds check for efficiency
    with cython.boundscheck(False):
        for i in range(len(y1)):
            for j in range(len(y2)):
                # Onset crowding
                if y1[i] and y2[j]:
                    U[i, j] += w_onset

                # Voice crowding
                for k in range(len(voice_edges)):
                    if (y1[i] & (1 << voice_edges[k, 0]) and
                            y2[j] & (1 << voice_edges[k, 1])):
                        U[i, j] += w_voice

                U[i, j] /= duration

    return U

import cython
import numpy as np
from numpy cimport uint32_t


def packbits(matrix, dtype='uint32'):
    assert matrix.shape[1] <= 32
    # Lower indices are less significant
    sig = (1 << np.arange(matrix.shape[1], dtype=dtype))[np.newaxis, :]

    return np.sum(matrix.astype(dtype) * sig, axis=1).astype(dtype)


def pitch_class_vectors(onset, Y):
    mat = np.zeros((len(Y), 12), dtype='uint32')
    for i, y in enumerate(Y):
        pcs = onset.pitch_classes[np.where(y == 1)]
        if len(pcs):
            mat[i, pcs] = 1

    return packbits(mat)


def get_horizontal_potentials(self, prev, Y_prev, Y_curr, w):
    # Convert to bit vectors for efficiency
    cdef uint32_t[:] y1 = packbits(Y_prev)
    cdef uint32_t[:] y2 = packbits(Y_curr)

    # Pre-computation
    cdef double duration = self.offset - prev.offset
    if duration == 0.0:  # Grace notes
        duration = 0.25

    arr = np.asarray(self.voice_edges, dtype='int32')
    if arr.ndim == 1:
        arr = arr[:, np.newaxis]
    cdef int[:, :] voice_edges = arr

    cdef uint32_t[:] pc1 = pitch_class_vectors(prev, Y_prev)
    cdef uint32_t[:] pc2 = pitch_class_vectors(self, Y_curr)

    cdef double w_onset, w_voice, w_pc_diff
    w_onset, w_voice, w_pc_diff = w[self.horiz_weight_start:]

    cdef double[:, :] U = np.zeros((len(y1), len(y2)), dtype='double')
    cdef uint32_t i, j, k

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

                # Pitch class difference
                U[i, j] += popcount(pc1[i] ^ pc2[j]) * w_pc_diff

                U[i, j] /= duration

    return np.asarray(U)


cdef extern:
    int __builtin_popcount(unsigned int x)


cdef int popcount(uint32_t x):
    # Supported by GCC and LLVM
    # Fix this if someone uses another compiler
    return __builtin_popcount(x)

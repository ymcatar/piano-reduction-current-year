import numpy as np


LEN = 255
dp = tuple([(0, 0)]*(LEN+1) for _ in range(2))

def global_alignment(first, second, dp=dp, match=1, mismatch=0, indel=0):
    '''
    Global sequence alignment for sequences with length <= LEN.
    Finds the highest alignment score and the longest alignment length.
    '''
    n, m = len(first), len(second)
    for j in range(m+1):
        dp[n&1][m-j] = 0, j

    for i in reversed(range(n)):
        dp[i&1][m] = 0, n-i
        for j in reversed(range(m)):
            eq = match if (first[i] == second[j]) else mismatch
            dp[i&1][j] = max(
                (dp[~i&1][j][0] + indel, dp[~i&1][j][1] + 1),
                (dp[i&1][j+1][0] + indel, dp[i&1][j+1][1] + 1),
                (dp[~i&1][j+1][0] + eq, dp[~i&1][j+1][1] + 1))

    return dp[0][0]


def global_alignment_vec(first, seconds, match=1, mismatch=0, indel=0):
    '''
    Works for strings with length at most 255 and non-negative alignment scores
    at most 255.
    '''

    assert match >= 0 and mismatch >= 0 and indel >= 0

    n = len(first)
    m = max(len(second) for second in seconds)
    t = len(seconds)

    # Convert symbols in first and seconds into 8-bit integers
    f = np.empty(n, dtype='uint8')
    mapping = {}
    for i, symbol in enumerate(first):
        try:
            f[i] = mapping[symbol]
        except KeyError:
            f[i] = mapping[symbol] = len(mapping) + 1

    ss = np.zeros((m, t), dtype='uint8')
    sstart = np.zeros(t, dtype='uint8')
    for i, second in enumerate(seconds):
        # Right align all second strings
        sstart[i] = m - len(second)
        for j, symbol in enumerate(second):
            try:
                ss[sstart[i] + j, i] = mapping[symbol]
            except KeyError:
                # Default to 0, which matches nothing, so it is fine
                pass

    # DP with memory compression; we do t instances of DP together for
    # vectorization.
    dp = np.empty((2, m+1, t), dtype='uint16')

    match = np.uint16(match << 8)
    mismatch = np.uint16(mismatch << 8)
    indel = np.uint16(indel << 8)
    one = np.uint16(1)

    results = np.zeros(t, dtype='uint16')

    # Each short is 2 bytes = 16 bits; the first (more significant) 8 bits are
    # used to store the alignment score, and the second 8 bits are used to
    # store the alignment length.
    for j in range(m+1):
        dp[n&1, m-j, :] = (((m-j) * indel)) + j

    for i in reversed(range(n)):
        dp[i&1, m, :] = (((n-i) * indel)) + (n-i)
        for j in reversed(range(m)):
            eq = ss[j, :] == f[i]
            align = eq * match + ~eq * mismatch
            dp[i&1, j, :] = np.max([
                dp[~i&1, j, :] + indel,
                dp[i&1, j+1, :] + indel,
                dp[~i&1, j+1, :] + align
                ], axis=0) + one

    # Collect results for each second string
    for i in range(t):
        results[i] = dp[0, sstart[i], i]

    return (results[:] >> 8), (results[:] & 0xff)


def align_sequences(first, second, LEN=LEN, global_alignment=global_alignment):
    ''' Align two arbitrary sequences (lists).

    Returns tuple (alignment score, max alignment length).
    '''
    assert len(first) <= LEN and len(second) <= LEN
    score, length = global_alignment(first, second)
    return (length - score) / length


def align_one_to_many(first, seconds):
    '''
    Align one arbitrary sequence with each of the list of arbitrary sequences.
    '''
    assert len(first) <= LEN and all(len(s) <= LEN for s in seconds)
    scores, lengths = global_alignment_vec(first, seconds)
    return (lengths - scores) / lengths

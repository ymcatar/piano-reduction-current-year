from collections import defaultdict
from itertools import islice
import numpy as np
from .algorithm.base import iter_notes_with_offset


class ContractionAlgorithm:
    def run(self, score_obj):
        '''
        Returns a list of pairs (x, y) indicating Note y should be contracted to
        Note x.
        '''
        raise NotImplemented()

    @property
    def key(self):
        return type(self).__name__

    @property
    def args(self):
        return ([], {})


class ContractTies(ContractionAlgorithm):
    def run(self, score_obj):
        '''
        Contract tied notes to their preceding notes.
        '''
        for n, n2 in zip(score_obj.notes, islice(score_obj.notes, 1)):
            if n.tie and n.tie.type in ('start', 'continue'):
                yield (score_obj.index(n), score_obj.index(n2))


class ContractByPitchOnset(ContractionAlgorithm):
    def run(self, score_obj):
        '''
        Contract notes with the same pitch and the same starting time.
        '''
        for bar in score_obj.by_bar:
            note_map = defaultdict(list)
            for n, offset in iter_notes_with_offset(bar, recurse=True):
                note_map[(offset, n.pitch.ps)].append(n)

            for first, *other in note_map.values():
                for n in other:
                    yield (score_obj.index(first), score_obj.index(n))


def flatten_contractions(contractions, n):
    '''
    Flatten contractions.

    contractions: Iterator of (u, v) pairs indicating v is to be merged to u.

    Returns a list of length n indicating the parent of the ith note.
    '''
    adj = [[] for _ in range(n)]
    for u, v in contractions:
        adj[u].append(v)
        adj[v].append(u)

    P = [None] * n

    for s in range(n):
        if P[s] is not None:
            continue

        # Flood fill with BFS
        queue = [s]
        while queue:
            u = queue.pop(0)
            if P[u] is not None:
                continue
            P[u] = s

            for v in adj[u]:
                if P[v] is None:
                    queue.append(v)

    return P


def compute_contraction_mapping(P):
    '''
    Compute a mapping such that each note is mapped to a renumbered entry in
    the new matrix.

    Returns (mapping, new length).
    '''
    mapping = {}
    C = []
    for g in P:
        if g not in mapping:
            mapping[g] = len(mapping)
        C.append(mapping[g])

    return C, len(mapping)


def contract_by(matrix, C):
    '''
    Contract matrix by the mapping C.
    '''
    matrix = np.asarray(matrix)

    groups = defaultdict(list)
    for i, g in enumerate(C):
        groups[g].append(matrix[i])

    result = np.empty((len(groups), *matrix.shape[1:]), dtype=matrix.dtype)
    for g, entries in groups.items():
        # Contract entries using the max operator
        result[g, ...] = np.max(entries, axis=0)

    return result


def contract_structure_by(structure, C):
    groups = defaultdict(list)
    for edge, feature in structure.items():
        new_edge = tuple(sorted([C[edge[0]], C[edge[1]]]))
        if new_edge[0] == new_edge[1]:  # Prohibit self-loops
            continue
        groups[new_edge].append(feature)

    return {k: np.max(v, axis=0) for k, v in groups.items()}

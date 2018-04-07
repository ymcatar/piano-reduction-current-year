from collections import defaultdict
from itertools import islice
import numpy as np
from .algorithm.base import iter_notes_with_offset


class ContractionAlgorithm:
    def __init__(self):
        # The *args and **kwargs that can be used to reconstruct this algorithm
        self.args = [], {}

    def run(self, score_obj):
        '''
        Returns a list of pairs (x, y) indicating Note y should be contracted to
        Note x.
        '''
        raise NotImplementedError()

    @property
    def key(self):
        return type(self).__name__


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


class IndexMapping:
    '''A many-to-one/zero mapping.'''
    def __init__(self, mapping, output_size=None, aggregator=None):
        self.mapping = [m if m != -1 else None for m in mapping]

        self.input_size = len(mapping)
        if output_size is None:
            self.output_size = max((m + 1 for m in self.mapping if m is not None), default=0)
        else:
            self.output_size = output_size

        self.aggregator = aggregator or (lambda x: np.max(x, axis=0))

        self.groups = [[] for _ in range(self.output_size)]
        for i, o in enumerate(self.mapping):
            if o is not None:
                self.groups[o].append(i)

    def map_matrix(self, matrix, default=None):
        assert len(matrix) == self.input_size

        if isinstance(matrix, list):
            result = [None] * self.output_size
        else:
            result = np.empty((self.output_size, *matrix.shape[1:]), dtype=matrix.dtype)
        for g, indices in enumerate(self.groups):
            if indices:
                result[g] = self.aggregator([matrix[i] for i in indices])
            else:
                result[g] = default

        return result

    def map_structure(self, structure):
        groups = defaultdict(list)
        for edge, feature in structure.items():
            new_edge = self.mapping[edge[0]], self.mapping[edge[1]]
            if new_edge[0] is None or new_edge[1] is None:  # Vertex does not exist in output
                continue
            new_edge = tuple(sorted(new_edge))
            if new_edge[0] == new_edge[1]:  # Prohibit self-loops
                continue
            groups[new_edge].append(feature)

        return {k: self.aggregator(v) for k, v in groups.items()}

    def unmap_matrix(self, matrix, default=None):
        assert len(matrix) == self.output_size
        matrix = np.asarray(matrix)

        result = np.empty((self.input_size, *matrix.shape[1:]), dtype=matrix.dtype)
        for i, o in enumerate(self.mapping):
            result[i, ...] = matrix[o] if o is not None else default

        return result

    def __getitem__(self, i):
        return self.mapping[i]


class ContractionMapping(IndexMapping):
    def __init__(self, contractions, input_size, **kwargs):
        self.parents = flatten_contractions(contractions, input_size)
        mapping, _ = compute_contraction_mapping(self.parents)
        super().__init__(mapping, **kwargs)

    def is_contracted(self, i):
        return i != self.parents[i]

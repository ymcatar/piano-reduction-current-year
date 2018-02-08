import numpy as np
from .contraction import contract_by, compute_contraction_mapping, flatten_contractions


def test_flatten_contractions():
    graph = []
    assert flatten_contractions(graph, 0) == []
    assert flatten_contractions(graph, 3) == [0, 1, 2]

    graph = [
        (2, 0),
        (0, 1),
        (1, 2),

        (3, 4),
        (4, 5),
        (6, 5),
        ]
    assert flatten_contractions(graph, 7) == [0, 0, 0, 3, 3, 3, 3]

    graph = [
        (3, 0),
        (4, 1),
        (5, 2),
        ]
    assert flatten_contractions(graph, 6) == [0, 1, 2, 0, 1, 2]


def test_compute_contraction_mapping():
    assert compute_contraction_mapping([]) == ([], 0)
    assert compute_contraction_mapping([0, 1, 2]) == ([0, 1, 2], 3)
    assert compute_contraction_mapping([0, 0, 0, 3, 3, 3, 3]) == ([0, 0, 0, 1, 1, 1, 1], 2)
    assert compute_contraction_mapping([0, 0, 2, 3, 2, 3]) == ([0, 0, 1, 2, 1, 2], 3)


def test_contract_by():
    data = [1, 2, 3, 4, 5]
    C = [0, 0, 0, 1, 1]
    assert np.all(contract_by(data, C) == [3, 5])

    C = [0, 1, 0, 1, 0]
    assert np.all(contract_by(data, C) == [5, 4])

    C = list(range(5))
    assert np.all(contract_by(data, C) == data)

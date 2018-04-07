'''
This module implements the "onset chain" conditional random field model. In an
onset chain, the notes of each onset are put in a clique. Adjacent cliques are
fully-connected. There are two potential functions:

-   Vertical potential: For an onset, takes the features and labels of all notes
    in the current onset as input.
-   Horizontal potential: For two adjacent onsets, takes the the features and
    labels of all notes in the two onsets as input.

Another way to view this is that this is an undirected Markov chain, where each
node represents an onset. A node that represents v notes will have 2^v states.
'''
import copy
import numpy as np
from pystruct.models import StructuredModel
from ..models.pystruct_crf import PyStructCRF
from .pre_processor import ContractingPreProcessor
from .algorithm.output_count_estimate import OutputCountEstimate
from .structure import AdjacentNotes
from . import onset_chain_ext


class OnsetStruct:
    '''
    Stores information that describes this onset and interactions between this
    onset and the previous onset.

    A list of OnsetStructs defines a conditional random field.
    '''
    def __init__(self, offset, note_features, note_count, max_kept, indices):
        self.voice_edges = []

        self.offset = offset

        self.note_features = note_features
        self.n_note_features = note_features.shape[1]

        self.note_count = note_count
        self.max_kept = max_kept
        self.indices = indices

    @classmethod
    def create(cls, score_obj, entry):
        '''
        Create a list of OnsetStructs from a ScoreObject.

        entry: the PreProcessedEntry that contains contracted features.
        '''
        onsets = []
        onset_lookup = {}

        count_algo = OutputCountEstimate()
        count_algo.key_prefix = 'OnsetStruct'
        count_algo.run(score_obj)

        for offset, notes in score_obj.iter_offsets():
            # Create a struct for each onset

            # Contracted indices
            indices = list({entry.mapping.mapping[score_obj.index(n)] for n in notes})
            output_est = notes[0].editorial.misc[count_algo.key] if notes else 0.0
            output_est = min(8, int(round(output_est)))

            struct = cls(offset, entry.X[indices, :], len(indices), output_est, indices)
            onset_index = len(onsets)
            onsets.append(struct)

            for i, index in enumerate(indices):
                onset_lookup[index] = onset_index, i

        # Add voice edges between onsets
        adj = entry.mapping.map_structure(dict(AdjacentNotes().run(score_obj)))
        for (u, v), _ in adj.items():
            # Sort by onset index
            (u_onset, u_index), (v_onset, v_index) = \
                sorted([onset_lookup[u], onset_lookup[v]])
            if v_onset - u_onset != 1:
                continue

            onsets[v_onset].voice_edges.append((u_index, v_index))

        return onsets

    def generate_labels(self, count=1024):
        '''
        Generate valid label vectors for this onset. Up to `count` vectors
        should be generated.

        Returns: int ndarray of shape (note_count, k) where k <= count
            Each row is a label vector.
        '''
        out = []
        for i in range(2 ** self.note_count):
            if len(out) == count:
                break
            if bin(i).count('1') <= self.max_kept:
                value = []
                for j in range(self.note_count):
                    value.append(int(bool((1 << j) & i)))
                out.append(value)
        return np.asarray(out)

    def get_vertical_potentials(self, Y, w):
        '''
        Given labels for this onset, compute the vertical potential function.

        Y: int ndarray of shape (note_count, k)
            Each row is a label vector.

        w: float ndarray of shape (n_weights,)
            The weights used by this potential function, which should be linear
            in w.

        Returns: float ndarray of shape (k,)
            The potential value for each label vector.
        '''
        intercept = w[self.n_note_features]
        weights = w[:self.n_note_features]

        # @ = matmul operator
        u = self.note_features @ weights + intercept
        return Y @ u

    def get_horizontal_potentials(self, prev, Y_prev, Y_curr, w):
        '''
        Given labels for this onset and the previous onset, compute the
        horizontal potential function.

        prev: OnsetStruct
            The OnsetStruct for the previous onset.

        Y_prev, Y_curr: int ndarray of shape (prev.note_count, k1), (note_count, k2)
            Each row is a label vector.

        w: float ndarray of shape (n_weights,)
            The weights used by this potential function, which should be linear
            in w.

        Returns: float ndarray of shape (k1, k2)
            The potential value for each combination of label vectors.
        '''
        return onset_chain_ext.get_horizontal_potentials(self, prev, Y_prev, Y_curr, w)


class OnsetChainPreProcessor(ContractingPreProcessor):
    '''
    A pre-processor that constructs each x for a score as OnsetStruct[].
    '''
    def process_score_obj_pair(self, input, output, **kwargs):
        parent = super().process_score_obj_pair(input, output, **kwargs)
        ret = copy.copy(parent)
        ret.parent = parent

        ret.X = OnsetStruct.create(input, parent)
        ret.features = parent.X
        ret.structures = {}

        return ret

    @property
    def n_weights(self):
        return len(self.all_keys) + 3


class OnsetChainPyStructModel(StructuredModel):
    '''
    Implements the PyStruct Model interface. In particular, this implements
    feature vector construction, MAP inference and loss-augmented MAP
    inference.

    In this Model, x is OnsetStruct[], while y is a binary vector of shape
    (number_of_notes,).
    '''
    def __init__(self, pre_processor):
        assert isinstance(pre_processor, OnsetChainPreProcessor)
        self.pre_processor = pre_processor
        self.size_joint_feature = pre_processor.n_weights

        assert pre_processor.label_type == 'align'
        self.n_states = 2

        self.inference_calls = 0

    def initialize(self, X, Y):
        pass

    def joint_feature(self, x, y):
        ret = np.zeros(self.size_joint_feature)
        Y = self._split_y(y, x)
        for i in range(self.size_joint_feature):
            # For simplicity, we simply evaluate the potential when w equals
            # each of the standard basis vectors.
            w = np.zeros(self.size_joint_feature)
            w[i] = 1.0
            u = 0.0
            onset_prev, y_prev = None, None
            for onset, y in zip(x, Y):
                u += onset.get_vertical_potentials(y[np.newaxis, :], w)[0]
                if onset_prev and onset_prev.note_count:
                    u += onset.get_horizontal_potentials(
                        onset_prev, y_prev[np.newaxis, :], y[np.newaxis, :], w)[0, 0]
                onset_prev, y_prev = onset, y
            ret[i] = u

        return ret

    def inference(self, x, w, relaxed=None):
        return self._inference(x, w)

    def loss_augmented_inference(self, x, y, w, relaxed=None):
        return self._inference(x, w, y)

    def _split_y(self, y, onsets):
        return [y[onset.indices] for onset in onsets]

    def _inference(self, onsets, w, y=None):
        '''
        Perform inference with Viteri algorithm -- except the states considered
        varies and has an exponential size. If y is provided, loss-augmented
        inference is performed.

        dp[t][i] = Max potential of the induced subgraph up to onset t, given
                   that onset t has state vector y_hat[t]
        dp[t][i] = max_j [dp[t-1][j] +
                          horizontal_potential(y_hat[t-1, j], y_hat[t, i]) +
                          vertical_potential(y_hat[t])]
        bt[t][i] = The state index for onset t-1 that leads to dp[t][i]
        '''
        if not onsets:
            return np.asarray([])

        loss_augmented = y is not None

        COUNT = 32768

        Y = self._split_y(y, onsets) if loss_augmented else None

        Y_hats = [onset.generate_labels(COUNT) for onset in onsets]
        bt = [-np.ones(len(Y_hats[0]))]  # Backtracking array

        u = onsets[0].get_vertical_potentials(Y_hats[0], w)
        if loss_augmented:
            u += np.sum(Y_hats[0] != Y[0][np.newaxis, :], axis=1)

        onset_prev, Y_hat_prev = onsets[0], Y_hats[0]
        for i, (onset, Y_hat) in enumerate(zip(onsets[1:], Y_hats[1:])):
            horiz = onset.get_horizontal_potentials(onset_prev, Y_hat_prev, Y_hat, w)
            horiz += u[:, np.newaxis]
            am = np.argmax(horiz, axis=0)
            bt.append(am)
            u = horiz[am, np.arange(len(Y_hat))]

            u += onset.get_vertical_potentials(Y_hat, w)
            if loss_augmented:
                u += np.sum(Y_hat != Y[i+1][np.newaxis, :], axis=1)

            onset_prev, Y_hat_prev = onset, Y_hat

        # Backtracking
        y_hat = np.empty(sum(onset.note_count for onset in onsets), dtype='int')
        state = np.argmax(u)
        for i in reversed(range(len(onsets))):
            y_hat[onsets[i].indices] = Y_hats[i][state]
            state = bt[i][state]

        self.inference_calls += 1

        return y_hat


class OnsetChainModel(PyStructCRF):
    '''
    Implements our Model interface.
    '''
    def __init__(self, pre_processor):
        super().__init__(pre_processor, Model=OnsetChainPyStructModel)

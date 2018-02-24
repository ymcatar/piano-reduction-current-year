import music21

class HandAssignmentAlgorithm(object):

    def __init__(self, max_hand_span=7):

        self.config = {}
        self.config['max_hand_span'] = max_hand_span

    def start(self, measures):

        for i, item in enumerate(measures):
            offset, notes = item
            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            # for i, note in enumerate(notes):
            #     if i < 5:
            #         note.hand = 'L'
            #         note.finger = i + 1
            #     elif i < 10:
            #         note.hand = 'R'
            #         note.finger = i - 5 + 1
            self.get_number_of_cluster(notes)
        return []

    def get_number_of_cluster(self, notes, verbose=False):

        max_cluster_size = 2 * self.config['max_hand_span'] - 1
        notes = sorted(notes, key=lambda n: n.note.pitch.ps)
        ps_list = [n.note.pitch.ps for n in notes]

        if len(ps_list) == 1: # only one note => trivially one cluster
            if verbose: print(ps_list)
            return 1

        if ps_list[-1] - ps_list[0] <= max_cluster_size: # all notes are close together
            if verbose: print(ps_list)
            return 1

        # greedily expand the left cluster until it is impossible
        for i, item in enumerate(ps_list):
            if item - ps_list[0] > max_cluster_size:
                if verbose: print(str(ps_list[:i]) + ' | ', end='')
                return 1 + self.get_number_of_cluster(notes[i:], verbose=verbose)


    def cost(self, measures):

        # print(measures)
        return 0



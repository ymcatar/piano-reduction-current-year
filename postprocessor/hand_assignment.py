import music21

class HandAssignmentAlgorithm(object):

    @staticmethod
    def start(measures):
        for offset, notes in measures:
            for i, note in enumerate(notes):
                if i < 2:
                    note.hand = 'R'
                    note.finger = i + 1
                elif i < 4:
                    note.hand = 'L'
                    note.finger = i - 2 + 1
        return []

    @staticmethod
    def cost(assignment):
        # print(assignment)
        return 0



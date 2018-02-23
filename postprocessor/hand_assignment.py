import music21

class HandAssignmentAlgorithm(object):

    @staticmethod
    def start(measures):
        for offset, notes in measures:
            notes = [n for n in notes if not n.deleted]
            notes = sorted(notes, key=lambda n: n.note.pitch.ps)
            for i, note in enumerate(notes):
                if i < 5:
                    note.hand = 'L'
                    note.finger = i + 1
                elif i < 10:
                    note.hand = 'R'
                    note.finger = i - 5 + 1
        return []

    @staticmethod
    def cost(assignment):
        # print(assignment)
        return 0



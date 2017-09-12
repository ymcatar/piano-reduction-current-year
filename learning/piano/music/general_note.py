from ..base import PianoReductionObject

import music21

# multiple inheritance is used here because there is no better solution
# to let music21 recognize my data and adding more attributes together
class GeneralNote(PianoReductionObject, music21.note.GeneralNote):
    def __init__(self, ref):
        super(GeneralNote, self).__init__(ref)
        self._marks = dict()
        self._align = 0

    def addMark(self, key, value):
        self._marks[key] = value

    @property
    def marks(self):
        return self._marks

    # if the note is aligned or not, { 0, 1 }
    @property
    def align(self):
        return self._align

    @align.setter
    def align(self, align):
        self._align = align

    # to generate input data based on all labels provided
    def dataInput(self, allKeys=[]):
        ret = tuple([ ((key in self._marks) and [self._marks[key]] or [0])[0] for key in allKeys ])
        return ret

    @property
    def dataOutput(self):
        return (float(self.align))

    def addToDataSet(self, dataset=None, allKeys=[]):
        if dataset is None:
            return
        dataset.addSample(self.dataInput(allKeys), self.dataOutput)

    # classify a note based on a given network
    def classify(self, network=None, allKeys=[]):
        if network is None:
            self.align = 0
            return
        self.align = network.activate(self.dataInput(allKeys))[0]

    # classify a note based on linear combination and a threshold
    def threshold(self, allKeys=[], threshold=0):
            self.align = ((sum(self.dataInput(allKeys)) >= threshold) and [1] or [0])[0]

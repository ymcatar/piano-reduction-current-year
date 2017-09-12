from .not_rest import NotRest

import music21

class Chord(NotRest, music21.chord.Chord):
    def __init__(self, ref):
        super(Chord, self).__init__(ref)

    def addMark(self, key, value):
        for noteObj in self:
            noteObj._marks[key] = value

    def addToDataSet(self, dataset=None, allKeys=[]):
        for noteObj in self:
            noteObj.addToDataSet(dataset=dataset, allKeys=allKeys)

    def classify(self, network=None, allKeys=[]):
        if network is None:
            return
        for noteObj in self:
            noteObj.align = network.activate(noteObj.dataInput(allKeys))[0]

    def threshold(self, allKeys=[], threshold=0):
        for noteObj in self:
            noteObj.align = ((sum(noteObj.dataInput(allKeys)) >= threshold) and [1] or [0])[0]
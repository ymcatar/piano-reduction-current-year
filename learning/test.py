#!/usr/local/bin/python2

import os
import music21
import piano

xml_path = os.getcwd() + '/sample/'

targetXml = 'input/i_0000_Beethoven_op18_no1-4.xml'

sampleInXml = [
    'input/i_0000_Beethoven_op18_no1-4.xml',
    'input/i_0001_spring_sonata_I.xml'
]

sampleOutXml = [
    'output/o_0000_Beethoven_op18_no1-4.xml',
    'output/o_0001_spring_sonata_I.xml'
]

# ------------------------------------------------------------------------------
print('read music score from file')

# target score
converter = music21.converter.subConverters.ConverterMusicXML()
converter.parseFile(xml_path+targetXml)
target = piano.score.Score(converter.stream)

# sample input
sampleIn = []
for sample in sampleInXml:
    converter = music21.converter.subConverters.ConverterMusicXML()
    converter.parseFile(xml_path+sample)
    sampleIn.append(piano.score.Score(converter.stream))
sampleOut = []
for sample in sampleOutXml:
    converter = music21.converter.subConverters.ConverterMusicXML()
    converter.parseFile(xml_path+sample)
    sampleOut.append(piano.score.Score(converter.stream))


# ------------------------------------------------------------------------------
print('building model')

# Guessing (include everything)
reducer = piano.reducer.Reducer(target)
reducer.addReductionAlgorithm(piano.algorithm.OnsetAfterRest())
#reducer.addReductionAlgorithm(piano.algorithm.StrongBeats(division=1))
reducer.addReductionAlgorithm(piano.algorithm.StrongBeats(division=0.5))
#reducer.addReductionAlgorithm(piano.algorithm.StrongBeats(division=0.25))
reducer.addReductionAlgorithm(piano.algorithm.ActiveRhythm())
reducer.addReductionAlgorithm(piano.algorithm.SustainedRhythm())
reducer.addReductionAlgorithm(piano.algorithm.RhythmVariety())
reducer.addReductionAlgorithm(piano.algorithm.VerticalDoubling())
reducer.addReductionAlgorithm(piano.algorithm.Occurrence())
reducer.addReductionAlgorithm(piano.algorithm.PitchClassStatistics(before=0, after=0))
reducer.addReductionAlgorithm(piano.algorithm.BassLine())
reducer.addReductionAlgorithm(piano.algorithm.EntranceEffect())


# ------------------------------------------------------------------------------
print('initialize training network and example')

for x in range(0, len(sampleIn)):
    reducer.addTrainingExample(sampleIn[x], sampleOut[x])
reducer.initAlgorithmKeys()
reducer.createAllMarkings()
reducer.createAlignmentMarkings()

dataset = None
for x in range(0, len(sampleIn)):
    dataset = sampleIn[x].TrainingDataSet(reducer=reducer, dataset=dataset)

# single layer
#network = piano.learning.buildNetwork(len(reducer.allKeys), 0, 1, bias=True, seed=0)

# multi layer
network = piano.learning.buildNetwork(len(reducer.allKeys), len(reducer.allKeys) * 2, 1, bias=True, seed=0)

trainer = piano.learning.BackpropTrainer(network, dataset, verbose=True)
print(reducer.allKeys)

# ------------------------------------------------------------------------------
print('show result')
result = music21.stream.Score()

trainer.trainUntilConvergence(maxEpochs = 300)
#trainer.trainUntilConvergence()
target.classify(network=network, reducer=reducer)
final_result = target.generatePianoScore(reduced=True, playable=True)

final_result.show('musicxml')


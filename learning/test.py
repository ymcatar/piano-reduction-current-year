# Run this script as:
#   python3 -m learning.test

import os
import music21
from . import piano

xml_path = os.getcwd() + '/sample/'

target_xml = 'input/i_0001_spring_sonata_I.xml'
target_xml = 'input/i_0000_Beethoven_op18_no1-4.xml'


sample_in_xml = [
    'input/i_0000_Beethoven_op18_no1-4.xml',
]

sample_out_xml = [
    'output/o_0000_Beethoven_op18_no1-4.xml',
]

# ------------------------------------------------------------------------------
print('read music score from file')

# target score
score = music21.converter.parse(xml_path + target_xml, format='musicxml')
target = piano.score.ScoreObject(score)

# sample input

sample_in = []
for sample in sample_in_xml:
    score = music21.converter.parse(xml_path + sample, format='musicxml')
    sample_in.append(piano.score.ScoreObject(score))

sample_out = []
for sample in sample_out_xml:
    score = music21.converter.parse(xml_path + sample, format='musicxml')
    sample_out.append(piano.score.ScoreObject(score))


# ------------------------------------------------------------------------------
print('building reducer')

# Guessing (include everything)
reducer = piano.reducer.Reducer(
    algorithms=[
        piano.algorithm.ActiveRhythm(),
        piano.algorithm.BassLine(),
        piano.algorithm.EntranceEffect(),
        piano.algorithm.Occurrence(),
        piano.algorithm.OnsetAfterRest(),
        piano.algorithm.PitchClassStatistics(),
        piano.algorithm.RhythmVariety(),
        piano.algorithm.StrongBeats(division=0.5),
        piano.algorithm.SustainedRhythm(),
        piano.algorithm.VerticalDoubling(),
        ])

# ------------------------------------------------------------------------------
print('extracting features for training data')

X = reducer.create_markings_on(sample_in)
import numpy as np
assert np.all(X == reducer.create_markings_on(sample_in))
y = reducer.create_alignment_markings_on(sample_in, sample_out)


if __name__ == '__main__':
    from sklearn.linear_model import LogisticRegression

    print('training ML model')
    print(reducer.all_keys)
    model = LogisticRegression()
    model.fit(X, y)
    print('Training accuracy = {}'.format(model.score(X, y)))

    X_test = reducer.create_markings_on(target)
    y_test = reducer.predict_from(model, target, X=X_test)

    for i, n in enumerate(reducer.iter_notes(target)):
        shade = int(n.editorial.misc['align'] * 255)
        n.style.color = '#{:02X}0000'.format(shade)

    target.score.show('musicxml')

    post_processor = piano.post_processor.PostProcessor()
    result = post_processor.generate_piano_score(target, reduced=True,
                                                 playable=True)
    result.show('musicxml')

'''
Utilities for literate programming. Use it like this:

    from experiments.util.literate import *

Make sure you install the dependencies from requirement-dev.txt
'''

from IPython.display import display, HTML

import numpy as np
from matplotlib import pyplot as plt
import music21


__all__ = ['np', 'plt', 'music21', 'show_score', 'show_score_and_save']

def show_score(filename):
    stream = music21.converter.parse(filename)
    stream.show()
    display(HTML('''
        <p><a href="{}" download>Download XML</a></p>
        '''.format(filename)))


def show_score_and_save(stream, basename):
    '''
    Displays the score and writes the associated XML file. Also outputs HTML
    tags to link to them.
    '''

    stream.show()
    stream.write('musicxml', basename + '.xml')

    display(HTML('''
        <p><a href="{}.xml" download>Download XML</a></p>
        '''.format(basename)))

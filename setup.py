from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy as np


setup(
    cmdclass={'build_ext': build_ext},
    ext_modules=[
        Extension('learning.piano.onset_chain_ext',
                  ['learning/piano/onset_chain_ext.pyx'],
                  include_dirs=[np.get_include()])
        ],
    )


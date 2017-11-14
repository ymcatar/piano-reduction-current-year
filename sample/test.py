# used to test if a musicxml is readable by music21

import sys
import music21

if len(sys.argv) != 2:
    print("Usage: $0 [path of the input MusicXML file]")
    exit()

try:
    music21.converter.parse(sys.argv[1])
    print('YES')
except:
    raise


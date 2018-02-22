import math
import music21
import vpython as vp
import threading

from collections import defaultdict
from music21.midi.realtime import StreamPlayer
from music21.stream import Stream

from util import isNote, isChord
from note_wrapper import NoteWrapper

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

class Visualizer(object):

    def __init__(self, score):

        self.score = score
        self.current_offset = 0
        self.active = {}

        self.keyboards = {}
        self.left = {}
        self.right = {}

        self.read_from_score()
        self.render()
        self.play()

    def read_from_score(self):

        # get all measures from the score
        self.measures = list(self.score.recurse(
            skipSelf=True).getElementsByClass('Measure'))

        # group measures with the same offset together
        self.grouped_measures = defaultdict(lambda: [])
        for measure in self.measures:
            self.grouped_measures[str(measure.offset)].append(measure)

        # group notes starting at the same time instance together
        self.grouped_onsets = defaultdict(lambda: [])
        for _, group in self.grouped_measures.items():
            for measure in group:
                measure = measure.stripTies(retainContainers=True, inPlace=True)
                offset_map = measure.offsetMap()
                for item in offset_map:
                    offset = measure.offset + item.offset
                    offset_label = '{0:.2f}'.format(offset)
                    if isChord(item.element):
                        for note in item.element._notes:
                            wappedNote = NoteWrapper(note, offset, item.element)
                            self.grouped_onsets[offset_label].append(wappedNote)
                    elif isNote(item.element):  # note or rest
                        note = NoteWrapper(item.element, offset)
                        self.grouped_onsets[offset_label].append(note)

    def render(self):

        # constants
        nts = ("C", "D", "E", "F", "G", "A", "B")
        tol = 0.12
        keybsize = 16.5  # cm, span of one octave
        wb = keybsize / 7.0
        nr_octaves = 7
        span = nr_octaves * wb * 7.0

        # visualization code modified from https://github.com/marcomusy/piano-fingering
        # initialize scene

        scene = vp.canvas(x=0, y=0, width=1400.0, height=600.0, userspin=True, center=vp.vector(75., 0., 0.), fov=math.pi/8.0, background=vp.vector(.95, .95, .95))
        scene.camera.rotate(angle=-math.pi/4.0, axis=vp.vector(1., 0., 0.))
        vp.lights = []
        vp.distant_light(direction=vp.vector(0., 1000., 0.), color=vp.color.white)

        # draw keyboard
        vp.box(pos=vp.vector(span/2 + keybsize, -1., -1), length=span+2, height=1, width=15, texture=vp.textures.wood)

        for ioct in range(nr_octaves):
            for ik in range(7):  # white keys
                x = ik * wb + (ioct + 1.0) * keybsize + wb / 2.0
                tb = vp.box(pos=vp.vector(x, 0., 0), length=wb-tol, shininess=0.0, height=1.0, width=10, up=vp.vector(0, 1, 0), color=vp.vector(1., 1., 1.))
                self.keyboards[nts[ik] + str(ioct + 1)] = tb
                if not nts[ik] in ("E", "B"):  # black keys
                    tn = vp.box(pos=vp.vector(x + wb / 2, 0.5, -2), shininess=0.0, length=wb * .6, height=1.0, width=6, up=vp.vector(0, 1, 0), color=vp.vector(0., 0., 0.))
                    self.keyboards[nts[ik] + "#" + str(ioct + 1)] = tn

        # draw left hand
        self.left[1] = vp.cylinder(pos=vp.vector(-2., 1.5, 4.5), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.left[2] = vp.cylinder(pos=vp.vector(-1., 1.5, 4.1), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.left[3] = vp.cylinder(pos=vp.vector( 0., 1.5, 4),   axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.left[4] = vp.cylinder(pos=vp.vector( 1., 1.5, 4.2), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.left[5] = vp.cylinder(pos=vp.vector( 2., 1.5, 6.2), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)

        # draw right hand
        self.right[1] = vp.cylinder(pos=vp.vector( 5., 1.5, 6.2), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.right[2] = vp.cylinder(pos=vp.vector( 6., 1.5, 4.2), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.right[3] = vp.cylinder(pos=vp.vector( 7., 1.5, 4),   axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.right[4] = vp.cylinder(pos=vp.vector( 8., 1.5, 4.1), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)
        self.right[5] = vp.cylinder(pos=vp.vector( 9., 1.5, 4.5), axis=vp.vector(0., 0., 5.), radius=.2, color=vp.color.red)

    # TODO: B- => A# etc.
    def draw_onsets(self):
        current_label = '{0:.2f}'.format(self.current_offset / 20)
        if current_label in self.grouped_onsets:
            # unhiglight the previously active key
            active_keys = [i for i in self.active.keys()]
            for name in active_keys:
                if '#' in name:
                    self.keyboards[name].color = vp.vector(0., 0., 0.) # black key
                else:
                    self.keyboards[name].color = vp.vector(1., 1., 1.) # white key
                del self.active[name]
            # prepare midi stream
            # stream = Stream()
            # highlight the active key
            for note in self.grouped_onsets[current_label]:
                # stream.append(note.note)
                name = note.note.nameWithOctave
                self.active[name] = True
                self.keyboards[name].color = vp.color.yellow

            # sp = StreamPlayer(stream)
            # sp.play()


    def play(self):

        def helper():
            self.draw_onsets()
            self.current_offset += 1

        set_interval(helper, 0.05)


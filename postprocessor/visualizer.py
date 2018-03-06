import math
import music21
import random
import threading
import vpython as vp

from collections import defaultdict

from util import isNote, isChord
from note_wrapper import NoteWrapper
from algorithms import PostProcessorAlgorithms
from hand_assignment import HandAssignmentAlgorithm

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

colors = {
    'white': vp.vector(1.0, 1.0, 1.0),
    'black': vp.vector(0.0, 0.0, 0.0),
    'left_primary': vp.vector(0.4, 0.12, 1.0),
    'left_secondary': vp.vector(0.58, 0.46, 0.8),
    'right_primary': vp.vector(1.0, 0.57, 0.0),
    'right_secondary': vp.vector(1.0, 0.8, 0.5),
    'unassigned_primary': vp.vector(1.0, 0.0, 0.0),
    'unassigned_secondary': vp.vector(0.5, 0.5, 0.5)
}

class Visualizer(object):

    def __init__(self, score):

        self.hand_assignment = HandAssignmentAlgorithm()

        self.score = score
        self.current_offset = 0
        self.active = {}

        self.keyboards = {}
        self.left = {}
        self.right = {}
        self.text = None

        self.read_from_score()
        self.render()
        self.draw_frame()

    def read_from_score(self):

        # get all measures from the score
        self.measures = list(self.score.recurse(skipSelf=True).getElementsByClass('Measure'))

        # # group measures with the same offset together
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

        for item in self.grouped_onsets.items():
            offset, notes = item
            PostProcessorAlgorithms.repeated_note([item]) # remove repeated notes
            self.grouped_onsets[offset] = [n for n in notes if not n.deleted]

        keys = [float(i) for i in self.grouped_onsets.keys()]
        self.sustained_onsets = defaultdict(lambda: [])
        for offset, notes in self.grouped_onsets.items():
            for note in notes:
                if not note.deleted:
                    start = float(offset)
                    end = start + note.note.duration.quarterLength
                    sites = ['{0:.2f}'.format(i) for i in keys if i > start and i < end]
                    for item in sites:
                        self.sustained_onsets[item].append(note)

        self.onset_keys = [i for i in self.grouped_onsets.keys()]

    def render(self):

        # constants
        nts = ("C", "D", "E", "F", "G", "A", "B")
        tol = 0.12
        keybsize = 16.5
        wb = keybsize / 7.0
        nr_octaves = 7
        span = nr_octaves * wb * 7.0 + wb

        # visualization code modified from https://github.com/marcomusy/piano-fingering

        # initialize scene

        scene = vp.canvas(x=0, y=0, width=1400.0, height=600.0,
                          userspin=True, center=vp.vector(75., 0., 0.),
                          fov=math.pi/4.0, background=vp.vector(.95, .95, .95))

        scene.camera.rotate(angle=-math.pi/4.0, axis=vp.vector(1., 0., 0.))

        vp.lights = []
        vp.distant_light(direction=vp.vector(0., 1000., 0.), color=vp.color.white)

        # draw keyboard

        vp.box(pos=vp.vector(span/2 + keybsize, -1., -1), length=span + 5, height=1, width=15, texture=vp.textures.wood)

        current_step = 12 # 12 = C0

        for ioct in range(nr_octaves + 1):
            if ioct == nr_octaves:
                # one extra C white key
                x = (ioct + 1.0) * keybsize + wb / 2.0
                tb = vp.box(pos=vp.vector(x, 0., 0),
                            length=wb-tol, shininess=0.0,
                            height=1.0, width=10,
                            up=vp.vector(0, 1, 0),
                            color=colors['white'])
                self.keyboards[current_step] = tb
            else:
                for ik in range(7):
                    x = ik * wb + (ioct + 1.0) * keybsize + wb / 2.0
                    tb = vp.box(pos=vp.vector(x, 0., 0),
                                length=wb-tol, shininess=0.0,
                                height=1.0, width=10,
                                up=vp.vector(0, 1, 0),
                                color=colors['white'])
                    self.keyboards[current_step] = tb
                    current_step += 1
                    # black keys
                    if not nts[ik] in ("E", "B"):
                        tn = vp.box(pos=vp.vector(x + wb / 2, 0.5, -2),
                                    shininess=0.0, length=wb * .6,
                                    height=1.5, width=6,
                                    up=vp.vector(0, 1, 0),
                                    color=colors['black'])
                        self.keyboards[current_step] = tn
                        current_step += 1

        # draw hands
        for i in range(1, 6):
            self.left[i] = vp.text( font='serif', axis=vp.vector(1, 0, 0),
                                    up=vp.vector(0, 0, -1), align='center',
                                    pos=vp.vector(75, 1.1, 0), text=str(i),
                                    depth=0.01, height=1.5,
                                    color=colors['black'])
            self.right[i] = vp.text(font='serif', axis=vp.vector(1, 0, 0),
                                    up=vp.vector(0, 0, -1), align='center',
                                    pos=vp.vector(75, 1.1, 0), text=str(i),
                                    depth=0.01, height=1.5,
                                    color=colors['black'])
            self.left[i].visible = False
            self.right[i].visible = False

        # bind next frame click handler
        def keydown(evt):
            s = evt.key
            if s in ('right', 'down'):
                self.next_frame()
            elif s in ('left', 'up'):
                self.prev_frame()

        scene.bind('click', self.next_frame)
        scene.bind('keydown', keydown)

    def draw_frame(self):

        current_label = self.onset_keys[self.current_offset]

        if self.text:
            self.text.visible = False
            self.text = None

        # unhiglight the previously active key
        active_keys = [i for i in self.active.keys()]
        for step in active_keys:
            temp = [math.trunc(n.note.pitch.ps) for n in self.sustained_onsets[current_label]]  # TODO: optimize
            if step not in temp:
                if step % 12 in (1, 3, 6, 8, 10):
                    self.keyboards[step].color = colors['black']  # black key
                else:
                    self.keyboards[step].color = colors['white']  # white key
                del self.active[step]

        active_left = {}
        active_right = {}

        # highlight the active key
        def highlight_note(note, onset=True):

            step = math.trunc(note.note.pitch.ps)

            if step not in self.keyboards:
                print("Error: pitch to be highlighted not on piano keyboard (" + str(step) + ")")
                return

            self.active[step] = True

            # move finger to the key
            if note.note.editorial.misc.get('hand') and note.note.editorial.misc.get('finger'):

                hand = note.note.editorial.misc.get('hand')
                finger = note.note.editorial.misc.get('finger')

                if onset:
                    self.keyboards[step].color = colors['left_primary'] if hand == 'L' else colors['right_primary']
                    active_hand = active_left if hand == 'L' else active_right
                    hand = self.left if hand == 'L' else self.right

                    active_hand[finger] = True
                    hand[finger].pos.x = self.keyboards[step].pos.x

                    if step % 12 in (1, 3, 6, 8, 10):
                        hand[finger].pos.y = 1.5
                        hand[finger].pos.z = 0.5
                    else:
                        hand[finger].pos.y = 0.5
                        hand[finger].pos.z = 4.5
                else:
                    self.keyboards[step].color = colors['left_secondary'] if hand == 'L' else colors['right_secondary']

            else:
                if onset:
                    self.keyboards[step].color = colors['unassigned_primary']
                else:
                    self.keyboards[step].color = colors['unassigned_secondary']

        for note in self.sustained_onsets[current_label]:
            highlight_note(note, onset=False)

        for note in self.grouped_onsets[current_label]:
            highlight_note(note)

        for i in range(1, 6):
            self.left[i].visible = i in active_left
            self.right[i].visible = i in active_right

        # show the current onset as a text

        helptext = '{:s} / {:s} ({:d})'.format(
            current_label,
            self.onset_keys[-1],
            self.hand_assignment.get_number_of_cluster(self.grouped_onsets[current_label], verbose=False)
        )

        self.text = vp.label(pos=vp.vector(75., 15., 0.),
                             font='monospace',
                             box=False, border=0,
                             height=25, text=helptext,
                             align='center', color=colors['black'])

    def next_frame(self):
        self.current_offset += 1
        self.current_offset %= len(self.onset_keys)
        self.draw_frame()

    def prev_frame(self):
        self.current_offset -= 1
        if self.current_offset == -1:
            self.current_offset = len(self.onset_keys) - 1
        self.draw_frame()



import music21
import vpython as vp

# modified from https://github.com/marcomusy/piano-fingering

class Visualizer(object):

    def __init__(self):

        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 #cm, span of one octave
        wb = keybsize/7.
        nr_octaves = 7
        span = nr_octaves*wb*7.

        vp.canvas(x=0, y=0, width=1400./1., height=600./1., center=vp.vector(75,0,0), forward=vp.vector(0.,-2,-1.), background=vp.vector(0., 0.25, 0.0))
        # wooden top and base
        vp.box(pos=vp.vector(span/2+keybsize,-1.,-3),length=span+1, height=1, width=17)
        vp.box(pos=vp.vector(span/2+keybsize, 1, -8),length=span+1, height=3, width=7)
        # leggio
        leggio = vp.box(pos=vp.vector(75, 8., -12.), length=span/2, height=span/8, width=0.08, color=vp.vector(1,1,0.9))
        leggio.rotate(angle=-0.4)

        for ioct in range(nr_octaves):
            for ik in range(7): # white keys
                x  = ik * wb + (ioct+1.)*keybsize +wb/2.
                tb = vp.box(pos=vp.vector(x,0.,0), length=wb-tol, height=1, width=10, up=vp.vector(0,1,0), color=vp.vector(1,1,1))
                #  self.KB.update({nts[ik]+str(ioct+1) : tb})
                if not nts[ik] in ("E","B"): # black keys
                    tn=vp.box(pos=vp.vector(x+wb/2,wb/2,-2), length=wb*.6, height=1, width=6, up=vp.vector(0,1,0), color=vp.vector(0,0,0))
                    # self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})


test = Visualizer()

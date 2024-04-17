'''
Play an infinite sequence of beeps to the soundcard

n.b. requires PyAudio to be installed.
'''

import audiogen
import itertools

audiogen.sampler.play(
    itertools.cycle(itertools.chain(audiogen.beep(), audiogen.silence(0.5))),
)

'''
Play a 440 Hz tone to the soundcard

n.b. requires PyAudio to be installed.
'''

import audiogen

audiogen.sampler.play(audiogen.tone(440))

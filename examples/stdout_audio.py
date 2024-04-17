'''
Example of outputting audio samples to /dev/stdout

You'll want to pipe the samples somewhere useful, e.g. sox:

    $ python examples/stdout_audio.py | play -t wav -

e.g.

    $ python examples/stdout_audio.py > beeps.wav
      ...
      Ctrl-C

Note that if you redirect to a file, you'll have to Ctrl-C to end
the file, since this is an infinite cycle of beeps.
'''
import audiogen
import itertools
import sys

beep_silence = itertools.chain(audiogen.beep(), audiogen.silence(0.5))
infinite_beeps = itertools.cycle(beep_silence)

audiogen.sampler.write_wav(sys.stdout, infinite_beeps)

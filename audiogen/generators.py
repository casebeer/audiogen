# coding=utf8

'''
Assorted generators
'''

from __future__ import absolute_import
import math
import itertools

from . import util
from . import sampler

TWO_PI = 2 * math.pi

# Audio sample generators


def beep(frequency=440, seconds=0.25):
    for sample in util.crop_with_fades(tone(frequency), seconds=seconds):
        yield sample


def tone(frequency=440, min_=-1, max_=1):
    def fixed_tone(frequency):
        period = int(sampler.FRAME_RATE / frequency)
        time_scale = 2 * math.pi / period  # period * scale = 2 * pi
        # precompute fixed tone samples
        # TODO: what about phase glitches at end?
        samples = [math.sin(i * time_scale) for i in range(period)]
        while True:
            for i in range(period):
                yield samples[i]

    def variable_tone(frequency):
        time_scale = TWO_PI / sampler.FRAME_RATE
        phase = 0
        for f in frequency:
            yield math.sin(phase)

            phase += time_scale * f

            # don't reset hard to zero – avoids sudden phase glitches due
            # to rounding error
            if phase > TWO_PI:
                phase -= TWO_PI

    if not hasattr(frequency, '__next__'):
        gen = fixed_tone(frequency)
    else:
        gen = variable_tone(frequency)
    return util.normalize(gen, -1, 1, min_, max_)


def synth(freq, angles):
    if isinstance(angles, (int, float)):
        # argument was just the end angle
        angles = [0, angles]
    gen = tone(freq)

    two_pi = 2.0 * math.pi
    normalized_freq = sampler.FRAME_RATE / freq
    samples = list(itertools.islice(gen,
                                    normalized_freq * angles[1] / two_pi))
    index = int((sampler.FRAME_RATE / freq) * (angles[0] / (2.0 * math.pi)))
    loop = samples[index:]
    while True:
        for sample in loop:
            yield sample


def silence(seconds=None):
    if seconds is not None:
        for i in range(int(sampler.FRAME_RATE * seconds)):
            yield 0
    else:
        while True:
            yield 0

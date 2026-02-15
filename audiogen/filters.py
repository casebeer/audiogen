# coding=utf8

'''
Assorted filters
'''

import math
import itertools
import collections

import audiogen.util as util
import audiogen.sampler as sampler

TWO_PI = 2 * math.pi

def iir(A, B):
    # Returns an IIR filter function based on the
    # provided input and output coefficient arrays
    #
    def filter(in_):
        input_ = iter(in_)
        # use deques as ring buffers
        outputs = collections.deque([0] * max(len(B), 1), maxlen=max(len(B), 1))
        inputs =  collections.deque([0] * len(A), maxlen=len(A))
        try:
            while True:
                inputs.appendleft(next(input_))
                y = sum(a * i for a, i in zip(A, inputs)) \
                    + sum(b * o for b, o in zip(B, outputs))
                yield outputs.pop()
                outputs.appendleft(y)
        except StopIteration:
            # clear the remaining samples in the buffer
            while len(outputs) > 0:
                yield outputs.pop()
    return filter

def band_pass(center, bandwidth):
    # Bandpass IIR filter
    #
    # Center frequency and bandwidth in fractions of sampling rate
    # Bandwidth is the -3 dB bandwidth
    # http://www.dspguide.com/ch19/3.htm
    #

    f = float(center) / sampler.FRAME_RATE
    bw = float(bandwidth) / sampler.FRAME_RATE

    R = 1 - 3 * bw
    K = (1 - 2 * R * math.cos(TWO_PI * f) + R ** 2) / (2 - 2 * math.cos(TWO_PI * f))

    a0 = 1 - K
    a1 = 2 * (K - R) * math.cos(TWO_PI * f)
    a2 = R ** 2 - K
    b1 = 2 * R * math.cos(TWO_PI * f)
    b2 = -R ** 2

    return iir([a0, a1, a2], [b1, b2])


def band_stop(center, bandwidth):
    # Band rejection IIR filter
    #
    # Center frequency and bandwidth in fractions of sampling rate
    # Bandwidth is the -3 dB bandwidth
    # http://www.dspguide.com/ch19/3.htm
    #
    f = float(center) / sampler.FRAME_RATE
    bw = float(bandwidth) / sampler.FRAME_RATE

    R = 1 - 3 * bw
    K = (1 - 2 * R * math.cos(TWO_PI * f) + R ** 2) / (2 - 2 * math.cos(TWO_PI * f))

    a0 = K
    a1 = -2 * K * math.cos(TWO_PI * f)
    a2 = K
    b1 = 2 * R * math.cos(TWO_PI * f)
    b2 = -R ** 2

    return iir([a0, a1, a2], [b1, b2])

def low_pass(cutoff: float):
    '''
    Single pole low pass IIR filter

    `cutoff` is cutoff frequency in Hz.

    http://www.dspguide.com/ch19/2.htm
    '''
    # normalized cutoff frequency
    fc = float(cutoff) / sampler.FRAME_RATE
    #rc_time_constant_samples = float(rc_time_constant) * sampler.FRAME_RATE

    # determine decay coefficient x from cutoff frequency
    x = math.exp(-TWO_PI * fc)

    # determine decay coefficient x from RC time constant
    #x = math.exp(-1.0 / rc_time_constant_samples)

    a0 = 1 - x
    b1 = x
    return iir([a0], [b1])

def low_pass_four_stage(cutoff: float):
    '''
    Four stage low pass IIR filter

    Equivalent to cascading single pole LPF four times.

    `cutoff` is cutoff frequency in Hz.

    http://www.dspguide.com/ch19/2.htm
    '''

    # normalized cutoff frequency
    fc = float(cutoff) / sampler.FRAME_RATE
    #rc_time_constant_samples = float(rc_time_constant) * sampler.FRAME_RATE

    # determine decay coefficient x from cutoff frequency
    x = math.exp(-TWO_PI * fc)

    # determine decay coefficient x from RC time constant
    #x = math.exp(-1.0 / rc_time_constant_samples)

    a0 = math.pow(1 - x, 4)
    b1 = 4 * x
    b2 = -6 * math.pow(x, 2)
    b3 = 4 * math.pow(x, 3)
    b4 = -1 * math.pow(x, 4)
    return iir([a0], [b1, b2, b3, b4])

def high_pass(cutoff: float):
    '''
    High pass IIR filter

    `cutoff` is cutoff frequency in Hz.

    http://www.dspguide.com/ch19/2.htm
    '''
    # normalized cutoff frequency
    fc = float(cutoff) / sampler.FRAME_RATE
    #rc_time_constant_samples = float(rc_time_constant) * sampler.FRAME_RATE

    # determine decay coefficient x from cutoff frequency
    x = math.exp(-TWO_PI * fc)

    # determine decay coefficient x from RC time constant
    #x = math.exp(-1.0 / rc_time_constant_samples)

    a0 = (1 + x) / 2.
    a1 = -(1 + x) / 2.
    b1 = x
    return iir([a0, a1], [b1])

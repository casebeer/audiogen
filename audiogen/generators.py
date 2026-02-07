# coding=utf8

'''
Assorted generators
'''

import logging
logger = logging.getLogger(__name__)

import math
import itertools

import audiogen.util as util
import audiogen.sampler as sampler
import audiogen.filters as filters

TWO_PI = 2 * math.pi

## Audio sample generators

bpf_cache = {}
def beep(frequency=440, seconds=0.25, use_bpf=True):
    if use_bpf:
        if frequency not in bpf_cache:
            bandwidth = max(frequency // 2 ** 6, 128)
            logger.debug('Creating {} Hz BPF centered at {} Hz for beep'.format(bandwidth, frequency))
            bpf_cache[frequency] = filters.band_pass(frequency, bandwidth)
        bpf = bpf_cache[frequency]
        # lower volume 0.25 dB (~95% full scale) so BPF ripple doesn't exceed 0 dbFS
        for sample in bpf(bpf(itertools.chain(
            util.crop(util.volume(tone(frequency), -0.25), seconds=(seconds - 0.03)),
            silence(0.03)
            ))):
            yield sample
    else:
        #for sample in util.crop_with_fades(tone(frequency), seconds=seconds):
        for sample in util.crop(tone(frequency), seconds=seconds):
            yield sample


class DDS(object):
    accumulatorBits = 24
    lutBits = 14

    # lut will be generated once on first use of DDS.dds() or by calling DDS.generateLut() directly
    lut = None

    @classmethod
    def generateLut(cls):
        import time
        import sys
        phasePerLutItem = 2 * math.pi / 2 ** cls.lutBits
        start = time.time()
        cls.lut = [ math.sin(i * phasePerLutItem) for i in range(2 ** cls.lutBits) ]
        generationTime = time.time() - start
        logger.debug('[dds] Generated DDS LUT in {} seconds'.format(generationTime))
        logger.debug('[dds] {} bit phase accumulator, {} bit DDS LUT'.format(
            cls.accumulatorBits,
            cls.lutBits,
        ))
        logger.debug('[dds] {} bit ({:,} entry) LUT takes {:,} bytes of memory ({} bits / entry)'.format(
            cls.lutBits,
            2 ** cls.lutBits,
            sys.getsizeof(cls.lut),
            sys.getsizeof(cls.lut) / 2 ** cls.lutBits * 8,
        ))

    @classmethod
    def dds(cls, freqHz, phaseOffsetRad=0):
        # https://www.allaboutcircuits.com/technical-articles/basics-of-phase-truncation-in-direct-digital-synthesizers/
        if cls.lut is None:
            cls.generateLut()
        accumulatorSize = 2 ** cls.accumulatorBits

        freqNorm = float(freqHz) / sampler.FRAME_RATE # 1 / samples
        deltaPhase = int(round(freqNorm * accumulatorSize)) # accumulatorPhases / sample

        logger.debug('[dds][acc] frequency resolution ≈ {} Hz'.format(
            round(float(sampler.FRAME_RATE) / accumulatorSize, 5)))
        logger.debug('[dds][acc] phase accumulator will overflow every {} seconds ({} Hz)'.format(
            round(float(accumulatorSize) / deltaPhase / sampler.FRAME_RATE, 5),
            round(float(deltaPhase) / accumulatorSize * sampler.FRAME_RATE, 5),
            ))
        logger.debug('[dds][lut] phase truncation spurs ~ {} dB below fundamental'.format(6.08 * cls.lutBits))

        phaseAccumulator = int(0 + phaseOffsetRad / freqNorm) % accumulatorSize
        truncateBits = cls.accumulatorBits - cls.lutBits
        while True:
            phaseAccumulator += deltaPhase
            if phaseAccumulator >= accumulatorSize:
                phaseAccumulator -= accumulatorSize
            yield cls.lut[phaseAccumulator >> truncateBits]

def dds(freqHz=440, phaseOffsetRad=0):
    return DDS.dds(freqHz, phaseOffsetRad)

def tone(frequency=440, phase_offset=0, min_=-1, max_=1, frame_rate=None):
    return DDS.dds(frequency)

    if frame_rate is None:
        frame_rate = sampler.FRAME_RATE
    def fixed_tone(frequency):
        frequencyHz = float(frequency)
        periodf = float(frame_rate) / frequency
        period = int(frame_rate / frequency)
        time_scale = 2 * math.pi / periodf # period * scale = 2 * pi
        # precompute fixed tone samples # TODO: what about phase glitches at end?

        logger.debug('Periodf is {}'.format(periodf))

        def phase_indexes():
            phase_index_offset = int(phase_offset / time_scale)
            for i in xrange(period * 1):
                phase_index = i + phase_index_offset
                if phase_index >= period:
                    phase_index -= period
                elif phase_index < 0:
                    phase_index += period
                yield phase_index

        #frequency                        # 1 / seconds
        freqNorm = frequencyHz / frame_rate # 1 / samples
        period = 1. / frequency           # seconds
        periodNorm = 1. / freqNorm        # samples

        # every periodNorm samples we want sin(sample) to cycle;
        # i.e. sin(periodNorm * cyclesPerSample) = sin(2 * PI)

        cyclesPerSample = 2 * math.pi / periodNorm # 1 / samples

        samples = [math.sin(i * cyclesPerSample) for i in range(int(periodNorm * 2))]

        #samples = [math.sin(i * time_scale) for i in phase_indexes()]
        #samples = [math.sin(i * time_scale) for i in range(int(periodf * 1))]
        #samples = [math.sin(i * samples_per_second) for i in range(int(periodf * 1))]

        return itertools.cycle(samples)

    def variable_tone(frequency):
        time_scale = TWO_PI / frame_rate
        phase = phase_offset
        for f in frequency:
            yield math.sin(phase)

            phase += time_scale * f

            # don't reset hard to zero – avoids sudden phase glitches due to rounding error
            if phase > TWO_PI:
                phase -= TWO_PI
            elif phase < 0:
                phase += TWO_PI

    if not hasattr(frequency, 'next'):
        gen = fixed_tone(frequency)
    else:
        gen = variable_tone(frequency)
    return util.normalize(gen, -1, 1, min_, max_)

def synth(freq, angles):
	if isinstance(angles, (int, float)):
		# argument was just the end angle
		angles = [0, angles]
	gen = tone(freq)
	loop = list(itertools.islice(gen, (sampler.FRAME_RATE / freq) * (angles[1] / (2.0 * math.pi))))[int((sampler.FRAME_RATE / freq) * (angles[0] / (2.0 * math.pi))):]
	while True:
		for sample in loop:
			yield sample

def silence(seconds=None):
	if seconds != None:
		for i in range(int(sampler.FRAME_RATE * seconds)):
			yield 0
	else:
		while True:
			yield 0

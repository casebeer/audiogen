# coding=utf8

'''
Assorted generators 
'''

import math
import itertools

import util
import sampler

TWO_PI = 2 * math.pi

## Audio sample generators

def beep(frequency=440, seconds=0.25):
	for sample in util.crop_with_fades(tone(frequency), seconds=seconds):
		yield sample

def tone(frequency=440, phase_offset=0, min_=-1, max_=1):
	def fixed_tone(frequency):
		period = int(sampler.FRAME_RATE / frequency) 
		time_scale = 2 * math.pi / period # period * scale = 2 * pi
		# precompute fixed tone samples # TODO: what about phase glitches at end?

		def phase_indexes():
			phase_index_offset = int(phase_offset / time_scale)
			for i in xrange(period):
				phase_index = i + phase_index_offset
				if phase_index >= period:
					phase_index -= period
				elif phase_index < 0:
					phase_index += period
				yield phase_index
		
		samples = [math.sin(i * time_scale) for i in phase_indexes()]
		return itertools.cycle(samples)

	def variable_tone(frequency):
		time_scale = TWO_PI / sampler.FRAME_RATE
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


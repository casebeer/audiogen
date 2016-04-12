# coding=utf8

'''
Assorted filters
'''

import math
import itertools
import collections

import util
import sampler

TWO_PI = 2 * math.pi

def iir(a, b):
	def filter(in_):
		# use deques as ring buffers
		outputs = collections.deque([0] * 2, maxlen=2)
		inputs =  collections.deque([0] * 3, maxlen=3)
		try:
			while True:
				inputs.append(next(in_))
				y = a[0] * inputs[-1] + a[1] *  inputs[-2] + a[2] *  inputs[-3]\
									  + b[0] * outputs[-1] + b[1] * outputs[-2] 
				yield outputs.popleft()
				outputs.append(y)
		except StopIteration:
			# clear the remaining samples in the buffer
			while len(outputs) > 0:
				yield outputs.popleft()
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
	

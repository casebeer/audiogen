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

def iir(A, B):
	# Returns an IIR filter function based on the 
	# provided input and output coefficient arrays
	#
	def filter(in_):
		# use deques as ring buffers
		outputs = collections.deque([0] * max(len(B), 1), maxlen=max(len(B), 1))
		inputs =  collections.deque([0] * len(A), maxlen=len(A))
		try:
			while True:
				inputs.appendleft(next(in_))
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
	

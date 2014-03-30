# coding=utf-8

import logging

import math
import collections

import audiogen

def recursive_filter(gen, a, b):
	'''
	Generic recursive IIR filter helper

	Accepts two lists, 'a' and 'b, containing the recursion relation
	coefficients fo rthe the most recent input and output values, 
	respectively. 

	Note that the 'b' list is shifted left by one position relative to
	the 'a' list, since there is no 'b0' coefficient. 
	'''
	x = collections.deque([0] * len(a), maxlen=len(a))
	y = collections.deque([0] * len(b), maxlen=len(b))
	for value in gen:
		x.appendleft(value)
		# n.b. off by one index for y, since output not yet computed and pushed into deque
		output = \
			sum(a_ * x_ for a_, x_ in zip(a, x)) +\
			sum(b_ * y_ for b_, y_ in zip(b, y))
		y.appendleft(output)
		yield output

def low_pass(gen, x=0.9):
	'''
	Single pole low pass IIR filter

	Higher x = lower cutoff frequency.

	http://www.dspguide.com/ch19/2.htm
	'''
	a0 = 1 - x
	b1 = x

	for value in recursive_filter(gen, [a0], [b1]):
		yield value

def high_pass(gen, x=0.1):
	'''
	Single pole high pass IIR filter

	Lower x = higher cutoff frequency.

	http://www.dspguide.com/ch19/2.htm
	'''
	a0 = float(1 + x) / 2
	a1 = - a0
	b1 = x

	for value in recursive_filter(gen, [a0, a1], [b1]):
		yield value

def band_pass(gen, center=440, bandwidth=100):
	'''
	Band-pass IIR filter

	http://www.dspguide.com/ch19/3.htm
	'''
	f = float(center) / audiogen.sampler.FRAME_RATE
	bw = float(bandwidth) / audiogen.sampler.FRAME_RATE

	cos = math.cos
	pi = math.pi

	R = 1 - 3 * bw
	K = (1 - 2 * R * cos(2 * pi * f) + R ** 2) / (2 - 2 * cos(2 * pi * f))

	a0 = 1 - K
	a1 = 2 * (K - R) * cos(2 * pi * f)
	a2 = R ** 2 - K
	b1 = 2 * R * cos(2 * pi * f)
	b2 = - (R ** 2)

	for value in recursive_filter(gen, [a0, a1, a2], [b1, b2]):
		yield value

def band_stop(gen, center=440, bandwidth=100):
	'''
	Band-stop IIR filter

	http://www.dspguide.com/ch19/3.htm
	'''
	f = float(center) / audiogen.sampler.FRAME_RATE
	bw = float(bandwidth) / audiogen.sampler.FRAME_RATE

	cos = math.cos
	pi = math.pi

	R = 1 - 3 * bw
	K = (1 - 2 * R * cos(2 * pi * f) + R ** 2) / (2 - 2 * cos(2 * pi * f))

	a0 = K
	a1 = -2 * K * cos(2 * pi * f)
	a2 = K
	b1 = 2 * R * cos(2 * pi * f)
	b2 = - (R ** 2)

	for value in recursive_filter(gen, [a0, a1, a2], [b1, b2]):
		yield value

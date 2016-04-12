
import logging 
logger = logging.getLogger(__name__)

import itertools
import struct
import math

from .noise import white_noise
from .noise import white_noise_samples
from .noise import red_noise

import sampler 

def crop(gens, seconds=5, cropper=None):
	'''
	Crop the generator to a finite number of frames

	Return a generator which outputs the provided generator limited
	to enough samples to produce seconds seconds of audio (default 5s)
	at the provided frame rate.
	'''
	if hasattr(gens, "next"):
		# single generator
		gens = (gens,)

	if cropper == None:
		cropper = lambda gen: itertools.islice(gen, 0, seconds * sampler.FRAME_RATE)

	cropped = [cropper(gen) for gen in gens]
	return cropped[0] if len(cropped) == 1 else cropped

def crop_with_fades(gen, seconds, fade_in=0.01, fade_out=0.01):
	source = iter(gen)

	total_samples = int(seconds * sampler.FRAME_RATE)
	fade_in_samples = int(fade_in * sampler.FRAME_RATE)
	fade_out_samples = int(fade_out * sampler.FRAME_RATE)

	start = itertools.islice(source, 0, fade_in_samples)
	middle = itertools.islice(source, 0, total_samples - (fade_in_samples + fade_out_samples))
	end = itertools.islice(source, 0, fade_out_samples)

	def linear_fade(samples, direction="in"):
		for i in xrange(samples):
			if direction == "in":
				yield ( 1.0 / samples ) * i + 0
			elif direction == "out":
				yield ( -1.0 / samples ) * i + 1
			else:
				raise Exception('Fade direction must be "in" or "out"')
		while True:
			yield 0

	for sample in multiply(start, linear_fade(fade_in_samples, direction="in")):
		yield sample

	for sample in middle:
		yield sample
	
	for sample in multiply(end, linear_fade(fade_out_samples, direction="out")):
		yield sample

def crop_with_fade_out(gen, seconds, fade=.01):
	source = iter(gen)

	total_samples = int(seconds * sampler.FRAME_RATE)
	fade_samples = int(fade * sampler.FRAME_RATE)

	start = itertools.islice(source, 0, total_samples - fade_samples)
	end = itertools.islice(source, 0, fade_samples)

	def fader():
		for i in xrange(fade_samples):
			yield 1 - (float(i) / fade_samples) ** 1
		while True:
			yield 0

	for sample in start:
		yield sample
	
	for sample in multiply(end, fader()):
		yield sample


def crop_at_zero_crossing(gen, seconds=5, error=0.1):
	'''
	Crop the generator, ending at a zero-crossing

	Crop the generator to produce approximately seconds seconds 
	(default 5s) of audio at the provided FRAME_RATE, attempting 
	to end the clip at a zero crossing point to avoid clicking. 
	'''
	source = iter(gen)
	buffer_length = int(2 * error * sampler.FRAME_RATE)
	
	# split the source into two iterators:
	# - start, which contains the bulk of the sound clip
	# - and end, which contains the final 100ms, plus 100ms past 
	#   the desired clip length. We may cut the clip anywhere 
	#   within this +/-100ms end buffer.
	start = itertools.islice(source, 0, int((seconds - error) * sampler.FRAME_RATE))
	end = itertools.islice(source, 0, buffer_length)

	for sample in start:
		yield sample

	# pull end buffer generator into memory so we can work with it
	end = list(end)

	# find min by sorting buffer samples, first by abs of sample, then by distance from optimal
	best = sorted(enumerate(end), key=lambda x: (math.fabs(x[1]),abs((buffer_length/2)-x[0])))
	print best[:10]
	print best[0][0]

	# todo: better logic when we don't have a perfect zero crossing
	#if best[0][1] != 0:
	#	# we don't have a perfect zero crossing, so let's look for best fit?
	#	pass
	
	# crop samples at index of best zero crossing
	for sample in end[:best[0][0] + 1]:
		yield sample


def normalize(generator, min_in=0, max_in=256, min_out=-1, max_out=1):
	scale = float(max_out - min_out) / (max_in - min_in)
	return ((sample - min_in) * scale + min_out for sample in generator)

def hard_clip(generator, min=-1, max=1):
	while True:
		sample = generator.next()
		if sample > max:
			logger.warn("Warning, clipped value %f > max %f" % (sample, max))
			yield max
		elif sample < min:
			logger.warn("Warning, clipped value %f < min %f" % (sample, min))
			yield min
		else:
			yield sample

def vector_reduce(op, generators):
	while True:
		yield reduce(op, [g.next() for g in generators])
def vector_reduce1(op, generators):
	while True:
		yield reduce(op, [g.next() for g in generators])

def sum(*generators):
	return vector_reduce(lambda a,b: a + b, generators)

def multiply(*generators):
	return vector_reduce1(lambda a,b: a * b, generators)

def constant(value):
	while True:
		yield value

# filters

def volume(gen, dB=0):
	'''Change the volume of gen by dB decibles'''
	if not hasattr(dB, 'next'):
		# not a generator
		scale = 10 ** (dB / 20.)
	else:
		def scale_gen():
			while True:
				yield 10 ** (next(dB) / 20.)
		scale = scale_gen()
	return envelope(gen, scale)

def clip(gen, limit):
	if not hasattr(limit, 'next'):
		limit = constant(limit)
	while True:
		sample = gen.next()
		current_limit = limit.next()
		if math.fabs(sample) > current_limit:
			yield current_limit * (math.fabs(sample) / sample if sample != 0 else 0)
		else:
			yield sample

def envelope(gen, volume):
	if not hasattr(volume, 'next'):
		volume = constant(volume)
	while True:
		sample = gen.next()
		current_volume = volume.next()
		yield current_volume * sample

def loop(*gens):
	loops = [list(gen) for gen in gens]
	while True:
		for loop in loops: 
			for sample in loop:
				yield sample

def mixer(inputs, mix=None):
	'''
	Mix `inputs` together based on `mix` tuple

	`inputs` should be a tuple of *n* generators. 

	`mix` should be a tuple of *m* tuples, one per desired
	output channel. Each of the *m* tuples should contain
	*n* generators, corresponding to the time-sequence of 
	the desired mix levels for each of the *n* input channels.

	That is, to make an ouput channel contain a 50/50 mix of the
	two input channels, the tuple would be:

	    (constant(0.5), constant(0.5))
	
	The mix generators need not be constant, allowing for time-varying
	mix levels: 

	    # 50% from input 1, pulse input 2 over a two second cycle
	    (constant(0.5), tone(0.5))

	The mixer will return a list of *m* generators, each containing 
	the data from the inputs mixed as specified. 

	If no `mix` tuple is specified, all of the *n* input channels
	will be mixed together into one generator, with the volume of 
	each reduced *n*-fold.

	Example:

	    # three in, two out; 
	    # 10Hz binaural beat with white noise across both channels
	    mixer(
	    		(white_noise(), tone(440), tone(450)), 
	    		(
	    			(constant(.5), constant(1), constant(0)),
	    			(constant(.5), constant(0), constant(1)),
	    		)
	    	)
	'''
	if mix == None:
		# by default, mix all inputs down to one channel
		mix = ([constant(1.0 / len(inputs))] * len(inputs),)

	duped_inputs = zip(*[itertools.tee(i, len(mix)) for i in inputs])

# second zip is backwards
	return [\
			sum(*[multiply(m,i) for m,i in zip(channel_mix, channel_inputs)])\
			for channel_mix, channel_inputs in zip(mix, duped_inputs) \
			]

def channelize(gen, channels):
	'''
	Break multi-channel generator into one sub-generator per channel

	Takes a generator producing n-tuples of samples and returns n generators,
	each producing samples for a single channel.

	Since multi-channel generators are the only reasonable way to synchronize samples
	across channels, and the sampler functions only take tuples of generators,
	you must use this function to process synchronized streams for output.
	'''
	def pick(g, channel):
		for samples in g:
			yield samples[channel]
	return [pick(gen_copy, channel) for channel, gen_copy in enumerate(itertools.tee(gen, channels))]

def play(filename):
	import subprocess
	subprocess.call(["afplay", filename])



import logging

import struct
import wave
import itertools

import pyaudio
import time

from .util import hard_clip
from .util import normalize

### Constants

# frame rate in Hertz
FRAME_RATE=44100

# sample width in bytes, 2 = 16 bit
SAMPLE_WIDTH=2
COMPRESSION_TYPE='NONE'
COMPRESSION_NAME='no compression'
BUFFER_SIZE=100000

class frame_rate(object):
	def __init__(self, new_frame_rate):
		global FRAME_RATE
		self._saved_frame_rate = FRAME_RATE
		FRAME_RATE = new_frame_rate
	def __enter__(self, ):
		pass
	def __exit__(self, *args, **kwargs):
		global FRAME_RATE
		FRAME_RATE = self._saved_frame_rate


def sample(generator, min=-1, max=1, width=SAMPLE_WIDTH):
	'''Convert audio waveform generator into packed sample generator.'''
	# select signed char, short, or in based on sample width
	fmt = { 1: 'b', 2: 'h', 4: 'i' }[width]
	return (struct.pack(fmt, int(sample)) for sample in \
			normalize(hard_clip(generator, min, max),\
				min, max, -2**(width * 8 - 1), 2**(width * 8 - 1) - 1))
#	scale = float(2**(width * 8) - 1) / (max - min)
#	return (struct.pack('h', int((sample - min) * scale) - 2**(width * 8 - 1)) for sample in generator)

def sample_all(generators, *args, **kwargs):
	'''Convert list of audio waveform generators into list of packed sample generators.'''
	return [sample(gen, *args, **kwargs) for gen in  generators]

def interleave(channels):
	'''
	Interleave samples from multiple channels for wave output

	Accept a list of channel generators and generate a sequence
	of frames, one sample from each channel per frame, in the order
	of the channels in the list. 
	'''
	while True:
		yield "".join([channel.next() for channel in channels])

def buffer(stream, buffer_size=BUFFER_SIZE):
	'''
	Buffer the generator into byte strings of buffer_size samples

	Return a generator that outputs reasonably sized byte strings
	containing buffer_size samples from the generator stream. 

	This allows us to outputing big chunks of the audio stream to 
	disk at once for faster writes.
	'''
	i = iter(stream)
	return iter(lambda: "".join(itertools.islice(i, buffer_size)), "") 
	

def wav_samples(channels, sample_width=SAMPLE_WIDTH, raw_samples=False):
	if hasattr(channels, 'next'):
		# if passed one generator, we have one channel
		channels = (channels,)
	channel_count = len(channels)
	if not raw_samples:
		# we have audio waveforms, so sample/pack them first
		channels = sample_all(channels, width=sample_width)
	return interleave(channels)

def write_wav(f, channels, sample_width=SAMPLE_WIDTH, raw_samples=False):
	stream = wav_samples(channels, sample_width, raw_samples)
	channel_count = 1 if hasattr(channels, "next") else len(channels)

	w = wave.open(f)
	w.setparams((
		channel_count, 
		sample_width, 
		FRAME_RATE, 
		0, # setting zero frames, should update automatically as more frames written
		COMPRESSION_TYPE, 
		COMPRESSION_NAME
		))
	
	for chunk in buffer(stream):
		logging.debug("Writing %d bytes..." % len(chunk))
		w.writeframes(chunk)
	w.close()

def cache_finite_samples(f):
	'''Decorator to cache audio samples produced by the wrapped generator.'''
	cache = {}
	def wrap(*args):
		key = FRAME_RATE, args
		if key not in cache:
			cache[key] = [sample for sample in f(*args)]
		return (sample for sample in cache[key])
	return wrap

def pyaudio_callback(wavgen):
	def cb(a, frame_count, b, c):
		data = bytearray()
		try:
			for i in range(frame_count):
				data.extend(next(wavgen))
		except StopIteration:
			if len(data) == 0:
				return "", pyaudio.paComplete
		return str(data), pyaudio.paContinue
	return cb

def play(gen, blocking=False):
	wavgen = wav_samples(gen)
	p = pyaudio.PyAudio()
	stream = p.open(
		format=p.get_format_from_width(SAMPLE_WIDTH),
		channels=1,
		rate=FRAME_RATE,
		output=True,
		stream_callback=pyaudio_callback(wavgen) if not blocking else None
	)
	if blocking:
		try:
			for chunk in buffer(wavgen, 1024):
				stream.write(chunk)
		except Exception:
			raise
		finally:
			if not stream.is_stopped():
				stream.stop_stream()
			try:
				stream.close()
			except Exception:
				pass
	else:
		return stream



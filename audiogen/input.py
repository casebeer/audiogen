import logging
logging.basicConfig(level=logging.DEBUG)

import pyaudio
import code
import collections

import threading
import contextlib
import itertools
import struct

import audiogen
from audiogen import util

#FORMAT = pyaudio.paInt16
WIDTH=2 # sample width in bytes
RATE=48000
RATE=16000
RATE=44100
CHUNK_SIZE=2**17
CHUNK_SIZE=2**14
CHUNK_SIZE=1024
CHANNELS=1

BUFFER_LENGTH=2**7 # = 2**17 bytes
BUFFER_SIZE=2**18
BUFFER_SIZE=2**17
BUFFER_LENGTH=int(BUFFER_SIZE/CHUNK_SIZE)

def unsample(generator, min_=-1, max_=1, width=WIDTH):
	# select signed char, short, or in based on sample width
	# todo: handle float wave formats
	fmt = { 1: '<B', 2: '<h', 4: '<i' }[width]

	def raw_values(generator):
		for sample in generator:
			yield struct.unpack(fmt, sample)[0]
	
	if width == 1:
		# unsigned
		min_in = 0
		max_in = 2 ** 8
	else:
		# signed
		min_in = - (2 ** (8 * width - 1))
		max_in = 2 ** (8 * width - 1) - 1

	return util.normalize(
		raw_values(generator), 
		min_in=min_in, 
		max_in=max_in,
		min_out=min_,
		max_out=max_
	)

def raw_audio_input(rate=RATE, channels=CHANNELS, format_=None, input_device_index=None):
	'''
	Read chunks of audio frames from PyAudio

	Yields one CHUNK_SIZE chunk of audio frames at a time from PyAudio's
	input source. 
	'''
	p = pyaudio.PyAudio()
	stream = p.open(
		format=format_ if format_ else p.get_format_from_width(WIDTH),
		channels=channels,
		rate=rate,
		input=True,
		input_device_index=input_device_index,
		frames_per_buffer=CHUNK_SIZE
	)
	try:
		while True:
			try:
				yield stream.read(CHUNK_SIZE)
			except IOError:
				# eat the buffer overflows... but warn!
				logging.error("PyAudio input buffer overflow")
				pass
	finally:
		stream.stop_stream()
		stream.close()
		p.terminate()

class AudioInputReader(threading.Thread):
	empty = None
	def __init__(self, source=None):
		threading.Thread.__init__(self)
		self.source = source if source else raw_audio_input()
		self.buffer_ = collections.deque(maxlen=BUFFER_LENGTH)
		self.die = False

		# condition variable to notify reader when frames are available
		self.cv = threading.Condition()
	def kill(self):	
		self.die = True
	def read(self):
		count = 0
		with self.cv:
			while len(self.buffer_) == 0:
				count += 1
				self.cv.wait()
			return self.buffer_.popleft()
	def run(self):
		try:
			for chunk in self.source:
				if self.die:
					break
				with self.cv:
					if len(self.buffer_) >= self.buffer_.maxlen:
						logging.error("audiogen input buffer overflow, read faster")
					print "Buffer is {}% full".format(100 * len(self.buffer_) / self.buffer_.maxlen)
					self.buffer_.append(chunk)
					self.cv.notify()
		finally:
			with self.cv:
				self.buffer_.append(self.empty)

@contextlib.contextmanager
def buffered_audio_input(source=None):
	'''
	Context manager to get a buffered audio input generator

	Buffered audio input must be accessed via a context manager
	to ensure that the input reader thread gets cleaned up if the 
	generator is no longer in use. 
	'''
	def gen(reader):
		while True:
			chunk = reader.read()
			if chunk == reader.empty:
				raise StopIteration()
			# TODO: multiple channes, different formats, etc; must de-multiplex the Wave stream
			for frame in util.grouper(chunk, WIDTH):
				yield b"".join(frame)
	reader = None
	try:
		reader = AudioInputReader(source)
		reader.start()
		yield unsample(gen(reader))
	finally:
		logging.debug("Notifying reader thread to terminate.")
		if reader is not None:
			reader.kill()

import wave

def read_wav(f):
	w = wave.open(f)
	# TODO: read and use input wave metadata, e.g. frame rate, e.g. sample width
	while True:
		chunk = w.readframes(CHUNK_SIZE)
		if len(chunk) == 0:
			# TODO: what about streaming wav files that might underflow?
			raise StopIteration()
		yield chunk


def read_raw(f):
	while True:
		chunk = f.read(CHUNK_SIZE)
		yield chunk

def parse_wav(gen):
	def frames(gen):
		for chunk in gen:
			for frame in util.grouper(chunk, WIDTH):
				yield b"".join(frame)
	return unsample(frames(gen))

if __name__ == '__main__':
	from audiogen.filters import *
	import sys

	import time
#
#	with buffered_audio_input() as bai:
#		time.sleep(10)
#	
#	sys.exit(0)

	with audiogen.sampler.frame_rate(RATE):
		with buffered_audio_input() as bai:
			audiogen.sampler.play(band_pass(bai, 2000, 100), blocking=False)
			time.sleep(30)
		audiogen.sampler.play(band_pass(parse_wav(read_raw(sys.stdin)), 2000, 200), blocking=False)
		time.sleep(20)
		with buffered_audio_input(read_raw(sys.stdin)) as bai:
			audiogen.sampler.play(high_pass(bai, .1), blocking=False)
			time.sleep(10)
	print "done"
	sys.exit(0)

	afsk = band_stop(
				band_pass(
					parse_wav(read_wav(open('afsk-noise.wav', 'rb'))), 
					1700, 
					1050
				),
				1700, 
				950
			)
	audiogen.sampler.play(afsk, blocking=True)
#	with open('output.wav', 'wb') as f:
#		audiogen.sampler.write_wav(f, afsk)
#
#	sys.exit(0)
	with buffered_audio_input() as bai:
		def gen():
			for value in bai:
				#value = float((ord(sample[1]) << 8) + ord(sample[0])) / 2**15 - 1
				#value = float(ord(sample)) / 2**7 - 1
				yield value
		alpha = 0.9

		def lpf(gen, alpha0=0.9):
			output = 0
			for value in gen:
				output = value * alpha + output * (1 - alpha)
				yield output

		def echo(gen, by=0.5):
			buf = util.RingBuffer(maxlen=RATE * by)
			for value in gen:
				old = buf.append(value)
				if old is None:
					old = 0
				yield value + 0.2 * old

		def volume(gen, db=0):
			for value in gen:
				yield value * 10 ** (float(db) / 20)

		audiogen.sampler.play(volume(band_pass(bai, 50, 50), 0), blocking=True)
		audiogen.sampler.play(volume(band_stop(band_pass(bai, 50, 50), 60, 15), 0), blocking=True)
		#audiogen.sampler.play(volume(low_pass(gen(), 0.9), 0), blocking=False)
		#audiogen.sampler.play(volume(band_pass(gen(), 440, 100), 0), blocking=False)
		#audiogen.sampler.play(echo(echo(echo(lpf(gen(), 0.9), 0.3), .5), 1.0), blocking=False)

		try:
			while True:
				try:
					alpha = float(raw_input("alpha = "))
				finally:
					pass
		finally:
			pass

		audiogen.sampler.play(bai, blocking=True, raw_samples=True)
	
	if False:
		for index, value in enumerate(bai):
			if index % 2**14 == 0:
				print("{: 4d} value is: {}".format(index >> 14, value.encode('hex')))


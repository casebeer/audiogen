
import logging
logger = logging.getLogger(__name__)

import struct
import wave
import itertools

try:
	import pyaudio
	pyaudio_loaded = True
except ImportError:
	pyaudio_loaded = False
import time
import sys
import errno
import contextlib

from StringIO import StringIO

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

@contextlib.contextmanager
def sample_width(new_sample_width):
	global SAMPLE_WIDTH
	saved_sample_width = SAMPLE_WIDTH
	SAMPLE_WIDTH = new_sample_width
	yield
	SAMPLE_WIDTH = saved_sample_width

def file_is_seekable(f):
	'''
	Returns True if file `f` is seekable, and False if not
	
	Useful to determine, for example, if `f` is STDOUT to 
	a pipe.
	'''
	try:
		f.tell()
		logger.info("File is seekable!")
	except IOError, e:
		if e.errno == errno.ESPIPE:
			return False
		else:
			raise
	return True


def sample(generator, min=-1, max=1, width=SAMPLE_WIDTH):
	'''Convert audio waveform generator into packed sample generator.'''
	# select signed char, short, or in based on sample width
	fmt = { 1: '<B', 2: '<h', 4: '<i' }[width]
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

class NonSeekableFileProxy(object):
	def __init__(self, file_instance):
		'''Proxy to protect seek and tell methods of non-seekable file objects'''
		self.f = file_instance
	def __getattr__(self, attr):
		def dummy(*args):
			logger.debug("Suppressed call to '{0}'".format(attr))
			return 0
		if attr in ('seek', 'tell'):
			return dummy
		else:
			return getattr(self.f, attr)

def wave_module_patched():
	'''True if wave module can write data size of 0xFFFFFFFF, False otherwise.'''
	f = StringIO()
	w = wave.open(f, "wb")
	w.setparams((1, 2, 44100, 0, "NONE", "no compression"))
	patched = True
	try:
		w.setnframes((0xFFFFFFFF - 36) / w.getnchannels() / w.getsampwidth())
		w._ensure_header_written(0)
	except struct.error:
		patched = False
		logger.info("Error setting wave data size to 0xFFFFFFFF; wave module unpatched, setting sata size to 0x7FFFFFFF")
		w.setnframes((0x7FFFFFFF - 36) / w.getnchannels() / w.getsampwidth())
		w._ensure_header_written(0)
	return patched

def write_wav(f, channels, sample_width=SAMPLE_WIDTH, raw_samples=False, seekable=None):
	stream = wav_samples(channels, sample_width, raw_samples)
	channel_count = 1 if hasattr(channels, "next") else len(channels)

	output_seekable = file_is_seekable(f) if seekable is None else seekable

	if not output_seekable:
		# protect the non-seekable file, since Wave_write will call tell
		f = NonSeekableFileProxy(f)

	w = wave.open(f)
	w.setparams((
		channel_count, 
		sample_width, 
		FRAME_RATE, 
		0, # setting zero frames, should update automatically as more frames written
		COMPRESSION_TYPE, 
		COMPRESSION_NAME
		))

	if not output_seekable:
		if wave_module_patched():
			# set nframes to make wave module write data size of 0xFFFFFFF
			w.setnframes((0xFFFFFFFF - 36) / w.getnchannels() / w.getsampwidth())
			logger.debug("Setting frames to: {0}, {1}".format((w.getnframes()), w._nframes))
		else:
			w.setnframes((0x7FFFFFFF - 36) / w.getnchannels() / w.getsampwidth())
			logger.debug("Setting frames to: {0}, {1}".format((w.getnframes()), w._nframes))
	
	for chunk in buffer(stream):
		logger.debug("Writing %d bytes..." % len(chunk))
		if output_seekable:
			w.writeframes(chunk)
		else:
			# tell wave module not to update nframes header field 
			# if output stream not seekable, e.g. STDOUT to a pipe
			w.writeframesraw(chunk)
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

def _pyaudio_callback(wavgen):
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

def play(channels, blocking=True, raw_samples=False):
	'''
	Play the contents of the generator using PyAudio

	Play to the system soundcard using PyAudio. PyAudio, an otherwise optional
	depenency, must be installed for this feature to work. 
	'''
	if not pyaudio_loaded:
		raise Exception("Soundcard playback requires PyAudio. Install with `pip install pyaudio`.")

	channel_count = 1 if hasattr(channels, "next") else len(channels)
	wavgen = wav_samples(channels, raw_samples=raw_samples)
	p = pyaudio.PyAudio()
	stream = p.open(
		format=p.get_format_from_width(SAMPLE_WIDTH),
		channels=channel_count,
		rate=FRAME_RATE,
		output=True,
		stream_callback=_pyaudio_callback(wavgen) if not blocking else None
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



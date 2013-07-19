
import util
import math
import sampler

## Audio sample generators

def beep(frequency=440):
	for sample in util.crop_with_fades(tone(440), seconds=0.25):
		yield sample

def tone(frequency=440):
	# todo limit length in seconds or cycles
	period = int(sampler.FRAME_RATE / frequency) 
	time_scale = 2 * math.pi / period # period * scale = 2 * pi
	samples = [math.sin(i * time_scale) for i in xrange(period)]
	while True:
		for i in xrange(period):
			yield samples[i]

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


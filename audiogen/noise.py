
import logging
logger = logging.getLogger(__name__)

import audiogen.util as util

# Arcfour PRNG as a fast source of repeatable randomish numbers; totally unnecessary here, but simple.
def arcfour(key, csbN=1):
	'''Return a generator for the ARCFOUR/RC4 pseudorandom keystream for the
	   key provided. Keys should be byte strings or sequences of ints.'''
	if isinstance(key, str):
		key = [ord(c) for c in key]
	s = range(256)
	j = 0
	for n in range(csbN):
		for i in range(256):
			j = (j + s[i] + key[i % len(key)]) % 255
			s[i], s[j] = s[j], s[i]
	i, j = 0, 0
	while True:
		i = (i + 1) & 255
		j = (j + s[i]) & 255
		s[i], s[j] = s[j], s[i]
		yield s[(s[i] + s[j]) & 255]

def arcfour_drop(key, n=3072):
	'''Return a generator for the RC4-drop pseudorandom keystream given by
	   the key and number of bytes to drop passed as arguments. Dropped bytes
	   default to the more conservative 3072, NOT the SCAN default of 768.'''
	af = arcfour(key)
	[next(af) for c in range(n)]
	return af
mark_4 = arcfour_drop


def white_noise(key=(1,2,3,4,5)):
	def prng(key):
		af = arcfour(key)
		while True:
            # extract 16 bits of randomness per sample
			yield next(af) * 2**8 + next(af)
    # normalize to floats in [-1, 1]
	return util.normalize(prng(key), 0, 2**16)

'''Provides 16 bit raw integer samples as strs directly from random number generator'''
def white_noise_samples(key=(1,2,3,4,5)):
	af = arcfour(key)
	while True:
        # extract 16 bits of randomness per sample
        # since chr() produces strs, + concatenates the two bytes
		yield chr(next(af)) + chr(next(af))

def red_noise(key=(1,2,3,4,5)):
    def random_walk(key, dynamic_range):
        af = arcfour(key)
        max_ = dynamic_range / 2
        sample = 0
        while True:
            #step = next(af) - 128
            step = next(af) / (256.0 / 2 / 20) - 1 # Normalize to 5% of [-1, 1] range and center the step at zero
            # Skew the step probability to encourage the sample back towards DC
            #step *= (max_ * max_ - sample * sample) ** 0.5 / max_ if step * sample > 0 else 1
            step *= (1 - sample * sample) ** 0.5 if step * sample > 0 else 1
            sample += step

            # hard clipping if the random walk hits the limit of the dynamic range
            if sample > 1:
                logger.debug('[red_noise] Random walk hard clip!')
                sample = 1
            elif sample < -1:
                logger.debug('[red_noise] Random walk hard clip!')
                sample = -1
            yield sample
    # Since we're generating random values in [0, 255], set the dynamic range to make the
    # max step size 5% of the dynamic range
    dynamic_range = 256 * 20
    min_, max_ = -dynamic_range / 2, dynamic_range / 2
    # normalize to floats in [-1, 1]
    #return util.normalize(random_walk(key, dynamic_range), min_, max_)
    return random_walk(key, dynamic_range)

'''
RFC 6229
2.  Test Vectors for RC4

 Key length: 40 bits.
 key: 0x0102030405

 DEC    0 HEX    0:  b2 39 63 05  f0 3d c0 27   cc c3 52 4a  0a 11 18 a8
 DEC   16 HEX   10:  69 82 94 4f  18 fc 82 d5   89 c4 03 a4  7a 0d 09 19
 DEC  240 HEX   f0:  28 cb 11 32  c9 6c e2 86   42 1d ca ad  b8 b6 9e ae
 DEC  256 HEX  100:  1c fc f6 2b  03 ed db 64   1d 77 df cf  7f 8d 8c 93
 DEC  496 HEX  1f0:  42 b7 d0 cd  d9 18 a8 a3   3d d5 17 81  c8 1f 40 41
 DEC  512 HEX  200:  64 59 84 44  32 a7 da 92   3c fb 3e b4  98 06 61 f6
 DEC  752 HEX  2f0:  ec 10 32 7b  de 2b ee fd   18 f9 27 76  80 45 7e 22
 DEC  768 HEX  300:  eb 62 63 8d  4f 0b a1 fe   9f ca 20 e0  5b f8 ff 2b
 DEC 1008 HEX  3f0:  45 12 90 48  e6 a0 ed 0b   56 b4 90 33  8f 07 8d a5
 DEC 1024 HEX  400:  30 ab bc c7  c2 0b 01 60   9f 23 ee 2d  5f 6b b7 df
 DEC 1520 HEX  5f0:  32 94 f7 44  d8 f9 79 05   07 e7 0f 62  e5 bb ce ea
 DEC 1536 HEX  600:  d8 72 9d b4  18 82 25 9b   ee 4f 82 53  25 f5 a1 30
 DEC 2032 HEX  7f0:  1e b1 4a 0c  13 b3 bf 47   fa 2a 0b a9  3a d4 5b 8b
 DEC 2048 HEX  800:  cc 58 2f 8b  a9 f2 65 e2   b1 be 91 12  e9 75 d2 d7
 DEC 3056 HEX  bf0:  f2 e3 0f 9b  d1 02 ec bf   75 aa ad e9  bc 35 c4 3c
 DEC 3072 HEX  c00:  ec 0e 11 c4  79 dc 32 9d   c8 da 79 68  fe 96 56 81
 DEC 4080 HEX  ff0:  06 83 26 a2  11 84 16 d2   1f 9d 04 b2  cd 1c a0 50
 DEC 4096 HEX 1000:  ff 25 b5 89  95 99 67 07   e5 1f bd f0  8b 34 d8 75
'''

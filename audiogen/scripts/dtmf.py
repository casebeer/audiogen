# coding=utf8

import logging

import itertools
import argparse

import audiogen

logger = logging.getLogger(__name__)

LPF_RUNOUT = 0.01  # seconds


def digitFrequencies(digit: str) -> tuple[int, int]:
    '''
    Return a pair of frequencies given a DTMF digit

    `digit` must be one of 1234567890*#ABCD encoded as a string.
    '''
    digitMap = "123A456B789C*0#D"
    high = [1290, 1336, 1477, 1633]
    low = [697, 770, 852, 941]

    index = digitMap.index(digit.upper())

    return (low[index // 4], high[index % 4])


def main():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument(
        "-o", "--output-file",
        default=None,
        help="Output file to write. If not set, tone audio plays with no "
             "file output."
    )
    parser.add_argument(
        "-s", "--seconds",
        type=float,
        default=2.0,
        help="Length of audio to play in seconds. Partial seconds allowed."
    )
    parser.add_argument(
        "-d", "--digits",
        action='append',
        type=str.upper,
        default=[],
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                 "*", "#", "A", "B", "C", "D"],
        help="DTMF digits to playback. Should be one of [1234567890*#ABCD]. "
             "May be provided multiple times."
    )
    parser.add_argument(
        "--dial",
        action='store_true',
        default=False,
        help="Play a North American dial tone combining 350 Hz and 440 Hz."
    )
    parser.add_argument(
        "frequencies", nargs='*', type=int,
        help="Frequency of tones to play. Can be any number of arguments. "
             "If --digit options are also provided, "
             "the digit tones are mixed with the specified frequencies. "
             "If neither --digit nor posititional arguments are provided, "
             "defaults to a standard North American dial tone combining "
             "350 Hz and 440 Hz."
        )
    args = parser.parse_args()

    frequencies = []

    if len(args.frequencies) == 0 and len(args.digits) == 0 or args.dial:
        # default to NA dial tone
        frequencies = [350, 440]

    frequencies += args.frequencies

    digitFrequencyPairs = [digitFrequencies(digit) for digit in args.digits]
    frequencies += \
        [frequency for pair in digitFrequencyPairs for frequency in pair]

    tones = [audiogen.beep(frequency, args.seconds, use_bpf=False)
             for frequency in frequencies]

    # Mix all tones down to one channel
    # Since we know we will have only one channel, pull out channel [0]'s
    # sample generator for direct use by e.g. the low pass filter
    samples = audiogen.util.mixer(tones)[0]

    # append a brief silence so the LPF can work
    samples = itertools.chain(samples, audiogen.generators.silence(LPF_RUNOUT))

    lpf = audiogen.filters.low_pass(max(frequencies) * 1.2)

    # lpf twice to get better stopband attenuation
    samples = lpf(samples)
    samples = lpf(samples)

    filename = args.output_file
    if filename is None:
        audiogen.sampler.play(samples)
    else:
        logger.info('Writing {}...'.format(filename))
        with open(filename, 'wb') as f:
            audiogen.sampler.write_wav(f, samples)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

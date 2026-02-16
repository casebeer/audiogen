
import argparse
import logging

import audiogen

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
    parser.add_argument(
        "-o", "--output-file",
        default=None,
        help="Output file to write."
             "If not set, tone audio plays without writing file.",
    )
    parser.add_argument(
        "-s", "--seconds",
        type=float,
        default=2.0,
        help="Length of audio to play in seconds. Partial seconds allowed.",
    )
    parser.add_argument(
        "-r", "--sample-rate",
        type=int,
        default=48000,
        help="Sampling rate in Hertz.",
    )
    parser.add_argument(
        "frequency", nargs='?', default=440, type=int,
        help="Frequency of tone to play.",
        )
    args = parser.parse_args()

    with audiogen.sampler.frame_rate(args.sample_rate):
        tone = audiogen.beep(args.frequency, args.seconds)

        filename = args.output_file
        if filename is None:
            audiogen.sampler.play(tone)
        else:
            logger.info(f'Writing {filename}...')
            with open(filename, 'wb') as f:
                audiogen.sampler.write_wav(f, tone)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

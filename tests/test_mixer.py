# coding=utf8

import unittest

import audiogen
from itertools import zip_longest

unit = audiogen.util.constant(1)


class TestMixer(unittest.TestCase):
    def setup_mux(self):
        return audiogen.util.mixer((iter(list(range(10))),),
                                   ((unit,), (unit,))
                                   )

    def test_mux_output_channels(self):
        output = self.setup_mux()
        self.assertEqual(len(output), 2)

    def test_mux_duplicated_content(self):
        output = self.setup_mux()
        saved = [list(channel) for channel in output]

        # print out first for debugging if test fails
        for num, channel in enumerate(saved):
            print(f"Channel {num}: {', '.join([str(c) for c in channel])}")

        for channel in saved:
            for sample, test in zip_longest(channel, list(range(10))):
                self.assertEqual(sample, test)


if __name__ == '__main__':
    unittest.main()

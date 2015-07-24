# coding=utf8

import audiogen
from itertools import izip_longest

unit = audiogen.util.constant(1)

def setup_mux():
	return audiogen.util.mixer((iter(range(10)),), ((unit,),(unit,)))

def test_mux_output_channels():
	output = setup_mux()
	assert len(output) == 2

def test_mux_duplicated_content():
	output = setup_mux()
	saved = [list(channel) for channel in output]

	# print out first for debugging if test fails
	for num, channel in enumerate(saved):
		print("Channel {}: {}".format(num, ", ".join([str(c) for c in channel])))

	for channel in saved:
		for sample, test in izip_longest(channel, range(10)):
			assert(sample == test)


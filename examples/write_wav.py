import audiogen

# mix 440 Hz and 445 Hz tones to get 5 Hz beating
beats = audiogen.util.mixer(
    (audiogen.tone(440), audiogen.tone(445)),
    [(audiogen.util.constant(1), audiogen.util.constant(1)),]
)

with open("beats.wav", "wb") as f:
    # crop the beats generator to 15 seconds worth of samples
    # and write the output to a wav file
    audiogen.sampler.write_wav(f, audiogen.util.crop(beats, seconds=15))

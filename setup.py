#!/usr/bin/env python

from setuptools import setup, find_packages

required_modules = []
extras_require = {
    'soundcard_playback': ['pyaudio'],
}

with open("README.rst", "rb") as f:
    readme = f.read().decode('utf8')

setup(
    name="audiogen",
    version="0.1.2",
    description="Generator based tools for working with audio clips.",
    author="Christopher H. Casebeer",
    author_email="",
    url="https://github.com/casebeer/audiogen",

    packages=find_packages(exclude='tests'),
    install_requires=required_modules,
    extras_require=extras_require,

    entry_points={
        "console_scripts": [
            "tone = audiogen.scripts.tone:main",
            "dtmf = audiogen.scripts.dtmf:main",
        ]
    },

    tests_require=["nose"],
    test_suite="nose.collector",

    long_description=readme,
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio",
    ]
)

#!/usr/bin/env python
"""nacreous

Downloads and tags tracks from Soundcloud.

"""
from setuptools import setup


setup(
    name="nacreous",
    version="0.0.1",
    description=__doc__.split("\n")[2],
    license="BSD",
    author="David Gidwani",
    author_email="david.gidwani@gmail.com",
    url="https://github.com/darvid/nacreous",
    download_url="https://github.com/darvid/nacreous/tarball/0.1",
    keywords="soundcloud music audio sync",
    py_modules=["nacreous"],
    install_requires=[
        "click",
        "furl",
        "logbook",
        "mutagen",
        "plumbum",
        "requests",
        "selenium",
        "youtube-dl",
    ],
    tests_require=["pytest"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points={
        "console_scripts": ["nacreous=nacreous:main"],
    }
)

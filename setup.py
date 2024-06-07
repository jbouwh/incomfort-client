#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""The setup.py file."""

import os
import sys

from setuptools import find_packages, setup
from setuptools.command.install import install

with open("incomfortclient/__init__.py") as fh:
    for line in fh:
        if line.strip().startswith("__version__"):
            VERSION = eval(line.split("=")[-1])
            break

URL = "https://github.com/jbouwh/incomfort-client"

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our VERSION."""

    def run(self):
        tag = os.getenv("CIRCLE_TAG")
        if tag != VERSION:
            info = f"Error: git tag ({tag}) does not match the pkg version ({VERSION})"
            sys.exit(info)


setup(
    name="incomfort-client",
    description="An aiohttp-based client for Intergas InComfort/InTouch Lan2RF systems",
    keywords=["intergas", "incomfort", "intouch", "lan2rf"],
    author="Jan Bouwhuis",
    author_email="jan@jbsoft.nl",
    url=URL,
    download_url=f"{URL}/archive/{VERSION}.tar.gz",
    install_requires=[list(val.strip() for val in open("requirements.txt"))],
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["test", "docs"]),
    version=VERSION,
    license="MIT",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
        "Topic :: Home Automation",
    ],
    cmdclass={
        "verify": VerifyVersionCommand,
    },
)

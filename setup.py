#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The setup.py file."""

import os
from setuptools import find_packages, setup
from setuptools.command.install import install
import sys

VERSION = "0.4.5"

with open("README.md", "r") as fh:
    long_description = fh.read()


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version."""

    description = "verify that the git tag matches our version"

    def run(self):
        tag = os.getenv("CIRCLE_TAG")

        if tag != VERSION:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, VERSION
            )
            sys.exit(info)


setup(
    name="incomfort-client",
    version=VERSION,
    author="David Bonnes",
    author_email="zxdavb@bonnes.me",
    description="An aiohttp-based client for Intergas InComfort/InTouch Lan2RF systems",
    keywords=["intergas", "incomfort", "intouch", "lan2rf"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zxdavb/incomfort-client",
    download_url="https://github.com/zxdavb/incomfort-client/archive/VERSION.tar.gz",
    license="MIT",
    packages=find_packages(),
    install_requires=["aiohttp"],
    cmdclass={
        "verify": VerifyVersionCommand,
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup file for Distutils."""

from logging import DEBUG
from logging import getLogger
from logging import StreamHandler
import os

import slack_rtm

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

try:
    from setuptools import find_packages
    from setuptools import setup
except ImportError:
    logger.critical("Please install setuptools.")


def main() -> None:
    """Setup package after read meta information from files."""
    long_description = "Forward message as email by Slack reaction."
    if os.path.exists("README.rst"):
        with open("README.rst") as f:
            long_description = f.read()

    install_requires = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt") as f:
            install_requires = f.read().split()

    setup(name="slack rtm",
          version=slack_rtm.__version__,
          description="Forward message as email by Slack reaction.",
          long_description=long_description,
          license="MIT",
          author="Amane Katagiri",
          author_email="amane@ama.ne.jp",
          url="https://github.com/amane-katagiri/slack-rtm",
          keywords="slack reaction email",
          install_requires=[
          ] + install_requires,
          classifiers=[
              "Development Status :: 3 - Alpha",
              "License :: OSI Approved :: MIT License",
              "Programming Language :: Python :: 3.7",
              "Framework :: Tornado",
          ],
          packages=find_packages(),
          entry_points="""
          [console_scripts]
          slack-rtm = slack_rtm.main:main
          """, )


if __name__ == "__main__":
    main()

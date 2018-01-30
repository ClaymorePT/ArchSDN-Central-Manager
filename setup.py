#!/usr/bin/env python
# coding=utf-8

"""
python distribute file
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals, with_statement)

from setuptools import setup, find_packages


def requirements_file_to_list(fn="requirements.txt"):
    """read a requirements file and create a list that can be used in setup.

    """
    with open(fn, 'r') as f:
        return [x.rstrip() for x in list(f) if x and not x.startswith('#')]


setup(
    name="of_central",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements_file_to_list(),
    dependency_links=[
        # If your project has dependencies on some internal packages that is
        # not on PyPI, you may list package index url here. Then you can just
        # mention package name and version in requirements.txt file.
    ],
    entry_points={
        # 'console_scripts': [
        #     'main = mypkg.main:main',
        # ]
    },
    package_data={
        'mypkg': ['logger.conf']
    },
    author="Carlos Miguel Ferreira",
    author_email="carlosmf.pt@gmail.com",
    maintainer="Carlos Miguel Ferreira",
    maintainer_email="carlosmf.pt@gmail.com",
    description="Minimal centralized manager for OpenFlow enabled networks",
    long_description=open('README.rst').read(),
    license="GPLv3",
    url="https://pypi.python.org/pypi/mypkg",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
    ]
)
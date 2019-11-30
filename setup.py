#!/usr/bin/env python3
# coding=utf-8

'''
    python distribute file
'''

# from __future__ import (absolute_import, division, print_function,
#                         unicode_literals, with_statement)

from setuptools import setup, find_packages


def requirements_file_to_list(fn='requirements.txt'):
    '''
        read a requirements file and create a list that can be used in setup.
    '''
    with open(fn, 'r') as f:
        return [x.rstrip() for x in list(f) if x and not x.startswith('#')]


setup(
    name='archsdn_central',
    version='1.4.1',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'': ['*.sql']},
    install_requires=requirements_file_to_list(),
    py_modules=['main'],
    entry_points={
        'console_scripts': [
            'archsdn_central = archsdn_central:main',
        ]
    },
    test_suite="tests",
    author='Carlos Miguel Ferreira',
    author_email='cmf@av.it.pt',
    maintainer='Carlos Miguel Ferreira',
    maintainer_email='cmf@av.it.pt',
    description='Minimal centralized manager for OpenFlow enabled networks',
    long_description=open('README.rst').read(),
    keywords='SDN OpenFlow Management',
    license='GPLv3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
    ]
)

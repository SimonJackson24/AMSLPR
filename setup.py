
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('requirements.txt', 'r') as f:
    requirements = f.read().splitlines()

setup(
    name='visigate',
    version='0.1.0',
    author='VisiGate',
    author_email='info@automatesystems.com',
    description='License Plate Recognition System for Barrier Control',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/visigate/visigate',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.7',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'visigate=src.main:main',
        ],
    },
)

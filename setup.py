#!/usr/bin/env python
from setuptools import setup

setup(name='QuiltLoader',
      description=' adds bio-science loaders to quilt nodes as well as niceties for interacting and navigating quilt nodes',
      author='Jackson Maxfield Brown',
      author_email='jacksonb@alleninstitute.org',
      url='https://github.com/AllenCellModeling/QuiltLoader',
      packages=['quilt','matplotlib', 'numpy', 'tifffile'],
      install_requires=['quilt','matplotlib', 'numpy', 'tifffile'])
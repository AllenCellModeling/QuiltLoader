# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
_version_major = 0
_version_minor = 1
_version_micro = 4
_version_extra = 'dev'

# Construct full version string from these.
_ver = [_version_major, _version_minor]
if _version_micro:
    _ver.append(_version_micro)
if _version_extra:
    _ver.append(_version_extra)

__version__ = '.'.join(map(str, _ver))

CLASSIFIERS = ["Development Status :: 4 - Beta",
               "Environment :: Console",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: GNU License",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Scientific/Engineering"]

# Description should be a one-liner:
description = "quiltloader: adding custom attributes to quilt nodes"
# Long description will go up on the pypi page
long_description = """
QuiltLoader
========
QuiltLoader is a project to add arbitrary attributes and functions to the
defined quilt (quiltdata.com) nodes.
At it's core, it is primarily defined to support AICS datasets with
navigating and conducting analysis of the data contained in the loaded dataset.
While the default functions and attributes added to the quiltloader
object are aimed to support AICS datasets, this project can work as a
template for implementing your own arbitrary attributes to your own datasets.
Contact
=======
Jackson Maxfield Brown
jacksonb@alleninstitute.org
License
=======
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see http://www.gnu.org/licenses/.
"""

NAME = "quiltloader"
MAINTAINER = "Jackson Maxfield Brown"
MAINTAINER_EMAIL = "jacksonb@alleninstitute.org"
DESCRIPTION = description
LONG_DESCRIPTION = long_description
URL = "https://github.com/AllenCellModeling/QuiltLoader"
DOWNLOAD_URL = "https://github.com/AllenCellModeling/QuiltLoader"
LICENSE = "GNU"
AUTHOR = "Jackson Maxfield Brown"
AUTHOR_EMAIL = "jacksonb@alleninstitute.org"
PLATFORMS = "OS Independent"
MAJOR = _version_major
MINOR = _version_minor
MICRO = _version_micro
VERSION = __version__
REQUIRES = ["quilt", "numpy", "tifffile", "matplotlib"]

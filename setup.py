"""
Navtools 2021 setup.
"""

from setuptools import setup
import sys

if sys.version_info < (3, 9):
    print( "NavTools requires Python 3.9" )
    sys.exit(2)

setup(
    name='navtools',
    version='2021',
    description='Navigation Tools for Course, Bearing, and Compass Deviation',
    author='S.Lott',
    author_email='slott56@gmail.com',
    url='https://github.com/slott56/navtools',
    packages=[
        'navtools',
    ],
    package_data={'navtools': ["igrf11coeffs.txt", "igrf13coeffs.txt"]},
    classifiers=[
        "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        ],
    )

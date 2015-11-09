..    #!/usr/bin/env python3

##############################
Installation via ``setup.py``
##############################

The NavTools distribution kit (minimally) is just the following.

-   :file:`source`.  The RST-formatted source used by PyLit3 to
    to create code and documentation.

-   :file:`build.py`.  The build procedure.

Given this  directory, the build procedure uses PyLit to create the ``navtools`` package.
It uses Sphinx to create the documentation.

See :ref:`build` for more information on the build procedure.
A build requires PyLit3 and Sphinx to be installed.

-   PyLit3.  https://github.com/slott56/PyLit-3

-   Sphinx.  http://sphinx-doc.org

The build itself run like this:

..  code-block:: bash

    python3 build.py

Install ``navtools``.  This may require privileges via ``sudo``.

..  code-block:: bash

    python3 setup.py install

The ``setup.py`` File
======================

This provides Python package information.

::

    from setuptools import setup
    import sys

    if sys.version_info < (3,3):
        print( "NavTools requires Python 3.3" )
        sys.exit(2)

    setup(
        name='navtools',
        version='2.1',
        description='Navigation Tools for Course, Bearing and Compass Deviation',
        author='S.Lott',
        author_email='slott56@gmail.com',
        url='https://github.com/slott56/navtools',
        packages=[
            'navtools',
            ],

We have a data file which must also be installed.
This can be fetched from http://www.ngdc.noaa.gov/IAGA/vmod/igrf11coeffs.txt
directly.

::

        package_data={'navtools': ["igrf11coeffs.txt"]},

We depend on Sphinx.
We also depend on PyLit3.

::

        install_requires=["sphinx>1.2"],

Here are some `trove classifiers <http://pypi.python.org/pypi?%3Aaction=list_classifiers>`_.

::

        classifiers=[
            "Development Status :: 6 - Mature",
            "Environment :: Console",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            ],
        )

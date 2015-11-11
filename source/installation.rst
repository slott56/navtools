..    #!/usr/bin/env python3

##############################
Installation via ``setup.py``
##############################

The NavTools distribution includes the following.

-   :file:`navtools`. The Python code which gets installed.

-   :file:`igrf11coeffs.txt`. Data used to compute magnetic deviation.
    This, too, will be installed.

-   :file:`source`.  The RST-formatted source used by PyLit3 to
    to create the code and the documentation. This

-   :file:`build.py`.  The build procedure to rebuild source
    and documentation from the :file:`source`.

See :ref:`build` for more information on the build procedure.
See https://github.com/slott56/PyLit-3 and http://slott56.github.io/PyLit-3/index.html
for more information on Literate Programming.

Install ``navtools``.  Windows users can omit the ``sudo``.

..  code-block:: bash

    sudo python3 setup.py install

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

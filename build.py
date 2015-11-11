#!/usr/bin/env python3

# .. _`build`:
#
# #########################
# NavTools Build
# #########################
#
# The source for :mod:`navtools` is a Sphinx project that depends on PyLit.
# Yes.  The documentation spawns the code.
#
# In addition to Python 3.4, there are two other projects required to build.
#
# -   PyLit3.  https://github.com/slott56/PyLit-3 and http://slott56.github.io/PyLit-3/index.html.
#
# -   Sphinx.  http://sphinx-doc.org
#
# The PyLit3 install is little more than download and move the :file:`src/pylit.py` file to
# the Python :file:`site-packages` directory.
#
# Sphinx should be
# installed with ``pip3.4`` or ``easy_install_3.4``, both of which are part of the Python3.4 distribution.
#
# ..  code-block:: bash
#
#     pip3.4 install sphinx
#
# Build Procedure
# ==================
#
# 1.  Bootstrap the :file:`build.py` script by running PyLit.
#
#     ..  code-block:: bash
#
#         python3 -m pylit -t source/build.rst build.py
#
#     This reports that an extract was written to :file:`build.py`.
#
# 2.  Use the :file:`build.py` script to create the ``navtools`` source, unit
#     tests, demonstration applications.
#     It also builds the Sphinx documentation.
#     And it runs the unit test suite, too.
#
#     ..  code-block:: bash
#
#         python3 build.py
#
#     At the end of this step, the directory tree will include the following.
#
#     -   :file:`../navtools-gh-pages`.  The documentation.  In HTML.
#     -   :file:`navtools`.  The Python source, ready for installation.
#     -   :file:`setup.py`. The distutils installation.
#     -   :file:`test`.  The unit test script.
#
#     This reports, also, that 49 tests were run.
#
# An alternative to step 2 is the following:
#
# ..  code-block:: bash
#
#     chmod +x build.py
#     ./build.py
#
# Build Script Design
# =====================
#
# The issue is to remain DRY: we hate to repeat the list of PyLit steps
# for multiple OS with slightly different path definitions.
#
# There are three common choices:
#
# -   Make both :file:`build.sh` and :file:`build.bat` from a common source.
#     This would, potentially, lead to some real complication with
#     PyLit trying to build two files (in different resulting syntax)
#     from some kind of common source material. We'd rather not get involved.
#
# -   Depend on ``make``, which is quite common. While this isn't an onerous
#     dependency, we'd like to avoid it.
#
# -   Create a platform-independent :file:`build.py` file for the build script.
#     We'll use ``from sphinx.application import Sphinx``
#     and ``import pylit`` to access these modules from within Python.
#
# We'll really like the Python script approach to the build.
#
# Overheads
# -------------
#
# We're going to make use of three "applications" to build navtools.
#
# -   Sphinx top-level application.
#
# -   PyLit top-level application.
#
# -   Unittest top-level test runner.
#
# ::

"""Platform-independent build script for NavTools 2.1"""
import os
import sys
import errno
from sphinx.application import Sphinx
import pylit
import unittest
import pathlib

# Sphinx Build
# ---------------
#
# ..  py:function:: sphinx_build( srcdir, outdir, buildername='html' )
#
# This function handles the simple use case for the ``sphinx-build`` script.
# The destination directory is -- often -- build/html or some place like
# that.
#
# When working with GitHub and a ``gh-pages`` branch, it can work
# well when the html is generated in the top-level directory. However.
# For this project, we'll create a separate ``gh-pages`` branch which
# is a peer to this directory.
#
# ::

def sphinx_build( srcdir, outdir, buildername='html' ):
    """Essentially: ``sphinx-build $* -b html source .``"""
    confdir= srcdir= pathlib.Path( srcdir )
    outdir= pathlib.Path( outdir )
    doctreedir = outdir / pathlib.Path('.doctrees')
    app = Sphinx(str(srcdir), str(confdir), str(outdir), str(doctreedir), buildername)
    app.build(force_all=False, filenames=[])
    return app.statuscode

# PyLit Build
# ---------------
#
# ..  py:function:: pylit_build( infile, outfile )
#
# This function handles the simple use case for PyLit. We force an overwrite because
# PyLit exits when there's a problem. A bad design.
#
# ::

def pylit_build( infile, outfile ):
    """Essentially: ``python3 -m pylit -t source/{document}.rst demo/{module}.py``

    The issue here is that we need to provide platform-specific paths.
    """
    try:
        pylit.main( txt2code= True, overwrite= "yes", infile= infile, outfile= outfile )
    except SystemExit as e:
        print("Failed to transform {0} to {1}".format(infile, outfile))
        raise

# Make Directories
# -------------------
#
# ..  py:function:: mkdir( path )
#
# This function handles the simple use case for assuring that the directory
# tree exists.
#
# This also handles a rewrite to modify standard paths to Windows paths.
#
# ::

def mkdir( path ):
    try:
        os.makedirs( path )
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

# Run the Test Script
# -----------------------
#
# ..  py:function:: run_test( )
#
# In effect, this does ``python3 test/main.py``
#
# ::

def run_test():
    import test.main
    result= test.main.run()


# The Build Sequence
# ---------------------
#
# ::

def build():
    sphinx_build( 'source', '../navtools-gh-pages', 'html' )

    mkdir( 'navtools' )

    pylit_build( 'source/navtools_init.rst', 'navtools/__init__.py' )
    pylit_build( 'source/igrf11.rst', 'navtools/igrf11.py' )
    pylit_build( 'source/navigation.rst', 'navtools/navigation.py' )
    pylit_build( 'source/planning.rst', 'navtools/planning.py' )
    pylit_build( 'source/analysis.rst', 'navtools/analysis.py' )
    pylit_build( 'source/installation.rst', 'setup.py' )

    mkdir( 'test' )

    pylit_build( 'source/testing/test_init.rst', 'test/__init__.py' )
    pylit_build( 'source/testing/main.rst', 'test/main.py' )
    pylit_build( 'source/testing/test_igrf11.rst', 'test/test_igrf11.py' )
    pylit_build( 'source/testing/test_navigation.rst', 'test/test_navigation.py' )
    pylit_build( 'source/testing/test_planning.rst', 'test/test_planning.py' )
    pylit_build( 'source/testing/test_analysis.rst', 'test/test_analysis.py' )

    run_test()

# Main Program Switch
# ---------------------
#
# When the :file:`build.py` script is run from the command line,
# it will execute the :py:func:`build` function.  When it is imported,
# however, it will do nothing special.
#
# ::

if __name__ == "__main__":
    build()

# Additional Builds
# =====================
#
# Sometimes it's desriable to refresh the documentation.
#
# The HTML pages are built with this command.
#
# ..  code-block:: bash
#
#     sphinx-build $* -b html source ../navtools-gh-pages
#
# A LaTeX document can be built with this command.
# This can build a great-looking PDF.
#
# ..  code-block:: bash
#
#     sphinx-build $* -b latex source ../navtools-gh-pages

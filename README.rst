############
navtools
############

Python-based tools for simple navigation calculations.

See http://slott56.github.io/navtools/.

Installation
============

The NavTools distribution includes the following.

-   :file:`navtools`. The Python code which gets installed.

-   :file:`igrf11coeffs.txt`. Data used to compute magnetic deviation.
    This is from http://www.ngdc.noaa.gov/IAGA/vmod/igrf11coeffs.txt

-   :file:`docs`.  The RST-formatted documentation files.

Clone the Git repository (or download the .zip archive).

..  code-block:: bash

    git clone https://github.com/slott56/navtools

Run the ``setup.py`` to install the package.

..  code-block:: bash

    python setup.py install

For details, see http://slott56.github.io/navtools/installation.html.
This is not available in PyPI, so a simple `python -m pip install navtools` isn't supported.

Use
====

There are three sample applications that process ``.gpx`` or ``.csv``
files:

-   Route Planning: http://slott56.github.io/navtools/planning.html
    computes a schedule for arrival at the various waypoints.

-   Track Analysis: http://slott56.github.io/navtools/analysis.html
    annotates a historical log with distance and speed.

-   OpenCPN Conversion: transforms an OpenCPN route planning table into
    more useful content for spreadsheet use.

An additional use case is to import that :mod:`navtools.navigation` module
to create your own applications.

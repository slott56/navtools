###############################################################
:py:mod:`navtools.opencpn_table` -- OpenCPN Table Application
###############################################################

The :py:mod:`opencpn_table` application is used to do extract a useful CSV
formatted file from the OpenCPN planning display.

The display is a CSV file with a great deal of supplemental formatting.
This application strips away the formatting so the data can be more easily
loaded into a spreadsheet.

..  todo:: Refactor OpenCPN Table to reuse elements of :py:mod:`navigation`

Implementation
==============

..  py:module:: navtools.opencpn_table

Core objects
------------

A :py:class:`Leg` is the space between waypoints.
Rather than repeat each endpoint, only the ending
point is shown and the starting point is implied
by the previous leg's ending point.

(Note. Some of these duplicate :py:mod:`navtools.analysis`.)

..  autoclass:: Leg
    :members:
    :undoc-members:

A :py:class:`Route` is an ordered collection of :py:class:`Leg`
instances with some overall summary data.

..  autoclass:: Route
    :members:
    :undoc-members:

A Duration is a span of time, not an absolute point in time.
This is essentially similar to ``datetime.timedelta``.

..  autoclass:: Duration

The following classes -- to an extent -- duplicate :py:mod:`navtools.navigation`.
However, these are only superficially the same. These
are used to reformat inputs, not actually undertake any
detailed computations.

..  autoclass:: Point

..  autoclass:: Latitude

..  autoclass:: Longitude

Application Processing
----------------------

..  autofunction:: to_html

..  autofunction:: to_csv

..  autofunction:: main

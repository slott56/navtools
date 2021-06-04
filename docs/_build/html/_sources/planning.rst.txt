###############################################################
:py:mod:`navtools.planning` -- Route Planning Application
###############################################################

..  py:module:: planning

The :py:mod:`planning` application is used to do voyage planning.
It computes range, bearing and elapsed time for points along a route.

The input parsing supports two formats: CSV and GPX.  Each source format has
a different kind of parser.  The CSV parser uses the :mod:`csv` module.  The GPX parser uses
:mod:`xml.etree`; it uses the ``findall()`` method to iterate
through all of the rows.

The various navigation calculations use an immutable object (or functional
programming) style.  A series of functions create new, richer objects
from the initial :py:class:`RoutePoint` objects.

Specifically, we use the following kind of function composition.

..  code-block:: python

    gen_schedule(
        gen_mag_bearing(
            gen_rhumb( point_iter ),
            variance),
        speed ):

This module includes three groups of components.
The `Input Parsing`_ group is the functions and a namedtuple that
acquire input from the GPX or CSV file.

The functions and namedtuples
support computations of range and true bearing, magnetic bearing, total distance run,
elapsed time in minutes and hours.

Finally, the :ref:`planning-cli` components are used
to build a proper command-line application.

Input Parsing
===============

The purpose of input parsing is to create :py:class:`RoutePoint` objects
from input file sources.

A :py:class:`RoutePoint` is a 5-tuple of name, latitude, longitude, description
and "point" information.   The "point" information is a
:py:class:`navigation.LatLon` instance that combines the source lat and lon
values.

Note that the GPSNavX output was encoded in ``Western (Mac OS Roman)``.
This can make CSV parsing a bit more complex because there will be
Unicode characters that the CSV module doesn't always handle gracefully.
However, the patterns used for parsing tolerate the extraneous bytes
that appear in the midst of degree-minute values.

..  _`planning.cli`:

Command-Line Interface
======================

Writes a sequence of :py:class:`Schedule` objects to a given target file.

The file will have the following columns:

    "Name", "Lat", "Lon", "Desc",
    "Distance (nm)", "True Bearing", "Magnetic Bearing",
    "Distance Run", "Elapsed HH:MM"

Note that we apply some rounding rules to these values before writing them
to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
an inch, or 2 cm: more accurate than the GPS position.
The bearing is rounded to zero places.

..  note::

    It's hard to steer to a given degree,
    much less a fraction of a degree. Classically, the mariner's compass divides
    the circle into 32 points; this is 12.5 degrees each point.
    The width of your fist at arm's length is 10°. If you extend index finger and pinky,
    that's 15°. That's about as close as you can steer by hand.

..  _`planning-cli`:

Command-Line Interface
======================

Typical use cases for this module include the following.

-   Run from the command line:

..  parsed-literal::

    python -m navtools.planning -s 5.0 '../../Sailing/Cruising Plans/Lewes 2011/Jackson Creek to Cape Henlopen -- Offshore.gpx'

-   Run within a Python script:

..  parsed-literal::

    from navtools.planning import plan
    plan( '../../Sailing/Cruising Plans/Routes/Whitby Rendezvous.csv', 5.0 )
    plan( '../../Sailing/Cruising Plans/Routes/Whitby Rendezvous.gpx', 5.0 )

Implementation
==============

..  py:module:: navtools.planning

A waypoint on a route
---------------------

..  autoclass:: RoutePoint
    :members:
    :undoc-members:

CSV input parsing
-----------------

..  autofunction:: csv_to_RoutePoint

GPX input parsing
-----------------

..  autofunction:: gpx_to_RoutePoint

Point with Distance and Bearing
-------------------------------

..  autoclass:: RoutePoint_Rhumb

Creating the point with distance and bearing
--------------------------------------------

..  autofunction:: gen_rhumb

Point with Distance, Bearing, and Declination
---------------------------------------------

..  autoclass:: RoutePoint_Rhumb_Magnetic

Creating declination
--------------------------------------------

..  autofunction:: gen_mag_bearing

A Waypoint with Schedule Details
--------------------------------

..  autoclass:: SchedulePoint

Building a schedule
-------------------

..  autofunction:: gen_schedule


Writing The CSV Output
----------------------

..  autofunction:: nround

..  autofunction:: write_csv

The :py:func:`plan` application
----------------------------------

..  autofunction:: plan

The :py:func:`main` CLI
-----------------------

..  autofunction:: main

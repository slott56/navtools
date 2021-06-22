###############################################################
:py:mod:`navtools.planning` -- Route Planning Application
###############################################################

..  py:module:: planning

The :py:mod:`planning` application is used to do voyage planning.
It computes range, bearing and elapsed time for points along a route.

Here's the structure of the classes in this application:

..  uml::

    @startuml
    component planning {
        class Waypoint_Rhumb {
            point : Waypoint
        }
        class Waypoint_Rhumb_Magnetic {
            point: Waypoint_Rhumb
        }
        Waypoint_Rhumb_Magnetic *-> Waypoint_Rhumb
        class SchedulePoint {
            point: Waypoint_Rhumb
        }
        SchedulePoint *-> Waypoint_Rhumb
    }
    component navigation {
        class Waypoint {
            lat: Lat
            lon: Lon
        }
    }
    Waypoint_Rhumb *-- Waypoint
    @enduml

This module includes several groups of components.

-   The :ref:`planning-input` group is the functions and classes that
    acquire input from the GPX or CSV file.

-   The :ref:`planning-computations` functions work out range and bearing, magnetic bearing, total distance run,
    and elapsed time in minutes and hours.

-   The :ref:`planning-output` group is the functions to write the CSV result.

-   Finally, the :ref:`planning-cli` components are used
    to build a proper command-line application.


..  py:module:: navtools.planning

..  _planning-input:

Input Parsing
===============

The purpose of input parsing is to create :py:class:`Waypoint` objects
from input file sources.

A :py:class:`Waypoint` is a 5-tuple of name, latitude, longitude, description
and "point" information.   The "point" information is a
:py:class:`navigation.LatLon` instance that combines the source lat and lon
values.

The input parsing supports two formats: CSV and GPX.  Each source format has
a different kind of parser.  The CSV parser uses the :mod:`csv` module.  The GPX parser uses
:mod:`xml.etree`; it uses the ``findall()`` method to iterate
through all of the rows.

Note that the GPSNavX output was encoded in ``Western (Mac OS Roman)``.
This can make CSV parsing a bit more complex because there will be
Unicode characters that the CSV module doesn't always handle gracefully.
However, the patterns used for parsing tolerate the extraneous bytes
that appear in the midst of degree-minute values.


..  autofunction:: csv_to_Waypoint

..  autofunction:: gpx_to_Waypoint

..  _planning-computations:

Planning Computations
=====================

The various navigation calculations use an immutable object (or functional
programming) style.  A series of functions create new, richer objects
from the initial :py:class:`Waypoint` objects.

Specifically, we use the following kind of function composition.

..  code-block:: python

    gen_schedule(
        gen_mag_bearing(
            gen_rhumb(point_iter),
            variance),
        speed)

The ``point_iter`` is a CSV or GPX file with the route defined as a series of waypoints.


Point with Distance and Bearing
-------------------------------

..  autoclass:: Waypoint_Rhumb

..  autofunction:: gen_rhumb

Point with Distance, Bearing, and Declination
---------------------------------------------

..  autoclass:: Waypoint_Rhumb_Magnetic

..  autofunction:: gen_mag_bearing

Schedule Details
--------------------------------

..  autoclass:: SchedulePoint

..  autofunction:: gen_schedule



..  _planning-output:

Output Writing
======================

Writes a sequence of :py:class:`Schedule` objects to a given target file.

The file will have the following columns:

    "Name", "Lat", "Lon", "Desc",
    "Distance (nm)", "True Bearing", "Magnetic Bearing",
    "Distance Run", "Elapsed HH:MM"

Note that we apply some rounding rules to these values before writing them
to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
an inch, or 2 cm more accurate than the GPS position.
The bearing is rounded to zero places.

..  note::

    It's hard to steer to a given degree,
    much less a fraction of a degree. Classically, the mariner's compass divides
    the circle into 32 points; this is 12.5 degrees each point. That's an appropriate rounding
    for coastal cruising.

    The width of your fist at arm's length is 10°. If you extend index finger and pinky,
    that's 15°. In the middle is all the accuracy you have when steering by hand.


..  autofunction:: nround

..  autofunction:: write_csv


..  _`planning-cli`:

Command-Line Interface
======================

Typical use cases for this module include the following.

-   Run from the command line:

    ..  code-block:: bash

        python -m navtools.planning -s 5.0 '../../Sailing/Cruising Plans/Lewes 2011/Jackson Creek to Cape Henlopen -- Offshore.gpx'

-   Run within a Python script:

    ..  code-block:: python

        from navtools.planning import plan
        from pathlib import Path
        routes = Path("/path/to/routes")
        plan(routes/'Whitby Rendezvous.csv', 5.0)
        plan(routes/'Whitby Rendezvous.gpx', 5.0)


The :py:func:`plan` application
----------------------------------

..  autofunction:: plan

The :py:func:`main` CLI
-----------------------

..  autofunction:: main

Improvements
============

There are several improvements required.

..  todo:: Refactor magnetic bearing computation

    Include variance directly, not as a separate step.

..  todo:: Locate the sunrise equation and include anticipated time-of-day for an ETA

    See https://gml.noaa.gov/grad/solcalc/solareqns.PDF

..  todo:: Compute the locations at noon of each day.

    This requires looking at waypoints before and after local noon, Splitting the segment
    to find noon, and adding a waypoint with no course change.


###############################################################
:py:mod:`planning` -- Route Planning Application
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

Planning Approach
=================

Currently, the planning application computes distances and Estimated Time Enroute (ETE) for each leg.
It does little more than this. The approach is embodied by creating a :py:class:`SchedulePoint` object.
This is direct enrichment of the :py:class:`Waypoint` instances along the route.

There are a number of potential improvements to this approach:

-   Include an estimated time of departure (ETD) as a basis for computing ETE and ETA.

-   Include the position of the sun for each ETA.

-   Include a Noon position on any leg that spans local noon.


The goal is to match the output content of :py:mod:`opencpn_table`:

    - waypoint: Waypoint
    - leg: int
    - ETE: Optional["Duration"]
    - ETA: Optional[datetime.datetime]
    - ETA_summary: Optional[str]
    - speed: float
    - tide: Optional[str]
    - distance: Optional[float]
    - bearing: Optional[float]
    - course: Optional[float] = None


Improvements
============

There are several improvements required.

Time-of-Day
-----------

..  todo:: Locate the sunrise equation and include anticipated time-of-day for an ETA

    See https://gml.noaa.gov/grad/solcalc/solareqns.PDF

Noon Location
-------------

..  todo:: Compute the locations at noon of each day.

    This requires looking at waypoints before and after local noon, Splitting the segment
    to find noon, and adding a waypoint with no course change.

A route is a sequence of points. Of those, two points, :math:`A` and :math:`B`, have times, :math:`T(x)`, that bracket noon, :math:`N`.

..  math::

    T(A) \leq N \leq T(B)

There are three cases here, two of which are trivial. If :math:`T(A) = N` or :math:`N = T(B)`, there's
no further computation required. The interesting case, then, is :math:`T(A) < N < T(B)`.

We know the distance, :math:`d = D(A, B)`, and bearing, :math:`\theta = \Theta(A, B)`.

We also know the time, :math:`t`, to traverse the leg, given a speed, :math:`s`.

..  math::

    t = \frac{D(A, B)}{s}

The time until noon, :math:`N - T(A)`, is a fraction of the overall duration of the leg, :math:`t`.
Which gives us distance until noon, :math:`d_n`,

..  math::

    \frac{N - T(A)}{t} = \frac{d_n}{d}

or,

..  math::

    d_n = \frac{D(A, B)[N - T(A)]}{\frac{D(A, B)}{s}} = s[N - T(A)]

We can then offset from point :math:`A` by distance :math:`d_n` in direction :math:`\theta` to compute
the noon location. This is the :py:func:`navigation.destination` function.

The destination function, :math:`D( p_1, d, \theta )`, is defined like this.

..  math::

    D_{\phi}( p_1, d, \theta ), &\text{ latitude at distance $d$, angle $\theta$ from $p_1$}\\
    D_{\lambda}( p_1, d, \theta ), &\text{ longitude at distance $d$, angle $\theta$ from $p_1$}

    D( p_1, d, \theta ) = \Bigl( D_{\phi}( p_1, d, \theta ), D_{\lambda}( p_1, d, \theta ) \Bigr)

The definition of these two functions are in :ref:`calc.destination`.

Forward and Reverse Plans
--------------------------

An event more sophisticated planner would allow for two kinds of plans:

-   A "forward" plan uses a Scheduled Time of Departure (STD) to compute a sequence of ETE and ETA's.

-   A "reverse" plan would use a Scheduled Time of Arrival (STA) and work backwords to
    compute departures and times enroute. This would lead to a Scheduled Time of Departure (STD).

The idea is to reduce the amount of work done with a spreadsheet outside :py:mod:`navtools`.

We can also imagine a plan with both STD and STA information from which speed is deduced
to meet the scheduled times. This is a two pass operation.

1. Starting from STD or STA, compute a plan that involves pre-dawn or post-dusk arrivals or departures.

2. Adjust departure to be earlier or arrival to be later -- within daylight times -- and compute the speed required.

This is a more sophisticated planning operation, but can be automated because the constraints are well-defined.

Implementation
==============

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

..  uml::

    @startuml
    start
    switch (format?)
    case ( CSV )
        :route = csv_to_Waypoint;
    case ( GPX )
        :route = gpx_to_Waypoint;
    endswitch
    :gen_schedule;
    :write_csv;
    stop
    @enduml



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


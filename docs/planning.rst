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
Given this information we can compute an arrival time based on a departure time.

The approach is embodied by creating a :py:class:`SchedulePoint` object.
This is direct enrichment of the :py:class:`Waypoint` instances along the route.

Here's how the solution is based on source data.

1.  A route can be understood as a sequence of :math:`n` waypoints.

    ..  math::

        r_w = \langle w_0, w_1, w_2, ..., w_{n-1} \rangle

2.  A waypoint is a latitutde (:math:`\phi`), and longitude (:math:`\lambda`) pair.

    ..  math::

        w = \langle \phi, \lambda \rangle

3.  A route can also be understood as a sequence of legs, :math:`l_i(f, t)`, formed from pairs of waypoints,
    called "from" and "to".
    Note that we provide a placeholder leg, :math:`l_{n-1}`, so that each waypoint, :math:`w_x`, is
    the "from" item of a leg, :math:`l_x(w_x, w_{x+1} \cup \bot)`.

    ..  math::

        r_l = \langle l_0(w_0, w_1), l_1(w_1, w_2), ..., l_i(w_i, w_{i+1}), ..., l_{n-2}(w_{n-2}, w_{n-1}), l_{n-1}(w_{n-1}, \bot) \rangle

3.  The distance, :math:`d(f, t)`,  and bearing, :math:`\theta(f, t)`,
    are computed from legs, which are pairs of waypoints. We prefer nautical miles as the units.

    ..  math::

        d(l_i) = r(l_i \cdot f, l_i \cdot t) = r(w_i, w_{i+1}) \\
        \theta(l_i) = \theta(l_i \cdot f, l_i \cdot t) = \theta(w_i, w_{i+1})

4.  Given speed, :math:`s`, in knots, we can compute ETE for each leg, :math:`e(l_i; s)`.
    This is a duration generally in hours. It's often more useful in minutes than hours.

    ..  math::

        e(l_i; s) = 60 \frac{d(l_i)}{s}

We often summarize the ETE to a point, :math:`i`, on the route.
If :math:`i = n`, then, this is the total elapsed time enroute.

..  math::

    \sum\limits_{0 \leq x < i}e(l_x; s) = \frac{\sum\limits_{0 \leq x < i}d(l_x)}{s}


There are three summary computations:

-   Final Arrival Time, given speed, and Departure Time. :math:`A_n(r; s, T_0)`.

-   Initial Departure Time, given Arrival Time and speed. :math:`D_0(r; s, T_n)`.

-   Speed, given Initial Departure Time and Final Arrival Time. :math:`s(r; T_0, T_n)`.

We'll look at arrival time, first.

1.  Given speed, :math:`s`, in knots, and a departure time, :math:`T_0`,
    we can compute ETA's, :math:`A(l_i; s, T_0)`, for each leg.
    These are date-time stamps. We formulate this to show how it accumulates and the final result.

    ..  math::

        A(l_i; s, T_0)
            &= T_0 + e(l_i; s) + \left(\sum\limits_{0 \leq x < i}e(l_x; s)\right) \\
            &= T_0 + \left( \frac{\sum\limits_{0 \leq x \leq i}d(l_x)}{s} \right)

#.  The final arrival time, :math:`A_n`, then, is the last arrival time for the route, `r`,

    ..  math::

        A_n(r; s, T_0) = A(l_n; s, T_0)

We can also do the computation in the reverse direction to compute departure times, :math:`D(l_i; s, T_n)`
to work out the departure for leg :math:`l_i` required to have final arrival time `T_n`.
We can use this to work out the initial departure time, :math:`D_0(r; s, T_n)`.

1.  Given speed, :math:`s`, in knots, and an arrival time, :math:`T_n`,
    we can compute ETD's, :math:`D(l_i; s, T_n)`, for each preceeding leg.

    ..  math::

        D(l_i; s, T_n)
            &= T_n - e(l_i; s) - \left(\sum\limits_{0 \leq x < i}e(l_x; s)\right) \\
            &= T_n - \left( \frac{\sum\limits_{0 \leq x \leq i}d(l_x)}{s} \right)

#.  The initial departure time, :math:`D_0`, then, is the first departure time for the route, `r`,

    ..  math::

        D_0(r; s, T_n) = D(l_0; s, T_n)


Speed for a route, :math:`r`, given departure, :math:`T_0`, and arrival, :math:`T_n`.

    ..  math::

        s(r; T_0, T_n) = \frac{\sum\limits_{0 \leq i < n}d(l_i)}{T_n-T_0}


Improvements
============

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

A route is a sequence of waypoints forming legs.
One leg, :math:`l_a(w_a, w_{a+1})`, spans noon, :math:`N`.

We can think of arrival time and departure for this leg.

..  math::

        T_a = A(l_a; s, T_0) \\
        T_{a+1} = A(l_{a+1}; s, T_0)

..  math::

    T_a \leq N \leq T_{a+1}

There are three cases here, two of which are trivial. If :math:`T_a = N` or :math:`N = T_{a+1}`, there's
no further computation required. The interesting case, then, is :math:`T_a < N < T_{a+1}`.

We know the distance for this leg, :math:`d(l_a)`.
This gives us time enroute, :math:`e(l_a; s)`, to traverse the leg, given a speed, :math:`s`.

..  math::

    e(l_a; s) = \frac{d(l_a)}{s}

The time until noon, :math:`N - T_a`, is a fraction of the overall elapsed time of the leg, :math:`e(l_a; s)`.
Which gives us distance until noon for a given leg, at a tiven speed, :math:`N_d(l_a; s)`,

..  math::

    \frac{N - T_a}{e(l_a; s)} = \frac{N_d(l_a; s)}{d(l_a)}

or,

..  math::

    N_d(l_a; s) = \frac{d(l_a)[N - T_a]}{\frac{d(l_a)}{s}} = s[N - T_a]

We can then offset from point :math:`w_a` by distance :math:`N_d(la;s)` in direction :math:`\theta(l_a)` to compute
the noon location. This is the :py:func:`navigation.destination` function.

The destination function, :math:`D( w, d, \theta )`, is defined like this.

..  math::

    D_{\phi}( w, d, \theta ), &\text{ latitude at distance $d$, angle $\theta$ from $w$}\\
    D_{\lambda}( w, d, \theta ), &\text{ longitude at distance $d$, angle $\theta$ from $w$}

    D( w, d, \theta ) = \langle D_{\phi}( w, d, \theta ), D_{\lambda}( w, d, \theta ) \rangle

The definition of these two functions are in :ref:`calc.destination`.

Forward and Reverse Plans
--------------------------

Currently, only forward plans are supported.

An event more sophisticated planner would allow for all three kinds of plans:

-   A "forward" plan uses a Scheduled Time of Departure (STD) to compute a sequence of ETE and ETA's.

-   A "reverse" plan would use a Scheduled Time of Arrival (STA) and work backwords to
    compute departures and times enroute. This would lead to a Scheduled Time of Departure (STD).

-   A "speed" plan would compute optimal speed to pass between given STD and STA.

-   We can also imagine pinning specific waypoints to specific STA or STD to compute variant
    speeds along a route.

The idea is to reduce the amount of work done with a spreadsheet outside :py:mod:`navtools`.


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


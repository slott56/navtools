###############################################################
:py:mod:`navtools.opencpn_table` -- OpenCPN Table Application
###############################################################

The :py:mod:`opencpn_table` application is used to do extract a useful CSV
formatted file from the OpenCPN planning display.

The display is a CSV file with a great deal of supplemental formatting.
This application strips away the formatting so the data can be more easily
loaded into a spreadsheet.

Here's the structure of this application

..  uml::

    @startuml
    component opencpn_table {
        class Leg
        class Route
        Route *-- "*" Leg
        class Duration
        Leg -- Duration
    }
    component navigation {
        class Waypoint {
            lat: Lat
            lon: Lon
        }
    }
    Leg *-- Waypoint
    @enduml


This module includes several groups of components.

-   The :ref:`opencpn-input` group is the functions and classes that
    acquire input from the GPX or CSV file.

-   The :ref:`opencpn-output` group is the functions to write the CSV result.

-   Finally, the :ref:`opencpn-cli` components are used
    to build a proper command-line application.

..  py:module:: navtools.opencpn_table

..  _`opencpn-input`:

Input Parsing
=============

The data is a CSV file with a fixed set of columns.

::

    "Leg", "To waypoint", "Distance", "Bearing",
    "Latitude", "Longitude", "ETE", "ETA",
    "Speed", "Next tide event", "Description", "Course"


Core objects
------------

A :py:class:`Leg` is the space between waypoints.
Rather than repeat each endpoint, only the ending
point is shown and the starting point is implied
by the previous leg's ending point.

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



..  _`opencpn-output`:

Output Writing
==============

We're creating a CSV output file with de-formatted inputs. We maintain the column
titles for simplistic compatibility with the source file.

..  autofunction:: to_html

..  autofunction:: to_csv

..  _`opencpn-cli`:

Command-Line Interface
======================

We generally use it like this:

..  code-block:: bash

    python -m navtools.opencpn_table 'planned_route.csv'

..  autofunction:: main


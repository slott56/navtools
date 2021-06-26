######################################################################
:mod:`waypoint_merge` -- Waypoint and Route Merge Application
######################################################################

With multiple chart plotters, it's very easy to have waypoints
defined (or modified) separately. It's necessary to reconcile
the changes to arrive at a single, comprehensive list of waypoints
that can be then distributed to all devices.

This requires reading and comparing GPX files to arrive at a master
list of waypoints.

Similar analysis must be done for routes to accomodate changes.


Here's the structure of this application

..  uml::

    @startuml
    component waypoint_merge {
        class Waypoint_Plot
        class History
        History *-- "2" Waypoint_Plot
        class WP_Match {
            wp_1: Waypoint_Plot
            wp_2: Waypoint_Plot
        }
        WP_Match::wp_1 -- "?" Waypoint_Plot
        WP_Match::wp_2 -- "?" Waypoint_Plot
    }
    component navigation {
        class Waypoint {
            lat: Lat
            lon: Lon
        }
    }
    Waypoint_Plot *-- Waypoint

    @enduml

This module includes several groups of components.

-   The :ref:`merge-input` group is the functions and classes that
    acquire input from the GPX or CSV file.

-   The :ref:`merge-computations` functions work out range and bearing, magnetic bearing, total distance run,
    and elapsed time in minutes and hours.

-   The :ref:`merge-output` group is the functions to write the CSV result.

-   Finally, the :ref:`merge-cli` components are used
    to build a proper command-line application.

..  py:module:: navtools.waypoint_merge

..  _`merge-input`:

Input Parsing
=============

There are two kinds of inputs

-   GPX files. Each source has a unique logical layout imposed over a common physical format.

    -   OpenCPN GPX. These tend to be richly detailed, using OpenCPN extensions.

    -   Chartplotter GPX. These are minimal, skipping import details like GUID's that
        provide unique identity to routes and waypoints.

-   USR files. Also called "Lowrance USR files." These are a binary dump of chartplotter
    information.


Base Classes
------------

..  autoclass:: Waypoint_Plot

Input Processing
-----------------

..  autofunction:: parse_datetime

..  autofunction:: opencpn_GPX_to_WayPoint

..  autofunction:: lowrance_GPX_to_WayPoint

..  autofunction:: lowrance_USR_to_WayPoint

..  _`merge-computations`:

Processing
==========

This is part of a four-step use case.

1.  Dump charplotter-unique waypoints. These are not on the computer, which is the
    single source of truth.

2.  Merge the waypoints, loading OpenCPN. Make manual edits and updates to cleanup and simplify.
    Locate "to-be deleted" waypoints. These are duplicates (or near duplicates) that need to
    be merged and reconciled. Removing a waypoint can break routes, so route editing is part of
    this.

3.  Dump chartplotter-unique routes (if any.) These are not on the computer, which is the
    single source of truth.

4.  Merge the routes into OpenCPN. Make any manual edits.

Adjacency
---------

While we can use loxodromic distance, this is a lot of computation.

Instead we use OLC. Using truncated OLC permits flexible adjacency via simple string-based processing.
Less math.

See https://en.m.wikipedia.org/wiki/Open_Location_Code

Classes and Functions
---------------------

..  autoclass:: History

..  autoclass:: WP_Match

..  autofunction:: match_gen

..  _`merge-output`:

Output Writing
==============

We use Jinja2 to write an XML-format file with the
waypoints that need to be updated in OpenCPN.

..  autofunction:: waypoint_to_GPX

..  _`merge-cli`:

CLI
====


A typical command looks like this::

    python navtools/waypoint_merge.py -p data/WaypointsRoutesTracks.usr -c "data/2021 opencpn waypoints.gpx" --by name --by geocode

This produces a report comparing the .USR output from the chartplotter
with the GPX data dumped from OpenCPN. Waypoints are compared by name for literal matches,
then by Geogode for likely matches that have different names.

The output is a list of points that have been created or changed in the
chartplotter, plus a less-interesting list of points that are only
in the computer.

..  autofunction:: report

..  autofunction:: main


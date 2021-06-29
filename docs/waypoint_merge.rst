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

1.  Dump charplotter-unique waypoints. These are not on the computer, which should be the
    single source of truth.

2.  Merge the waypoints, loading OpenCPN. Make manual edits and updates to cleanup and simplify.
    Locate "to-be deleted" waypoints. These are duplicates (or near duplicates) that need to
    be merged and reconciled. Removing a waypoint can break routes, so route editing is part of
    this. There several cases:

    -   Same name, new location. These are updates to OpenCPN to move an existing waypoint
        to a new location. It's not clear how this should be done, but GUID matching should
        make this work.

    -   Different names, proximate locations. The waypoint was renamed or is a duplicate.

    -   New name, unique location. These are simply added.

3.  Dump chartplotter-unique routes (if any.) These are not on the computer, which is the
    single source of truth.

4.  Merge the routes into OpenCPN. Make any manual edits.

We're focused on step 2, and the various comparisons between waypoints to determine
what merge should be done.
Step 2 decomposes into three phases:

-   Survey of differences. This is an text (or HTML) file with a comparison using
    all of rules.

-   Preparation of modifications; this is a GPX file that can be used to load OpenCPN.
    Some manual changes may be needed before these waypoints can be used.

-   Preparation of adds; this is a GPX file that is simply loaded into OpenCPN,
    since the waypoints are all new.

Comparisons
-----------

We have a number of comparison rules among waypoints. We can meaningfully compare waypoints
on any of the following attributes:

-   "name" -- While names change, they also reflect old technology limitations.
    So, some names are sometimes rewritten on a new device. There's no near-miss
    matching here because "CHPTNK6" may have become "Choptank Entrance 6" with
    few overlapping letters.

-   "guid" -- These should be immutable, but it's not clear if it's preserved in
    tranfers between devices.

-   "distance" -- this is the waypoint-to-waypoint distance computation. This is
    the equirectangular distance. While accurate it's also computationally intensive.

-   "geocode" -- this is the faster geocode-based proximity test. Intead of
    computing :math:`m \times n` distances, we can compute :math:`m + n` geocodes,
    and use string comparison for a simple proximity check.
    The loxodromic or equirectangular distance involves a lot of computation.
    Using truncated OLC permits flexible adjacency via simple string-based processing.
    Less math. See https://en.m.wikipedia.org/wiki/Open_Location_Code

    ..  csv-table::

        positions,degrees,distances
        6,1/20,"5566 meters, 3 nmi"
        8,1/400,"278 meters, .15 nmi"
        10,1/8000,"13.9 meters, 45 feet"


This leads to a four comparison outcomes.

-   **Same Name -- Different Locations**.
    This means a waypoint was moved. It can also mean two waypoints were created near
    each other with coincidentally identical names. This is a GPX file of waypoints
    which must be modified in OpenCPN.

-   **Different Names -- Proximate Locations**.
    These are likely simple duplicates; one of the two must be removed,
    and the other used for all routes. Depending on the use within OpenCPN routes,
    this may be a complex change to modify reoutes to replace a waypoint.

-   **Completely Different**.
    In this case, Chartplotter points need to be added to the OpenCPN computer points.
    This should be visible as a GPX file of waypoints to add.

-   **The Same**.
    These are simple duplicates that can be ignored.

Classes and Functions
---------------------

..  autoclass:: History

..  autoclass:: List_Compare

..  autoclass:: CompareByName

..  autoclass:: CompareByGUID

..  autoclass:: CompareByDistance

..  autoclass:: CompareByGeocode

..  autoclass:: duplicates

..  autofunction:: survey


..  _`merge-output`:

Output Writing
==============

We translae the two sequences of history information into a single
stream of :py:class:`WP_Match` instances. We can then summarize these.

We use Jinja2 to write an XML-format file with the
waypoints that need to be updated in OpenCPN.

..  autoclass:: WP_Match

..  autofunction:: match_gen

..  autofunction:: waypoint_to_GPX

..  autofunction:: computer_upload

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

..  autofunction:: main


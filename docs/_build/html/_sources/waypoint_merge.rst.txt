##########################################################
:mod:`navtools.waypoint_merge` -- Waypoint and Route Merge
##########################################################

With multiple chart plotters, it's very easy to have waypoints
defined (or modified) separately. It's necessary to reconcile
the changes to arrive at a single, comprehensive list of waypoints
that can be then distributed to all devices.

This requires reading and comparing GPX files to arrive at a master
list of waypoints.

Similar analysis must be done for routes to accomodate changes.

Input Parsing
=============

There are two kinds of inputs

-   GPX files. Each source has a unique logical layout imposed over a common physical format.

    -   OpenCPN GPX. These tend to be richly detailed, using OpenCPN extensions.

    -   Chartplotter GPX. These are minimal, skipping import details like GUID's that
        provide unique identity to routes and waypoints.

-   USR files. Also called "Lowrance USR files." These are a binary dump of chartplotter
    information.

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
=========

While we can use loxodromic distance, this is a lot of computation.

Instead we use OLC. Using truncated OLC permits flexible adjacency via simple string-based processing.
Less math.

See https://en.m.wikipedia.org/wiki/Open_Location_Code


Implementation
==============

..  py:module:: navtools.waypoint_merge

..  autoclass:: WayPoint

Input Processing
-----------------

..  autofunction:: parse_datetime

..  autofunction:: opencpn_GPX_to_WayPoint

..  autofunction:: lowrance_GPX_to_WayPoint

..  autofunction:: lowrance_USR_to_WayPoint

Output Processing
-----------------

..  autofunction:: waypoint_to_GPX

Matching
--------

..  autoclass:: History

..  autoclass:: WP_Match

..  autofunction:: match_gen

Output
------

..  autofunction:: report

..  autofunction:: main


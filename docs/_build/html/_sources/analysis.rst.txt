###############################################################
:py:mod:`navtools.analysis` -- Track Analysis Application
###############################################################

The :py:mod:`analysis` application is used to do voyage analysis.
This can make a more useful log from manually prepared log data or
tracks dumped from OpenCPN (or iNavX.)
It's helpful to add the distance run between waypoints as well as the
elapsed time between waypoints.

This additional waypoint-to-waypoint time and distance allows
for fine-grained analysis of sailing performance.

This module includes three groups of components.

The `Input Parsing`_ group is the functions and a namedtuple that
acquire input from the GPX or CSV file.

The application processing components consume track data
and computes derived values including distances,
times, and rates.

The :ref:`analysis.cli` components are used to build a proper command-line application.

Input Parsing
===============

The purpose of input parsing is to create :py:class:`LogEntry` objects
from input file sources.

Manually prepared data will be a CSV in the following form

..  code-block:: text

    Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location
    9:21 AM,37 50.424N,076 16.385W,None,0,None,1200 RPM,,,Cockrell Creek
    10:06 AM,37 47.988N,076 16.056W,None,6.6,None,1500 RPM,315,7.0,

This is essentially a deck log entry: time, lat, lon, course over ground,
speed over ground, rig configuration, engine RPM, wind information, and any
additional notes on the location.

The times for the manual entry are generally local.

iNavX track has the following format for CSV extract

..  code-block:: text

    2011-06-04 13:12:32 +0000,37.549225,-76.330536,219,3.6,,,,,,
    2011-06-04 13:12:43 +0000,37.549084,-76.330681,186,3.0,,,,,,

The columns with data include date, latitude, longitude, cog, sog, heading, speed, depth, windAngle, windSpeed, comment.  Not all of these
fields are populated unless OpenCPN (or iNavX) gets an instrument feed.

iNavX track has the following format for GPX extract

..  code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
    <gpx version="1.1" creator="iNavX"
    xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
    <trk>
    <name>TRACK_041812</name>
    <trkseg>
    <trkpt lat="37.549225" lon="-76.330536">
    <time>2011-06-04T13:12:32Z</time>
    </trkpt>
    <trkpt lat="37.549084" lon="-76.330681">
    <time>2011-06-04T13:12:43Z</time>
    </trkpt>
    </trkseg>
    </trk>
    </gpx>

The iPhone iNavX can save track information via
http://x-traverse.com/.  These are standard GPX files, and are
identical with the tracks created directly by iNavX.

..  _`analysis.cli`:

Command-Line Interface
======================

Typical use cases for this module include the following:

-   Command Line:

..  parsed-literal::

    python -m navtools.analysis '../../Sailing/Cruise History/2011 Reedville/reedville.csv'

-   Within a Python Script:

..  parsed-literal::

    from navtools.analysis import analyze
    analyze( '../../Sailing/Cruise History/2011 Reedville/jackson.csv', 5.0 )


Implementation
==============

..  py:module:: navtools.analysis

Date parsing
-------------

..  autofunction:: parse_date

Base Log Entry
--------------

..  autoclass:: LogEntry
    :members:
    :undoc-members:

CSV input parsing
-----------------

..  autofunction:: csv_to_LogEntry

GPX input parsing
-----------------

..  autofunction:: gpx_to_LogEntry

Log Entry With Derived Details
-------------------------------

..  autoclass:: LogEntry_Rhumb
    :members:
    :undoc-members:

Computing Details
-----------------

..  autofunction:: gen_rhumb

Writing The CSV Output
----------------------

..  autofunction:: nround

..  autofunction:: write_csv

The :py:func:`analyze` application
----------------------------------

..  autofunction:: analyze

The :py:func:`main` CLI
-----------------------

..  autofunction:: main

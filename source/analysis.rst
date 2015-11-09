..    #!/usr/bin/env python3

###############################################################
Track Analysis Application
###############################################################

..  py:module:: analysis

The :py:mod:`analysis` application is used to do voyage analysis.
This can make a more useful log from manually prepared log data or
tracks dumped from GPSNavX.  It's helpful to add the distance
run between waypoints as well as the elapsed time between
waypoints.

This additional waypoint-to-waypoint time and distance allows
for fine-grained analysis of sailing performance.

This module includes three groups of components.
The `Input Parsing`_ group is the functions and a namedtuple that
acquire input from the GPX or CSV file.

The `Application Processing`_ functions and namedtuples
compute range between waypoints.

Finally, the `Command-Line Interface`_ components are used
to build a proper command-line application.

Overheads
===========

::

    from . import navigation

    import csv
    import xml.etree.ElementTree
    from xml.etree.ElementTree import QName
    import sys
    import os
    from collections import namedtuple
    import datetime
    import argparse
    import pathlib

Input Parsing
===============

The purpose of input parsing is to create :py:class:`LogEntry` objects
from input file sources.

Manually prepared data will be a CSV in the following form

..  parsed-literal::

    Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location
    9:21 AM,37 50.424N,076 16.385W,None,0,None,1200 RPM,,,Cockrell Creek
    10:06 AM,37 47.988N,076 16.056W,None,6.6,None,1500 RPM,315,7.0,

This is essentially a deck log entry: time, lat, lon, course over ground,
speed over ground, rig configuration, engine RPM, wind information, and any
additional notes on the location.

The times for the manual entry are generally local.

GPSNavX track has the following format for CSV extract

..  parsed-literal::

    2011-06-04 13:12:32 +0000,37.549225,-76.330536,219,3.6,,,,,,
    2011-06-04 13:12:43 +0000,37.549084,-76.330681,186,3.0,,,,,,

The columns with data include date, latitude, longitude, cog, sog, heading, speed, depth, windAngle, windSpeed, comment.  Not all of these
fields are populated unless GPSNavX gets an instrument feed.

GPSNavX track has the following format for GPX extract

..  parsed-literal::

    <?xml version="1.0" encoding="utf-8"?>
    <gpx version="1.1" creator="GPSNavX"
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
identical with the tracks created directly by GPSNavX.

..  py:class:: UTC

    This is used to parse UTC timestamps from GPS device track files.
    This is more-or-less copied from the ``datetime`` module
    documentation.

::

    ZERO = datetime.timedelta(0)

    class UTC(datetime.tzinfo):
        def utcoffset(self, dt):
            return ZERO
        def tzname(self, dt):
            return "UTC"
        def dst(self, dt):
            return ZERO

    utc = UTC()

..  py:function:: parse_date( date, default=None )

    Parse a date string. We'll try a fairly large number
    of date, time, and datetime formats.

    -   Time only: HHMM, HH:MM and HH:MM AM/PM
    -   More complete m/d/y hhmm, m/d/y hh:mm and m/d/y hh:mm AM/PM
    -   Also y-mon-d hhmm, y-mon-d hh:mm and y-mon-d hh:mm AM/PM
    -   Plus mon-d hhmm, mon-d hh:mm and mon-d hh:mm AM/PM

    :param date: string to parse
    :param default: default date to use; if nothing is specified
        this will use the current date and time.
    :returns: :py:class:`datetime.dateetime` object.
        If nothing can be parsed, this will raise a :py:exc:`ValueError` exception.

Here are the formats that will be tried:

::

    default_date_formats = [
        "%H%M",
        "%H:%M",
        "%I:%M %p",
    ]

    default_year_formats = [
        "%m/%d %H%M", "%m/%d %H:%M", "%m/%d %I:%M %p",
        "%b %d %H%M", "%b %d %H:%M", "%b %d %I:%M %p",
        "%d %b %H%M", "%d %b %H:%M", "%d %b %I:%M %p",
        "%b-%d %H%M", "%b-%d %H:%M", "%b-%d %I:%M %p",
        "%d-%b %H%M", "%d-%b %H:%M", "%d-%b %I:%M %p",
        "%B %d %H%M", "%B %d %H:%M", "%B %d %I:%M %p",
    ]

    full_formats = [
        "%m/%d/%Y %H%M", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %H%M", "%m/%d/%y %H:%M", "%m/%d/%y %I:%M %p",
        "%Y-%m-%d %H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p",
        "%y-%m-%d %H%M", "%y-%m-%d %H:%M", "%y-%m-%d %I:%M %p",
        "%m-%d-%Y %H%M", "%m-%d-%Y %H:%M", "%m-%d-%Y %I:%M %p",
        "%m-%d-%y %H%M", "%m-%d-%y %H:%M", "%m-%d-%y %I:%M %p",
    ]

Here's the algorithm for trying all of these date formats.

::

    def parse_date( date, default=None ):
        if default is None: default= datetime.date.today()
        for fmt in default_date_formats:
            try:
                dt= datetime.datetime.strptime( date, fmt )
                dt= dt.replace( year=default.year, month=default.month, day=default.day )
                return dt
            except ValueError as e:
                pass
        for fmt in default_year_formats:
            try:
                dt= datetime.datetime.strptime( date, fmt )
                dt= dt.replace( year=default.year )
                return dt
            except ValueError as e:
                pass
        for fmt in full_formats:
            try:
                dt= datetime.datetime.strptime( date, fmt )
                return dt
            except ValueError as e:
                pass

..  py:class:: LogEntry

A :py:class:`LogEntry` object contains a date-time stamp, latitude,
longitude, a combined :py:class:`navigation.LatLon` object, and
the "extra_dict" of the original row's raw data as a dictionary.

::

    LogEntry= namedtuple( 'LogEntry', 'time,lat,lon,point,extra_dict' )

..  py:function:: csv_to_LogEntry( source, date=None )

    Parses a CSV file to yield an iterable sequence
    of :py:class:`LogEntry` objects.

    There are two formats:

    -   Standard (i.e., GPSNavX). These files have no header.
    -   Manual. These files **must** include a heading row for it to be processed.

    The heading row must use terms like the following:

        "date", "latitude", "longitude", "cog", "sog", "heading", "speed",
        "depth", "windAngle", "windSpeed", "comment"

    :param source: Open file or file-like object that can be read.
    :param date: :py:class:`datetime.datetime` object used to fill in default
        values for incomplete dates. By default, it's "now".
    :returns: iterable sequence of :py:class:`LogEntry` instances.

::

    def csv_to_LogEntry( source, date=None ):
        """Generate LogEntry from a CSV reader.

        :param source: an open CSV file.
        :param date: default date used for incomplete date formats.

        :returns: An iterator over :py:class:`LogEntry` objects.
        """
        if date is None:
            date= datetime.date.today()
        hdr = csv.Sniffer().has_header(source.read(512))
        source.seek(0)
        if hdr:
            trk= csv.DictReader( source )
            if not set(trk.fieldnames) >= set( "Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location".split(',')):
                raise TypeError( "Column Headings aren't valid" )
            def extract( row ):
                # Handle local time formats
                dt= parse_date( row['Time'], default=date )
                return dt, row['Lat'], row['Lon']
        else:
            trk= csv.DictReader( source, fieldnames=[
            "date", "latitude", "longitude", "cog", "sog", "heading", "speed", "depth", "windAngle", "windSpeed", "comment"] )
            def extract( row ):
                lat, lon = row["latitude"], row["longitude"]
                # Typical time: 2011-06-04 13:12:32 +0000
                dt= datetime.datetime.strptime(row['date'],"%Y-%m-%d %H:%M:%S +0000").replace(tzinfo=utc)
                return dt, lat, lon
        for row in trk:
            time, lat, lon = extract( row )
            try:
                point= navigation.LatLon( lat, lon )
                yield LogEntry( time, lat, lon, point, row )
            except TypeError as e:
                print( row )

For more complex situations (i.e., multi-day voyages with partial
date-time stamps in the log) this function isn't quite appropriate.
The simplistic assumption behind :py:func:`parse_date` are that a single
date is sufficient to fill in missing fields. In some cases, we might have
timestamps that roll past midnight without an obvious indicator of date
change. Or, we might have some notation like "d1, d2" or "+1d, +2d".

..  py:function:: gpx_to_LogEntry( source )

    Parses a CSV file to yield an iterable sequence
    of :py:class:`LogEntry` objects.

    :param source: Open file or file-like object that can be read.
    :returns: iterable sequence of :py:class:`LogEntry` instances.

Parsing the GPX is pretty easy.  However, transforming the
"raw" XML int0 a CSV-compatible form is done with a helper function
to turn XML into a sequence of 2-tuples.

::

    def gpx_to_LogEntry( source ):
        """Generate LogEntry from an GPX doc.

        :param source: an open XML file.

        :returns: An iterator over :py:class:`LogEntry` objects.
        """
        gpx_ns= "http://www.topografix.com/GPX/1/1"
        path = "/".join( n.text for n in (QName(gpx_ns, "trk"), QName(gpx_ns, "trkseg"), QName(gpx_ns, "trkpt") ) )
        time_tag = QName(gpx_ns, 'time')
        doc = xml.etree.ElementTree.parse( source )
        for pt in doc.findall( path ):
            lat, lon = pt.get('lat'), pt.get('lon')
            lat = navigation.Angle2.fromdegrees( float(lat) )
            lon = navigation.Angle2.fromdegrees( float(lon) )
            point= navigation.LatLon( lat, lon )
            # Typical time: 2011-06-04T15:21:03Z
            raw_dt= pt.findtext(time_tag.text)
            dt= datetime.datetime.strptime(raw_dt,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc)
            row_dict= dict( xml_to_pairs(pt) )
            yield LogEntry( dt,
                lat, lon,
                point,
                row_dict,
                )

..  py:function:: xml_to_pairs( pt )

    Transforms a sequence of XML ``<tag>value</tag>`` into a Python ``('tag', 'value')``
    sequence. This can be used to build a dictionary with a ``{'tag': 'value'}``
    structure.

    :param pt: an XML structure with a number of children to process.
    :returns: iterable over (tag, text) tuples.

::

    def xml_to_pairs(pt):
        for e in pt.iter():
            ns, _, tag = e.tag.partition('}')
            text = e.text.strip()
            if text:
                yield tag, text
            else:
                for attr in e.items():
                    yield attr


Application Processing
=======================

The raw point has distance, bearing, and delta-time to the next waypoint computed.
A final waypoint with no additional distacne, bearing, and delta-time is emitted.

..  py:class:: LogEntry_Rhumb

::

    LogEntry_Rhumb= namedtuple( 'LogEntry_Rhumb', 'point,distance,bearing,delta_time' )

..  py:function:: gen_rhumb( log_entry_iter )

    Transforms a sequence of :py:class:`LogEntry` instances into
    :py:class:`LogEntry_Rhumb` instances. The rhumb line distance, bearing, and
    delta-time are added to each entry.

    :param log_entry_iter: iterable sequence of :py:class:`LogEntry` instances.
        This can be produced by :py:func:`gpx_to_LogEntry` or :py:func:`csv_to_LogEntry`.
    :return: iterable sequence of  :py:class:`LogEntry_Rhumb` instances.

::

    def gen_rhumb( log_entry_iter ):
        """Generate LogEntry_Rhumb from LogEntry.

        Each point has range and bearing to the next point.
        The last point as no range and bearing.
        """
        p1= next(log_entry_iter)
        for p2 in log_entry_iter:
            #print( repr(p1), repr(p2) )
            r, theta= navigation.range_bearing( p1.point, p2.point )
            yield LogEntry_Rhumb( p1, r, theta, p2.time-p1.time )
            p1= p2
        yield LogEntry_Rhumb( p2, None, None, None )


Command-Line Interface
======================

..  py:function:: write_csv( log_entry_rhumb_iter, target )

    Writes a sequence of :py:class:`LogEntry_Rhumb`
    objects to a given target file.   The objects are usually built by the
    :py:func:`gen_rhumb` function.

    Since the source data has a poorly-defined set of columns,
    we emit just a few additional attributes joined onto the original,
    untouched row.

    :param log_entry_rhumb_iter:  iterable sequence of  :py:class:`LogEntry_Rhumb` instances.
        This is often the output of :py:func:`gen_rhumb`.
    :param target: File to which to write the analyzed rows.

Note that we apply some rounding rules to these values before writing them
to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
an inch, or 2 cm: more accurate than the GPS position.
The bearing is rounded to an 0 places.

::

    def nround(value, digits):
        return None if value is None else round(value,digits)

::

    def write_csv( log_entry_rhumb_iter, target ):
        def build_row_dict( log, td, tt ):
            row= { 'calc_distance' : nround(log.distance,5),
            'calc_bearing' : None if log.bearing is None else nround(log.bearing.degrees,0),
            'calc_time' : log.point.time,
            'calc_elapsed' : log.delta_time,
            'calc_total_dist' : nround(td,5),
            'calc_total_time' : tt, }
            row.update( log.point.extra_dict )
            return row
        try:
            # Get the first LogEntry_Rhumb to get the original headings.
            first= next( log_entry_rhumb_iter )
        except StopIteration:
            return # No data.
        headings= list(first.point.extra_dict.keys())
        headings += [ 'calc_distance', 'calc_bearing', 'calc_time', 'calc_elapsed', 'calc_total_dist', 'calc_total_time' ]
        rte_rhumb= csv.DictWriter( target, headings )
        rte_rhumb.writeheader()
        td= first.distance
        tt= first.delta_time
        rte_rhumb.writerow( build_row_dict(first, td, tt) )
        for log in log_entry_rhumb_iter:
            if log.distance is not None:
                td += log.distance
            if log.delta_time is not None:
                tt += log.delta_time
            rte_rhumb.writerow( build_row_dict(log, td, tt) )

..  todo:: :py:func:`write_csv` should not compute totals.

    Decompose this into two mapping functions:

    - log_entry_rhumb_iter computes the rhumb from log entries
    - log_entry_running_total_iter computes running totals.

    The final write_csv can then use this composition to write rows.

..  py:function:: analyze( log_filename, date=None )

    Analyze a log file, writing a new log file with additional
    calculated values.

    The :py:func:`gen_rhumb` calculation is applied to each row.

    :param log_filename: name of a log file to analyze.
        If the input is :samp:`{some_name}.csv` or :samp:`{some_name}.gpx`
        the output will be :samp:`{some_name} Distance.csv`.

    :param date: Default date to use when incomplete date-time fields
        are present in the input.

::

    def analyze( log_filename, date=None ):
        """Transform a simple log into a log with distances figured in.
        """
        if date is None:
            date= datetime.date.today()

        log_path = pathlib.Path(log_filename)
        ext= log_path.suffix.lower()
        distance_path= log_path.parent / (log_path.stem + " Distance" + ".csv")

        #print( distance_path )
        if ext == '.csv':
            with log_path.open() as source:
                with distance_path.open('w',newline='') as target:
                    track= gen_rhumb( csv_to_LogEntry( source, date ) )
                    write_csv( track, target )
        elif ext == '.gpx':
            with log_path.open() as source:
                with distance_path.open('w',newline='') as target:
                    track= gen_rhumb( gpx_to_LogEntry( source ) )
                    write_csv( track, target )
        else:
            raise Exception( "Can't process {0}".format(log_path) )

Main Function
================

::

    date_formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
        "%y-%m-%d",
        "%Y-%b-%d",
        "%y-%b-%d",
        "%Y-%B-%d",
        "%y-%B-%d",
    ]

..  py:function:: main()

    Parse command-line arguments to get the log file names and the default
    date to use for partial date strings.

    Then use :py:func:`analyze` to process each file, creating a :file:`{name} Distance.csv`
    output file with the detailed analysis.

::

    def main():
        parser= argparse.ArgumentParser()
        parser.add_argument( 'tracks', nargs='*', type=str )
        parser.add_argument( '-d', '--date', nargs='?', type=str, default=None )
        args = parser.parse_args()
        # Parse the assumed date for a time-only log in options.date
        if args.date is not None:
            for f in date_formats:
                try:
                    dt= datetime.datetime.strptime( args.date, f ).date()
                    break
                except ValueError:
                    pass
        else:
            dt= None
        # Process the track files.
        for file in args.tracks:
            analyze( file, date=dt )

Main Script
===============

::

    if __name__ == "__main__":
        main()


Typical use cases for this module include the following:

-   Command Line:

..  parsed-literal::

    python -m navtools.analysis '../../Sailing/Cruise History/2011 Reedville/reedville.csv'

-   Within a Python Script:

..  parsed-literal::

    from navtools.analysis import analyze
    analyze( '../../Sailing/Cruise History/2011 Reedville/jackson.csv', 5.0 )

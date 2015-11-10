..    #!/usr/bin/env python3

###############################################################
Route Planning Application
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

The `Application Processing`_ functions and namedtuples
compute range and true bearing, magnetic bearing, total distance run,
elapsed time in minutes and hours.

Finally, the `Command-Line Interface`_ components are used
to build a proper command-line application.

Overheads
==========

::

    from . import navigation

    import csv
    import xml.etree.ElementTree
    from xml.etree.ElementTree import QName
    import sys
    from collections import namedtuple
    import argparse
    import pathlib

Input Parsing
===============

The purpose of input parsing is to create :py:class:`RoutePoint` objects
from input file sources.

..  py:class:: RoutePoint

A :py:class:`RoutePoint` is a 5-tuple of name, latitude, longitude, description
and "point" information.   The "point" information is a
:py:class:`navigation.LatLon` instance that combines the source lat and lon
values.

::

    RoutePoint= namedtuple( 'RoutePoint', 'name,lat,lon,desc,point' )

..  py:function:: csv_to_RoutePoint( source )

    Parses the CSV files produced by GPSNavX to yield an iterable sequence
    of :py:class:`RoutePoint` objects.

    :param source: Open file or file-like object that can be read
    :returns: iterable sequence of :py:class:`RoutePoint` instances.

Note that the GPSNavX output is encoded in ``Western (Mac OS Roman)``.
This can make CSV parsing a bit more complex because there will be
Unicode characters that the CSV module doesn't always handle gracefully.
However, the patterns used for parsing tolerate the extraneous bytes
that appear in the midst of degree-minute values.

::

    def csv_to_RoutePoint( source ):
        """Generate RoutePoint from a CSV reader.  The assumed column
        order is "name", "lat", "lon" followed by any additional attributes.

        :param source: an open CSV file.

        :returns: An iterator over :py:class:`RoutePoint` objects.
        """
        rte= csv.reader(source)
        for name,lat,lon,desc in rte:
            point= navigation.LatLon( lat, lon )
            yield RoutePoint( name, lat, lon, desc, point )

..  py:function:: gpx_to_RoutePoint( source )

    Parses the GPX files
    produced by GPSNavX to yield an iterable sequence of :py:class:`RoutePoint` objects.

    :param source: Open file or file-like object that can be read
    :returns: iterable sequence of :py:class:`RoutePoint` instances.

::

    def gpx_to_RoutePoint( source ):
        """Generate RoutePoint from an XML doc.

        :param source: an open XML file.

        :returns: An iterator over :py:class:`RoutePoint` objects.
        """
        gpx_ns= "http://www.topografix.com/GPX/1/1"
        path = "/".join( n.text for n in (QName(gpx_ns, "rte"), QName(gpx_ns, "rtept") ) )
        name_tag= QName(gpx_ns, "name")
        desc_tag= QName(gpx_ns, "desc")
        doc = xml.etree.ElementTree.parse( source )
        for pt in doc.findall( path ):
            lat, lon = pt.get('lat'), pt.get('lon')
            lat = navigation.Angle2.fromstring( lat )
            lon = navigation.Angle2.fromstring( lon )
            point= navigation.LatLon( lat, lon )
            yield RoutePoint( pt.findtext(name_tag.text),
                lat, lon,
                pt.findtext(desc_tag.text),
                point )

Application Processing
=======================

..  py:class:: RoutePoint_Rhumb

This is a three-tuple with the original :py:class:`RoutePoint`,
the computed distance and computed (true) bearing to the next waypoint.

::

    RoutePoint_Rhumb= namedtuple( 'RoutePoint_Rhumb', 'point,distance,bearing' )

..  py:function:: gen_rhumb( route_points_iter )

    Calculates the simple, true bearing
    and distance between points.  Since this is for navigating forward
    along a route, each point is decorated with range and bearing to the
    next mark.  The last point is included, but has :samp:`None` for
    range and bearing.

    :param route_points_iter: Iterator over individual :py:class:`RoutePoint` instances.
        For example, the results of the :py:func:`csv_to_RoutePoint` or :py:func:`gpx_to_RoutePoint`
        function.

    :returns: iterator over :py:class:`RoutePoint_Rhumb` instances.

::

    def gen_rhumb( route_points_iter ):
        """Generate RoutePoint_Rhumb from RoutePoint."""
        p1= next( route_points_iter )
        for p2 in route_points_iter:
            r, theta= navigation.range_bearing( p1.point, p2.point )
            yield RoutePoint_Rhumb( p1, r, theta )
            p1= p2
        yield RoutePoint_Rhumb( p2, None, None )


..  py:class:: RoutePoint_Rhumb_Magnetic

This is a 4-tuple with the original :py:class:`RoutePoint_Rhumb`,
the computed distance, the true bearing and the bearing offset with
the magnetic variance.

::

    RoutePoint_Rhumb_Magnetic= namedtuple( 'RoutePoint_Rhumb_Magnetic',
        'point,distance,true_bearing,magnetic' )

..  py:function:: gen_mag_bearing( rhumb_iter, declination, date=None )

    Applies the given ``declination`` function to each point to
    compute the compass bearing value from the true bearing at each waypoint in a route.

    :param rhumb_iter: iterator over :py:class:`RoutePoint_Rhumb` instances.
        For example, the :py:func:`gen_rhumb` function.
    :param declination: function to compute declination.
        We often use :py:func:`navigation.declination` for this.
    :param date: Optional :py:class:`datetime.datetime` for which to compute
        the declination. If omitted, today's date is used.
    :returns: Iterator over :py:class:`RoutePoint_Rhumb_Magnetic` objects.

::

    def gen_mag_bearing( rhumb_iter, declination, date=None ): # A/k/a Variation
        """Generate RoutePoint_Rhumb_Magnetic from RoutePoint_Rhumb iterator."""
        for rp_rhumb in rhumb_iter:
            if rp_rhumb.bearing is None:
                yield RoutePoint_Rhumb_Magnetic(rp_rhumb, None, None, None)
            else:
                magnetic= rp_rhumb.bearing+declination(rp_rhumb.point.point,date)
                yield RoutePoint_Rhumb_Magnetic(
                    rp_rhumb, rp_rhumb.distance, rp_rhumb.bearing, magnetic )


..  py:class:: SchedulePoint

This is a 7-tuple with the :py:class:`RoutePoint_Rhumb`, plus
the various computed values: distance, true bearing, magnetic bearing, running distance, elapsed time in minutes, and elapsed time as a string with
hours and minutes formatted nicely.

::

    SchedulePoint = namedtuple( 'SchedulePoint',
        'point,distance,true_bearing,magnetic,running,elapsed_min,elapsed_hm' )

..  py:function:: gen_schedule( rhumb_mag_iter, speed= 5.0 )

    Calculates the elapsed
    distance and elapsed time (in two formats) for each waypoint.
    This is (technically) the time to the **next** waypoint.

    :param rhumb_mag_iter:  Iterator over :py:class:`RoutePoint_Rhumb_Magnetic` objects.
    :param speed: Default speed assumption to use; default is 5.0 knots.
    :returns: iterator over :py:class:`SchedulePoint` instances.

    An input bearing of :samp:`None` in a :py:class:`RoutePoint_Rhumb_Magnetic` object
    indicates the trailing waypoint which is the final destination.

::

    def gen_schedule( rhumb_mag_iter, speed= 5.0 ):
        """Create the schedule from an iterator over RoutePoint_Rhumb_Magnetic values."""
        distance = 0.0
        for rp in rhumb_mag_iter:
            if rp.true_bearing is None:
                yield SchedulePoint( rp.point, rp.distance, rp.true_bearing, rp.magnetic, None, None, None )
            else:
                distance += rp.distance
                elapsed_min= 60.*distance/speed
                h, m = divmod( int(elapsed_min), 60 )
                elapsed_hm = "{0:02d}h {1:02d}m".format( h, m )
                yield SchedulePoint( rp.point, rp.distance, rp.true_bearing, rp.magnetic, distance, elapsed_min, elapsed_hm )

Command-Line Interface
======================

..  py:function:: write_csv( sched_iter, target )

    Writes a sequence of :py:class:`Schedule` objects to a given target file.

    The file will have the following columns:

        "Name", "Lat", "Lon", "Desc",
        "Distance (nm)", "True Bearing", "Magnetic Bearing",
        "Distance Run", "Elapsed HH:MM"

    :param sched_iter:  iterator over :py:class:`SchedulePoint` instances.
        For example, the output from the :py:func:`gen_schedule` function.
    :param target: Open file (or file-like object) to which csv data will be
        written.

Note that we apply some rounding rules to these values before writing them
to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
an inch, or 2 cm: more accurate than the GPS position.
The bearing is rounded to zero places.

..  note::

    It's hard to steer to a given degree,
    much less a fraction of a degree. Classically, the mariner's compass divides
    the circle into 32 points; about 10 degrees each point.

::

    def nround(value, digits):
        return None if value is None else round(value,digits)

::

    def write_csv( sched_iter, target ):
        """sched_iter is an iterable of Schedule objects."""
        rte_rhumb= csv.writer( target )
        rte_rhumb.writerow(
            ["Name", "Lat", "Lon", "Desc",
            "Distance (nm)", "True Bearing", "Magnetic Bearing",
            "Distance Run", "Elapsed HH:MM", ]
            )
        for sched in sched_iter:
            lat, lon= sched.point.point.point.dm
            rte_rhumb.writerow(
                [sched.point.point.name, lat, lon, sched.point.point.desc,
                nround(sched.distance,5),
                None if sched.true_bearing is None else nround(sched.true_bearing.deg,0),
                None if sched.magnetic is None else nround(sched.magnetic.deg,0),
                nround(sched.running,5),
                sched.elapsed_hm, ]
                )

..  py:function:: plan( route_file, speed=5.0, date=None, variance=None )

    Transform a simple route file into a route with a detailed schedule. This
    will read the a :file:`.csv` or :file:`.gpx` file and produce a file
    with the schedule data.

    :param route_file: Source route, extracted from GPSNavX in CSV or GPX notation.
        For a file named :samp:`{somename}.csv` or :samp:`{somename}.gpx`
        the output will be :samp:`{somename} Schedule.csv`.

    :param speed: Assumed speed; default is 5.0kn.

    :param date: The :py:class:`datetime.datetime` for magnetic declination calculation;
        default is today.

    :param variance: Declination function to use.  Default is :py:func:`navigation.declination`.

::

    def plan( route_filename, speed=5.0, date=None, variance=None ):
        """Transform a simple route into a route with a detailed schedule.

        :param route_filename: Source route, extracted from GPSNavX in CSV.

        :param speed: Assumed speed; default is 5.0kn.

        :param date: Assumed date for magnetic declination; default is today.

        :param variance: Declination function to use.  Default is :py:func:`navigation.declination`
        """
        if variance is None: variance= navigation.declination

        def schedule(source, variance, date, speed ):
            sched= gen_schedule(
                gen_mag_bearing(
                    gen_rhumb( route ), variance, date), speed )
            return sched

        route_path = pathlib.Path(route_filename)
        ext= route_path.suffix.lower()
        schedule_path= route_path.parent / (route_path.stem + " Schedule" + ".csv")

        with schedule_path.open('w', newline='') as target:
            if ext == '.csv':
                with route_path.open() as source:
                    route= csv_to_RoutePoint( source )
                    sched= schedule(source, variance, date, speed)
                    write_csv( sched, target )
            elif ext == '.gpx':
                with route_path.open() as source:
                    route= gpx_to_RoutePoint( source )
                    sched= schedule(source, variance, date, speed)
                    write_csv( sched, target )
            else:
                raise Exception( "Can't process {0}".format(route_filename) )

Main Function
================

..  py:function:: main()

    Parse command-line arguments to get the routes file names, and the default speed
    to use.

    Then use :py:func:`plan` to process each file, creating a :file:`{name} Schedule.csv`
    output file with the detailed schedule.

::

    def main():
        parser= argparse.ArgumentParser()
        parser.add_argument( 'routes', nargs='*', type=str )
        parser.add_argument( '-s', '--speed', action='store', nargs='?', type=float, default=5.0 )
        args = parser.parse_args()
        for file in args.routes:
            plan( file, speed=args.speed )

Main Script
=============

::

    if __name__ == "__main__":
        main()

Typical use cases for this module include the following.

-   Run from the command line:

..  parsed-literal::

    python -m navtools.planning -s 5.0 '../../Sailing/Cruising Plans/Lewes 2011/Jackson Creek to Cape Henlopen -- Offshore.gpx'

-   Run within a Python script:

..  parsed-literal::

    from navtools.planning import plan
    plan( '../../Sailing/Cruising Plans/Routes/Whitby Rendezvous.csv', 5.0 )
    plan( '../../Sailing/Cruising Plans/Routes/Whitby Rendezvous.gpx', 5.0 )

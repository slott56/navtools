"""
Route Planning Application

The :py:mod:`planning` application is used to do voyage planning.
It computes range, bearing and elapsed time for points along a route.

The input parsing supports two formats: CSV and GPX.  Each source format has
a different kind of parser.  The CSV parser uses the :mod:`csv` module.  The GPX parser uses
:mod:`xml.etree`; it uses the ``findall()`` method to iterate
through all of the rows.

The various navigation calculations use an immutable object (or functional
programming) style.  A series of functions create new, richer objects
from the initial :py:class:`RoutePoint` objects.
"""

from navtools import navigation

import csv
import datetime
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
import sys
import argparse
from pathlib import Path
from typing import TextIO, Iterator, Iterable, Callable, Optional, NamedTuple, Union


class RoutePoint(NamedTuple):
    name: str
    lat: Union[navigation.Angle, str]
    lon: Union[navigation.Angle, str]
    desc: str
    point: navigation.LatLon

# ..  py:function:: csv_to_RoutePoint( source )
#

# ::

def csv_to_RoutePoint( source: TextIO ) -> Iterator[RoutePoint]:
    """
    Parses the CSV files produced by tools like GPSNavX, iNavX, OpenCPN
    to yield an iterable sequence of :py:class:`RoutePoint` objects.

    Generate RoutePoint from a CSV reader.  The assumed column
    order is "name", "lat", "lon" followed by any additional attributes.

    Note that the GPSNavX output was encoded in ``Western (Mac OS Roman)``.
    This can make CSV parsing a bit more complex because there will be
    Unicode characters that the CSV module doesn't always handle gracefully.
    However, the patterns used for parsing tolerate the extraneous bytes
    that appear in the midst of degree-minute values.

    :param source: Open file or file-like object that can be read
    :returns: iterable sequence of :py:class:`RoutePoint` instances.
    """
    rte= csv.reader(source)
    for name,lat,lon,desc in rte:
        point= navigation.LatLon( lat, lon )
        yield RoutePoint( name, lat, lon, desc, point )


def gpx_to_RoutePoint( source: TextIO ) -> Iterator[RoutePoint]:
    """
    Generate an iterable sequence of :py:class:`RoutePoint` objects an XML doc.

    :param source: an open XML file.
    :returns: An iterator over :py:class:`RoutePoint` objects.
    """
    gpx_ns= "http://www.topografix.com/GPX/1/1"
    path = "/".join( n.text for n in (QName(gpx_ns, "rte"), QName(gpx_ns, "rtept") ) )
    name_tag= QName(gpx_ns, "name")
    desc_tag= QName(gpx_ns, "desc")
    doc = xml.etree.ElementTree.parse( source )
    for pt in doc.findall( path ):
        lat_text, lon_text = pt.get('lat'), pt.get('lon')
        if not lat_text or not lon_text:
            raise ValueError(f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}")
        lat = navigation.Angle.fromstring( lat_text )
        lon = navigation.Angle.fromstring( lon_text )
        point= navigation.LatLon( lat, lon )
        yield RoutePoint(
            pt.findtext(name_tag.text) or "",
            lat,
            lon,
            pt.findtext(desc_tag.text) or "",
            point
        )


class RoutePoint_Rhumb(NamedTuple):
    point: RoutePoint
    distance: Optional[float]
    bearing: Optional[navigation.Angle]

def gen_rhumb( route_points_iter: Iterator[RoutePoint]) -> Iterator[RoutePoint_Rhumb]:
    """
    Calculates the simple, true bearing
    and distance between points.  Since this is for navigating forward
    along a route, each point is decorated with range and bearing to the
    next mark.  The last point is included, but has :samp:`None` for
    range and bearing.

    :param route_points_iter: Iterator over individual :py:class:`RoutePoint` instances.
        For example, the results of the :py:func:`csv_to_RoutePoint` or :py:func:`gpx_to_RoutePoint`
        function.

    :returns: iterator over :py:class:`RoutePoint_Rhumb` instances.

    """
    p1= next( route_points_iter )
    for p2 in route_points_iter:
        r, theta= navigation.range_bearing( p1.point, p2.point )
        yield RoutePoint_Rhumb( p1, r, theta )
        p1= p2
    yield RoutePoint_Rhumb( p2, None, None )


class RoutePoint_Rhumb_Magnetic(NamedTuple):
    point: RoutePoint_Rhumb
    distance: Optional[float]
    true_bearing: Optional[navigation.Angle]
    magnetic: Optional[navigation.Angle]


def gen_mag_bearing( rhumb_iter: Iterable[RoutePoint_Rhumb], declination: Callable[[navigation.LatLon, Optional[datetime.date]], float], date: Optional[datetime.date]=None ) -> Iterator[RoutePoint_Rhumb_Magnetic]:
    """
    Applies the given ``declination`` function to each point to
    compute the compass bearing value from the true bearing at each waypoint in a route.

    :param rhumb_iter: iterator over :py:class:`RoutePoint_Rhumb` instances.
        For example, the :py:func:`gen_rhumb` function.
    :param declination: function to compute declination.
        We often use :py:func:`navigation.declination` for this.
    :param date: Optional :py:class:`datetime.datetime` for which to compute
        the declination. If omitted, today's date is used.
    :returns: Iterator over :py:class:`RoutePoint_Rhumb_Magnetic` objects.

    # A/k/a Variation
    """
    for rp_rhumb in rhumb_iter:
        if rp_rhumb.bearing is None:
            yield RoutePoint_Rhumb_Magnetic(rp_rhumb, None, None, None)
        else:
            magnetic= rp_rhumb.bearing+declination(rp_rhumb.point.point, date)
            yield RoutePoint_Rhumb_Magnetic(
                rp_rhumb, rp_rhumb.distance, rp_rhumb.bearing, magnetic )


class SchedulePoint(NamedTuple):
    """Last point in a route has none of the derived attributes."""
    point: RoutePoint_Rhumb
    distance: Optional[float]
    true_bearing: Optional[navigation.Angle]
    magnetic: Optional[navigation.Angle]
    running: Optional[float]
    elapsed_min: Optional[float]
    elapsed_hm: Optional[str]


def gen_schedule( rhumb_mag_iter: Iterable[RoutePoint_Rhumb_Magnetic], speed: float = 5.0 ) -> Iterator[SchedulePoint]:
    """
    Calculates the elapsed
    distance and elapsed time (in two formats) for each waypoint.
    This is (technically) the time to the **next** waypoint.

    :param rhumb_mag_iter:  Iterator over :py:class:`RoutePoint_Rhumb_Magnetic` objects.
    :param speed: Default speed assumption to use; default is 5.0 knots.
    :returns: iterator over :py:class:`SchedulePoint` instances.

    An input bearing of :samp:`None` in a :py:class:`RoutePoint_Rhumb_Magnetic` object
    indicates the trailing waypoint which is the final destination.
    """
    distance = 0.0
    for rp in rhumb_mag_iter:
        if rp.true_bearing is None:
            yield SchedulePoint( rp.point, rp.distance, rp.true_bearing, rp.magnetic, None, None, None )
        else:
            distance += (rp.distance or 0)
            elapsed_min= 60.*distance/speed
            h, m = divmod( int(elapsed_min), 60 )
            elapsed_hm = "{0:02d}h {1:02d}m".format( h, m )
            yield SchedulePoint( rp.point, rp.distance, rp.true_bearing, rp.magnetic, distance, elapsed_min, elapsed_hm )


def nround(value: Optional[float], digits: int) -> Optional[float]:
    return None if value is None else round(value,digits)


def write_csv(sched_iter: Iterable[SchedulePoint], target: TextIO ) -> None:
    """
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
    """
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


Declination_Func = Callable[[navigation.LatLon, Optional[datetime.date]], float]

def plan( route_path: Path, speed: float = 5.0, date: Optional[datetime.date] = None, variance: Optional[Declination_Func] = None ) -> None:
    """
    Transforms a simple route into a route with a detailed schedule.

    :param route_filename: Source route, extracted into CSV format.
    :param speed: Assumed speed; default is 5.0kn.
    :param date: Assumed date for magnetic declination; default is today.
    :param variance: Declination function to use.  Default is :py:func:`navigation.declination`
    """
    if variance is None: variance= navigation.declination

    def schedule(source: TextIO, variance: Declination_Func, date: Optional[datetime.date], speed: float) -> Iterator[SchedulePoint]:
        sched= gen_schedule(
            gen_mag_bearing(
                gen_rhumb( route ), variance, date), speed )
        return sched

    ext = route_path.suffix.lower()
    schedule_path = route_path.parent / (route_path.stem + " Schedule" + ".csv")

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
            raise ValueError( "Can't process {0}".format(route_path) )


def main(argv: list[str]) -> None:
    """
    Parses command-line arguments to get the routes file names, and the default speed
    to use.

    Then use :py:func:`plan` to process each file, creating a :file:`{name} Schedule.csv`
    output file with the detailed schedule.
    """
    parser= argparse.ArgumentParser()
    parser.add_argument( '-s', '--speed', action='store', type=float, default=5.0 )
    parser.add_argument( 'routes', nargs='*', type=Path )
    args = parser.parse_args(argv)

    for file in args.routes:
        plan( file, speed=args.speed )


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])


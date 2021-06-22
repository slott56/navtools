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
from the initial :py:class:`Waypoint` objects.
"""

from navtools import navigation

import argparse
import csv
from dataclasses import dataclass, field
import datetime
from math import degrees, radians
from pathlib import Path
from typing import TextIO, Iterator, Iterable, Callable, Optional, NamedTuple, Union
import sys
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
from navtools import olc
from navtools.navigation import Waypoint


def csv_to_Waypoint(source: TextIO) -> Iterator[Waypoint]:
    """
    Parses the CSV files produced by tools like GPSNavX, iNavX, OpenCPN
    to yield an iterable sequence of :py:class:`Waypoint` objects.

    Generate Waypoint from a CSV reader.  The assumed column
    order is "name", "lat", "lon" followed by any additional attributes.

    Note that the GPSNavX output was encoded in ``Western (Mac OS Roman)``.
    This can make CSV parsing a bit more complex because there will be
    Unicode characters that the CSV module doesn't always handle gracefully.
    However, the patterns used for parsing tolerate the extraneous bytes
    that appear in the midst of degree-minute values.

    :param source: Open file or file-like object that can be read
    :returns: iterable sequence of :py:class:`Waypoint` instances.
    """
    rte = csv.reader(source)
    for name, lat, lon, desc in rte:
        yield Waypoint(
            name=name,
            lat=navigation.Lat.fromstring(lat),
            lon=navigation.Lon.fromstring(lon),
            description=desc,
        )


def gpx_to_Waypoint(source: TextIO) -> Iterator[Waypoint]:
    """
    Generates :py:class:`Waypoint` onjects from a GPX doc.

    We assume a minimal schema:

    -   ``<rte>`` contains

        -   ``<rtept lat="" lon="">`` contains

            -   ``<name>``

            -   ``<description>``

    :param source: an open XML file.
    :returns: An iterator over :py:class:`Waypoint` objects.
    """
    gpx_ns = "http://www.topografix.com/GPX/1/1"
    path = "/".join(n.text for n in (QName(gpx_ns, "rte"), QName(gpx_ns, "rtept")))
    name_tag = QName(gpx_ns, "name")
    desc_tag = QName(gpx_ns, "description")
    doc = xml.etree.ElementTree.parse(source)
    for pt in doc.findall(path):
        lat_text, lon_text = pt.get("lat"), pt.get("lon")
        if not lat_text or not lon_text:
            raise ValueError(
                f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}"
            )
        lat = navigation.Lat.fromstring(lat_text)
        lon = navigation.Lon.fromstring(lon_text)
        yield Waypoint(
            name=pt.findtext(name_tag.text) or "",
            lat=lat,
            lon=lon,
            description=pt.findtext(desc_tag.text) or "",
        )


class Waypoint_Rhumb(NamedTuple):
    """
    A waypoint along a planned route; includes
    distance and true bearing from the previous waypoint.
    """

    point: Waypoint
    distance: float
    bearing: Optional[navigation.Angle]


def gen_rhumb(route_points_iter: Iterator[Waypoint]) -> Iterator[Waypoint_Rhumb]:
    """
    Calculates the range and bearing to each maypoint from a previous waypoint.

    This uses :py:mod:`navigation` to compute range and bearing between points.

    An assumed mark prior to the first waypoint in the route is required.
    This can either be
    -   the current lat/lon, OR,
    -   a repeat of the first waypoint, leading to an irrelevant bearing and zero distance.

    :param route_points_iter: Iterator over individual :py:class:`Waypoint` instances.
        For example, the results of the :py:func:`csv_to_RoutePoint` or :py:func:`gpx_to_RoutePoint`
        function.

    :returns: iterator over :py:class:`Waypoint_Rhumb` instances.
    """
    start = next(route_points_iter)
    yield Waypoint_Rhumb(start, distance=0, bearing=None)
    for here in route_points_iter:
        r, theta = navigation.range_bearing(start.point, here.point)
        yield Waypoint_Rhumb(here, distance=r, bearing=theta)
        start = here


class Waypoint_Rhumb_Magnetic(NamedTuple):
    """
    A waypoint along a planned route; includes
    distance and bearing from the previous waypoint.
    Includes both true and magnetic bearings with current local variance.

    This keeps the magnetic bearing as a value computed once only.

    An alternative design is to make ``magnetic`` a property
    and compute it as needed. This would allow us to refactor
    the variance and magnetic computations into the :py:class:``Waypoint_Rhumb`` class,
    eliminating a need for this separate class and computation.
    """

    point: Waypoint_Rhumb
    distance: float
    true_bearing: Optional[navigation.Angle]
    magnetic: Optional[navigation.Angle]


def gen_mag_bearing(
    rhumb_iter: Iterable[Waypoint_Rhumb],
    declination: Callable[[navigation.LatLon, Optional[datetime.date]], float],
    date: Optional[datetime.date] = None,
) -> Iterator[Waypoint_Rhumb_Magnetic]:
    """
    Applies the given ``declination`` function to each point to
    compute the compass bearing value from the true bearing at each waypoint in a route.

    ..  important::

        Declination is also known as Variation

    :param rhumb_iter: iterator over :py:class:`Waypoint_Rhumb` instances.
        For example, the :py:func:`gen_rhumb` function.
    :param declination: function to compute declination.
        We often use :py:func:`navigation.declination` for this.
    :param date: Optional :py:class:`datetime.datetime` for which to compute
        the declination. If omitted, today's date is used.
    :returns: Iterator over :py:class:`Waypoint_Rhumb_Magnetic` objects.

    """
    for rp_rhumb in rhumb_iter:
        if rp_rhumb.bearing is None:
            yield Waypoint_Rhumb_Magnetic(
                rp_rhumb,
                distance=rp_rhumb.distance,
                true_bearing=rp_rhumb.bearing,
                magnetic=None,
            )
        else:
            magnetic = rp_rhumb.bearing + declination(rp_rhumb.point.point, date)
            yield Waypoint_Rhumb_Magnetic(
                rp_rhumb,
                distance=rp_rhumb.distance,
                true_bearing=rp_rhumb.bearing,
                magnetic=magnetic,
            )


class SchedulePoint(NamedTuple):
    """Scheduled waypoints.
    These include distance, bearing, and estimated time enroute (ETE)
    """

    point: Waypoint_Rhumb
    distance: float
    true_bearing: Optional[navigation.Angle]
    magnetic: Optional[navigation.Angle]
    cumulative_distance: float
    enroute_min: Optional[float]
    enroute_hm: Optional[str]


def gen_schedule(
    rhumb_mag_iter: Iterable[Waypoint_Rhumb_Magnetic], speed: float = 5.0
) -> Iterator[SchedulePoint]:
    """
    Calculates the elapsed
    distance and elapsed time (in two formats) for each waypoint.
    This is (technically) the time to the **next** waypoint.

    An input bearing of :samp:`None` in a :py:class:`Waypoint_Rhumb_Magnetic` object
    indicates the first waypoint which is the starting position.

    :param rhumb_mag_iter:  Iterator over :py:class:`Waypoint_Rhumb_Magnetic` objects.
    :param speed: Default speed assumption to use; default is 5.0 knots.
    :returns: iterator over :py:class:`SchedulePoint` instances.

    """
    cumulative_distance = 0.0
    for rp in rhumb_mag_iter:
        if rp.true_bearing is None:
            yield SchedulePoint(
                rp.point,
                distance=rp.distance,
                true_bearing=rp.true_bearing,
                magnetic=rp.magnetic,
                cumulative_distance=0.0,
                enroute_min=0,
                enroute_hm="0h 0m",
            )
        else:
            cumulative_distance += rp.distance or 0
            enroute_min = 60.0 * rp.distance / speed
            h, m = divmod(int(enroute_min), 60)
            enroute_hm = "{0:02d}h {1:02d}m".format(h, m)
            yield SchedulePoint(
                point=rp.point,
                distance=rp.distance,
                true_bearing=rp.true_bearing,
                magnetic=rp.magnetic,
                cumulative_distance=cumulative_distance,
                enroute_min=enroute_min,
                enroute_hm=enroute_hm,
            )


def nround(value: Optional[float], digits: int) -> Optional[float]:
    """
    Returns a rounded value, properly honoring ``None`` objects.

    :param value: Float value (or None)
    :param digits: number of digits
    :returns: rounded float value (or None)
    """
    return None if value is None else round(value, digits)


def write_csv(sched_iter: Iterable[SchedulePoint], target: TextIO) -> None:
    """
    Writes a sequence of :py:class:`Schedule` objects to a given target file.

    The file will have the following columns:

        "Name", "Lat", "Lon", "Desc",
        "Distance (nm)", "True Bearing", "Magnetic Bearing",
        "Distance Run", "Elapsed HH:MM"

    Note that we apply some rounding rules to these values before writing them
    to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
    an inch, or 2 cm: more accurate than the GPS position.
    The bearing is rounded to zero places.

    :param sched_iter:  iterator over :py:class:`SchedulePoint` instances.
        For example, the output from the :py:func:`gen_schedule` function.
    :param target: Open file (or file-like object) to which csv data will be
        written.

    """
    rte_rhumb = csv.writer(target)
    rte_rhumb.writerow(
        [
            "Name",
            "Lat",
            "Lon",
            "Desc",
            "Distance (nm)",
            "True Bearing",
            "Magnetic Bearing",
            "Distance Run",
            "Elapsed HH:MM",
        ]
    )
    for sched in sched_iter:
        lat, lon = sched.point.point.point.dm
        rte_rhumb.writerow(
            [
                sched.point.point.name,
                lat,
                lon,
                sched.point.point.description,
                nround(sched.distance, 5),
                (
                    None
                    if sched.true_bearing is None
                    else nround(sched.true_bearing.deg, 0)
                ),
                (None if sched.magnetic is None else nround(sched.magnetic.deg, 0)),
                nround(sched.cumulative_distance, 5),
                sched.enroute_hm,
            ]
        )


Declination_Func = Callable[[navigation.LatLon, Optional[datetime.date]], float]


def plan(
    route_path: Path,
    speed: float = 5.0,
    date: Optional[datetime.date] = None,
    variance: Optional[Declination_Func] = None,
) -> None:
    """
    Transforms a simple route into a route with a detailed schedule.

    This doesn't compute ETA's. It computes ETE's for each leg, and
    an assumed start time can be plugged in to create ETA's.

    The date is used to compute variance, but not to compute ETA's.

    A more sophisticated planner would allow for two kinds of plans.

    -   A "forward" plan uses a departure time to compute a sequence of ETA's.

    -   A "reverse" plan would use a desired arrival time and work backwords to
        compute departures.

    :param route_filename: Source route, extracted into CSV format.
    :param speed: Assumed speed; default is 5.0kn.
    :param date: Assumed date for magnetic declination; default is today.
    :param variance: Declination function to use.  Default is :py:func:`navigation.declination`
    """
    if variance is None:
        variance = navigation.declination

    def schedule(
        source: TextIO,
        variance: Declination_Func,
        date: Optional[datetime.date],
        speed: float,
    ) -> Iterator[SchedulePoint]:
        sched = gen_schedule(gen_mag_bearing(gen_rhumb(route), variance, date), speed)
        return sched

    ext = route_path.suffix.lower()
    schedule_path = route_path.parent / (route_path.stem + " Schedule" + ".csv")

    with schedule_path.open("w", newline="") as target:
        if ext == ".csv":
            with route_path.open() as source:
                route = csv_to_Waypoint(source)
                sched = schedule(source, variance, date, speed)
                write_csv(sched, target)
        elif ext == ".gpx":
            with route_path.open() as source:
                route = gpx_to_Waypoint(source)
                sched = schedule(source, variance, date, speed)
                write_csv(sched, target)
        else:
            raise ValueError("Can't process {0}".format(route_path))


def main(argv: list[str]) -> None:
    """
    Parses command-line arguments to get the routes file names, and the default speed
    to use.

    Then use :py:func:`plan` to process each file, creating a :file:`{name} Schedule.csv`
    output file with the detailed schedule.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--speed", action="store", type=float, default=5.0)
    parser.add_argument("routes", nargs="*", type=Path)
    args = parser.parse_args(argv)

    for file in args.routes:
        plan(file, speed=args.speed)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

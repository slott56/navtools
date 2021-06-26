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
    Parses the CSV files produced by tools like GPSNavX or iNavX
    to yield an iterable sequence of :py:class:`Waypoint` objects.
    These files had no heading row.
    The assumed column order is "name", "lat", "lon", "description".

    Note that the old GPSNavX output was encoded in ``Western (Mac OS Roman)``.
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

    In some cases, there are additional attributes available, but we
    don't seem to need them for planning.

    :param source: an open GPX file.
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


@dataclass
class SchedulePoint:
    """Scheduled waypoints.
    These include distance, bearing, and estimated time enroute (ETE).

    ..  todo:: Unify with :py:class:`opencpn_table.Leg`.

        - leg: int
        - ETE: Optional["Duration"]
        - ETA: Optional[datetime.datetime]
        - ETA_summary: Optional[str]
        - speed: float
        - tide: Optional[str]
        - distance: Optional[float]
        - bearing: Optional[float]
        - course: Optional[float] = None
    """

    point: Waypoint
    distance: float
    true_bearing: Optional[navigation.Angle]
    magnetic: Optional[navigation.Angle]
    speed: Optional[float]
    enroute_min: Optional[float]
    next_course: Optional[navigation.Angle]
    arrival: Optional[datetime.datetime]


Declination_Func = Callable[[navigation.LatLon, Optional[datetime.date]], float]


def gen_schedule(
    waypoints: Iterable[Waypoint],
    variance: Declination_Func,
    start_datetime: Optional[datetime.datetime] = None,
    speed: float = 5.0,
) -> Iterator[SchedulePoint]:
    """
    Calculates distance, bearing, and time en route for each waypoint.
    This is the forward algorithm starting from start_datetime.

    The algorithm peeks ahead to compute the course to the next waypoint.
    This requires a route with two or more waypoints.

    It works like this:

    -   Set previous = next(iter); here = next(iter)

    -   Yield previous with no ETE or distance, course from previous to here.

    -   For end in iter:

        -   Compute ETE and distance from previous to here

        -   Yield here with ETE and distance from previous to here and course from here to end.

        -   Set previous, here = here, end; with some cleverness, we should be able to reuse distance and bearing.

    -   Compute ETE and distance from previous to here

    -   Yield here with ETE and course from previous to here and no course.

    This requires a wee bit of optimization to prevent duplicate cade.
    We should, specifically, cache the distance and bearing to avoid recomputation.

    :param waypoints:  Iterable collection of :py:class:`Waypoint` objects.
    :param variance: the magnetic variance (a/k/a declination) function;
        generally use :py:func:`navigation.declination`.
    :param start_datetime: the date on which to compute the variance; default is today
    :param speed: Default speed assumption to use; default is 5.0 knots.
    :returns: iterator over :py:class:`SchedulePoint` instances.

    """
    if start_datetime is None:
        start_datetime = datetime.datetime.now()
    waypoints_iter = iter(waypoints)
    previous, here = next(waypoints_iter), next(waypoints_iter)
    _, next_course = navigation.range_bearing(previous.point, here.point)
    yield SchedulePoint(
        point=previous,
        distance=0,
        true_bearing=None,
        magnetic=None,
        speed=None,
        enroute_min=0,
        next_course=navigation.Angle(
            next_course - variance(here.point, start_datetime)
        ),
        arrival=start_datetime,
    )
    for end in waypoints_iter:
        r, theta = navigation.range_bearing(previous.point, here.point)
        magnetic = theta - variance(here.point, start_datetime)
        enroute_min = 60.0 * r / speed
        start_datetime += datetime.timedelta(seconds=enroute_min * 60)
        _, next_true = navigation.range_bearing(here.point, end.point)
        yield SchedulePoint(
            point=here,
            distance=r,
            true_bearing=theta,
            magnetic=magnetic,
            speed=speed,
            enroute_min=enroute_min,
            next_course=navigation.Angle(
                next_true - variance(end.point, start_datetime)
            ),
            arrival=start_datetime,
        )
        previous, here = here, end
    r, theta = navigation.range_bearing(previous.point, here.point)
    magnetic = theta - variance(here.point, start_datetime)
    enroute_min = 60.0 * r / speed
    print(f"{start_datetime} {enroute_min}")
    start_datetime += datetime.timedelta(seconds=enroute_min * 60)
    print(f"{start_datetime}")
    yield SchedulePoint(
        point=here,
        distance=r,
        true_bearing=theta,
        magnetic=magnetic,
        speed=speed,
        enroute_min=enroute_min,
        next_course=None,
        arrival=start_datetime,
    )


def nround(value: Optional[float], digits: int) -> Optional[float]:
    """
    Returns a rounded value, properly honoring ``None`` objects.

    :param value: Float value (or None)
    :param digits: number of digits
    :returns: rounded float value (or None)
    """
    return None if value is None else round(value, digits)


def write_csv(target: TextIO, sched_iter: Iterable[SchedulePoint]) -> None:
    """
    Writes a sequence of :py:class:`Schedule` objects to a given target file.

    The file has the following columns::

        "Name", "Lat", "Lon", "Desc",
        "Distance (nm)", "True Bearing", "Magnetic Bearing",
        "Distance Run", "Elapsed HH:MM"

    It makes sense to unify the output with OpenCPN's plan.
    This leads to the following columns::

        "Leg" -- sequence number of legs.
        "To waypoint" -- Waypoint name from the GPX source
        "Distance" -- Equirectangular distance to the waypoint.
        "True Bearing" -- True-North Bearting
        "Bearing" -- Magnetic bearing (with decliation.)
        "Latitude" -- Waypoint latitude from the GPX source
        "Longitude" -- Waypoint longitude from the GPX source
        "ETE" -- Estimated Time Enroute in "d h m" duration format.
        "ETA" -- Estimated time of arrival as "date hh:mm (summary)"
        "Speed" -- Given speed for this leg (usually it's all one assumed speed.)
        "Next tide event" -- usually empty
        "Description" -- Waypoint description from the GPX source
        "Course" -- Course to steer to the next waypoint

    Note that we apply some rounding rules to some values before writing them
    to a CSV file. The distances are rounded to :math:`10^{-1}` which is about 607'.
    The bearing is rounded to zero places.

    :param target: Open file (or file-like object) to which csv data will be
        written.
    :param sched_iter:  iterator over :py:class:`SchedulePoint` instances.
        For example, the output from the :py:func:`gen_schedule` function.

    """
    headings = [
        "Leg",
        "Name",
        "Lat",
        "Lon",
        "Desc",
        "Distance (nm)",
        "True Bearing",
        "Magnetic Bearing",
        "Distance Run",
        "Elapsed HH:MM",
        "ETA",
        "Course",
    ]
    rte_rhumb = csv.DictWriter(target, headings)
    rte_rhumb.writeheader()
    cumulative_distance = 0.0
    for leg, sched in enumerate(sched_iter):
        lat, lon = sched.point.point.dm
        cumulative_distance += sched.distance or 0
        h, m = divmod(round(sched.enroute_min), 60) if sched.enroute_min else (0, 0)
        enroute_hm = f"{h:02d}h {m:02d}m"
        rte_rhumb.writerow(
            {
                "Leg": leg,
                "Name": sched.point.name,
                "Lat": lat,
                "Lon": lon,
                "Desc": sched.point.description,
                "Distance (nm)": nround(sched.distance, 1),
                "True Bearing": (
                    None
                    if sched.true_bearing is None
                    else nround(sched.true_bearing.deg, 0)
                ),
                "Magnetic Bearing": (
                    None if sched.magnetic is None else nround(sched.magnetic.deg, 0)
                ),
                "Distance Run": nround(cumulative_distance, 1),
                "Elapsed HH:MM": enroute_hm,
                "Course": (
                    None
                    if sched.next_course is None
                    else nround(sched.next_course.deg, 0)
                ),
                "ETA": f"{sched.arrival:%b %d %H:%M}",
            }
        )


def plan(
    route_path: Path,
    speed: float = 5.0,
    departure: Optional[datetime.datetime] = None,
    variance: Optional[Declination_Func] = None,
) -> None:
    """
    Transforms a simple route into a route with a detailed schedule.

    This doesn't compute ETA's. It computes ETE's for each leg, and
    an assumed start time can be plugged in to create ETA's.

    The date is used to compute variance, but not to compute ETA's.

    :param route_filename: Source route, extracted into CSV format.
    :param speed: Assumed speed; default is 5.0kn.
    :param date: Assumed date for magnetic declination; default is today.
    :param variance: Declination function to use.  Default is :py:func:`navigation.declination`
    """

    def planning_steps(
        route: Iterable[Waypoint],
        target: TextIO,
        speed: float,
        departure: datetime.datetime,
        variance: Declination_Func,
    ) -> None:
        """
        Given a source of waypoints, and a target Path,
        generate a schedule and write the CSV output.
        """
        sched = gen_schedule(route, variance, departure, speed)
        write_csv(target, sched)

    if variance is None:
        variance = navigation.declination
    if departure is None:
        departure = datetime.datetime.now()

    ext = route_path.suffix.lower()
    schedule_path = route_path.parent / (route_path.stem + " Schedule" + ".csv")

    with schedule_path.open("w", newline="") as target:
        if ext == ".csv":
            with route_path.open() as source, schedule_path.open(
                "w", newline=""
            ) as target:
                planning_steps(
                    csv_to_Waypoint(source), target, speed, departure, variance
                )
        elif ext == ".gpx":
            with route_path.open() as source, schedule_path.open(
                "w", newline=""
            ) as target:
                planning_steps(
                    gpx_to_Waypoint(source), target, speed, departure, variance
                )
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--departure", action="store", default=None)
    group.add_argument("-a", "--arrival", action="store", default=None)
    parser.add_argument("routes", nargs="*", type=Path)
    args = parser.parse_args(argv)
    # TODO: Parse departure or arrival date to support ETA computations.
    # Use parse_date from analysis.
    if args.departure:
        departure = datetime.datetime.strptime(args.departure, "%Y-%m-%dT%H:%M")
    elif args.arrival:
        arrival = datetime.datetime.strptime(
            args.arrival, "%Y-%m-%dT:%H:%M"
        )  # pragma: no cover
    elif not args.arrival and not args.departure:
        # Default is departure from now
        departure = datetime.datetime.now()
    else:
        parser.error("Cannot have both arrival and departure")  # pragma: no cover
        # Actually... maybe we can.
        # Given departure and arrival deduce a speed that would make both work.

    for file in args.routes:
        plan(file, speed=args.speed, departure=departure)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

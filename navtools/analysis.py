"""
Track Analysis Application

The :py:mod:`analysis` application is used to do voyage analysis
of a track.
This can make a more useful log from manually prepared log data or
tracks dumped from tools like GPSNavX, iNavX, and OpenCPN.
It's helpful to add the distance run between waypoints as well as the
elapsed time between waypoints.

This additional waypoint-to-waypoint time and distance allows
for fine-grained analysis of sailing performance.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
import datetime
from math import degrees, radians
import os
from pathlib import Path
from typing import Any, Optional, TextIO, Iterator, Iterable, Union, NamedTuple, cast
import sys
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
from navtools import navigation
from navtools import olc


class DateParser:
    """
    Parses input dates in a variety of formats.

    For more complex situations (i.e., multi-day voyages with partial
    date-time stamps in the log) this function isn't quite appropriate.
    This assumes a single date field is sufficient to fill in all attributes of a date.
    In some cases, we might have timestamps that roll past midnight without an obvious
    indicator of date change. Or, we might have some notation like "d1, d2" or "+1d, +2d".

    ..  todo:: Refactor to merge with :py:func:`opencpn_table.parse_datetime`

    """

    default_date_formats = [
        "%H%M",
        "%H:%M",
        "%I:%M %p",
    ]

    default_year_formats = [
        "%m/%d %H%M",
        "%m/%d %H:%M",
        "%m/%d %I:%M %p",
        "%b %d %H%M",
        "%b %d %H:%M",
        "%b %d %I:%M %p",
        "%d %b %H%M",
        "%d %b %H:%M",
        "%d %b %I:%M %p",
        "%b-%d %H%M",
        "%b-%d %H:%M",
        "%b-%d %I:%M %p",
        "%d-%b %H%M",
        "%d-%b %H:%M",
        "%d-%b %I:%M %p",
        "%B %d %H%M",
        "%B %d %H:%M",
        "%B %d %I:%M %p",
    ]

    full_formats = [
        "%m/%d/%Y %H%M",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %H%M",
        "%m/%d/%y %H:%M",
        "%m/%d/%y %I:%M %p",
        "%Y-%m-%d %H%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%y-%m-%d %H%M",
        "%y-%m-%d %H:%M",
        "%y-%m-%d %I:%M %p",
        "%m-%d-%Y %H%M",
        "%m-%d-%Y %H:%M",
        "%m-%d-%Y %I:%M %p",
        "%m-%d-%y %H%M",
        "%m-%d-%y %H:%M",
        "%m-%d-%y %I:%M %p",
    ]

    def parse(
        self, date: str, default: Optional[datetime.date] = None
    ) -> datetime.datetime:
        """
        March through all of the known date formats until we find one that works.

        :param date: string in some known format
        :param default: default date to use when only a time is given.
        :returns: datetime
        """
        if default is None:
            default = datetime.date.today()
        for fmt in self.default_date_formats:
            try:
                dt = datetime.datetime.strptime(date, fmt)
                dt = dt.replace(year=default.year, month=default.month, day=default.day)
                return dt
            except ValueError as e:
                pass
        for fmt in self.default_year_formats:
            try:
                dt = datetime.datetime.strptime(date, fmt)
                dt = dt.replace(year=default.year)
                return dt
            except ValueError as e:
                pass
        for fmt in self.full_formats:
            try:
                dt = datetime.datetime.strptime(date, fmt)
                return dt
            except ValueError as e:
                pass
        raise ValueError(f"Cannot parse {date!r}")


parse_date = DateParser().parse


@dataclass(eq=True)
class LogEntry:
    """
    A point on a track.

    The source_row is the source data. For CSV files, it's untouched.
    For GPX files, it's lightly massaged to flatten out the attributes of the ``<trkpt>`` tag.

    This is similar to a Waypoint in a plan. The differences are minor.
    Log Entries generally lack names; they're not named points, they're just a piece of data
    at a point in time. Consequently, log entries always have a timestamp.
    """

    time: datetime.datetime
    lat: navigation.Lat
    lon: navigation.Lon
    name: Optional[str] = None
    description: Optional[str] = None
    source_row: dict[str, Any] = field(default_factory=dict)
    point: navigation.LatLon = field(init=False, compare=False)
    geocode: str = field(init=False, compare=True)

    def __post_init__(self) -> None:
        self.point = navigation.LatLon(self.lat, self.lon)
        self.geocode = olc.OLC().encode(degrees(self.lat), degrees(self.lon))


GPS_NAVX_HEADER = [
    "date",
    "latitude",
    "longitude",
    "cog",
    "sog",
    "heading",
    "speed",
    "depth",
    "windAngle",
    "windSpeed",
    "comment",
]


def csv_reader(source: TextIO) -> csv.DictReader[str]:
    """
    There are two formats:

    -   Standard (i.e., OpenCPN). These files have no header.
        This function returns the assumed header which must be provided to build a ``DictReader``.

    -   Manual. These files **must** include a heading row for it to be processed.
        This function returns True. A ``DictReader`` can then use the headers that are found.

    A heading row **must** use labels drawn from this domain of known labels:

    ::

        "date", "latitude", "longitude", "cog", "sog", "heading", "speed",
        "depth", "windAngle", "windSpeed", "comment"

    This leads to two, separate, csv readers for

    -   OpenCPN files without headers;  a default header is assumed.
        See ``GPS_NAVX_HEADER``.

    -   Manual files with headers from the defined set of headers.

    :param source: Open File
    :return: DictReader instance with the headers present or a default set of headers
    """
    sample = source.read(512)
    source.seek(0)
    if csv.Sniffer().has_header(sample):
        reader = csv.DictReader(source)
    else:
        reader = csv.DictReader(source, GPS_NAVX_HEADER)
    return reader


def csv_to_LogEntry(
    reader: csv.DictReader[str], date: Optional[datetime.date] = None,
) -> Iterator[LogEntry]:
    """
    Parses a CSV file to yield an iterable sequence
    of :py:class:`LogEntry` objects. Headers must be provided, otherwise GPS_NAVX_HEADERS
    will be assumed.

    The headers issue.

    -   GPS NavX doesn't provide headers. The list ``GPS_NAVX_HEADER`` is used as an external schema.

    -   Other sources may use ['Time', 'Lat', 'Lon', 'COG', 'SOG', 'Rig', 'Engine', 'windAngle', 'windSpeed', ...

    We "canonicalize" this by looking for ``date`` or ``time``, something starting with ``lat``
    and something starting with ``lon``. These are the minimum required to compute distance and duration.

    :param reader: csv.DictReader with proper headers
    :param date: :py:class:`datetime.datetime` object used to fill in default
        values for incomplete dates. By default, it's "now".
    :returns: An iterator over :py:class:`LogEntry` objects.

    ..  todo:: Refactor :func:`csv_to_LogEntry` into a class that can be extended.
    """

    def best_match(field_names: list[str], target: str) -> str:
        """Given a list of field_names, which field starts with the hoped-for target?"""
        for nm in field_names:
            if nm.lower().startswith(target.lower()):
                return nm
        raise TypeError(f"Can't find a field like {target!r} in {field_names!r}")

    header: list[str] = cast(list[str], reader.fieldnames)

    if set(["date", "latitude", "longitude"]) <= set(header):
        date_field = "date"
        lat_field = "latitude"
        lon_field = "longitude"
    else:
        try:
            date_field = best_match(header, "date")
        except TypeError:
            date_field = best_match(header, "time")
        lat_field = best_match(header, "lat")
        lon_field = best_match(header, "lon")

    if date is None:
        date = datetime.date.today()

    for row in reader:
        try:
            lat = navigation.Lat.fromstring(row[lat_field])
            lon = navigation.Lon.fromstring(row[lon_field])
            try:
                # Typical time: 2011-06-04 13:12:32 +0000
                dt = datetime.datetime.strptime(
                    row[date_field], "%Y-%m-%d %H:%M:%S +0000"
                ).replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                dt = parse_date(row[date_field], default=date)
            yield LogEntry(time=dt, lat=lat, lon=lon, source_row=row)
        except ValueError as e:
            print(row)
            print(e)


def gpx_to_LogEntry(source: TextIO) -> Iterator[LogEntry]:
    """
    Generates :py:class:`LogEntry` onjects from a GPX doc.
    These should perhaps be called "TrackPoints" to better match the GPX tags.

    We assume a minimal schema:

    -   ``<trk>`` contains

        -   ``<trkseg>`` contains

            -   ``<trkpt lat="" lon="">`` contains

                -   ``<time>`` ISO format timestamp

                -   Any other tag values and attribute are preserved as the "source row"

    :param source: an open XML file.
    :returns: An iterator over :py:class:`LogEntry` objects.
    """

    def xml_to_tuples(pt: xml.etree.ElementTree.Element) -> Iterator[tuple[str, str]]:
        """
        Walks elements within an XML container tag, transforming all
        ``<tag attr="avalue">text</tag>`` into a Python ``('tag', 'text'), ('attr', 'avalue')``.

        This flattens an XML structure into a dict[str, str], suitable for CSV processing.

        This is **not** recursive. It is intentionally flat, and is used to collect
        simple structures into a Pythonic structure.

        :param pt: an XML structure with a number of children to process.
        :returns: iterable over (tag, text) tuples and (attr, value) tuples.
        """
        for e in pt.iter():
            ns, _, tag = e.tag.partition("}")
            text = e.text.strip() if e.text else ""
            if text:
                yield tag, text
            else:
                for name, value in e.items():
                    yield name, value

    gpx_ns = "http://www.topografix.com/GPX/1/1"
    path = "/".join(
        n.text
        for n in (QName(gpx_ns, "trk"), QName(gpx_ns, "trkseg"), QName(gpx_ns, "trkpt"))
    )
    time_tag = QName(gpx_ns, "time")
    doc = xml.etree.ElementTree.parse(source)
    for pt in doc.findall(path):
        lat_text, lon_text = pt.get("lat"), pt.get("lon")
        if not lat_text or not lon_text:
            raise ValueError(
                f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}"
            )
        lat = navigation.Lat.fromdegrees(float(lat_text))
        lon = navigation.Lon.fromdegrees(float(lon_text))
        # Typical time: 2011-06-04T15:21:03Z
        raw_dt = pt.findtext(time_tag.text)
        if not raw_dt:
            raise ValueError(
                f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}"
            )
        dt = datetime.datetime.strptime(raw_dt, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
        row_dict = dict(xml_to_tuples(pt))
        yield LogEntry(
            time=dt, lat=lat, lon=lon, source_row=row_dict,
        )


class LogEntry_Rhumb(NamedTuple):
    """
    The raw point plus the distance, bearing, and delta-time to the next waypoint.

    As a special case, a final waypoint will have no additional distance, bearing, or delta-time.
    """

    point: LogEntry
    distance: Optional[float]
    bearing: Optional[navigation.Angle]
    delta_time: Optional[datetime.timedelta]


def gen_rhumb(log_entry_iter: Iterator[LogEntry]) -> Iterator[LogEntry_Rhumb]:
    """
    Transforms a sequence of :py:class:`LogEntry` instances into
    :py:class:`LogEntry_Rhumb` instances. The rhumb line distance, bearing, and
    delta-time are added to each entry.

    Each point has range and bearing to the next point.
    The last point as no range and bearing.

    :param log_entry_iter: iterable sequence of :py:class:`LogEntry` instances.
        This can be produced by :py:func:`gpx_to_LogEntry` or :py:func:`csv_to_LogEntry`.
    :return: iterable sequence of  :py:class:`LogEntry_Rhumb` instances.
    """
    p1 = next(log_entry_iter)
    for p2 in log_entry_iter:
        # print( repr(p1), repr(p2) )
        r, theta = navigation.range_bearing(p1.point, p2.point)
        yield LogEntry_Rhumb(p1, r, theta, p2.time - p1.time)
        p1 = p2
    yield LogEntry_Rhumb(p2, None, None, None)


def nround(value: Optional[float], digits: Optional[Any]) -> Union[int, float, None]:
    """Returns a rounded value, properly honoring ``None`` objects."""
    return None if value is None else round(value, digits)


def write_csv(
    target: TextIO,
    log_entry_rhumb_iter: Iterator[LogEntry_Rhumb],
    source_headers: list[str],
) -> None:
    """
    Writes a sequence of :py:class:`LogEntry_Rhumb`
    objects to a given target file.   The objects are usually built by the
    :py:func:`gen_rhumb` function.

    Since the source data has a poorly-defined set of columns,
    we emit just a few additional attributes joined onto the original,
    untouched row.

    :param target: File to which to write the analyzed rows.
    :param log_entry_rhumb_iter:  iterable sequence of  :py:class:`LogEntry_Rhumb` instances.
        This is often the output of :py:func:`gen_rhumb`.
    :param source_headers: Headers from source to which additional details are added.

    Note that we apply some rounding rules to these values before writing them
    to a CSV file. The distances are rounded to :math:`10^{-5}` which is about
    an inch, or 2 cm: more accurate than the GPS position.
    The bearing is rounded to an 0 places.
    """

    def build_row_dict(
        log: LogEntry_Rhumb, td: Optional[float], tt: Optional[datetime.timedelta]
    ) -> dict[str, Any]:
        """Most entries have total distance and total time. The final entry"""
        row = log.point.source_row.copy()
        calc = {
            "calc_distance": nround(log.distance, 5),
            "calc_bearing": None
            if log.bearing is None
            else nround(log.bearing.degrees, 0),
            "calc_time": log.point.time,
            "calc_elapsed": log.delta_time,
            "calc_total_dist": nround(td, 5),
            "calc_total_time": tt,
        }
        row.update(calc)
        return row

    td = 0.0
    tt = datetime.timedelta(0)

    # Extract the existing headings from the "source_row"; and our additional fields
    headings = source_headers
    headings += [
        "calc_distance",
        "calc_bearing",
        "calc_time",
        "calc_elapsed",
        "calc_total_dist",
        "calc_total_time",
    ]
    rte_rhumb = csv.DictWriter(target, headings)
    rte_rhumb.writeheader()

    # For all other points, update the accumulators and emit the data.
    for log in log_entry_rhumb_iter:
        td += log.distance or 0.0
        tt += log.delta_time or datetime.timedelta(0)
        rte_rhumb.writerow(build_row_dict(log, td, tt))


def analyze(log_filepath: Path, date: Optional[datetime.date] = None) -> None:
    """
    Analyze a log file, writing a new log file with additional
    calculated values.

    The :py:func:`gen_rhumb` calculation is applied to each row.

    :param log_filepath: Path of a log file to analyze.
        If the input is :samp:`{some_name}.csv` or :samp:`{some_name}.gpx`
        the output will be :samp:`{some_name} Distance.csv`.

    :param date: Default date to use when incomplete date-time fields
        are present in the input.
    """
    if date is None:
        date = datetime.date.today()

    ext = log_filepath.suffix.lower()
    distance_path = log_filepath.parent / (log_filepath.stem + " Distance" + ".csv")

    # print(distance_path)
    if ext == ".csv":
        with log_filepath.open() as source:
            with distance_path.open("w", newline="") as target:
                reader = csv_reader(source)
                log_iter = csv_to_LogEntry(reader, date)
                track = gen_rhumb(log_iter)
                write_csv(target, track, cast(list[str], reader.fieldnames))
    elif ext == ".gpx":
        with log_filepath.open() as source:
            with distance_path.open("w", newline="") as target:
                log_iter = gpx_to_LogEntry(source)
                track = gen_rhumb(log_iter)
                write_csv(target, track, ["lat", "lon", "time"])
    else:
        raise ValueError("Can't process {0}: unknown extension".format(log_filepath))


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


def main(argv: list[str]) -> None:
    """
    Parse command-line arguments to get the log file names and the default
    date to use for partial date strings.

    Then use :py:func:`analyze` to process each file, creating a :file:`{name} Distance.csv`
    output file with the detailed analysis.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--date", action="store", type=str, default=None)
    parser.add_argument("tracks", nargs="*", type=Path)
    args = parser.parse_args(argv)

    # Parse the assumed date for a time-only log in options.date
    dt: Optional[datetime.date]
    if args.date is not None:
        for f in date_formats:
            try:
                dt = datetime.datetime.strptime(args.date, f).date()
                break
            except ValueError:
                pass
    else:
        dt = None

    # Process the track files.
    for file in args.tracks:
        analyze(file, date=dt)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

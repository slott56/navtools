"""
Voyage Analysis Application

The :py:mod:`analysis` application is used to do voyage analysis.
This can make a more useful log from manually prepared log data or
tracks dumped from tools like GPSNavX, iNavX, and OpenCPN.
It's helpful to add the distance run between waypoints as well as the
elapsed time between waypoints.

This additional waypoint-to-waypoint time and distance allows
for fine-grained analysis of sailing performance.
"""

from __future__ import annotations

import csv
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
import sys
import os
import datetime
import argparse
from pathlib import Path
from typing import Any, Optional, TextIO, Iterator, Iterable, Union, NamedTuple
from navtools import navigation


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


def parse_date( date: str, default: Optional[datetime.date]=None ) -> datetime.datetime:
    """
    March through all of the known date formats until we find one that works.

    For more complex situations (i.e., multi-day voyages with partial
    date-time stamps in the log) this function isn't quite appropriate.
    This assumes a single date field is sufficient to fill in all attributes of a date.
    In some cases, we might have timestamps that roll past midnight without an obvious
    indicator of date change. Or, we might have some notation like "d1, d2" or "+1d, +2d".
    """
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
    raise ValueError(f"Cannot parse {date!r}")

class LogEntry(NamedTuple):
    time: datetime.datetime
    lat: Union[str, navigation.Angle]
    lon: Union[str, navigation.Angle]
    point: navigation.LatLon
    source_row: dict[str, Any]  # The original source row!



def csv_to_LogEntry( source: TextIO, date: Optional[datetime.date]=None ) -> Iterator[LogEntry]:
    """
    Parses a CSV file to yield an iterable sequence
    of :py:class:`LogEntry` objects.

    There are two formats:

    -   Standard (i.e., GPSNavX). These files have no header. We assume a set of headings.

    -   Manual. These files **must** include a heading row for it to be processed.
        The heading row **must** use labels like the following:

        ::

            "date", "latitude", "longitude", "cog", "sog", "heading", "speed",
            "depth", "windAngle", "windSpeed", "comment"

    ..  todo:: Refactor the sniffing out of csv_to_LogEntry.

        There should be two, separate, csv readers for files with headers
        and a separate one for files without headers, where a default header
        is assumed or the analysis main program provides a header.

    :param source: Open file or file-like object that can be read.
    :param date: :py:class:`datetime.datetime` object used to fill in default
        values for incomplete dates. By default, it's "now".
    :returns: An iterator over :py:class:`LogEntry` objects.
    """
    if date is None:
        date= datetime.date.today()
    hdr = csv.Sniffer().has_header(source.read(512))
    source.seek(0)
    if hdr:
        trk= csv.DictReader( source )
        if trk.fieldnames and set(trk.fieldnames) < set( "Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location".split(',')):
            raise TypeError( "Column Headings aren't valid" )  # pragma: no cover
        def extract( row: dict[str, str] ) -> tuple[datetime.datetime, str, str]:
            # Handle local time formats
            dt= parse_date( row['Time'], default=date )
            return dt, row['Lat'], row['Lon']
    else:
        # GPSNavX CSV file columns.
        trk= csv.DictReader( source, fieldnames=[
        "date", "latitude", "longitude", "cog", "sog", "heading", "speed", "depth", "windAngle", "windSpeed", "comment"] )
        def extract( row: dict[str, str] ) -> tuple[datetime.datetime, str, str]:
            lat, lon = row["latitude"], row["longitude"]
            # Typical time: 2011-06-04 13:12:32 +0000
            dt= datetime.datetime.strptime(row['date'],"%Y-%m-%d %H:%M:%S +0000").replace(tzinfo=datetime.timezone.utc)
            return dt, lat, lon
    for row in trk:
        time, lat, lon = extract( row )
        try:
            point= navigation.LatLon( lat, lon )
            yield LogEntry( time, lat, lon, point, row )
        except ValueError as e:
            print(row)
            print(e)


def gpx_to_LogEntry( source: TextIO ) -> Iterator[LogEntry]:
    """Generate LogEntry from an GPX doc.

    We assume a minimal schema:

    -   ``<trk>`` contains

        -   ``<trkseg>`` contains

            -   ``<trkpt lat="" lon="">`` contains

                -   ``<time>`` ISO format timestamp

                -   Any other tag values and attribute are preserved as the "source row"

    :param source: an open XML file.
    :returns: An iterator over :py:class:`LogEntry` objects.
    """
    gpx_ns= "http://www.topografix.com/GPX/1/1"
    path = "/".join( n.text for n in (QName(gpx_ns, "trk"), QName(gpx_ns, "trkseg"), QName(gpx_ns, "trkpt") ) )
    time_tag = QName(gpx_ns, 'time')
    doc = xml.etree.ElementTree.parse( source )
    for pt in doc.findall( path ):
        lat_text, lon_text = pt.get('lat'), pt.get('lon')
        if not lat_text or not lon_text:
            raise ValueError(f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}")
        lat = navigation.Angle.fromdegrees( float(lat_text) )
        lon = navigation.Angle.fromdegrees( float(lon_text) )
        point= navigation.LatLon( lat, lon )
        # Typical time: 2011-06-04T15:21:03Z
        raw_dt= pt.findtext(time_tag.text)
        if not raw_dt:
            raise ValueError(f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}")
        dt= datetime.datetime.strptime(raw_dt,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        row_dict= dict( xml_to_pairs(pt) )
        yield LogEntry( dt,
            lat, lon,
            point,
            row_dict,
            )


def xml_to_pairs(pt: xml.etree.ElementTree.Element) -> Iterator[tuple[str, str]]:
    """
    Transforms a sequence of XML ``<tag>value</tag>`` into a Python ``('tag', 'value')``
    sequence. This can be used to build a dictionary with a ``{'tag': 'value'}``
    structure.

    :param pt: an XML structure with a number of children to process.
    :returns: iterable over (tag, text) tuples.
    """
    for e in pt.iter():
        ns, _, tag = e.tag.partition('}')
        text = e.text.strip() if e.text else ""
        if text:
            yield tag, text
        else:
            for attr in e.items():
                yield attr


class LogEntry_Rhumb(NamedTuple):
    """
    The raw point plus the distance, bearing, and delta-time to the next waypoint.

    As a special case, a final waypoint will have no additional distance, bearing, or delta-time.
    """
    point: LogEntry
    distance: Optional[float]
    bearing: Optional[navigation.Angle]
    delta_time: Optional[datetime.timedelta]


def gen_rhumb( log_entry_iter: Iterator[LogEntry] ) -> Iterator[LogEntry_Rhumb]:
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
    p1= next(log_entry_iter)
    # TODO: At this point, we know the header for the p1.source_row.
    for p2 in log_entry_iter:
        #print( repr(p1), repr(p2) )
        r, theta= navigation.range_bearing( p1.point, p2.point )
        yield LogEntry_Rhumb( p1, r, theta, p2.time-p1.time )
        p1= p2
    yield LogEntry_Rhumb( p2, None, None, None )


def nround(value: Optional[float], digits: Optional[Any]) -> Union[int, float, None]:
    return None if value is None else round(value,digits)


def write_csv( log_entry_rhumb_iter: Iterator[LogEntry_Rhumb], target: TextIO ) -> None:
    """
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

    ..  todo:: Refactor to eliminate (if possible) sniffing the source_row keys to create CSV headers.

        Option 1. Replace with a class. An iterator method to update the source_row
        with LogEntry_Rhumb and accumulated sub-totals. Essentially, ``build_row_dict``.
        A method to write CSV preserving original headers
        and adding new headers based on values computed by the iterator.

        Option 2. The client provides the source_row keys, doing the sniffing for us.
    
    """
    def build_row_dict( log: LogEntry_Rhumb, td: Optional[float], tt: Optional[datetime.timedelta]) -> dict[str, Any]:
        """Most entries have total distance and total time. The final entry"""
        row = {
            'calc_distance' : nround(log.distance, 5),
            'calc_bearing' : None if log.bearing is None else nround(log.bearing.degrees, 0),
            'calc_time' : log.point.time,
            'calc_elapsed' : log.delta_time,
            'calc_total_dist' : nround(td, 5),
            'calc_total_time' : tt,
        }
        row.update(log.point.source_row)
        return row

    td = 0.0
    tt = datetime.timedelta(0)

    try:
        # Get the first LogEntry_Rhumb to get the original headings.
        first= next( log_entry_rhumb_iter )
    except StopIteration:
        return # No data.

    # Extract the existing headings from the "source_row"; and our additional fields
    headings= list(first.point.source_row.keys())
    headings += [ 'calc_distance', 'calc_bearing', 'calc_time', 'calc_elapsed', 'calc_total_dist', 'calc_total_time' ]
    rte_rhumb= csv.DictWriter( target, headings )
    rte_rhumb.writeheader()

    # Emit the first point with information on the leg to the next point.
    # Ugh on this repetition.
    td += first.distance or 0.0
    tt += first.delta_time or datetime.timedelta(0)
    rte_rhumb.writerow( build_row_dict(first, td, tt) )

    # For all other points, update the accumulators and emit the data.
    for log in log_entry_rhumb_iter:
        td += log.distance or 0.0
        tt += log.delta_time or datetime.timedelta(0)
        rte_rhumb.writerow( build_row_dict(log, td, tt) )


def analyze( log_filepath: Path, date: Optional[datetime.date]=None ) -> None:
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
        date= datetime.date.today()

    ext= log_filepath.suffix.lower()
    distance_path= log_filepath.parent / (log_filepath.stem + " Distance" + ".csv")

    #print( distance_path )
    if ext == '.csv':
        # TODO: Refactor header sniffing here from ``csv_to_LogEntry``.
        with log_filepath.open() as source:
            with distance_path.open('w',newline='') as target:
                # TODO: Emit source_row keys, also.
                track= gen_rhumb( csv_to_LogEntry( source, date ) )
                write_csv( track, target )
    elif ext == '.gpx':
        with log_filepath.open() as source:
            with distance_path.open('w',newline='') as target:
                # TODO: Emit source_row keys, also.
                track= gen_rhumb( gpx_to_LogEntry( source ) )
                write_csv( track, target )
    else:
        raise ValueError( "Can't process {0}: unknown extension".format(log_filepath) )

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
    parser= argparse.ArgumentParser()
    parser.add_argument( '-d', '--date', action='store', type=str, default=None )
    parser.add_argument( 'tracks', nargs='*', type=Path )
    args = parser.parse_args(argv)

    # Parse the assumed date for a time-only log in options.date
    dt: Optional[datetime.date]
    if args.date is not None:
        for f in date_formats:
            try:
                dt = datetime.datetime.strptime( args.date, f ).date()
                break
            except ValueError:
                pass
    else:
        dt = None

    # Process the track files.
    for file in args.tracks:
        analyze( file, date=dt )

if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])


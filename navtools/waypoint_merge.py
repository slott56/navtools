"""
Merges waypoints created by OpenCPN or B&G Zeus2 Chartplotter.

Reads source files to gather waypoints in a unified internal model.

-   OpenCPN GPX  waypoints and routes dump

-   B&G Chartplotter ("Lowrance") GPX WaypointsRoutesTracks

-   Lowrance USR WaypointsRoutesTracks

Compare the internal model documents to locate the waypoints which are unchanged.

What's left are either new, deleted, or changed.

We can emit GPX waypoints to add and change. The deletes must be done manually.

We can emit GPX routes to add and chnage. Algain, deletes must be done manually.

To compare proximate waypoints, we translate Lat/Lon to OLC (Open Location Code.)
OLC comparisons provide a very handy proximity test.

Code length	Precision in degrees	Precision
2	20	2226 km
4	1	111.321 km
6	1/20	5566 meters
8	1/400	278 meters
10	1/8000	13.9 meters

Further geocode details narrow
the space to spaces 2.8 x 3.5 meters or smaller.
"""
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import datetime
from math import isclose, degrees
from pathlib import Path
import re
import sys
from typing import (
    TextIO,
    BinaryIO,
    Iterator,
    Optional,
    Any,
    NamedTuple,
    Callable,
    Iterable,
)
import uuid
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
from jinja2 import Environment, PackageLoader, select_autoescape
from navtools import navigation
from navtools import analysis
from navtools import lowrance_usr
from navtools import olc


@dataclass(eq=True)
class WayPoint:
    lat: navigation.Lat
    lon: navigation.Lon
    time: Optional[datetime.datetime] = None
    name: Optional[str] = None
    description: Optional[str] = None
    sym: Optional[str] = None
    type: Optional[str] = None
    extensions: dict[str, str] = field(default_factory=dict)
    point: navigation.LatLon = field(init=False, compare=False)
    geocode: str = field(init=False, compare=True)

    def __post_init__(self) -> None:
        self.point = navigation.LatLon(self.lat, self.lon)
        self.geocode = olc.OLC().encode(degrees(self.lat), degrees(self.lon))


def parse_datetime(text: Optional[str]) -> Optional[datetime.datetime]:
    """
    There are two formats observed:

    - ``2020-09-30T07:52:39Z``

    - ``2013-11-08T13:53:42-05:00``

    :param text: source text
    :return: datetime.datetime
    """
    if text is None:
        return None

    try:
        dt = datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        pass
    try:
        dt = datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S%z")
        return dt
    except ValueError:
        pass
    raise ValueError(f"Can't parse {text!r}")


def opencpn_GPX_to_WayPoint(source: TextIO) -> Iterator[WayPoint]:
    """
    Generates :py:class:`WayPoint` onjects from an OpenCPN GPX doc.

    ::

          <wpt lat="37.184990000" lon="-76.422203000">
            <time>2020-09-30T07:52:39Z</time>
            <name>Chisman Creek</name>
            <sym>anchor</sym>
            <type>WPT</type>
            <extensions>
              <opencpn:guid>34de7898-f37e-458c-8ccb-e4e03fa325ec</opencpn:guid>
              <opencpn:viz_name>1</opencpn:viz_name>
              <opencpn:arrival_radius>0.050</opencpn:arrival_radius>
              <opencpn:waypoint_range_rings visible="false" number="-1" step="-1" units="-1" colour="#FFFFFF" />
              <opencpn:scale_min_max UseScale="false" ScaleMin="2147483646" ScaleMax="0" />
            </extensions>

    This uses a BUNCH of namespaces

    -   xmlns="http://www.topografix.com/GPX/1/1"
    -   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    -   xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3"
    -   xmlns:opencpn="http://www.opencpn.org"

    :param source: an open XML file.
    :returns: An iterator over :py:class:`LogEntry` objects.
    """
    namespaces = [
        ("", "http://www.topografix.com/GPX/1/1"),  # the default namespace
        ("gpxx", "http://www.garmin.com/xmlschemas/GpxExtensions/v3"),
        ("opencpn", "http://www.opencpn.org"),
    ]

    def xml_to_tuples(pt: xml.etree.ElementTree.Element) -> Iterator[tuple[str, str]]:
        """
        Expand a tag into a list[tuple[str, Any]].

        This assumes one of two types of subtags.

        -   ``<ns:tag>value</tag>`` becomes a ``("ns:tag", "value")`` pair.

        -   ``<ns:tag attr=value/>`` becomes a ``("ns:tag.attr", "value")`` pair.

        This is **not** recursive. It is intentionally flat, and is used to collect
        simple structures into a Pythonic structure.
        """
        ns_name = {full: abbrev for abbrev, full in namespaces}
        for e in pt.iter():
            if match := re.match(r"\{(?P<ns>[^}]+)\}(?P<tag>.+)", e.tag):
                ns, tag = match.group("ns"), match.group("tag")
            else:
                print(f"Unqualified tag {e.tag!r}")  # pragma: no cover
            text = e.text.strip() if e.text else ""
            if text:
                yield f"{ns_name[ns]}:{tag}", text
            for name, value in e.items():
                yield f"{ns_name[ns]}:{tag}.{name}", value

    gpx_ns = "http://www.topografix.com/GPX/1/1"
    path = "/".join(n.text for n in (QName(gpx_ns, "wpt"),))
    time_tag = QName(gpx_ns, "time")
    name_tag = QName(gpx_ns, "name")
    sym_tag = QName(gpx_ns, "sym")
    type_tag = QName(gpx_ns, "type")
    extensions_tag = QName(gpx_ns, "extensions")

    doc = xml.etree.ElementTree.parse(source)

    for pt in doc.findall(path):
        lat_text, lon_text = pt.get("lat"), pt.get("lon")
        if not lat_text or not lon_text:
            raise ValueError(  # pragma: no cover
                f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}"
            )
        lat = navigation.Lat.fromdegrees(float(lat_text))
        lon = navigation.Lon.fromdegrees(float(lon_text))
        # point = navigation.LatLon(lat, lon)
        dt = parse_datetime(pt.findtext(time_tag.text))
        name = pt.findtext(name_tag.text)
        sym = pt.findtext(sym_tag.text)
        type = pt.findtext(type_tag.text)
        extensions = pt.find(extensions_tag.text)
        if extensions:
            row_dict = dict(xml_to_tuples(extensions))
        else:
            row_dict = {}
        yield WayPoint(
            lat, lon, dt, name, None, sym, type, row_dict,  # point,
        )


def lowrance_GPX_to_WayPoint(source: TextIO) -> Iterator[WayPoint]:
    """
    Generates :py:class:`WayPoint` onjects from an Chartplotter GPX doc.

    ::

        <metadata>
            <time>2021-06-04T16:55:38Z</time>
            <depthunits>meters</depthunits>
            <tempunits>C</tempunits>
            <sogunits>m/s</sogunits>
        </metadata>
        <wpt lon="-80.22695124" lat="25.71541470" >
            <time>2017-05-28T19:15:52Z</time>
            <name>Coconut Grove</name>
            <sym>anchor</sym>
        </wpt>

    This uses one namespace

    -   xmlns="http://www.topografix.com/GPX/1/1"

    :param source: an open XML file.
    :returns: An iterator over :py:class:`LogEntry` objects.
    """
    gpx_ns = "http://www.topografix.com/GPX/1/1"
    path = "/".join(n.text for n in (QName(gpx_ns, "wpt"),))
    time_tag = QName(gpx_ns, "time")
    name_tag = QName(gpx_ns, "name")
    sym_tag = QName(gpx_ns, "sym")

    doc = xml.etree.ElementTree.parse(source)

    for pt in doc.findall(path):
        lat_text, lon_text = pt.get("lat"), pt.get("lon")
        if not lat_text or not lon_text:
            raise ValueError(  # pragma: no cover
                f"Can't process {xml.etree.ElementTree.tostring(pt, encoding='unicode', method='xml')}"
            )
        lat = navigation.Lat.fromdegrees(float(lat_text))
        lon = navigation.Lon.fromdegrees(float(lon_text))
        # point = navigation.LatLon(lat, lon)
        dt = parse_datetime(pt.findtext(time_tag.text))
        name = pt.findtext(name_tag.text)
        sym = pt.findtext(sym_tag.text)
        row_dict: dict[str, Any] = {}
        yield WayPoint(
            lat, lon, dt, name, None, sym, None, row_dict,  # point,
        )


def lowrance_USR_to_WayPoint(source: BinaryIO) -> Iterator[WayPoint]:
    """
    USR Details

    ::

        {'uuid': UUID('41f0e2b8-e631-462a-82fd-f5292523f98d'),
        'UID_unit_number': 12988,
        'UID_sequence_number': 328,
        'waypt_stream_version': 2,
        'waypt_name_length': 18,
        'waypt_name': 'ALLIGTR C',
        'UID_unit_number_2': 12988,
        'longitude': -76.64669528,
        'latitude': 24.38829583,
        'flags': 4,
        'icon_id': 0,
        'color_id': 0,
        'waypt_description_length': -1,
        'waypt_description': '',
        'alarm_radius': 0.0,
        'waypt_creation_date': datetime.date(2017, 6, 11),
        'waypt_creation_time': datetime.timedelta(seconds=36080, microseconds=754000),
        'unknown_2': -1,
        'depth': 0.0,
        'LORAN_GRI': -1, 'LORAN_Tda': 0, 'LORAN_Tdb': 0}

    :param source:
    :return:
    """
    u = lowrance_usr.Lowrance_USR.load(source)
    for wp in u["waypoints"]:
        lat = navigation.Lat.fromdegrees(wp["latitude"])
        lon = navigation.Lon.fromdegrees(wp["longitude"])
        # point = navigation.LatLon(lat, lon)
        dt = wp["waypt_creation_date"] + wp["waypt_creation_time"]
        name = wp["waypt_name"]
        description = wp["waypt_description"]
        try:
            sym = lowrance_usr.ICON_TABLE_2[wp["icon_id"], wp["color_id"]]
        except KeyError:  # pragma: no cover
            sym = f'{wp["icon_id"]},{wp["color_id"]}'  # pragma: no cover
        row_dict = wp
        yield WayPoint(
            lat, lon, dt, name, description, sym, None, row_dict,  # point,
        )


def waypoint_to_GPX(source: Iterable[WayPoint]) -> str:
    """
    Inject waypoint data into an XML template.

    :param source: source of  WayPoint instances.
    :return: XML document as text.
    """
    env = Environment(loader=PackageLoader("navtools"), autoescape=select_autoescape())
    template = env.get_template("gpx_waypoints.xml")
    return template.render(waypoints=source)


@dataclass
class History:
    """
    The state of the matching operation.
    This allows us to track waypoints that have matches.
    """

    wp: WayPoint
    matched: Optional[WayPoint] = None


class WP_Match(NamedTuple):
    """
    The match result.
    There are three states.

    -   Both -- they passed a comparison test

    -   1 -- From the first source (usually the computer) with no match

    -   2 -- From the second source (usually the chart plotter) with no match
    """

    wp_1: Optional[WayPoint]
    wp_2: Optional[WayPoint]


def match_gen(
    compare: Callable[[WayPoint, WayPoint], bool],
    wp_list_1: list[WayPoint],
    wp_list_2: list[WayPoint],
) -> Iterator[WP_Match]:
    """
    Given a comparison function, generate :py:class:`WP_Match` pairs.

    This does a brute-force :math:`m \\times n` comparison
    of all items in both lists. It applies the :py:func:`comparison`
    function to all elements to locate
    matches.

    The remaining items are in the list 1 or list 2,
    and we use this to generate the the unmatched items.

    :param compare: Comparison function to use.
    :param wp_list_1: master list of waypoints (often the computer)
    :param wp_list_2: other devices list of waypoints (iPad, Chart Plotter, Phone, etc.)
    """
    history_1 = [History(wp) for wp in wp_list_1]
    history_2 = [History(wp) for wp in wp_list_2]
    for pt_1 in history_1:
        for pt_2 in history_2:
            if compare(pt_1.wp, pt_2.wp):
                yield WP_Match(pt_1.wp, pt_2.wp)
                pt_1.matched = pt_2.wp
                pt_2.matched = pt_1.wp
    for pt_1 in (h for h in history_1 if h.matched is None):
        yield WP_Match(pt_1.wp, None)
    for pt_2 in (h for h in history_2 if h.matched is None):
        yield WP_Match(None, pt_2.wp)


def report(matches: Iterable[WP_Match]) -> None:
    """
    Report on a list of :py:class:`WP_Match` instances.
    """
    # Common
    for m in matches:
        if m.wp_1 and m.wp_2:
            if isclose(d := m.wp_1.point.near(m.wp_2.point), 0.0, abs_tol=0.05):
                print(f"  {m.wp_1.name:24s}={m.wp_2.name:24s}")
            else:
                print(
                    f"  {m.wp_1.name:24s}={m.wp_2.name:24s} {m.wp_1.point} {m.wp_2.point} {d:0.2f} NM"
                )
        elif m.wp_1:
            print(f"- {m.wp_1.name:24s}={'':24s} {m.wp_1.point}")
        elif m.wp_2:
            print(f"+ {'':24s}={m.wp_2.name:24s} {'':24s} {m.wp_2.point}")
        else:
            raise RuntimeError("WTF")  # pragma: no cover


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--plotter",
        action="store",
        type=Path,
        default=Path.cwd() / "data" / "WaypointsRoutesTracks.usr",
    )
    parser.add_argument(
        "-c",
        "--computer",
        action="store",
        type=Path,
        default=Path.cwd() / "data" / "2021 opencpn waypoints.gpx",
    )
    parser.add_argument(
        "-b",
        "--by",
        action="store",
        type=str,
        choices=["name", "distance", "geocode", "guid"],
    )
    parser.add_argument(
        "-r",
        "--report",
        action="store",
        type=str,
        choices=["summary", "gpx"],
        default="summary",
    )
    options = parser.parse_args(argv)

    opencpn = options.computer
    with opencpn.open() as opencpn_source:
        opencpn_wp = list(opencpn_GPX_to_WayPoint(opencpn_source))

    plotter = options.plotter
    with plotter.open("rb") as plotter_source:
        plotter_wp = list(lowrance_USR_to_WayPoint(plotter_source))

    if options.by == "name":
        title = "By Name"
        match_rule = lambda pt1, pt2: pt1.name == pt2.name
    elif options.by == "distance":
        title = "By Distance"
        match_rule = lambda pt1, pt2: isclose(
            pt1.point.near(pt2.point), 0.0, abs_tol=0.05
        )
    elif options.by == "geocode":
        title = "By Geocode"
        match_rule = lambda pt1, pt2: pt1.geocode[:8] == pt2.geocode[:8]
    elif options.by == "guid":
        title = "By GUID"
        match_rule = (
            lambda pt1, pt2: pt1.extensions["opencpn:guid"] == pt2.extensions["uuid"]
        )
    else:
        raise ValueError(f"Uknown --by {options.by!r}")  # pragma: no cover

    matches = match_gen(match_rule, opencpn_wp, plotter_wp)

    if options.report == "summary":
        print(f"{title}\nComputer (-) | Chartplotter (+)")
        report(matches)
    elif options.report == "gpx":
        unique_plotter = (
            m.wp_2 for m in matches if m.wp_1 is None and m.wp_2 is not None
        )
        print(waypoint_to_GPX(unique_plotter))
    else:
        raise ValueError(f"Uknown --report {options.report!r}")  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

"""
Merges waypoints created by OpenCPN or B&G Zeus2 Chartplotter.

Reads source files to gather waypoints in a unified internal model.

-   OpenCPN provides a GPX waypoints and routes dump.

-   B&G Chartplotter can provide GPX WaypointsRoutesTracks; this doesn't have complete detail.

-   B&G Chartplotter can provide a Lowrance USR WaypointsRoutesTracks; this has everything.

Compare the internal model documents to locate the waypoints which are unchanged.
These can be ignored.

What's left are either new, deleted, or changed.

-   Emit GPX waypoints to add.

-   We can produce a list of deletes to be done manually.

-   For changes, we have a number of cases.

    -   Same name (or same GUID) with a new location.

    -   New name but matching location.

In principle, we can also emit GPX routes that have changed.
This is more complex because "matching" requires a number of similar waypoints.
Again, deletes must be done manually.

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
    Type,
    DefaultDict,
    Union,
)
import uuid
import xml.etree.ElementTree
from xml.etree.ElementTree import QName
from jinja2 import Environment, PackageLoader, select_autoescape
from navtools import navigation
from navtools.navigation import Waypoint
from navtools import analysis
from navtools import lowrance_usr
from navtools import olc


@dataclass(eq=True, unsafe_hash=True)
class Waypoint_Plot:
    """
    Plotted image of a waypoint.
    """

    waypoint: Waypoint
    last_updated: Optional[datetime.datetime] = None
    sym: Optional[str] = None
    type: Optional[str] = None
    extensions: dict[str, str] = field(default_factory=dict)


class DateParser:
    def parse(self, text: Optional[str]) -> Optional[datetime.datetime]:
        """
        There are two formats observed:

        - ``2020-09-30T07:52:39Z``

        - ``2013-11-08T13:53:42-05:00``

        ..  todo:: Refactor to merge with :py:func:`analysis.parse_date`

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


parse_datetime = DateParser().parse


def opencpn_GPX_to_WayPoint(source: TextIO) -> Iterator[Waypoint_Plot]:
    """
    Generates :py:class:`Waypoint_Plot` onjects from an OpenCPN GPX doc.

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

    -   ``xmlns="http://www.topografix.com/GPX/1/1"``
    -   ``xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"``
    -   ``xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3"``
    -   ``xmlns:opencpn="http://www.opencpn.org"``

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
            row_dict = {}  # pragma: no cover
        yield Waypoint_Plot(
            Waypoint(lat=lat, lon=lon, name=name, description=None,),
            last_updated=dt,
            sym=sym,
            type=type,
            extensions=row_dict,
        )


def lowrance_GPX_to_WayPoint(source: TextIO) -> Iterator[Waypoint_Plot]:
    """
    Generates :py:class:`Waypoint_Plot` onjects from an Chartplotter GPX doc.

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

    -   ``xmlns="http://www.topografix.com/GPX/1/1"``

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
        yield Waypoint_Plot(
            Waypoint(lat=lat, lon=lon, name=name, description=None,),
            last_updated=dt,
            sym=sym,
            type=None,
            extensions=row_dict,
        )


def lowrance_USR_to_WayPoint(source: BinaryIO) -> Iterator[Waypoint_Plot]:
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
        yield Waypoint_Plot(
            Waypoint(lat=lat, lon=lon, name=name, description=description,),
            last_updated=dt,
            sym=sym,
            type=None,
            extensions=row_dict,
        )


def waypoint_to_GPX(source: Iterable[Waypoint_Plot]) -> str:
    """
    Inject waypoint data into an XML template.

    :param source: source of  Waypoint_Plot instances.
    :return: XML document as text.
    """
    env = Environment(loader=PackageLoader("navtools"), autoescape=select_autoescape())
    template = env.get_template("gpx_waypoints.xml")
    return template.render(waypoints=source)


@dataclass(unsafe_hash=True)
class History:
    """
    The state of the matching operation.

    Each History reflects a waypoint and the matches against other
    waypoints from the same source, or waypoints from a different source.
    """

    wp: Waypoint_Plot
    matches: DefaultDict[str, list[Waypoint_Plot]] = field(
        default_factory=lambda: defaultdict(list)
    )

    @property
    def all_matches(self) -> list[Waypoint_Plot]:
        return list(m for r, m_list in self.matches.items() for m in m_list)


class List_Compare:
    """
    Given a comparison function, updates two collections of :py:class:`History` objects,
    to reflect matches between the waypoints.

    This does a brute-force :math:`m \\times n` comparison
    of all items in both lists. It applies the :py:func:`comparison`
    function to all elements to locate
    matches.

    The remaining items are exclusive to list 1 or list 2,
    representing the unmatched items.
    """

    rule_name = "Invalid"

    def __init__(self) -> None:
        self.history_1: list[History]
        self.history_2: list[History]

    def rule(self, wp_1: Waypoint_Plot, wp_2: Waypoint_Plot) -> bool:
        raise NotImplementedError  # pragma: no cover

    def compare(self, wp_1: list[History], wp_2: list[History]) -> None:
        """
        Applies the rule to the History to accumulate all matches.
        """
        self.history_1 = wp_1
        self.history_2 = wp_2
        for pt_1 in self.history_1:
            for pt_2 in self.history_2:
                if pt_1 is pt_2:
                    # Skip comparisons against self.
                    continue
                if pt_1.wp in pt_2.all_matches:
                    # Skip if already matched; don't rematch.
                    pass
                if self.rule(pt_1.wp, pt_2.wp):
                    pt_1.matches[self.rule_name].append(pt_2.wp)
                    pt_2.matches[self.rule_name].append(pt_1.wp)


class CompareByName(List_Compare):
    """Compares names simply.  Levenshtein distance might be helpful."""

    rule_name = "ByName"

    def rule(self, pt1: Waypoint_Plot, pt2: Waypoint_Plot) -> bool:
        return pt1.waypoint.name == pt2.waypoint.name


class CompareByGUID(List_Compare):
    """Compares GUID's. Assumes collection 1 is OpenCPN."""

    rule_name = "ByGUID"

    def rule(self, pt1: Waypoint_Plot, pt2: Waypoint_Plot) -> bool:
        """Assumes pt1 is OpenCPN and pt2 is from the chartplotter."""
        uuid_1_u: Union[uuid.UUID, str] = pt1.extensions["opencpn:guid"]
        uuid_1: uuid.UUID = uuid.UUID(uuid_1_u) if isinstance(
            uuid_1_u, str
        ) else uuid_1_u
        uuid_2_u: Union[uuid.UUID, str, None] = pt2.extensions.get("uuid")
        if uuid_2_u is None:
            # A GPX file from the chartplotter often lacks UUID's.
            return False
        uuid_2: uuid.UUID = uuid.UUID(uuid_2_u) if isinstance(
            uuid_2_u, str
        ) else uuid_2_u
        return uuid_1 == uuid_2


class CompareByDistance(List_Compare):
    """Uses :py:class:`Waypoint` definition of :py:meth:`near`.
    Has a hard-coded distance threshold of ±0.05 nmi.
    """

    rule_name = "ByDist"

    def rule(self, pt1: Waypoint_Plot, pt2: Waypoint_Plot) -> bool:
        return isclose(pt1.waypoint.point.near(pt2.waypoint.point), 0.0, abs_tol=0.05)


class CompareByGeocode(List_Compare):
    """Uses OLC matching to a given number of positions.

    ..  csv-table::

        positions,degrees,distance
        8,1/400,"278 meters, .15 nmi"
        10,1/8000,"13.9 meters, 45 feet"

    default size is 8.

    Usaage::

        c = CompareByGeocode.range(8)()
        c.compare(l1, l2)

    """

    rule_name = "ByCode"
    size = 8

    def rule(self, pt1: Waypoint_Plot, pt2: Waypoint_Plot) -> bool:
        return pt1.waypoint.geocode[: self.size] == pt2.waypoint.geocode[: self.size]

    @classmethod
    def range(cls, size: int) -> Type["CompareByGeocode"]:
        class Geocode(CompareByGeocode):
            pass

        Geocode.size = size
        Geocode.rule_name = f"ByCode{Geocode.size}"
        return Geocode


def duplicates(wp_list: list[Waypoint_Plot]) -> list[Waypoint_Plot]:
    """
    Report on duplicates. Also, returns a reduced list of waypoints with
    duplicates removed.

    Given a collection of duplicates, we use the we use the last_updated
    time to locate the newest copy and keep that.

    :param wp_list: list[Waypoint_Plot], usually from a derived list in a chartplotter
    :returns: list[Waypoint_Plot] with duplicates removed.
    """
    # Locate CP duplicates
    h_2 = [History(w) for w in wp_list]
    CompareByGeocode.range(10)().compare(h_2, h_2)
    unique = list(filter(lambda h: not h.matches, h_2))
    non_unique = list(filter(lambda h: h.matches, h_2))
    print("Chartplotter Duplicates")
    seen_once: list[Waypoint_Plot] = []
    preferred: list[Waypoint_Plot] = []
    for h in non_unique:
        alternatives = [h.wp] + h.all_matches
        alternatives.sort(
            key=lambda wp: wp.last_updated or datetime.datetime(1900, 1, 1)
        )
        keep = alternatives[-1]
        remove = alternatives[:-1]
        if keep not in seen_once:
            print(keep.waypoint)
            for r in remove:
                print(f"  - {r.waypoint}")
            seen_once.extend(alternatives)
            preferred.append(keep)
    return preferred


def survey(wp_1: list[Waypoint_Plot], wp_2: list[Waypoint_Plot]) -> None:
    """
    Report on the comparison of two waypoint lists.
    This is a human-readable DIFF-like report, it uses
    all of the comparison algorithms to locate candidate duplicates.

    :param wp_1: Waypoints, usually from the master list in OpenCPN
    :param wp_2: Waypoints, usually from a derived list in a chartplotter
    """

    # Locate *all* matches; updating the History objects.
    history_1 = [History(w) for w in wp_1]  # or list(map(History, wp_1))
    history_2 = [History(w) for w in wp_2]  # or list(map(History, wp_2))
    the_rules: tuple[Type[List_Compare], ...] = (
        CompareByName,
        CompareByGUID,
        CompareByGeocode.range(8),
    )
    for C in the_rules:
        C().compare(history_1, history_2)

    # Rank by number of matches in the OpenCPN list of waypoints
    history_1.sort(
        key=lambda h: sum(len(m) for r, m in h.matches.items()), reverse=True
    )

    # Summarize the matches found
    print(f"Computer (-) | Chartplotter (+)")
    for h in history_1:
        if bool(h.matches):
            # Common -- two cases. Common and proximate; common and not proximate
            matches = "\n    ".join(
                f"{r}: {[m.waypoint for m in ml]}" for r, ml in h.matches.items()
            )
            print(f"  {h.wp.waypoint}\n    {matches}")
        else:
            # Source 1 (the computer) only. These can be ignored.
            pass  # pragma: no cover
    for h in history_2:
        if bool(h.matches):
            # Already reported
            pass
        else:
            # Source 2 (the chartplotter) only. These must be added.
            print(f"+ {h.wp.waypoint}")


class WP_Match(NamedTuple):
    """
    The final match result.
    There are three states.

    -   Both -- they passed the given comparison test, and appear to be the same

    -   1 only -- From the first source (usually the computer) with no match

    -   2 only -- From the second source (usually the chart plotter) with no match
    """

    wp_1: Optional[Waypoint_Plot]
    wp_2: Optional[Waypoint_Plot]

    @property
    def both(self) -> bool:
        return self.wp_1 is not None and self.wp_2 is not None

    @property
    def first(self) -> bool:
        return self.wp_1 is not None and self.wp_2 is None

    @property
    def second(self) -> bool:
        return self.wp_1 is None and self.wp_2 is not None


def match_gen(history_1: list[History], history_2: list[History]) -> Iterator[WP_Match]:
    """
    Merge two sequences of :py:class:`History` instances into single sequence of :py:class:`WP_Match`
    instances.

    There are three subtypes of matches in the final sequence:

    -   Something was the same.

    -   Only in the first history list (usually the computer) with no match.

    -   Only in the second history list (usually the chart plotter) with no match.
    """
    for pt_1 in (h for h in history_1 if h.matches):
        for rule in pt_1.matches:
            for m in pt_1.matches[rule]:
                yield WP_Match(pt_1.wp, m)
    for pt_1 in (h for h in history_1 if not h.matches):
        yield WP_Match(pt_1.wp, None)
    for pt_2 in (h for h in history_2 if not h.matches):
        yield WP_Match(None, pt_2.wp)


def computer_upload(matches: Iterable[WP_Match]) -> None:
    """
    Report on a list of :py:class:`WP_Match` instances.
    This is a GPX Upload to get the computer up-to-date with what's on the chartplotter.

    This has two clumps of data.

    1.  Common but not proximate: these may need to be updated on the computer to reflect
        changes on the chartplotter. (Or. They may need to be updated on the chartplotter.)

    2.  Chartplotter only: these need to be transferred to the computer.
    """
    raise NotImplementedError  # pragma: no cover


def main(argv: list[str]) -> None:
    """
    Waypoint merge. Parses the command line options.
    Compares two files, and emits a report/summary or GPX.

    ..  todo:: parameterize the distance or geocode options.
    """
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
        action="append",
        type=str,
        choices=["name", "distance", "geocode", "guid"],
        help="matching rule to use",
    )
    parser.add_argument(
        "-r",
        "--report",
        action="store",
        type=str,
        choices=["survey", "gpx.new", "gpx.match"],
        default="survey",
        help="What kind of output? GPX or Display",
    )
    options = parser.parse_args(argv)

    opencpn = options.computer
    with opencpn.open() as opencpn_source:
        opencpn_wp = list(opencpn_GPX_to_WayPoint(opencpn_source))

    plotter = options.plotter
    with plotter.open("rb") as plotter_source:
        plotter_wp = list(lowrance_USR_to_WayPoint(plotter_source))

    if options.report == "survey":
        duplicates(plotter_wp)
        print()
        print("==========")
        print()
        survey(opencpn_wp, plotter_wp)

    elif options.report.startswith("gpx"):

        opencpn_history = [History(wp) for wp in opencpn_wp]
        plotter_history = [History(wp) for wp in plotter_wp]

        rules: list[Type[List_Compare]] = []
        for compare in options.by:
            if compare == "name":
                rules.append(CompareByName)
            elif compare == "distance":
                rules.append(CompareByDistance)
            elif compare == "geocode":
                rules.append(CompareByGeocode.range(8))
            elif compare == "guid":
                rules.append(CompareByGUID)
            else:
                raise ValueError(
                    f"Unknown {compare} in {' --by '.join(options.by)}"
                )  # pragma: no cover
            for C in rules:
                C().compare(opencpn_history, plotter_history)

        # TODO: Separate changed from new.
        matches = match_gen(opencpn_history, plotter_history)

        # computer_upload(matches)

        # Spike Solution...
        unique_plotter = (
            m.wp_2 for m in matches if m.wp_1 is None and m.wp_2 is not None
        )
        print(waypoint_to_GPX(unique_plotter))
    else:
        raise ValueError(f"Unknown --report {options.report!r}")  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

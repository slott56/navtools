"""
Parse the OpenCPN Table format.

Example::

    Herrington to Drum Point
    Name	Herrington to Drum Point
    Depart From
    Destination
    Total distance	 22.9 NMi
    Speed (Kts)	6
    Departure Time (%x %H:%M)	05/25/2021 08:43
    Time enroute	 3H 49M

    Leg	To waypoint	Distance	Bearing	Latitude	Longitude	ETE	ETA	Speed	Next tide event	Description	Course	ETD
    ---	Herring Bay	  2.5 NMi	165 °M	38° 44.2' N	076° 32.4' W	24M 51S	Start: 05/25/2021 08:43 (MoTwilight)	6			72 °M
    1	Kent Point	  9.4 NMi	72 °M	38° 48.7' N	076° 21.9' W	 1H 34M	05/25/2021 11:51 (Daytime)	6			66 °M
    2	Eastern Bay	  7.1 NMi	66 °M	38° 52.9' N	076° 14.5' W	 1H 11M	05/25/2021 13:02 (Daytime)	6			158 °M
    3	Wye R. Entrance	  2.9 NMi	158 °M	38° 50.5' N	076° 12.5' W	28M 31S	05/25/2021 13:31 (Daytime)	6			44 °M
    4	Bordley Pt.	  1.6 NMi	44 °M	38° 51.8' N	076° 11.4' W	16M 13S	05/25/2021 13:47 (Daytime)	6			14 °M
    5	Drum Point	  1.4 NMi	14 °M	38° 53.2' N	076° 11.3' W	13M 43S	05/25/2021 14:01 (Daytime)	6			120 °M
    6	Drum Point Anchorage	  0.5 NMi	120 °M	38° 53.0' N	076° 10.7' W	 4M 52S	05/25/2021 14:06 (Daytime)	6			Arrived

There are three kinds of lines.

1. The title (the first line.)
2. The top ``name\\tvalue`` lines.
3. Details have ``\\t``-separated columns.

This is a pair of logical layouts in a single CSV physical format file.

We have an overall :class:`Route` object, and the detailed :class:`Leg` objects.
These, in turn, have some specialized data types, including :class:`Duration`,
:class:`Latitude` and :class:`Longitude`.
"""
from __future__ import annotations
import abc
import argparse
import csv
from dataclasses import dataclass
import datetime
from pathlib import Path
import re
import sys
from typing import Iterable, NamedTuple, Callable, Any


class Leg:
    """
    Map attribute values between OpenCPN CSV, something Pythonic,
    and a more generic CSV with less fancy formatting.
    """

    def __init__(self, details: dict[str, str]) -> None:
        try:
            self.leg = int(details["Leg"]) if details["Leg"] != "---" else 0
            self.to_waypoint = details["To waypoint"]
            self.distance = float(m.group(1)) if (m:=re.match(r"\s*(\d+\.?\d*)\s\w+", details["Distance"])) is not None else None
            self.bearing = float(m.group(1)) if (m:=re.match(r"\s*(\d+)\s.\w+", details["Bearing"])) is not None else None
            self.lat = Latitude.parse(details["Latitude"])
            self.lon = Longitude.parse(details["Longitude"])
            self.ETE = Duration.parse(details["ETE"])
            eta_time, eta_summary = m.groups() if (m:=re.match(r"(?:Start: )?(.{16})\s\((\w+)\)", details["ETA"])) is not None else ("", "")
            self.ETA = datetime.datetime.strptime(eta_time, "%m/%d/%Y %H:%M") if eta_time else None
            self.ETA_summary = eta_summary
            self.speed = float(details["Speed"])
            self.tide = details["Next tide event"]
            self.description = details["Description"]
            self.course = (float(m.group(1)) if (m:=re.match(r"\s*(\d+)\s.\w+", details["Course"])) is not None else None) if details["Course"] != "Arrived" else None
        except (KeyError, ValueError) as ex:
            print(f"Invalid {details} {ex!r}")
            raise

    attr_names: dict[str, Callable[[Any], str]] = {
        "Leg": lambda l: f"{l.leg}",
        "To waypoint": lambda l: f"{l.to_waypoint}",
        "Distance": lambda l: f"{l.distance}",
        "Bearing": lambda l: f"{l.bearing}",
        "Latitude": lambda l: f"{l.lat}",
        "Longitude": lambda l: f"{l.lon}",
        "ETE": lambda l: f"{l.ETE}",
        "ETA": lambda l: f"{l.ETA} ({l.ETA_summary})",
        "Speed": lambda l: f"{l.speed}",
        "Next tide event": lambda l: f"{l.tide}",
        "Description": lambda l: f"{l.description}",
        "Course": lambda l: f"{l.course}",
    }

    def asdict(self) -> dict[str, str]:
        r = {
            k: str(attr_func(self))
            for k, attr_func in self.attr_names.items()
        }
        return r

class Route:
    """
    The overall Route. A number of pre-computed attributes are available,
    like the estimated duration and distance.
    The values of Speed and Departure are inputs, actually.
    The Name, Depart From, and Destination attributes are the most valuable.
    """
    def __init__(self, summary: dict[str, str], details: Iterable[dict[str, str]]) -> None:
        self.summary = summary
        self.legs = [Leg(d) for d in details]

    @classmethod
    def load(cls, path: Path) -> "Route":
        with path.open("r") as source:
            rdr = csv.reader(source, delimiter="\t")
            title = next(rdr)
            summary = {}
            for line in rdr:
                # Blank line at the end of the header?
                if len(line) == 0:
                    break
                # Name only line with no value?
                elif len(line) == 1:
                    summary[line[0]] = ""
                # Name \t value line?
                elif len(line) == 2:
                    summary[line[0]] = line[1].strip()
                # Ugh.
                else:  # pragma: no cover
                    # We may want to "\t".join(line[1:])
                    raise ValueError("Unparsable summary line {line!r}")
            details_header = next(rdr)
            details = (
                dict(zip(details_header, row)) for row in rdr
            )
            return Route(summary, details)

@dataclass
class Duration:
    """
    A duration in days, hours, minutes, and seconds.

    We map between hours or minutes as float and (d, h, m, s) duration values.
    """
    d: int = 0
    h: int = 0
    m: int = 0
    s: int = 0

    @classmethod
    def parse(cls, text: str) -> "Duration":
        raw = {match.group(2).lower(): int(match.group(1))
               for match in re.finditer("(\d+)([dHMS])", text)}
        return cls(**raw)

    def __add__(self, other: Any) -> "Duration":
        m1 = ((self.d*24+self.h)*60+self.m)*60+self.s
        m2 = ((other.d*24+other.h)*60+other.m)*60+other.s
        d_h_m, s = divmod(m1 + m2, 60)
        d_h, m = divmod(d_h_m, 60)
        d, h = divmod(d_h, 24)
        return Duration(d, h, m, s)

    def __sub__(self, other: Any) -> "Duration":
        m1 = ((self.d*24+self.h)*60+self.m)*60+self.s
        m2 = ((other.d*24+other.h)*60+other.m)*60+other.s
        d_h_m, s = divmod(m1 - m2, 60)
        d_h, m = divmod(d_h_m, 60)
        d, h = divmod(d_h, 24)
        return Duration(d, h, m, s)

    @property
    def days(self) -> float:
        """Duration as a single float in days"""
        return self.d + self.h/24 + self.m/24/60 + self.s/24/60/60

    @property
    def hours(self) -> float:
        """Duration as a single float in hours"""
        return self.d*24 + self.h + self.m/60 + self.m/60/60

    @property
    def minutes(self) -> float:
        """Duration as a single float in minutes"""
        return (self.d*24 + self.h)*60 + self.m + self.s/60

    def __str__(self) -> str:
        """Numbers-friendly tags on hours, minutes and seconds."""
        return f"{self.d:d}d {self.h:02d}h {self.m:02d}m {self.s:02d}s"

@dataclass
class Point:
    """
    Superclass for Latitude and Longitude.
    """
    deg: int
    min: float
    h: str

    @classmethod
    def parse(cls, text: str) -> "Point":
        deg, min, hem = m.groups() if (m:=re.match(r"\s*(\d+)\D\s(\d+\.?\d*)\D\s([EWNS])", text)) is not None else ("0", "0", "?")
        return cls(int(deg), float(min), hem)

    def __str__(self) -> str:
        return f"{self.deg:d}° {self.min:.1f}′ {self.h}"


class Latitude(Point):
    def __str__(self) -> str:
        return f"{self.deg:02d}° {self.min:4.1f}′ {self.h}"


class Longitude(Point):
    def __str__(self) -> str:
        return f"{self.deg:03d}° {self.min:4.1f}′ {self.h}"


def to_html(route: Route) -> None:
    """
    Print an HTML version of the supplied OpenCPN data.
    """
    print(f"<table>")
    for k, v in route.summary.items():
        print(f"<tr><td>{k}</td><td>{v}</td></tr>")
    print(f"</table>")
    print(f"<table>")
    print(f"<tr>")
    for k in Leg.attr_names.keys():
        print(f"<th>{k}</th>", end="")
    print()
    print(f"</tr>")
    for row in route.legs:
        data = row.asdict()
        for k in Leg.attr_names.keys():
            print(f"<td>{data[k]}</td>", end="")
        print()
    print(f"</table>")

def to_csv(route: Route) -> None:
    """Convert OpenCPN to a more spreadsheet friendly format."""
    writer = csv.DictWriter(sys.stdout, list(Leg.attr_names.keys()))
    writer.writeheader()
    writer.writerows(row.asdict() for row in route.legs)

def main(argv: list[str]) -> None:
    parser= argparse.ArgumentParser()
    parser.add_argument('-f', '--format', choices=("csv", "html"), action='store', default='csv')
    parser.add_argument( 'source', nargs='*', type=Path )
    args = parser.parse_args(argv)

    for file in args.source:
        route = Route.load(file)
        if args.format == 'csv':
            to_csv(route)
        elif args.format == 'html':
            to_html(route)
        else:  # pragma: no cover
            raise RuntimeError("Faulty if")

if __name__ == "__main__":  # pragma: no cover
    main([str(Path.cwd()/"data" / "beaufort to st marys.txt")])

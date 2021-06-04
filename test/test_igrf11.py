"""
Test IGRF11

Use sample data from geomag 7.0 implementation to test the :py:mod:`igrf11` module.

Date: xxxx.xxx for decimal  (1947.32)

     YYYY,MM,DD for year, month, day  (1947,10,13)

     or start_date-end_date (1943.21-1966.11)

     or start_date-end_date-step (1943.21-1966.11-1.2)

Coord:
    D - Geodetic (WGS84 latitude and altitude above mean sea level)

    C - Geocentric (spherical, altitude relative to Earth's center)

Altitude:
    Kxxxxxx.xxx for kilometers  (K1000.13)

    Mxxxxxx.xxx for meters  (M1389.24)

    Fxxxxxx.xxx for feet  (F192133.73)

Lat/Lon: xxx.xxx for decimal  (-76.53)

    ddd,mm,ss for degrees, minutes, seconds (-60,23,22)

    (Lat and Lon must be specified in the same format,
    for ddd,mm,ss format, two commas each are required
    and decimals of arc-seconds are ignored)
"""

from __future__ import annotations
from pytest import *
from unittest.mock import Mock, call
import csv
import datetime
import math
import navtools.igrf11
from navtools.igrf11 import igrf11syn, deg2dm, declination
from typing import NamedTuple, cast, Iterator


sample_output = "geomag70_linux/sample_out_IGRF11.txt"


class Geomag_Case(NamedTuple):
    date: float
    lat: float
    lon: float
    alt: float
    coord: str
    D_deg: float
    D_min: float

    @classmethod
    def parse(cls, row: dict[str, str]) -> "Geomag_Case":
        return cls(
            cls.parse_date(row["Date"]),
            cls.parse_lat_lon(row["Latitude"]),
            cls.parse_lat_lon(row["Longitude"]),
            cls.parse_altitude(row["Altitude"]),
            row["Coord-System"],
            row["D_deg"],
            row["D_min"],
        )

    @staticmethod
    def parse_date(date_str: str) -> float:
        if "," in date_str:
            # y,m,d format.
            dt = datetime.date(*map(int, date_str.split(",")))
            first_of_year = dt.replace(month=1, day=1)
            date = dt.year + (dt.toordinal() - first_of_year.toordinal()) / 365.242
        else:
            # floating-point date
            date = float(date_str)
        return date

    @staticmethod
    def parse_altitude(alt_str: str) -> float:
        if alt_str.startswith("F"):
            # feet to km
            alt = float(alt_str[1:]) / 3280.8399
        elif alt_str.startswith("M"):
            # m to km
            alt = float(alt_str[1:]) / 1000
        elif alt_str.startswith("K"):
            alt = float(alt_str[1:])
        else:
            raise Exception("Unknown altitude units")
        return alt

    @staticmethod
    def parse_lat_lon(ll_str: str) -> float:
        if "," in ll_str:
            if ll_str.startswith("-"):
                sign = -1
                ll_str = ll_str[1:]
            else:
                sign = +1
            d, m, s = (float(x) if x else 0.0 for x in ll_str.split(","))
            return sign * (d + (m + s / 60) / 60)
        else:
            return float(ll_str)


def case_gen() -> Iterator[Geomag_Case]:
    """
    Each test case is built from the ``sample_output`` file
    in the Geomag distribution.

    :return: An iterator over :py:class:`Geomag_Case` instances
    """
    with open(sample_output, "r") as expected:
        rdr = csv.DictReader(expected, delimiter=" ", skipinitialspace=True)
        for row in rdr:
            print(
                f"Source: {row['Date']:10s}"
                f" {row['Coord-System']}"
                f" {row['Altitude']:7s}"
                f" {row['Latitude']:10s}"
                f" {row['Longitude']:10s}"
                f" {row['D_deg']:5s}"
                f" {row['D_min']:5s}"
            )
            case = Geomag_Case.parse(row)
            yield case


@fixture(params=list(case_gen()), ids=str)
def igfr11_case(request) -> Geomag_Case:
    return cast(Geomag_Case, request.param)


def test_igrf11(igfr11_case: Geomag_Case) -> None:
    case = igfr11_case

    x, y, z, f = igrf11syn(
        case.date,
        math.radians(case.lat),
        math.radians(case.lon),
        case.alt,
        coord=case.coord,
    )
    D = math.degrees(math.atan2(y, x))  # Declination in degrees

    deg, min = deg2dm(D)

    print(
        f"Result: {case.date:10.5f} {case.coord} K{case.alt:<6.1f} {case.lat:<10.3f} {case.lon:<10.3f} {deg:4d}d {min:4d}m"
    )

    assert case.D_deg == f"{deg}d"
    assert case.D_min == f"{min}m"


def test_declination():
    """
    Geomag_Case(date=2015.0, lat=0.0, lon=0.0, alt=0.0, coord='D', D_deg='-5d', D_min='26m')
    """
    d = declination(date=datetime.date(2015, 1, 1), nlat=0.0, elong=0.0)
    assert deg2dm(d) == (-5, 26)


@fixture
def mock_datetime(monkeypatch):
    today = datetime.date(2015, 1, 1)
    mock_date = Mock(today=Mock(return_value=today))
    mock_datetime = Mock(date=mock_date)
    monkeypatch.setattr(navtools.igrf11, "datetime", mock_datetime)
    return mock_datetime


def test_declination_2(mock_datetime):
    """
    Geomag_Case(date=2015.0, lat=0.0, lon=0.0, alt=0.0, coord='D', D_deg='-5d', D_min='26m')
    """
    d = declination(nlat=0.0, elong=0.0)
    assert mock_datetime.mock_calls == [call.date.today()]
    assert deg2dm(d) == (-5, 26)


def test_early_dates():
    """
    Before 2010 and Before 1995
    """
    d_2009 = declination(date=datetime.date(2009, 1, 1), nlat=0.0, elong=0.0)
    assert d_2009 == approx(-6.2256, rel=1e-4)
    d_1994 = declination(date=datetime.date(1994, 1, 1), nlat=0.0, elong=0.0)
    assert d_1994 == approx(-8.0643, rel=1e-4)

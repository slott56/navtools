#!/usr/bin/env python3
"""
Test the :py:mod:`planning` application.
"""

from pytest import *
from textwrap import dedent
import csv
from io import StringIO
import datetime
import os
from navtools.navigation import LatLon, declination, Angle
from navtools.planning import (
    RoutePoint,
    RoutePoint_Rhumb,
    RoutePoint_Rhumb_Magnetic,
    SchedulePoint,
    csv_to_RoutePoint,
    gpx_to_RoutePoint,
    gen_rhumb,
    gen_mag_bearing,
    gen_schedule,
    write_csv,
    plan,
)
from navtools import planning


csv_data = dedent(
    """\
    Piankatank 6,37º31.99'N,076º19.02'W,
    Jackson Creek Entrance,37º32.58'N,076º19.17'W,
    """
)


@fixture
def csv_file_1():
    return StringIO(csv_data)


def test_csv_to_RoutePoint(csv_file_1):
    generator = csv_to_RoutePoint(csv_file_1)
    points = list(generator)
    assert len(points) == 2

    assert points[0].name == "Piankatank 6"
    assert points[0].point.lat.deg == approx(37.53316666)
    assert points[0].point.lon.deg == approx(-76.3170)

    assert points[1].name == "Jackson Creek Entrance"
    assert points[1].point.lat.deg == approx(37.5430)
    assert points[1].point.lon.deg == approx(-76.3195)


gpx_data_1 = dedent(
    """\
    <?xml version="1.0" encoding="utf-8"?>
    <gpx version="1.1" creator="GPSNavX"
    xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
    <rte>
    <name>Whitby Rendezvous</name>
    <rtept lat="37.533195" lon="-76.316963">
    <name>Piankatank 6</name>
    <sym>BUOYR</sym>
    </rtept>
    <rtept lat="37.542961" lon="-76.319580">
    <name>Jackson Creek Entrance</name>
    <sym>BOATSLIP</sym>
    </rtept>
    </rte>
    </gpx>
    """
)


@fixture
def gpx_file_1():
    return StringIO(gpx_data_1)


def test_gpx_to_RoutePoint(gpx_file_1):
    generator = gpx_to_RoutePoint(gpx_file_1)
    points = list(generator)
    assert len(points) == 2

    assert points[0].name == "Piankatank 6"
    assert points[0].point.lat.deg == approx(37.533195)
    assert points[0].point.lon.deg == approx(-76.316963)

    assert points[1].name == "Jackson Creek Entrance"
    assert points[1].point.lat.deg == approx(37.542961)
    assert points[1].point.lon.deg == approx(-76.319580)


gpx_data_bad = dedent(
    """\
    <?xml version="1.0" encoding="utf-8"?>
    <gpx version="1.1" creator="GPSNavX"
    xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
    <rte>
    <name>Whitby Rendezvous</name>
    <rtept lat="37.533195">
    <name>Piankatank 6</name>
    <sym>BUOYR</sym>
    </rtept>
    <rtept lat="37.542961" lon="-76.319580">
    <name>Jackson Creek Entrance</name>
    <sym>BOATSLIP</sym>
    </rtept>
    </rte>
    </gpx>
    """
)


@fixture
def gpx_file_bad():
    return StringIO(gpx_data_bad)


def test_gpx_bad(gpx_file_bad):
    generator = gpx_to_RoutePoint(gpx_file_bad)
    with raises(ValueError):
        points = list(generator)


@fixture
def gen_rhumb_1():
    route = [
        RoutePoint(
            "Piankatank 6",
            "37.533195",
            "-76.316963",
            "",
            LatLon("37.533195N", "76.316963W"),
        ),
        RoutePoint(
            "Jackson Creek Entrance",
            "37.542961",
            "-76.319580",
            "",
            LatLon("37.542961N", "76.319580W"),
        ),
    ]
    generator = gen_rhumb(iter(route))
    return generator


def test_gen_rhumb(gen_rhumb_1):
    points = list(gen_rhumb_1)
    assert len(points) == 2

    assert points[0].point.name == "Piankatank 6"
    assert points[0].distance == approx(0.59944686)
    assert points[0].bearing.deg == approx(348.0038223)

    # Last is always None -- no more places to go.
    assert points[1].point.name == "Jackson Creek Entrance"
    assert points[1].distance is None
    assert points[1].bearing is None


@fixture
def gen_mag_bearing_1():
    route = [
        RoutePoint_Rhumb(
            RoutePoint(
                "Piankatank 6",
                "37.533195",
                "-76.316963",
                "",
                LatLon("37.533195N", "76.316963W"),
            ),
            0.59944686,
            Angle.fromdegrees(348.0038223),
        ),
        RoutePoint_Rhumb(
            RoutePoint(
                "Jackson Creek Entrance",
                "37.542961",
                "-76.319580",
                "",
                LatLon("37.542961N", "76.319580W"),
            ),
            None,
            None,
        ),
    ]
    generator = gen_mag_bearing(
        iter(route), declination, date=datetime.date(2012, 4, 18)
    )
    return generator


def test_gen_mag_bearing(gen_mag_bearing_1):
    points = list(gen_mag_bearing_1)
    assert len(points) == 2

    assert points[0].point.point.name == "Piankatank 6", f"Unexpected {points[0]!r}"
    assert points[0].distance == approx(0.59944686)
    assert points[0].true_bearing.deg == approx(348.0038223)
    assert points[0].magnetic.deg == approx(337.0867231)

    # Last is always None -- no more places to go.
    assert points[1].point.point.name == "Jackson Creek Entrance"
    assert points[1].distance is None
    assert points[1].true_bearing is None
    assert points[1].magnetic is None


@fixture
def gen_schedule_1():
    route = [
        RoutePoint_Rhumb_Magnetic(
            RoutePoint_Rhumb(
                RoutePoint(
                    "Piankatank 6",
                    "37.533195",
                    "-76.316963",
                    "",
                    LatLon("37.533195N", "76.316963W"),
                ),
                0.59944686,
                Angle.fromdegrees(348.0038223),
            ),
            0.59944686,
            Angle.fromdegrees(348.0038223),
            Angle.fromdegrees(337.0867607),
        ),
        RoutePoint_Rhumb_Magnetic(
            RoutePoint_Rhumb(
                RoutePoint(
                    "Jackson Creek Entrance",
                    "37.542961",
                    "-76.319580",
                    "",
                    LatLon("37.542961N", "76.319580W"),
                ),
                None,
                None,
            ),
            None,
            None,
            None,
        ),
    ]
    generator = gen_schedule(iter(route), speed=5)
    return generator


def test_gen_schedule(gen_schedule_1):
    points = list(gen_schedule_1)
    assert len(points) == 2

    assert points[0].point.point.name == "Piankatank 6"
    assert points[0].distance == approx(0.59944686)
    assert points[0].true_bearing.deg == approx(348.0038223)
    assert points[0].magnetic.deg == approx(337.0867231)
    assert points[0].running == approx(0.59944686)
    assert points[0].elapsed_min == approx(7.19336232)
    assert points[0].elapsed_hm == "00h 07m"

    # Last is always None -- no more places to go.
    assert points[1].point.point.name == "Jackson Creek Entrance"
    assert points[1].distance is None
    assert points[1].true_bearing is None
    assert points[1].magnetic is None
    assert points[0].running == approx(0.59944686)
    assert points[0].elapsed_min == approx(7.19336232)
    assert points[0].elapsed_hm == "00h 07m"


@fixture
def schedule_1():
    schedule = [
        SchedulePoint(
            RoutePoint_Rhumb(
                RoutePoint(
                    "Piankatank 6",
                    "37.533195",
                    "-76.316963",
                    "",
                    LatLon("37.533195N", "76.316963W"),
                ),
                0.59944686,
                Angle.fromdegrees(348.0038223),
            ),
            0.59944686,
            Angle.fromdegrees(348.0038223),
            Angle.fromdegrees(337.0867607),
            0.59944686,
            7.19336232,
            "00h 07m",
        ),
        SchedulePoint(
            RoutePoint_Rhumb(
                RoutePoint(
                    "Jackson Creek Entrance",
                    "37.542961",
                    "-76.319580",
                    "",
                    LatLon("37.542961N", "76.319580W"),
                ),
                None,
                None,
            ),
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    ]
    return schedule


def test_write_csv(schedule_1):
    target = StringIO()
    write_csv(iter(schedule_1), target)
    expected = dedent(
        """\
    Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM\r
    Piankatank 6,37 31.992N,076 19.018W,,0.59945,348.0,337.0,0.59945,00h 07m\r
    Jackson Creek Entrance,37 32.578N,076 19.175W,,,,,,\r
    """
    )
    assert expected == target.getvalue()


@fixture
def sample_csv_1(csv_file_1, tmp_path):
    source = tmp_path / "temp1.csv"
    with source.open("w", newline="") as fixture:
        fixture.write(csv_file_1.read())
    yield source
    source.unlink()
    target = tmp_path / f"{source.stem} Schedule.csv"
    target.unlink()


def test_plan_csv(sample_csv_1):
    plan(sample_csv_1, date=datetime.date(2012, 4, 18))
    target = sample_csv_1.parent / f"{sample_csv_1.stem} Schedule.csv"
    expected = dedent(
        """\
    Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM
    Piankatank 6,37 31.990N,076 19.020W,,0.60228,349.0,338.0,0.60228,00h 07m
    Jackson Creek Entrance,37 32.580N,076 19.170W,,,,,,
    """
    )
    with target.open() as result:
        assert expected == result.read()


@fixture
def sample_gpx_1(gpx_file_1, tmp_path):
    source = tmp_path / "temp2.gpx"
    with source.open("w", newline="") as fixture:
        fixture.write(gpx_file_1.read())
    yield source
    source.unlink()
    target = tmp_path / f"{source.stem} Schedule.csv"
    target.unlink()


def test_plan_GPX(sample_gpx_1):
    plan(sample_gpx_1, date=datetime.date(2012, 4, 18))
    expected = dedent(
        """\
    Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM
    Piankatank 6,37 31.992N,076 19.018W,,0.59945,348.0,337.0,0.59945,00h 07m
    Jackson Creek Entrance,37 32.578N,076 19.175W,,,,,,
    """
    )
    target = sample_gpx_1.parent / f"{sample_gpx_1.stem} Schedule.csv"
    with target.open() as result:
        assert expected == result.read()


@fixture
def sample_invalid_format(tmp_path):
    source = tmp_path / "invalid.format"
    yield source


def test_plan_invalid_format(sample_invalid_format):
    with raises(ValueError):
        plan(sample_invalid_format)


def test_main_full(sample_gpx_1):
    planning.main(["-s", "5.5", str(sample_gpx_1)])
    target = sample_gpx_1.parent / f"{sample_gpx_1.stem} Schedule.csv"
    assert target.exists()
    # Processing details tested in test_plan... functions

#!/usr/bin/env python3
"""
Test the :py:mod:`planning` application.
"""

from pytest import *
from unittest.mock import Mock, call
from textwrap import dedent
import csv
from io import StringIO
import datetime
import os
from navtools.navigation import LatLon, declination, Angle, Lat, Lon
from navtools.planning import (
    Waypoint,
    SchedulePoint,
    csv_to_Waypoint,
    gpx_to_Waypoint,
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
    generator = csv_to_Waypoint(csv_file_1)
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
    generator = gpx_to_Waypoint(gpx_file_1)
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
    generator = gpx_to_Waypoint(gpx_file_bad)
    with raises(ValueError):
        points = list(generator)


@fixture
def schedule_1():
    route = [
        Waypoint(
            name="Fishing Bay",
            lat=Lat.fromstring("37.54001607"),
            lon=Lon.fromstring("-76.33728421"),
            description="",
        ),
        Waypoint(
            name="Piankatank 6",
            lat=Lat.fromstring("37.533195"),
            lon=Lon.fromstring("-76.316963"),
            description="",
        ),
        Waypoint(
            name="Jackson Creek Entrance",
            lat=Lat.fromstring("37.542961"),
            lon=Lon.fromstring("-76.319580"),
            description="",
        ),
    ]
    return route

@fixture
def gen_schedule_1(schedule_1):
    generator = gen_schedule(iter(schedule_1), declination, start_datetime=datetime.date(2012, 4, 18), speed=5)
    return generator


def test_gen_schedule_1(gen_schedule_1):
    points = list(gen_schedule_1)
    assert len(points) == 3

    # First is always None -- this is our departure
    assert points[0].waypoint.name == "Fishing Bay"
    assert points[0].distance is 0
    assert points[0].true_bearing is None
    assert points[0].magnetic is None

    # Next have computed values.
    assert points[1].waypoint.name == "Piankatank 6"
    assert points[1].enroute_min == approx(12.6072302)
    assert points[1].distance == approx(1.05060252)
    assert points[1].true_bearing.deg == approx(112.9, rel=1E-3)
    assert points[1].magnetic.deg == approx(123.9, rel=1E-3)
    assert points[1].enroute_min == approx(12.607230)

    # Next have computed values.
    assert points[2].waypoint.name == "Jackson Creek Entrance"
    assert points[2].enroute_min == approx(7.19336232)
    assert points[2].distance == approx(0.59944686)
    assert points[2].true_bearing.deg == approx(348.0038223)
    assert points[2].magnetic.deg == approx(358.9, rel=1E-3)
    assert points[2].enroute_min == approx(7.19336232)

@fixture
def mock_today(monkeypatch):
    date_class = Mock(today=Mock(return_value=datetime.date(2021, 1, 18)))
    datetime_class = Mock(today=Mock(return_value=datetime.datetime(2021, 1, 18)), now=Mock(return_value=datetime.datetime(2021, 1, 18, 19, 20, 21)))
    mock_datetime = Mock(wraps=datetime, date=date_class, datetime=datetime_class)
    monkeypatch.setattr(planning, "datetime", mock_datetime)
    return mock_datetime


@fixture
def gen_schedule_1_default_date(schedule_1, mock_today):
    generator = gen_schedule(iter(schedule_1), declination, speed=5)
    return generator

def test_gen_schedule_1_default_date(gen_schedule_1_default_date):
    points = list(gen_schedule_1_default_date)
    assert len(points) == 3
    # TODO: Some additional checks are appropriate.


@fixture
def schedule_2():
    schedule = [
        SchedulePoint(
            Waypoint(
                name="Piankatank 6",
                lat=Lat.fromstring("37.533195"),
                lon=Lon.fromstring("-76.316963"),
                description="",
            ),
            distance=None,
            true_bearing=None,
            magnetic=None,
            speed=0,
            enroute_min=0,
            next_course=Angle.fromdegrees(337.0867607),
            arrival=datetime.datetime(2010,9,10,11,12,13)
        ),
        SchedulePoint(
            Waypoint(
                name="Jackson Creek Entrance",
                lat=Lat.fromstring("37.542961"),
                lon=Lat.fromstring("-76.319580"),
                description="",
            ),
            distance = 0.59944686,
            true_bearing = Angle.fromdegrees(348.0038223),
            magnetic = Angle.fromdegrees(337.0867607),
            enroute_min = 7.19336232,
            speed=5.0,
            next_course=None,
            arrival=datetime.datetime(2010, 9, 10, 12, 13, 14)
        ),
    ]
    return schedule


def test_write_csv(schedule_2):
    target = StringIO()
    write_csv(target, iter(schedule_2))
    expected = dedent(
        """\
        Leg,Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM,ETA,Course\r
        0,Piankatank 6,37 31.992N,076 19.018W,,,,,0.0,00h 00m,Sep 10 11:12,337.0\r
        1,Jackson Creek Entrance,37 32.578N,076 19.175W,,0.6,348.0,337.0,0.6,00h 07m,Sep 10 12:13,\r
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
    plan(sample_csv_1, departure=datetime.datetime(2012, 4, 18, 0, 0, 0))
    target = sample_csv_1.parent / f"{sample_csv_1.stem} Schedule.csv"
    expected = dedent(
        """\
    Leg,Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM,ETA,Course
    0,Piankatank 6,37 31.990N,076 19.020W,,0,,,0.0,00h 00m,Apr 18 00:00,360.0
    1,Jackson Creek Entrance,37 32.580N,076 19.170W,,0.6,349.0,360.0,0.6,00h 07m,Apr 18 00:07,
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
    plan(sample_gpx_1, departure=datetime.datetime(2012, 4, 18, 0, 0, 0))
    expected = dedent(
        """\
    Leg,Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM,ETA,Course
    0,Piankatank 6,37 31.992N,076 19.018W,,0,,,0.0,00h 00m,Apr 18 00:00,359.0
    1,Jackson Creek Entrance,37 32.578N,076 19.175W,,0.6,348.0,359.0,0.6,00h 07m,Apr 18 00:07,
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

# TODO: Test with various defaults for departure times.
def test_main_depart(sample_gpx_1):
    planning.main(["--departure", "2021-09-10T11:45", str(sample_gpx_1)])
    target = sample_gpx_1.parent / f"{sample_gpx_1.stem} Schedule.csv"
    assert target.exists()
    # Processing details tested in test_plan... functions


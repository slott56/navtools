"""
Test Navigation

The :py:mod:`navigation` module includes the rather complex calculations
for range and bearing.  It also wraps the declination function from
:py:mod:`igrf`.

The magnetic declination is imported from the **igrf** implementation.
The :py:mod:`navigation` uses it; which means we're really doing
a kind of integration test to be sure that the :py:func:`navigation.declination` function
properly reflects :py:mod:`igrf`.

"""

from pytest import *
from unittest.mock import Mock, call
import re
import sys
import datetime
import math
import doctest
import navtools.navigation
from navtools.navigation import (
    Angle,
    AngleParser,
    Lat,
    Lon,
    LatLon,
    KM,
    NM,
    declination,
    destination,
    range_bearing,
    Waypoint
)


def test_angle_parser():
    """
    dms_pat = re.compile( r"(\d+)\D+(\d+)\D+(\d+)[^NEWSnews]*([NEWSnews]?)" )
    dm_pat = re.compile( r"(\d+)\D+(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)" )
    d_pat = re.compile( r"(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)" )
    navx_dmh_pat = re.compile( r"(\d+)\D+(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)" )
    """
    assert AngleParser.parse("10 20 30N") == approx(10.341666)
    assert AngleParser.parse("10 20.5N") == approx(10.341666)
    assert AngleParser.parse("10.341666N") == approx(10.341666)
    with raises(ValueError):
        AngleParser.parse("Big Nope")


def test_angle():
    assert Angle.fromdegrees(10.341666) == approx(math.radians(10.341666))
    assert Angle.fromdegrees(10.341666, "S") == approx(math.radians(-10.341666))
    with raises(ValueError):
        Angle.fromdegrees(10.341666, "?")
    assert Angle.fromstring("10.341666") == approx(math.radians(10.341666))
    assert Angle.fromstring("10.341666S") == approx(math.radians(-10.341666))
    with raises(ValueError):
        Angle.fromstring("True North")
    assert Angle.parse("10.341666") == approx(math.radians(10.341666))
    a = Angle.fromdegrees(10.341666)
    assert a.radians == approx(math.radians(10.341666))
    assert a.r == approx(math.radians(10.341666))
    assert a.degrees == approx(10.341666)
    assert a.sdeg == approx(10.341666)
    assert a.deg == approx(10.341666)
    assert a.dm == approx((10, 20.5), rel=1e-4)
    assert a.dms == approx((10, 20, 30), rel=1e-4)
    assert a.h == "+"
    assert f"{a}" == "10.341666"
    assert f"{a:%d %h}" == "10.341666 +"
    assert f"{a:%03.0d %02m}" == "010 20.499960"
    assert f"{a:%03.0d %02.0m %02.0s}" == "010 20 30"

    edge = Angle(math.radians(9.999999999))
    assert edge.dm == approx((10, 0))
    assert edge.dms == approx((10, 0, 0))

    assert (a + math.radians(10)).deg == approx(20.341666)
    assert (a - math.radians(10)).deg == approx(0.341666)
    assert (a * 2).deg == approx(2 * 10.341666)
    assert (a / 2).deg == approx(0.5 * 10.341666)
    assert (a // 2).deg == approx(math.degrees(math.radians(10.341666) // 2))
    assert (a % 2).deg == approx(math.degrees(math.radians(10.341666) % 2))
    assert (a ** 2) == approx(math.radians(10.341666) ** 2)

    assert (math.radians(10) + a).deg == approx(20.341666)
    assert (math.radians(20) - a).deg == approx(9.658334)
    assert (2 * a).deg == approx(2 * 10.341666)
    assert (2 / a).deg == approx(math.degrees(2 / math.radians(10.341666)))
    assert (2 // a).deg == approx(math.degrees(2 // math.radians(10.341666)))
    assert (2 % a).deg == approx(math.degrees(2 % math.radians(10.341666)))
    assert (2 ** a) == approx(2 ** math.radians(10.341666))

    assert (-a).deg == approx(-10.341666)
    assert (+a).deg == approx(10.341666)
    assert abs(a) == a  # True because a is positive!

    assert round(a) == int(math.radians(10.341666))
    assert round(a, 1) == round(math.radians(10.341666), 1)
    from math import trunc, ceil, floor

    assert ceil(a) == math.ceil(math.radians(10.341666))
    assert floor(a) == math.floor(math.radians(10.341666))

    assert a == a
    assert not (a != a)
    assert a <= a
    assert not (a < a)
    assert a >= a
    assert not (a > a)


def test_lat():
    a = Lat.fromstring("10 20 30N")
    assert a.d == approx(10.341666)
    assert a.h == "N"
    assert repr(a) == "10°20.500′N"
    assert math.degrees(a.north) == approx(100.341666)


def test_lon():
    a = Lon.fromstring("10 20 30E")
    assert a.d == approx(10.341666)
    assert a.h == "E"
    assert repr(a) == "010°20.500′E"
    assert math.degrees(a.east) == approx(10.341666)


def test_LatLon():
    latlon_1 = LatLon(lat="50 21 50N", lon="004 09 25W")
    assert latlon_1.dms == ("50 21 50.0N", "004 09 25.0W")
    assert latlon_1.dm == ("50 21.833N", "004 9.417W")
    assert latlon_1.d == ("50.364N", "004.157W")
    assert repr(latlon_1) == "LatLon(50°21.833′N, 004°09.417′W)"

    ll_2 = LatLon(Lat.fromstring("50 21 50N"), Lon.fromstring("004 09 25W"))
    assert ll_2.lat == latlon_1.lat and ll_2.lon == latlon_1.lon
    ll_3 = LatLon(Angle.fromstring("50 21 50N"), Angle.fromstring("004 09 25W"))
    assert ll_3.lat == latlon_1.lat and ll_3.lon == latlon_1.lon
    ll_4 = LatLon(50 + 21 / 60 + 50 / 3600, -(4 + 9 / 60 + 25 / 3600))
    assert ll_4.lat == latlon_1.lat and ll_4.lon == latlon_1.lon
    with raises(ValueError):
        LatLon(("Can't", "Work",), 0.0)
    with raises(ValueError):
        LatLon(0.0, ["Won't Work", "Either"])


@fixture
def case_1():
    p1 = LatLon(lat=Lat.fromstring("50 21 50N"), lon=Lon.fromstring("004 09 25W"))
    p2 = LatLon(lat=Lat.fromstring("42 21 04N"), lon=Lon.fromstring("071 02 27W"))
    return p1, p2, 2805, 260.127


def test_range_bearing_1(case_1):
    p1, p2, distance, bearing = case_1
    d_km, brg = range_bearing(p1, p2, R=KM)
    assert d_km == approx(distance / NM * KM, rel=0.1)
    assert math.degrees(brg) == approx(bearing, rel=0.01)
    d_nm, brg = range_bearing(p1, p2, R=NM)
    assert d_nm == approx(distance, rel=0.1)
    assert math.degrees(brg) == approx(bearing, rel=0.01)


@fixture
def case_2():
    """
    Suppose point 1 is LAX: (33deg 57min N, 118deg 24min W)
    Suppose point 2 is JFK: (40deg 38min N,  73deg 47min W)
    distance = 2164.6nm
    bearing = 79.32
    """
    p1 = LatLon(lat=Lat.fromstring("33 75.0 N"), lon=Lon.fromstring("118 24.0 W"))
    p2 = LatLon(lat=Lat.fromstring("40 38.0 N"), lon=Lon.fromstring("073 47.0 W"))
    return p1, p2, 2164, 79.32


def test_range_bearing_2(case_2):
    p1, p2, distance, bearing = case_2
    d_nm, brg = range_bearing(p1, p2, R=NM)
    assert d_nm == approx(distance, rel=0.1)
    assert math.degrees(brg) == approx(bearing, rel=0.01)


def test_destination_2(case_2):
    p1, p2_expected, distance, bearing = case_2
    p2 = destination(p1, distance, bearing, R=NM)
    assert p2.lat == approx(p2_expected.lat, rel=0.1) and p2.lon == approx(
        p2_expected.lon, rel=0.1
    )


@fixture
def case_3():
    """
    Point 1: 37.549033N, 76.328957W
    Point 2: 37.2678N, 76.0178 W
    Distance: 41.63 km = 22.4784 nm
    Bearing: 138°41′23″ = 138.689
    °"""
    p1 = LatLon(lat=Lat.fromstring("37.549033N"), lon=Lon.fromstring("76.328957W"))
    p2 = LatLon(lat=Lat.fromstring("37.2678N"), lon=Lon.fromstring("76.0178W"))
    return p1, p2, 22.4784, 138.689


def test_range_bearing_3(case_3):
    p1, p2, distance, bearing = case_3
    d_nm, brg = range_bearing(p1, p2, R=NM)
    assert d_nm == approx(distance, rel=0.1)
    assert math.degrees(brg) == approx(bearing, rel=0.01)


def test_destination_3(case_3):
    p1, p2_expected, distance, bearing = case_3
    p2 = destination(p1, distance, bearing, R=NM)
    assert p2.lat == approx(p2_expected.lat, rel=0.1) and p2.lon == approx(
        p2_expected.lon, rel=0.1
    )


@fixture
def pt_range_bearing_4():
    p_1 = LatLon(lat=Lat.fromstring("51 07 32N"), lon=Lon.fromstring("001 20 17E"))
    bearing_text = "116 38 10"
    d, m, s = map(int, re.match(r"(\d+)\s+(\d+)\s+(\d+)", bearing_text).groups())
    bearing = d + m / 60 + s / 60 / 60
    p_2 = LatLon(lat=Lat.fromstring("50 57 48.1N"), lon=Lon.fromstring("001 51 08.8E"))
    return p_1, p_2, 40.23, bearing


def test_destination_4(pt_range_bearing_4):
    p1, p2_expected, distance, bearing = pt_range_bearing_4
    p2 = destination(p1, distance, bearing, R=KM)
    assert p2.lat == approx(p2_expected.lat, rel=0.1) and p2.lon == approx(
        p2_expected.lon, rel=0.1
    )
    assert p2.dms == ("50 57 48.1N", "001 51 08.8E")
    assert p2.d == ("50.963N", "001.852E")


def test_declination_chesapeake():
    """About 11d 0m W, (almost exactly -11) for 4/18/2012"""
    p1 = LatLon(lat=Lat.fromdegrees(37.8311, "N"), lon=Lon.fromdegrees(76.2819, "W"))
    # print( "p1 = {0}".format( p1.dms ) )
    d = declination(p1, date=datetime.date(2012, 4, 18))
    # print( "declination= {0}".format(d.dm) )
    assert round(math.degrees(d)) == -11


def test_declination_equator():
    """somewhere near -5d 50m for 4/18/2012"""
    p1 = LatLon(lat=Lat.fromstring("0.0N"), lon=Lon.fromstring("0.0E"))
    # print( "p1 = {0}".format( p1.dms ) )
    d = declination(p1, date=datetime.date(2012, 4, 18))
    # print( "declination= {0}".format(d.dm) )
    assert math.degrees(d) == approx(-5.801, rel=1E-3)


@fixture
def mock_datetime(monkeypatch):
    mock_date = Mock(today=Mock(return_value=datetime.date(2015, 1, 1)))
    mock_datetime_class = Mock(today=Mock(return_value=datetime.datetime(2015, 1, 1, 2, 3, 4)))
    mock_datetime = Mock(date=mock_date, datetime=mock_datetime_class)
    monkeypatch.setattr(navtools.navigation, "datetime", mock_datetime)
    return mock_datetime


def test_declination_2(mock_datetime):
    """
    Geomag_Case(date=2015.0, lat=0.0, lon=0.0, alt=0.0, coord='D', D_deg='-5d', D_min='26m')
    """
    d = declination(LatLon(lat=0.0, lon=0.0))
    assert mock_datetime.mock_calls == [call.datetime.today()]
    assert d == approx(math.radians(-(5 + 26 / 60)), rel=0.1 / 60)



def test_waypoint():
    lat = Lat(math.radians(47.0))
    lon = Lon(math.radians(8.0))
    wp = Waypoint(
            lat=lat,
            lon=lon,
            name="sample",
            description="test data",
        )
    assert wp.lat == lat
    assert wp.lon == lon
    assert wp.point.near(LatLon(lat, lon)) < 1E-05
    assert wp.geocode == "8FVC2222+222"

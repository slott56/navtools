"""
Test the :py:mod:`opencpn_table` application.
"""

from pytest import *
import re
from textwrap import dedent
from navtools.opencpn_table import *
from navtools.navigation import Waypoint


def test_leg():
    r_0 = {
        "Leg": "---",
        "To waypoint": "Beafort, NC",
        "Distance": "251.7 NMi",
        "Bearing": "192 °M",
        "Latitude": "34° 34.8' N",
        "Longitude": "076° 41.4' W",
        "ETE": "1d 17H 57M",
        "ETA": "Start: 05/26/2021 04:47 (Nighttime)",
        "Speed": "6",
        "Next tide event": "",
        "Description": "Entrance to the fairway",
        "Course": "223 °M",
    }
    leg_0 = Leg.fromdict(r_0)
    assert leg_0.waypoint.name == "Beafort, NC"
    assert leg_0.waypoint.lat == navigation.Lat.fromdegmin(34, 34.8, "N")
    assert leg_0.waypoint.lon == navigation.Lon.fromdegmin(76, 41.4, "W")
    assert leg_0.waypoint.description == "Entrance to the fairway"
    assert leg_0.leg == 0
    assert leg_0.distance == approx(251.7)
    assert leg_0.bearing == approx(192.0)
    assert leg_0.ETE == Duration(d=1, h=17, m=57, s=0)
    assert leg_0.ETA == datetime.datetime(2021, 5, 26, 4, 47)
    assert leg_0.speed == approx(6.0)
    assert leg_0.tide == ""
    assert leg_0.course == approx(223.0)
    expected_dict = {
        "Bearing": "192.0",
        "Course": "223.0",
        "Description": "Entrance to the fairway",
        "Distance": "251.7",
        "ETA": "2021-05-26 04:47:00 (Nighttime)",
        "ETE": "1d 17h 57m 00s",
        "Latitude": "34° 34.8′ N",
        "Leg": "0",
        "Longitude": "076° 41.4′ W",
        "Next tide event": "",
        "Speed": "6.0",
        "To waypoint": "Beafort, NC",
    }
    assert leg_0.asdict() == expected_dict


def test_leg_bad(capsys):
    r_bad = {
        "Leg": "---",
        "To waypoint": "Beafort, NC",
        "Nope": "251.7 NMi",
        "Bearing": "192 °M",
        "Latitude": "34° 34.8' N",
        "Longitude": "076° 41.4' W",
        "ETE": "1d 17H 57M",
        "ETA": "Start: 05/26/2021 04:47 (Nighttime)",
        "Speed": "6",
        "Description": "",
    }
    with raises(KeyError) as error:
        leg_0 = Leg.fromdict(r_bad)
    assert error.value.args[0] == "Distance"
    out, err = capsys.readouterr()
    assert out == f"Invalid {r_bad} KeyError('Distance')\n"


@fixture
def route_path(tmp_path):
    path = tmp_path / "test_1.csv"
    path.write_text(
        dedent(
            """\
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
            """
        )
    )
    yield path
    path.unlink()


def test_route(route_path):
    with route_path.open() as route_file:
        r = Route.load(route_file)
    assert repr(r) == dedent("""\
    Route('Herrington to Drum Point',
    {'Name': 'Herrington to Drum Point', 'Total distance': '22.9 NMi', 'Speed (Kts)': '6', 'Departure Time (%x %H:%M)': '05/25/2021 08:43', 'Time enroute': '3H 49M'},
    [Leg(waypoint=Waypoint(lat=38°44.200′N, lon=076°32.400′W, name='Herring Bay', description='', point=LatLon(38°44.200′N, 076°32.400′W), geocode='87C5PFP6+M26'), leg=0, ETE=Duration(d=0, h=0, m=24, s=51), ETA=datetime.datetime(2021, 5, 25, 8, 43), ETA_summary='MoTwilight', speed=6.0, tide='', distance=2.5, bearing=165.0, course=72.0), Leg(waypoint=Waypoint(lat=38°48.700′N, lon=076°21.900′W, name='Kent Point', description='', point=LatLon(38°48.700′N, 076°21.900′W), geocode='87C5RJ6P+M26'), leg=1, ETE=Duration(d=0, h=1, m=34, s=0), ETA=datetime.datetime(2021, 5, 25, 11, 51), ETA_summary='Daytime', speed=6.0, tide='', distance=9.4, bearing=72.0, course=66.0), Leg(waypoint=Waypoint(lat=38°52.900′N, lon=076°14.500′W, name='Eastern Bay', description='', point=LatLon(38°52.900′N, 076°14.500′W), geocode='87C5VQJ5+M88'), leg=2, ETE=Duration(d=0, h=1, m=11, s=0), ETA=datetime.datetime(2021, 5, 25, 13, 2), ETA_summary='Daytime', speed=6.0, tide='', distance=7.1, bearing=66.0, course=158.0), Leg(waypoint=Waypoint(lat=38°50.500′N, lon=076°12.500′W, name='Wye R. Entrance', description='', point=LatLon(38°50.500′N, 076°12.500′W), geocode='87C5RQRR+MM7'), leg=3, ETE=Duration(d=0, h=0, m=28, s=31), ETA=datetime.datetime(2021, 5, 25, 13, 31), ETA_summary='Daytime', speed=6.0, tide='', distance=2.9, bearing=158.0, course=44.0), Leg(waypoint=Waypoint(lat=38°51.800′N, lon=076°11.400′W, name='Bordley Pt.', description='', point=LatLon(38°51.800′N, 076°11.400′W), geocode='87C5VR76+82J'), leg=4, ETE=Duration(d=0, h=0, m=16, s=13), ETA=datetime.datetime(2021, 5, 25, 13, 47), ETA_summary='Daytime', speed=6.0, tide='', distance=1.6, bearing=44.0, course=14.0), Leg(waypoint=Waypoint(lat=38°53.200′N, lon=076°11.300′W, name='Drum Point', description='', point=LatLon(38°53.200′N, 076°11.300′W), geocode='87C5VRP6+MM7'), leg=5, ETE=Duration(d=0, h=0, m=13, s=43), ETA=datetime.datetime(2021, 5, 25, 14, 1), ETA_summary='Daytime', speed=6.0, tide='', distance=1.4, bearing=14.0, course=120.0), Leg(waypoint=Waypoint(lat=38°53.000′N, lon=076°10.700′W, name='Drum Point Anchorage', description='', point=LatLon(38°53.000′N, 076°10.700′W), geocode='87C5VRMC+8MM'), leg=6, ETE=Duration(d=0, h=0, m=4, s=52), ETA=datetime.datetime(2021, 5, 25, 14, 6), ETA_summary='Daytime', speed=6.0, tide='', distance=0.5, bearing=120.0, course=None)])""")
    assert r.summary["Name"] == "Herrington to Drum Point"
    assert r.summary["Total distance"] == "22.9 NMi"
    assert r.summary["Time enroute"] == "3H 49M"
    assert len(r.legs) == 7
    assert r.legs[0].waypoint.name == "Herring Bay"
    assert r.legs[6].waypoint.name == "Drum Point Anchorage"


def test_duration():
    d_0 = Duration(h=5, m=7)
    d_1 = Duration(d=1, s=59)
    assert d_0 + d_1 == Duration(d=1, h=5, m=7, s=59)
    assert Duration(d=1, h=5, m=7, s=59) - d_0 == d_1
    assert d_0.days == approx(5 / 24 + 7 / 24 / 60)
    assert d_0.hours == approx(5 + 7 / 60, rel=1e-2)
    assert d_0.minutes == approx(5 * 60 + 7)
    d_2 = Duration.fromfloat(hours=2.5)
    assert d_2.d == 0
    assert d_2.h == 2
    assert d_2.m == 30
    assert d_2.s == 0
    assert d_2.days == approx(2.5 / 24)
    assert d_2.hours == approx(2.5)
    assert d_2.minutes == approx(2.5*60)
    assert d_0 + datetime.datetime(2021, 9, 10, 11, 12, 13) == datetime.datetime(2021, 9, 10, 16, 19, 13)
    with raises(TypeError):
        d_0 + "random thing"
    with raises(TypeError):
        d_0 - "random thing"

@fixture
def route_path_2(tmp_path):
    path = tmp_path / "test_2.csv"
    path.write_text(
        dedent(
            """\
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
            """
        )
    )
    yield path
    path.unlink()


def test_to_html(route_path_2, capsys):
    with route_path_2.open() as route_file:
        r = Route.load(route_file)
    to_html(r)
    out, err = capsys.readouterr()
    assert out == dedent(
        """\
    <table>
    <tr><td>Name</td><td>Herrington to Drum Point</td></tr>
    <tr><td>Total distance</td><td>22.9 NMi</td></tr>
    <tr><td>Speed (Kts)</td><td>6</td></tr>
    <tr><td>Departure Time (%x %H:%M)</td><td>05/25/2021 08:43</td></tr>
    <tr><td>Time enroute</td><td>3H 49M</td></tr>
    </table>
    <table>
    <tr>
    <th>Leg</th><th>To waypoint</th><th>Distance</th><th>Bearing</th><th>Latitude</th><th>Longitude</th><th>ETE</th><th>ETA</th><th>Speed</th><th>Next tide event</th><th>Description</th><th>Course</th>
    </tr>
    <td>0</td><td>Herring Bay</td><td>2.5</td><td>165.0</td><td>38° 44.2′ N</td><td>076° 32.4′ W</td><td>0d 00h 24m 51s</td><td>2021-05-25 08:43:00 (MoTwilight)</td><td>6.0</td><td></td><td></td><td>72.0</td>
    <td>1</td><td>Kent Point</td><td>9.4</td><td>72.0</td><td>38° 48.7′ N</td><td>076° 21.9′ W</td><td>0d 01h 34m 00s</td><td>2021-05-25 11:51:00 (Daytime)</td><td>6.0</td><td></td><td></td><td>66.0</td>
    </table>
    """
    )


def test_to_csv(route_path_2, capsys):
    with route_path_2.open() as route_file:
        r = Route.load(route_file)
    to_csv(r)
    out, err = capsys.readouterr()
    assert out == (
        "Leg,To waypoint,Distance,Bearing,Latitude,Longitude,ETE,ETA,Speed,Next tide event,Description,Course\r\n"
        "0,Herring Bay,2.5,165.0,38° 44.2′ N,076° 32.4′ W,0d 00h 24m 51s,2021-05-25 08:43:00 (MoTwilight),6.0,,,72.0\r\n"
        "1,Kent Point,9.4,72.0,38° 48.7′ N,076° 21.9′ W,0d 01h 34m 00s,2021-05-25 11:51:00 (Daytime),6.0,,,66.0\r\n"
    )


def test_main_csv(route_path_2, capsys):
    main([str(route_path_2)])
    out, err = capsys.readouterr()
    assert out == (
        "Leg,To waypoint,Distance,Bearing,Latitude,Longitude,ETE,ETA,Speed,Next tide event,Description,Course\r\n"
        "0,Herring Bay,2.5,165.0,38° 44.2′ N,076° 32.4′ W,0d 00h 24m 51s,2021-05-25 08:43:00 (MoTwilight),6.0,,,72.0\r\n"
        "1,Kent Point,9.4,72.0,38° 48.7′ N,076° 21.9′ W,0d 01h 34m 00s,2021-05-25 11:51:00 (Daytime),6.0,,,66.0\r\n"
    )


def test_main_html(route_path_2, capsys):
    main([str(route_path_2), "-f", "html"])
    out, err = capsys.readouterr()
    assert re.match(r"^\s*\<table\>.*\</table\>\s*$", out, re.M | re.S) is not None

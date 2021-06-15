"""
Test waypoint_merge application.
"""
from pytest import *
from unittest.mock import Mock, call, sentinel
from textwrap import dedent
import io
import datetime
from math import radians, degrees
from navtools import waypoint_merge
from navtools import navigation
from navtools import lowrance_usr
from uuid import UUID

def test_waypoint():
    lat = navigation.Lat(radians(47.0))
    lon = navigation.Lat(radians(8.0))
    wp = waypoint_merge.WayPoint(
        lat,
        lon,
        datetime.datetime(2021, 9, 10, 11, 12, 13),
        "sample",
        "test data",
        None,
        None,
        {}
    )
    assert wp.lat == lat
    assert wp.lon == lon
    assert wp.point.near(navigation.LatLon(lat, lon)) < 1E-05
    assert wp.geocode == "8FVC2222+222"


def test_parse_datetime():
    EST = datetime.timezone(datetime.timedelta(seconds=-5*60*60))
    assert waypoint_merge.parse_datetime("2020-09-30T07:52:39Z") == datetime.datetime(2020, 9, 30, 7, 52, 39, tzinfo=datetime.timezone.utc)
    assert waypoint_merge.parse_datetime("2013-11-08T13:53:42-05:00") == datetime.datetime(2013, 11, 8, 13, 53, 42, tzinfo=EST)
    assert waypoint_merge.parse_datetime(None) is None
    with raises(ValueError):
        waypoint_merge.parse_datetime("not a date")

@fixture
def opencpn_GPX():
    doc = dedent("""\
    <?xml version="1.0"?>
    <gpx version="1.1" creator="OpenCPN" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns:opencpn="http://www.opencpn.org">
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
        </wpt>
    </gpx>
    """)
    return io.StringIO(doc)

@fixture
def opencpn_GPX_wp():
    return [
        waypoint_merge.WayPoint(
            lat=navigation.Lat(radians(37.184990000)),
            lon=navigation.Lon(radians(-76.422203000)),
            time=datetime.datetime(2020, 9, 30, 7, 52, 39, tzinfo=datetime.timezone.utc),
            name='Chisman Creek',
            description=None,
            sym='anchor',
            type='WPT',
            extensions={
                'opencpn:guid': '34de7898-f37e-458c-8ccb-e4e03fa325ec',
                'opencpn:viz_name': '1',
                'opencpn:arrival_radius': '0.050',
                'opencpn:waypoint_range_rings.visible': 'false',
                'opencpn:waypoint_range_rings.number': '-1',
                'opencpn:waypoint_range_rings.step': '-1',
                'opencpn:waypoint_range_rings.units': '-1',
                'opencpn:waypoint_range_rings.colour': '#FFFFFF',
                'opencpn:scale_min_max.UseScale': 'false',
                'opencpn:scale_min_max.ScaleMin': '2147483646',
                'opencpn:scale_min_max.ScaleMax': '0'
            },
        )
    ]

def test_opencpn_GPX_to_WayPoint(opencpn_GPX, opencpn_GPX_wp):
    wp_list = list(waypoint_merge.opencpn_GPX_to_WayPoint(opencpn_GPX))
    assert wp_list == opencpn_GPX_wp

@fixture
def lowrance_GPX():
    doc = dedent("""\
    <?xml version="1.0"?>
    <gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1" creator="Zeus2 W9 12988" >
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
    </gpx>
    """)
    return io.StringIO(doc)

@fixture
def lowrance_GPX_wp():
    return [
        waypoint_merge.WayPoint(
            lat=navigation.Lat(radians(25.71541470)),
            lon=navigation.Lon(radians(-80.22695124)),
            time=datetime.datetime(2017, 5, 28, 19, 15, 52, tzinfo=datetime.timezone.utc),
            name='Coconut Grove',
            description=None,
            sym='anchor',
            type=None,
            extensions={},
        ),
    ]

def test_lowrance_GPX_to_WayPoint(lowrance_GPX, lowrance_GPX_wp):
    wp_list = list(waypoint_merge.lowrance_GPX_to_WayPoint(lowrance_GPX))
    assert wp_list == lowrance_GPX_wp

@fixture
def mock_usr_load(monkeypatch):
    mock_class = Mock(
        load=Mock(
            return_value={
                "waypoints": [
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
                ]
            }
        )
    )
    monkeypatch.setattr(waypoint_merge.lowrance_usr, 'Lowrance_USR', mock_class)
    return mock_class

@fixture
def lowrance_USR_wp():
    return [
        waypoint_merge.WayPoint(
            lat=navigation.Lat(radians(24.38829583)),
            lon=navigation.Lon(radians(-76.64669528)),
            time=datetime.date(2017, 6, 11),
            name='ALLIGTR C',
            description='',
            sym='cross,blue',
            type=None,
            extensions={
                'uuid': UUID('41f0e2b8-e631-462a-82fd-f5292523f98d'),
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
                'LORAN_GRI': -1,
                'LORAN_Tda': 0,
                'LORAN_Tdb': 0
            }
        ),
    ]


def test_lowrance_USR_to_WayPoint(mock_usr_load, lowrance_USR_wp):
    wp_list = list(waypoint_merge.lowrance_USR_to_WayPoint(sentinel.source))
    assert wp_list == lowrance_USR_wp


def test_waypoint_to_GPX(lowrance_GPX_wp):
    xml = waypoint_merge.waypoint_to_GPX(lowrance_GPX_wp)
    assert xml.splitlines() == [
        '<?xml version="1.0"?>',
        '<gpx version="1.1" creator="OpenCPN" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
        'http://www.topografix.com/GPX/1/1/gpx.xsd" '
        'xmlns:opencpn="http://www.opencpn.org">',
        '    <metadata>',
        '        <time>2021-06-04T16:55:38Z</time>',
        '    </metadata>',
        '    ',
        '    <wpt lon="-80.22695124" lat="25.7154147">',
        '        <time>2017-05-28 19:15:52+00:00</time>',
        '        <name>Coconut Grove</name>',
        '        <desc>None</desc>',
        '        <sym>anchor</sym>',
        '        <type>WPT</type>',
        '        <extensions>',
        '          <opencpn:guid></opencpn:guid>',
        '        </extensions>',
        '    </wpt>',
        '    ',
        '</gpx>',
    ]

def test_History():
    h = waypoint_merge.History(
        waypoint_merge.WayPoint(30.0, -80.0),
    )
    assert h.matched is None

def test_WP_Match():
    m = waypoint_merge.WP_Match(
        waypoint_merge.WayPoint(30.0, -80.0),
        waypoint_merge.WayPoint(30.0, -80.0),
    )
    assert m.wp_1.point.near(waypoint_merge.WayPoint(30.0, -80.0).point) < 1E-05
    assert m.wp_2.point.near(waypoint_merge.WayPoint(30.0, -80.0).point) < 1E-05
    assert m.wp_1.geocode == m.wp_2.geocode


def test_match_gen_match(lowrance_GPX_wp):
    compare = Mock(return_value=True)
    result = list(waypoint_merge.match_gen(compare, lowrance_GPX_wp, lowrance_GPX_wp))
    assert result == [
        waypoint_merge.WP_Match(lowrance_GPX_wp[0], lowrance_GPX_wp[0])
    ]
    compare.assert_called_once()

def test_match_gen_nomatch_1(lowrance_GPX_wp, opencpn_GPX_wp):
    compare = Mock(return_value=False)
    result = list(waypoint_merge.match_gen(compare, lowrance_GPX_wp, opencpn_GPX_wp))
    assert result == [
        waypoint_merge.WP_Match(lowrance_GPX_wp[0], None),
        waypoint_merge.WP_Match(None, opencpn_GPX_wp[0])
    ]
    compare.assert_called_once()

def test_report(lowrance_GPX_wp, opencpn_GPX_wp, lowrance_USR_wp, capsys):
    matches = [
        waypoint_merge.WP_Match(lowrance_GPX_wp[0], lowrance_GPX_wp[0]),
        waypoint_merge.WP_Match(lowrance_GPX_wp[0], None),
        waypoint_merge.WP_Match(None, opencpn_GPX_wp[0]),
        waypoint_merge.WP_Match(lowrance_USR_wp[0], opencpn_GPX_wp[0])
    ]
    waypoint_merge.report(matches)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        '  Coconut Grove           =Coconut Grove           ',
        '- Coconut Grove           =                         25°42.925′N 080°13.617′W',
        '+                         =Chisman Creek                                     37°11.099′N 076°25.332′W',
        '  ALLIGTR C               =Chisman Creek            24°23.298′N 076°38.802′W 37°11.099′N 076°25.332′W 768.41 NM',
    ]

@fixture
def mock_gpx_usr(tmp_path):
    f_1 = tmp_path/"gpx"
    f_1.write_text('<?xml version="1.0"?>')
    f_2 = tmp_path/"usr"
    f_2.write_bytes(b'\x06\x00\x00\x00')
    yield f_1, f_2
    f_1.unlink()
    f_2.unlink()

@fixture
def mock_opencpn_gpx(monkeypatch, opencpn_GPX_wp):
    mock_function = Mock(
        return_value = opencpn_GPX_wp
    )
    monkeypatch.setattr(waypoint_merge, 'opencpn_GPX_to_WayPoint', mock_function)
    return mock_function

@fixture
def mock_lowrance_usr(monkeypatch, lowrance_USR_wp):
    mock_function = Mock(
        return_value = lowrance_USR_wp
    )
    monkeypatch.setattr(waypoint_merge, 'lowrance_USR_to_WayPoint', mock_function)
    return mock_function


def test_main_name_summary(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "name"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'By Name',
        'Computer (-) | Chartplotter (+)',
        '- Chisman Creek           =                         37°11.099′N 076°25.332′W',
        '+                         =ALLIGTR C                                         24°23.298′N 076°38.802′W',
    ]

def test_main_distance_summary(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "distance"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'By Distance',
        'Computer (-) | Chartplotter (+)',
        '- Chisman Creek           =                         37°11.099′N 076°25.332′W',
        '+                         =ALLIGTR C                                         24°23.298′N 076°38.802′W',
    ]

def test_main_geocode_summary(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "geocode"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'By Geocode',
        'Computer (-) | Chartplotter (+)',
        '- Chisman Creek           =                         37°11.099′N 076°25.332′W',
        '+                         =ALLIGTR C                                         24°23.298′N 076°38.802′W',
    ]

def test_main_guid_summary(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "guid"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'By GUID',
        'Computer (-) | Chartplotter (+)',
        '- Chisman Creek           =                         37°11.099′N 076°25.332′W',
        '+                         =ALLIGTR C                                         24°23.298′N 076°38.802′W',
    ]
def test_main_name_gpx(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "name", "-r", "gpx"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        '<?xml version="1.0"?>',
        '<gpx version="1.1" creator="OpenCPN" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
        'http://www.topografix.com/GPX/1/1/gpx.xsd" '
        'xmlns:opencpn="http://www.opencpn.org">',
        '    <metadata>',
        '        <time>2021-06-04T16:55:38Z</time>',
        '    </metadata>',
        '    ',
        '    <wpt lon="-76.64669528" lat="24.38829583">',
        '        <time>2017-06-11</time>',
        '        <name>ALLIGTR C</name>',
        '        <desc></desc>',
        '        <sym>cross,blue</sym>',
        '        <type>WPT</type>',
        '        <extensions>',
        '          <opencpn:guid>41f0e2b8-e631-462a-82fd-f5292523f98d</opencpn:guid>',
        '        </extensions>',
        '    </wpt>',
        '    ',
        '</gpx>',
    ]

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
        waypoint_merge.Waypoint_Plot(
            waypoint = waypoint_merge.Waypoint(
                lat=navigation.Lat(radians(37.184990000)),
                lon=navigation.Lon(radians(-76.422203000)),
                name='Chisman Creek',
                description=None,
            ),
            last_updated=datetime.datetime(2020, 9, 30, 7, 52, 39, tzinfo=datetime.timezone.utc),
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
        waypoint_merge.Waypoint_Plot(
            waypoint_merge.Waypoint(
                lat=navigation.Lat(radians(25.71541470)),
                lon=navigation.Lon(radians(-80.22695124)),
                name='Coconut Grove',
                description=None,
            ),
            last_updated=datetime.datetime(2017, 5, 28, 19, 15, 52, tzinfo=datetime.timezone.utc),
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
        waypoint_merge.Waypoint_Plot(
            waypoint_merge.Waypoint(
                lat=navigation.Lat(radians(24.38829583)),
                lon=navigation.Lon(radians(-76.64669528)),
                name='ALLIGTR C',
                description='',
            ),
            last_updated=datetime.date(2017, 6, 11),
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
        '        <description>None</description>',
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
        waypoint_merge.Waypoint_Plot(30.0, -80.0),
    )
    assert not h.matches

def test_WP_Match():
    m = waypoint_merge.WP_Match(
        waypoint_merge.Waypoint_Plot(waypoint_merge.Waypoint(30.0, -80.0)),
        waypoint_merge.Waypoint_Plot(waypoint_merge.Waypoint(30.0, -80.0)),
    )
    assert m.wp_1.waypoint.point.near(waypoint_merge.Waypoint_Plot(waypoint_merge.Waypoint(30.0, -80.0)).waypoint.point) < 1E-05
    assert m.wp_2.waypoint.point.near(waypoint_merge.Waypoint_Plot(waypoint_merge.Waypoint(30.0, -80.0)).waypoint.point) < 1E-05
    assert m.wp_1.waypoint.geocode == m.wp_2.waypoint.geocode
    assert m.both
    assert not m.first
    assert not m.second

def test_compare_by_name_match(lowrance_GPX_wp):
    h1 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    h2 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    waypoint_merge.CompareByName().compare(h1, h2)
    assert h1[0].wp == lowrance_GPX_wp[0]
    assert h2[0].wp == lowrance_GPX_wp[0]
    assert h1[0].matches['ByName'] == [h2[0].wp]
    assert h2[0].matches['ByName'] == [h1[0].wp]

@fixture
def lowrance_USR_duplicate():
    return [
        waypoint_merge.Waypoint_Plot(
            waypoint_merge.Waypoint(
                lat=navigation.Lat(radians(37.18093682)),
                lon=navigation.Lon(radians(-76.41148230)),
                name='Chisman Creek',
                description='',
            ),
            last_updated=datetime.date(2017, 6, 11),
            sym='anchor,blue',
            type=None,
            extensions={
                'uuid': UUID('34de7898-f37e-458c-8ccb-e4e03fa325ec'),
                'UID_unit_number': 12988,
                'UID_sequence_number': 328,
                'waypt_stream_version': 2,
                'waypt_name_length': 18,
                'waypt_name': 'Chisman Creek',
                'UID_unit_number_2': 12988,
                'longitude': -76.41148230,
                'latitude': 37.18093682,
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

def test_compare_by_guid_match(opencpn_GPX_wp, lowrance_USR_duplicate):
    h1 = list(map(waypoint_merge.History, opencpn_GPX_wp))
    h2 = list(map(waypoint_merge.History, lowrance_USR_duplicate))
    waypoint_merge.CompareByGUID().compare(h1, h2)
    assert h1[0].wp == opencpn_GPX_wp[0]
    assert h2[0].wp == lowrance_USR_duplicate[0]
    assert h1[0].matches['ByGUID'] == [h2[0].wp]
    assert h2[0].matches['ByGUID'] == [h1[0].wp]

def test_compare_by_code_match(lowrance_GPX_wp):
    h1 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    h2 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    waypoint_merge.CompareByGeocode.range(8)().compare(h1, h2)
    assert h1[0].wp == lowrance_GPX_wp[0]
    assert h2[0].wp == lowrance_GPX_wp[0]
    assert h1[0].matches['ByCode8'] == [h2[0].wp]
    assert h2[0].matches['ByCode8'] == [h1[0].wp]

def test_compare_by_distance_match(lowrance_GPX_wp):
    h1 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    h2 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    waypoint_merge.CompareByDistance().compare(h1, h2)
    assert h1[0].wp == lowrance_GPX_wp[0]
    assert h2[0].wp == lowrance_GPX_wp[0]
    assert h1[0].matches['ByDist'] == [h2[0].wp]
    assert h2[0].matches['ByDist'] == [h1[0].wp]


def test_history_update_nomatch_1(monkeypatch, opencpn_GPX_wp, lowrance_GPX_wp):
    h1 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    h2 = list(map(waypoint_merge.History, lowrance_GPX_wp))
    monkeypatch.setattr(waypoint_merge.CompareByDistance, 'rule', Mock(return_value=False))
    waypoint_merge.CompareByDistance().compare(h1, h2)
    assert h1[0].wp == lowrance_GPX_wp[0]
    assert h2[0].wp == lowrance_GPX_wp[0]
    assert h1[0].matches['ByDist'] == []
    assert h2[0].matches['ByDist'] == []



def test_match_gen(lowrance_GPX_wp, opencpn_GPX_wp, lowrance_USR_wp):
    history_1 = [
        waypoint_merge.History(lowrance_GPX_wp[0], {"ByName": [opencpn_GPX_wp[0]]}),
        waypoint_merge.History(opencpn_GPX_wp[0]),
    ]
    history_2 = [
        waypoint_merge.History(opencpn_GPX_wp[0])
    ]
    matches = list(waypoint_merge.match_gen(history_1, history_2))
    assert matches == [
        waypoint_merge.WP_Match(lowrance_GPX_wp[0], opencpn_GPX_wp[0]),
        waypoint_merge.WP_Match(opencpn_GPX_wp[0], None),
        waypoint_merge.WP_Match(None, opencpn_GPX_wp[0]),

    ]

def test_duplicates_none(opencpn_GPX_wp, capsys):
    waypoint_merge.duplicates(opencpn_GPX_wp)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Chartplotter Duplicates'
    ]

def test_duplicates_one(opencpn_GPX_wp, capsys):
    dup_waypoint = opencpn_GPX_wp + opencpn_GPX_wp
    waypoint_merge.duplicates(dup_waypoint)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Chartplotter Duplicates',
        "Waypoint(lat=37°11.099′N, lon=076°25.332′W, name='Chisman Creek', description=None, point=LatLon(37°11.099′N, 076°25.332′W), geocode='87955HMH+X4V')",
        "  - Waypoint(lat=37°11.099′N, lon=076°25.332′W, name='Chisman Creek', description=None, point=LatLon(37°11.099′N, 076°25.332′W), geocode='87955HMH+X4V')",
        "  - Waypoint(lat=37°11.099′N, lon=076°25.332′W, name='Chisman Creek', description=None, point=LatLon(37°11.099′N, 076°25.332′W), geocode='87955HMH+X4V')",
    ]

def test_survey(opencpn_GPX_wp, lowrance_USR_wp, capsys):
    waypoint_merge.survey(opencpn_GPX_wp, lowrance_USR_wp)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Computer (-) | Chartplotter (+)',
        "+ Waypoint(lat=24°23.298′N, lon=076°38.802′W, name='ALLIGTR C', description='', point=LatLon(24°23.298′N, 076°38.802′W), geocode='77P599Q3+887')"]

def test_survey_2(opencpn_GPX_wp, lowrance_USR_duplicate, capsys):
    """Lines 525-528: a match in OpenCPN"""
    waypoint_merge.survey(opencpn_GPX_wp, lowrance_USR_duplicate)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Computer (-) | Chartplotter (+)',
        "  Waypoint(lat=37°11.099′N, lon=076°25.332′W, name='Chisman Creek', description=None, point=LatLon(37°11.099′N, 076°25.332′W), geocode='87955HMH+X4V')",
        "    ByName: [Waypoint(lat=37°10.856′N, lon=076°24.689′W, name='Chisman Creek', description='', point=LatLon(37°10.856′N, 076°24.689′W), geocode='87955HJQ+9CC')]",
        "    ByGUID: [Waypoint(lat=37°10.856′N, lon=076°24.689′W, name='Chisman Creek', description='', point=LatLon(37°10.856′N, 076°24.689′W), geocode='87955HJQ+9CC')]",
    ]

def test_survey_3(opencpn_GPX_wp, lowrance_GPX_wp, capsys):
    """Lines 531: Unique to OpenCPN
    test fixtures have unique OpenCPN waypoint.
    """
    waypoint_merge.survey(opencpn_GPX_wp, lowrance_GPX_wp)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Computer (-) | Chartplotter (+)',
        "+ Waypoint(lat=25°42.925′N, lon=080°13.617′W, name='Coconut Grove', description=None, point=LatLon(25°42.925′N, 080°13.617′W), geocode='76QXPQ8F+567')"
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

def test_main_survery(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-r", "survey"])
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'Chartplotter Duplicates',
        '',
        '==========',
        '',
        'Computer (-) | Chartplotter (+)',
        "+ Waypoint(lat=24°23.298′N, lon=076°38.802′W, name='ALLIGTR C', "
        "description='', point=LatLon(24°23.298′N, 076°38.802′W), "
        "geocode='77P599Q3+887')",
    ]

def test_main_name_gpx(mock_gpx_usr, mock_opencpn_gpx, mock_lowrance_usr, capsys):
    f_1, f_2 = mock_gpx_usr
    waypoint_merge.main(["-c", str(f_1), "-p", str(f_2), "-b", "name", "-b", "distance", "-b", "geocode", "-b", "guid", "-r", "gpx.new"])
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
        '        <description></description>',
        '        <sym>cross,blue</sym>',
        '        <type>WPT</type>',
        '        <extensions>',
        '          <opencpn:guid>41f0e2b8-e631-462a-82fd-f5292523f98d</opencpn:guid>',
        '        </extensions>',
        '    </wpt>',
        '    ',
        '</gpx>',
    ]

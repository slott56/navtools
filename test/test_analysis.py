"""
Test the :py:mod:`analysis` application.
"""

from pytest import *
from unittest.mock import Mock, call
import datetime
from textwrap import dedent
from io import StringIO
from navtools.navigation import LatLon, declination, Angle
from navtools.analysis import *
from navtools import analysis
from navtools import navigation


@fixture
def mock_today(monkeypatch):
    date_class = Mock(today=Mock(return_value=datetime.date(2021, 1, 18)))
    mock_datetime = Mock(wraps=datetime, date=date_class)
    monkeypatch.setattr(analysis, "datetime", mock_datetime)
    return mock_datetime


def test_parse_date(mock_today):
    assert parse_date("11:12 PM") == datetime.datetime(2021, 1, 18, 23, 12)
    assert parse_date("Sep 10 11:12 PM") == datetime.datetime(2021, 9, 10, 23, 12)
    assert parse_date("9-10-2021 11:12 PM") == datetime.datetime(2021, 9, 10, 23, 12)
    with raises(ValueError):
        parse_date("9-10-2021 11:12 Nope")


@fixture
def iNavX_csv_file():
    navx_csv_data = dedent(
        """\
        2011-06-04 13:12:32 +0000,37.549225,-76.330536,219,3.6,,,,,,
        2011-06-04 13:12:43 +0000,37.549084,-76.330681,186,3.0,,,,,,
        """
    )
    return StringIO(navx_csv_data)


def test_csv_to_LogEntry_no_header(iNavX_csv_file):
    assert not csv_sniff_header(iNavX_csv_file)
    generator = csv_externheader_to_LogEntry(iNavX_csv_file, None)
    points = list(generator)
    assert len(points) == 2
    assert (
        points[0].time.strftime("%Y-%m-%d %H:%M:%S %z") == "2011-06-04 13:12:32 +0000"
    )
    assert points[0].point.lat.deg == approx(37.549225)
    assert points[0].point.lon.deg == approx(-76.330536)

    assert (
        points[1].time.strftime("%Y-%m-%d %H:%M:%S %z") == "2011-06-04 13:12:43 +0000"
    )
    assert points[1].point.lat.deg == approx(37.549084)
    assert points[1].point.lon.deg == approx(-76.330681)


@fixture
def manual_csv_file():
    manual_csv_data = dedent(
        """\
        Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location
        9:21 AM,37 50.424N,076 16.385W,None,0,None,1200 RPM,,,Cockrell Creek
        10:06 AM,37 47.988N,076 16.056W,None,6.6,None,1500 RPM,315,7.0,
        """
    )
    return StringIO(manual_csv_data)


def test_csv_to_LogEntry_header(manual_csv_file):
    assert csv_sniff_header(manual_csv_file)
    generator = csv_internheader_to_LogEntry(manual_csv_file)
    points = list(generator)
    # for p in points: print( repr(p) )
    assert len(points) == 2

    assert points[0].time.strftime("%H:%M") == "09:21"
    assert points[0].point.lat.deg == approx(37.8404)
    assert points[0].point.lon.deg == approx(-76.2730833)

    assert points[1].time.strftime("%H:%M") == "10:06"
    assert points[1].point.lat.deg == approx(37.7998)
    assert points[1].point.lon.deg == approx(-76.2676)


@fixture
def bad_manual_csv_file():
    bad_manual_csv_data = dedent(
        """\
        Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location
        9:21 AM,Nope,076 16.385W,None,0,None,1200 RPM,,,Cockrell Creek
        10:06 AM,37 47.988N,Not Good,None,6.6,None,1500 RPM,315,7.0,
        """
    )
    return StringIO(bad_manual_csv_data)


def test_bad_csv_to_LogEntry(bad_manual_csv_file, capsys):
    assert csv_sniff_header(bad_manual_csv_file)
    generator = csv_internheader_to_LogEntry(bad_manual_csv_file)
    points = list(generator)
    output, error = capsys.readouterr()
    assert output == dedent(
        """\
    {'Time': '9:21 AM', 'Lat': 'Nope', 'Lon': '076 16.385W', 'COG': 'None', 'SOG': '0', 'Rig': 'None', 'Engine': '1200 RPM', 'windAngle': '', 'windSpeed': '', 'Location': 'Cockrell Creek'}
    Cannot parse 'Nope'
    {'Time': '10:06 AM', 'Lat': '37 47.988N', 'Lon': 'Not Good', 'COG': 'None', 'SOG': '6.6', 'Rig': 'None', 'Engine': '1500 RPM', 'windAngle': '315', 'windSpeed': '7.0', 'Location': ''}
    Cannot parse 'Not Good'
    """
    )
    assert error == ""

@fixture
def bad_noheader_csv_file():
    bad_manual_csv_data = dedent(
        """\
        2011-06-04 13:12:32 +0000,nope,-76.330536,219,3.6,,,,,,
        2011-06-04 13:12:43 +0000,37.549084,not good,186,3.0,,,,,,
        """
    )
    return StringIO(bad_manual_csv_data)

def test_bad_noheader_csv_to_LogEntry(bad_noheader_csv_file, capsys):
    assert not csv_sniff_header(bad_noheader_csv_file)
    generator = csv_externheader_to_LogEntry(bad_noheader_csv_file)
    points = list(generator)
    output, error = capsys.readouterr()
    assert output == dedent(
        """\
    {'date': '2011-06-04 13:12:32 +0000', 'latitude': 'nope', 'longitude': '-76.330536', 'cog': '219', 'sog': '3.6', 'heading': '', 'speed': '', 'depth': '', 'windAngle': '', 'windSpeed': '', 'comment': ''}
    Cannot parse 'nope'
    {'date': '2011-06-04 13:12:43 +0000', 'latitude': '37.549084', 'longitude': 'not good', 'cog': '186', 'sog': '3.0', 'heading': '', 'speed': '', 'depth': '', 'windAngle': '', 'windSpeed': '', 'comment': ''}
    Cannot parse 'not good'
    """
    )
    assert error == ""

@fixture
def gpx_file_1():
    gpx_data = dedent(
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <gpx version="1.1" creator="GPSNavX"
        xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
        <trk>
        <trkseg>
        <trkpt lat="37.534599" lon="-76.313622">
        <time>2010-09-06T16:50:42Z</time>
        </trkpt>
        <trkpt lat="37.535213" lon="-76.312889">
        <time>2010-09-06T16:51:34Z</time>
        </trkpt>
        </trkseg>
        </trk>
        </gpx>
        """
    )
    return StringIO(gpx_data)


def test_gpx_to_LogEntry(gpx_file_1):
    generator = gpx_to_LogEntry(gpx_file_1)
    points = list(generator)
    assert len(points) == 2

    assert (
        points[0].time.strftime("%Y-%m-%d %H:%M:%S %z") == "2010-09-06 16:50:42 +0000"
    )
    assert points[0].point.lat.deg == approx(37.549225, rel=0.01)
    assert points[0].point.lon.deg == approx(-76.313622)

    assert (
        points[1].time.strftime("%Y-%m-%d %H:%M:%S %z") == "2010-09-06 16:51:34 +0000"
    )
    assert points[1].point.lat.deg == approx(37.535213, rel=0.01)
    assert points[1].point.lon.deg == approx(-76.312889)


@fixture
def bad_gpx_file_1():
    gpx_data = dedent(
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <gpx version="1.1" creator="GPSNavX"
        xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
        <trk>
        <trkseg>
        <trkpt lat="37.534599">
        <time>2010-09-06T16:50:42Z</time>
        </trkpt>
        <trkpt lat="37.535213" lon="-76.312889">
        <time>2010-09-06T16:51:34Z</time>
        </trkpt>
        </trkseg>
        </trk>
        </gpx>
        """
    )
    return StringIO(gpx_data)


def test_bad_gpx_to_LogEntry_1(bad_gpx_file_1):
    generator = gpx_to_LogEntry(bad_gpx_file_1)
    with raises(ValueError) as error:
        points = list(generator)
    assert error.value.args[0] == (
        'Can\'t process <ns0:trkpt xmlns:ns0="http://www.topografix.com/GPX/1/1" '
        'lat="37.534599">\n'
        "<ns0:time>2010-09-06T16:50:42Z</ns0:time>\n"
        "</ns0:trkpt>\n"
    )


@fixture
def bad_gpx_file_2():
    gpx_data = dedent(
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <gpx version="1.1" creator="GPSNavX"
        xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
        <trk>
        <trkseg>
        <trkpt lat="37.534599" lon="-76.313622">
        <time>2010-09-06T16:50:42Z</time>
        </trkpt>
        <trkpt lat="37.535213" lon="-76.312889">
        <time>2010-09-06 Nope This is Invalid</time>
        </trkpt>
        </trkseg>
        </trk>
        </gpx>
        """
    )
    return StringIO(gpx_data)


def test_bad_gpx_to_LogEntry_2(bad_gpx_file_2):
    generator = gpx_to_LogEntry(bad_gpx_file_2)
    with raises(ValueError) as error:
        points = list(generator)
    assert error.value.args[0] == (
        "time data '2010-09-06 Nope This is Invalid' does not match format '%Y-%m-%dT%H:%M:%SZ'"
    )


@fixture
def bad_gpx_file_3():
    gpx_data = dedent(
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <gpx version="1.1" creator="GPSNavX"
        xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
        <trk>
        <trkseg>
        <trkpt lat="37.534599" lon="-76.313622">
        </trkpt>
        <trkpt lat="37.535213" lon="-76.312889">
        <time>2010-09-06 Nope This is Invalid</time>
        </trkpt>
        </trkseg>
        </trk>
        </gpx>
        """
    )
    return StringIO(gpx_data)


def test_bad_gpx_to_LogEntry_3(bad_gpx_file_3):
    generator = gpx_to_LogEntry(bad_gpx_file_3)
    with raises(ValueError) as error:
        points = list(generator)
    assert error.value.args[0] == (
        'Can\'t process <ns0:trkpt xmlns:ns0="http://www.topografix.com/GPX/1/1" lat="37.534599" lon="-76.313622">\n</ns0:trkpt>\n'
    )


@fixture
def gen_rhumb_1():
    route = [
        LogEntry(
            time=datetime.datetime(2012, 4, 17, 9, 21),
            lat=navigation.Lat.fromstring("37.533195"),
            lon=navigation.Lat.fromstring("-76.316963"),
            source_row={
                "Engine": "1200 RPM",
                "SOG": "0",
                "Lon": "076 16.385W",
                "windSpeed": "",
                "Location": "Cockrell Creek",
                "COG": "None",
                "Time": "9:21 AM",
                "Lat": "37 50.424N",
                "Rig": "None",
                "windAngle": "",
            },
        ),
        LogEntry(
            time=datetime.datetime(2012, 4, 17, 10, 6),
            lat=navigation.Lat.fromstring("37.542961"),
            lon=navigation.Lon.fromstring("-76.319580"),
            source_row={
                "Engine": "1500 RPM",
                "SOG": "6.6",
                "Lon": "076 16.056W",
                "windSpeed": "7.0",
                "Location": "",
                "COG": "None",
                "Time": "10:06 AM",
                "Lat": "37 47.988N",
                "Rig": "None",
                "windAngle": "315",
            },
        ),
    ]
    generator = gen_rhumb(iter(route))
    return generator


def test_gen_rhumb(gen_rhumb_1):
    points = list(gen_rhumb_1)
    assert len(points) == 2

    assert points[0].point.time.strftime("%I:%M %p") == "09:21 AM"
    assert points[0].distance == approx(0.59944686)
    assert points[0].bearing.deg == approx(348.0038223)
    assert points[0].delta_time.seconds == approx(45 * 60)

    # Last is always None -- no more places to go.
    assert points[1].point.time.strftime("%I:%M %p") == "10:06 AM"
    assert points[1].distance is None
    assert points[1].bearing is None
    assert points[1].delta_time is None


from itertools import zip_longest


def equalCSV(expected_txt, actual_txt, row_builder=None):
    """
    Compare CSV output files.

    Prior to Python 3.6, CSV column orders can't easily be controlled.
    There's no compelling reason to force a specific logical layout.
    Instead, we'll compare the actual and expected CSV files while
    permitting column orders to vary.

    The number of rows must be the same. We use :py:func:`zip_longest`, to
    inject ``None`` objects and fail the comparison.

    We'll compare two CSV files by building the list-of-dict objects that we can
    then compare for equality. We're comparing text values only.
    In the case where float values must be compared, a row-comparison
    function must be injected to convert float fields and apply the
    :py:func:`pytest.approx` function as needed.

    :param expected_txt: CSV file text
    :param actual_txt: CSV file text
    :return: True if the match
    :raises: :exc:`AssertionError` if they don't match.

    ..  todo:: The :func:`equalCSV` function needs to be shared with test_planning, also.
    """
    if row_builder is None:
        row_builder = lambda row: row
    ex_rdr = csv.DictReader(StringIO(expected_txt))
    ex_data = list(ex_rdr)
    ac_rdr = csv.DictReader(StringIO(actual_txt))
    ac_data = list(ac_rdr)
    for ex_row, ac_row in zip_longest(ex_data, ac_data):
        assert row_builder(ex_row) == row_builder(
            ac_row
        ), f"Expected {ex_row!r} != Actual {ac_row!r}"
    return True


@fixture
def sample_track_1():
    track = [
        LogEntry_Rhumb(
            LogEntry(
                time=datetime.datetime(2012, 4, 17, 9, 21),
                lat=navigation.Lat.fromstring("37.533195"),
                lon=navigation.Lon.fromstring("-76.316963"),
                source_row={
                    "Engine": "1200 RPM",
                    "SOG": "0",
                    "Lon": "076 16.385W",
                    "windSpeed": "",
                    "Location": "Cockrell Creek",
                    "COG": "None",
                    "Time": "9:21 AM",
                    "Lat": "37 50.424N",
                    "Rig": "None",
                    "windAngle": "",
                },
            ),
            distance=0.59944686,
            bearing=Angle.fromdegrees(348.0038223),
            delta_time=datetime.timedelta(seconds=45 * 60),
        ),
        LogEntry_Rhumb(
            LogEntry(
                time=datetime.datetime(2012, 4, 17, 10, 6),
                lat=navigation.Lat.fromstring("37.542961"),
                lon=navigation.Lat.fromstring("-76.319580"),
                source_row={
                    "Engine": "1500 RPM",
                    "SOG": "6.6",
                    "Lon": "076 16.056W",
                    "windSpeed": "7.0",
                    "Location": "",
                    "COG": "None",
                    "Time": "10:06 AM",
                    "Lat": "37 47.988N",
                    "Rig": "None",
                    "windAngle": "315",
                },
            ),
            distance=None,
            bearing=None,
            delta_time=None,
        ),
    ]
    return track


def test_write_csv(sample_track_1):
    expected = dedent(
        """\
        Engine,windSpeed,COG,Location,SOG,Time,Lat,Rig,Lon,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time\r
        1200 RPM,,None,Cockrell Creek,0,9:21 AM,37 50.424N,None,076 16.385W,,0.59945,348.0,2012-04-17 09:21:00,0:45:00,0.59945,0:45:00\r
        1500 RPM,7.0,None,,6.6,10:06 AM,37 47.988N,None,076 16.056W,315,,,2012-04-17 10:06:00,,0.59945,0:45:00\r
        """
    )
    target = StringIO()
    write_csv(target, iter(sample_track_1))
    assert equalCSV(expected, target.getvalue())


@fixture
def sample_track_empty():
    track = []
    return track


def test_empty_write_csv(sample_track_empty):
    target = StringIO()
    write_csv(iter(sample_track_empty), target)
    assert target.getvalue() == ""


@fixture
def sample_csv_1(iNavX_csv_file, tmp_path):
    source = tmp_path / "temp1.csv"
    with source.open("w", newline="") as fixture:
        fixture.write(iNavX_csv_file.read())
    yield source
    source.unlink()
    target = tmp_path / f"{source.stem} Distance.csv"
    target.unlink()


def test_NavX_analyze_CSV(sample_csv_1):
    analyze(sample_csv_1)
    target = sample_csv_1.parent / f"{sample_csv_1.stem} Distance.csv"
    expected = dedent(
        """\
        comment,sog,windSpeed,longitude,latitude,depth,cog,date,speed,heading,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
        ,3.6,,-76.330536,37.549225,,219,2011-06-04 13:12:32 +0000,,,,0.01092,219.0,2011-06-04 13:12:32+00:00,0:00:11,0.01092,0:00:11
        ,3.0,,-76.330681,37.549084,,186,2011-06-04 13:12:43 +0000,,,,,,2011-06-04 13:12:43+00:00,,0.01092,0:00:11
        """
    )
    with target.open() as result:
        assert equalCSV(expected, result.read())


@fixture
def sample_csv_2(manual_csv_file, tmp_path):
    source = tmp_path / "temp2.csv"
    with source.open("w", newline="") as fixture:
        fixture.write(manual_csv_file.read())
    yield source
    source.unlink()
    target = tmp_path / f"{source.stem} Distance.csv"
    target.unlink()


def test_Manual_analyze_CSV(sample_csv_2):
    analyze(sample_csv_2, date=datetime.date(2012, 4, 18))
    target = sample_csv_2.parent / f"{sample_csv_2.stem} Distance.csv"
    expected = dedent(
        """\
        Engine,SOG,Lon,windSpeed,Location,COG,Time,Lat,Rig,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
        1200 RPM,0,076 16.385W,,Cockrell Creek,None,9:21 AM,37 50.424N,None,,2.45148,174.0,2012-04-18 09:21:00,0:45:00,2.45148,0:45:00
        1500 RPM,6.6,076 16.056W,7.0,,None,10:06 AM,37 47.988N,None,315,,,2012-04-18 10:06:00,,2.45148,0:45:00
        """
    )
    with target.open() as result:
        assert equalCSV(expected, result.read())


@fixture
def sample_gpx(gpx_file_1, tmp_path):
    source = tmp_path / "temp3.gpx"
    with source.open("w", newline="") as fixture:
        fixture.write(gpx_file_1.read())
    yield source
    source.unlink()
    target = tmp_path / f"{source.stem} Distance.csv"
    target.unlink()


def test_analyze_GPX(sample_gpx):
    analyze(sample_gpx)
    target = sample_gpx.parent / f"{sample_gpx.stem} Distance.csv"
    expected = dedent(
        """\
        lat,lon,time,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
        37.534599,-76.313622,2010-09-06T16:50:42Z,0.05076,43.0,2010-09-06 16:50:42+00:00,0:00:52,0.05076,0:00:52
        37.535213,-76.312889,2010-09-06T16:51:34Z,,,2010-09-06 16:51:34+00:00,,0.05076,0:00:52
        """
    )
    with target.open() as result:
        assert equalCSV(expected, result.read())


@fixture
def sample_invalid_format(tmp_path):
    source = tmp_path / "invalid.format"
    yield source


def test_analyze_invalid_format(sample_invalid_format):
    with raises(ValueError):
        analyze(sample_invalid_format)


def test_main_full(sample_gpx):
    main([str(sample_gpx), "-d", "2021-Jan-18"])
    target = sample_gpx.parent / f"{sample_gpx.stem} Distance.csv"
    assert target.exists()
    # Processing details tested in test_analyze... functions


def test_main_default(sample_gpx):
    analysis.main([str(sample_gpx)])
    target = sample_gpx.parent / f"{sample_gpx.stem} Distance.csv"
    assert target.exists()
    # Processing details tested in test_analyze... functions

"""
Test lowrance_usr file parser.
"""

from pytest import *
from unittest.mock import Mock, call, sentinel
from io import BytesIO
import struct
from navtools import lowrance_usr


@fixture
def format_6_empty():
    return BytesIO(
        bytes(
            b'\x06\x00\x00\x00\n\x00\x00\x00\x17\x00\x00\x00Navico export data file\n\x00\x00\x0006/04/2021\xea\x86%\x00vJ{\x02\xff\xbc2\x00\x00\x1d\x00\x00\x00Waypoints, routes, and trails\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        )
    )


def test_dump_next(format_6_empty, capsys):
    lowrance_usr.dump_next(format_6_empty, 95)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        '06 00 00 00 0a 00 00 00 17 00 00 00 4e 61 76 69 63 6f 20 65 78 70 6f 72 74 '
        '20 64 61 74 61 20 66 69 6c 65 0a 00 00 00 30 36 2f 30 34 2f 32 30 32 31 ea '
        '86 25 00 76 4a 7b 02 ff bc 32 00 00 1d 00 00 00 57 61 79 70 6f 69 6e 74 73 '
        '2c 20 72 6f 75 74 65 73 2c 20 61 6e 64 20 74 72 61 69 6c 73',
        '\x06  \x00  \x00  \x00  ',
        '  \x00  \x00  \x00  \x17  \x00  \x00  \x00  N  a  v  i  c  o     e  x  p  o  '
        'r  t     d  a  t  a     f  i  l  e  ',
        '  \x00  \x00  \x00  0  6  /  0  4  /  2  0  2  1  ê  \x86  %  \x00  v  J  {  '
        '\x02  ÿ  ¼  2  \x00  \x00  ',
        '  \x00  \x00  \x00  W  a  y  p  o  i  n  t  s  ,     r  o  u  t  e  s  ,     '
        'a  n  d     t  r  a  i  l  s ',
        "b'\\x06\\x00\\x00\\x00\\n\\x00\\x00\\x00\\x17\\x00\\x00\\x00Navico export "
        'data '
        'file\\n\\x00\\x00\\x0006/04/2021\\xea\\x86%\\x00vJ{\\x02\\xff\\xbc2\\x00\\x00\\x1d\\x00\\x00\\x00Waypoints, '
        "routes, and trails'",
    ]

def test_dump_next_eof(capsys):
    data = BytesIO()
    lowrance_usr.dump_next(data, 95)
    out, err = capsys.readouterr()
    assert out == "EOF\n"


def test_unpack_context():
    """
    The mock_field does not update the state of the source.
    """
    mock_field = Mock(
        extract=Mock(return_value=sentinel.extract)
    )
    uc = lowrance_usr.UnpackContext(BytesIO(b'\x05\x00\x00\x00'))
    assert uc.peek(mock_field) == sentinel.extract
    assert uc.extract(mock_field) == sentinel.extract
    assert not uc.eof()

def test_unpack_context_eof():
    mock_field = Mock(
        extract=Mock(return_value=sentinel.extract)
    )
    uc = lowrance_usr.UnpackContext(BytesIO(b''))
    assert uc.eof()


@fixture
def mock_unpack_context_int():
    unpack_context = Mock(
        source = BytesIO(b'\x05\x00\x00\x00'),
        fields = {}
    )
    return unpack_context

def test_field(mock_unpack_context_int):
    f = lowrance_usr.AtomicField("name", "<I", lambda x: 2 ** x[0])
    r = f.extract(mock_unpack_context_int)
    assert r == 32
    assert mock_unpack_context_int.fields["name"] == 32
    assert list(f.report()) == [
        {"name": "name", "format": "<I", "size": "4"},
    ]

@fixture
def mock_unpack_context_ascii():
    unpack_context = Mock(
        source = BytesIO(b'\x05\x00\x00\x00xyzzy'),
        fields = {}
    )
    return unpack_context

def test_field_dependency(mock_unpack_context_ascii):
    f1 = lowrance_usr.AtomicField("name_len", "<i")
    f2 = lowrance_usr.AtomicField("name", "<{name_len}s", lambda x: x[0].decode("ascii"))
    r1 = f1.extract(mock_unpack_context_ascii)
    r2 = f2.extract(mock_unpack_context_ascii)
    assert r1 == 5
    assert r2 == "xyzzy"
    assert mock_unpack_context_ascii.fields["name_len"] == 5
    assert mock_unpack_context_ascii.fields["name"] == "xyzzy"
    assert list(f1.report()) == [{'format': '<i', 'name': 'name_len', 'size': '4'}]
    assert list(f2.report()) == [{'format': '', 'name': 'name', 'size': 'varies'}]


def test_field_bad_encoding(mock_unpack_context_ascii):
    f1 = lowrance_usr.AtomicField("name_len", "<R")
    with raises(struct.error) as exinfo:
        f1.extract(mock_unpack_context_ascii)
    assert exinfo.value.args == ('bad char in struct format',)

def test_field_bad_conversion(mock_unpack_context_ascii):
    f1 = lowrance_usr.AtomicField("name_len", "<i", lambda x: x[0] / 0)
    with raises(ZeroDivisionError) as exinfo:
        f1.extract(mock_unpack_context_ascii)
    assert exinfo.value.args == ('division by zero',)

def test_field_list(mock_unpack_context_ascii):
    f1 = lowrance_usr.AtomicField("name_len", "<i")
    f2 = lowrance_usr.AtomicField("name", "<{name_len}s", lambda x: x[0].decode("ascii"))
    f3 = lowrance_usr.FieldList(
        "name_and_len",
        [f1, f2]
    )
    r3 = f3.extract(mock_unpack_context_ascii)
    assert r3 == {"name_len": 5, "name": "xyzzy"}
    assert mock_unpack_context_ascii.fields["name_len"] == 5
    assert mock_unpack_context_ascii.fields["name"] == "xyzzy"
    assert mock_unpack_context_ascii.fields["name_and_len"] == {"name": "xyzzy", "name_len": 5}
    assert list(f3.report()) == [
        {'name': 'name_and_len'},
        {'format': '<i', 'name': 'name_and_len - name_len', 'size': '4'},
        {'format': '', 'name': 'name_and_len - name', 'size': 'varies'},
    ]

@fixture
def mock_unpack_context_array():
    unpack_context = Mock(
        source = BytesIO(b'\x03\x00\xda\x0fI@T\xf8-@\x00\x00(B'),
        fields = {}
    )
    return unpack_context

def test_field_repeat(mock_unpack_context_array):
    f1 = lowrance_usr.AtomicField("count", "<h")
    f2 = lowrance_usr.FieldRepeat("values", lowrance_usr.AtomicField("v", "<f"), "count")
    f3 = lowrance_usr.FieldList(
        "count_and_values",
        [f1, f2]
    )
    r3 = f3.extract(mock_unpack_context_array)
    assert r3 ==  {'count': 3, 'values': approx([3.1415926, 2.718281828, 42.0])}
    assert list(f3.report()) == [
        {'name': 'count_and_values'},
        {'format': '<h', 'name': 'count_and_values - count', 'size': '2'},
        {'format': 'depends on count', 'name': 'count_and_values - values'},
        {'format': '<f', 'name': 'count_and_values - values - v', 'size': '4'},
    ]

def test_lon_degree():
    """
    <wpt lon="-76.66669595" lat="24.36669586" >

    {'uuid': UUID('89f2be82-8907-4a34-afe8-5155e8e61920'), 'UID_unit_number': 12988, 'UID_sequence_number': 206, 'waypt_stream_version': 2, 'waypt_name_length': 20, 'waypt_name': 'WARDRCK BR', 'UID_unit_number_2': 12988, 'longitude': -76.66669595, 'latitude': 24.36669586, 'flags': 2, 'icon_id': 0, 'color_id': 0, 'waypt_description_length': -1, 'waypt_description': '', 'alarm_radius': 0.0, 'waypt_creation_date': datetime.date(2017, 6, 11), 'waypt_creation_time': datetime.timedelta(seconds=35309, microseconds=973000), 'unknown_2': -1, 'depth': 0.0, 'LORAN_GRI': -1, 'LORAN_Tda': 0, 'LORAN_Tdb': 0}
    """
    assert lowrance_usr.lon_deg(-8505883) == -76.66669595

def test_lat_degree():
    """
    <wpt lon="-76.66669595" lat="24.36669586" >

    {'uuid': UUID('89f2be82-8907-4a34-afe8-5155e8e61920'), 'UID_unit_number': 12988, 'UID_sequence_number': 206, 'waypt_stream_version': 2, 'waypt_name_length': 20, 'waypt_name': 'WARDRCK BR', 'UID_unit_number_2': 12988, 'longitude': -76.66669595, 'latitude': 24.36669586, 'flags': 2, 'icon_id': 0, 'color_id': 0, 'waypt_description_length': -1, 'waypt_description': '', 'alarm_radius': 0.0, 'waypt_creation_date': datetime.date(2017, 6, 11), 'waypt_creation_time': datetime.timedelta(seconds=35309, microseconds=973000), 'unknown_2': -1, 'depth': 0.0, 'LORAN_GRI': -1, 'LORAN_Tda': 0, 'LORAN_Tdb': 0}
    """
    assert lowrance_usr.lat_deg(2788774) == 24.36669586

def test_b2i_le():
    assert lowrance_usr.b2i_le(b'\x2a\x00\x00\x00') == 42

def test_lowrance_usr_empty(format_6_empty):
    usr = lowrance_usr.Lowrance_USR.load(format_6_empty)
    assert usr["format"] == 6
    assert usr["file_title"] == 'Navico export data file'
    assert usr["file_creation_date_text"] == "06/04/2021"
    assert usr["file_description"] == "Waypoints, routes, and trails"

@fixture
def format_6():
    """
    TODO: Format 6 with

    - 1 waypoint
    - 1 route
    - 1 event marker
    - 1 trail
    """
    return BytesIO(
        bytes(
            b'\x06\x00\x00\x00\n\x00\x00\x00\x17\x00\x00\x00Navico export data file\n\x00\x00\x0006/04/2021\xea\x86%\x00vJ{\x02\xff\xbc2\x00\x00\x1d\x00\x00\x00Waypoints, routes, and trails'
            
            # 1 Waypoint
            b'\x01\x00\x00\x00'
            b'\x82\xbe\xf2\x89\x07\x894J\xaf\xe8QU\xe8\xe6\x19 \xbc2\x00\x00\xce\x00\x00\x00\x00\x00\x00\x00\x02\x00\x14\x00\x00\x00W\x00A\x00R\x00D\x00R\x00C\x00K\x00 \x00B\x00R\x00\xbc2\x00\x00\xe55~\xff\xa6\x8d*\x00\x02\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\x00\x00\x00\x00<\x81%\x00\x95\xc9\x1a\x02\xff\x00\x00\x00\x00\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00'
            
            # 1 Route 
            b'\x01\x00\x00\x00'
            b'\xb6\x19/%\x9675F\x92.\x95&\x9br\x8f\x1e\xbc2\x00\x00M\x01\x00\x00\x00\x00\x00\x00\x01\x00\x14\x00\x00\x00W\x00R\x00D\x00R\x00K\x00 \x00B\x00L\x00K\x00P\x00\xbc2\x00\x00\x04\x00\x00\x00\x82\xbe\xf2\x89\x07\x894J\xaf\xe8QU\xe8\xe6\x19 /\xff\xd3\r\xca>\xc0K\x99oU|D`\xedI\xb0\x99\xd9\xf0\x00\x92&D\x98\xd4\x9cZ\x8b\xc5\x88n\x1c\x15\xa7\xd0\xdb\x7f\x02L\x99%C\xbf<\xf17\xa3\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            
            # zero Event Markers
            b'\x00\x00\x00\x00'
            
            # zero Trails
            b'\x00\x00\x00\x00'
        )
    )

def test_lowrance_usr(format_6):
    usr = lowrance_usr.Lowrance_USR.load(format_6)
    assert usr["format"] == 6
    assert len(usr["waypoints"]) == 1
    assert len(usr["routes"]) == 1
    assert usr["waypoints"][0]["waypt_name"] == "WARDRCK BR"
    assert usr["routes"][0]["route_name"] == "WRDRK BLKP"
    assert usr["routes"][0]["leg_uuids"][0] == usr["waypoints"][0]["uuid"]

def test_layout(capsys):
    f = lowrance_usr.AtomicField("name", "<I", lambda x: 2 ** x[0])
    lowrance_usr.layout(f)
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        'name,format,size',
        'name,<I,4'
    ]

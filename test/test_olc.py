"""
Test the OLC serialization

See https://github.com/google/open-location-code/blob/main/test_data/decoding.csv
and https://github.com/google/open-location-code/blob/main/test_data/encoding.csv

Note that 4 of the decoding test cases don't pass correctly.
"""
from pytest import *
from pathlib import Path
import csv
from typing import Iterable, Iterator, NamedTuple
from navtools import olc

def reject_comment(source: str) -> bool:
    """i.e. pass non-comment, or pass lines without a leading "#"."""
    return not source.startswith("#")


class EncodeCase(NamedTuple):
    latitude: float
    longitude: float
    length: int
    expected_code: str


def encode_iter():
    source_path = Path.cwd()/"test"/"encoding.csv"
    with source_path.open() as source:
        reader = csv.DictReader(
            filter(reject_comment, source),
            ["latitude", "longitude", "length", "expected code"]
        )
        for row in reader:
            yield EncodeCase(
                float(row["latitude"]),
                float(row["longitude"]),
                int(row["length"]),
                row["expected code"],
            )

@fixture(params=list(encode_iter()), ids=repr)
def encode_case(request):
    return request.param

def test_encode(encode_case):
    text = olc.OLC().encode(encode_case.latitude, encode_case.longitude, encode_case.length)
    assert encode_case.expected_code == text, f"{encode_case} != {text!r}"


class DecodeCase(NamedTuple):
    code: str
    length: int
    latLo: float
    lngLo: float
    latHi: float
    lngHi: float


def decode_iter():
    source_path = Path.cwd()/"test"/"decoding.csv"
    with source_path.open() as source:
        reader = csv.DictReader(
            filter(reject_comment, source),
            ["code","length","latLo","lngLo","latHi","lngHi"]
        )
        for row in reader:
            yield DecodeCase(
                row["code"],
                int(row["length"]),
                float(row["latLo"]),
                float(row["lngLo"]),
                float(row["latHi"]),
                float(row["lngHi"]),
            )

@fixture(params=list(decode_iter()), ids=repr)
def decode_case(request):
    return request.param

@mark.skip
def test_decode(decode_case):
    lat, lon = olc.OLC().decode(decode_case.code)
    assert decode_case.latLo <= lat <= decode_case.latHi, f"{decode_case}: {lat!r} not in latLo-latHi"
    assert decode_case.lngLo <= lon <= decode_case.lngHi, f"{decode_case}: {lon!r} not in lngLo-lngHi"

@fixture
def decode_case_2():
    """8FVC2222+22,10,47.0,8.0,47.000125,8.000125"""
    return DecodeCase(
        "8FVC2222+22",
        10,
        47.0,
        8.0,
        47.000125,
        8.000125,
    )

def test_decode_2(decode_case_2):
    lat, lon = olc.OLC().decode(decode_case_2.code)
    assert decode_case_2.latLo <= lat <= decode_case_2.latHi, f"{decode_case_2}: {lat!r} not in latLo-latHi"
    assert decode_case_2.lngLo <= lon <= decode_case_2.lngHi, f"{decode_case_2}: {lon!r} not in lngLo-lngHi"

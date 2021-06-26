"""
Test :py:mod:`navtools.solar`.
"""
from textwrap import dedent
from navtools.navigation import Lat, Lon
from navtools import solar
import datetime

def test_sun_times(capsys):
    lat = Lat.fromstring("40° 0.0' N")
    lon = Lon.fromstring("105° 0.0' W")
    now = datetime.datetime(2021, 6, 23, 1, 00)
    noon, rise, set = solar.sun_times(now, lat, lon, solar.US_CST, debug=True)
    assert noon == datetime.datetime(2021, 6, 23, 13, 2, 15)
    assert rise == datetime.datetime(2021, 6, 23, 5, 31, 53)
    assert set == datetime.datetime(2021, 6, 23, 20, 32, 37)

    out, err = capsys.readouterr()
    assert out == dedent("""\
        now=datetime.datetime(2021, 6, 23, 1, 0) D=44370 E=0.041666666666666664 F=2459388.79
        G=0.21475131 I=91.67902391 J=8088.372379 K=0.016699601
        L=0.377959691 M=92.0569836 N=8088.750339
        P=92.04681102 Q=23.43649845 R=23.43738737
        S=92.2306899 T=23.42154087
        U=0.04302734 V=-2.246194634 W=112.5920774
        X=0.543226524 Y=0.230470754 Z=0.855982295
        """)

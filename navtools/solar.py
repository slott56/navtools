"""Location of the sun.

This lets us compute whether an arrival is in daylight, or in the dark.

Further, with some interpolation along legs of a route,
it lets us inject noon waypoints that are reminders to send notifications
of progress.


>>> from navtools.navigation import Lat, Lon
>>> import datetime
>>> lat = Lat.fromstring("40° 0.0' N")
>>> lon = Lon.fromstring("105° 0.0' W")
>>> now = datetime.datetime(2021, 6, 23, 1, 00)
>>> noon, rise, set = sun_times(now, lat, lon, US_CST, debug=True)
now=datetime.datetime(2021, 6, 23, 1, 0) D=44370 E=0.041666666666666664 F=2459388.79
G=0.21475131 I=91.67902391 J=8088.372379 K=0.016699601
L=0.377959691 M=92.0569836 N=8088.750339
P=92.04681102 Q=23.43649845 R=23.43738737
S=92.2306899 T=23.42154087
U=0.04302734 V=-2.246194634 W=112.5920774
X=0.543226524 Y=0.230470754 Z=0.855982295

>>> print(f"{noon=:%d %H:%M:%S} {rise=:%d %H:%M:%S} {set=:%d %H:%M:%S}")
noon=23 13:02:15 rise=23 05:31:53 set=23 20:32:37

Twilight
========

Computing nautical twilight is Solar zenith angle is 102°, solar elevation angle is -12°.
This is 12° beyond the horizon.

For some information, see http://www.stargazing.net/kepler/sunrise.html

This appears to be an offset to the Hour Angle of sunrise.

..  math::

    ha = \\arccos [ \\frac{cos 90.833}{\\cos {lat} \\cos T} - \\tan{lat}\\tan T ]

This suggests the horizon where we're looking for the sun (90.833)
can be switched to 102 to add 12° to compute the start and end of twilight.

Computations
============

See     https://gml.noaa.gov/grad/solcalc/calcdetails.html

See     https://edwilliams.org/sunrise_sunset_algorithm.htm

..  todo::

    Add nautical twilight offsets.
"""
from __future__ import annotations
import calendar
import datetime
from typing import Optional
from navtools.navigation import Lat, Lon
from math import radians, degrees, pi, sin, cos, tan, asin, acos, atan2

US_EST = datetime.timedelta(seconds=-5 * 60 * 60)
US_CST = datetime.timedelta(seconds=-6 * 60 * 60)
US_MST = datetime.timedelta(seconds=-7 * 60 * 60)
US_PST = datetime.timedelta(seconds=-8 * 60 * 60)


def sun_times(
    now: datetime.datetime,
    lat: Lat,
    lon: Lon,
    tzoffset: datetime.timedelta = US_EST,
    debug: bool = False,
) -> tuple[datetime.datetime, datetime.datetime, datetime.datetime]:
    """
    A literal transcription of the NOAA Spreadsheet.
    https://gml.noaa.gov/grad/solcalc/calcdetails.html

    :param now: Date for which to compute sunrise and sunset.
    :param lat: Latitude
    :param lon: Longitude
    :param tzoffset: Local timezone offset to provide local times.
    :param debug: True to display the columns of the spreadsheet with intermediate values.
    :return: Tuple with local apparent noon, surise, and sunset times.
    """
    D = now.date().toordinal() - datetime.date(1900, 1, 1).toordinal() + 2  # Date
    E = (
        (now - now.replace(hour=0, minute=0, second=0)).total_seconds() / 24 / 60 / 60
    )  # Time (past local midnight)
    F = D + 2415018.5 + E - (tzoffset.total_seconds() / 60 / 60) / 24  # Julian Day
    G = (F - 2451545) / 36525  # Julian Century
    I = (
        280.46646 + 36000.76983 * G + 0.0003032 * G ** 2
    ) % 360  #  Sun Geometric mean longitude (degrees)
    J = (
        357.52911 + 35999.05029 * G - 0.0001537 * G ** 2
    )  # Sun Geometric mean anomaly (degrees)
    K = 0.016708634 - G * (
        0.000042037 + 0.0000001267 * G
    )  # Eccentricity of Earth Orbit
    L = (
        sin(radians(J)) * (1.914602 - G * (0.004817 + 0.000014 * G))
        + sin(radians(2 * J)) * (0.019993 - 0.000101 * G)
        + sin(radians(3 * J)) * 0.000289
    )  # Sun equation of center
    M = I + L  # Sun true longitude (degrees)
    N = J + L  # Sun true anomaly (degrees)
    # O = (1.000001018 * (1 - K ** 2)) / (1 + K * cos(radians(N)))  # Sun rad Vector (AUs)
    P = (
        M - 0.00569 - 0.00478 * sin(radians(125.04 - 1934.136 * G))
    )  # Sun apparent longitude (degrees)
    Q = (
        23 + (26 + ((21.448 - G * (46.815 + G * (0.00059 - G * 0.001813)))) / 60) / 60
    )  # Mean obliquity ecliptic (degrees)
    R = Q + 0.00256 * cos(
        radians(125.04 - 1934.136 * G)
    )  # obliquity correction (degrees)
    S = degrees(
        atan2(cos(radians(R)) * sin(radians(P)), cos(radians(P)))
    )  # Sun right ascension (degrees)
    T = degrees(asin(sin(radians(R)) * sin(radians(P))))  # Sun declination (degrees)
    U = tan(radians(R / 2)) ** 2  # variable Y
    V = 4 * degrees(
        U * sin(2 * radians(I))
        - 2 * K * sin(radians(J))
        + 4 * K * U * sin(radians(J)) * cos(2 * radians(I))
        - 0.5 * U * U * sin(4 * radians(I))
        - 1.25 * K * K * sin(2 * radians(J))
    )  # Equation of time (minutes)
    # NOTE: 90.833 is the 90° 50' zenith for sunrise/sunset.
    # Use 102.0 to include Nautical Twilight.
    W = degrees(
        acos(
            cos(radians(90.833)) / (cos(lat) * cos(radians(T)))
            - tan(lat) * tan(radians(T))
        )
    )  # Hour Angle of Sunrise (degrees)
    X = (
        720 - 4 * lon.degrees - V + (tzoffset.total_seconds() / 60)
    ) / 1440  # Solar Noon (LST)
    Y = X - W * 4 / 1440  # Sunrise (LST)
    Z = X + W * 4 / 1440  # Subset (LST)
    if debug:
        print(
            f"{now=} {D=} {E=} {F=:.2f}\n{G=:.8f} {I=:.8f} {J=:.6f} {K=:.9f}\n{L=:.9f} {M=:.7f} {N=:.6f}\n{P=:.8f} {Q=:.8f} {R=:.8f}\n{S=:.7f} {T=:.8f}\n{U=:.8f} {V=:.9f} {W=:.7f}\n{X=:.9f} {Y=:.9f} {Z=:.9f}"
        )
    noon = datetime.timedelta(
        seconds=round(X * 24 * 60 * 60)
    ) + datetime.datetime.combine(
        now.date(), datetime.time(0, 0, 0)
    )  # Solar Noon (LST)
    rise = datetime.timedelta(
        seconds=round(Y * 24 * 60 * 60)
    ) + datetime.datetime.combine(
        now.date(), datetime.time(0, 0, 0)
    )  # Sunrise (LST)
    set = datetime.timedelta(
        seconds=round(Z * 24 * 60 * 60)
    ) + datetime.datetime.combine(
        now.date(), datetime.time(0, 0, 0)
    )  # Sunset (LST)
    return noon, rise, set


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod()

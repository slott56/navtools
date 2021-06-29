"""
This module computes ranges and bearings between points.
It also inverts this and computes a point from a point, range, and bearing.
It leverages the :mod:`igrf` module to compute compass bearing from
true bearing.

A "rhumb line" (or loxodrome) is a path of constant bearing, which
crosses all meridians at the same angle. This is a simplified, flat-earth
model that side-steps the more sophisticated haversine-based approach.

Sailors navigate along rhumb lines because
it is easier to follow a constant compass bearing than to be continually
adjusting the bearing to follow a great circle. Rhumb
lines are straight lines on a chart that uses the Mercator projection.

Rhumb lines are generally longer than great-circle (orthodrome) routes.
For instance, London to New York is 4% longer along a rhumb line than
along a great circle; whiile this is important for aviation fuel, it is not
particularly important for sailing vessels.


Navigation Module Design
==========================

The :mod:`navigation` module contains domain objects and calculations.
The domain objects include the following:

-   A coordinate point (:py:class:`LatLon`) is a pair of angles,
    :math:`(lat, lon)`.  Each of these values is an :py:class:`Angle`.

-   The angle definition (:py:class:`Angle`, :py:class:`Lat`, and :py:class:`Lon`)
    includes the various format conversions from human
    friendly notations in degrees, minutes, seconds with hemisphere.
    It also includes formatting into these human-friendly notations.

A central design question is the packaging of the calculations
themselves.  There are two choices:

-   Stand-alone functions.

-   Methods of the :py:class:`LatLon` class.

We have a handy range-bearing function, :math:`R(p_1, p_2)` which
is a composition of two elements: distance, :math:`d`, and bearing, :math:`\\theta`.

..  math::

    d( p_1, p_2 ), &\\text{ distance from $p_1$ to $p_2$}\\\\
    \\theta( p_1, p_2 ), &\\text{ bearing from $p_1$ to $p_2$}

    R( p_1, p_2 ) = \\Bigl( d( p_1, p_2 ), \\theta( p_1, p_2 ) \\Bigr)

The destination function, :math:`D( p_1, d, \\theta )`, has (almost) two parts, also.
It can also be seen as a single object, which is a coordinate pair.

..  math::

    D_{\\phi}( p_1, d, \\theta ), &\\text{ latitude at distance $d$, angle $\\theta$ from $p_1$}\\\\
    D_{\\lambda}( p_1, d, \\theta ), &\\text{ longitude at distance $d$, angle $\\theta$ from $p_1$}

    D( p_1, d, \\theta ) = \\Bigl( D_{\\phi}( p_1, d, \\theta ), D_{\\lambda}( p_1, d, \\theta ) \\Bigr)

Stand-alone functions like these fit the mathematical definitions in a simple
and precise way.  The code would look like the following:

..  code-block:: python

    d, b = distance_bearing(p1, p2)

This is an apt summary of what we're doing.

The alternative, method functions of the :py:class:`LatLon` class, have a
problem in clarity.  The arguments to the function are textually
separated by the method name, like this:

..  code-block:: python

    d, b = p1.distance_bearing(p2)

With this syntax, the coordinates ``p1`` and ``p2`` lose the obvious "peer" relationship
For this reason, the various calculations are implemented as
stand-alone functions, not method functions of the :py:class:`LatLon` class.


Problem Domain Objects
=======================

An essential feature of the navigation calculations is that Latitude
and Longitude are actually angles.  They appear (on a Mercator chart) to be
planar Cartesian coordinates, but they're actually a pair of angles measured
from the center of the earth.

A point on the surface has two angles: latitude is the angle
normal to the equator and longitude is the angle normal to the
Greenwich meridian, parallel to the equator.

Note that lines of longitude converge at the poles.

Angle
-----

Fundamentally, the calculations we're interested in,
:py:func:`range_bearing` and :py:func:`destination`, work
with radians.  An :py:class:`Angle` is a signed radians number,
an extension to built-in :py:class:`float`.

Our source and target presentations
are various kinds of Degree-Minute-Second values.
The :py:class:`Angle` class includes a number of conversion and parsing
features.

Generally, we create an :py:class:`Angle` from one of these sources:

-   :py:class:`float`: create an :py:class:`Angle` from a floating-point value in degrees.
    The :py:meth:`fromdegrees` static method does this.

-   :py:class:`string`: attempts a number of DMS conversions.
    The :py:meth:`fromstring` static method does this.

    This is implemented via the separate :py:class:`AngleParser` object.
    We can extend the parsing without actually changing the base :py:class:`Angle` class.
    Formats include ``dd mm ss.sss``, ``dd mm.mmm``, ``dd.dddd``, and
    ``dd\\xbcdd.ddd`` from GPX files.

-   :py:class:`Angle`: This is the ordinary ``Angle(someangle)`` which will
    use a value which is expressed in radians.

There are two subclasses of representations for those angles:

-   :py:class:`Lat` -- Latitude -- with a 0°-90° range and a sign expressed as "N" or "S".

-   :py:class:`Lon` -- Longitude -- with a 0°-180° range and a sign expressed as "E" or "W".

This works nicely because the complex features are related to formatting and parsing.
The rest of the life of a :py:class:`Lat` or :py:class:`Lon` is merely as a float value of signed radians.

Note that the subclasses of :py:class:`Angle` have narrowly-defined contexts:

- Latitude is an angle from the equator, hemisphere is "N" or "S". Range is 0 to 90.

- Longitude is an angle from the prime meridian, hemisphere is "E" or "W". Range is 0 to 180.

There are other angles, which are not constrained by the Lat and Lon rules.
These are simply float values.


AngleParser
---------------------

The :py:class:`AngleParser` class is used to parse a input string values. We try four
distinct formats. The value returned, ultimately, is a signed degree value.

This class is used by the :py:class:`Angle` class to parse a string.
See :py:meth:`Angle.fromstring`. These are implemented separately to
make it slightly easier to add angle parsing features without breaking
the fundamental definition of the :py:class:`Angle` class.

It's possible to create a slight generalization to the parsing
approach. If we use ``r"(?P<d>...)(?P<m>...)..."`` then a pattern will
have some combination of groups named 'd', 'm' and 's'.  We can then
use code like ``float(m.groupdict('0').get('m'))`` to get a value, or supply '0'
as a default.

Doing this would allow us to step through a sequence of regular expressions
looking for a match.

Note that the parser for a generic :py:class:`Angle`  handles the hemisphere even
though it isn't really meaningful for the abstract superclass.
These should be introduced by the :py:class:`Lat` and :py:class:`Lon` classes.
But, it seems simpler to push it up the parent class.

LatLon
------

This pair of angles defines a point on the surface of a sphere.
The essential problem-domain object is the "point": a (lat, lon) pair.
The main applications will create points from input sources.

Once we have :py:class:`LatLon` objects, we can apply calculations
to determine range and bearing. We can sum the ranges to compute
distance traveled and do other useful things.


Globals
========

We have several global values that are used to determine the units
for range calculations.

..  py:data:: NM

    Mean radius of the earth in nautical miles.
    This is the default;  ranges and bearings are in nautical miles.

..  py:data:: MI

    Mean radius of the earth in statute miles.

..  py:data:: KM

    Mean radius of the earth in kilometers.

"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from math import degrees

from navtools import igrf, olc
import datetime
import numbers
import string
from typing import Optional, Any, overload, Union, cast


# The International Union of Geodesy and Geophysics (IUGG) defined mean radius values
KM = 6371.009  # R in km
MI = 3958.761  # R in mi
NM = 3440.069  # R in nm, better value is 60*180/pi


class AngleParser:
    """Parse a sting representation of a latitude or longitude.

    >>> AngleParser.parse("76.123N")
    76.123
    >>> AngleParser.parse("76.123S")
    -76.123
    >>> AngleParser.parse("Due North") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: Cannot parse 'Due North'
    """

    dms_pat = re.compile(r"(\d+)\D+(\d+)\D+(\d+)[^NEWSnews]*([NEWSnews]?)")
    dm_pat = re.compile(r"(\d+)\D+(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)")
    d_pat = re.compile(r"(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)")
    # This is identical to the dm_pat, above... It may change, however, so
    # navx_dmh_pat = re.compile( r"(\d+)\D+(\d+\.\d+)[^NEWSnews]*([NEWSnews]?)" )

    @staticmethod
    def sign(txt: str) -> int:
        return {"N": +1, "S": -1, "E": +1, "W": -1}.get(txt.upper(), +1)

    @staticmethod
    def parse(value: str) -> float:
        """
        Parses a text value, returning signed degrees as a float value.

        :param value: text to parse
        :returns: float degrees or a :py:exc:`ValueError` exception.
        """

        if d_match := AngleParser.d_pat.match(value):
            deg = float(d_match.group(1))
            return AngleParser.sign(d_match.group(2)) * deg

        elif dm_match := AngleParser.dm_pat.match(value):
            d, m = int(dm_match.group(1)), float(dm_match.group(2))
            return AngleParser.sign(dm_match.group(3)) * (d + m / 60)

        elif dms_match := AngleParser.dms_pat.match(value):
            d, m, s = (
                int(dms_match.group(1)),
                int(dms_match.group(2)),
                float(dms_match.group(3)),
            )
            return AngleParser.sign(dms_match.group(4)) * (d + m / 60 + s / 3600)

        # elif navx_match := AngleParser.navx_dmh_pat.match( value ):
        #     d_f, m_f = float(navx_match.group(1)), float(navx_match.group(2))
        #     return AngleParser.sign(navx_match.group(3))*(d_f + m_f/60)

        else:
            raise ValueError("Cannot parse {0!r}".format(value))


class Angle(float):
    """
    A signed angle in radians; the superclass for Lat and Lon.
    These are relative to the equator or the prime meridian.
    In that sense, they aren't completely generic angles; they're restricted in their
    meaning.

    Currently, we extend ``float``. This leads to the following

        DeprecationWarning: Angle.__float__ returned non-float (type Angle).
        The ability to return an instance of a strict subclass of float is deprecated,
        and may be removed in a future version of Python.

    This suggests we need to switch to a separate class that implements ``numbers.Real``.
    This would "wrap" the internal ``float`` object.

    ::

        class Angle(numbers.Real):
            def __init__(self, value: float) -> None:
                self.value = value
            def __add__(self, other: Any) -> Angle:
                return self.value + cast(Angle, other).value
            etc.

    This class has lots of conversions to DMS.
    A subclass can treat the sign ("h") as the hemisphere,
    using "N", "S", "E", or "W". Lat uses "N"/"S", Lon uses "E"/"W".

    Note that we have to "prettify" some values to
    remove annoying 10E-16 noise bits that arise sometimes.

    >>> import math
    >>> a = Angle(-math.pi/6)
    >>> round(a,3)
    -0.524
    >>> round(a.radians,3)
    -0.524
    >>> round(a.degrees,3)
    -30.0
    >>> round(a.sdeg,3)
    -30.0
    >>> round(a.deg,3)
    -30.0
    >>> a.dm
    (-30, 0.0)
    >>> a.dms
    (-30, 0, 0.0)
    >>> a.h
    '-'
    >>> round(a.r,3)
    -0.524

    **Formatter**.

    >>> fmt, prop = Angle._rewrite("%02.0d° %2.5m'")
    >>> fmt
    "{d:02.0f}° {m:2.5f}'"
    >>> sorted(prop)
    ['d', 'm']
    >>> "Lat: {0:%02.0d° %6.3m'}".format(a)
    "Lat: 30°  0.000'"

    **Another round-off test**.

    >>> a2 = Angle(math.pi/12)
    >>> a2.dms
    (15, 0, 0.0)

    **Math**.

    >>> round(a+a2, 5)
    -0.2618
    >>> round((a+a2).degrees, 3)
    -15.0

    We define the core numeric object special methods, all of which simply appeal to the superclass
    methods for the implementation. The results create new :class:`Angle` objects,
    otherwise, we behave just like a :class:`float`.

    """

    # The default parser for Lat or Lon values.
    parser = AngleParser

    @classmethod
    def fromdegrees(cls, deg: float, hemisphere: Optional[str] = None) -> "Angle":
        """
        Creates an :py:class:`Angle` from a numeric value,
        which must be degrees.

        :param deg: numeric degrees value.
        :param hemisphere: sign value, which can be encoded as
            "N", "S", "E", or "W". If omitted, it's positive.
        :returns: :py:class:`Angle` object.

        >>> a = Angle.fromdegrees(45)
        >>> round(a, 4)
        0.7854
        >>> b = Angle.fromdegrees(23.456, "N")
        >>> round(b, 4)
        0.4094
        """
        if hemisphere in ("N", "E", None):
            sign = +1
        elif hemisphere in ("S", "W"):
            sign = -1
        else:
            raise ValueError(f"Can't create Angle from {deg!r}, {hemisphere!r}")
        return cls(math.radians(sign * deg))

    @classmethod
    def fromdegmin(
        cls, deg: float, min: float, hemisphere: Optional[str] = None
    ) -> "Angle":
        return cls.fromdegrees(deg + min / 60, hemisphere)

    @classmethod
    def fromstring(cls, value: str) -> "Angle":
        """
        Creates an :py:class:`Angle` from a string value,
        which must be represent degrees, either as a simple
        string value, or as a more complex value recognized by
        the :py:class:`AngleParser` class.

        :param deg: string degrees value.
        :param hemisphere: sign value, which can be encoded as
            "N", "S", "E", or "W". If omitted, it's positive.
        :returns: :py:class:`Angle` object.

        We start by assuming the text value is simply
        a string representation of a float.
        If it isn't, we use the :py:class:`AngleParser` class to parse the string.

        A subclass might change the :data:`parser` reference to use a different parser.

        >>> a0 = Angle.fromstring("-77.4325")
        >>> round(a0.degrees,4)
        -77.4325
        >>> a1 = Angle.fromstring("37°28'8\\"N")
        >>> round(a1.degrees,4)
        37.4689

        Note use of prime and double-prime which are preferred over ' and "

        >>> a2 = Angle.fromstring("77°25′57″W")
        >>> round(a2.degrees,4)
        -77.4325
        """

        try:
            deg = float(value)
            return cls(math.radians(deg))
        except ValueError:
            pass
        try:
            deg = cls.parser.parse(value)
            return cls(math.radians(deg))
        except ValueError:
            pass
        raise ValueError(f"Cannot parse {value!r}")

    @classmethod
    def parse(cls, value: str) -> "Angle":
        """Alias for :py:meth:`fromstring`"""
        return cls.fromstring(value)

    @property
    def radians(self) -> float:
        """Angle in radians"""
        return float(self)

    @property
    def r(self) -> float:
        """Angle in radians"""
        return float(self)

    @property
    def degrees(self) -> float:
        """Angle in signed degrees"""
        return math.degrees(self)

    @property
    def sdeg(self) -> float:
        """Angle in signed degrees"""
        return math.degrees(self)

    @property
    def deg(self) -> float:
        """Angle in signed degrees"""
        return math.degrees(self)

    @property
    def dm(self) -> tuple[float, float]:
        """:returns: (d, m) tuple of signed values"""
        sign = -1 if self < 0 else +1
        ad = abs(self.deg)
        d = int(ad)
        ms = 60 * (ad - d)
        if abs(ms - 60) / 60 < 1e-5:
            ms = 0.0
            d += 1
        return d * sign, ms * (sign if d == 0 else 1)

    @property
    def dms(self) -> tuple[float, float, float]:
        """:returns: (d, m, s) tuple of signed values"""
        sign = -1 if self < 0 else +1
        ad = abs(self.deg)
        d = int(ad)
        ms = 60 * (ad - d)
        if abs(ms - 60) / 60 < 1e-5:
            ms = 0.0
            d += 1
        m = int(ms)
        s = round((ms - m) * 60, 3)
        return (
            d * sign,
            m * (sign if d == 0 else 1),
            s * (sign if d == 0 and m == 0 else 1),
        )

    @property
    def h(self) -> str:
        """
        The :meth:`h` property is the sign; the "hemisphere".
        A subclass like :class:`Lat` and :class:`Lon` will
        override this to provide a string instead of an int value.

        :returns: "+" or "-"
        """
        return "-" if self < 0 else "+"

    spec_pat = re.compile(r"%([0-9\.#\+ -]*)([dmshr])")
    formatter = string.Formatter()

    @classmethod
    def _rewrite(cls, spec: str) -> tuple[str, set[str]]:
        """
        Rewrites a "%x" spec into a "{x:fmt}" format.
        Returns the revised format at the set of properties
        used.

        There are several variant cases where we want
        different kinds of display values:

        -   ``%d %m %s`` means that degrees and minutes are integer values.

        -   ``%d %m`` means that degrees is an int and m is a float.

        -   ``%d`` means that degrees is a float.

        To make this work, we note the pattern of  ``{'d', 'm', 's'}``, or ``{'d', 'm'}``, or ``{'d'}``
        and determine the appropriate mix of int or float values to include.
        """
        if spec is None or spec == "" or spec == "s":
            return "{d:f}", {"d"}
        else:
            used: set[str] = set()
            m = cls.spec_pat.search(spec)
            # pattern group 0 is the detailed spec
            # pattern group 1 is the 1-letter property (d, m, s, h, or r)
            while m:
                # Rewrite this item in the spec.
                fmt, prop = m.groups()
                spec = cls.spec_pat.sub(
                    "{{{prop}:{fmt}{tp}}}".format(
                        prop=prop, fmt=fmt, tp="s" if prop == "h" else "f"
                    ),
                    spec,
                    count=1,
                )
                used.add(prop)
                # "Recursively" check for more items.
                m = cls.spec_pat.search(spec)
        return spec, used

    def __format__(self, spec: str = "") -> str:
        """
        Formatted string representation of an Angle.

        The specification uses a number of ``%{fmt}{prop}`` items. The ``{fmt}`` is a floating-point
        style specification, for example ``03.0``.  The ``{prop}`` is the
        property name:  ``%d``, ``%m`` and ``%s`` to show
        degrees, minutes, and seconds. Additional properties include ``%r``
        to show radians and ``%h`` to show the hemisphere ("N", "S", "E", or "W" are
        representations of the sign).

        This can lead to a fairly complex format specifications.
        A format request can look like this: ``"Lat: {0:%02d° %06.3m'}".format(lat)``
        Or perhaps this: ``"({0:%.5d}, {1:%.5d})".format(lat, lon)``

        We have an internal function, :meth:`_rewrite()`, which will parse a format specification
        and then rebuild the format spec into something a bit more useful.
        Once the format has been rewritten we can use the :class:`string.Formatter`
        to build the resulting output.

        :class spec: format specification for this value.
        :returns: text representation of this :class:`Angle`.
        :meta public:
        """
        fmt_str, prop_set = self._rewrite(spec)
        data = dict(h=self.h, r=self.radians)
        if {"d", "m", "s"} <= prop_set:
            data["d"], data["m"], data["s"] = Angle(abs(self)).dms
        elif {"d", "m"} <= prop_set and not {"s"} <= prop_set:
            data["d"], data["m"] = Angle(abs(self)).dm
        elif {"d"} <= prop_set and not {"m", "s"} <= prop_set:
            data["d"] = abs(self.degrees)
        return self.formatter.format(fmt_str, **data)

    def __add__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__add__(other))

    def __sub__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__sub__(other))

    def __mul__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__mul__(other))

    def __truediv__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__truediv__(other))

    def __floordiv__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__floordiv__(other))

    def __mod__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__mod__(other))

    def __pow__(self, other: Any, mod: None = None) -> float:
        """:meta public:"""
        return super().__pow__(other)

    def __radd__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__radd__(other))

    def __rsub__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__rsub__(other))

    def __rmul__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__rmul__(other))

    def __rtruediv__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__rtruediv__(other))

    def __rfloordiv__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__rfloordiv__(other))

    def __rmod__(self, other: Any) -> "Angle":
        """:meta public:"""
        return Angle(super().__rmod__(other))

    def __rpow__(self, other: Any, mod: None = None) -> float:
        """:meta public:"""
        return super().__rpow__(other)

    def __abs__(self) -> "Angle":
        """:meta public:"""
        return Angle(super().__abs__())

    def __float__(self) -> float:
        """:meta public:"""
        return self

    @overload
    def __round__(self, ndigits: None = None) -> int:
        ...  # pragma: no cover

    @overload
    def __round__(self, ndigits: int) -> float:
        ...  # pragma: no cover

    def __round__(self, ndigits: Optional[int] = None) -> Union[int, float]:
        """:meta public:"""
        if ndigits is None:
            return super().__round__()
        return super().__round__(ndigits)

    def __neg__(self) -> "Angle":
        """:meta public:"""
        return Angle(super().__neg__())

    def __pos__(self) -> "Angle":
        """:meta public:"""
        return self

    def __eq__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__eq__(other)

    def __ne__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__ne__(other)

    def __le__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__le__(other)

    def __lt__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__lt__(other)

    def __ge__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__ge__(other)

    def __gt__(self, other: Any) -> bool:
        """:meta public:"""
        return super().__gt__(other)

    def __hash__(self) -> int:
        """:meta public:"""
        return super().__hash__()


class Lat(Angle):
    """Latitude Angle, normal to the equator.

    Hemisphere text of "N" and "S".
    Two digits as the default format for degrees.

    >>> a = Lat.fromdegrees(37.1234)
    >>> repr(a)
    '37°07.404′N'
    >>> b = Lat.fromstring('37°07.404′N')
    >>> round(b.degrees,4)
    37.1234
    """

    @classmethod
    def fromdegrees(cls, deg: float, hemisphere: Optional[str] = None) -> "Lat":
        return Lat(super().fromdegrees(deg, hemisphere))

    @classmethod
    def fromstring(cls, value: str) -> "Lat":
        return Lat(super().fromstring(value))

    @property
    def d(self) -> float:
        """:returns: Latitude in degrees."""
        return abs(super().deg)

    @property
    def h(self) -> str:
        """:returns: The hemisphere, "N" or "S"."""
        return "S" if self < 0 else "N"

    def __repr__(self) -> str:
        return "{0:%02.0d°%06.3m′%h}".format(self)

    @property
    def north(self) -> float:
        """
        :returns: North latitude, positive "co-latitude".
            Range is 0 to pi instead of -pi/2 to +pi/2.
        """
        return self + math.pi / 2


class Lon(Angle):
    """Longitude Angle, parallel to the equator

    Hemisphere text of "E" and "W".
    Three digits as the default format for degrees.

    >>> a = Lon.fromdegrees(-76.5678)
    >>> repr(a)
    '076°34.068′W'
    >>> b = Lon.fromstring('076°34.068′W')
    >>> round(b.degrees,4)
    -76.5678
    """

    @classmethod
    def fromdegrees(cls, deg: float, hemisphere: Optional[str] = None) -> "Lon":
        return Lon(super().fromdegrees(deg, hemisphere))

    @classmethod
    def fromstring(cls, value: str) -> "Lon":
        return Lon(super().fromstring(value))

    @property
    def d(self) -> float:
        """:returns: Longitude in degrees."""
        return abs(super().deg)

    @property
    def h(self) -> str:
        """:returns: The hemisphere, "E" or "W"."""
        return "W" if self < 0 else "E"

    def __repr__(self) -> str:
        return "{0:%03.0d°%06.3m′%h}".format(self)

    @property
    def east(self) -> float:
        """:returns: East longitude. Positive only."""
        return (self + math.pi * 2) % (math.pi * 2)


class LatLon:
    """A latitude/longitude coordinate pair.
    This is a glorified namedtuple with additional properties to
    provide nicely-formatted results.

    This includes input and output conversions.

    Output conversions as degree-minute-second, degree-minute, and degree.
    We return a tuple of two strings so that the application can use
    these values to populate separate spreadsheet columns.

    :ivar lat: The latitude :py:class:`Lat`.
    :ivar lon: The longitude :py:class:`Lon`.
    :ivar dms: A pair of DMS strings.
    :ivar dm: A pair of DM strings.
    :ivar d: A pair of D strings.
    """

    def __init__(
        self, lat: Union[Lat, Angle, float, str], lon: Union[Lon, Angle, float, str]
    ) -> None:
        """Build a LatLon from two values.

        :param lat: the latitude, used to build an Angle. A float is presumed to be in degrees.
        :param lon: the longitude, used to build an Angle. A float is presumed to be in degrees.
        """
        if isinstance(lat, Lat):
            self.lat = lat
        elif isinstance(lat, Angle):
            self.lat = Lat(lat)
        elif isinstance(lat, float):
            self.lat = Lat.fromdegrees(lat)
        elif isinstance(lat, str):
            self.lat = Lat.fromstring(lat)
        else:
            raise ValueError("Can't convert {0!r}".format(lat))
        if isinstance(lon, Lon):
            self.lon = lon
        elif isinstance(lon, Angle):
            self.lon = Lon(lon)
        elif isinstance(lon, float):
            self.lon = Lon.fromdegrees(lon)
        elif isinstance(lon, str):
            self.lon = Lon.fromstring(lon)
        else:
            raise ValueError("Can't convert {0!r}".format(lon))

    lat_dms_format = "{0:%02.0d %02.0m %04.1s%h}"
    lon_dms_format = "{0:%03.0d %02.0m %04.1s%h}"
    lat_dm_format = "{0:%02.0d %.3m%h}"
    lon_dm_format = "{0:%03.0d %.3m%h}"
    lat_d_format = "{0:%06.3d%h}"
    lon_d_format = "{0:%07.3d%h}"

    @property
    def dms(self) -> tuple[str, str]:
        """Long Degree Minute Second format.

        :returns: A pair of strings of the form :samp:`{ddd} {mm} {s.s}{h}`
        """
        lat = LatLon.lat_dms_format.format(self.lat)
        lon = LatLon.lon_dms_format.format(self.lon)
        return (lat, lon)

    @property
    def dm(self) -> tuple[str, str]:
        """GPS-friendly Degree Minute format.

        :returns: A pair of strings of the form :samp:`{ddd} {m.mmm}{h}`
        """
        lat = LatLon.lat_dm_format.format(self.lat)
        lon = LatLon.lon_dm_format.format(self.lon)
        return (lat, lon)

    @property
    def d(self) -> tuple[str, str]:
        """GPS-friendly Degree format.

        :returns: A pair of strings of the form :samp:`{ddd.ddd}{h}`
        """
        lat = LatLon.lat_d_format.format(self.lat)
        lon = LatLon.lon_d_format.format(self.lon)
        return (lat, lon)

    def __str__(self) -> str:
        return f"{self.lat!s} {self.lon!s}"

    def __repr__(self) -> str:
        return f"LatLon({self.lat!r}, {self.lon!r})"

    def near(self, other: "LatLon", R: float = NM) -> float:
        """
        Distance from another point.
        This can be expensive to compute, a geocode
        to do proximity tests can be more efficient.
        """
        r, b = range_bearing(self, other, R=R)
        return r


def range_bearing(p1: LatLon, p2: LatLon, R: float = NM) -> tuple[float, Angle]:
    """Rhumb-line course from :py:data:`p1` to :py:data:`p2`.

    See :ref:`calc.range_bearing`.
    This is the equirectangular approximation.
    Without even the minimal corrections for non-spherical Earth.

    :param p1: a :py:class:`LatLon` starting point
    :param p2: a :py:class:`LatLon` ending point
    :param R: radius of the earth in appropriate units;
        default is nautical miles.
        Values include :py:data:`KM` for kilometers,
        :py:data:`MI` for statute miles and :py:data:`NM` for nautical miles.
    :returns: 2-tuple of range and bearing from p1 to p2.

    """
    d_NS = R * (p2.lat.radians - p1.lat.radians)
    d_EW = (
        R
        * math.cos((p2.lat.radians + p1.lat.radians) / 2)
        * (p2.lon.radians - p1.lon.radians)
    )
    d = math.hypot(d_NS, d_EW)
    tc = math.atan2(d_EW, d_NS) % (2 * math.pi)
    theta = Angle(tc)
    return d, theta


def destination(p1: LatLon, range: float, bearing: float, R: float = NM) -> LatLon:
    """Rhumb line destination given point, range and bearing.

    See :ref:`calc.destination`.

    :param p1: a :py:class:`LatLon` starting point
    :param range: the distiance to travel.
    :param bearing: the direction of travel in degrees.
    :param R: radius of the earth in appropriate units;
        default is nautical miles.
        Values include :py:data:`KM` for kilometers,
        :py:data:`MI` for statute miles and :py:data:`NM` for nautical miles.
    :returns: a :py:class:`LatLon` with the ending point.
    """
    d = range / R
    theta = math.radians(bearing)
    lat1 = p1.lat.radians
    lon1 = p1.lon.radians
    lat2 = lat1 + d * math.cos(theta)
    # check for some daft bugger going past the pole, normalize latitude if so
    if abs(lat2) > math.pi / 2:
        lat2 = math.pi - lat2 if lat2 > 0 else -(math.pi - lat2)
    dLat = lat2 - lat1
    if abs(dLat) < 1.0e-6:
        q = math.cos(lat1)
    else:
        dPhi = math.log(
            math.tan(lat2 / 2 + math.pi / 4) / math.tan(lat1 / 2 + math.pi / 4)
        )
        q = dLat / dPhi

    dLon = d * math.sin(theta) / q
    lon2 = ((lon1 + dLon + math.pi) % (2 * math.pi)) - math.pi

    return LatLon(Lat(lat2), Lon(lon2))


def declination(point: LatLon, date: Optional[datetime.date] = None) -> float:
    """Computes standard declination for a given :py:class:`LatLon`
    point.

    http://www.ngdc.noaa.gov/geomag/models.shtml

    http://www.ngdc.noaa.gov/IAGA/vmod/igrf.html

    See :ref:`igrf` for details.

    :param point: LatLon point
    :param date: :py:class:`datetime.date` in question, default is today.
    :returns: declination as a float offset to an Angle.
    """
    # print( "declination: {0!r} {1!r}".format(point.lat, point.lon) )

    if date is None:
        date = datetime.datetime.today()
    first_of_year = date.replace(month=1, day=1)
    astro_dt_tm = date.year + (date.toordinal() - first_of_year.toordinal()) / 365.242

    x, y, z, f = igrf.igrfsyn(astro_dt_tm, point.lat, point.lon.east)
    decl = math.atan2(y, x)  # Declination
    return decl


@dataclass(eq=True, unsafe_hash=True)
class Waypoint:
    """
    A waypoint.

    This is the destination of a Leg of a Route.
    This is the location, name, and description for a plotted waypoint.
    """

    lat: Lat
    lon: Lon
    name: Optional[str] = None
    description: Optional[str] = None
    point: LatLon = field(init=False, compare=False)
    geocode: str = field(init=False, compare=True)

    def __post_init__(self) -> None:
        self.point = LatLon(self.lat, self.lon)
        self.geocode = olc.OLC().encode(degrees(self.lat), degrees(self.lon))


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod()

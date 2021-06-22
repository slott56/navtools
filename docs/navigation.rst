###############################################################
:mod:`navtools.navigation` -- Navigation Calculations
###############################################################
.. include:: <isonum.txt>

The :py:mod:`navtools.navigation` module computes range and bearing between two points.
It leverages the :py:mod:`navtools.igrf` module to compute compass bearing from
true bearing.

See the Aviation Formulary: http://edwilliams.org/avform147.htm for a number of useful formulae
and examples.

Also see http://www.movable-type.co.uk/scripts/latlong.html, |copy| 2002-2010 Chris Veness.

..  _`calc.range_bearing`:

Distance/Bearing Calculation
===============================

These are based on the equirectangular approximation for distance.
This the loxodrome or rhumb line.

See http://edwilliams.org/avform147.htm#flat.

Generally,
the :math:`\phi` values are N-S latitude, and :math:`\lambda` values are E-W longitude.

This means :math:`(\phi_0, \lambda_0)` and :math:`(\phi_1, \lambda_1)`
are the two points we're navigating between.

The distance, :math:`d`, is given by the following computation:

..  math::

    x &= R \times \Delta \lambda \times \cos \frac{\Delta \phi}{2} \\
    y &= R \times \Delta \phi \\
    d &= \sqrt{x^2 + y^2}

We *could* fine-tune this with :math:`R_y` and :math:`R_x` radius
of curvature values. We don't need answers closer than 10%, so we skip this
in the implementation.

The implementation does not compute the :math:`R_y`  flattening effect on the north-south component of a distance;
nor does it compute the :math:`R_x` flattening effect on east-west component of a distance.

..  math::

    R_y &= a \times \frac{1-e^2}{\bigl(1 - e^2 \times \sin(\phi_0)^2\bigr)^\frac{3}{2}} \\
    R_x &= a \times \frac{1}{\sqrt{1 - e^2 \times \sin(\phi_0)^2}}

Where

``a`` is the equatorial radius of the earth:

- a=6378.137000 km for WGS84
- a=3958.761 miles
- a=3440.069 nautical miles, but 180*60/pi can be more useful.


``e^2=f*(2-f)`` is the eccentricity, a function of the flattening factor, f=1/298.257223563, for WGS84.

..  math::

    e^2 = f\times(2-f) = 0.0066943799901413165

See https://en.wikipedia.org/wiki/World_Geodetic_System for more details.


The bearing, :math:`\theta` is given by this formula.

..  math::

    \theta = \arctan \frac{x} {y} \mod 2 \pi

Example
----------

Suppose point 1 is LAX: (33deg 57min N, 118deg 24min W)

Suppose point 2 is JFK: (40deg 38min N,  73deg 47min W)

d = 0.629650 radians = 2164.6 nm
theta = 1.384464 radians = 79.32 degrees

Conversely,
2164.6nm (0.629650 radians) on a rhumbline course of 79.3 degrees (1.384464 radians) starting at LAX
should arrive at JFK.

..  _`calc.destination`:

Destination Calculation
========================

This is the direct Rhumb-line formula.
From :math:`(\phi_1, \lambda_1)` in direction :math:`\theta` for distance :math:`d`.

Generally,
the :math:`\phi` values are N-S latitude, and :math:`\lambda` values are E-W longitude.

The steps:

1.  Compute new latitude.

    ..  math::

        \phi_d =  \phi_1 + d \cos \theta

2.  Sanity Check.

    ..  math::

        \lvert \phi_d \rvert \leq \frac{\pi}{2}

3.  How much northing? Too little? We're on an E-W line and a simplification avoids
    a fraction with terms near zero. A lot? We're not an a simple E-W line.

    ..  math::

        q = \begin{cases}
        \cos \phi_1 &\textbf{if $\lvert \phi_d - \phi_1 \rvert < \sqrt{\epsilon}$} \\
        \phi_d - \phi_1 / \log {\dfrac{\tan(\tfrac{\phi_d}{2}+\tfrac{\pi}{4})}{\tan(\tfrac{\phi_1}{2}+\tfrac{\pi}{4})}}  &\textbf{otherwise}
        \end{cases}

4.  Compute new Longitude

    ..  math::

        \Delta \lambda &= d \times \frac{\sin(\theta)}{q} \\
        \lambda_d &= (\lambda_1 + \Delta \lambda + \pi \mod 2\pi) - \pi

Implementation
==============

Here's the UML overview of this module.

..  uml::

    @startuml
    'navtools.navigation'
    allow_mixing

    component navigation {

        class AngleParser {
            {static} sign(str) : int
            {static} parse(str) : str
        }

        class float

        class Angle {
            {static} fromstring(str) : str
        }

        float <|-- Angle

        Angle --> AngleParser

        class Lat

        class Lon

        Angle <|-- Lat
        Angle <|-- Lon

        class LatLon {
            lat : Lat
            lon : Lon
        }

        LatLon::lat -- Lat
        LatLon::lon -- Lon
    }

    component igrf

    navigation ..> igrf

    @enduml

..  py:module:: navtools.navigation

AngleParser
-----------

..  autoclass:: AngleParser
    :members:
    :undoc-members:

Angle class hierarchy
---------------------

The superclass, :py:class:`navtools.navigation.Angle`.

..  autoclass:: Angle
    :members:
    :undoc-members:

The Latitude subclass, :py:class:`navtools.navigation.Lat`.

..  autoclass:: Lat
    :members:

The Longitude subclass, :py:class:`navtools.navigation.Lon`.

..  autoclass:: Lon
    :members:

LatLon point
------------

..  autoclass:: LatLon
    :members:

Globals
-------

..  py:data:: KM
..  py:data:: MI
..  py:data:: NM

range and bearing
-----------------

..  autofunction:: range_bearing

destination
-----------

..  autofunction:: destination

declination (or variance)
-------------------------

..  autofunction:: declination


Historical Archive
==================

The original :py:class:`Angle` and :py:class:`GlobeAngle` classes do things which are close
to correct. They included some needless complexity, however.
They worked in degrees (not radians) and implemented a lot of operations that could
have been inherited from ``float``.


Angle class -- independent of float
-----------------------------------

An :py:class:`Angle` is a signed radians number, essentially equivalent
to ``float``. The operators are include the flexibility to work with
``float`` values, doing coercion to :py:class:`Angle`.

::

    class Angle(numbers.Real):
        """
        An Angle, with conversion from several DMS notations,
        as well as from radians.  The angle can be reported as
        degrees, a (D, M, S) tuple or as a value in radians.

        :ivar deg: The angle in degrees.

        :ivar radians: The angle in radians

        :ivar dm: The angle as a (D, M) tuple

        :ivar dms: The angle as a (D, M, S) tuple

        :ivar tail: Any additional text found after parsing a string value.
                This may be a hemisphere indication that a subclass might want to use.
        """

        dms_pat= re.compile( r"(\d+)\s+(\d+)\s+(\d+)(.*)" )
        dm_pat= re.compile( r"(\d+)\s+(\d+\.\d+)(.*)" )
        d_pat= re.compile( r"(\d+\.\d+)(.*)" )
        navx_dmh_pat= re.compile( "(\\d+)\\D+(\\d+\\.\\d+)'([NEWS])" )

        @staticmethod
        def from_radians( value ):
            """Create an Angle from radians.

            :param value: Angle in radians.

            Generally used like this::

                a = Angle.from_radians( float )
            """
            return Angle( 180 * value / math.pi )

        def __init__( self, value ):
            """Create an Angle from an Angle, float or string degrees.

            :param value: Angle in degrees as Angle, float or string.
            """
            self.tail= None
            if isinstance(value,Angle):
                self.deg= value.deg
                return
            if isinstance(value,float):
                self.deg= value
                return
            dms= Angle.dms_pat.match( value )
            if dms:
                d, m, s = int(dms.group(1)), int(dms.group(2)), float(dms.group(3))
                self.deg= d + m/60 + s/3600
                self.tail= dms.group(4)
                return
            dm= Angle.dm_pat.match( value )
            if dm:
                d, m = int(dm.group(1)), float(dm.group(2))
                self.deg= d + m/60
                self.tail= dm.group(3)
                return
            d= Angle.d_pat.match( value )
            if d:
                self.deg = float(d.group(1))
                self.tail= d.group(2)
                return
            navx= Angle.navx_dmh_pat.match( value )
            if navx:
                d, m = float(navx.group(1)), float(navx.group(2))
                self.deg= d + m/60
                self.tail= navx.group(3)
                return
            raise TypeError( "Cannot parse Angle {0!r}".format(value) )

        @property
        def radians( self ):
            """Returns the angle in radians.

            :returns: angle in radians.
            """
            return math.pi * self.deg / 180
        @property
        def dm( self ):
            """Returns the angle as (D, M).

            :returns: (d, m) tuple
            """
            sign= -1 if self.deg < 0 else +1
            ad= abs(self.deg)
            d= int(ad)
            ms= ad-d
            return d*sign, 60*ms*(sign if d == 0 else 1)
        @property
        def dms( self ):
            """Returns the angle as (D, M, S).

            :returns: (d, m, s) tuple
            """
            sign= -1 if self.deg < 0 else +1
            ad= abs(self.deg)
            d= int(ad)
            ms= 60*(ad-d)
            m= int(ms)
            s= round((ms-m)*60,3)
            return d*sign, m*(sign if d == 0 else 1), s*(sign if d==0 and m==0 else 1)
        def __repr__( self ):
            return "Angle( {0.deg!r} )".format( self )
        def __str__( self ):
            return "{0.deg:7.3f}".format( self )

        def __add__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg + other.deg )
            elif isinstance(other,float):
                return Angle( self.deg + other )
            else:
                return NotImplemented
        def __sub__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg - other.deg )
            elif isinstance(other,float):
                return Angle( self.deg - other )
            else:
                return NotImplemented
        def __mul__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg * other.deg )
            elif isinstance(other,float):
                return Angle( self.deg * other )
            else:
                return NotImplemented
        def __div__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg / other.deg )
            elif isinstance(other,float):
                return Angle( self.deg / other )
            else:
                return NotImplemented
        def __truediv__( self, other ):
            return self.__div__( self, other )
        def __floordiv__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg // other.deg )
            elif isinstance(other,float):
                return Angle( self.deg // other )
            else:
                return NotImplemented
        def __mod__( self, other ):
            if isinstance(other,Angle):
                return Angle( self.deg % other.deg )
            elif isinstance(other,float):
                return Angle( self.deg % other )
            else:
                return NotImplemented

        def __abs__( self ):
            return Angle( abs(self.deg) )
        def __float__( self ):
            return self.deg
        def __trunc__( self ):
            return Angle( trunc(self.deg) )
        def __ceil__( self ):
            return Angle( math.ceil( self.deg ) )
        def __floor__( self ):
            return Angle( math.floor( self.deg ) )
        def __round__( self, ndigits ):
            return Angle( round( self.deg, ndigits=0 ) )
        def __neg__( self ):
            return Angle( -self.deg )
        def __pos__( self ):
            return self
        def __eq__( self, other ):
            return self.deg == other.deg
        def __ne__( self, other ):
            return self.deg != other.deg
        def __le__( self, other ):
            return self.deg <= other.deg
        def __lt__( self, other ):
            return self.deg < other.deg
        def __ge__( self, other ):
            return self.deg >= other.deg
        def __gt__( self, other ):
            return self.deg > other.deg
        def __pow__( self, other ):
            return Angle( self.deg**other )

        def __radd__( self, other ):
            return other+self
        def __rdiv__( self, other ):
            return NotImplemented
        def __rfloordiv__( self, other ):
            return NotImplemented
        def __rmod__( self, other ):
            return NotImplemented
        def __rmul__( self, other ):
            return other*self
        def __rpow__( self, other ):
            return NotImplemented
        def __rtruediv__( self, other ):
            return NotImplemented

Old GlobeAngle Class
--------------------

We need to extend the simple :py:class:`Angle` to include globe hemisphere
information so that the simple angle (in degrees or radians)
can be parsed and presented in proper N, S, E and W hemisphere
notation.


..  important:: This doesn't handle signs properly.

    Note that we do not handle sign well as a conversion from a string.
    This is because this angle is axis-independent.  Since it isn't
    aware of being a longitude or a latitude, it doesn't know which
    hemisphere code to use.

::

    class GlobeAngle( Angle ):
        """An Angle which includes hemisphere information: N, S, E or W.

        :ivar deg: The angle in degrees.

        :ivar radians: The angle in radians

        :ivar dm: The angle as a (D, M) tuple

        :ivar dms: The angle as a (D, M, S, H) tuple

        :ivar hemi: The hemisphere ("N", "S", "E" or "W")
        """

        def _hemisphere( self, hemi, debug=None ):
            if len(hemi) == 1:
                self.hemi= hemi
            elif len(hemi) == 2:
                self.hemi= hemi[0 if self.deg >= 0 else 1]
            else:
                raise TypeError( "Cannot parse GlobeAngle{0!r}".format(debug) )

        def __init__( self, value, hemi=None ):
            """Create a GlobeAngle from an GlobeAngle, Angle or float degrees.
            This will delegate construction to Angle for parsing the
            various strings that could be present. An Angle string may
            include a "tail" of N, S, E or W, making the hemisphere
            irrelevant.

            :param value: Angle in degrees as :py:class:`Angle`,
                :py:class:`GlobeAngle`, float or string.
                The string parsing is delegated to :py:class:`Angle`.

            :param hemi: The hemisphere label ('N', 'S', 'E' or 'W')
                Or.
                In the case of Angle or Float, this is the set of hemisphere
                alternatives. For Latitude provide "NS"; for Longitude provide "EW".
                This must be folded into an Angle or a float value.
                Positive Angle or float means N or E.
                Negative Angle or float means S or W.
            """
            if isinstance(value,GlobeAngle):
                self.deg= value.deg
                self.hemi= value.hemi
                return
            if isinstance(value,Angle):
                self.deg= value.deg
                self._hemisphere( hemi, debug=(value,hemi) )
                return
            if isinstance(value,float) and hemi is not None:
                self.deg= value
                self._hemisphere( hemi, debug=(value,hemi) )
                return
            # String parsing.
            angle= Angle( value )
            self.deg= angle.deg
            if angle.tail and angle.tail[0].upper() in ("N","S","E","W"):
                self.hemi= angle.tail[0].upper()
                return
            self._hemisphere( hemi, debug=(value,hemi) )

        @property
        def radians( self ):
            """Returns the angle in radians with appropriate sign based on hemisphere.
            W and S are negative values.

            :returns: angle in radians.
            """
            if self.hemi in ("W","S"):
                return -super(GlobeAngle,self).radians
            return super(GlobeAngle,self).radians
        @property
        def dms( self ):
            """Returns the angle as a (D, M, S, Hemisphere).

            :return: (d, m, s, hemisphere) 4-tuple.
            """
            return super(GlobeAngle,self).dms + ( self.hemi, )
        @property
        def sdeg( self ):
            """Returns a signed angle: positive N or E, negative S or W."""
            if self.hemi in ("S", "W"):
                return -self.deg
            return self.deg
        def __str__( self ):
            return str(self.deg)+self.hemi

Old Rhumb-Line Range and Bearing
--------------------------------

This is *not* what we're using. This is an alternative that uses
a more sophsticated Rhumb line computation. The increased accuracy
isn't important enough to use.


::

    def range_bearing(p1: LatLon, p2: LatLon, R: float = NM) -> Tuple[float, float]:
        lat1 = p1.lat.radians
        lat2 = p2.lat.radians
        dLat = lat2 - lat1
        dPhi = math.log(math.tan(lat2/2+math.pi/4)/math.tan(lat1/2+math.pi/4))
        if abs(dPhi) < 1.0E-6:
            q = math.cos(lat1)
        else:
            q = dLat/dPhi
        lon1 = p1.lon.radians
        lon2 = p2.lon.radians
        dLon = lon2 - lon1
        if abs(dLon) > math.pi:
            dLon = -(2*math.pi-dLon) if dLon > 0 else (2*math.pi+dLon)
        d = math.sqrt(dLat*dLat + q*q*dLon*dLon) * R
        brng = math.atan2(dLon, dPhi)
        if brng < 0:
            brng = 2*math.pi+brng
        theta = Angle(brng)
        return d, theta

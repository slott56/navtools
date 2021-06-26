########################################
:py:mod:`solar` -- Sunrise and Sunset
########################################

This module computes sunrise and sunset.

See https://en.wikipedia.org/wiki/Sunrise_equation

https://gml.noaa.gov/grad/solcalc/calcdetails.html

Also see https://gml.noaa.gov/grad/solcalc/solareqns.PDF.
This uses the deprecated Spencer equations https://www.mail-archive.com/sundial@uni-koeln.de/msg01050.html.
It appears the Fourier Transform approximations are no longer considered accurate enough.
Also, this paper seems to have a number of small errors in it. (See "cost", for example.)

Also see https://gml.noaa.gov/grad/solcalc/sunrise.html which seems to produce
different, more accurate results. The associated Excel spreadsheet seems more
useful because it seems to be the preferred approach and provides test data.


Generally,
the :math:`\phi` values are N-S latitude, and :math:`\lambda` values are E-W longitude.

The procedure is as follows:

1.  D is the given date as an ordinal number after 1900.
    The spreadsheet representation of dates provides a helpful approximation.
    ``date - (1900-1-1) + 2``.

2.  E is the time past midnight as a float in minutes.

3.  F is the Julian day number.

4.  G is the Julian century.
    :math:`\frac{F - 2451545}{36525}`

5.  I is the sun's geometric mean longitude (in degrees).
    :math:`280.46646 + G(36000.76983 + 0.0003032 G) \mod 360`

6.  J is the sun's geometric mean anomaly (in degrees).
    :math:`357.52911 + 35999.05029 G - 0.0001537 G^2`

7.  K is the eccentricity of earth's orbit.
    :math:`0.016708634 - 0.000042037 G + 0.0000001267 G^2`

#.  L is the sun's equation of center.
    :math:`(1.914602 - 0.004817 G + 0.000014 G^2) \sin J + (0.019993 - 0.000101 G) \sin 2 J + 0.000289 \sin 2 J`

#.  M is the sun's true longitude (in degrees),
    :math:`I + L`.

#.  N is the sub's true anomaly (in degrees),
    :math:`J + L`.

#.  (Not required, but in the original spreadsheet anyway.) O is the sun's radius vector (in Astronomical Units).
    :math:`\frac{1.000001018 (1 - K^2)}{1 + K \cos(N)}`

#.  P is the sun's apparent longitude (in degrees).
    :math:`M - 0.00569 - 0.00478 \sin (125.04 - 1934.136 G)\frac{\pi}{180}`

#.  Q is the mean obliquity to the ecliptic (in degrees).
    :math:`23 + \frac{26}{60} + \frac{21.448 - 46.815 G + 0.00059 G^2 - 0.001813 G^3}{3600}`


#.  R is the obliquity correction (degrees). :math:`Q + 0.00256 \cos(125.04 - 1934.136 G) \frac{\pi}{180}`

#.  S is the sun's right ascension (degrees). :math:`\arctan \frac{\cos R \sin P} {\cos P}`

#.  T is the sun's declination (degrees). :math:`\arcsin (\sin R \sin P)`

#.  U is the "variable Y". :math:`\tan^2 \frac{R}{2}`. This is referenced as :math:`y` in several
    variations. See https://ui.adsabs.harvard.edu/abs/1989MNRAS.238.1529H/abstract for an example.

#.  V is the "Equation" of time (in minutes) how apparent time equates to measured time.
    :math:`4 U \sin(2I) - 2K\sin J + 4KU\sin J \cos 2I - 0.5 U^2 \sin 4I - 1.25 K^2 \sin 2J`

#.  W is the Hour Angle of Sunrise (degrees)
    :math:`\arccos (\frac{\cos 90.833}{\cos \phi \cos T} - \tan \phi \tan T)`

#.  X is Solar Noon in Local Standard Time.
    :math:`\frac{720 - 4 \lambda - V + t}{1440}`

#.  Y is sunrise. :math:`X - 4 W / 1440`.

#.  Z is sunset. :math:`X + 4 W / 1440`.


Twilight
========

Computing nautical twilight is Solar zenith angle is 102°, solar elevation angle is -12°.
This is 12° beyond the horizon.

For some information, see http://www.stargazing.net/kepler/sunrise.html

This appears to be an offset to the Hour Angle of sunrise. The following
uses 90.833 as the horizon with a correction for refraction of the atmosphere:

..  math::

    W = \arccos \left[ \frac{\cos 90.833}{\cos {\phi} \cos T} - \tan{\phi}\tan T \right]

If so, then Nautical twilight could be:

..  math::

    W_n = \arccos \left[ \frac{\cos 102}{\cos {\phi} \cos T} - \tan{\phi}\tan T \right]

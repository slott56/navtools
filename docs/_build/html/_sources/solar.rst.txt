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
Also, the final time requires a time zone offet, :math:`t`, to convert to local time,
and account for savings vs. daylight time.

The procedure is as follows:

1.  D is the given date as an ordinal number after 1900.
    The spreadsheet representation of dates provides a helpful approximation.
    ``date - (1900-1-1) + 2``.

2.  E is the time past midnight of D as a float, in minutes.

3.  F is the Julian day number.  (:math:`t` is the timezone offset, in hours.)

    ..  math::

        F = D + 2415018.5 + E - \frac{t}{24}

4.  G is the Julian century.

    ..  math::

        G = \frac{F - 2451545}{36525}

5.  I is the sun's geometric mean longitude (in degrees).

    ..  math::

        I = (280.46646 + 36000.76983 G + 0.0003032 G^2) \mod 360

6.  J is the sun's geometric mean anomaly (in degrees).

    ..  math::

        J = 357.52911 + 35999.05029 G - 0.0001537 G^2

7.  K is the eccentricity of earth's orbit.

    ..  math::

        K  = 0.016708634 - 0.000042037 G + 0.0000001267 G^2

#.  L is the sun's equation of center.

    ..  math::

        L = (1.914602 - 0.004817 G + 0.000014 G^2) \sin J + (0.019993 - 0.000101 G) \sin 2 J + 0.000289 \sin 2 J

#.  M is the sun's true longitude (in degrees),
    :math:`M = I + L`.

#.  N is the sub's true anomaly (in degrees),
    :math:`M = J + L`.

#.  (Not required, but is in the original spreadsheet.) O is the sun's radius vector (in Astronomical Units).

    ..  math::

        O = \frac{1.000001018 (1 - K^2)}{1 + K \cos N}

#.  P is the sun's apparent longitude (in degrees).

    ..  math::

        P = M - 0.00569 - 0.00478 \sin (125.04 - 1934.136 G)\frac{\pi}{180}

#.  Q is the mean obliquity to the ecliptic (in degrees).

    ..  math::

        Q = 23 + \frac{26}{60} + \frac{21.448 - 46.815 G + 0.00059 G^2 - 0.001813 G^3}{3600}

#.  R is the obliquity correction (degrees).

    ..  math::

        R = Q + 0.00256 \cos(125.04 - 1934.136 G) \frac{\pi}{180}

#.  S is the sun's right ascension (degrees).

    ..  math::

        S = \arctan \frac{\cos R \sin P} {\cos P}

#.  T is the sun's declination (degrees).

    ..  math::

        T = \arcsin (\sin R \sin P)

#.  U is the "variable Y". This is referenced as :math:`y` in several
    variations. See https://ui.adsabs.harvard.edu/abs/1989MNRAS.238.1529H/abstract for an example.

    ..  math::

        U = \tan^2 \frac{R}{2}

#.  V is the "Equation" of time (in minutes) how apparent time equates to measured time.

    ..  math::

        V = 4 U \sin(2I) - 2K\sin J + 4KU\sin J \cos 2I - 0.5 U^2 \sin 4I - 1.25 K^2 \sin 2J

#.  W is the Local Hour Angle of Sunrise (degrees). The baseline for a visible sun is :math:`90^{\circ}50^{\prime}`,
    or 90.833. Other values account for civil, nautical, or astronomial twilight.

    ..  math::

        W = \arccos \left(\frac{\cos 90.833}{\cos \phi \cos T} - \tan \phi \tan T\right)

#.  X is Solar Noon in Local Standard Time. Note that :math:`1440 = 24 \times 60`, the number
    of minutes in a day. The equation of time is in minutes.

    ..  math::

        X = \frac{720 - 4 \lambda - V + t}{1440}

#.  Y is sunrise.

    ..  math::

        Y = \frac{X - 4 W}{1440}

#.  Z is sunset.

    ..  math::

        Z = \frac{X + 4 W}{1440}


Twilight
========

Computing nautical twilight is Solar zenith angle is 102°, solar elevation angle is -12°.
This is 12° beyond the horizon.

For some information, see http://www.stargazing.net/kepler/sunrise.html

This appears to be an offset to the Hour Angle of sunrise. The following
uses 90.833 as the horizon with a correction for refraction of the atmosphere:

..  math::

    W = \arccos \left( \frac{\cos 90.833}{\cos {\phi} \cos T} - \tan{\phi}\tan T \right)

If so, then Nautical twilight could be:

..  math::

    W_n = \arccos \left( \frac{\cos 102}{\cos {\phi} \cos T} - \tan{\phi}\tan T \right)

Alternative
===========

See https://edwilliams.org/sunrise_sunset_algorithm.htm

This is a reference to the *Almanac for computers*, 1990 edition.

The official citation:

    United States Naval Observatory. Nautical Almanac Office. (19801991).
    *Almanac for computers*. Washington, D.C.: Nautical Almanac Office, United States Naval Observatory.

Day of the Year
---------------

Preliminary Information from Page B1 and B2.

.. |N| replace:: :math:`N`

:|N|:
    Day of year, integer; the time in days since the beginning of the year
    Range is 1 to 365 for non-leap years, 1 to 366 for leap years.

..  math::

    N = \left\lfloor \frac{275 M}{9} \right\rfloor – \left\lfloor \frac{M+9}{12} \right\rfloor \left(1+\left\lfloor \frac{K \mod 4+2}{3} \right\rfloor \right) + I - 30

Where |N| is the day of the year, :math:`K` is the year, :math:`M` is the month (:math:`1 \leq M \leq 12`),
and :math:`I` is the day of the month (:math:`1 \leq I \leq 31`).

This is valid for any year except centurial years not evenly divisible by 400. This is valid
for 2000, but not for 1900 or 2100.

Sunrise, Sunset and Twilight
----------------------------

This starts on Page B5.

For locations between latitudes 65° North and 65° South, the following algorithm
provides times of sunrise, sunset and twilight to an accuracy of :math:`\pm 2 ^m`,
for any date in the latter half of the twentieth century.

Notation:

.. |phi| replace:: :math:`\phi`
.. |lambda| replace:: :math:`\lambda`
.. |delta| replace:: :math:`\delta`
.. |H| replace:: :math:`H`
.. |L| replace:: :math:`L`
.. |M| replace:: :math:`M`
.. |RA| replace:: :math:`RA`
.. |z| replace:: :math:`z`

:|phi|:
    latitude of observer (north is positive; south is negative)

:|lambda|:
    longitude of observer (east is positive; west is negative)

:|M|:
    Sun's mean anomaly

:|L|:
    Sun's true longitude

:|RA|:
    Sun's right ascension

:|delta|:
    Sun's declination

:|H|:
    Sun's local hour angle

:|z|:
    Sun's zenith distance for sunrise or sunset.
    One of the following:

    ..  table:: Zenith Choices
        :align: left

        =====================  =======  ========
        Phenomenon             z        cos z
        =====================  =======  ========
        Sunrise Sunset          90°50′  -0.01454
        Civil Twilight          96°     -0.10453
        Nautical Twilight      102°     -0.20791
        Astronomical Twilight  108°     -0.30902
        Noon                     0°     +1.00000
        =====================  =======  ========

.. |T| replace:: :math:`T`
.. |t| replace:: :math:`t`
.. |T_U| replace:: :math:`T_U`

:|t|:
    approximate time of phenomenon in days since 0 January, :math:`O^h` UT

:|T|:
    local mean time of phenomenon


:|T_U|:
    universal time of phenomenon

Formulas:

..  math::
    :name: 1

    M = 0^{\circ}\!.985600 t - 3^{\circ}\!.289

..  math::
    :name: 2

    L = M + 1^{\circ}\!.916 \sin M + 0^{\circ}\!.020 \sin 2M + 282^{\circ}\!.634

..  math::
    :name: 3

    \tan {RA} = 0.91746 \tan L

..  math::
    :name: 4

    \sin \delta = 0.39782 \sin L

..  math::
    :name: 5

    x = \cos H = \frac{\cos z - \sin \delta \sin \phi}{\cos \delta \cos \phi}

..  math::
    :name: 6

    T = H + {RA} - 0^{h}\!.65710 t - 6^{h}\!.622

..  math::
    :name: 7

    T_U = T - \lambda


Procedure:


1.  With an initial valueof |t|, compute |M| from eq. (`1`_) and then |L| from eq. (`2`_).
    If a morning phenomenon (sunrise or the beginning of morning twilight) is being computed,
    construct an initial value of |t| from the formula

    ..  math::

            t=N+(6^{h}-\lambda)/24

    Where |N| is the day of the year (see calendar formulas on page B1)
    and |lambda| is the observer's longitude expressed in hours.

    If an evening phenomenon is being computed, use

    ..  math::

            t=N+(18^{h}-\lambda)/24

    For transit of the local meridian (i.e., noon), use

    ..  math::

            t=N+(12^{h}-\lambda)/24

2.  Solve eq. (`3`_) for |RA|, nothing that |RA| is in the same quadrant as |L|.
    Transform |RA| to hours for later use in eq. (`6`).

3.  Solve eq. (`4`_) for :math:`\sin \delta`, which appears in eq. (`5`_);
    :math:`\cos \delta`, which also is required in eq. (`5`_), should be determined
    from :math:`\sin \delta`. While :math:`\sin \delta` may be positive or negative,
    :math:`\cos \delta` is always positive.

4.  Solve eq. (`5`_) for |H|. Since computers and calculators normally give arccosine
    in the range 0°-180°, the correct quadrant for |H| can be selected according to
    the following rules:

    rising phenomena: :math:`H = 360^{\circ} - \arccos x`;

    setting phenomena: :math:`H = \arccos x`.

    In other words, for rising phenomena, |H| must be in quadrant 3 or 4 (depending on the sign of :math:`\cos H`),
    whereas |H| must be either in quadrant 1 or 2 for setting phenomena.
    Convert |H| from degrees to hours for use in eq. (`6`_).

5.  Compute |T| from eq. (`6`_), recalling that |H| and |RA| must be expressed in hours.
    If |T| is negative or greater than :math:`24^h`, it should be converted to the
    range :math:`0^h - 24^h` by adding or subtracting multiples of :math:`24^h`.

6.  Compute |T_U| from eq. (`7`_), where |lambda| must be expression in hours.
    |T_U| is an approximation to the time of the desired rising or setting phenomenon,
    referred to the Greenwich meridian.  If |T_U| is greater than :math:`24^h`, the
    phenomenon occurs on the following day, Greenwich time. If |T_U| is negative,
    the phenomenon occurs on the previous day day, Greenwich time.

Under certain conditions, eq. (`5`_) will yield a value of :math:`\lvert{\cos H}\rvert > 1`,
indicating the absence of the phenomenon on that day. At far northern latitudes,
for example, there is continuous illumination during certain summer days and continuous
darkness during winter days.

Example:

Compute the time of sunrise on 25 June at Wayne, New Jersey.

Latitude: :math:`40^{\circ}\!.9 \text{ North}`  :math:`\phi=+40^{\circ}\!.9` :math:`\sin \phi=+0.65474` :math:`\cos \phi=+0.75585`

Longitude: :math:`74^{\circ}\!.3 \text{ West}`  :math:`\lambda=-74^{\circ}\!.3/15 = -4^{h}\!.953`

For sunrise: :math:`z=90^{\circ} 50^{\prime}`   :math:`\cos z = -0.01454`

..  math::

    \begin{flalign*}
    t& = 176^{d} + (6^h + 4^{h}\!.953) / 24 = 176^{d}\!.456\\
    M& = 0^{\circ}\!.985600(176^{d}\!.456) - 3^{\circ}\!.289 = 170^{\circ}\!.626\\
    L& = 170^{\circ}\!.626 + 1^{\circ}\!.916 (0.16288) + 0^{\circ}\!.020 (-0.32141) + 282^{\circ}\!.634 = 453^{\circ}\!.566 = 93^{\circ}\!.566\\
    \tan {RA}& = 0.91746 (-16.046) = -14.722\\
    &\text{Since $L$ is in quadrant 2, so is $RA$}\\
    {RA}& = 93^{\circ}\!.566/15 = 6^{h}\!.259\\
    \sin\delta& = 0.39782 (0.99806) = 0.39705\\
    \cos\delta& = 0.91780\\
    x& = \cos H = \frac{-0.01454 - (0.39705)(0.65474)}{(0.91780)(0.75585)} = -0.39570\\
    \arccos x& = 113^{\circ}\!.310\\
    &\text{Since sunrise is being computed, $H = 360^{\circ} - 113^{\circ}\!.310 = 246^{\circ}\!.690$}\\
    H& = 246^{\circ}\!.690 / 15 = 16^{h}\!.446\\
    T& = 16^{h}\!.446 + 6^{h}\!.259 - 0^{h}\!.65710(176^{d}\!.456) - 6^{h}\!.622 = 4^{h}\!.488\\
    T_U&= 4^{h}\!.488 + 4^{h}\!.953 = 9^{h}\!.441\\
    \end{flalign*}

Sunrise occurs at :math:`9^{h} 26^{m}` UT = :math:`5^{h} 26^{m}` EDT

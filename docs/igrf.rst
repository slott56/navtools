..  _igrf:

#############################################################################
:py:mod:`igrf` -- International Geomagnetic Reference Field
#############################################################################

This module computes the compass deviation (or variance)
at a given point.  It allows mapping from true bearings to
magnetic bearings.

This is a migration of the Geomag 7.0 software from Fortran to Python.

It relies on the coefficients table, provided by NOAA.  See https://www.ngdc.noaa.gov/IAGA/vmod/igrf.html
for more information.


Background
==========

From the web page.

..  math::

    V(r,\theta,\phi,t) = a \sum_{n=1}^{N}\sum_{m=0}^{n}\Big(\frac{a}{r}\Big)^{n+1}[g_n^m(t)\cos (m \phi) + h_n^m(t)\sin (m \phi)] P_n^m(\cos \theta)

With :math:`g_n^m` and :math:`h_n^m` are the coefficients to determine
phase and amplitude. These are provided by the associated :file:`igrf13coeffs.txt` file.

:math:`a` is the radius of the Earth, 6371.2 km.

:math:`N` is the degree of truncation, 13.

The position, :math:`r,\theta,\phi,t`, is the altitude, latitude,
longitude and time. At the surface, :math:`r = a`.

:math:`P_n^m` are associated Legendre functions of the first kind
of degree :math:`n`, order :math:`m`.

..  math::

    P_n^m(z) = \frac{1}{\Gamma(1-m)}\Big[\frac{1+z}{1-z}\Big]^{m / 2} {{}_{2}F_{1}}\left(-n, n+1; 1-m; \frac{1-z}{2}\right)

:math:`{}_{2}F_{1}(a,b;c;z)` is the Hypergeometric function.

..  math::

    {}_{2}F_{1}(a,b;c;z)=\sum_{n=0}^{\infty} {\frac {(a)_{n}(b)_{n}}{(c)_{n}}}{\frac {z^{n}}{n!}}=1+{\frac {ab}{c}}{\frac {z}{1!}}+{\frac {a(a+1)b(b+1)}{c(c+1)}}{\frac {z^{2}}{2!}}+\cdots

The Gamma function is :math:`\Gamma (n)=(n-1)!`, or :math:`\Gamma (z)=\int _{0}^{\infty }x^{z-1}e^{-x}\,dx,\ \qquad \Re (z)>0`

http://www.ngdc.noaa.gov/IAGA/vmod/igrf.html

Testing
=======

This is tested with IGRF-11, and IGRF-13 coefficients.

..  sidebar:: Alternative

    See https://pypi.org/project/pyIGRF/ for an implementation that
    can be forked to remove a numpy dependency.


Implementation
===============

..  py:module:: navtools.igrf

The core model.

..  autoclass:: IGRF
    :members:
    :undoc-members:

..  autofunction:: igrfsyn

A slightly simplified function that allows a
client to get today's declination at a specific
point.

..  autofunction:: declination

A utility to convert simple degrees to (degree, minute) two-tuples.

..  autofunction:: deg2dm

..  _igrf11:

#############################################################################
:py:mod:`navtools.igrf11` -- International Geomagnetic Reference Field Module
#############################################################################

This module computes the compass deviation (or variance)
at a given point.  It allows mapping from true bearings to
magnetic bearings.

..  py:module:: navtools.igrf11

The core model.

..  autoclass:: IGRF11
    :members:
    :undoc-members:

..  autofunction:: igrf11syn

A slightly simplified function that allows a
client to get today's declination at a specific
point.

..  autofunction:: declination

A utility to convert simple degrees to (degree, minute) two-tuples.

..  autofunction:: deg2dm

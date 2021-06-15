########################################
:mod:`navtools.olc` -- OLC Geocoding
########################################

This is one of many Geocoding schemes that permits simplistic proximity checks.

See https://github.com/google/open-location-code/blob/main/docs/specification.md

This document has a few tiny gaps.

1.  The "Encoding" section omits details on clipping and normalization.

2.  The "Decoding" section implies that the decoded value is a box that brackets
    the original coordinations. This menas that enoding and decoding aren't proper
    inverses, exception in a few special cases.

3.  The topic of "precision" is noted without explaining how it is used when decoding.
    The replacement of "00" padding characters, and the creation of a bounding box
    are not really described very carefully.

See the official Test Cases:
https://github.com/google/open-location-code/blob/main/test_data

Implementation
==============

..  py:module:: navtools.olc

Abstract Superclass
-------------------

..  autoclass:: Geocode
    :members:
    :undoc-members:

Concrete Subclass
-----------------

..  autoclass:: OLC
    :members:
    :undoc-members:

Base 20/Base 5 Conversions
--------------------------

There are subtle bugs in the :py:func:`from20` conversion.
It doesn't pass all the decode tests because it
doesn't -- correctly -- include the size of the bounding
box for the LSB of the OLC value.

..  autofunction:: base20

..  autofunction:: from20


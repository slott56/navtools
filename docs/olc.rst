########################################
:py:mod:`olc` -- OLC Geocoding
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

Encoding
=============

The encoding algorithm has the following outline:

1. Clip latitude to -90 - +90.
   This includes a special case for excluding +90: back off based on how many digits are going to be encoded.

2.  Normalize longitude to -180 to +180 (excluding +180)

3.  Convert lat and lon to N latitude and E longitude via offsets to remove signs.

4.  Encode in base 20.

5.  Interleave 5 pairs of digits from latitude and longitude for the most significant portion.

6.  Convert pairs of digits into a single base 20 number for least significant portion.

7.  Truncate (or zero pad) given the the size parameter.

8.  Inject the "+" after position 8.

This is a rectangle, not a point. That means there's an implied box around the given point.
This concept of describing a box with a size implied by the number of digits informs
decoding.

Implementation
==============


Here's the UML overview of this module.

..  uml::

    @startuml
    'navtools.olc'
    allow_mixing

    component olc {
        abstract class Geocode {
            {abstract} encode(Lat, Lon): str
            {abstract} decode(str): Lat, Lon
        }

        class OLC {
            encode(Lat, Lon): str
            decode(str): Lat, Lon
        }

        Geocode <|-- OLC
    }

    @enduml

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


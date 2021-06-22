########################################################
:mod:`navtools.lowrance_usr` -- Lowrance USR File Parser
########################################################

The Lowrance USR file is a binary file, and parsing it is a fairly complex exercise.


See https://www.gpsbabel.org/htmldoc-1.7.0/fmt_lowranceusr.html

The documentation for GPSBabel has a number of errors.
It does, however, provide some advice on the overall structure of the USR file
and how to decode it one field at a time.

See https://github.com/GPSBabel/gpsbabel/blob/master/lowranceusr.cc for the code,
which appears to work.

Data Encodings
==============

Latitude and Logitude encoding:

    Latitude and longitude for USR coords are in the lowrance mercator meter
    format in WGS84.  The below code converts them to degrees.

    - ``lon = x / (DEGREESTORADIANS * SEMIMINOR)``

    - ``lat = (2.0 * atan(exp(x / SEMIMINOR)) - M_PI / 2.0) / DEGREESTORADIANS``

    Where

    -   ``static constexpr double SEMIMINOR = 6356752.3142;``

    -   ``static constexpr double DEGREESTORADIANS = M_PI/180.0;``

(See https://en.wikipedia.org/wiki/World_Geodetic_System#1984_version
This says :math:`s_b = 6356752.314245`, but that may not be the constant
that Lowrance actually uses.)

Generally,
the :math:`\phi` values are N-S latitude, and :math:`\lambda` values are E-W longitude.

The above formula combine two things.

..  math::

    \lambda = \frac{x}{s_b} \times \frac{180}{\pi}

The :math:`\frac{x}{s_b}` term converts millimeters to radians.
These are then converted to degrees.

..  math::

    \phi = \Big( 2 \arctan( e^{\frac{x}{s_b}} ) - \frac{\pi}{2} \Big)  \times \frac{180}{\pi}

As with the longitude, we convert mm to radians and then radians to degrees.

Dates are Julian Day Numbers.  Use fromordinal(JD-1721425) to convert to a ``datetime.date``

Times are milliseconds past midnight. Either use ``seconds=time/1000`` or ``microseconds=time*1000``.
to create a ``datetime.timedelta`` that can be added to the date to create a usable ``datetime.datetime`` object.

See the ``lowranceusr4_parse_waypt()`` function for the decoding of a waypoint.

..  sidebar:: Is this part of :py:mod:`navtools.navigation`?

    Pro: It's a prepresentation of lat and lon

    Con: It's unique to USR files and not widely useful.

    Note the vagueness of "widely." We vote for separate because we can't find another use for
    this millimeter mercator value.

Field Extraction
======================

The general approach is to leverage :py:mod:`struct`
to handle decoding little-endian values.

Many structures are a sequence of fields,
often a repeating sequence of fields where the
repeat factor is a field.

For example::

    AtomicField("count", "<i"),
    AtomicField("data", "<{count}f"),

The first field has the four-byte count.
The second field depends on this count
to define an array of floats.

Implementation
==============

Here's the UML overview of this module.

..  uml::

    @startuml
    'navtools.lowrance_usr'
    allow_mixing

    component lowrance_usr {
        abstract class Field {
            name: str
            extract(UnpackContext)
        }

        class AtomicField {
            encoding: str
        }
        class FieldList {
            field_list: List[Field]
        }
        class FieldRepeat {
            name: str
            field_list: Field
            count: str
        }

        Field <|-- AtomicField
        Field <|-- FieldList
        Field <|-- FieldRepeat

        FieldList *-- "*" Field
        FieldRepeat *-- Field

        class UnpackContext {
            source: BinaryIO
            fields: dict[str, Any]
            extract(Field)
        }

        class Lowrance_USR {
            {static} load(BinaryIO): Lowrance_USR
        }

        AtomicField ..> UnpackContext

        Lowrance_USR *-- "*" Field
        Lowrance_USR -- "1" UnpackContext
    }

    @enduml


..  py:module:: navtools.lowrance_usr

..  automodule:: navtools.lowrance_usr
    :noindex:

Atomic Field
------------

..  autoclass:: AtomicField
    :members:
    :undoc-members:

Collection of Fields
--------------------

..  autoclass:: FieldList
    :members:
    :undoc-members:

Repeated of Field
-------------------------------

..  autoclass:: FieldRepeat
    :members:
    :undoc-members:

The Stateful Context
---------------------

This is where we maintain state, reading the binary file.
This allows fields to be defined independently, only sharing this context object.

..  autoclass:: UnpackContext
    :members:
    :undoc-members:

Conversions
-----------

..  autofunction:: lon_deg

..  autofunction:: lat_deg

..  autofunction:: b2i_le

Unpack The File
----------------

..  autoclass:: Lowrance_USR
    :members:
    :undoc-members:



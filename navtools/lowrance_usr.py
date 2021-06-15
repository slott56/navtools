"""
Parse a Lowrance .USR file.

We define a recursive data structure that defines fields.
It must be traversed in order to correctly locate dependencies among field definitions.
This approach will capture repeat factors and lengths.

The :py:class:`Lowrance_USR` class contians
the field definitions. Once loaded, it behaves
like a dictionary.

See https://github.com/GPSBabel/gpsbabel/blob/master/lowranceusr.h and https://github.com/GPSBabel/gpsbabel/blob/master/lowranceusr.cc

"""
from dataclasses import dataclass
import datetime
import math
import re
import struct
import sys
import uuid
from typing import (
    TextIO,
    BinaryIO,
    Iterator,
    Optional,
    Callable,
    Any,
    Union,
    Dict,
    Tuple,
    cast,
)
from pathlib import Path


def dump_next(source: BinaryIO, count: int) -> None:
    """This peeks at a bunch of bytes in a file so we can diagnose problems with decoding them."""
    here = source.tell()
    look_ahead = source.read(count)
    if look_ahead:
        print(" ".join([f"{b:02x}" for b in look_ahead]))
        print(" ".join([f"{chr(b)} " for b in look_ahead]))
        print(repr(look_ahead))
    else:
        print("EOF")
    source.seek(here)


Conversion = Callable[[Tuple[Any, ...]], Any]

# lowranceusr4_icon_value_table.
# Does not seem to apply properly to B&G.

ICON_CODE = """
  static constexpr lowranceusr4_icon_mapping_t lowranceusr4_icon_value_table[] = {

    /*  USR     GPX Symbol                COLOR1     COLOR2     COLOR3    COLOR4     COLOR5    COLOR6      COLOR7         HOOK2 Displays */

    {     1,    "diamond 1",            { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // diamond
    {     0,    "diamond 1",            { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // diamond
    {     1,    "diamond 2",            { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // diamond
    {     1,    "diamond 3",            { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // diamond
    {     2,    "x 1",                  { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // X
    {     2,    "x 2",                  { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // X
    {     2,    "x 3",                  { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // X
    {     4,    "fish",                 { "green",  "aqua",    "blue",   "magenta", "red",     "yellow",  "white" }},   // single fish
    {     5,    "two fish",             { "aqua",   "blue",    "red",    "orange",  "yellow",  "green",   "white" }},   // schoolfish
    {     8,    "hole",                 { "aqua",   "blue",    "red",    "orange",  "yellow",  "green",   "white" }},   // dip sign
    {     9,    "hump",                 { "aqua",   "blue",    "red",    "orange",  "yellow",  "green",   "white" }},   // bump sign
    {    10,    "longgrass",            { "green",  "aqua",    "blue",   "red",     "orange",  "yellow",  "white" }},   // long grass
    {    12,    "rocks",                { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // rocks
    {    17,    "gas station",          { "red",    "yellow",  "green",  "aqua",    "blue",    "magenta", "white" }},   // gas pump
    {    28,    "tree",                 { "green",  "aqua",    "blue",   "magenta", "red",     "yellow",  "white" }},   // tree
    {    30,    "campsite",             { "yellow", "green",   "aqua",   "blue",    "magenta", "red",     "white" }},   // tent
    {    37,    "skull and crossbones", { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // skull and crossbones
    {    40,    "dive flag",            { "red",    "yellow",  "green",  "aqua",    "blue",    "magenta", "white" }},   // diveflag
    {    42,    "anchor",               { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // anchor
    {    44,    "boat ramp",            { "red",    "yellow",  "green",  "aqua",    "blue",    "magenta", "white" }},   // boatramp
    {    48,    "pier",                 { "blue",   "magenta", "orange", "yellow",  "green",   "aqua",    "white" }},   // pier

    // END OF ICON MAPPING
    {    -1,    nullptr,                { nullptr,  nullptr,   nullptr,  nullptr,   nullptr,   nullptr,  nullptr  }}
  };
"""


def icon_parse(icon_code: str) -> Iterator[tuple[int, int, str]]:
    for txt in icon_code.splitlines():
        if m := re.match(r'^\s+\{\s+(\d+),\s+"([\w\s]+)",\s+\{(.+)\}\},\s+//.*$', txt):
            icon_id, symbol, color_text = m.groups()
            colors = re.findall(r'"(\w+)"', color_text)
            for color_id, color in enumerate(colors):
                yield int(icon_id), color_id, f"{symbol},{color}"


ICON_TABLE_1 = {
    (icon_id, color_id): text for icon_id, color_id, text in icon_parse(ICON_CODE)
}

# Actual Observation from Chartplotter files.
ICON_TABLE_2 = {
    (3, 0): "anchor",
    (2, 0): "diamond,blue",
    (1, 6): "circle,white",
    (
        0,
        0,
    ): "cross,blue",  # Actually found three mappings! {'anchor', 'cross,yellow', 'cross,blue'}
    (0, 3): "cross,yellow",
    (10, 4): "rocksubmerged",
    (12, 6): "rock",
    (21, 2): "flag",
    (28, 0): "warning",
    (13, 3): "portlateralmarker",  # Yellow?
    (13, 4): "portlateralmarker",  # Green?
    (1, 4): "circle,green",
}


@dataclass
class Field:
    """
    An isolated, atomic field or sequence of fields that we are not examining more deeply.

    The name must be unique, otherwise previous values will be overwritten.

    The encoding is a :py:mod:`struct` format.
    It is extended to permit including ``{name}`` to refer to a previously loaded field's value.
    For example::

        Field("count", "<i"),
        Field("data", "<{count}f"),

    This defines a count field followed by a data field. The data field will be a number of
    float values, defined by the value of the preceeding field.

    The conversion is additional conversion beyond what :py:mod:`struct` does.
    For example::

        Field("name_len", "<i"),
        Field("name", "<{name_len}s", lambda x: x[0].decode("ASCII"))

    """

    name: str
    encoding: str
    conversion: Conversion = lambda x: x[0]

    def extract(self, context: "UnpackContext") -> Any:
        conversion = cast(Conversion, self.conversion)  # type: ignore [misc]
        format = self.encoding
        replacements = re.finditer(r"\{(\w+)\}", format)
        for repl in replacements:
            name = repl.group(1)
            value = context.fields[name]
            format = re.sub(
                f"\\{{{name}\\}}", str(value if value >= 0 else 0), format, count=1
            )
        try:
            size = struct.calcsize(format)
            source_bytes = context.source.read(size)
        except Exception as ex:
            print(ex)
            print(self)
            print(f"{self.name=}, {self.encoding=}, {format=}")
            print(context.fields)
            raise
        try:
            results = conversion(struct.unpack(format, source_bytes))
        except Exception as ex:
            print(ex)
            print(self)
            print(f"{source_bytes!r}")
            print(context.fields)
            raise
        context.fields[self.name] = results
        return results


@dataclass
class FieldList:
    """A sequence of FieldList, FieldRepeat, and Field instances. This is a "block" of data."""

    name: str
    field_list: list[Union["FieldList", "Field", "FieldRepeat"]]

    def extract(self, context: "UnpackContext") -> dict[str, Any]:
        # print(self.name)
        # dump_next(context.source, 160)
        results = {field.name: field.extract(context) for field in self.field_list}
        context.fields[self.name] = results
        return results


@dataclass
class FieldRepeat:
    """A repeating Field or FieldList where the repeat count comes from another field."""

    name: str
    field_list: Union["FieldList", "Field"]
    count: str  # Name of a field with the count

    def extract(self, context: "UnpackContext") -> list[Any]:
        repeat_value = context.fields[self.count]
        results = [self.field_list.extract(context) for repeat in range(repeat_value)]
        context.fields[self.name] = results
        return results


class UnpackContext:
    """
    Used to unpack a binary file. This is used to manage the input
    buffer and extract fields using :py:class:`Field`, :py:class:`FieldList`, :py:class:`FieldRepeat`
    definitions.

    THe fields includes the currently named fields being processed.
    This makes them visible for resolving dependencies in repeating fields and formats
    that depend on the values of other fields.
    """

    def __init__(self, source: BinaryIO) -> None:
        self.source = source
        self.fields: dict[str, Any] = {}

    def extract(
        self, field_list: Union[Field, FieldList, FieldRepeat]
    ) -> Union[Any, dict[str, Any], list[Any]]:
        """Extracts the next fields present in the file of bytes."""
        return field_list.extract(self)

    def peek(self, field: Field) -> Any:
        """Peeks ahead in the file of bytes to see what follows."""
        here = self.source.tell()
        result = field.extract(self)
        self.source.seek(here)
        return result

    def eof(self) -> bool:
        """
        At EOF? Try to read another byte.
        Might be better to get the file size and compare the tell location.
        """
        here = self.source.tell()
        if len(next8 := self.source.read(8)) == 0:
            return True
        else:
            # DEBUG: print(f"{next8!r}")
            self.source.seek(here)
            return False


JD_TO_ORDINAL = 1721425
SEMIMINOR_B = 6_356_752.3142


def lon_deg(mm: int) -> float:
    """Convert millimeters to degrees of longitude"""
    lon = round(math.degrees(mm / SEMIMINOR_B), 8)
    return lon


def lat_deg(mm: int) -> float:
    """Convert millimeters to degrees of latitude"""
    lat = round(
        math.degrees(2 * math.atan(math.exp(mm / SEMIMINOR_B)) - math.pi / 2), 8
    )
    return lat


def b2i_le(value: bytes) -> int:
    """Converts a sequence of bytes (in little-endian order) to a single integer."""
    value_int = sum(b * 2 ** (i * 8) for i, b in enumerate(value))
    return value_int


class Lowrance_USR(Dict[str, Any]):
    """
    Read a Lowrance USR file, creating a complex dict[str, Any] structure
    that reflects the header fields, waypoints, routes, event markers, and trails.
    """

    @classmethod
    def load(cls, source: BinaryIO) -> "Lowrance_USR":
        uc = UnpackContext(source)
        format = uc.peek(Field("format", "<I"))
        # format = struct.unpack("<I", source.read(4))[0]
        if format == 2:  # pragma: no cover
            return cls.load_2(uc)
        elif format == 3:  # pragma: no cover
            return cls.load_3(uc)
        elif format == 4:  # pragma: no cover
            return cls.load_4(uc)
        elif format == 5:  # pragma: no cover
            return cls.load_5(uc)
        elif format == 6:
            return cls.load_6(uc)
        else:  # pragma: no cover
            raise ValueError(f"Unkown format {format}")

    @classmethod
    def load_2(cls, uc: UnpackContext) -> "Lowrance_USR":  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def load_3(cls, uc: UnpackContext) -> "Lowrance_USR":  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def load_4(cls, uc: UnpackContext) -> "Lowrance_USR":  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def load_5(cls, uc: UnpackContext) -> "Lowrance_USR":  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def load_6(cls, uc: UnpackContext) -> "Lowrance_USR":

        wp_fields = FieldList(
            "waypoint",
            [
                # 1.  16 bytes -- UUID.
                Field("uuid", "<16s", lambda x: uuid.UUID(bytes_le=x[0])),
                # Field("uuid", "<IHHBB6s", lambda x: uuid.UUID(fields=x[:5]+(b2i_le(x[5]),))),
                # 2.  4 bytes INT -- UID unit number
                Field("UID_unit_number", "<I"),
                # 3.  8 bytes -- UID sequence number. (This may be two separate small-endian integers.)
                Field("UID_sequence_number", "<Q"),
                # 4.  2 bytes INT -- Waypt stream version number
                Field("waypt_stream_version", "<h"),
                # 5.  4 bytes INT -- name_length
                Field("waypt_name_length", "<i"),
                # 6.  name_length bytes -- name in utf-16 encoding
                Field(
                    "waypt_name",
                    "<{waypt_name_length}s",
                    lambda x: x[0].decode("utf-16"),
                ),
                # 7.  4 bytes INT -- repeated UID unit number
                Field("UID_unit_number_2", "<I"),
                # 8.  4 bytes INT -- longitude in mercator meter encoding
                Field("longitude", "<i", lambda x: lon_deg(x[0])),
                # 9.  4 bytes INT -- latitude in mercator meter encoding
                Field("latitude", "<i", lambda x: lat_deg(x[0])),
                # 10. 4 bytes INT -- flags
                Field("flags", "<I"),
                # 11. 2 bytes INT -- icon ID (See ``lowranceusr4_find_desc_from_icon_number()`` to decode)
                Field("icon_id", "<h"),
                # 12. 2 bytes INT -- color ID (See ``lowranceusr4_find_color_from_icon_number_plus_color_index()`` to decode)
                Field("color_id", "<h"),
                # 13. 4 bytes INT -- description_length
                Field("waypt_description_length", "<i"),
                # 14. description_length bytes -- description in utf-16 encoding
                Field(
                    "waypt_description",
                    "<{waypt_description_length}s",
                    lambda x: x[0].decode("utf-16"),
                ),
                # 15. 4 bytes FLOAT -- alarm radius
                Field("alarm_radius", "<f"),
                # 16. 4 bytes INT -- creation date, Julian day number; Julian date 2440487 is 1/1/1970
                Field(
                    "waypt_creation_date",
                    "<I",
                    lambda x: datetime.date.fromordinal(x[0] - JD_TO_ORDINAL),
                ),
                # 17. 4 bytes INT -- creation time, milliseconds
                Field(
                    "waypt_creation_time",
                    "<I",
                    lambda x: datetime.timedelta(seconds=x[0] / 1000),
                ),
                # 18. 1 byte -- unused
                Field("unknown_2", "<b"),
                # 19. 4 bytes FLOAT -- depth in feet
                Field("depth", "<f"),
                # 20. 4 bytes -- LORAN GRI
                Field("LORAN_GRI", "<i"),
                # 21. 4 bytes -- LORAN Tda
                Field("LORAN_Tda", "<i"),
                # 22. 4 bytes -- LORAN Tdb
                Field("LORAN_Tdb", "<i"),
            ],
        )
        route_fields = FieldList(
            "route",
            [
                # 1.  16 bytes -- UUID. (This may be four small-endian integers that are later combined.)
                Field("uuid", "<16s", lambda x: uuid.UUID(bytes_le=x[0])),
                # 2.  4 bytes INT -- UID unit number
                Field("UID_unit_number", "<I"),
                # 3.  8 bytes -- UID sequence number. (This may be two separate small-endian integers.)
                Field("UID_sequence_number", "<Q"),
                # 4.  2 bytes INT -- Waypt stream version number
                Field("route_stream_version", "<h"),
                # 5.  4 bytes INT -- name_length
                Field("route_name_length", "<i"),
                # 6.  name_length bytes -- name in utf-16 encoding
                Field(
                    "route_name",
                    "<{route_name_length}s",
                    lambda x: x[0].decode("utf-16"),
                ),
                # 7.  4 bytes INT -- repeated UID unit number
                Field("UID_unit_number_3", "<I"),
                # 8. 4 bytes INT -- number_legs
                Field("number_legs", "<i"),
                # 9. leg_uuids = [struct.unpack("<16s", source.read(16))[0] for l in range(number_legs)]
                FieldRepeat(
                    "leg_uuids",
                    Field("leg_uuid", "<16s", lambda x: uuid.UUID(bytes_le=x[0])),
                    "number_legs",
                ),
                # 10. unknown = source.read(10)
                Field("route_unknown", "<10s"),
            ],
        )
        usr_fields = FieldList(
            "header",
            [
                Field(
                    "format", "<I"
                ),  # (Was already peeked at, but it's here for completeness.)
                Field("data_stream_version", "<I"),
                Field("file_title_length", "<i"),
                Field(
                    "file_title",
                    "<{file_title_length}s",
                    lambda x: x[0].decode("ascii"),
                ),
                Field("file_creation_date_length", "<i"),
                Field(
                    "file_creation_date_text",
                    "<{file_creation_date_length}s",
                    lambda x: x[0].decode("ascii"),
                ),
                Field(
                    "file_creation_date",
                    "<I",
                    lambda x: datetime.date.fromordinal(x[0] - JD_TO_ORDINAL),
                ),
                Field(
                    "file_creation_time",
                    "<I",
                    lambda x: datetime.timedelta(seconds=x[0] / 1000),
                ),
                Field("unknown", "<b"),
                Field("unit_serial_number", "<I"),
                Field("file_description_length", "<i"),
                Field(
                    "file_description",
                    "<{file_description_length}s",
                    lambda x: x[0].decode("ascii"),
                ),
                Field("number_waypoints", "<i"),
                FieldRepeat("waypoints", wp_fields, "number_waypoints"),
                Field("number_routes", "<i"),
                FieldRepeat("routes", route_fields, "number_routes"),
                Field("number_event_markers", "<i"),
                # FieldRepeat("event_markers", event_marker_fields, "number_event_markers"),
                Field("number_trails", "<i"),
                # FieldRepeat("trails", trail_fields, "number_trails"),
            ],
        )

        data = uc.extract(usr_fields)

        if not uc.eof():  # pragma: no cover
            print("Warning: UNREAD BYTES")
            extra = uc.source.read(128)
            print(extra)

        return Lowrance_USR(data)


def t3() -> None:  # pragma: no cover
    plotter = Path.cwd() / "data" / "WaypointsRoutesTracks.usr"
    raw = False
    with plotter.open("rb") as source:
        # dump_next(source, 128)
        u = Lowrance_USR.load(source)

    for k in u.keys():
        if k not in {"waypoints", "routes"}:
            print(f"{k} {u[k]!r}")
    if raw:
        for wp in u["waypoints"]:
            print()
            for k in wp:
                print(f"  {k} {wp[k]!r}")
        for rt in u["routes"]:
            print()
            for k in rt:
                print(f"  {k} {rt[k]!r}")
    else:
        wp_map = {wp["uuid"]: wp for wp in u["waypoints"]}
        for rt in u["routes"]:
            print(rt)
            for leg in rt["leg_uuids"]:
                print(f" - {wp_map[leg]}")
            print()


if __name__ == "__main__":  # pragma: no cover
    t3()

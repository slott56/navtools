"""OLC Representation of latitude/longitude pairs.
(Sometimes called a "Plus Code")

This is one of many Geocoding schemes that permits simplistic proximity checks.

There are two parts to the encoding: most significant 10, least signficant 5.

-   Most significant is base 20 for 5 digits.
    Lat and Lon codes are interleaved we create a 10 digit sequence.
    A "+" is inserted after 8 characters. This is approximately a 13.9 meter square.

-   Least significant is base 5/base 4 decomposition, combined into single digits.
    There can be at most 5 of these. They are optional.

>>> from math import isclose
>>> lat = 1.286785
>>> lon = 103.854503
>>> OLC().encode(lat, lon)
'6PH57VP3+PR6'
>>> lat_2, lon_2 = OLC().decode('6PH57VP3+PR6')
>>> isclose(lat_2, 1.28675, rel_tol=1E-5)  # Truncation, not the original value
True
>>> isclose(lon_2, 103.8545, rel_tol=1E-5)  # Truncation: not the original lon value.
True
>>> isclose(lat, lat_2, rel_tol=1E-4)
True
>>> isclose(lon, lon_2, rel_tol=1E-5)
True

The official Test Cases:
https://github.com/google/open-location-code/blob/main/test_data

We don't actually pass *all* of these. There are four decoding
test cases
that involve careful rounding that are implemented incorrectly.

"""

from typing import Iterable, Iterator


class Geocode:  # pragma: no cover
    def encode(self, lat: float, lon: float) -> str:
        pass

    def decode(self, code: str) -> tuple[float, float]:
        pass


class OLC(Geocode):
    code = "23456789CFGHJMPQRVWX"

    def encode(self, lat: float, lon: float, size: int = 11) -> str:
        """
        Encode an OLC string from a lat, lon pair.

        The latitude number must be clipped to be in the range -90 to 90.
        The longitude number must be normalised to be in the range -180 to 180.

        >>> OLC().encode(20.3701135, 2.78223535156, size=13)
        '7FG49QCJ+2VXGJ'

        :param lat: latitude, signed
        :param lon: longitude, signed
        :param size: limit of detail, usually 10 or 11, but be up to 15.
        :return: OLC string
        """
        # Clip latitude to -90 - +90.
        # Special case for excluding +90: back off based on how many digits are needed.
        lat = max(min(lat, 90), -90)
        if lat == 90.0:
            if size <= 10:
                adj = 20 ** (2 - size / 2)
            else:
                adj = 20 ** -3 / 5 ** (size - 10)
            lat -= adj
        # Normalize longitude to -180 to +180 (excluding +180)
        while lon >= 180:
            lon -= 360
        while lon < -180:
            lon += 360
        # Convert to N latitude and E longitude via offsets to remove signs.
        nlat = lat + 90
        elon = lon + 180
        # Create the sequences of digits
        lat_digits = list(base20(nlat, lsb=5))
        lon_digits = list(base20(elon, lsb=4))
        # Interleave 5 pairs of digits from latitude and longitude for the most significant portion
        msb = "".join(
            f"{self.code[lat_digits[i]]}{self.code[lon_digits[i]]}" for i in range(5)
        )
        # Append five of the LSB characters from pairs of digits.
        lsb = "".join(
            self.code[lat_digits[p] * 4 + lon_digits[p]] for p in range(5, 10)
        )
        # Handle the size parameter with truncation and/or zero-padding.
        olc = (msb + lsb)[:size]
        if len(olc) < 8:
            olc += "0" * (8 - len(olc))
        # Inject the "+" after 8.
        return f"{olc[:8]}+{olc[8:]}"

    def decode(self, olc: str, size: int = 11) -> tuple[float, float]:
        """
        Decode a lat, lon pair from an OLC string.

        An OLC has several forms, punctuated by an "+" that signals
        the end of the leading 8 characters.

        1.  ``AOAOAOAO``: no plus. Assume "+00" suffix to fill up to a 10-digit MSB-only form.
        2.  ``AOAOAOAO+AO``: the expected 10-digit MSB-only form
        3.  ``AOAOAOAO+AOVWYXZ``:  after the 10-digits, an LSB suffix of 1 to 5 additional digits.
        4.  ``AOAO0000`` zeros used as place-holders to fill out the MSB section.
        5.  ``AOAO+`` leading positions can be assumed based on other context.
            We don't handle this.

        Note that the encoded value is allowed to pad with zeroes, which are not otherwise valid.
        These are -- in effect -- wild-card matching values. We can replace them with "2" which
        is not as obviously a wild-card.

        The reference implementation provides a bounding box; not a single point.

        This needs to locate the center of the box to parallel the reference implementation.
        Four test cases do not pass with this implementation.

        :param olc: OLC string
        :param size: not used, but can truncate long over-specified strings
        :return: lat, lon pair
        """
        # Expand to a single, uniform string (without punctuation or special cases.)
        # 10 MSB positions of 2-digit, 5 LSB positions of 1-digit.
        olc_clean = "".join(olc.split("+"))
        if len(olc_clean) <= 15:
            olc_15 = olc_clean.replace("0", "2") + "2" * (15 - len(olc_clean))
        else:
            olc_15 = olc_clean
        # Each of the LSB Characters needs to be expanded into base 5/base 4 lat-lon pair
        msb = olc_15[:10]
        lsb = olc_15[10:15]
        pairs = (divmod(self.code.index(c), 5) for c in lsb)
        lsb_expanded = "".join(
            f"{self.code[lat]}{self.code[lon]}" for lat, lon in pairs
        )
        lsb_expanded += "2" * (10 - len(lsb_expanded))
        full = msb + lsb_expanded
        # Convert from base-20 and base-5/base-4 to float.
        # TODO: Honor the size parameter by chopping the values.
        nlat = from20(list(self.code.index(c) for c in full[0::2]), lsb=5)
        elon = from20(list(self.code.index(c) for c in full[1::2]), lsb=4)
        # TODO: Tweak a tiny bit with the level of precision given by the size.
        nlat += 0.5 / 20 ** 3 / 5 ** 5
        elon += 0.5 / 20 ** 3 / 4 ** 5
        # Remove North and East offsets.
        return round(nlat - 90, 8), round(elon - 180, 8)


def base20(x: float, msb: int = 20, lsb: int = 5) -> Iterable[int]:
    """
    Decompose a positive Lat or Lon value to a sequence of 5 base-20 values
    followed by 5 base-4 or base-5 values.

    See https://github.com/google/open-location-code/blob/main/docs/specification.md#encoding

    >>> list(base20(1.286785+90, lsb=5))
    [4, 11, 5, 14, 14, 1, 2, 0, 0, 0]
    >>> list(base20(103.854503+180, lsb=4))
    [14, 3, 17, 1, 16, 0, 0, 1, 2, 0]

    From 20.3701135,2.78223535156,13,7FG49QCJ+2VXGJ
    The last 3, XGJ, are combinations of base 5, base 4 pairs.
    X = (4, 3), G = (2, 2), J = (3, 0)

    "7G9C2645"

    >>> list(base20(20.3701135+90, lsb=5))
    [5, 10, 7, 8, 0, 4, 2, 3, 2, 2]

    "F4QJV642"

    >>> list(base20(2.78223535156+180, lsb=4))
    [9, 2, 15, 12, 17, 3, 2, 0, 1, 3]

    """

    def ldigits(value: int, base: int) -> Iterable[int]:
        """
        Generates 5 digits from an integer value for a given base.
        This is starts with Least Significant, which requires reversal.
        """
        for b in range(5):
            value, digit = divmod(value, base)
            yield digit

    def digits(value: int, base: int) -> list[int]:
        """
        A list of six digits from a positive integer value for a given base.
        This starts with the Most Significant Digit.
        """
        return list(reversed(list(ldigits(value, base))))

    # Scale up the latitude or longitude float to a large integer for the 5 MSB's.
    x_most = int(round(x * msb ** 3, 6))
    # Create the sequence of digits in the MSB base (20, usually)
    msb_digits = digits(int(x_most), msb)
    # Scale up the latitude or longitude float to a larger integer for the 5 LSB's.
    x_least = int(round(x * msb ** 3 * lsb ** 5, 5))
    # Create a sequence of digits in the LSB base (4 or 5, depending.)
    lsb_digits = digits(int(x_least), lsb)
    # Emit the sequence of digits
    return msb_digits + lsb_digits


def from20(digits: list[int], msb: int = 20, lsb: int = 5) -> float:
    """
    Convert a sequence of 10 digits, 5 in the msb base and 5 in the lsb base,
    into a float value.

    >>> from math import isclose
    >>> nlat_i = from20([4, 11, 5, 14, 14, 1, 1, 4, 4, 4])
    >>> isclose(nlat_i, 91.286785, rel_tol=1E-6)
    True

    >>> elon_i = from20([14, 3, 17, 1, 16, 0, 0, 1, 2, 0], lsb=4)
    >>> isclose(elon_i, 283.854503, rel_tol=1E-5)
    True

    """
    m = digits[0]
    for d in digits[1:5]:
        m = m * msb + d
    l = digits[5]
    for d in digits[6:10]:
        l = l * lsb + d
    # print(f"{digits=} {m=} {msb ** 3=} {m / msb ** 3=} {l=} {l / lsb**5=}")
    return (m + l / lsb ** 5) / msb ** 3

..    #!/usr/bin/env python3

###############################################################
Test IGRF11
###############################################################

Use sample data from geomag 7.0 implementation to test the :py:mod:`igrf11` module.

Date: xxxx.xxx for decimal  (1947.32)

     YYYY,MM,DD for year, month, day  (1947,10,13)

     or start_date-end_date (1943.21-1966.11)

     or start_date-end_date-step (1943.21-1966.11-1.2)

Coord:
    D - Geodetic (WGS84 latitude and altitude above mean sea level)

    C - Geocentric (spherical, altitude relative to Earth's center)

Altitude:
    Kxxxxxx.xxx for kilometers  (K1000.13)

    Mxxxxxx.xxx for meters  (M1389.24)

    Fxxxxxx.xxx for feet  (F192133.73)

Lat/Lon: xxx.xxx for decimal  (-76.53)

    ddd,mm,ss for degrees, minutes, seconds (-60,23,22)

    (Lat and Lon must be specified in the same format,
    for ddd,mm,ss format, two commas each are required
    and decimals of arc-seconds are ignored)

Overheads
===========

::

    import unittest
    import logging
    import sys
    import csv
    import datetime
    import math
    from navtools.igrf11 import igrf11syn, deg2dm

    logger= logging.getLogger(__name__)
    details= sys.stderr # to see the test cases.
    # details= None # to silence the log.

    sample_output= "geomag70_linux/sample_out_IGRF11.txt"

Test Case
===========

Each test case is built from the "sample output" file
in the Geomag distribution.

::

    class Test_Geomag( unittest.TestCase ):
        def __init__( self, date, lat, lon, alt, coord, D_deg, D_min ):
            super( Test_Geomag, self ).__init__()
            self.date= date
            self.lat= lat
            self.lon= lon
            self.alt= alt
            self.coord= coord
            self.D_deg= D_deg
            self.D_min= D_min

::

        def runTest( self ):

            x, y, z, f = igrf11syn( self.date, self.lat*math.pi/180, self.lon*math.pi/180, self.alt, coord=self.coord )
            D = 180.0/math.pi*math.atan2(y, x) # Declination

            deg, min = deg2dm( D )

            logger.debug( "Result: {0:10.5f} {1} K{2:<6.1f} {3:<10.3f} {4:<10.3f} {5:5s} {6:5s}".format(
                self.date, self.coord, self.alt, self.lat, self.lon, str(deg)+"d", str(min)+"m" ),
                )

            self.assertEqual( self.D_deg, "{0}d".format(deg) )
            self.assertEqual( self.D_min, "{0}m".format(min) )


suite Function
=================

These utility functions parse the wide variety of inputs provided.

::

    def parse_date( date_str ):
        if ',' in date_str:
            # y,m,d format.
            dt= datetime.date( *map(int, date_str.split(',') ) )
            first_of_year= dt.replace( month=1, day=1 )
            date= dt.year + (dt.toordinal() - first_of_year.toordinal())/365.242
        else:
            # floating-point date
            date= float(date_str)
        return date

    def parse_altitude( alt_str ):
        if alt_str.startswith("F"):
            # Feet to km
            alt= float(alt_str[1:])/3280.8399
        elif alt_str.startswith("M"):
            # m to km
            alt= float(alt_str[1:])/1000
        elif alt_str.startswith("K"):
            alt= float(alt_str[1:])
        else:
            raise Exception( "Unknown altitude units" )
        return alt

    def parse_lat_lon( ll_str ):
        if ',' in ll_str:
            if ll_str.startswith('-'):
                sign= -1
                ll_str= ll_str[1:]
            else:
                sign= +1
            d, m, s = (float(x) if x else 0.0 for x in ll_str.split(','))
            return sign*(d + (m + s/60)/60)
        else:
            return float(ll_str)

The suite is a set of test cases built from the Geomag sample output file.

::

    def suite():
        s= unittest.TestSuite()
        with open(sample_output,"r") as expected:
            rdr= csv.DictReader( expected, delimiter=' ', skipinitialspace=True )
            for row in rdr:
                logger.debug( "Source: {0:10s} {1} {2:7s} {3:10s} {4:10s} {5:5s} {6:5s}".format(
                    row['Date'], row['Coord-System'], row['Altitude'], row['Latitude'], row['Longitude'], row['D_deg'], row['D_min'] ),
                    )

                date= parse_date( row['Date'] )
                lat= parse_lat_lon( row['Latitude'] )
                lon= parse_lat_lon( row['Longitude'] )
                alt= parse_altitude( row['Altitude'] )

                case= Test_Geomag( date, lat, lon, alt, row['Coord-System'],
                    row['D_deg'], row['D_min']  )
                s.addTest( case )
        return s

Main Script
==============

Run the test suite from the test classes. We can use this for debugging purposes.

::

    if __name__ == "__main__":
        logging.basicConfig( stream=sys.stdout, level=logging.DEBUG )
        r = unittest.TextTestRunner(sys.stdout, verbosity=2)
        result= r.run( suite() )
        logging.shutdown()
        sys.exit(len(result.failures))



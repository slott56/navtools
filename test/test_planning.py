#!/usr/bin/env python3

# ###############################################################
# Test Planning
# ###############################################################
#
# There are a number of test cases for route planning embodied
# in the :py:mod:`planning` module.
#
# Overheads
# ==========
#
# ::

import unittest
import sys
import csv
from io import StringIO
import datetime
import os
from navtools.navigation import LatLon, declination, Angle2
from navtools.planning import (
    RoutePoint, RoutePoint_Rhumb, RoutePoint_Rhumb_Magnetic,
    SchedulePoint,
    csv_to_RoutePoint, gpx_to_RoutePoint,
    gen_rhumb, gen_mag_bearing, gen_schedule,
    write_csv, plan,
    )

# Test Cases
# =============
#
# csv_to_RoutePoint function
# ------------------------------
#
# ::

csv_data = """\
Piankatank 6,37º31.99'N,076º19.02'W,
Jackson Creek Entrance,37º32.58'N,076º19.17'W,
"""

# ::

class Test_csv_to_RoutePoint( unittest.TestCase ):
    def setUp( self ):
        data_file= StringIO( csv_data )
        self.generator= csv_to_RoutePoint( data_file )
    def test_should_parse( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "Piankatank 6", points[0].name )
        self.assertAlmostEqual( 37.53316666, points[0].point.lat.deg )
        self.assertAlmostEqual( -76.3170, points[0].point.lon.deg )
        self.assertEqual( "Jackson Creek Entrance", points[1].name )
        self.assertAlmostEqual( 37.5430, points[1].point.lat.deg )
        self.assertAlmostEqual( -76.3195, points[1].point.lon.deg )

# gpx_to_RoutePoint function
# ---------------------------
#
# ::

gpx_data = """\
<?xml version="1.0" encoding="utf-8"?>
<gpx version="1.1" creator="GPSNavX"
xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
<rte>
<name>Whitby Rendezvous</name>
<rtept lat="37.533195" lon="-76.316963">
<name>Piankatank 6</name>
<sym>BUOYR</sym>
</rtept>
<rtept lat="37.542961" lon="-76.319580">
<name>Jackson Creek Entrance</name>
<sym>BOATSLIP</sym>
</rtept>
</rte>
</gpx>
"""

# ::

class Test_gpx_to_RoutePoint( Test_csv_to_RoutePoint ):
    def setUp( self ):
        data_file= StringIO( gpx_data )
        self.generator= gpx_to_RoutePoint( data_file )
    def test_should_parse( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "Piankatank 6", points[0].name )
        self.assertAlmostEqual( 37.533195, points[0].point.lat.deg )
        self.assertAlmostEqual( -76.316963, points[0].point.lon.deg )
        self.assertEqual( "Jackson Creek Entrance", points[1].name )
        self.assertAlmostEqual( 37.542961, points[1].point.lat.deg )
        self.assertAlmostEqual( -76.319580, points[1].point.lon.deg )

# gen_rhumb Function
# ------------------------
#
# ::

class Test_gen_rhumb( unittest.TestCase ):
    def setUp( self ):
        route = [
            RoutePoint( "Piankatank 6", "37.533195", "-76.316963", "",
                LatLon("37.533195N", "76.316963W") ),
            RoutePoint( "Jackson Creek Entrance", "37.542961", "-76.319580", "",
                LatLon("37.542961N", "76.319580W") ),
        ]
        self.generator= gen_rhumb( iter( route ) )
    def test_should_compute_rhumb( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "Piankatank 6", points[0].point.name )
        self.assertAlmostEqual( 0.59944686, points[0].distance )
        self.assertAlmostEqual( 348.0038223, points[0].bearing.deg )

        # Last is always None -- no more places to go.
        self.assertEqual( "Jackson Creek Entrance", points[1].point.name )
        self.assertIsNone( points[1].distance )
        self.assertIsNone( points[1].bearing )


# gen_mag_bearing Function
# ------------------------
#
# ::

class Test_gen_mag_bearing( unittest.TestCase ):
    def setUp( self ):
        route = [
            RoutePoint_Rhumb(
                RoutePoint(  "Piankatank 6", "37.533195", "-76.316963", "",
                LatLon("37.533195N", "76.316963W"),
                 ),
                 0.59944686,
                 Angle2.fromdegrees(348.0038223),
                ),
            RoutePoint_Rhumb(
                RoutePoint( "Jackson Creek Entrance", "37.542961", "-76.319580", "",
                LatLon("37.542961N", "76.319580W")
                ),
                None,
                None,
            ),
        ]
        self.generator= gen_mag_bearing( iter( route ), declination, date=datetime.date(2012,4,18) )
    def test_should_compute_magnetic_bearing( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "Piankatank 6", points[0].point.point.name )
        self.assertAlmostEqual( 0.59944686, points[0].distance )
        self.assertAlmostEqual( 348.0038223, points[0].true_bearing.deg )
        self.assertAlmostEqual( 337.0867231, points[0].magnetic.deg )

        # Last is always None -- no more places to go.
        self.assertEqual( "Jackson Creek Entrance", points[1].point.point.name )
        self.assertIsNone( points[1].distance )
        self.assertIsNone( points[1].true_bearing )
        self.assertIsNone( points[1].magnetic )

# gen_schedule Function
# ------------------------
#
# ::

class Test_gen_schedule( unittest.TestCase ):
    def setUp( self ):
        route = [
            RoutePoint_Rhumb_Magnetic(
                RoutePoint_Rhumb(
                    RoutePoint(  "Piankatank 6", "37.533195", "-76.316963", "",
                    LatLon("37.533195N", "76.316963W"),
                     ),
                     0.59944686,
                     Angle2.fromdegrees(348.0038223),
                ),
                0.59944686,
                Angle2.fromdegrees(348.0038223),
                Angle2.fromdegrees(337.0867607),
            ),
            RoutePoint_Rhumb_Magnetic(
                RoutePoint_Rhumb(
                    RoutePoint( "Jackson Creek Entrance", "37.542961", "-76.319580", "",
                    LatLon("37.542961N", "76.319580W")
                    ),
                    None,
                    None,
                ),
                None,
                None,
                None,
            ),
        ]
        self.generator= gen_schedule( iter( route ), speed=5 )
    def test_should_compute_magnetic_bearing( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "Piankatank 6", points[0].point.point.name )
        self.assertAlmostEqual( 0.59944686, points[0].distance )
        self.assertAlmostEqual( 348.0038223, points[0].true_bearing.deg )
        self.assertAlmostEqual( 337.0867607, points[0].magnetic.deg )
        self.assertAlmostEqual( 0.59944686, points[0].running )
        self.assertAlmostEqual( 7.19336232, points[0].elapsed_min )
        self.assertEqual( "00h 07m", points[0].elapsed_hm )

        # Last is always None -- no more places to go.
        self.assertEqual( "Jackson Creek Entrance", points[1].point.point.name )
        self.assertIsNone( points[1].distance )
        self.assertIsNone( points[1].true_bearing )
        self.assertIsNone( points[1].magnetic )
        self.assertIsNone( points[1].running )
        self.assertIsNone( points[1].elapsed_min )
        self.assertIsNone( points[1].elapsed_hm )

# write_csv Function
# ---------------------
#
# ::

class Test_write_csv( unittest.TestCase ):
    def setUp( self ):
        self.schedule = [
            SchedulePoint(
                    RoutePoint_Rhumb(
                        RoutePoint(  "Piankatank 6", "37.533195", "-76.316963", "",
                        LatLon("37.533195N", "76.316963W"),
                         ),
                         0.59944686,
                         Angle2.fromdegrees(348.0038223),
                    ),
                0.59944686,
                Angle2.fromdegrees(348.0038223),
                Angle2.fromdegrees(337.0867607),
                0.59944686,
                7.19336232,
                "00h 07m",
            ),
            SchedulePoint(
                    RoutePoint_Rhumb(
                        RoutePoint( "Jackson Creek Entrance", "37.542961", "-76.319580", "",
                        LatLon("37.542961N", "76.319580W")
                        ),
                        None,
                        None,
                    ),
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]
        self.target= StringIO()
        self.expected= """\
Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM\r
Piankatank 6,37 31.992N,076 19.018W,,0.59945,348.0,337.0,0.59945,00h 07m\r
Jackson Creek Entrance,37 32.578N,076 19.175W,,,,,,\r
"""
    def test_should_write( self ):
        write_csv( iter(self.schedule), self.target )
        self.assertEqual( self.expected, self.target.getvalue() )

# plan Function
# ---------------------
#
# Note. This is highly Python release dependent because the distance
# values may differ several decimal places in. The values *shuold*
# be truncated and compared a little more rationally.
#
# ::

class Test_plan_CSV( unittest.TestCase ):
    maxDiff= None
    def setUp( self ):
        with open('temp1.csv', 'w') as fixture:
            fixture.write( csv_data )
        self.expected= """\
Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM
Piankatank 6,37 31.990N,076 19.020W,,0.60228,349.0,338.0,0.60228,00h 07m
Jackson Creek Entrance,37 32.580N,076 19.170W,,,,,,
"""
    def tearDown(self):
        try:
            os.unlink('temp1.csv')
        except OSError:
            pass
        try:
            os.unlink('temp1 Schedule.csv')
        except OSError:
            pass
    def test_should_plan( self ):
        plan( "temp1.csv", date=datetime.date(2012,4,18) )
        with open('temp1 Schedule.csv') as result:
            self.assertEqual( self.expected, result.read() )

class Test_plan_GPX( unittest.TestCase ):
    maxDiff= None
    def setUp( self ):
        with open('temp2.gpx', 'w') as fixture:
            fixture.write( gpx_data )
        self.expected= """\
Name,Lat,Lon,Desc,Distance (nm),True Bearing,Magnetic Bearing,Distance Run,Elapsed HH:MM
Piankatank 6,37 31.992N,076 19.018W,,0.59945,348.0,337.0,0.59945,00h 07m
Jackson Creek Entrance,37 32.578N,076 19.175W,,,,,,
"""
    def tearDown(self):
        try:
            os.unlink('temp2.gpx')
        except OSError:
            pass
        try:
            os.unlink('temp2 Schedule.csv')
        except OSError:
            pass
    def test_should_plan( self ):
        plan( "temp2.gpx", date=datetime.date(2012,4,18) )
        with open('temp2 Schedule.csv') as result:
            self.assertEqual( self.expected, result.read() )

# suite Function
# ================
#
# Build a suite from the test classes.
#
# ::

def suite():
    s= unittest.TestSuite()
    for c in Test_csv_to_RoutePoint, Test_gpx_to_RoutePoint, Test_gen_rhumb, Test_gen_mag_bearing, Test_gen_schedule, Test_write_csv, Test_plan_CSV, Test_plan_GPX:
        s.addTests( unittest.defaultTestLoader.loadTestsFromTestCase(c) )
    return s

# Main Script
# ================
#
# Run the test suite from the test classes. We can use this for debugging purposes.
#
# ::

if __name__ == "__main__":
    import sys
    print( sys.version )
    unittest.main()

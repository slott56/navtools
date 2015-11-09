#!/usr/bin/env python3

# ###############################################################
# Test Analysis
# ###############################################################
#
# There are a number of test cases for track analysis in
# the :py:mod:`analysis` module.
#
# Overheads
# ==========
#
# ::

import unittest
import sys
from io import StringIO
from navtools.navigation import LatLon, declination, Angle2
from navtools.analysis import *

# Test Cases
# =============
#
# csv_to_LogEntry function with GPSNavX Data
# --------------------------------------------
#
# ::

csv_NavX_data = """\
2011-06-04 13:12:32 +0000,37.549225,-76.330536,219,3.6,,,,,,
2011-06-04 13:12:43 +0000,37.549084,-76.330681,186,3.0,,,,,,
"""

# ::

class Test_csv_to_LogEntry_NavX( unittest.TestCase ):
    def setUp( self ):
        data_file= StringIO( csv_NavX_data )
        self.generator= csv_to_LogEntry( data_file )
    def test_should_parse( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "2011-06-04 13:12:32 +0000", points[0].time.strftime( "%Y-%m-%d %H:%M:%S %z" ) )
        self.assertAlmostEqual( 37.549225, points[0].point.lat.deg )
        self.assertAlmostEqual( -76.330536, points[0].point.lon.deg )
        self.assertEqual( "2011-06-04 13:12:43 +0000", points[1].time.strftime( "%Y-%m-%d %H:%M:%S %z" ) )
        self.assertAlmostEqual( 37.549084, points[1].point.lat.deg )
        self.assertAlmostEqual( -76.330681, points[1].point.lon.deg )

# csv_to_LogEntry function with Manual Data
# --------------------------------------------
#
# ::

csv_Manual_data = """\
Time,Lat,Lon,COG,SOG,Rig,Engine,windAngle,windSpeed,Location
9:21 AM,37 50.424N,076 16.385W,None,0,None,1200 RPM,,,Cockrell Creek
10:06 AM,37 47.988N,076 16.056W,None,6.6,None,1500 RPM,315,7.0,
"""

# ::

class Test_csv_to_LogEntry_Man( unittest.TestCase ):
    def setUp( self ):
        data_file= StringIO( csv_Manual_data )
        self.generator= csv_to_LogEntry( data_file )
    def test_should_parse( self ):
        points= list( self.generator )
        #for p in points: print( repr(p) )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "09:21", points[0].time.strftime("%H:%M") )
        self.assertAlmostEqual( 37.8404, points[0].point.lat.deg )
        self.assertAlmostEqual( -76.2730833, points[0].point.lon.deg )
        self.assertEqual( "10:06", points[1].time.strftime("%H:%M")  )
        self.assertAlmostEqual( 37.7998, points[1].point.lat.deg )
        self.assertAlmostEqual( -76.2676, points[1].point.lon.deg )

# gpx_to_LogEntry function
# ---------------------------
#
# This is difficult to test because we don't have a real GPX track
# file.
#
# ::

gpx_data = """\
<?xml version="1.0" encoding="utf-8"?>
<gpx version="1.1" creator="GPSNavX"
xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
<trk>
<trkseg>
<trkpt lat="37.534599" lon="-76.313622">
<time>2010-09-06T16:50:42Z</time>
</trkpt>
<trkpt lat="37.535213" lon="-76.312889">
<time>2010-09-06T16:51:34Z</time>
</trkpt>
</trkseg>
</trk>
</gpx>
"""

# ::

class Test_gpx_to_LogEntry( unittest.TestCase ):
    def setUp( self ):
        data_file= StringIO( gpx_data )
        self.generator= gpx_to_LogEntry( data_file )
    def test_should_parse( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "2010-09-06 16:50:42 +0000", points[0].time.strftime( "%Y-%m-%d %H:%M:%S %z" ) )
        self.assertAlmostEqual( 37.534599, points[0].point.lat.deg )
        self.assertAlmostEqual( -76.313622, points[0].point.lon.deg )
        self.assertEqual( "2010-09-06 16:51:34 +0000", points[1].time.strftime( "%Y-%m-%d %H:%M:%S %z" ) )
        self.assertAlmostEqual( 37.535213, points[1].point.lat.deg )
        self.assertAlmostEqual( -76.312889, points[1].point.lon.deg )

# gen_rhumb Function
# ------------------------
#
# ::

class Test_gen_rhumb( unittest.TestCase ):
    def setUp( self ):
        route = [
            LogEntry( datetime.datetime(2012,4,17,9,21), "37.533195", "-76.316963",
                LatLon("37.533195N", "76.316963W"),
                {'Engine': '1200 RPM', 'SOG': '0', 'Lon': '076 16.385W', 'windSpeed': '', 'Location': 'Cockrell Creek', 'COG': 'None', 'Time': '9:21 AM', 'Lat': '37 50.424N', 'Rig': 'None', 'windAngle': ''} ),
            LogEntry( datetime.datetime(2012,4,17,10,6), "37.542961", "-76.319580",
                LatLon("37.542961N", "76.319580W"),
                {'Engine': '1500 RPM', 'SOG': '6.6', 'Lon': '076 16.056W', 'windSpeed': '7.0', 'Location': '', 'COG': 'None', 'Time': '10:06 AM', 'Lat': '37 47.988N', 'Rig': 'None', 'windAngle': '315'} ),
        ]
        self.generator= gen_rhumb( iter( route ) )
    def test_should_compute_rhumb( self ):
        points= list( self.generator )
        self.assertEqual( 2, len(points) )
        self.assertEqual( "09:21 AM", points[0].point.time.strftime("%I:%M %p") )
        self.assertAlmostEqual( 0.59944686, points[0].distance )
        self.assertAlmostEqual( 348.0038223, points[0].bearing.deg )
        self.assertAlmostEqual( 45*60, points[0].delta_time.seconds )

        # Last is always None -- no more places to go.
        self.assertEqual( "10:06 AM", points[1].point.time.strftime("%I:%M %p") )
        self.assertIsNone( points[1].distance )
        self.assertIsNone( points[1].bearing )
        self.assertIsNone( points[1].delta_time )

# Utility to compare CSV output
# ------------------------------
#
# Because CSV column orders can't easily be controlled, we need to compare
# the actual and expected CSV files in a way that permits column orders to
# vary.
#
# We'll compare two CSV files by building the list-of-dict objects that we can
# then compare for equality. This is a bit tricky because we're comparing
# text values to each other, which can have some complications with floating-point
# representation.
#
# ::

from itertools import zip_longest
class Test_CSV_Compare( unittest.TestCase ):
    def assertEqualCSV( self, expected_txt, actual_txt ):
        ex_rdr= csv.DictReader( StringIO(expected_txt) )
        ex_data= list( ex_rdr )
        ac_rdr= csv.DictReader( StringIO(actual_txt) )
        ac_data= list( ac_rdr )
        for ex_row, ac_row in zip_longest(ex_data, ac_data):
            for k in sorted(set(ex_row.keys())|set(ac_row.keys())):
                self.assertEqual( ex_row.get(k).strip(), ac_row.get(k).strip(),
                    "{0}: {1} != {2}".format(k, ex_row.get(k), ac_row.get(k)) )

# write_csv Function
# ---------------------
#
# Do we write CSV from a track?
#
# ::

class Test_write_csv( Test_CSV_Compare ):
    def setUp( self ):
        self.track = [
            LogEntry_Rhumb(
                LogEntry( datetime.datetime(2012,4,17,9,21), "37.533195", "-76.316963",
                    LatLon("37.533195N", "76.316963W"),
                    {'Engine': '1200 RPM', 'SOG': '0', 'Lon': '076 16.385W', 'windSpeed': '', 'Location': 'Cockrell Creek', 'COG': 'None', 'Time': '9:21 AM', 'Lat': '37 50.424N', 'Rig': 'None', 'windAngle': ''} ),
                0.59944686,
                Angle2.fromdegrees(348.0038223),
                datetime.timedelta(seconds=45*60),
                ),
            LogEntry_Rhumb(
                LogEntry( datetime.datetime(2012,4,17,10,6), "37.542961", "-76.319580",
                    LatLon("37.542961N", "76.319580W"),
                    {'Engine': '1500 RPM', 'SOG': '6.6', 'Lon': '076 16.056W', 'windSpeed': '7.0', 'Location': '', 'COG': 'None', 'Time': '10:06 AM', 'Lat': '37 47.988N', 'Rig': 'None', 'windAngle': '315'} ),
                None,
                None,
                None,
                ),
        ]
        self.target= StringIO()
        self.expected= """\
Engine,windSpeed,COG,Location,SOG,Time,Lat,Rig,Lon,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time\r
1200 RPM,,None,Cockrell Creek,0,9:21 AM,37 50.424N,None,076 16.385W,,0.59945,348.0,2012-04-17 09:21:00,0:45:00,0.59945,0:45:00\r
1500 RPM,7.0,None,,6.6,10:06 AM,37 47.988N,None,076 16.056W,315,,,2012-04-17 10:06:00,,0.59945,0:45:00\r
"""
    def test_should_write( self ):
        write_csv( iter(self.track), self.target )
        self.assertEqualCSV( self.expected, self.target.getvalue() )

# analyze Function
# ---------------------
#
# Since the CSV writer now rounds values to a sensible number of decimal places,
# these results can be platform- and release-independent.
#
# ::

class Test_analyze_CSV_NavX( Test_CSV_Compare ):
    maxDiff= None
    def setUp( self ):
        with open('temp1.csv', 'w', newline='') as fixture:
            fixture.write( csv_NavX_data )
        self.expected= """\
comment,sog,windSpeed,longitude,latitude,depth,cog,date,speed,heading,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
,3.6,,-76.330536,37.549225,,219,2011-06-04 13:12:32 +0000,,,,0.01092,219.0,2011-06-04 13:12:32+00:00,0:00:11,0.01092,0:00:11
,3.0,,-76.330681,37.549084,,186,2011-06-04 13:12:43 +0000,,,,,,2011-06-04 13:12:43+00:00,,0.01092,0:00:11
"""
    def tearDown(self):
        try:
            os.unlink('temp1.csv')
        except OSError:
            pass
        try:
            os.unlink('temp1 Distance.csv')
        except OSError:
            pass
    def test_should_plan( self ):
        analyze( "temp1.csv" )
        with open('temp1 Distance.csv') as result:
            self.assertEqualCSV( self.expected, result.read() )

# This has a default-date assumption.
#
# ::

class Test_analyze_CSV_Manual( Test_CSV_Compare ):
    maxDiff= None
    def setUp( self ):
        with open('temp2.csv', 'w', newline='') as fixture:
            fixture.write( csv_Manual_data )
        self.expected= """\
Engine,SOG,Lon,windSpeed,Location,COG,Time,Lat,Rig,windAngle,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
1200 RPM,0,076 16.385W,,Cockrell Creek,None,9:21 AM,37 50.424N,None,,2.45148,174.0,2012-04-18 09:21:00,0:45:00,2.45148,0:45:00
1500 RPM,6.6,076 16.056W,7.0,,None,10:06 AM,37 47.988N,None,315,,,2012-04-18 10:06:00,,2.45148,0:45:00
"""
    def tearDown(self):
        try:
            os.unlink('temp2.csv')
        except OSError:
            pass
        try:
            os.unlink('temp2 Distance.csv')
        except OSError:
            pass
    def test_should_plan( self ):
        analyze( "temp2.csv", date=datetime.date(2012,4,18) )
        with open('temp2 Distance.csv') as result:
            self.assertEqualCSV( self.expected, result.read() )

# ::

class Test_analyze_GPX( Test_CSV_Compare ):
    maxDiff= None
    def setUp( self ):
        with open('temp3.gpx', 'w', newline='') as fixture:
            fixture.write( gpx_data )
        self.expected= """\
lat,lon,time,calc_distance,calc_bearing,calc_time,calc_elapsed,calc_total_dist,calc_total_time
37.534599,-76.313622,2010-09-06T16:50:42Z,0.05076, 43.0,2010-09-06 16:50:42+00:00,0:00:52,0.05076,0:00:52
37.535213,-76.312889,2010-09-06T16:51:34Z,,,2010-09-06 16:51:34+00:00,,0.05076,0:00:52
"""
    def tearDown(self):
        try:
            os.unlink('temp3.gpx')
        except OSError:
            pass
        try:
            os.unlink('temp3 Distance.csv')
        except OSError:
            pass
    def test_should_plan( self ):
        analyze( "temp3.gpx" )
        with open('temp3 Distance.csv') as result:
            self.assertEqualCSV( self.expected, result.read() )


# suite Function
# ================
#
# Build a suite from the test classes.
#
# ::

def suite():
    s= unittest.TestSuite()
    for c in Test_csv_to_LogEntry_NavX, Test_csv_to_LogEntry_Man, Test_gpx_to_LogEntry, Test_gen_rhumb, Test_write_csv, Test_analyze_CSV_NavX, Test_analyze_CSV_Manual, Test_analyze_GPX:
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
    result= unittest.TextTestRunner(verbosity=2).run(suite())
    sys.exit(len(result.failures))

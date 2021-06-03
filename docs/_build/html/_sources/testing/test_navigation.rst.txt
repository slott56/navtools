..    #!/usr/bin/env python3

###############################################################
Test Navigation
###############################################################

The :py:mod:`navigation` module includes the rather complex calculations
for range and bearing.  It also "wraps" the declination from
IGRF11.

Overheads
==========

::

    import unittest
    import sys
    import datetime
    import doctest
    import navtools.navigation
    from navtools.navigation import (Angle, GlobeAngle, Angle2, LatLon, KM, NM,
        declination, destination, range_bearing)

Test Cases
=============

We need to be sure the core abstractions and functions work.

Globe Angle and Angle classes
------------------------------

We'll test the (older) :class:`GlobeAngle` class, which will
also test the :class:`Angle` class. 

..  todo:: Remove Tests for GlobeAngle and Angle.

::

    class Test_GlobeAngle( unittest.TestCase ):
        """Also tends to test Angle."""
        def test_should_create_1( self ):
            lat=GlobeAngle("50 21 50N")
            self.assertAlmostEqual( 50.36388888, lat.deg )
            self.assertEqual( (50, 21, 50.0, "N"), lat.dms )
        def test_should_create_2( self ):
            lon=GlobeAngle("004 09 25W")
            self.assertAlmostEqual( 4.1569444, lon.deg )
            self.assertEqual( (4, 9, 25.0, "W"), lon.dms )
        def test_should_create_3( self ):
            lat=GlobeAngle("42 21 04N")
            self.assertAlmostEqual( 42.3511111, lat.deg )
            self.assertEqual( (42, 21, 4.0, "N"), lat.dms )
        def test_should_create_4( self ):
            lon=GlobeAngle("071 02 27W")
            self.assertAlmostEqual( 71.0408333, lon.deg )
            self.assertEqual( (71, 2, 27.0, "W"), lon.dms )


Angle2 Class
--------------

This is a replacement for Angle/GlobeAngle. The doctest cases will also cover this.
See the :func:`suite` function, below.

LatLon Class
------------------------

This is a pair of :class:`Angle2` objects.

::

    class Test_LatLon( unittest.TestCase ):
        def setUp( self ):
            self.p1= LatLon( lat="50 21 50N", lon="004 09 25W" )
        def test_should_format_dms( self ):
            self.assertEqual( ("50 21 50.0N","004 09 25.0W"), self.p1.dms )
        def test_should_format_dm( self ):
            self.assertEqual( ("50 21.833N","004 9.417W"), self.p1.dm )
        def test_should_format_d( self ):
            self.assertEqual( ("50.364N","004.157W"), self.p1.d )
        
range_bearing Function
------------------------

There are two parts to this, the haversine function, and the bearing 
function.

We'll use a single pair of points from the web to show that this works.  

::

    class Test_Range_Bearing( unittest.TestCase ):
        def test_should_compute( self ):
            p1= LatLon( lat=Angle2.fromstring("50 21 50N"), lon=Angle2.fromstring("004 09 25W") )
            p2= LatLon( lat=Angle2.fromstring("42 21 04N"), lon=Angle2.fromstring("071 02 27W") )
            #print( "p1 = {0}".format( p1.dms ) )
            #print( "p2 = {0}".format( p2.dms ) )
            d, brg = range_bearing( p1, p2, R=KM )
            self.assertEqual( 5196, int(d) )
            self.assertEqual( (260, 7, 38), tuple(map(int,map(round,brg.dms))) )
            d, brg = range_bearing( p1, p2, R=NM )
            self.assertEqual( 2805, int(d) )
            self.assertEqual( (260, 7, 38), tuple(map(int,map(round,brg.dms))) )

destination Function
------------------------

This is the inverse of the haversine function. Again, we'll use a single example

::

    class Test_Destination( unittest.TestCase ):
        def test_should_compute( self ):
            p1= LatLon( lat=Angle2.fromstring("51 07 32N"), lon=Angle2.fromstring("001 20 17E") )
            #print( "p1 = {0}".format( p1.dms ) )
            bearing= Angle( "116 38 10" )
            #print( "theta = {0}".format( bearing.dms ) )
            p2= destination( p1, 40.23, bearing, R=KM )
            self.assertEqual( ("50 57 48.1N", "001 51 08.8E"), p2.dms )
            self.assertEqual( ("50.963N", "001.852E"), p2.d )

declination Function
------------------------

The magnetic declination is imported from the **igrf11** implementation.
This has it's own set of use cases. In this example, we're really doing
a kind of integration test to be sure that the :func:`declination` function
properly reflects **igrf11**.

::

    class Test_Declination( unittest.TestCase ):
        """Varies with current date; not easy to test with the API."""
        def test_should_compute_chesapeake( self ):
            """About 11d 0m W, (almost exactly -11) for 4/18/2012"""
            p1= LatLon( lat=Angle2.fromdegrees(37.8311, "N"), lon=Angle2.fromdegrees(76.2819, "W") )
            #print( "p1 = {0}".format( p1.dms ) )
            d= declination( p1, date=datetime.date(2012,4,18) )
            #print( "declination= {0}".format(d.dm) )
            self.assertAlmostEqual( -11, d.dm[0] )
        def test_should_compute_equator( self ):
            """somewhere near -5d 50m for 4/18/2012"""
            p1= LatLon( lat=Angle2.fromstring("0.0N"), lon=Angle2.fromstring( "0.0E" ) )
            #print( "p1 = {0}".format( p1.dms ) )
            d= declination( p1, date=datetime.date(2012,4,18)  )
            #print( "declination= {0}".format(d.dm) )
            self.assertAlmostEqual( -5, d.dm[0] )
            self.assertTrue( 45 <= d.dm[1] <= 55 )

suite Function
================

Build a suite from the test classes.

::

    def suite():
        s= unittest.TestSuite()
        for c in Test_GlobeAngle, Test_LatLon, Test_Range_Bearing, Test_Destination, Test_Declination:
            s.addTests( unittest.defaultTestLoader.loadTestsFromTestCase(c) )
        s.addTests(doctest.DocTestSuite(navtools.navigation))
        return s

Main Script
================

Run the test suite from the test classes. We can use this for debugging purposes.

::

    if __name__ == "__main__":
        import sys
        print( sys.version )
        result= unittest.TextTestRunner(verbosity=2).run(suite())
        sys.exit(len(result.failures))

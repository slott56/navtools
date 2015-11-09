#!/usr/bin/env python3

# ##################
# Main Test Script
# ##################
#
# This module imports the other test modules and builds a complete suite
# from the individual module suites.
#
# ::

"""navtools test script."""
from __future__ import print_function
import unittest
import sys
import warnings
import test.test_igrf11
import test.test_navigation
import test.test_planning
import test.test_analysis

# Construction of an overall suite depends on each module providing
# and easy-to-use :py:func:`suite` function that returns the module's suite.
#    
# ::

def suite():
    s= unittest.TestSuite()
    s.addTests( test.test_igrf11.suite() )
    s.addTests( test.test_navigation.suite() )
    s.addTests( test.test_planning.suite() )
    s.addTests( test.test_analysis.suite() )
    return s
    
def run():
    return unittest.TextTestRunner(warnings='once').run(suite())
    
if __name__ == "__main__":
    result= run()
    sys.exit(len(result.failures))

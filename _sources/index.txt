.. The NavTools documentation master file, created by
   sphinx-quickstart on Tue Apr 17 07:46:24 2012.

================================================================
NavTools 2.1
================================================================

NavTools helps with planning, execution and analysis of
simple waypoint-based navigation using great-circle routes.
The current implementation uses spreadsheets and downloaded
waypoint files.

This is focused on Python 3.4.

With ``from __future__ import division, print_function, unicode_literals`` it may
also work in Python 2.x.

Introduction
=============

.. toctree::
   :maxdepth: 2

   introduction

Implementation
=================

.. toctree::
   :maxdepth: 1

   navigation
   planning
   analysis
   igrf11
   navtools_init

Testing
==========

.. toctree::
   :maxdepth: 2

   testing/index

Other Overheads
=================

.. toctree::
   :maxdepth: 1

   build
   installation

The TODO List
===============

If you have PySerial installed, you could write applications to read common
GPS devices and decode the messages. This would allow you to track
waypoints, and possibly even build an anchor alarm monitor.

..  todolist::

Indices and Tables
==================

* :ref:`genindex`
* :ref:`search`

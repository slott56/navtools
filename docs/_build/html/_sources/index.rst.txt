.. The NavTools documentation master file, created by
   sphinx-quickstart on Tue Apr 17 07:46:24 2012.

================================================================
NavTools 2021.06
================================================================

NavTools helps with planning, execution and analysis of
simple waypoint-based navigation using rhumb-line routes.
It's suitable for small craft making relatively short passages
where the great circle accuracy isn't critical.

This is focused on Python 3.9.

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
   opencpn_table
   igrf11

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

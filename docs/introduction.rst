.. include:: <isonum.txt>

Overview
=========

The essential story is this:

    "As skipper of sailing vessel *Red Ranger*,
    I need to create detailed voyage plans with distance,
    bearing, and estimated time of arrival to each mark or waypoint."

To put this story into context, we have a number of tools
for voyage planning, execution and analysis. This software fills
an essential gap among those tools. We'll look at the three areas
separately.

**Planning**.
Voyage planning involves locating courses that avoid navigational hazards
and make use of the available Aids to Navigation (ATONs).  In some cases,
tide and current are accounted for, as well as adverse weather.

For route planning, S/V *Red Ranger* carries three copies of the NOAA charts.

-   Paper charts.  A mixture of old and new.

-   The Jeppesen C-Map charts (http://www.c-map.com/) on an
    electronic chart plotter.

-   Several copies of and GPSNavX (http://www.gpsnavx.com/) and iNavX with the latest charts
    downloaded  from NOAA.  (http://www.charts.noaa.gov/RNCs/RNCs.shtml)

It's not simple to sketch a route on an electronic chart and transform this into
a schedule for sailing. Trying to do this is likely to introduce transcription errors.

There are numerous piloting techniques that apply to paper charts,
but the electronic chart support for these techniques is sketchy.

It would be better to do planning in a way that doesn't involve manual transcriptions.

**Execution**.
For sailing a particular voyage, S/V *Red Ranger* carries several ways of assuring
that she is on course.

-   Crew observation of the ATONs, landmarks, and seascape.

-   Paper charts and standard piloting techniques like dead reckoning,
    lines of position and course lines.

-   Electronic Chartplotter in the cockpit.
    (Standard Horizon `CP180i <http://www.standardhorizon.com/indexVS.cfm?cmd=DisplayProducts&ProdCatID=84&encProdID=491E084FB06B41812BEEF96C77A4A8E2&DivisionID=3&isArchived=1>`_)

-   GPSNavX on a MacBook Pro with its own GPS antenna (entirely separate from
    the chartplotter). (http://www.gpsnavx.com)

-   iNavX on a iPhones and iPad (http://www.inavx.com).
    This uses a separate Dual XGPS 150 antenna (http://gps.dualav.com/explore-by-product/xgps150a/).

All this tells where S/V *Red Ranger* is.
The important gap here is in contingency planning: knowing where
S/V *Red Ranger* should be.
Will she arrive on time?  Do we need to change course, or
use the auxiliary engine?  Do we need to look for an alternate
route or anchorage?

    *"The most dangerous piece of equipment is the calendar.
    The issue here is not maintaining a schedule, but sailing
    safely during daylight hours and leaving enough time to
    locate an anchorage before dark."*

The cockpit chartplotter provides an Estimated Time of Arrival (ETA)
to a specific waypoint based on current
course and speed.  It fails to provide any *planned* ETA to that waypoint that
serves as basis for comparison.

**Analysis**.
Logging is done several ways.

-   Electronic Chartplotter in the cockpit can record a track.  Currently,
    this is difficult to upload from the chartplotter.

-   OpenCPN on a MacBook Pro with its own GPS antenna.
    This means finding a way to secure a computer and leave it running
    to accumulate a track. This is not currently feasible on *Red Ranger*:
    there's no way to secure the computer or provide power.

-   iNavX on an iPhone or iPad with a separate GPS antenna.  This also requires
    leaving the phone running.  The track can be extracted through
    The X-Traverse web site.

-   Paper logging of heading, speed, wind and engine for each sail change,
    tack and each hour. This is currently how track analysis is handled.

There are no tools for retrospective analysis of logs at all.

Actors
=======

The primary actor for the use cases is the skipper of S/V *Red Ranger*.

Crew members may participate in the Execution.  However,
the ultimate responsibility lies with the skipper.

Voyage planning can be forwarded to shore crew as a kind of **Float Plan**.
Using SPOT Satellite communications, we can provide actual positions so
that the shore crew can compare positions against the voyage plan.

Use Cases
============

There are four broad use cases

-   `Execution Use Case`_

-   `Planning Use Case`_

-   `Float Plan Use Case`_

-   `Analysis Use Case`_

Execution Use Case
--------------------

Consider a sample sailing story.

1.  Actors depart their slip for a destination that involves :math:`n > 2`
    waypoints.

2.  System (cockpit chart plotter) shows ETA to waypoint 1.  Actors arrive
    at waypoint 1, switch system to waypoint 2.

3.  System shows ETA to waypoint 2.  Actors arrive
    at waypoint 2, switch system to waypoint 3.

#.  System shows ETA to waypoint 3.  Actors realize that arrival time is
    now unsafe (i.e., after dark).

At waypoint 1 -- due to adverse wind or currents -- *Red Ranger*
could have been behind the overall schedule, and the actors needed to know this
before setting course for waypoint 2.

This means that waypoint-by-waypoint planned ETA's are required for safe
execution of a schedule. The skipper can then compare planned ETA's with actual
ETA's to determine if contingency plans should be executed.

Planning Use Case
--------------------

The overall planning use case creates a
a waypoint-by-waypoint schedule or "Voyage Track".
See Bowditch [bowditch]_, section 2508, Constructing a Voyage Track.
Also, see Bowditch [bowditch]_, section 802 for more information on planning.

..  [bowditch] THE AMERICAN PRACTICAL NAVIGATOR.  http://www.irbs.com/bowditch/
    Also http://msi.nga.mil/MSISiteContent/StaticFiles/NAV_PUBS/APN/pub9.zip

1.  Actor plans the route in general.  This is a separate use
    case, outside the scope of this document.  System saves
    the route as a list of waypoints.

2.  Actor runs the "route_planning" application.  The system
    creates a "schedule" file with the waypoints plus
    additional information like distance to next waypoint,
    bearing of next waypoint, and ETA.

3.  Actor runs a spreadsheet application (Open Office Org, for example),
    and imports the schedule file.  This is a separate use
    case, outside the scope of this document.
    The system prints the resulting schedule or downloads it to an iPad.

The actor can cycle through this use case to create alternatives
and contingency plans.

Float Plan Use Case
-------------------

This involves two extensions to the `Planning Use Case`_ and _`Execution Use Case`.

-   Instead of merely printing or saving the plan for their own use,
    the skipper merges the plan with a description of the vessel and crew.
    This merged document becomes a float plan that can be sent to trusted
    on-shore people to act as a check-list against periodic notification.

    *Red Ranger* uses a Spot Tracker (http://findmespot.com/en/). A noon email
    is sent to confirm progress. An email could be sent for each waypoint,
    in addition to a noon position.

Analysis Use Case
---------------------

In retrospect, a track may be analyzed to compute actual distance
run (and times of arrival).  This can be compared with the plan to
improve the quality of the planning process.

The essential feature is analysis of the track created by the
GPS chartplotter (or computer) during sailing.

1.  Actor extracts the track from the GPS chartplotter.  This is a separate use
    case, outside the scope of this document.  System saves
    the track as a list of positions and times.

2.  Actor runs the "track_analysis" application.  The system
    creates a file with the track position plus
    additional information like distance to next position,
    cumulative time and cumulative distance.

3.  Actor runs a spreadsheet application (Open Office Org, for example),
    and imports the track file.  This is a separate use
    case, outside the scope of this document.
    The actor can then do additional analysis on these results.

Solution Overview
======================

The core planning software is OpenCPN (formerly GPSNavX) on an iMac.
This application can export a route file in GPX or CSV notation.

These GPX or CSV files can be imported and parsed by a Python application,
which can use a set of navigation calculations to compute
range, bearing, time for each leg.  It can also compute
an accumulated time and accumulated distance.

The Python application can emit CSV files for use in other desktop tools.
A spreadsheet can be used to print
a paper schedule is used for cockpit decision-making.
The actual time of arrival (ATA) to each waypoint can be logged.
The gap between ETA and ATA supports a number of sailing decisions.

A spreadsheet can be emailed to support a float plan. And a spreadsheet
can be used for retrospective analysis of voyages.

Data Interface
-----------------

The application reads GPX or CSV files and writes a CSV file.

It relies on an additional configuration parameter:
the anticipated speed of the boat on each leg of the course.  Ideally,
this is part of the GPX route.  GPXNavX, however, doesn't seem
to have an easy way to enter it.

Further, in a sailboat, a default value is the only thing
that makes sense.  Because of the hull speed of displacement
hulls (like S/V *Red Ranger*) there are further constraints.

:math:`1.34\times\sqrt{LWL}` is the maximum hull speed.
A more useful default sailing  speed is 5 kn.

An additional configuration detail is the magnetic compass deviation.
This varies from location to location around the planet, and also
with the date on which the trip is made. We can compute this using
the IGRF module.

Additional inputs could include details from the serial interface.
A USB GPS antenna (Like the `BU-535 <http://usglobalsat.com/p-688-bu-353-s4.aspx#images/product/large/688.jpg>`_) can be read via PySerial.

User Interface
------------------

The application is essentially a simple "filter".
Consistent with the **\*nix** philosophy, the
interface is a simple CLI that reads a file or standard input.

Here's a concept of how this might be used.

..  parsed-literal::

    python -m navtools.planning my_trip.gpx

This creates a :file:`my_trip Schedule.csv` file with the schedule
calculations.

..  parsed-literal::

    python -m navtools.analysis some_log.csv

This creates a :file:`some_log Distance.csv` file with the distance
and speed calculation.

Architecture
=============

There are several layers to this application.

1.  Fundamental Navigation Calculations.  These are the domain
    objects and functions. This includes GPS coordinates, range and bearing
    calculations.  It also includes compass deviation calculations.

2.  The GPX or CSV input parsing.  This will create Navigation
    objects from the input file.  These objects can then be transformed
    into the output CSV file.

3.  The "main" applications.  Each of these opens a file, acquires the
    input route, uses the navigation calculations, and creates
    the output schedule or analysis.

4.  The CLI overheads.

Based on the potential for reusability, we can package these
layers into several modules.

Consequences
=====================

This application is not "plugged into" OpenCPN or iNavX.  Consequently, planning
involves multiple steps with multiple tools.  A route is created, the ETA's examined, and
waypaints added to handle overnight anchorages.
Any change to a waypoint means the schedule must be recalculated.

A tool like ``scons`` can be used to "automate" creation of the
schedule from the :file:`.GPX` file.  Even this is not *totally* automated,
since someone has to remember to regenerate the schedule after
modifying the route.

Additional annotations that should be included on the paper chart
(like ATON details, for example) aren't present in this schedule.
The details aren't in the GPX file, and can't easily be located.

To an extent, the online light list http://www.navcen.uscg.gov/?pageName=lightLists
could be consulted to provide waypoint information.  Locating the lights
passed along the track as well as lights near each waypoint is challenging.


References
=====================

See [bowditch]_ Chapters 21 and 22.

See http://www.ngdc.noaa.gov/IAGA/vmod/igrf.html for information on the
magnetic declination.

The International Union of Geodesy and Geophysics (IUGG) defines mean radius values.
This is used to convert angles to distances.

GPX format is described here: http://www.topografix.com/gpx.asp

Here's the official GPX schema: http://www.topografix.com/GPX/1/1/

See http://williams.best.vwh.net/avform.htm

See http://www.movable-type.co.uk/scripts/latlong.html, |copy| 2002-2010 Chris Veness

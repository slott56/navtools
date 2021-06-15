"""
Tech spike to examine Lowrance USR
and Lowrance GPX to attempt to identify
symbol name and color codes.
"""
from navtools.waypoint_merge import opencpn_GPX_to_WayPoint, lowrance_GPX_to_WayPoint, lowrance_USR_to_WayPoint
from collections import defaultdict, Counter
from pathlib import Path
from typing import Optional


def t1() -> None:  # pragma: no cover
    opencpn = Path.cwd() / "data" / "2021 opencpn waypoints.gpx"
    with opencpn.open() as source:
        opencpn_wp = list(opencpn_GPX_to_WayPoint(source))
    for wp in opencpn_wp:
        print(wp)


def t2() -> dict[Optional[str], Optional[str]]:  # pragma: no cover
    plotter = Path.cwd() / "data" / "WaypointsRoutesTracks-2021.gpx"
    with plotter.open() as source:
        plotter_wp = list(lowrance_GPX_to_WayPoint(source))
    # for wp in plotter_wp:
    #    print(wp)
    print(f"{plotter}: {len(plotter_wp)}")
    syms = {wp.name: wp.sym for wp in plotter_wp}
    return syms


def t3() -> dict[Optional[str], tuple[str, str]]:  # pragma: no cover
    plotter = Path.cwd() / "data" / "WaypointsRoutesTracks.usr"
    with plotter.open("rb") as source:
        plotter_wp = list(lowrance_USR_to_WayPoint(source))
    # for wp in plotter_wp:
    #    print(wp)
    print(f"{plotter}: {len(plotter_wp)}")
    syms = {
        wp.name: (wp.extensions["icon_id"], wp.extensions["color_id"])
        for wp in plotter_wp
    }
    return syms


def icon_table() -> None:
    sym_2 = t2()
    sym_3 = t3()
    print("Symbol Mappings from USR to GPX")
    print("(icon id, color): name")
    mapping = defaultdict(list)
    for k in sym_3:
        if k in sym_2:
            mapping[sym_3[k]].append(sym_2[k])
    for k in mapping:
        print(f"{k}: {Counter(mapping[k])}")

if __name__ == "__main__":
    icon_table()

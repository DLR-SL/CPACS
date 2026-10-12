# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the pressure bulkheads, walls,
doors and intercostals of the fuselage structure (pressureBulkheadAssemblyPositionType,
pressureBulkheadType, wallsType, wallPositionType, wallSegmentType,
structuralWallElementType, doorAssemblyPositionType, doorCutOutType,
intercostalPositionType and their collections). They are built into the structure of
fuselageStructure.py and written into the same example file.

Run from the repository root:

    uv run documentation/scripts/fuselageBulkheadWall.py

The script writes

    documentation/figures/pressureBulkhead.png
    documentation/figures/fuselageWall.png
    examples/fuselageStructure.xml (the same file as fuselageStructure.py)

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: the area of the bulkheads, the ring between
the frame and the calotte, the extent and area of the walls, their clearance to the
wing box and the floor, and the height of the intercostals at the edges of the cargo
door. The schema documentation is not written by this script; copy the printed
excerpts there when the example changes.

Definitions shown (as in the documentation), all in the fuselage coordinate system:

- A pressure bulkhead closes the cross section of its frame. A flat bulkhead is the
  surface the path of the frame encloses; its vertical and horizontal reinforcements
  are evenly distributed, i.e. n reinforcements divide the width (the height) of the
  surface into n + 1 equal parts. A curved bulkhead is a spherical calotte with the
  radius bulkheadCalotteRadiusAtFrame in the plane of the frame and the depth
  maxFlectionDepth, centred in the centroid of the enclosed surface and curved
  backwards (towards +x); between the frame and the edge of the calotte, a flat ring
  closes the bulkhead.
- A wall position is the point (x, y, z). A wall segment is made of plane faces, one
  between each pair of consecutive positions, spanned by the line between them and
  the extrusion direction: the z-axis rotated about the x-axis by phi (as
  referenceAngle). The faces reach from the line to the surface, and with
  doubleSidedExtrusion to the surface on both sides of the line.
- A door of the structure is the area of the shell between its two frames and from
  its start stringer, in the direction of increasing angle, to its end stringer (as a
  skin panel). An intercostal runs between its two frames at the relative height
  positionRelZ between the lower (0) and the upper (1) of the two stringers.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon

from example_xml import indent
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, axes_cross, dot, figure_style, label, save_figure
from fuselage import FUSELAGE_UID, LOFT
from fuselageCutOut import CUTOUTS, FLOOR_Z, cutout
import fuselageStructure as shell
import structuralProfile
from wing import AIRFOIL, SECTIONS, WING_TRANSLATION

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"

# Colors: sheets of bulkheads and walls as a wash of series 1 with their reinforcements in series 1 (as the skin and
# the floor panels), frames in series 3 (fuselageStructure.py), the contour of the fuselage muted.
SHEET = COLORS["series1"]
FRAME = COLORS["series3"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
WASH = 0.13
RADIUS = shell.RADIUS

# ------------------------------------------------------------------ example data
# Pressure bulkheads (uID suffix, frame uID suffix, x, element uID): a flat one in front of the cockpit, behind the
# radome, and a curved one behind the aft galley; the cabin of deck.py reaches from x = 4.6 to 19.8 m.
BULKHEADS = [
    ("fwdPressureBulkhead", "frameFwdBulkhead", 1.5, "FwdPressureBulkhead"),
    ("aftPressureBulkhead", "frameAftBulkhead", 20.0, "AftPressureBulkhead"),
]
# Flat bulkhead: number of vertical and horizontal reinforcements and their element; curved bulkhead: radius of the
# calotte at the frame, depth, number of radial reinforcements and their element. Sheet elements (uID, thickness).
FLAT = {"vertical": (5, shell.FRAME_ELEMENT), "horizontal": (3, structuralProfile.ELEMENT_UID)}
CALOTTE_RADIUS = 1.45
CALOTTE_DEPTH = 0.55
RADIAL = (16, structuralProfile.ELEMENT_UID)
BULKHEAD_SHEETS = [("BulkheadFlat", 0.002), ("BulkheadCalotte", 0.0012)]

# Walls of the bay of the main landing gear behind the wing box: a horizontal pressure deck from the rear spar to the
# aft wall, below the cabin floor, and the aft wall from there down to the keel. The two walls share the position at
# their common edge. Positions (uID suffix, x, y, z); segments (uID suffix, phi, double-sided, positions).
REAR_SPAR_XSI = 0.65  # at the root, as in wingStructure.py
REAR_SPAR_X = WING_TRANSLATION[0] + REAR_SPAR_XSI * SECTIONS[0][1]  # 13.25
BAY_AFT_X = 15.4
BAY_CEILING_Z = -0.75
WALL_POSITIONS = [
    ("mlgBayFwd", REAR_SPAR_X, 0.0, BAY_CEILING_Z),
    ("mlgBayAft", BAY_AFT_X, 0.0, BAY_CEILING_Z),
    ("mlgBayKeel", BAY_AFT_X, 0.0, -RADIUS),
]
WALL_SEGMENTS = [
    ("mlgBayCeiling", 90.0, True, ["mlgBayFwd", "mlgBayAft"]),
    ("mlgBayAftWall", 90.0, True, ["mlgBayAft", "mlgBayKeel"]),
]
WALL_ELEMENT = ("PressureWall", "WallSheet", 0.0025)

# The forward cargo door in the structure: between the frames at its edges and the stringers along them, as the
# door surround panel of fuselageStructure.py. Intercostals: the sill and the header beam between the edge frames,
# at the lower and the upper edge of the cut-out, as relative heights between the two stringers.
CARGO_DOOR = cutout(next(row for row in CUTOUTS if row[0] == "cargoDoorFwd"))
DOOR_UID = f"{FUSELAGE_UID}_cargoDoorFwdStructure"  # the cut-out of the door is Fuselage_cargoDoorFwd
DOOR_FRAMES = (shell.FRAME_X[1], shell.FRAME_X[3])
DOOR_ELEMENT = "CargoDoor"
INTERCOSTALS = [("cargoDoorSill", "Sill beam", 0.14), ("cargoDoorHeader", "Header beam", 0.705)]
INTERCOSTAL_ELEMENT = shell.FRAME_ELEMENT


def frame_uid(suffix):
    return f"{FUSELAGE_UID}_{suffix}"


def bulkhead_frames():
    """(uID, [(x, angle)]) of the frames that carry the bulkheads, each a whole cross section."""
    return [(frame_uid(f), [(x, shell.FULL_FRAME_ANGLE)]) for _, f, x, _ in BULKHEADS]


# ------------------------------------------------------------------ geometry
def contour(x, n=721):
    """Cross section of the surface at x as (y, z), starting at the top."""
    width, height, zc = LOFT.station(x)
    t = np.linspace(0.0, 2.0 * np.pi, n)
    return np.column_stack([0.5 * width * np.sin(t), zc + 0.5 * height * np.cos(t)])


def enclosed_area(x):
    width, height, _ = LOFT.station(x)
    return float(np.pi / 4.0 * width * height)


def flat_reinforcements(x):
    """Lines (y, z) of the vertical and the horizontal reinforcements of a flat bulkhead at x, clipped to the
    contour: n reinforcements divide the width (height) into n + 1 equal parts."""
    width, height, zc = LOFT.station(x)
    a, b = width / 2, height / 2
    vertical = []
    for i in range(1, FLAT["vertical"][0] + 1):
        y = -a + i * width / (FLAT["vertical"][0] + 1)
        h = b * np.sqrt(1.0 - (y / a) ** 2)
        vertical.append(((y, zc - h), (y, zc + h)))
    horizontal = []
    for j in range(1, FLAT["horizontal"][0] + 1):
        z = zc - b + j * height / (FLAT["horizontal"][0] + 1)
        w = a * np.sqrt(1.0 - ((z - zc) / b) ** 2)
        horizontal.append(((-w, z), (w, z)))
    return vertical, horizontal


def sphere_radius():
    return (CALOTTE_RADIUS**2 + CALOTTE_DEPTH**2) / (2.0 * CALOTTE_DEPTH)


def calotte_section(x_frame, zc, n=181):
    """The calotte in the plane y = 0 as (x, z), from the lower to the upper edge, curved towards +x."""
    r = sphere_radius()
    half = np.arcsin(CALOTTE_RADIUS / r)
    t = np.linspace(-half, half, n)
    centre_x = x_frame + CALOTTE_DEPTH - r
    return np.column_stack([centre_x + r * np.cos(t), zc + r * np.sin(t)])


def calotte_area():
    return float(2.0 * np.pi * sphere_radius() * CALOTTE_DEPTH)


def wall_position(suffix):
    return next(np.array(p[1:]) for p in WALL_POSITIONS if p[0] == suffix)


def extrusion(phi):
    """Extrusion direction: the z-axis rotated about the x-axis by phi [deg], as (y, z)."""
    a = np.radians(phi)
    return np.array([-np.sin(a), np.cos(a)])


def half_width(z):
    return float(np.sqrt(RADIUS**2 - z**2))


def ceiling_area():
    """The ceiling spans the barrel from skin to skin at its height, from the first to the second position."""
    x0, x1 = wall_position("mlgBayFwd")[0], wall_position("mlgBayAft")[0]
    return (x1 - x0) * 2.0 * half_width(BAY_CEILING_Z)


def aft_wall_area():
    """The aft wall closes the cross section below the ceiling: a segment of the circle."""
    d = -BAY_CEILING_Z
    return float(RADIUS**2 * np.arccos(d / RADIUS) - d * half_width(BAY_CEILING_Z))


def root_section():
    """Airfoil of the wing root in the fuselage coordinate system, as (x, z)."""
    chord = SECTIONS[0][1]
    return np.column_stack([WING_TRANSLATION[0] + chord * AIRFOIL[:, 0], WING_TRANSLATION[2] + chord * AIRFOIL[:, 1]])


def stringer_z(angle):
    return RADIUS * np.cos(np.radians(angle))


def intercostal_z(rel):
    lower, upper = sorted(stringer_z(a) for a in shell.DOOR_STRINGERS)
    return lower + rel * (upper - lower)


# --------------------------------------------------------------------- figures
VIEW_Z = (-1.78, 1.82)  # vertical range of both panels of the bulkhead figure [m]


def figure_bulkhead():
    """(a) the flat forward bulkhead seen from behind; (b) the curved aft bulkhead in the section y = 0."""
    x_flat, x_curved = BULKHEADS[0][2], BULKHEADS[1][2]
    flat_range = (-1.75, 1.75)
    curved_range = (x_curved - 0.95, x_curved + 1.35)
    with figure_style():
        widths = [flat_range[1] - flat_range[0], curved_range[1] - curved_range[0]]
        fig, (front, side) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 4.2),
                                          gridspec_kw={"width_ratios": widths, "wspace": 0.12})
        _flat(front, x_flat, flat_range)
        _curved(side, x_curved, curved_range)
        save_figure(fig, FIGURES / "pressureBulkhead.png")


def _flat(ax, x, xlim):
    ring = contour(x)
    ax.add_patch(Polygon(ring, closed=True, facecolor=to_rgba(SHEET, WASH), edgecolor="none", zorder=0))
    ax.plot(*ring.T, color=FRAME, lw=2.4, solid_capstyle="butt", zorder=3)
    vertical, horizontal = flat_reinforcements(x)
    for line in vertical + horizontal:
        ax.plot(*np.array(line).T, color=SHEET, lw=LINE["data"], solid_capstyle="butt", zorder=2)
    width, height, zc = LOFT.station(x)
    # equal spacing: the width divided into n + 1 parts, marked above the contour
    top = zc + height / 2 + 0.16
    ys = [-width / 2] + [line[0][0] for line in vertical] + [width / 2]
    ax.plot([ys[0], ys[-1]], [top, top], color=INK2, lw=LINE["reference"])
    for y in ys:
        ax.plot([y, y], [top - 0.04, top + 0.04], color=INK2, lw=LINE["reference"])
    label(ax, (0.0, top), f"width in {FLAT['vertical'][0] + 1} equal parts", (0, 4), va="bottom", color=INK2)
    ax.plot([ys[0], ys[0]], [zc, top - 0.04], color=MUTED, lw=LINE["reference"], zorder=1)
    ax.plot([ys[-1], ys[-1]], [zc, top - 0.04], color=MUTED, lw=LINE["reference"], zorder=1)
    label(ax, (vertical[0][0][0], zc - height / 2 - 0.02), f"{FLAT['vertical'][0]} vertical", (0, -4), va="top")
    label(ax, (width / 2, horizontal[0][0][1]), f"{FLAT['horizontal'][0]} horizontal", (8, 0), ha="left")
    t = np.radians(145.0)  # a point of the frame at the lower right
    label(ax, (width / 2 * np.sin(t), zc + height / 2 * np.cos(t)), f"frame at x = {x:g} m", (6, -6), ha="left",
          va="top", color=INK2)
    axes_cross(ax, (xlim[0] + 0.15, VIEW_Z[0] + 0.12), [(1, 0), (0, 1)], ["y", "z"], 0.32, [(6, 0), (0, 7)])
    ax.set_xlim(*xlim)
    ax.set_ylim(*VIEW_Z)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("(a) Flat bulkhead, seen from behind", fontsize=FONT_SIZE["base"])


def _curved(ax, x, xlim):
    width, height, zc = LOFT.station(x)
    xs = np.linspace(xlim[0], xlim[1], 200)
    rows = np.array([LOFT.station(v) for v in xs])
    for s in (1, -1):
        ax.plot(xs, rows[:, 2] + s * rows[:, 1] / 2, color=MUTED, lw=LINE["secondary"], zorder=1)
    top, bottom = zc + height / 2, zc - height / 2
    # the frame: its profile, 80 mm high, inside the surface at the top and the bottom
    depth = shell.FRAME_POINTS["P3"][1]
    for z0, s in ((top, -1), (bottom, 1)):
        ax.plot([x, x], [z0, z0 + s * depth], color=FRAME, lw=4.0, solid_capstyle="butt", zorder=3)
    # the bulkhead: flat ring from the frame to the edge of the calotte, the calotte curved backwards
    arc = calotte_section(x, zc)
    edge = (zc - CALOTTE_RADIUS, zc + CALOTTE_RADIUS)
    ax.plot([x, x], [top, edge[1]], color=SHEET, lw=LINE["data"], solid_capstyle="butt", zorder=4)
    ax.plot([x, x], [bottom, edge[0]], color=SHEET, lw=LINE["data"], solid_capstyle="butt", zorder=4)
    ax.plot(*arc.T, color=SHEET, lw=LINE["data"], zorder=4)
    # the plane of the frame through the centroid, and the dimensions: the radius on the plane, the depth along x
    ax.plot([x, x], [edge[0], edge[1]], color=MUTED, lw=LINE["reference"], zorder=2)
    apex = x + CALOTTE_DEPTH
    dot(ax, (x, zc), size=3.5)
    label(ax, (x, zc), "centroid", (-5, -5), ha="right", va="top", color=INK2)
    r_x = x - 0.42
    ax.plot([r_x, r_x], [zc, edge[1]], color=INK2, lw=LINE["reference"])
    for z in (zc, edge[1]):
        ax.plot([r_x - 0.035, r_x + 0.035], [z, z], color=INK2, lw=LINE["reference"])
        ax.plot([r_x + 0.035, x], [z, z], color=MUTED, lw=LINE["reference"], zorder=1)
    label(ax, (r_x, zc + 0.5 * CALOTTE_RADIUS),
          f"bulkheadCalotte-\nRadiusAtFrame\n{CALOTTE_RADIUS:g} m", (-5, 0), ha="right", color=INK2)
    # the depth on the axis through the centroid, from the plane of the frame to the apex
    ax.plot([x, apex], [zc, zc], color=INK2, lw=LINE["reference"], zorder=2)
    for v in (x, apex):
        ax.plot([v, v], [zc - 0.035, zc + 0.035], color=INK2, lw=LINE["reference"], zorder=2)
    label(ax, (apex, zc), f"maxFlectionDepth\n{CALOTTE_DEPTH:g} m", (6, 0), ha="left", color=INK2)
    label(ax, (x, top), f"frame at x = {x:g} m", (-4, 5), ha="right", va="bottom", color=INK2)
    ax.annotate("flat ring", xy=(x, edge[1] + 0.6 * (top - depth - edge[1])), xytext=(x + 0.3, top - 0.32),
                fontsize=FONT_SIZE["annotation"], color=INK2, ha="left", va="center",
                arrowprops={"arrowstyle": "-", "color": MUTED, "lw": LINE["reference"], "shrinkA": 2, "shrinkB": 2})
    label(ax, tuple(arc[int(0.72 * len(arc))]), "calotte", (7, 0), ha="left")
    axes_cross(ax, (xlim[1] - 0.45, VIEW_Z[0] + 0.12), [(1, 0), (0, 1)], ["x", "z"], 0.32, [(6, 0), (0, 7)])
    ax.set_xlim(*xlim)
    ax.set_ylim(*VIEW_Z)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("(b) Curved bulkhead, section at y = 0", fontsize=FONT_SIZE["base"])


WALL_X = (REAR_SPAR_X - 1.25, BAY_AFT_X + 1.3)
WALL_Z = (-2.1, -0.2)
SECTION_X = 14.3


def figure_wall():
    """(a) the bay of the main landing gear in the section y = 0, seen from the left; (b) the section at x = 14.3 m,
    seen from behind."""
    with figure_style():
        widths = [WALL_X[1] - WALL_X[0], 2 * 1.95]
        fig, (side, back) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9),
                                         gridspec_kw={"width_ratios": widths, "wspace": 0.1})
        _wall_side(side)
        _wall_section(back)
        save_figure(fig, FIGURES / "fuselageWall.png")


def _wall_side(ax):
    x0, x1 = WALL_X
    ax.plot([x0, x1], [-RADIUS, -RADIUS], color=MUTED, lw=LINE["secondary"], zorder=1)
    label(ax, (REAR_SPAR_X + 0.3, -RADIUS), "skin", (0, -4), ha="left", va="top", color=INK2)
    # the aft part of the wing box, up to the rear spar
    root = root_section()
    n = len(AIRFOIL) // 2
    lower, upper = root[:n + 1], root[n:]
    keep = lambda p: p[(p[:, 0] >= x0) & (p[:, 0] <= REAR_SPAR_X)]  # noqa: E731
    lower, upper = keep(lower), keep(upper)
    outline = np.vstack([upper[np.argsort(upper[:, 0])], lower[np.argsort(-lower[:, 0])]])
    ax.add_patch(Polygon(outline, closed=True, facecolor=to_rgba(MUTED, 0.16), edgecolor="none", zorder=0))
    z_spar = (np.interp(REAR_SPAR_X, *lower[np.argsort(lower[:, 0])].T), np.interp(REAR_SPAR_X,
                                                                                   *upper[np.argsort(upper[:, 0])].T))
    ax.plot([REAR_SPAR_X, REAR_SPAR_X], z_spar, color=MUTED, lw=LINE["data"], solid_capstyle="butt", zorder=2)
    label(ax, (x0 + 0.08, float(np.mean(z_spar))), "wing box", (0, 0), ha="left", color=INK2)
    label(ax, (REAR_SPAR_X, z_spar[0]), "rear spar", (5, 0), ha="left", va="bottom", color=INK2)
    # the walls and their positions
    fwd, aft, keel = (wall_position(s) for s in ("mlgBayFwd", "mlgBayAft", "mlgBayKeel"))
    ax.plot([fwd[0], aft[0]], [fwd[2], aft[2]], color=SHEET, lw=2.6, solid_capstyle="butt", zorder=3)
    ax.plot([aft[0], keel[0]], [aft[2], keel[2]], color=SHEET, lw=2.6, solid_capstyle="butt", zorder=3)
    for p in (fwd, aft, keel):
        dot(ax, (p[0], p[2]))
    # positions in ink below the ceiling, inside the bay; the names of the walls in ink along them
    label(ax, (fwd[0], fwd[2]), "mlgBayFwd", (-5, 4), ha="right", va="bottom")
    label(ax, (aft[0], aft[2]), "mlgBayAft", (5, 4), ha="left", va="bottom")
    label(ax, (keel[0], keel[2]), "mlgBayKeel", (5, -4), ha="left", va="top")
    label(ax, (0.5 * (fwd[0] + aft[0]), fwd[2]), "mlgBayCeiling", (0, 4), va="bottom")
    label(ax, (aft[0], 0.5 * (aft[2] + keel[2])), "mlgBayAftWall", (7, 0), ha="left")
    axes_cross(ax, (x0 + 0.1, WALL_Z[0] + 0.02), [(1, 0), (0, 1)], ["x", "z"], 0.22, [(6, 0), (0, 7)])
    ax.set_xlim(*WALL_X)
    ax.set_ylim(*WALL_Z)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("(a) Section at y = 0, seen from the left", fontsize=FONT_SIZE["base"])


def _wall_section(ax):
    t = np.linspace(0.0, 2.0 * np.pi, 721)
    ring = np.column_stack([RADIUS * np.sin(t), RADIUS * np.cos(t)])
    ax.plot(*ring.T, color=MUTED, lw=LINE["secondary"], zorder=1)
    half = half_width(BAY_CEILING_Z)
    ax.plot([-half, half], [BAY_CEILING_Z, BAY_CEILING_Z], color=SHEET, lw=2.6, solid_capstyle="butt", zorder=3)
    origin = np.array([0.0, BAY_CEILING_Z])
    phi = WALL_SEGMENTS[0][1]
    d = extrusion(phi)
    # phi from the z direction, as a pale area, and the two directions of the double-sided extrusion
    r = 0.22
    wedge = np.radians(np.linspace(0.0, phi, 91))
    ax.add_patch(Polygon(np.vstack([origin, origin + r * np.column_stack([-np.sin(wedge), np.cos(wedge)])]),
                         closed=True, facecolor=SHEET, alpha=0.14, edgecolor="none", zorder=1))
    ax.plot([0.0, 0.0], [BAY_CEILING_Z, BAY_CEILING_Z + 0.4], color=MUTED, lw=LINE["reference"], zorder=2)
    label(ax, (0.0, BAY_CEILING_Z + 0.4), "z", (0, 3), va="bottom", color=INK2)
    label(ax, (0.0, BAY_CEILING_Z + 0.25), f"phi {phi:g}°", (5, 0), ha="left")
    # the directions, parallel to the wall and just above it, so that they do not lie on it; their names above the
    # extrusion direction and below the opposite one, clear of each other and of the contour
    lift = np.array([0.0, 0.08])
    arrow(ax, origin + lift, origin + lift + 0.95 * d, color=INK, lw=LINE["secondary"], head=7)
    arrow(ax, origin + lift, origin + lift - 0.95 * d, color=INK2, lw=LINE["reference"], head=6)
    label(ax, origin + lift + 0.25 * d, "extrusion\ndirection", (0, 4), ha="right", va="bottom")
    label(ax, origin - 0.65 * d, "double-sided", (0, -5), va="top", color=INK2)
    dot(ax, origin)
    label(ax, origin, "positions", (-6, -5), ha="right", va="top")
    axes_cross(ax, (-1.85, WALL_Z[0] + 0.02), [(1, 0), (0, 1)], ["y", "z"], 0.22, [(6, 0), (0, 7)])
    ax.set_xlim(-1.95, 1.95)
    ax.set_ylim(*WALL_Z)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"(b) Section at x = {SECTION_X:g} m, seen from behind", fontsize=FONT_SIZE["base"])


# --------------------------------------------------------------------- example
def bulkhead_xml(row):
    suffix, frame, _, element = row
    return "\n".join([f'<pressureBulkhead uID="{FUSELAGE_UID}_{suffix}">', f"    <frameUID>{frame_uid(frame)}</frameUID>",
                      f"    <pressureBulkheadElementUID>{element}</pressureBulkheadElementUID>",
                      "</pressureBulkhead>"])


def wall_position_xml(row):
    suffix, x, y, z = row
    return "\n".join([f'<wallPosition uID="{FUSELAGE_UID}_{suffix}">', f"    <x>{x:g}</x>", f"    <y>{y:g}</y>",
                      f"    <z>{z:g}</z>", "</wallPosition>"])


def wall_segment_xml(row):
    suffix, phi, double, positions = row
    return "\n".join([
        f'<wallSegment uID="{FUSELAGE_UID}_{suffix}">', f"    <phi>{phi:g}</phi>",
        *([f"    <doubleSidedExtrusion>true</doubleSidedExtrusion>"] if double else []),
        f"    <structuralWallElementUID>{WALL_ELEMENT[0]}</structuralWallElementUID>", "    <wallPositionUIDs>",
        *(f"        <wallPositionUID>{FUSELAGE_UID}_{p}</wallPositionUID>" for p in positions),
        "    </wallPositionUIDs>", "</wallSegment>"])


def walls_xml():
    return "\n".join(["<walls>", indent(shell.collection("wallPositions", [wall_position_xml(p) for p in WALL_POSITIONS]),
                                        1),
                      indent(shell.collection("wallSegments", [wall_segment_xml(s) for s in WALL_SEGMENTS]), 1),
                      "</walls>"])


def door_xml():
    x0, x1 = DOOR_FRAMES
    a0, a1 = shell.DOOR_STRINGERS
    return "\n".join([
        f'<cargoDoor uID="{DOOR_UID}">', "    <name>Forward cargo door</name>", "    <doorType>cargo</doorType>",
        f"    <doorElementUID>{DOOR_ELEMENT}</doorElementUID>",
        f"    <startFrameUID>{shell.frame_uid(x0)}</startFrameUID>", f"    <endFrameUID>{shell.frame_uid(x1)}</endFrameUID>",
        f"    <startStringerUID>{shell.stringer_uid(a0)}</startStringerUID>",
        f"    <endStringerUID>{shell.stringer_uid(a1)}</endStringerUID>", "</cargoDoor>"])


def intercostal_xml(row):
    suffix, name, rel = row
    x0, x1 = DOOR_FRAMES
    return "\n".join([
        f'<intercostal uID="{FUSELAGE_UID}_{suffix}">', f"    <name>{name}</name>",
        f"    <frontFrameUID>{shell.frame_uid(x0)}</frontFrameUID>", f"    <rearFrameUID>{shell.frame_uid(x1)}</rearFrameUID>",
        f"    <doorUID>{DOOR_UID}</doorUID>", f"    <positionRelZ>{rel:g}</positionRelZ>",
        f"    <structuralElementUID>{INTERCOSTAL_ELEMENT}</structuralElementUID>", "</intercostal>"])


def interior_xml():
    """The collections of the structure that follow the floors, in the order of fuselageStructureType."""
    return "\n".join([shell.collection("pressureBulkheads", [bulkhead_xml(b) for b in BULKHEADS]), walls_xml(),
                      shell.collection("cargoDoors", [door_xml()]),
                      shell.collection("intercostals", [intercostal_xml(i) for i in INTERCOSTALS])])


def bulkhead_element_xml(uid):
    if uid == BULKHEADS[0][3]:
        (nv, ev), (nh, eh) = FLAT["vertical"], FLAT["horizontal"]
        body = [f"    <name>Forward pressure bulkhead</name>", f"    <sheetElementUID>{BULKHEAD_SHEETS[0][0]}</sheetElementUID>",
                f"    <reinforcementNumberVertical>{nv}</reinforcementNumberVertical>",
                f"    <structuralElementVerticalUID>{ev}</structuralElementVerticalUID>",
                f"    <reinforcementNumberHorizontal>{nh}</reinforcementNumberHorizontal>",
                f"    <structuralElementHorizontalUID>{eh}</structuralElementHorizontalUID>"]
    else:
        n, e = RADIAL
        body = [f"    <name>Aft pressure bulkhead</name>", f"    <sheetElementUID>{BULKHEAD_SHEETS[1][0]}</sheetElementUID>",
                f"    <bulkheadCalotteRadiusAtFrame>{CALOTTE_RADIUS:g}</bulkheadCalotteRadiusAtFrame>",
                f"    <maxFlectionDepth>{CALOTTE_DEPTH:g}</maxFlectionDepth>",
                f"    <reinforcementNumberRadial>{n}</reinforcementNumberRadial>",
                f"    <structuralElementRadialUID>{e}</structuralElementRadialUID>"]
    return "\n".join([f'<pressureBulkhead uID="{uid}">', *body, "</pressureBulkhead>"])


def wall_element_xml():
    uid, sheet, _ = WALL_ELEMENT
    return "\n".join([f'<structuralWallElement uID="{uid}">', f"    <sheetElementUID>{sheet}</sheetElementUID>",
                      "</structuralWallElement>"])


def door_element_xml():
    return "\n".join([f'<door uID="{DOOR_ELEMENT}">', "    <name>Cargo door</name>",
                      f"    <filletRadius>{CARGO_DOOR['fillet']:g}</filletRadius>", "</door>"])


def interior_sheets():
    """Sheet elements (uID, thickness) of the bulkheads and the walls."""
    return [*BULKHEAD_SHEETS, WALL_ELEMENT[1:]]


def interior_elements_xml():
    """The collections of structuralElements after the sheet and profile based elements, in the order of
    structuralElementsType."""
    return [shell.collection("structuralWallElements", [wall_element_xml()]),
            shell.collection("pressureBulkheads", [bulkhead_element_xml(b[3]) for b in BULKHEADS]),
            shell.collection("doors", [door_element_xml()])]


# --------------------------------------------------------------------- report
def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    for suffix, frame, x, _ in BULKHEADS:
        width, height, zc = LOFT.station(x)
        print(f"{suffix}: frame at x = {x:g}, cross section {width:.4f} x {height:.4f}, centre z = {zc:.4f}, "
              f"enclosed area {enclosed_area(x):.4f} m^2")
    width, height, zc = LOFT.station(BULKHEADS[1][2])
    ring = (min(width, height) / 2 - CALOTTE_RADIUS, max(width, height) / 2 - CALOTTE_RADIUS)
    print(f"Calotte: sphere radius {sphere_radius():.4f}, area {calotte_area():.4f} m^2, ring between frame and calotte "
          f"{1000 * ring[0]:.0f} to {1000 * ring[1]:.0f} mm, apex at x = {BULKHEADS[1][2] + CALOTTE_DEPTH:g}")
    assert ring[0] > 0.05, "the calotte reaches the frame"
    apex_station = LOFT.station(BULKHEADS[1][2] + CALOTTE_DEPTH)
    assert CALOTTE_RADIUS < min(apex_station[:2]) / 2, "the calotte leaves the fuselage"
    cabin_end = 4.6 + 15.2
    print(f"Cabin ends at x = {cabin_end:g}, aft bulkhead at {BULKHEADS[1][2]:g}; cockpit from {BULKHEADS[0][2]:g} to 4.6")
    vertical, horizontal = flat_reinforcements(BULKHEADS[0][2])
    print(f"Flat bulkhead: vertical reinforcements at y = {[round(float(v[0][0]), 4) for v in vertical]}, horizontal at "
          f"z = {[round(float(h[0][1]), 4) for h in horizontal]}")
    # the walls
    root = root_section()
    n = len(AIRFOIL) // 2
    upper = root[n:]
    wing_at_spar = float(np.interp(REAR_SPAR_X, *upper[np.argsort(upper[:, 0])].T))
    print(f"Ceiling at z = {BAY_CEILING_Z:g}: wing upper side at the rear spar (x = {REAR_SPAR_X:g}) z = "
          f"{wing_at_spar:.4f}, {BAY_CEILING_Z - wing_at_spar:.3f} m below the ceiling; cabin floor at {FLOOR_Z:g}")
    assert BAY_CEILING_Z > wing_at_spar and BAY_CEILING_Z < FLOOR_Z
    print(f"Ceiling: x {REAR_SPAR_X:g} to {BAY_AFT_X:g}, y +-{half_width(BAY_CEILING_Z):.4f}, area {ceiling_area():.4f}"
          f" m^2; aft wall: z {-RADIUS:g} to {BAY_CEILING_Z:g}, area {aft_wall_area():.4f} m^2")
    for x in (REAR_SPAR_X, BAY_AFT_X):
        w, h, c = LOFT.station(x)
        assert max(abs(w - 2 * RADIUS), abs(h - 2 * RADIUS), abs(c)) < 3e-3, "bay leaves the barrel"
    # the cargo door and its intercostals
    a0, a1 = shell.DOOR_STRINGERS
    print(f"Cargo door: frames x = {DOOR_FRAMES}, stringers {a0} to {a1} deg (sweep {shell.sweep(a0, a1):g} deg), "
          f"area {(DOOR_FRAMES[1] - DOOR_FRAMES[0]) * RADIUS * np.radians(shell.sweep(a0, a1)):.4f} m^2")
    edges = [RADIUS * np.cos(np.radians(a)) for a in shell.DOOR_ANGLES]
    for (suffix, name, rel), edge in zip(INTERCOSTALS, sorted(edges), strict=True):
        print(f"{name}: positionRelZ {rel:g} -> z = {intercostal_z(rel):.4f}; cut-out edge at z = {edge:.4f} "
              f"({1000 * (intercostal_z(rel) - edge):+.0f} mm)")
        assert 0.0 <= (intercostal_z(rel) - edge) * (1 if rel > 0.5 else -1) < 0.01, "intercostal not at the edge"


def excerpts():
    return [
        ("pressureBulkheadAssemblyType", shell.collection("pressureBulkheads", [bulkhead_xml(b) for b in BULKHEADS])),
        ("pressureBulkheadType", shell.collection("pressureBulkheads", [bulkhead_element_xml(b[3]) for b in BULKHEADS])),
        ("wallsType", walls_xml()),
        ("doorAssemblyPositionType", shell.collection("cargoDoors", [door_xml()])),
        ("intercostalPositionType", shell.collection("intercostals", [intercostal_xml(i) for i in INTERCOSTALS])),
    ]


def main():
    figure_bulkhead()
    figure_wall()
    shell.write_example()
    report()
    print(f"\nWritten {shell.EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in excerpts():
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

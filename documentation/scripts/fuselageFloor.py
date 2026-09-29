# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the floors of the fuselage
structure (crossBeamAssemblyPositionType, crossBeamStrutAssemblyPositionType,
alignmentCrossBeamType, longFloorBeamType, longFloorBeamPositionType,
alignmentStructMemberType, floorPanelType, alignmentFloorPanelType and their
collections). The floors are built into the barrel of fuselageStructure.py, on its
frames, and written into the same example file.

Run from the repository root:

    uv run documentation/scripts/fuselageFloor.py

The script writes

    documentation/figures/fuselageFloor.png
    documentation/figures/floorPanel.png
    documentation/figures/floorBeamProfile.png
    examples/fuselageStructure.xml (the same file as fuselageStructure.py)

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: the ends of the cross beams, the feet of
the struts, the clearance to the wing box under the floor and the height of the
cargo floor at the sill of the cargo door. The schema documentation is not written
by this script; copy the printed excerpts there when the example changes.

Definitions shown (as in the documentation), all in the fuselage coordinate system:

- A cross beam is the straight line in the plane of its frame at the height
  z = positionZ, between the two points where the path of the frame has this
  height. Its path runs from the end with the larger y to the end with the smaller
  y; offset1LocX and offset2LocX shorten it at the start and at the end.
- A strut starts at the point of its cross beam with y = positionYAtCrossBeam and
  runs in the direction of the z-axis rotated about the x-axis by angleX (as
  referenceAngle: 180 degrees is straight down, the default) until it meets the
  path of its frame.
- A longitudinal floor beam runs straight from the point of each of its positions
  (the point of the cross beam with y = positionY) to the next.
- Profiles have their origin on the path. Cross beam and strut: the x-axis of the
  profile along the x-axis of the fuselage, its y-axis = path direction x fuselage
  x-axis (up for a cross beam). Longitudinal floor beam: the y-axis of the profile up
  (normal to the path, in the vertical plane through it), its x-axis = profile y x
  path direction.
- A floor panel is the surface between the paths of its two longitudinal floor
  beams from x = startX to x = endX. Its local y-axis runs from beam 1 to beam 2 and
  its z-axis up; offset1LocY and offset2LocY move its edges at beam 1 and beam 2
  along y, offsetLocZ moves the panel along z.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon, Rectangle

from example_xml import indent
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, dot, figure_style, label, save_figure
from fuselage import FUSELAGE_UID
from fuselageCutOut import CUTOUTS, FLOOR_Z
import fuselageStructure as shell
import structuralProfile
from wing import AIRFOIL, POSITIONINGS, SECTIONS, WING_TRANSLATION, positioning_ends, section_airfoil

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"

# Colors: the floor members in series 1 (as the stringers, the other members running through the fuselage), the
# frames in series 3 and the cut-outs in series 2, as in fuselageStructure.py; floor panels as a wash of series 1.
MEMBER = COLORS["series1"]
FRAME = COLORS["series3"]
CUTOUT = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]
RADIUS = shell.RADIUS

# ------------------------------------------------------------------ example data
# Passenger floor: the cabin floor (the deck of deck.py) at FLOOR_Z is the top of the panels, which lie on seat rails
# 20 mm high; the rails stand on the cross beams, whose path is their upper edge. Cargo floor: at the sill of the
# forward cargo door. The frame through the door (x = 8 m) does not reach the height of either floor on the right, so
# it carries no cross beams; the rails span from x = 7.5 to 8.5 m there.
SEAT_RAIL_HEIGHT = 0.02
PAX_Z = round(FLOOR_Z - SEAT_RAIL_HEIGHT, 4)  # -0.57
CARGO_Z = -1.27
BEAM_OFFSET = 0.03  # offset1LocX, offset2LocX: the ends of the cross beams stay clear of the skin
PAX_RAILS = [("L2", -1.02), ("L1", -0.52), ("R1", 0.52), ("R2", 1.02)]  # under the double seats, y = +-0.77
CARGO_RAILS = [("L", -0.4), ("R", 0.4)]
# struts (side, positionYAtCrossBeam, angleX): the passenger floor on vertical struts beside the cargo hold, the cargo
# floor on struts inclined outwards and downwards
PAX_STRUTS = [("L", -1.1, 180.0), ("R", 1.1, 180.0)]
CARGO_STRUTS = [("L", -0.5, 160.0), ("R", 0.5, 200.0)]
# floor panels (uID suffix, beam 1, beam 2, startX, endX) on the passenger rails and between the cargo rails; the
# panels stop 5 mm short of the axis of each rail and lie on top of the rails
PANEL_X = [(7.0, 8.5), (8.5, 9.5)]
PANEL_OFFSET_Y = 0.005
PANEL_OFFSET_Z = SEAT_RAIL_HEIGHT

# Profiles (points, sheets as (from, to, name, thickness)), in metres; see the docstring for their placement.
PROFILES = {
    "CrossBeam": ("I-profile cross beam", "Flanges of 40 mm, web of 120 mm height below the path",
                  {"P1": (-0.02, 0.0), "P2": (0.0, 0.0), "P3": (0.02, 0.0), "P4": (-0.02, -0.12), "P5": (0.0, -0.12),
                   "P6": (0.02, -0.12)},
                  {"S1": ("P1", "P2", "Upper flange, rear", 0.002), "S2": ("P2", "P3", "Upper flange, front", 0.002),
                   "S3": ("P2", "P5", "Web", 0.0016), "S4": ("P4", "P5", "Lower flange, rear", 0.002),
                   "S5": ("P5", "P6", "Lower flange, front", 0.002)}),
    "SeatRail": ("Seat rail", "Flanges of 20 mm, web of 20 mm height above the path",
                 {"P1": (-0.01, 0.0), "P2": (0.0, 0.0), "P3": (0.01, 0.0), "P4": (-0.01, 0.02), "P5": (0.0, 0.02),
                  "P6": (0.01, 0.02)},
                 {"S1": ("P1", "P2", "Lower flange, left", 0.002), "S2": ("P2", "P3", "Lower flange, right", 0.002),
                  "S3": ("P2", "P5", "Web", 0.002), "S4": ("P4", "P5", "Upper flange, left", 0.002),
                  "S5": ("P5", "P6", "Upper flange, right", 0.002)}),
    "Strut": ("Strut", "Square tube of 30 mm",
              {"P1": (-0.015, -0.015), "P2": (0.015, -0.015), "P3": (0.015, 0.015), "P4": (-0.015, 0.015)},
              {"S1": ("P1", "P2", "Side 1", 0.0015), "S2": ("P2", "P3", "Side 2", 0.0015),
               "S3": ("P3", "P4", "Side 3", 0.0015), "S4": ("P4", "P1", "Side 4", 0.0015)}),
}
PANEL_ELEMENT = "FloorPanel"
PANEL_THICKNESS = 0.01
PANEL_MATERIAL = ("FloorPanelSandwich", "Floor panel sandwich",
                  "Glass fibre skins on aramid honeycomb, 10 mm, smeared to an isotropic equivalent", 250, 2.0e9, 0.8e9)

BEAM_HEIGHT = -min(y for _, y in PROFILES["CrossBeam"][2].values())
WING_CLEARANCE = 0.01  # at least between the lower edge of the cross beams and the upper side of the wing box
ROOT_SPARS = (0.15, 0.65)  # front and rear spar at the root, xsi (wingStructure.py)


def floor_frames():
    """(frame uID, x) of the frames that carry cross beams: all whole frames."""
    return [(uid, positions[0][0]) for uid, positions in shell.frames() if len(positions) == 1]


def beam_uid(deck, x):
    return f"{FUSELAGE_UID}_{deck}CrossBeam{shell.FRAME_X.index(x) + 1}"


def strut_uid(deck, x, side):
    return f"{FUSELAGE_UID}_{deck}Strut{shell.FRAME_X.index(x) + 1}{side}"


def rail_uid(deck, side):
    return f"{FUSELAGE_UID}_{deck}Rail{side}"


def panel_uid(deck, side, index):
    return f"{FUSELAGE_UID}_{deck}Panel{side}{index + 1}"


DECKS = {"pax": (PAX_Z, PAX_RAILS, PAX_STRUTS), "cargo": (CARGO_Z, CARGO_RAILS, CARGO_STRUTS)}


def panels(deck):
    """(uID, rail 1 uID, rail 2 uID, y1, y2, startX, endX): one strip between each pair of neighbouring rails."""
    rails = DECKS[deck][1]
    rows = []
    for (s1, y1), (s2, y2) in zip(rails, rails[1:]):
        side = "C" if y1 < 0 < y2 else (s1 if y1 < 0 else s2)
        for i, (x0, x1) in enumerate(PANEL_X):
            rows.append((panel_uid(deck, side, i), rail_uid(deck, s1), rail_uid(deck, s2), y1, y2, x0, x1))
    return rows


# ------------------------------------------------------------------ geometry
def beam_ends(z, offsets=(0.0, 0.0)):
    """Start and end of a cross beam at height z in the barrel (y from + to -), shortened by the offsets."""
    half = np.sqrt(RADIUS**2 - z**2)
    return half - offsets[0], -half + offsets[1]


def direction(angle):
    """Direction in the y-z plane of the z-axis rotated about the x-axis by angle [deg] (as referenceAngle)."""
    a = np.radians(angle)
    return np.array([-np.sin(a), np.cos(a)])


def strut_foot(y, z, angle):
    """Point (y, z) where the strut from (y, z) in the direction of angle meets the frame (the barrel circle)."""
    p, d = np.array([y, z]), direction(angle)
    b, c = p @ d, p @ p - RADIUS**2
    return p + (-b + np.sqrt(b * b - c)) * d


def wing_box_top():
    """Highest point of the upper side of the root airfoil between the spars, in the fuselage coordinate system."""
    chord = SECTIONS[0][1]
    upper = AIRFOIL[len(AIRFOIL) // 2:]
    inside = (upper[:, 0] >= ROOT_SPARS[0]) & (upper[:, 0] <= ROOT_SPARS[1])
    return WING_TRANSLATION[2] + chord * float(upper[inside, 1].max())


def wing_upper_at(x, y):
    """z of the upper side of the wing at (x, y) between root and kink, in the fuselage coordinate system."""
    root, kink = section_airfoil(SECTIONS[0]), section_airfoil(SECTIONS[1])
    t = y / positioning_ends(POSITIONINGS)[SECTIONS[1][0]][1]
    points = (1 - t) * root + t * kink + np.asarray(WING_TRANSLATION)
    upper = points[len(points) // 2:]
    return float(np.interp(x, upper[:, 0], upper[:, 2]))


# --------------------------------------------------------------------- figures
SECTION_X = shell.FRAME_X[1]  # the section of figure (a): the frame at the forward edge of the cargo door
SECTION_RANGE = (-1.75, 1.75)  # horizontal range of the section [m]
SECTION_TOP = 0.32  # the section shows the lower half of the fuselage, where the floors are
PLAN_RANGE = (shell.BARREL[0] - 0.2, shell.BARREL[1] + 1.15)
VERTICAL_RANGE = (-2.0, 1.75)


def figure_floor():
    """The lower half of the section through a frame with both floors, seen from behind."""
    with figure_style():
        width = SECTION_RANGE[1] - SECTION_RANGE[0]
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, FULL_WIDTH * (SECTION_TOP - VERTICAL_RANGE[0]) / width))
        _section(ax)
        save_figure(fig, FIGURES / "fuselageFloor.png")


def figure_panel():
    """The passenger floor seen from above."""
    with figure_style():
        fig, ax = plt.subplots(figsize=(0.72 * FULL_WIDTH, 3.9))
        _plan(ax)
        save_figure(fig, FIGURES / "floorPanel.png")


def _section(ax):
    t = np.linspace(0.5 * np.pi, 1.5 * np.pi, 361)
    ring = np.column_stack([RADIUS * np.sin(t), RADIUS * np.cos(t)])
    ax.add_patch(Polygon(ring, closed=True, facecolor=to_rgba(MUTED, 0.06), edgecolor="none", zorder=0))
    ax.plot(*ring.T, color=FRAME, lw=2.4, solid_capstyle="butt", zorder=2)
    label(ax, ring[40], f"frame at x = {SECTION_X:g} m", (8, 0), ha="left", color=INK2)
    for deck, (z, rails, struts) in DECKS.items():
        y0, y1 = beam_ends(z, (BEAM_OFFSET, BEAM_OFFSET))
        ax.plot([y0, y1], [z, z], color=MEMBER, lw=2.6, solid_capstyle="butt", zorder=4)
        for _, y, angle in struts:
            foot = strut_foot(y, z, angle)
            ax.plot([y, foot[0]], [z, foot[1]], color=MEMBER, lw=1.6, solid_capstyle="butt", zorder=3)
        for _, y in rails:
            ax.plot(y, z + 0.035, ls="none", marker="s", ms=4.0, color=MEMBER, mec=COLORS["surface"], mew=0.6,
                    zorder=5)
    rails = [y for _, y in PAX_RAILS if y < 0]
    label(ax, (sum(rails) / 2, PAX_Z + 0.06), "seat rails", (0, 3), va="bottom", color=INK2)
    # the fuselage axis, the reference of positionZ and positionYAtCrossBeam
    dot(ax, (0.0, 0.0), size=4)
    label(ax, (0.0, 0.0), "fuselage axis", (-6, 0), ha="right", color=INK2)
    # positionZ of the passenger cross beam, down from the axis
    _dimension(ax, (0.0, 0.0), (0.0, PAX_Z), f"positionZ {PAX_Z:g} m", (-5, 0), ha="right", tick="h")
    # positionYAtCrossBeam of the right passenger strut, from the axis, with a reference line up from the strut
    y_strut = PAX_STRUTS[1][1]
    ax.plot([y_strut, y_strut], [PAX_Z + 0.06, 0.04], color=MUTED, lw=LINE["reference"], zorder=3)
    _dimension(ax, (0.0, 0.0), (y_strut, 0.0), f"positionYAtCrossBeam {y_strut:g} m", (0, 4), va="bottom",
               tick="v")
    # angleX of the right cargo strut, from the z direction, as a pale area
    _, y, angle = CARGO_STRUTS[1]
    origin = np.array([y, CARGO_Z])
    r = 0.2
    wedge = np.radians(np.linspace(0.0, angle, 181))
    ax.add_patch(Polygon(np.vstack([origin, origin + r * np.column_stack([-np.sin(wedge), np.cos(wedge)])]),
                         closed=True, facecolor=MEMBER, alpha=0.14, edgecolor="none", zorder=1))
    ax.plot([y, y], [CARGO_Z, CARGO_Z + r + 0.06], color=MUTED, lw=LINE["reference"], zorder=3)
    label(ax, (y, CARGO_Z + r + 0.06), f"angleX\n{angle:g}°", (4, 0), ha="left", va="top")
    # names, below the passenger cross beam and above the cargo cross beam, clear of rails and struts
    label(ax, (-0.95, PAX_Z), "passenger cross beam", (0, -5), ha="left", va="top")
    label(ax, (-0.05, CARGO_Z), "cargo cross beam", (0, 5), ha="center", va="bottom")
    ax.set_xlim(*SECTION_RANGE)
    ax.set_ylim(VERTICAL_RANGE[0] + 0.3, SECTION_TOP)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Lower half of the section at x = {SECTION_X:g} m, seen from behind", fontsize=FONT_SIZE["base"])


def _dimension(ax, start, end, text, offset, ha="center", va="center", tick="h"):
    ax.plot(*np.array([start, end]).T, color=INK2, lw=LINE["reference"], zorder=6)
    for p in (start, end):
        d = np.array([0.04, 0.0]) if tick == "h" else np.array([0.0, 0.04])
        ax.plot(*np.array([np.subtract(p, d), np.add(p, d)]).T, color=INK2, lw=LINE["reference"], zorder=6)
    label(ax, 0.5 * (np.asarray(start) + np.asarray(end)), text, offset, ha=ha, va=va, color=INK2)


def _plan(ax):
    """The passenger floor seen from above: x to the right, y up (the left side of the fuselage below)."""
    x0, x1 = shell.BARREL
    half = np.sqrt(RADIUS**2 - FLOOR_Z**2)
    for s in (-1, 1):
        ax.plot([x0 - 0.15, x1 + 0.15], [s * half, s * half], color=MUTED, lw=LINE["secondary"], zorder=1)
    for uid, _, _, y1, y2, a, b in panels("pax"):
        ax.add_patch(Rectangle((a + 0.02, y1 + PANEL_OFFSET_Y), b - a - 0.04, y2 - y1 - 2 * PANEL_OFFSET_Y,
                               facecolor=to_rgba(MEMBER, 0.13), edgecolor="none", zorder=0))
    for _, x in floor_frames():
        y0, y1 = beam_ends(PAX_Z, (BEAM_OFFSET, BEAM_OFFSET))
        ax.plot([x, x], [y0, y1], color=MEMBER, lw=2.6, solid_capstyle="butt", zorder=3)
    for _, y in PAX_RAILS:
        ax.plot([x0, x1], [y, y], color=MEMBER, lw=1.2, solid_capstyle="butt", zorder=4)
    # the frame through the door carries no cross beam: its place, at the wall
    x_door = shell.FRAME_X[2]
    for s in (-1, 1):
        ax.plot([x_door, x_door], [s * half, s * (half - 0.12)], color=FRAME, lw=2.4, solid_capstyle="butt",
                zorder=2)
    label(ax, (x_door, half), "frame without cross beam", (0, 4), va="bottom", color=INK2)
    # one panel: its rails and its extent along x
    uid, _, _, y1, y2, a, b = next(p for p in panels("pax") if p[0].endswith("C1"))
    ax.add_patch(Rectangle((a + 0.02, y1 + PANEL_OFFSET_Y), b - a - 0.04, y2 - y1 - 2 * PANEL_OFFSET_Y,
                           facecolor="none", edgecolor=MEMBER, lw=LINE["reference"], zorder=5))
    label(ax, (shell.FRAME_X[2], (y1 + y2) / 2), "floor panel", (0, 0), color=INK)  # between two cross beams
    label(ax, (x1, y2), "longFloorBeam2UID", (4, 0), ha="left", color=INK2)
    label(ax, (x1, y1), "longFloorBeam1UID", (4, 0), ha="left", color=INK2)
    z_dim = -half - 0.16
    ax.plot([a, b], [z_dim, z_dim], color=INK2, lw=LINE["reference"])
    for x in (a, b):
        ax.plot([x, x], [z_dim - 0.04, z_dim + 0.04], color=INK2, lw=LINE["reference"])
        ax.plot([x, x], [y1, z_dim + 0.04], color=MUTED, lw=LINE["reference"], zorder=1)
    label(ax, (a, z_dim), "startX", (0, -4), va="top", color=INK2)
    label(ax, (b, z_dim), "endX", (0, -4), va="top", color=INK2)
    ax.set_xlim(*PLAN_RANGE)
    ax.set_ylim(*VERTICAL_RANGE)
    ax.set_aspect("equal")
    ax.set_yticks([])
    ax.set_xticks(shell.FRAME_X, [f"{x:g}" for x in shell.FRAME_X])
    ax.spines["bottom"].set_bounds(x0, x1)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("x [m]")
    ax.set_title("Passenger floor, seen from above", fontsize=FONT_SIZE["base"])


DETAIL = 90.0  # half width of the detail views [mm]


def figure_profile():
    """(a) a seat rail on a cross beam, seen from behind; (b) a cross beam with a rail on it, seen from the left."""
    with figure_style():
        fig, (back, left) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.3), gridspec_kw={"wspace": 0.08})
        _profile_detail(back, "rail")
        _profile_detail(left, "beam")
        save_figure(fig, FIGURES / "floorBeamProfile.png")


def _sheets(ax, profile, placed, color):
    for start, end, *_ in PROFILES[profile][3].values():
        ax.plot(*np.array([placed(PROFILES[profile][2][start]), placed(PROFILES[profile][2][end])]).T, color=color,
                lw=2.2, solid_capstyle="butt", zorder=4)


def _profile_detail(ax, kind):
    """In millimetres, relative to the point of the rail R1 on the path of the cross beam."""
    mm = 1000.0
    rail = PROFILES["SeatRail"][2]
    height = BEAM_HEIGHT * mm
    panel_z = PANEL_OFFSET_Z * mm
    if kind == "rail":
        # seen from behind: y to the right, z up; the cross beam runs in the drawing plane, the rail out of it
        ax.add_patch(Rectangle((-DETAIL - 5, -height), 2 * DETAIL + 10, height, facecolor=to_rgba(MEMBER, 0.16),
                               edgecolor="none", zorder=1))
        label(ax, (-DETAIL + 4, -height + 4), "cross beam", (0, 0), ha="left", va="bottom", color=INK2)
        _sheets(ax, "SeatRail", lambda p: (p[0] * mm, p[1] * mm), MEMBER)  # profile x -> y, profile y -> z
        # the panels on both sides, 5 mm short of the axis of the rail, on top of the rail
        gap = PANEL_OFFSET_Y * mm
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * gap if s > 0 else -DETAIL - 5, panel_z), DETAIL + 5 - gap,
                                   PANEL_THICKNESS * mm, facecolor=to_rgba(MUTED, 0.35), edgecolor="none", zorder=2))
        label(ax, (-DETAIL + 4, panel_z + PANEL_THICKNESS * mm), "floor panel", (0, 3), ha="left", va="bottom",
              color=INK2)
        _vertical_dimension(ax, 40.0, 0.0, panel_z, f"offsetLocZ\n{panel_z:g} mm")
        cross = np.array([35.0, -75.0])
        title = "(a) Seat rail on a cross beam, seen from behind"
    else:
        # seen from the left: x to the right, z up; the cross beam runs out of the drawing plane (towards -y)
        _sheets(ax, "CrossBeam", lambda p: (p[0] * mm, p[1] * mm), MEMBER)  # profile x -> x, profile y -> z
        top = max(y for _, y in rail.values()) * mm
        ax.add_patch(Rectangle((-DETAIL - 5, 0.0), 2 * DETAIL + 10, top, facecolor=to_rgba(MEMBER, 0.16),
                               edgecolor="none", zorder=1))
        label(ax, (-DETAIL + 4, top / 2), "seat rail", (0, 0), ha="left", color=INK2)
        ax.add_patch(Rectangle((-DETAIL - 5, panel_z), 2 * DETAIL + 10, PANEL_THICKNESS * mm,
                               facecolor=to_rgba(MUTED, 0.35), edgecolor="none", zorder=2))
        label(ax, (-DETAIL + 4, panel_z + PANEL_THICKNESS * mm), "floor panel", (0, 3), ha="left", va="bottom",
              color=INK2)
        cross = np.array([35.0, -75.0])
        title = "(b) Cross beam, seen from the left"
    dot(ax, (0.0, 0.0), size=3.5)
    length = 14.0
    for d, name in (((1, 0), "profile x"), ((0, 1), "profile y")):
        tip = cross + length * np.array(d)
        arrow(ax, cross, tip, color=INK, lw=LINE["secondary"], head=6)
        if d[0]:
            label(ax, tip, name, (4, 0), ha="left")
        else:
            label(ax, tip, name, (0, 3), va="bottom")
    shell._out_of_plane(ax, cross)
    label(ax, cross, "path", (-6, -6), ha="right", va="top", color=INK2)
    ax.set_xlim(-DETAIL, DETAIL)
    ax.set_ylim(-height - 12.0, 48.0)
    ax.set_aspect("equal")
    ax.set_anchor("N")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(COLORS["axis"])
    ax.set_title(title, fontsize=FONT_SIZE["base"])


def _vertical_dimension(ax, x, z0, z1, text):
    ax.plot([x, x], [z0, z1], color=INK2, lw=LINE["reference"], zorder=6)
    for z in (z0, z1):
        ax.plot([x - 2.5, x + 2.5], [z, z], color=INK2, lw=LINE["reference"], zorder=6)
    label(ax, (x, (z0 + z1) / 2), text, (4, 0), ha="left", color=INK2)


# --------------------------------------------------------------------- example
def cross_beam_xml(deck, frame, x, z):
    uid = beam_uid(deck, x)
    return "\n".join([
        f'<{deck}CrossBeam uID="{uid}">', f"    <structuralElementUID>CrossBeam</structuralElementUID>",
        f"    <frameUID>{frame}</frameUID>", f"    <positionZ>{z:g}</positionZ>",
        f'    <alignment uID="{uid}_alignment">', f"        <offset1LocX>{BEAM_OFFSET:g}</offset1LocX>",
        f"        <offset2LocX>{BEAM_OFFSET:g}</offset2LocX>", "    </alignment>", f"</{deck}CrossBeam>"])


def strut_xml(deck, frame, x, side, y, angle):
    return "\n".join([
        f'<{deck}CrossBeamStrut uID="{strut_uid(deck, x, side)}">', "    <structuralElementUID>Strut</structuralElementUID>",
        f"    <frameUID>{frame}</frameUID>", f"    <crossBeamUID>{beam_uid(deck, x)}</crossBeamUID>",
        f"    <positionYAtCrossBeam>{y:g}</positionYAtCrossBeam>", f"    <angleX>{angle:g}</angleX>",
        f"</{deck}CrossBeamStrut>"])


def rail_position_xml(deck, uid, i, x, y):
    return "\n".join([
        f'<longFloorBeamPosition uID="{uid}_position{i + 1}">', "    <structuralElementUID>SeatRail</structuralElementUID>",
        f"    <crossBeamUID>{beam_uid(deck, x)}</crossBeamUID>", f"    <positionY>{y:g}</positionY>",
        "</longFloorBeamPosition>"])


def rail_xml(deck, side, y, count=None):
    """A rail over the cross beams of all floor frames; count limits the positions written (for an excerpt)."""
    uid = rail_uid(deck, side)
    frames = floor_frames()
    shown = frames[:count] if count else frames
    return "\n".join([f'<longFloorBeam uID="{uid}">',
                      *(indent(rail_position_xml(deck, uid, i, x, y), 1) for i, (_, x) in enumerate(shown)),
                      *(["    ..."] if len(shown) < len(frames) else []), "</longFloorBeam>"])


def panel_xml(row):
    uid, rail1, rail2, _, _, x0, x1 = row
    return "\n".join([
        f'<floorPanel uID="{uid}">', f"    <startX>{x0:g}</startX>", f"    <endX>{x1:g}</endX>",
        f"    <longFloorBeam1UID>{rail1}</longFloorBeam1UID>", f"    <longFloorBeam2UID>{rail2}</longFloorBeam2UID>",
        f"    <sheetElementUID>{PANEL_ELEMENT}</sheetElementUID>", f'    <alignment uID="{uid}_alignment">',
        f"        <offset1LocY>{PANEL_OFFSET_Y:g}</offset1LocY>", f"        <offset2LocY>{-PANEL_OFFSET_Y:g}</offset2LocY>",
        f"        <offsetLocZ>{PANEL_OFFSET_Z:g}</offsetLocZ>", "    </alignment>", "</floorPanel>"])


def floor_xml():
    """The floor collections of the structure, in the order of fuselageStructureType."""
    blocks = []
    for deck, (z, _, struts) in DECKS.items():
        blocks.append(shell.collection(f"{deck}CrossBeams", [cross_beam_xml(deck, f, x, z) for f, x in floor_frames()]))
        blocks.append(shell.collection(f"{deck}CrossBeamStruts", [strut_xml(deck, f, x, side, y, a)
                                                                  for f, x in floor_frames() for side, y, a in struts]))
    blocks.append(shell.collection("longFloorBeams", [rail_xml(deck, side, y) for deck, (_, rails, _) in DECKS.items()
                                                      for side, y in rails]))
    blocks.append(shell.collection("floorPanels", [panel_xml(p) for deck in DECKS for p in panels(deck)]))
    return "\n".join(blocks)


def profile_xml(uid):
    name, description, points, sheets = PROFILES[uid]
    p = f"{uid}Profile"
    lines = [f'<structuralProfile2D uID="{p}">', f"    <name>{name}</name>", f"    <description>{description}</description>",
             "    <pointList>"]
    for key, (x, y) in points.items():
        lines += [f'        <point uID="{p}_{key}">', f"            <x>{x:g}</x>", f"            <y>{y:g}</y>",
                  "        </point>"]
    lines += ["    </pointList>", "    <sheetList>"]
    for key, (start, end, readable, _) in sheets.items():
        lines += [f'        <sheet uID="{p}_{key}">', f"            <name>{readable}</name>",
                  f"            <fromPointUID>{p}_{start}</fromPointUID>", f"            <toPointUID>{p}_{end}</toPointUID>",
                  "        </sheet>"]
    return "\n".join([*lines, "    </sheetList>", "</structuralProfile2D>"])


def element_xml(uid):
    name, _, _, sheets = PROFILES[uid]
    lines = [f'<profileBasedStructuralElement uID="{uid}">', f"    <name>{name}</name>"]
    for key, (*_, thickness) in sheets.items():
        lines += ["    <sheetProperties>", f"        <sheetUID>{uid}Profile_{key}</sheetUID>",
                  f"        <materialUID>{structuralProfile.MATERIAL_UID}</materialUID>",
                  f"        <thickness>{thickness:g}</thickness>", "    </sheetProperties>"]
    return "\n".join([*lines, f"    <structuralProfileUID>{uid}Profile</structuralProfileUID>",
                      "</profileBasedStructuralElement>"])


def panel_element_xml():
    return "\n".join([f'<sheetBasedStructuralElement uID="{PANEL_ELEMENT}">', "    <materialDefinition>",
                      f"        <materialUID>{PANEL_MATERIAL[0]}</materialUID>",
                      f"        <thickness>{PANEL_THICKNESS:g}</thickness>", "    </materialDefinition>",
                      "</sheetBasedStructuralElement>"])


def panel_material_xml():
    uid, name, description, rho, e, g = PANEL_MATERIAL
    return "\n".join([f'<material uID="{uid}">', f"    <name>{name}</name>", f"    <description>{description}</description>",
                      f"    <rho>{rho:g}</rho>", "    <isotropicProperties>", f"        <E>{e:.0f}</E>",
                      f"        <G>{g:.0f}</G>", "    </isotropicProperties>", "</material>"])


def floor_profiles_xml():
    return [profile_xml(uid) for uid in PROFILES]


def floor_elements_xml():
    return [element_xml(uid) for uid in PROFILES]


# --------------------------------------------------------------------- report
def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    floor_x = [x for _, x in floor_frames()]
    print(f"Cross beams on the frames at x = {floor_x}")
    for deck, (z, rails, struts) in DECKS.items():
        start, end = beam_ends(z)
        short = beam_ends(z, (BEAM_OFFSET, BEAM_OFFSET))
        print(f"{deck}: cross beams at z = {z:g}, path from y = {start:.4f} to {end:.4f}, shortened to {short[0]:.4f} "
              f"to {short[1]:.4f}")
        for _, y in rails:
            assert short[1] < y < short[0], (deck, y)
        for side, y, angle in struts:
            foot = strut_foot(y, z, angle)
            print(f"    strut {side}: from ({y:g}, {z:g}) at angleX {angle:g} to the frame at "
                  f"({foot[0]:.4f}, {foot[1]:.4f}), length {np.linalg.norm(foot - (y, z)):.4f} m")
    # the passenger struts pass beside the cargo floor
    cargo_half = beam_ends(CARGO_Z)[0]
    for _, y, angle in PAX_STRUTS:
        assert abs(y) > cargo_half and strut_foot(y, PAX_Z, angle)[1] > CARGO_Z, "passenger strut hits the cargo floor"
    # the frame through the door does not reach the floors on the right side
    door_frame = next(p for _, p in shell.frames() if len(p) > 1)
    gap = (door_frame[1][1], door_frame[0][1])
    for deck, (z, *_) in DECKS.items():
        right = 360.0 - float(np.degrees(np.arccos(z / RADIUS)))
        print(f"{deck}: the floor meets the right side at {right:.1f} deg, the frame at x = {door_frame[0][0]:g} is "
              f"open from {gap[0]:g} to {gap[1]:g} deg")
        assert gap[0] < right < gap[1]
    # cargo floor at the sill of the cargo door
    door_sill = RADIUS * np.cos(np.radians(shell.DOOR_ANGLES[0]))
    print(f"Cargo floor (top of the rails) at z = {CARGO_Z + SEAT_RAIL_HEIGHT:g}, sill of the cargo door at "
          f"{door_sill:.3f}")
    # the wing box lies under the passenger floor
    box = wing_box_top()
    lower = PAX_Z - BEAM_HEIGHT
    print(f"Wing box at the root up to z = {box:.4f} (wing at z = {WING_TRANSLATION[2]:g}), lower edge of the "
          f"passenger cross beams {lower:.4f}: clearance {1000 * (lower - box):.0f} mm")
    assert lower - box >= WING_CLEARANCE
    # over-wing exits: the step inside (sill over the floor) and outside (sill over the wing)
    for row in CUTOUTS:
        if row[0].startswith("emergencyExit"):
            sill = row[5] - row[10] / 2
            y = np.sqrt(RADIUS**2 - sill**2)
            wing = wing_upper_at(row[3], y)
            print(f"{row[0]}: sill at z = {sill:.3f}, {sill - FLOOR_Z:.3f} m over the floor, {sill - wing:.3f} m over "
                  f"the wing (z = {wing:.3f} at x = {row[3]:g}, y = {y:.3f})")
            assert 0.0 < sill - FLOOR_Z <= 0.51 and 0.0 < sill - wing <= 0.69  # CS 25.807, Type III: 20 in, 27 in


def _block(xml, tag):
    """The element tag inside xml, dedented to column 0."""
    lines = xml.splitlines()
    first = next(i for i, line in enumerate(lines) if line.lstrip().startswith(f"<{tag}"))
    last = next(i for i, line in enumerate(lines) if line.strip() == f"</{tag}>")
    depth = len(lines[first]) - len(lines[first].lstrip())
    return "\n".join(line[depth:] for line in lines[first:last + 1])


def excerpts():
    (frame, x), z = floor_frames()[0], PAX_Z
    side, y, angle = PAX_STRUTS[1]
    rail = PAX_RAILS[2]
    panel = next(p for p in panels("pax") if p[0].endswith("C1"))
    return [
        ("crossBeamAssemblyPositionType", shell.collection("paxCrossBeams", [cross_beam_xml("pax", frame, x, z)],
                                                           more=True)),
        ("crossBeamStrutAssemblyPositionType", shell.collection("paxCrossBeamStruts",
                                                                [strut_xml("pax", frame, x, side, y, angle)],
                                                                more=True)),
        ("longFloorBeamType", shell.collection("longFloorBeams", [rail_xml("pax", *rail, count=2)], more=True)),
        ("longFloorBeamPositionType", rail_position_xml("pax", rail_uid("pax", rail[0]), 0, x, rail[1])),
        ("floorPanelType", shell.collection("floorPanels", [panel_xml(panel)], more=True)),
        ("alignmentCrossBeamType", _block(cross_beam_xml("pax", frame, x, z), "alignment")),
        ("alignmentFloorPanelType", _block(panel_xml(panel), "alignment")),
    ]


def main():
    figure_floor()
    figure_panel()
    figure_profile()
    shell.write_example()
    report()
    print(f"\nWritten {shell.EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in excerpts():
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

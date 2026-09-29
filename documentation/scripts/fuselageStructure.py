# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the shell of the fuselage
structure (fuselageStructureType, skinType, skinSegmentType, stringerType, frameType,
stringerFramePositionType, alignmentStringFrameType). The structure is placed in
the fuselage of the other examples, imported from fuselage.py together with its
cut-outs from fuselageCutOut.py, and its profiles come from structuralProfile.py.

Run from the repository root:

    uv run documentation/scripts/fuselageStructure.py

The script writes

    documentation/figures/fuselageStructure.png
    documentation/figures/stringerFramePosition.png
    documentation/figures/stringerFrameProfile.png
    examples/fuselageStructure.xml

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: the points of the positions on the
surface, the clearance between the cargo door and the stringers and frames around
it, and the length of the frame that runs around the door. The schema documentation
is not written by this script; copy the printed excerpts there when the example
changes.

Definitions shown (as in the documentation), all in the fuselage coordinate system:

- A position is the point where the ray from the reference point (positionX,
  referenceY, referenceZ), in the direction of the z-axis rotated about the x-axis
  by referenceAngle, meets the surface (as for a cut-out, fuselageCutOut.py).
- A stringer runs on the surface from each of its positions to the next. A frame
  with one position is the whole cross section of the surface in the plane
  x = positionX; a frame with several positions runs on the surface from each
  position to the next, in the direction of increasing referenceAngle.
- The coordinate system of the profile at a point of the path has its x-axis along
  the path, its z-axis normal to the surface and pointing inwards, and its y-axis
  z cross x. The x-axis of the two-dimensional profile lies along this y-axis and
  its y-axis along this z-axis. The alignment first rotates the profile about the
  x-axis by rotationLocX and then moves it by translationLocY and translationLocZ.
  The path of a frame with one position runs in the direction of increasing angle.
- A skin panel extends along x from its start frame to its end frame and around the
  fuselage from its start stringer, in the direction of increasing angle, to its end
  stringer. The skin outside all panels is the standard sheet.

The fuselage cross section is a circle in the barrel of the example, so the points
of the positions and the paths are found in closed form.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle

from example_xml import indent, write_cpacs_file
from figure_style import (COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, axes_cross, dot, figure_style, label, leader,
                          save_figure)
from fuselage import CYLINDER, DIAMETER, FUSELAGE_UID, LOFT, circle_profile_xml
from fuselageCutOut import CUTOUTS, centre, cutout, frame as cutout_frame, fuselage_with_cutouts_xml, on_surface
from fuselageCutOut import rounded_rectangle
import structuralProfile

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageStructure.xml"

# Colors of the fuselage structure: stringers and the construction of a position in series 1, frames in series 3
# (like the ribs of the wing), the cut-out in series 2 (as in fuselageCutOut.py), skin panels as a wash of series 1.
STRINGER = COLORS["series1"]
FRAME = COLORS["series3"]
CUTOUT = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
# The barrel between the forward passenger door (x = 5.8 to 6.6 m) and the wing (from x = 10 m), around the forward
# cargo door on the right side of the lower lobe (x = 7.5 to 8.5 m). Frames at a pitch of 0.5 m, stringers every
# 15 degrees; all reference points on the fuselage axis.
FRAME_X = [7.0 + 0.5 * i for i in range(6)]
STRINGER_ANGLES = list(range(0, 360, 15))
BARREL = (FRAME_X[0], FRAME_X[-1])
CARGO_DOOR = cutout(next(row for row in CUTOUTS if row[0] == "cargoDoorFwd"))
DOOR_STRINGERS = (210, 255)  # the stringers along the lower and the upper edge of the cargo door
FULL_FRAME_ANGLE = 0.0  # a frame with one position starts at the top

STRINGER_ELEMENT = structuralProfile.ELEMENT_UID  # T-stringer, 25 mm high
STRINGER_HEIGHT = structuralProfile.POINTS["P4"][1]
FRAME_ELEMENT = "ZFrame"
FRAME_PROFILE = "ZFrameProfile"
# Z-shaped frame, 80 mm high: outer flange of 20 mm on the skin side, inner flange of 25 mm, all in metres.
FRAME_POINTS = {"P1": (0.0, 0.0), "P2": (0.02, 0.0), "P3": (0.0, 0.08), "P4": (-0.025, 0.08)}
FRAME_SHEETS = {"S1": ("P1", "P2", "Outer flange", 0.0016), "S2": ("P1", "P3", "Web", 0.0016),
                "S3": ("P3", "P4", "Inner flange", 0.002)}
# The frames stand on the stringers: their profile is moved inwards by the height of the stringer.
FRAME_OFFSET = STRINGER_HEIGHT

# Skin: sheet elements (uID, thickness [m]) and panels (uID suffix, sheet, start and end frame x, start and end
# stringer angle). The crown panel runs across the top, from 315 over 0 to 45 degrees.
SHEETS = [("SkinStandard", 0.0016), ("SkinCrown", 0.0018), ("SkinKeel", 0.0025), ("SkinDoorSurround", 0.0032)]
STANDARD_SHEET = "SkinStandard"
PANELS = [
    ("crownPanel", "SkinCrown", 7.0, 9.5, 315, 45),
    ("keelPanel", "SkinKeel", 7.0, 9.5, 135, 210),
    ("doorSurroundPanel", "SkinDoorSurround", 7.0, 9.0, 210, 270),
]
PANEL_NAMES = {"crownPanel": "crown panel", "keelPanel": "keel panel", "doorSurroundPanel": "door surround"}


def frame_uid(x):
    return f"{FUSELAGE_UID}_frame{FRAME_X.index(x) + 1}"


def stringer_uid(angle, part=""):
    return f"{FUSELAGE_UID}_stringer{angle:03d}{part}"


# ------------------------------------------------------------------ geometry
def surface_point(x, angle, ref=(0.0, 0.0)):
    """Point where the ray of a position meets the surface (see fuselageCutOut.centre)."""
    point, _ = centre({"uid": "position", "x": x, "ref_y": ref[0], "ref_z": ref[1], "angle": angle})
    return point


def angle_of(point):
    """referenceAngle of a point seen from the fuselage axis, in [0, 360)."""
    return float(np.degrees(np.arctan2(-point[1], point[2])) % 360.0)


def door_outline():
    """Outline of the cargo door on the surface, as rows (x, angle in [0, 360))."""
    point, _ = centre(CARGO_DOOR)
    ex, ey, ez = cutout_frame(CARGO_DOOR)
    rows = []
    for v, w in rounded_rectangle(CARGO_DOOR["width"], CARGO_DOOR["height"], CARGO_DOOR["fillet"], n=48):
        q = point + v * ey + w * ez
        hits, gap = on_surface(q, ex)
        assert hits
        s = q + gap * ex
        rows.append((s[0], angle_of(s)))
    return np.array(rows)


DOOR = door_outline()
DOOR_X = (float(DOOR[:, 0].min()), float(DOOR[:, 0].max()))
DOOR_ANGLES = (float(DOOR[:, 1].min()), float(DOOR[:, 1].max()))


def interrupted(angle):
    """Whether the stringer at the angle runs through the cargo door."""
    return DOOR_STRINGERS[0] < angle < DOOR_STRINGERS[1]


def stringers():
    """(uID, [(x, angle), ...]) of all stringers; those through the door end at the frames at its edges."""
    rows = []
    for a in STRINGER_ANGLES:
        if interrupted(a):
            rows.append((stringer_uid(a, "Fwd"), [(BARREL[0], a), (DOOR_X[0], a)]))
            rows.append((stringer_uid(a, "Aft"), [(DOOR_X[1], a), (BARREL[1], a)]))
        else:
            rows.append((stringer_uid(a), [(BARREL[0], a), (BARREL[1], a)]))
    return rows


def frames():
    """(uID, [(x, angle), ...]) of all frames. A frame through the door runs from the stringer above the door over
    the top to the stringer below it: from 255 degrees in the direction of increasing angle to 210 degrees."""
    rows = []
    for x in FRAME_X:
        if DOOR_X[0] < x < DOOR_X[1]:
            rows.append((frame_uid(x), [(x, float(DOOR_STRINGERS[1])), (x, float(DOOR_STRINGERS[0]))]))
        else:
            rows.append((frame_uid(x), [(x, FULL_FRAME_ANGLE)]))
    return rows


def sweep(a0, a1):
    """Angle swept from a0 to a1 in the direction of increasing angle, in (0, 360]."""
    d = (a1 - a0) % 360.0
    return d if d > 0.0 else 360.0


def frame_path(positions, n=721):
    """Points of the frame on the surface (all positions of the example lie in one plane x = const)."""
    x = positions[0][0]
    if len(positions) == 1:
        angles = positions[0][1] + np.linspace(0.0, 360.0, n)
    else:
        angles = np.concatenate([a0 + np.linspace(0.0, sweep(a0, a1), n)
                                 for (_, a0), (_, a1) in zip(positions, positions[1:])])
    return np.array([surface_point(x, a) for a in angles])


def path_length(points):
    return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))


def profile_axes(point, tangent):
    """Axes x, y, z of the profile coordinate system at a point of a path: x along the path, z the inward normal."""
    ex = np.asarray(tangent, dtype=float) / np.linalg.norm(tangent)
    radial = np.array([0.0, point[1], point[2]])
    ez = -radial / np.linalg.norm(radial)  # the barrel is a circle: the normal is radial
    ez -= (ez @ ex) * ex
    ez /= np.linalg.norm(ez)
    return ex, np.cross(ez, ex), ez


def place_profile(points, point, tangent, alignment=(0.0, 0.0, 0.0)):
    """Profile points (x, y) placed at a point of a path: rotated about the local x-axis by rotationLocX [deg], then
    moved by translationLocY and translationLocZ; alignment = (rotationLocX, translationLocY, translationLocZ)."""
    ex, ey, ez = profile_axes(point, tangent)
    r = np.radians(alignment[0])
    local = np.array([[np.cos(r) * u - np.sin(r) * v + alignment[1], np.sin(r) * u + np.cos(r) * v + alignment[2]]
                      for u, v in points])
    return np.array([point + u * ey + v * ez for u, v in local])


# --------------------------------------------------------------------- figures
RADIUS = DIAMETER / 2


def _development(angle):
    """Horizontal coordinate of the developed barrel [m]: the arc length from 0 degrees, the range starting at the
    stringer below the door (210 - 360 = -150 degrees), so that every panel is drawn in one piece."""
    a = (np.asarray(angle, dtype=float) - DOOR_STRINGERS[0]) % 360.0 + DOOR_STRINGERS[0] - 360.0
    return RADIUS * np.radians(a)


def figure_structure():
    """The barrel of the example developed into the plane: frames, stringers, the cargo door and the skin panels."""
    left, right = DOOR_STRINGERS[0] - 360.0, float(DOOR_STRINGERS[0])
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.9))
        s0, s1 = RADIUS * np.radians(left), RADIUS * np.radians(right)
        # skin panels as a wash between their frames and stringers, named above the barrel over the angles they span;
        # the rest of the barrel is the standard sheet
        above = BARREL[1] + 0.22
        spans = []
        for suffix, _, x0, x1, a0, a1 in PANELS:
            u0 = float(_development(a0))
            width = RADIUS * np.radians(sweep(a0, a1))
            ax.add_patch(Rectangle((u0, x0), width, x1 - x0, facecolor=to_rgba(STRINGER, 0.13), edgecolor="none",
                                   zorder=0))
            spans.append((u0, u0 + width, PANEL_NAMES[suffix], INK))
        taken = sorted(spans)
        free = [(a, b) for (_, a, *_), (b, *_) in zip(taken, taken[1:]) if b - a > 0.1]
        spans += [(a, b, "standard\nsheet", INK2) for a, b in free]
        for u0, u1, name, color in spans:
            ax.plot([u0 + 0.04, u1 - 0.04], [above, above], color=MUTED, lw=LINE["reference"], clip_on=False)
            for u in (u0 + 0.04, u1 - 0.04):
                ax.plot([u, u], [above - 0.06, above + 0.06], color=MUTED, lw=LINE["reference"], clip_on=False)
            label(ax, (0.5 * (u0 + u1), above), name, (0, 3), va="bottom", color=color)
        # stringers and frames
        for _, positions in stringers():
            u = float(_development(positions[0][1]))
            ax.plot([u, u], [positions[0][0], positions[-1][0]], color=STRINGER, lw=LINE["secondary"], zorder=2)
        for _, positions in frames():
            x = positions[0][0]
            if len(positions) == 1:
                ax.plot([s0, s1], [x, x], color=FRAME, lw=LINE["data"], zorder=3)
            else:
                u0 = float(_development(positions[0][1]))
                u1 = u0 + RADIUS * np.radians(sweep(positions[0][1], positions[1][1]))
                ax.plot([u0, u1], [x, x], color=FRAME, lw=LINE["data"], zorder=3)
        # the cargo door
        outline = np.column_stack([_development(DOOR[:, 1]), DOOR[:, 0]])
        ax.add_patch(Polygon(outline, closed=True, facecolor=to_rgba(CUTOUT, 0.12), edgecolor=CUTOUT,
                             lw=LINE["data"], joinstyle="round", zorder=4))
        # axes: the angle below, x on the left
        ticks = [0, 45, 90, 135, 180, 225, 270, 315]
        ax.set_xticks([float(_development(a)) for a in ticks], [f"{a}" for a in ticks])
        ax.set_xlim(s0 - 0.05, s1 + 0.05)
        ax.set_ylim(BARREL[0] - 0.12, above + 0.3)
        ax.spines["left"].set_bounds(BARREL[0] - 0.12, BARREL[1] + 0.12)
        ax.set_yticks(FRAME_X, [f"{x:g}" for x in FRAME_X])
        ax.set_xlabel("referenceAngle [deg]")
        ax.set_ylabel("x [m]")
        ax.set_aspect("equal")
        ax.spines["bottom"].set_bounds(s0, s1)
        handles = [Line2D([], [], color=FRAME, lw=LINE["data"]), Line2D([], [], color=STRINGER, lw=LINE["secondary"]),
                   Patch(facecolor=to_rgba(STRINGER, 0.13), edgecolor="none"),
                   Patch(facecolor=to_rgba(CUTOUT, 0.12), edgecolor=CUTOUT, lw=LINE["data"])]
        fig.legend(handles, ["frame", "stringer", "skin panel", "cargo door (cut-out)"], loc="lower center", ncol=4,
                   bbox_to_anchor=(0.5, -0.08), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "fuselageStructure.png")


def figure_position():
    """The section through the frame around the door, seen from behind: reference point, rays, and the frame from its
    first to its last position."""
    uid, positions = next(f for f in frames() if len(f[1]) > 1)
    x = positions[0][0]
    with figure_style():
        fig, sec = plt.subplots(figsize=(0.62 * FULL_WIDTH, 3.9))
        # section at x, seen from behind: y to the right, z up
        t = np.linspace(0.0, 2.0 * np.pi, 721)
        sec.add_patch(Polygon(np.column_stack([RADIUS * np.sin(t), RADIUS * np.cos(t)]), closed=True,
                              facecolor=to_rgba(MUTED, 0.06), edgecolor=MUTED, lw=LINE["reference"], zorder=1))
        path = frame_path(positions)
        sec.plot(path[:, 1], path[:, 2], color=FRAME, lw=3.0, solid_capstyle="butt", zorder=3)
        # the door between the two positions: the arc of the contour it removes
        door = np.array([surface_point(x, a) for a in np.linspace(DOOR_ANGLES[0], DOOR_ANGLES[1], 100)])
        sec.plot(door[:, 1], door[:, 2], color=CUTOUT, lw=3.0, solid_capstyle="butt", zorder=3)
        ref = np.zeros(2)
        first, last = (surface_point(*p)[1:] for p in positions)
        # angle of the first position, from the z direction, as a pale area
        r_angle = 0.42
        wedge = np.radians(np.linspace(0.0, positions[0][1], 180))
        sec.add_patch(Polygon(np.vstack([ref, r_angle * np.column_stack([-np.sin(wedge), np.cos(wedge)])]),
                              closed=True, facecolor=STRINGER, alpha=0.14, edgecolor="none", zorder=2))
        sec.plot([0.0, 0.0], [0.0, 0.75], color=MUTED, lw=LINE["reference"], zorder=3)
        middle = np.radians(positions[0][1] / 2)
        label(sec, (r_angle + 0.12) * np.array([-np.sin(middle), np.cos(middle)]),
              f"referenceAngle\n{positions[0][1]:g}°", (0, 0), ha="center", va="top", color=INK)
        for point in (first, last):
            arrow(sec, ref, point, color=STRINGER, lw=LINE["data"], head=8)
            dot(sec, point, color=STRINGER)
        label(sec, first, f"first position\n{positions[0][1]:g}°", (7, 2), ha="left", va="bottom")
        label(sec, last, f"last position\n{positions[1][1]:g}°", (7, -2), ha="left", va="top")
        dot(sec, ref)
        label(sec, ref, "reference point", (-6, 6), ha="right", va="bottom")
        # direction of the frame: an arrow on the frame at the top, from the first towards the last position
        a = np.radians(np.array([-12.0, 12.0]))
        tip = (RADIUS + 0.22) * np.column_stack([-np.sin(a), np.cos(a)])
        sec.annotate("", xy=tip[1], xytext=tip[0], zorder=5, arrowprops={
            "arrowstyle": "-|>", "lw": LINE["secondary"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
            "color": INK, "connectionstyle": "arc3,rad=0.12"})
        label(sec, (0.0, RADIUS + 0.28), "frame, in the direction of\nincreasing referenceAngle", (0, 2), va="bottom")
        label(sec, door[len(door) // 2, 1:], "cargo\ndoor", (8, 0), ha="left")
        axes_cross(sec, (-2.0, -1.95), [(1, 0), (0, 1)], ["y", "z"], 0.45, [(6, 0), (0, 7)])
        sec.set_xlim(-2.2, 2.6)
        sec.set_ylim(-2.05, 2.35)
        sec.set_aspect("equal")
        sec.axis("off")
        sec.set_title(f"Section at positionX = {x:g} m, seen from behind", fontsize=FONT_SIZE["base"])
        save_figure(fig, FIGURES / "stringerFramePosition.png")


def figure_profile():
    """(a) A stringer at the top, (b) a frame at the top: the profile coordinate system and the alignment."""
    with figure_style():
        fig, (top, side) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 4.2), gridspec_kw={"wspace": 0.08})
        # (a) a stringer at the top, section between two frames, seen from behind; lengths in millimetres
        _profile_detail(top, "stringer")
        # (b) a frame at the top, seen from the left: x to the right, z up
        _profile_detail(side, "frame")
        save_figure(fig, FIGURES / "stringerFrameProfile.png")


DETAIL_WIDTH = 62.0  # half width of the detail views [mm]
DETAIL_Z = ((-62.0, 12.0), (-118.0, 12.0))  # vertical range of the detail views of the stringer and the frame [mm]
DETAIL_CROSS = (42.0, -40.0)  # origin of the axes cross beside the profile [mm]


def _profile_detail(ax, kind):
    """Profile of a stringer or a frame at the top of the fuselage, in millimetres relative to the surface point.
    The axes of the profile coordinate system are drawn as a cross beside the profile, so that they do not lie on
    its sheets."""
    mm = 1000.0
    top = surface_point(8.0, 0.0)
    if kind == "stringer":
        # seen from behind: horizontal y, vertical z; the stringer runs along +x, out of the drawing plane
        tangent = (1.0, 0.0, 0.0)
        view = lambda p: np.array([p[1], p[2] - top[2]]) * mm  # noqa: E731
        points, sheets, alignment = structuralProfile.POINTS, {k: v[:2] for k, v in structuralProfile.SHEETS.items()}, \
            (0.0, 0.0, 0.0)
        color, title, limits = STRINGER, "(a) Stringer at the top, seen from behind", DETAIL_Z[0]
    else:
        # seen from the left: horizontal x, vertical z; the frame runs towards -y at the top, out of the drawing plane
        tangent = (0.0, -1.0, 0.0)
        view = lambda p: np.array([p[0] - top[0], p[2] - top[2]]) * mm  # noqa: E731
        points, sheets, alignment = FRAME_POINTS, {k: v[:2] for k, v in FRAME_SHEETS.items()}, (0.0, 0.0, FRAME_OFFSET)
        color, title, limits = FRAME, "(b) Frame at the top, seen from the left", DETAIL_Z[1]
    names = list(points)
    placed = dict(zip(names, place_profile([points[n] for n in names], top, tangent, alignment), strict=True))
    w = DETAIL_WIDTH + 5.0
    if kind == "stringer":
        # the skin: the arc of the surface
        a = np.linspace(-w, w, 121) / mm / RADIUS
        skin = np.array([view((0.0, -RADIUS * np.sin(b), RADIUS * np.cos(b))) for b in a])
    else:
        skin = np.array([(-w, 0.0), (w, 0.0)])
        # the stringer at the top runs along x under the skin: its web, seen from the side
        height = STRINGER_HEIGHT * mm
        ax.add_patch(Rectangle((-w, -height), 2 * w, height, facecolor=to_rgba(STRINGER, 0.16), edgecolor="none",
                               zorder=1))
        label(ax, (-DETAIL_WIDTH + 3.0, -height / 2), "stringer", (0, 0), ha="left", color=INK2)
        # the offset of the profile by translationLocZ, between the skin and the origin of the profile
        x_dim = 10.0
        ax.plot([x_dim, x_dim], [0.0, -height], color=MUTED, lw=LINE["reference"], zorder=3)
        for z in (0.0, -height):
            ax.plot([x_dim - 2.0, x_dim + 2.0], [z, z], color=MUTED, lw=LINE["reference"], zorder=3)
        label(ax, (x_dim, -height / 2), f"translationLocZ\n{FRAME_OFFSET * mm:g} mm", (4, 0), ha="left", color=INK2)
    ax.plot(*skin.T, color=MUTED, lw=LINE["secondary"], zorder=2)
    label(ax, (-DETAIL_WIDTH + 3.0, 0.0), "surface", (0, 3), ha="left", va="bottom", color=INK2)
    for start, end in sheets.values():
        ax.plot(*np.array([view(placed[start]), view(placed[end])]).T, color=color, lw=2.2,
                solid_capstyle="butt", zorder=4)
    dot(ax, view(top), size=3.5)
    # the axes of the profile coordinate system, beside the profile
    ex, ey, ez = profile_axes(top, tangent)
    origin = np.array(DETAIL_CROSS)
    length = 13.0
    for vector, name in ((ey, "y: profile x"), (ez, "z: profile y")):
        d = view(top + vector / mm) - view(top)
        tip = origin + length * d / np.linalg.norm(d)
        arrow(ax, origin, tip, color=INK, lw=LINE["secondary"], head=6)
        if abs(d[0]) > abs(d[1]):
            label(ax, 0.5 * (origin + tip), name, (0, 4), va="bottom")
        else:
            label(ax, tip, name, (0, -3), va="top")
    _out_of_plane(ax, origin)
    label(ax, origin, "x", (7, 0), ha="left")
    ax.set_xlim(-DETAIL_WIDTH, DETAIL_WIDTH)
    ax.set_ylim(*limits)
    ax.set_aspect("equal")
    ax.set_anchor("N")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(COLORS["axis"])
    ax.set_title(title, fontsize=FONT_SIZE["base"])


def _out_of_plane(ax, xy, radius_pt=3.2):
    """Symbol for an axis pointing out of the drawing plane (circle with a dot)."""
    ax.plot(*xy, ls="none", marker="o", ms=2 * radius_pt, mfc=COLORS["surface"], mec=INK, mew=LINE["secondary"],
            zorder=6)
    ax.plot(*xy, ls="none", marker="o", ms=1.6, color=INK, zorder=7)


# --------------------------------------------------------------------- example
def alignment_xml(uid, alignment):
    rotation, dy, dz = alignment
    lines = [f'<alignment uID="{uid}">']
    for tag, value in (("rotationLocX", rotation), ("translationLocY", dy), ("translationLocZ", dz)):
        if value:
            lines.append(f"    <{tag}>{value:g}</{tag}>")
    return "\n".join([*lines, "</alignment>"])


def position_xml(tag, uid, element, x, angle, alignment=None):
    lines = [f'<{tag} uID="{uid}">', f"    <structuralElementUID>{element}</structuralElementUID>",
             f"    <positionX>{x:g}</positionX>", "    <referenceY>0</referenceY>", "    <referenceZ>0</referenceZ>",
             f"    <referenceAngle>{angle:g}</referenceAngle>"]
    if alignment:
        lines.append(indent(alignment_xml(f"{uid}_alignment", alignment), 1))
    return "\n".join([*lines, f"</{tag}>"])


def stringer_xml(uid, positions):
    return "\n".join([f'<stringer uID="{uid}">',
                      *(indent(position_xml("stringerPosition", f"{uid}_position{i + 1}", STRINGER_ELEMENT, x, a), 1)
                        for i, (x, a) in enumerate(positions)), "</stringer>"])


def frame_xml(uid, positions):
    return "\n".join([f'<frame uID="{uid}">',
                      *(indent(position_xml("framePosition", f"{uid}_position{i + 1}", FRAME_ELEMENT, x, a,
                                            (0.0, 0.0, FRAME_OFFSET)), 1)
                        for i, (x, a) in enumerate(positions)), "</frame>"])


def panel_xml(panel):
    suffix, sheet, x0, x1, a0, a1 = panel
    return "\n".join([
        f'<skinSegment uID="{FUSELAGE_UID}_{suffix}">', f"    <sheetElementUID>{sheet}</sheetElementUID>",
        f"    <startFrameUID>{frame_uid(x0)}</startFrameUID>", f"    <endFrameUID>{frame_uid(x1)}</endFrameUID>",
        f"    <startStringerUID>{stringer_uid(a0)}</startStringerUID>",
        f"    <endStringerUID>{stringer_uid(a1)}</endStringerUID>", "</skinSegment>",
    ])


def skin_xml(panels=PANELS, more=False):
    return "\n".join(["<skin>", f"    <standardSheetElementUID>{STANDARD_SHEET}</standardSheetElementUID>",
                      "    <skinSegments>", *(indent(panel_xml(p), 2) for p in panels),
                      *(["        ..."] if more else []), "    </skinSegments>", "</skin>"])


def collection(tag, items, more=False):
    return "\n".join([f"<{tag}>", *(indent(item, 1) for item in items), *(["    ..."] if more else []), f"</{tag}>"])


def structure_xml():
    from fuselageFloor import floor_xml  # the floors stand on the frames of this shell

    return "\n".join(["<structure>", indent(skin_xml(), 1),
                      indent(collection("stringers", [stringer_xml(*s) for s in stringers()]), 1),
                      indent(collection("frames", [frame_xml(*f) for f in frames()]), 1), indent(floor_xml(), 1),
                      "</structure>"])


def fuselage_with_structure_xml():
    body = fuselage_with_cutouts_xml()
    assert body.endswith("\n</fuselage>")
    return body[: -len("</fuselage>")] + indent(structure_xml(), 1) + "\n</fuselage>"


def frame_profile_xml():
    lines = [f'<structuralProfile2D uID="{FRAME_PROFILE}">', "    <name>Z-frame</name>",
             "    <description>Outer flange of 20 mm, web of 80 mm height, inner flange of 25 mm</description>",
             "    <pointList>"]
    for name, (x, y) in FRAME_POINTS.items():
        lines += [f'        <point uID="{FRAME_PROFILE}_{name}">', f"            <x>{x:g}</x>",
                  f"            <y>{y:g}</y>", "        </point>"]
    lines += ["    </pointList>", "    <sheetList>"]
    for name, (start, end, readable, _) in FRAME_SHEETS.items():
        lines += [f'        <sheet uID="{FRAME_PROFILE}_{name}">', f"            <name>{readable}</name>",
                  f"            <fromPointUID>{FRAME_PROFILE}_{start}</fromPointUID>",
                  f"            <toPointUID>{FRAME_PROFILE}_{end}</toPointUID>", "        </sheet>"]
    return "\n".join([*lines, "    </sheetList>", "</structuralProfile2D>"])


def frame_element_xml():
    lines = [f'<profileBasedStructuralElement uID="{FRAME_ELEMENT}">', "    <name>Z-frame</name>"]
    for name, (_, _, _, thickness) in FRAME_SHEETS.items():
        lines += ["    <sheetProperties>", f"        <sheetUID>{FRAME_PROFILE}_{name}</sheetUID>",
                  f"        <materialUID>{structuralProfile.MATERIAL_UID}</materialUID>",
                  f"        <thickness>{thickness:g}</thickness>", "    </sheetProperties>"]
    return "\n".join([*lines, f"    <structuralProfileUID>{FRAME_PROFILE}</structuralProfileUID>",
                      "</profileBasedStructuralElement>"])


def sheet_elements_xml(*more):
    return collection("sheetBasedStructuralElements", [*(
        "\n".join([f'<sheetBasedStructuralElement uID="{uid}">', "    <materialDefinition>",
                   f"        <materialUID>{structuralProfile.MATERIAL_UID}</materialUID>",
                   f"        <thickness>{thickness:g}</thickness>", "    </materialDefinition>",
                   "</sheetBasedStructuralElement>"])
        for uid, thickness in SHEETS), *more])


def write_example():
    from fuselageFloor import floor_elements_xml, floor_profiles_xml, panel_element_xml, panel_material_xml

    profiles = "\n".join([structuralProfile.profile_xml(), frame_profile_xml(), *floor_profiles_xml()])
    elements = "\n".join([
        collection("profileBasedStructuralElements",
                   [structuralProfile.element_xml(), frame_element_xml(), *floor_elements_xml()]),
        sheet_elements_xml(panel_element_xml())])
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Fuselage structure",
        description="Skin, stringers, frames and floors of the barrel around the forward cargo door of a short-range "
                    "airliner fuselage.",
        model_uid="FuselageStructureAircraft",
        model_name="Fuselage structure example",
        components_tag="fuselages",
        components=fuselage_with_structure_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_profiles=[("structuralProfiles", profiles)],
        extra_vehicles=[("structuralElements", elements),
                        ("materials", "\n".join([structuralProfile.material_xml(), panel_material_xml()]))],
    )


# --------------------------------------------------------------------- report
def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    assert CYLINDER[0] <= BARREL[0] and BARREL[1] <= CYLINDER[1], "the barrel leaves the constant cross section"
    # the door lies between two frames and between the stringers along its edges
    assert np.isclose(DOOR_X[0], FRAME_X[2] - 0.5) and np.isclose(DOOR_X[1], FRAME_X[2] + 0.5), DOOR_X
    assert DOOR_STRINGERS[0] < DOOR_ANGLES[0] and DOOR_ANGLES[1] < DOOR_STRINGERS[1], DOOR_ANGLES
    below = RADIUS * np.radians(DOOR_ANGLES[0] - DOOR_STRINGERS[0])
    above = RADIUS * np.radians(DOOR_STRINGERS[1] - DOOR_ANGLES[1])
    print(f"Cargo door on the surface: x {DOOR_X[0]:.3f} to {DOOR_X[1]:.3f} m, referenceAngle {DOOR_ANGLES[0]:.2f} to "
          f"{DOOR_ANGLES[1]:.2f} deg; {below * 1000:.0f} mm above the stringer at {DOOR_STRINGERS[0]} deg, "
          f"{above * 1000:.0f} mm below the stringer at {DOOR_STRINGERS[1]} deg")
    cut = [a for a in STRINGER_ANGLES if interrupted(a)]
    print(f"Stringers ending at the door edge frames: {cut}")
    for uid, positions in frames():
        if len(positions) > 1:
            path = frame_path(positions)
            mid = path[len(path) // 2]
            print(f"{uid}: from {positions[0][1]:g} to {positions[1][1]:g} deg, sweep "
                  f"{sweep(positions[0][1], positions[1][1]):g} deg, length {path_length(path):.4f} m, "
                  f"middle at angle {angle_of(mid):.2f} deg, point {np.round(mid, 4)}")
            for x, a in positions:
                print(f"    position at {a:g} deg: {np.round(surface_point(x, a), 4)}")
    full = frame_path([(FRAME_X[0], FULL_FRAME_ANGLE)])
    print(f"Full frame: length {path_length(full):.4f} m (circumference {np.pi * DIAMETER:.4f} m)")
    for _, sheet, x0, x1, a0, a1 in PANELS:
        print(f"Panel {sheet}: x {x0:g}..{x1:g}, from {a0} over {sweep(a0, a1):g} deg to {a1}, area "
              f"{(x1 - x0) * RADIUS * np.radians(sweep(a0, a1)):.3f} m^2")
    # profile axes at the top: stringer running aft, frame running towards increasing angle
    top = surface_point(8.0, 0.0)
    for kind, tangent in (("stringer", (1.0, 0.0, 0.0)), ("frame", (0.0, -1.0, 0.0))):
        ex, ey, ez = profile_axes(top, tangent)
        print(f"Profile at the top, {kind}: x {np.round(ex, 3)}, y = profile x {np.round(ey, 3)}, "
              f"z = profile y {np.round(ez, 3)}")
    print(f"{len(stringers())} stringers, {len(frames())} frames")


def excerpts():
    frame_rows = frames()
    full = frame_rows[0]
    partial = next(f for f in frame_rows if len(f[1]) > 1)
    stringer = next(s for s in stringers() if s[0] == stringer_uid(45))
    x, a = full[1][0]
    return [
        ("stringerFramePositionType", position_xml("framePosition", f"{full[0]}_position1", FRAME_ELEMENT, x, a,
                                                   (0.0, 0.0, FRAME_OFFSET))),
        ("alignmentStringFrameType", alignment_xml(f"{full[0]}_position1_alignment", (0.0, 0.0, FRAME_OFFSET))),
        ("frameType", collection("frames", [frame_xml(*full), frame_xml(*partial)], more=True)),
        ("stringerType", collection("stringers", [stringer_xml(*stringer)], more=True)),
        ("skinType", skin_xml(PANELS[:1], more=True)),
    ]


def main():
    figure_structure()
    figure_position()
    figure_profile()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in excerpts():
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

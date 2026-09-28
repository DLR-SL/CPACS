# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the decks (decksType,
decksDeckType, the cabin geometry, aisles, spaces, doors and deck components) and
of the library of deck elements (deckElementsType). The deck is the passenger
cabin of the fuselage of the other examples, imported from fuselage.py, and its
doors reference the cut-outs of fuselageCutOut.py.

Run from the repository root:

    uv run documentation/scripts/deck.py

The script writes

    documentation/figures/deckLayout.png
    documentation/figures/deckCabinGeometry.png
    examples/fuselageDecks.xml

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: that every component lies inside the
cabin and clear of the aisle, the spaces and the other components, and the masses.
The schema documentation is not written by this script; copy the printed excerpts
there when the example changes.

Definitions shown (as in the documentation), all in the deck coordinate system: the
deck is placed relative to the fuselage, its origin at the rear wall of the cockpit
and at the height of the floor. A component places the coordinate system of the
element it references by its own transformation relative to the deck; the element
has its origin at the centre of the front lower edge of its box. The cabin geometry
gives, for each contour at the height z, the distance y of the cabin wall from the
x-z plane at every x of the common vector x. An aisle is the centre line of the
aisle on the floor with its width in y at each point; a space is a polygon on the
floor that has to be kept clear up to its height.

The inner surface of the cabin is the fuselage surface offset inwards by the
thickness of the lining; since every cross section of the fuselage is an ellipse
(fuselage.py), it is the ellipse with both half axes reduced by that thickness.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle

from example_xml import indent, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, axes_cross, dot, figure_style, label, save_figure
from fuselage import FUSELAGE_UID, LOFT, circle_profile_xml
from fuselageCutOut import CUTOUTS, FLOOR_Z, centre, cutout, fuselage_with_cutouts_xml

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageDecks.xml"

SEAT = COLORS["series1"]
LIGHT = COLORS["series1Light"]
FREE = COLORS["series2"]  # spaces, and the doors (cut-outs) they lead to
MONUMENT = COLORS["series3"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
DECK_UID = "mainDeck"
ORIGIN = (4.6, 0.0, FLOOR_Z)  # rear wall of the cockpit, floor height; in the fuselage coordinate system
LINING = 0.1  # thickness of the sidewall and ceiling lining, between the fuselage surface and the cabin wall

# Library of deck elements: (collection, tag, uID, name, cuboid, mass, location, extra element).
# The cuboid is (lengthX, depthY, heightZ, upperFaceYmin, upperFaceYmax) with upperFaceY None for a box; it is
# translated by -depthY/2 in y, so that the origin of the element is the centre of its front lower edge. The
# galleys and lavatories slope on their outboard side to follow the fuselage; the aft galley stands across the
# cabin and slopes on both sides. The geometry is an envelope, so the mass is given directly.
SEAT_ELEMENT = ("seatElements", "seatElement", "doubleSeat", "Double seat", (0.72, 1.02, 1.12, None, None), 22.0,
                (0.36, 0.0, 0.42), ("numberOfSeats", 2))
ELEMENTS = [
    ("galleyElements", "galleyElement", "galleyForward", "Forward galley", (0.9, 0.95, 1.8, 0.0, 0.35), 140.0,
     (0.45, -0.1, 0.8), ("numberOfTrolleys", 2)),
    ("galleyElements", "galleyElement", "galleyAft", "Aft galley", (0.8, 2.6, 1.8, 0.6, 2.0), 260.0,
     (0.4, 0.0, 0.8), ("numberOfTrolleys", 5)),
    ("lavatoryElements", "lavatoryElement", "lavatory", "Lavatory", (0.95, 1.0, 1.8, 0.6, 1.0), 110.0,
     (0.475, 0.1, 0.85), None),
    SEAT_ELEMENT,
]

# Seat rows of a 2 + 2 cabin at a pitch of 0.79 m (31 in): x of the front edge of each row in the deck coordinate
# system. The rows leave the passageway to the over-wing exits free; the first row stands behind the forward door.
PITCH = 0.79
ROWS = [round(2.18 + PITCH * k, 4) for k in range(7)] + [round(8.17 + PITCH * k, 4) for k in range(6)]
SEAT_Y = 0.77  # centre of a double seat from the x-z plane; its inner edge is 0.26 from it

# Instances: (collection, tag, uID, name, element uID, translation, rotation about z [deg]).
MONUMENTS = [
    ("galleys", "galley", "galleyForward", "Forward galley", "galleyForward", (0.05, 0.875, 0.0), 0.0),
    ("galleys", "galley", "galleyAft", "Aft galley", "galleyAft", (14.35, 0.0, 0.0), 0.0),
    ("lavatories", "lavatory", "lavatoryForward", "Forward lavatory", "lavatory", (0.05, -0.85, 0.0), 0.0),
    # the aft lavatory stands on the right side, turned about z so that its door faces the aisle as well
    ("lavatories", "lavatory", "lavatoryAft", "Aft lavatory", "lavatory", (13.95, 0.85, 0.0), 180.0),
]


def seat_instances():
    rows = []
    for number, x in enumerate(ROWS, start=1):
        for side, name, y in (("L", "left", -SEAT_Y), ("R", "right", SEAT_Y)):
            rows.append(("seatModules", "seatModule", f"row{number}{side}", f"Row {number} {name}", "doubleSeat",
                         (x, y, 0.0), 0.0))
    return rows


INSTANCES = seat_instances() + MONUMENTS

# Cabin geometry: contours at heights above the floor, sampled at a common pitch from the cockpit wall to the rear
# wall of the aft galley.
CABIN_X = [round(0.8 * k, 4) for k in range(20)]  # 0 to 15.2 m
CONTOUR_Z = [0.0, 0.5, 1.0, 1.5, 2.0]

# Aisle: centre line on the floor, wide from the cockpit past the forward galley, lavatory and door, and narrowing
# to the seat rows.
AISLE = ("aisle", "Main aisle", [0.0, 2.0, 2.18, 14.35], [0.0, 0.0, 0.0, 0.0], [0.7, 0.7, 0.5, 0.5])


def _cutout(suffix):
    return cutout(next(row for row in CUTOUTS if row[0] == suffix))


def _door_x(suffix):
    """Front and rear edge of a door in the deck coordinate system."""
    c = _cutout(suffix)
    return round(c["x"] - c["width"] / 2 - ORIGIN[0], 4), round(c["x"] + c["width"] / 2 - ORIGIN[0], 4)


def _exit_top(suffix):
    """Height of the upper edge of an over-wing exit above the floor, from its centre on the fuselage."""
    c = _cutout(suffix)
    point, _ = centre(c)
    return round(point[2] + c["height"] / 2 - ORIGIN[2], 2)


# Spaces: (uID suffix, name, cut-out, y inboard edge, y outboard edge, height). Each is the rectangle in front of a
# door, as wide as the door, from the cabin wall to the aisle; it has to be kept clear up to the given height.
SPACE_WALL = 1.39  # y of the cabin wall at the floor, rounded down
SPACES = [
    ("doorL1", "Passageway to the forward door", "paxDoorL1", -0.35, -SPACE_WALL, 1.85),
    ("exitL", "Passageway to the left over-wing exit", "emergencyExitL", -0.25, -SPACE_WALL,
     _exit_top("emergencyExitL")),
    ("exitR", "Passageway to the right over-wing exit", "emergencyExitR", 0.25, SPACE_WALL,
     _exit_top("emergencyExitR")),
    ("doorL2", "Passageway to the aft door", "paxDoorL2", -0.25, -SPACE_WALL, 1.85),
]

# Doors of the deck: (uID suffix, name, cut-out, doorType, paxCapacity). The capacity is half of the rating of a
# pair of exits of the type (Type I 45, Type III 35 passengers), since the example gives the exits of one pair
# only where the fuselage has them on both sides.
DOORS = [
    ("doorL1", "Forward door", "paxDoorL1", "boarding", 22),
    ("exitL", "Over-wing exit left", "emergencyExitL", "evacuation", 17),
    ("exitR", "Over-wing exit right", "emergencyExitR", "evacuation", 17),
    ("doorL2", "Aft door", "paxDoorL2", "boarding", 22),
]


def space_polygon(space):
    """Corner points (x, y) of a space, in the order written to the file."""
    _, _, suffix, inboard, outboard, _ = space
    x0, x1 = _door_x(suffix)
    return [(x0, outboard), (x1, outboard), (x1, inboard), (x0, inboard)]


# ------------------------------------------------------------------ geometry
def element(uid):
    return next(e for e in ELEMENTS if e[2] == uid)


def element_vertices(uid):
    """The eight corners of the envelope of an element in its coordinate system: lower face, then upper face."""
    length, depth, height, ymin, ymax = element(uid)[4]
    ymin, ymax = (0.0, depth) if ymin is None else (ymin, ymax)
    lower = [(0, 0), (length, 0), (length, depth), (0, depth)]
    upper = [(0, ymin), (length, ymin), (length, ymax), (0, ymax)]
    return np.array([(x, y - depth / 2, 0.0) for x, y in lower] + [(x, y - depth / 2, height) for x, y in upper])


def place(points, translation, rotation_z):
    a = np.radians(rotation_z)
    r = np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return points @ r.T + np.asarray(translation)


def instance_vertices(instance):
    """Corners of a component in the deck coordinate system."""
    _, _, _, _, element_uid, translation, rotation_z = instance
    return place(element_vertices(element_uid), translation, rotation_z)


def footprint(instance):
    """(xmin, xmax, ymin, ymax) of the lower face of a component in the deck coordinate system."""
    v = instance_vertices(instance)[:4]
    return v[:, 0].min(), v[:, 0].max(), v[:, 1].min(), v[:, 1].max()


def to_fuselage(points):
    return np.asarray(points) + np.asarray(ORIGIN)


def cabin_half_width(x, z):
    """Distance of the cabin wall from the x-z plane at x and at the height z above the floor, both in the deck
    coordinate system, or 0 above the ceiling."""
    width, height, zc = LOFT.station(x + ORIGIN[0])
    a, b = width / 2 - LINING, height / 2 - LINING
    q = 1.0 - ((z + ORIGIN[2] - zc) / b) ** 2
    return a * np.sqrt(q) if q > 0.0 else 0.0


def contour_y(z):
    """y of a contour at every x of the cabin geometry, rounded down to the millimetre so that it stays inside."""
    return [np.floor(cabin_half_width(x, z) * 1000.0) / 1000.0 for x in CABIN_X]


def inside_cabin(point):
    """Clearance of a point from the cabin wall in y [m], negative if it lies outside."""
    x, y, z = point
    return cabin_half_width(x, z) - abs(y)


# --------------------------------------------------------------------- figures
def _half_width(xs):
    """Half the width of the fuselage at the stations xs of the deck coordinate system."""
    return np.array([LOFT.station(v + ORIGIN[0])[0] / 2 for v in xs])


def _door_side(suffix):
    """-1 for a door on the left side, +1 on the right; a referenceAngle of 90 deg points to -y."""
    return float(np.sign(-np.sin(np.radians(_cutout(suffix)["angle"]))))


def _deck_plan(ax, xlim, ylim, lavatory):
    """Top view of the deck: fuselage, doors, spaces, aisle, galleys, lavatories and seats; lavatory is the name
    written in a lavatory, short where the scale is small."""
    xs = np.linspace(xlim[0] - 1.0, xlim[1] + 1.0, 400)
    for sign in (1, -1):
        ax.plot(xs, sign * _half_width(xs), color=MUTED, lw=LINE["reference"], zorder=1)
    # doors: the cut-outs, drawn on the fuselage outline
    for _, _, suffix, _, _ in DOORS:
        x0, x1 = _door_x(suffix)
        door = np.linspace(x0, x1, 20)
        ax.plot(door, _door_side(suffix) * _half_width(door), color=FREE, lw=3.0, solid_capstyle="butt", zorder=4)
    for space in SPACES:
        ax.add_patch(Polygon(space_polygon(space), closed=True, facecolor=to_rgba(FREE, 0.14), edgecolor=FREE,
                             lw=LINE["secondary"], joinstyle="round", zorder=2))
    # aisle: the band of its width, and its centre line through its points
    _, _, ax_x, ax_y, ax_w = AISLE
    ax_x, ax_y, ax_w = np.array(ax_x), np.array(ax_y), np.array(ax_w)
    ax.fill_between(ax_x, ax_y - ax_w / 2, ax_y + ax_w / 2, color=MUTED, alpha=0.16, lw=0, zorder=1)
    ax.plot(ax_x, ax_y, color=INK2, lw=LINE["reference"], zorder=2)
    for instance in INSTANCES:
        x0, x1, y0, y1 = footprint(instance)
        color = SEAT if instance[1] == "seatModule" else MONUMENT
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=to_rgba(color, 0.18), edgecolor=color,
                               lw=LINE["secondary"], zorder=3))
        if instance[1] != "seatModule" and xlim[0] < 0.5 * (x0 + x1) < xlim[1]:
            upright = (y1 - y0) > 1.5 * (x1 - x0)
            ax.text(0.5 * (x0 + x1), 0.5 * (y0 + y1), "galley" if instance[1] == "galley" else lavatory,
                    rotation=90 if upright else 0, ha="center", va="center", fontsize=NOTE, color=INK, zorder=6)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")


# Regions of the layout figure, in the deck coordinate system: the whole deck and the forward part in detail.
LAYOUT_WHOLE = ((-0.5, 15.5), (-1.72, 1.72))
LAYOUT_DETAIL = ((-1.45, 8.45), (-1.72, 1.72))


def figure_layout():
    """(a) The whole deck from above. (b) The forward part: deck origin, aisle and a space with its points."""
    (wx, wy), (dx, dy) = LAYOUT_WHOLE, LAYOUT_DETAIL
    width = FULL_WIDTH
    h_whole = width * (wy[1] - wy[0]) / (wx[1] - wx[0])
    h_detail = width * (dy[1] - dy[0]) / (dx[1] - dx[0])
    title, legend, gap = 0.3, 0.42, 0.12
    height = title + h_whole + gap + title + h_detail + legend
    with figure_style():
        fig = plt.figure(figsize=(width, height))
        whole = fig.add_axes((0.0, (legend + h_detail + title + gap) / height, 1.0, h_whole / height))
        part = fig.add_axes((0.0, legend / height, 1.0, h_detail / height))

        _deck_plan(whole, wx, wy, lavatory="lav")
        dot(whole, (0.0, 0.0), size=3.5)
        whole.set_title("(a) Deck seen from above", fontsize=FONT_SIZE["base"], loc="left")

        _deck_plan(part, dx, dy, lavatory="lavatory")
        part.set_title(f"(b) Forward part, up to x = {dx[1]:g} m", fontsize=FONT_SIZE["base"], loc="left")
        # the deck origin and the width of the aisle at its first point, both named in the free space in front of it
        _, _, ax_x, ax_y, ax_w = AISLE
        w = ax_w[0]
        part.plot([0.0, 0.0], [-w / 2, w / 2], color=INK2, lw=LINE["reference"], zorder=5)
        for yy in (-w / 2, w / 2):
            part.plot([-0.06, 0.06], [yy, yy], color=INK2, lw=LINE["reference"], zorder=5)
        label(part, (0.0, w / 2), f"widthY {w:g}", (-5, -2), ha="right", va="top", color=INK2)
        dot(part, (0.0, 0.0), size=4.0)
        label(part, (0.0, 0.0), "deck origin", (-5, -6), ha="right", va="top")
        for x, y in zip(ax_x[1:3], ax_y[1:3], strict=True):
            dot(part, (x, y), color=INK2, size=3.0)
        # the space at the forward door, with its corner points in the order of the file, numbered inside
        polygon = space_polygon(SPACES[0])
        centre = np.mean(polygon, axis=0)
        for number, (x, y) in enumerate(polygon, start=1):
            dot(part, (x, y), color=FREE, size=3.5)
            offset = (5 if x < centre[0] else -5, 5 if y < centre[1] else -5)
            label(part, (x, y), str(number), offset, ha="left" if offset[0] > 0 else "right",
                  va="bottom" if offset[1] > 0 else "top", color=INK2)
        axes_cross(part, (-1.3, -1.35), [(1, 0), (0, 1)], ["x", "y"], 0.4, [(6, 0), (0, 7)])

        handles = [Patch(facecolor=to_rgba(SEAT, 0.18), edgecolor=SEAT),
                   Patch(facecolor=to_rgba(MONUMENT, 0.18), edgecolor=MONUMENT),
                   Patch(facecolor=to_rgba(MUTED, 0.16), edgecolor="none"),
                   Patch(facecolor=to_rgba(FREE, 0.14), edgecolor=FREE), Line2D([], [], color=FREE, lw=3.0)]
        names = ["seat module", "galley, lavatory", "aisle", "space", "door (cut-out)"]
        fig.legend(handles, names, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.0), handlelength=1.4,
                   columnspacing=1.6)
        save_figure(fig, FIGURES / "deckLayout.png")


def figure_cabin_geometry():
    """(a) Section at a station, seen from behind: the contours at their heights and their distance y from the x-z
    plane. (b) Side view of the forward end: the contours share the vector x."""
    k_station = 9  # 7.2 m behind the cockpit wall, through a row of seats
    station = CABIN_X[k_station]
    ys = [contour_y(z)[k_station] for z in CONTOUR_Z]
    zlim = (-1.2, 2.55)
    with figure_style():
        fig, (sec, side) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.35),
                                        gridspec_kw={"width_ratios": [4.3, 5.6], "wspace": 0.02})
        width, height, zc = LOFT.station(station + ORIGIN[0])
        zc -= ORIGIN[2]
        t = np.linspace(0.0, 2.0 * np.pi, 721)
        sec.add_patch(Polygon(np.column_stack([width / 2 * np.sin(t), zc + height / 2 * np.cos(t)]),
                              closed=True, facecolor=to_rgba(MUTED, 0.06), edgecolor=MUTED, lw=LINE["reference"],
                              zorder=1))
        # seats of the row at this station, in section, as context
        for instance in INSTANCES:
            x0, x1, y0, y1 = footprint(instance)
            if instance[1] == "seatModule" and x0 <= station <= x1:
                sec.add_patch(Rectangle((y0, 0.0), y1 - y0, element(instance[4])[4][2],
                                        facecolor=to_rgba(MUTED, 0.12), edgecolor="none", zorder=1))
        # the floor, and the cabin wall above it on which the contour points lie
        floor = cabin_half_width(station, 0.0) + LINING
        sec.plot([-floor, floor], [0.0, 0.0], color=INK2, lw=LINE["reference"], zorder=2)
        zz = np.linspace(0.0, zc + height / 2 - LINING, 400)
        wall = np.array([cabin_half_width(station, z) for z in zz])
        sec.plot(np.concatenate([-wall[::-1], wall]), np.concatenate([zz[::-1], zz]), color=LIGHT,
                 lw=LINE["secondary"], zorder=2)
        for y, z in zip(ys, CONTOUR_Z, strict=True):
            for s in (-1, 1):
                dot(sec, (s * y, z), color=SEAT, size=4.5)
            label(sec, (-1.75, z), f"z = {z:g}", (0, 0), ha="right", color=INK2)
        # the x-z plane, and the distance y at two contours, measured from it
        sec.plot([0.0, 0.0], [0.0, 2.3], color=MUTED, lw=LINE["reference"], zorder=2)
        label(sec, (0.0, 2.3), "x-z plane", (0, 3), va="bottom", color=INK2)
        for k in (2, 3):
            y, z = ys[k], CONTOUR_Z[k]
            sec.annotate("", xy=(y, z), xytext=(0.0, z),
                         arrowprops={"arrowstyle": "-|>", "color": INK, "lw": LINE["secondary"], "shrinkA": 0,
                                     "shrinkB": 2.5, "mutation_scale": 8}, zorder=5)
            label(sec, (0.45 * y, z), f"y = {y:.3f}", (0, -3), va="top", color=INK2)
        axes_cross(sec, (1.45, -1.05), [(1, 0), (0, 1)], ["y", "z"], 0.35, [(6, 0), (0, 7)])
        sec.set_xlim(-2.35, 2.0)
        sec.set_ylim(*zlim)
        sec.set_aspect("equal")
        sec.axis("off")
        sec.set_title(f"(a) Section at x = {station:g} m, from behind", fontsize=FONT_SIZE["base"], loc="left")

        # (b) side view of the forward end: fuselage edges, cockpit wall, contours with the samples of x
        xs = np.linspace(-1.2, 4.4, 300)
        rows = np.array([LOFT.station(v + ORIGIN[0]) for v in xs]) - (0.0, 0.0, ORIGIN[2])
        for sign in (1, -1):
            side.plot(xs, rows[:, 2] + sign * rows[:, 1] / 2, color=MUTED, lw=LINE["reference"], zorder=1)
        side.fill_between(xs, rows[:, 2] - rows[:, 1] / 2, rows[:, 2] + rows[:, 1] / 2, color=MUTED, alpha=0.06,
                          lw=0, zorder=0)
        ceiling = CONTOUR_Z[-1] + 0.05
        side.plot([0.0, 0.0], [0.0, ceiling], color=INK2, lw=LINE["secondary"], zorder=2)
        label(side, (0.0, 0.75), "cockpit\nrear wall", (-6, 0), ha="right", color=INK2)
        shown = [x for x in CABIN_X if x <= 4.0]
        for z in CONTOUR_Z:
            side.plot([0.0, 4.4], [z, z], color=SEAT, lw=LINE["secondary"], zorder=3)
            for x in shown:
                dot(side, (x, z), color=SEAT, size=3.2)
        subscripts = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        for number, x in enumerate(shown, start=1):
            label(side, (x, 0.0), f"x{number}".translate(subscripts), (0, -6), va="top", color=INK2)
        label(side, (0.0, -0.42), f"x: {len(CABIN_X)} values from 0 to {CABIN_X[-1]:g} m,\nshared by all contours",
              (0, 0), ha="left", va="top", color=INK2)
        axes_cross(side, (3.6, -1.05), [(1, 0), (0, 1)], ["x", "z"], 0.35, [(6, 0), (0, 7)])
        side.set_xlim(-1.3, 4.45)
        side.set_ylim(*zlim)
        side.set_aspect("equal")
        side.axis("off")
        side.set_title("(b) Forward end, from the left", fontsize=FONT_SIZE["base"], loc="left")
        save_figure(fig, FIGURES / "deckCabinGeometry.png")


# --------------------------------------------------------------------- example
def _value(v):
    return f"{v:.10g}"


def _triple(tag, values):
    return "\n".join([f"<{tag}>", *(f"    <{a}>{_value(v)}</{a}>" for a, v in zip("xyz", values, strict=True)),
                      f"</{tag}>"])


def _transformation(translation, rotation_z=0.0):
    parts = ["<transformation>"]
    if rotation_z:
        parts.append(indent(f"<rotation>\n    <z>{_value(rotation_z)}</z>\n</rotation>", 1))
    parts.append(indent(_triple("translation", [round(v, 4) for v in translation]), 1))
    return "\n".join(parts + ["</transformation>"])


def collection(tag, items):
    return "\n".join([f"<{tag}>", *(indent(item, 1) for item in items), f"</{tag}>"])


def element_xml(e):
    _, tag, uid, name, (length, depth, height, ymin, ymax), mass, location, extra = e
    cuboid = [f"<lengthX>{_value(length)}</lengthX>", f"<depthY>{_value(depth)}</depthY>",
              f"<heightZ>{_value(height)}</heightZ>"]
    if ymin is not None:
        cuboid += [f"<upperFaceYmin>{_value(ymin)}</upperFaceYmin>", f"<upperFaceYmax>{_value(ymax)}</upperFaceYmax>"]
    cuboid.append(indent(f"<transformation>\n    <translation>\n        <y>{_value(-depth / 2)}</y>\n"
                         f"    </translation>\n</transformation>", 0))
    geometry = collection("geometry", [collection("cuboids", [collection("cuboid", cuboid)])])
    geometry = geometry.replace("<geometry>", '<geometry representation="envelope">', 1)
    lines = [f'<{tag} uID="{uid}">', f"    <name>{name}</name>", indent(geometry, 1), "    <mass>",
             f"        <mass>{_value(mass)}</mass>", indent(_triple("location", location), 2), "    </mass>"]
    if extra:
        lines.append(f"    <{extra[0]}>{extra[1]}</{extra[0]}>")
    return "\n".join(lines + [f"</{tag}>"])


def deck_elements_xml():
    groups = {}
    for e in ELEMENTS:
        groups.setdefault(e[0], []).append(element_xml(e))
    return "\n".join(collection(tag, items) for tag, items in sorted(groups.items()))


def instance_uid(instance):
    return f"{DECK_UID}_{instance[2]}"


def instance_xml(instance):
    _, tag, _, name, element_uid, translation, rotation_z = instance
    return "\n".join([f'<{tag} uID="{instance_uid(instance)}">', f"    <name>{name}</name>",
                      f"    <deckElementUID>{element_uid}</deckElementUID>",
                      indent(_transformation(translation, rotation_z), 1), f"</{tag}>"])


def instances_xml(collection_tag, instances=INSTANCES):
    return collection(collection_tag, [instance_xml(i) for i in instances if i[0] == collection_tag])


def cabin_geometry_xml(contours=None):
    shown = CONTOUR_Z if contours is None else [CONTOUR_Z[k] for k in contours]
    items = [collection("contour", [f"<y>{vector(contour_y(z))}</y>", f"<z>{_value(z)}</z>"]) for z in shown]
    body = collection("contours", items)
    if contours is not None:
        body = body.replace("</contours>", "    ...\n</contours>")
    return collection("cabinGeometry", ["<name>Cabin</name>", body, f"<x>{vector(CABIN_X)}</x>"])


def aisle_xml():
    uid, name, xs, ys, ws = AISLE
    return collection("aisles", ["\n".join([
        f'<aisle uID="{DECK_UID}_{uid}">', f"    <name>{name}</name>", f"    <x>{vector(xs)}</x>",
        f"    <y>{vector(ys)}</y>", f"    <widthY>{vector(ws)}</widthY>", "</aisle>"])])


def space_xml(space):
    suffix, name, _, _, _, height = space
    points = space_polygon(space)
    return "\n".join([
        f'<space uID="{DECK_UID}_{suffix}Passage">', f"    <name>{name}</name>",
        f"    <x>{vector(p[0] for p in points)}</x>", f"    <y>{vector(p[1] for p in points)}</y>",
        f"    <height>{_value(height)}</height>", "</space>"])


def door_xml(door):
    suffix, name, cut, kind, capacity = door
    return "\n".join([
        f'<deckDoor uID="{DECK_UID}_{suffix}">', f"    <name>{name}</name>", f"    <paxCapacity>{capacity}</paxCapacity>",
        "    <opening>", f"        <cutOutUID>{FUSELAGE_UID}_{cut}</cutOutUID>", "    </opening>",
        f"    <doorType>{kind}</doorType>", "</deckDoor>"])


def deck_xml():
    return "\n".join([
        f'<deck uID="{DECK_UID}">', "    <name>Main deck</name>",
        "    <description>Passenger cabin of 52 seats, 2 + 2 abreast</description>",
        indent(_transformation(ORIGIN), 1),
        "    <deckType>passenger</deckType>",
        indent(cabin_geometry_xml(), 1),
        indent(instances_xml("seatModules"), 1),
        indent(aisle_xml(), 1),
        indent(collection("spaces", [space_xml(s) for s in SPACES]), 1),
        indent(instances_xml("galleys"), 1),
        indent(instances_xml("lavatories"), 1),
        indent(collection("deckDoors", [door_xml(d) for d in DOORS]), 1),
        "</deck>",
    ])


def fuselage_with_decks_xml():
    body = fuselage_with_cutouts_xml()
    assert body.endswith("\n</fuselage>")
    return body[: -len("</fuselage>")] + indent(collection("decks", [deck_xml()]), 1) + "\n</fuselage>"


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Fuselage decks",
        description="Passenger cabin of a short-range airliner: seats, galleys, lavatories, aisle, spaces and doors.",
        model_uid="FuselageDecksAircraft",
        model_name="Fuselage decks example",
        components_tag="fuselages",
        components=fuselage_with_decks_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_vehicles=[("deckElements", deck_elements_xml())],
    )


def excerpt_deck_xml():
    return "\n".join([
        "<decks>", f'    <deck uID="{DECK_UID}">', "        <name>Main deck</name>",
        indent(_transformation(ORIGIN), 2), "        <deckType>passenger</deckType>",
        "        <cabinGeometry>", "            ...", "        </cabinGeometry>",
        "        <seatModules>", "            ...", "        </seatModules>",
        "        ...", "    </deck>", "</decks>",
    ])


def excerpt_components_xml():
    return instances_xml("lavatories")


def excerpt_seat_xml():
    return collection("seatElements", [element_xml(SEAT_ELEMENT)])


# --------------------------------------------------------------------- checks
def _overlap(a, b, tol=1e-9):
    return a[0] < b[1] - tol and b[0] < a[1] - tol and a[2] < b[3] - tol and b[2] < a[3] - tol


def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    worst = min((inside_cabin(p), i[2]) for i in INSTANCES for p in instance_vertices(i))
    assert worst[0] > 0.0, f"{worst[1]} leaves the cabin"
    print(f"All {len(INSTANCES)} components inside the cabin; smallest clearance {worst[0] * 1000:.0f} mm "
          f"({worst[1]})")
    boxes = [(i[2], footprint(i)) for i in INSTANCES]
    for k, (a, fa) in enumerate(boxes):
        for b, fb in boxes[k + 1:]:
            assert not _overlap(fa, fb), (a, b)
    # the aisle is clear of the components; its width is interpolated linearly between its points
    _, _, ax_x, ax_y, ax_w = AISLE
    for name, (x0, x1, y0, y1) in boxes:
        for x in np.linspace(max(x0, ax_x[0]), min(x1, ax_x[-1]), 50):
            if x0 >= ax_x[-1] or x1 <= ax_x[0]:
                break
            half = np.interp(x, ax_x, ax_w) / 2
            centre = np.interp(x, ax_x, ax_y)
            assert y0 >= centre + half - 1e-9 or y1 <= centre - half + 1e-9, (name, x)
    for space in SPACES:
        points = np.array(space_polygon(space))
        box = (points[:, 0].min(), points[:, 0].max(), points[:, 1].min(), points[:, 1].max())
        for name, fb in boxes:
            assert not _overlap(box, fb), (space[0], name)
        c = _cutout(space[2])
        assert abs(box[0] + ORIGIN[0] - (c["x"] - c["width"] / 2)) < 1e-9
        gap = inside_cabin((box[0], box[2] if box[2] < 0 else box[3], 0.0))
        print(f"space {space[0]:7s} x {box[0]:.3f}..{box[1]:.3f}, y {box[2]:+.2f}..{box[3]:+.2f}, height {space[5]:g} m,"
              f" {gap * 1000:.0f} mm from the cabin wall at the floor")
    print(f"Seats {2 * sum(1 for i in INSTANCES if i[1] == 'seatModule')}, exit capacity "
          f"{sum(d[4] for d in DOORS)}")
    masses = {e[2]: e[5] for e in ELEMENTS}
    total = sum(masses[i[4]] for i in INSTANCES)
    print(f"Total mass of the components {total:g} kg")
    rows = np.array(ROWS)
    print(f"Rows at x = {rows[0]:g} to {rows[-1]:g} m; gap at the over-wing exits "
          f"{rows[7] - (rows[6] + element('doubleSeat')[4][0]):.3f} m, exit width {_cutout('emergencyExitL')['width']:g} m")


def expected():
    """Expected corners and masses of all components in the fuselage coordinate system, for the check with TiGL."""
    masses = {e[2]: e[5] for e in ELEMENTS}
    return {instance_uid(i): {"corners": to_fuselage(instance_vertices(i)).tolist(), "mass": masses[i[4]]}
            for i in INSTANCES}


def main():
    figure_layout()
    figure_cabin_geometry()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in [
        ("decksDeckType", excerpt_deck_xml()),
        ("deckComponentBaseType", excerpt_components_xml()),
        ("seatElementType", excerpt_seat_xml()),
        ("cabinGeometryType", cabin_geometry_xml(contours=[0, 1])),
        ("cabinAisleType", aisle_xml()),
        ("cabinSpaceType", collection("spaces", [space_xml(SPACES[0])]).replace("</spaces>", "    ...\n</spaces>")),
        ("deckDoorType", collection("deckDoors", [door_xml(DOORS[0])]).replace("</deckDoors>", "    ...\n</deckDoors>")),
    ]:
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

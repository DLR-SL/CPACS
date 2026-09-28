# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the fuselage geometry
(fuselageType, fuselageSectionType, fuselageElementType, fuselageSegmentType).
The fuselage of the example is the one the other examples attach their wings,
tanks and systems to; wing.py and fuelTank.py import it from here.

Run from the repository root:

    uv run documentation/scripts/fuselage.py

The script writes

    documentation/figures/fuselageParts.png
    documentation/figures/fuselageGeometry.png
    documentation/figures/fuselageProfileTransformation.png
    documentation/figures/fuselageLoftPitch.png
    examples/fuselageGeometry.xml

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: how far the surface leaves the constant
cross section between the sections, the length and the volume. The schema
documentation is not written by this script; copy the printed excerpts there when
the example changes.

Definition shown (as in the documentation): a point p of a profile is placed in the
fuselage coordinate system at
    P = t_positioning + T_section T_element p,
as for a wing (wing.py). The fuselage profile lies in the y-z plane; the example
places its sections along the x-axis with the translation of the section, scales the
circle of diameter 1 with the element to width (y) and height (z) and moves it up or
down with the translation of the element in z.

The surface between the profiles is one loft through all of them, continuous in
curvature across the sections. The script computes it the way a lofting algorithm
does, so that the figures show the shape the data describes: each profile is the
circle, scaled and translated, so a point of the surface is the circle scaled by the
width and height and moved by the position that a cubic spline through the values of
the sections gives at the loft parameter. The parameters of the sections follow the
centripetal rule, averaged over the points of the profiles, and the knots are the
averages of the parameters. At the sections, the surface passes through the profiles;
between them, its shape also depends on the neighbouring sections.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from example_xml import indent, transformation_xml, write_cpacs_file
from figure_style import (COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, axes_cross, dot, figure_style, label, leader,
                          save_figure)

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageGeometry.xml"

PROFILE = COLORS["series1"]
LIGHT = COLORS["series1Light"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
FUSELAGE_UID = "Fuselage"
FUSELAGE_PROFILE_UID = "Circle"
DIAMETER = 3.2  # of the cylindrical part

# Sections of a short-range airliner fuselage, 28 m long: (uID suffix, x, width, height, z of the centre).
# Each section holds one element with the circle of diameter 1, scaled to width (y) and height (z) and
# translated in z. The nose is pointed and lies below the axis, the cylindrical part has sections at a pitch
# of 2 m, and the tail sweeps upwards to a small end profile, the exhaust of the auxiliary power unit.
SECTIONS = [
    ("nose", 0.0, 0.0, 0.0, -0.35),
    ("nose1", 1.0, 1.7, 1.6, -0.3),
    ("nose2", 2.2, 2.6, 2.6, -0.15),
    ("nose3", 3.6, 3.1, 3.1, -0.03),
    *((f"cabin{i}", 5.0 + 2.0 * i, DIAMETER, DIAMETER, 0.0) for i in range(8)),
    ("tail1", 21.5, 2.9, 2.75, 0.175),
    ("tail2", 24.0, 2.0, 1.75, 0.525),
    ("tail3", 26.3, 1.0, 0.95, 0.825),
    ("tail", 28.0, 0.4, 0.4, 1.0),
]
CYLINDER = (SECTIONS[4][1], SECTIONS[11][1])  # first and last section of constant cross section


# ------------------------------------------------------------------ loft model
def _circle(n=64):
    """Points of the circle of diameter 1 in the y-z plane, starting at the top."""
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.column_stack([0.5 * np.sin(t), 0.5 * np.cos(t)])


def _profile_points(section, circle):
    _, x, width, height, zc = section
    return np.column_stack([np.full(len(circle), x), width * circle[:, 0], zc + height * circle[:, 1]])


def loft_parameters(sections):
    """Parameters of the sections along the loft, centripetal and averaged over the points of the profiles."""
    circle = _circle()
    points = np.array([_profile_points(s, circle) for s in sections])  # section, point, xyz
    steps = np.sqrt(np.linalg.norm(np.diff(points, axis=0), axis=2))  # section step, point
    params = np.vstack([np.zeros(steps.shape[1]), np.cumsum(steps, axis=0)])
    return (params / params[-1]).mean(axis=1)


def _basis(knots, degree, t):
    """B-spline basis functions of the given degree at the parameters t (Cox-de Boor), shape (len(t), n)."""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    n = len(knots) - degree - 1
    last = np.searchsorted(knots, knots[-1]) - 1  # last non-empty interval, which includes its end
    b = np.zeros((len(t), len(knots) - 1))
    for i in range(len(knots) - 1):
        inside = (knots[i] <= t) & (t < knots[i + 1])
        if i == last:
            inside |= t == knots[-1]
        b[:, i] = inside
    for p in range(1, degree + 1):
        nxt = np.zeros((len(t), len(knots) - 1 - p))
        for i in range(len(knots) - 1 - p):
            left = knots[i + p] - knots[i]
            right = knots[i + p + 1] - knots[i + 1]
            if left > 0.0:
                nxt[:, i] += (t - knots[i]) / left * b[:, i]
            if right > 0.0:
                nxt[:, i] += (knots[i + p + 1] - t) / right * b[:, i + 1]
        b = nxt
    return b[:, :n]


def interpolation(params, values, max_degree=3):
    """Spline through values at params: clamped knots, inner knots averaged from the parameters."""
    degree = min(max_degree, len(params) - 1)
    inner = [np.mean(params[j:j + degree]) for j in range(1, len(params) - degree)]
    knots = np.concatenate([np.full(degree + 1, params[0]), inner, np.full(degree + 1, params[-1])])
    poles = np.linalg.solve(_basis(knots, degree, params), np.asarray(values, dtype=float))
    return lambda t: _basis(knots, degree, t) @ poles


class Loft:
    """Surface lofted through the profiles of the sections; each cross section is the circle, scaled and moved."""

    def __init__(self, sections):
        self.sections = sections
        self.params = loft_parameters(sections)
        self._spline = interpolation(self.params, [s[1:] for s in sections])  # x, width, height, z of the centre

    def at(self, t):
        """(x, width, height, z of the centre) at the loft parameters t, one row each."""
        return self._spline(t)

    def sample(self, n=4001):
        return self.at(np.linspace(0.0, 1.0, n))

    def station(self, x):
        """(width, height, z of the centre) at the station x."""
        rows = self.sample()
        return np.array([np.interp(x, rows[:, 0], rows[:, k]) for k in (1, 2, 3)]).T

    def volume(self, n=20001):
        rows = self.at(np.linspace(0.0, 1.0, n))
        area = np.pi / 4.0 * rows[:, 1] * rows[:, 2]
        return float(np.sum(0.5 * (area[1:] + area[:-1]) * np.diff(rows[:, 0])))


LOFT = Loft(SECTIONS)


def cylinder_deviation(loft=LOFT, stations=CYLINDER):
    """Largest deviation of the width and the height from the diameter between the given stations [m]."""
    rows = loft.sample()
    rows = rows[(rows[:, 0] >= stations[0]) & (rows[:, 0] <= stations[1])]
    return float(np.max(np.abs(rows[:, 1:3] - DIAMETER))), float(np.max(np.abs(rows[:, 3])))


# Illustration of the loft between sections, not part of the example file: a simple fuselage with sections only
# at the ends of its cylindrical part, and the same fuselage with further sections at a pitch of 2 m in between.
# (uID suffix, x, width, height, z of the centre) as in SECTIONS.
PITCH_SPARSE = [("nose", 0.0, 0.8, 0.8, 0.0), ("front", 6.0, 3.2, 3.2, 0.0), ("rear", 20.0, 3.2, 3.2, 0.0),
                ("tail", 28.0, 1.0, 1.0, 0.0)]
PITCH_DENSE = [PITCH_SPARSE[0], *((f"cabin{i}", 6.0 + 2.0 * i, 3.2, 3.2, 0.0) for i in range(8)), PITCH_SPARSE[-1]]


# --------------------------------------------------------------------- figures
def _ellipse(width, height, zc, n=181):
    """Profile of an element in the y-z plane: the circle of diameter 1 scaled to width and height, moved to zc."""
    t = np.linspace(0.0, 2.0 * np.pi, n)
    return np.column_stack([0.5 * width * np.sin(t), zc + 0.5 * height * np.cos(t)])


def _section_profile(section, n=181):
    _, x, width, height, zc = section
    yz = _ellipse(width, height, zc, n)
    return np.column_stack([np.full(len(yz), x), yz])


def _surface_lines(angles, loft=LOFT):
    """Lines along the surface at fixed angles of the profile [deg], 0 at the top and 90 at the side y > 0."""
    rows = loft.sample()
    return [np.column_stack([rows[:, 0], 0.5 * rows[:, 1] * np.sin(a), rows[:, 3] + 0.5 * rows[:, 2] * np.cos(a)])
            for a in np.radians(angles)]


def _closed(ax, points, color, lw, zorder):
    """A closed curve drawn as one closed path, so that its start and end do not show as a seam."""
    ax.add_patch(Polygon(points, closed=True, fill=False, edgecolor=color, lw=lw, joinstyle="round", zorder=zorder))


def _envelope(project, loft=LOFT, bins=1400, span=None):
    """Upper and lower outline of the surface in a projection, from dense cross sections, optionally only of the
    segment between the two sections span = (first, second), which it closes exactly with their profiles."""
    rows = loft.sample(3001)
    if span:
        first, second = span
        inside = rows[(rows[:, 0] > first[1]) & (rows[:, 0] < second[1])]
        rows = np.vstack([first[1:], inside, second[1:]])
    t = np.linspace(0.0, 2.0 * np.pi, 241)
    points = np.concatenate([
        project(np.column_stack([np.full(len(t), x), 0.5 * w * np.sin(t), zc + 0.5 * h * np.cos(t)]))
        for x, w, h, zc in rows])
    edges = np.linspace(points[:, 0].min(), points[:, 0].max(), bins + 1)
    index = np.clip(np.digitize(points[:, 0], edges) - 1, 0, bins - 1)
    upper, lower = np.full(bins, -np.inf), np.full(bins, np.inf)
    np.maximum.at(upper, index, points[:, 1])
    np.minimum.at(lower, index, points[:, 1])
    x = 0.5 * (edges[1:] + edges[:-1])
    keep = np.isfinite(upper)
    # the outline reaches the first and the last projected point exactly, so that the ends are not cut off (§21)
    first, last = points[np.argmin(points[:, 0])], points[np.argmax(points[:, 0])]
    upper_line = np.vstack([first, np.column_stack([x[keep], upper[keep]]), last])
    lower_line = np.vstack([first, np.column_stack([x[keep], lower[keep]]), last])
    return upper_line, lower_line


def _callout(ax, xy, text, offset, ha="center", va="center"):
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=INK,
                zorder=7, arrowprops=leader())


def _legend(fig, last, anchor):
    """Legend of the profiles and the section origins, and of the area of the surface if last names it."""
    handles = [Line2D([], [], color=PROFILE, lw=LINE["secondary"]),
               Line2D([], [], ls="none", marker="o", ms=3.5, color=INK, mec=COLORS["surface"]),
               Line2D([], [], color=PROFILE, lw=6, alpha=0.15)]
    names = ["profile of an element", "origin of a section", last]
    count = 3 if last else 2
    fig.legend(handles[:count], names[:count], loc="lower center", ncol=count, bbox_to_anchor=anchor,
               handlelength=1.4, columnspacing=1.6)


def figure_parts():
    """Oblique view of the example fuselage with its sections, elements and segments."""

    def project(p):  # oblique view: x to the right, z up, y running up to the right into the depth
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 0] + 0.4 * p[..., 1], p[..., 2] + 0.25 * p[..., 1]]).T

    sections = {s[0]: s for s in SECTIONS}
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.6))
        # the surface as a wash within its outline, and one segment highlighted: the surface between the profiles of
        # two neighbouring sections
        upper, lower = _envelope(project)
        ax.add_patch(Polygon(np.vstack([upper, lower[::-1]]), closed=True, facecolor=PROFILE, alpha=0.08,
                             edgecolor="none", zorder=0))
        for edge in (upper, lower):
            ax.plot(*edge.T, color=MUTED, lw=LINE["reference"], zorder=1)
        first, second = sections["cabin3"], sections["cabin4"]
        top, bottom = _envelope(project, span=(first, second))
        ax.add_patch(Polygon(np.vstack([top, bottom[::-1]]), closed=True, facecolor=PROFILE, alpha=0.16,
                             edgecolor="none", zorder=0))
        for section in SECTIONS[1:]:  # the profile of the nose is a point
            _closed(ax, project(_section_profile(section)), PROFILE, LINE["secondary"], 3)
        for section in SECTIONS:
            dot(ax, project((section[1], 0.0, 0.0)), size=3.5)

        # coordinate system of a tail section, named at the tip of its z-axis
        _, x, width, height, zc = sections["tail2"]
        origin = np.array([x, 0.0, 0.0])
        for direction, name, offset in (((1.0, 0, 0), "x", (0, -7)), ((0, 2.4, 0), "y", (6, 2)),
                                        ((0, 0, 2.3), "z", (-6, 0))):
            tip = project(origin + np.array(direction, dtype=float))
            arrow(ax, project(origin), tip, color=INK, lw=LINE["secondary"], head=6)
            label(ax, tip, name, offset, color=INK2)
        label(ax, project(origin + (0.0, 0.0, 2.3)), "coordinate system\nof a tail section", (8, 0), ha="left")

        # notes below and above the fuselage, each with a vertical leader through free space
        def note(xy, text, height, ha="center"):
            above = height > xy[1]  # the leader leaves the text at its edge next to the point, not at its centre
            ax.annotate(text, xy=xy, xytext=(xy[0], height), textcoords="data", ha=ha, va="bottom" if above else "top",
                        fontsize=NOTE, color=INK, zorder=7,
                        arrowprops={**leader(), "relpos": (0.0 if ha == "left" else 0.5, 0.0 if above else 1.0)})

        note(project((0.0, 0.0, 0.0)), "origin of the fuselage and of the nose section,\n"
             "whose element is scaled to a point", 3.0, ha="left")
        middle = project((0.5 * (first[1] + second[1]), 0.0, 0.0))[0]
        note((middle, np.interp(middle, *bottom.T)), "segment", -3.0)
        element = project(_section_profile(sections["tail2"]))
        lowest = element[np.argmin(element[:, 1])]
        note(lowest, "element: the circle, scaled to width\nand height and moved upwards", -3.0)
        ax.set_xlim(-0.5, 30.0)
        ax.set_ylim(-4.1, 4.0)
        ax.set_aspect("equal")
        ax.axis("off")
        _legend(fig, None, (0.5, -0.02))
        save_figure(fig, FIGURES / "fuselageParts.png")


def figure_geometry():
    """Side and top view of the example fuselage: sections, the translation of the elements and the contour."""
    rows = LOFT.sample()
    with figure_style():
        fig, (side, top) = plt.subplots(2, 1, figsize=(FULL_WIDTH, 4.1), gridspec_kw={"hspace": 0.12,
                                                                                         "height_ratios": [1.3, 1.0]})
        # (axis, column of the centre or None, column of the size, name of the vertical axis, title, y-limits)
        views = ((side, 3, 2, "z", "(a) Side view", (-3.5, 3.4)), (top, None, 1, "y", "(b) Top view", (-2.4, 2.9)))
        for ax, centre_column, size_column, axis_name, title, limits in views:
            centre = rows[:, centre_column] if centre_column else np.zeros(len(rows))
            upper, lower = centre + 0.5 * rows[:, size_column], centre - 0.5 * rows[:, size_column]
            ax.fill_between(rows[:, 0], lower, upper, color=PROFILE, alpha=0.08, lw=0, zorder=0)
            for edge in (upper, lower):
                ax.plot(rows[:, 0], edge, color=MUTED, lw=LINE["reference"], zorder=1)
            ax.plot([0.0, SECTIONS[-1][1]], [0.0, 0.0], color=INK2, lw=LINE["reference"], zorder=2)
            for _, x, width, height, zc in SECTIONS:
                c = zc if centre_column else 0.0
                half = 0.5 * (height if centre_column else width)
                ax.plot([x, x], [c - half, c + half], color=PROFILE, lw=LINE["secondary"], zorder=3)
                dot(ax, (x, 0.0), size=3.5)
            ax.set_xlim(-0.8, 33.0)
            ax.set_ylim(*limits)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(title)
            axes_cross(ax, (30.5, limits[0]),[(1, 0), (0, 1)], ["x", axis_name], 0.9, [(6, 0), (0, 7)])

        # side view: the constant cross section, and the translation of the elements in z at the nose and the tail
        x0, x1 = CYLINDER
        y = DIAMETER / 2 + 0.5
        side.plot([x0, x1], [y, y], color=MUTED, lw=LINE["reference"])
        for x in (x0, x1):
            side.plot([x, x], [y - 0.12, y + 0.12], color=MUTED, lw=LINE["reference"])
        label(side, (0.5 * (x0 + x1), y), f"constant cross section: sections at a pitch of "
              f"{SECTIONS[5][1] - SECTIONS[4][1]:g} m, diameter {DIAMETER:g} m", (0, 4), va="bottom", color=INK2)
        # the translation of the tail element as a dimension beside the tail, so that it does not lie on the profile
        _, x, _, _, zc = SECTIONS[-1]
        for z in (0.0, zc):
            side.plot([x + 0.25, x + 0.95], [z, z], color=MUTED, lw=LINE["reference"])
        side.plot([x + 0.75, x + 0.75], [0.0, zc], color=MUTED, lw=LINE["reference"])
        label(side, (x + 0.95, 0.5 * zc), f"tail: element\ntranslated by {zc:g} in z", (5, 0), ha="left", color=INK2)
        # the nose, with a vertical leader from its point down past the fuselage
        _, x, _, _, zc = SECTIONS[0]
        side.annotate(f"nose: element scaled to a point\nand translated by {zc:g} in z", xy=(x, zc),
                      xytext=(x, -2.0), textcoords="data", ha="left", va="top", fontsize=NOTE, color=INK2,
                      zorder=7, arrowprops={**leader(), "relpos": (0.0, 1.0)})
        _legend(fig, "surface", (0.5, -0.02))
        save_figure(fig, FIGURES / "fuselageGeometry.png")


def figure_profile_transformation():
    """The circle of diameter 1, scaled by the element to width and height, then translated in z."""
    _, _, width, height, zc = next(s for s in SECTIONS if s[0] == "tail2")
    circle = _ellipse(1.0, 1.0, 0.0)
    scaled = _ellipse(width, height, 0.0)
    moved = _ellipse(width, height, zc)
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.5), gridspec_kw={"wspace": 0.08})
        steps = [("(a) Profile", [(circle, PROFILE)]),
                 ("(b) Element: scaling", [(circle, LIGHT), (scaled, PROFILE)]),
                 ("(c) Element: translation", [(scaled, LIGHT), (moved, PROFILE)])]
        for ax, (title, curves) in zip(axes, steps, strict=True):
            for points, color in curves:
                final = color == PROFILE
                _closed(ax, points, color, LINE["data"] if final else LINE["secondary"], 3 if final else 2)
            axes_cross(ax, (0.0, 0.0), [(1, 0), (0, 1)], ["y", "z"], 0.25, [(6, 0), (0, 7)])
            dot(ax, (0.0, 0.0), size=3.5)
            ax.set_xlim(-1.35, 1.35)
            ax.set_ylim(-1.3, 1.55)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(title, fontsize=FONT_SIZE["base"])

        def dimension(ax, start, end, text, offset, ha="center", va="center"):
            start, end = np.asarray(start), np.asarray(end)
            normal = np.array([end[1] - start[1], start[0] - end[0]])
            normal = 0.06 * normal / np.linalg.norm(normal)
            ax.plot(*np.array([start, end]).T, color=MUTED, lw=LINE["reference"])
            for point in (start, end):
                ax.plot(*np.array([point - normal, point + normal]).T, color=MUTED, lw=LINE["reference"])
            label(ax, 0.5 * (start + end), text, offset, ha=ha, va=va, color=INK2)

        dimension(axes[0], (-0.5, -0.7), (0.5, -0.7), "diameter 1", (0, -4), va="top")
        dimension(axes[1], (-0.5 * width, -0.5 * height - 0.2), (0.5 * width, -0.5 * height - 0.2),
                  f"width {width:g}: scaling in y", (0, -4), va="top")
        dimension(axes[1], (-0.5 * width - 0.15, -0.5 * height), (-0.5 * width - 0.15, 0.5 * height),
                  f"height {height:g}:\nscaling in z", (-4, 0), ha="right")
        # translation, drawn at the lowest point of the profile so that it does not lie on the z-axis
        arrow(axes[2], (0.0, -0.5 * height), (0.0, zc - 0.5 * height), color=INK, lw=LINE["secondary"], head=6)
        label(axes[2], (0.0, -0.5 * height), f"translation {zc:g} in z", (0, -4), va="top", color=INK2)
        save_figure(fig, FIGURES / "fuselageProfileTransformation.png")


def figure_loft_pitch():
    """Upper edge of a simple fuselage with sections only at the ends of its cylindrical part and at a close pitch."""
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.6))
        radius = PITCH_SPARSE[1][3] / 2
        cases = ((PITCH_SPARSE, MUTED, "sections at the ends of the cylindrical part only"),
                 (PITCH_DENSE, PROFILE, "further sections at a pitch of 2 m"))
        for sections, color, _ in cases:
            rows = Loft(sections).sample()
            ax.plot(rows[:, 0], rows[:, 3] + 0.5 * rows[:, 2], color=color, zorder=3 if color == PROFILE else 2)
            ax.plot([s[1] for s in sections], [s[4] + 0.5 * s[3] for s in sections], ls="none", marker="o", ms=4,
                    color=color, mec=COLORS["surface"], mew=1.0, zorder=4)
        rows = Loft(PITCH_SPARSE).sample()
        peak = np.argmax(rows[:, 3] + 0.5 * rows[:, 2])
        x, top = rows[peak, 0], rows[peak, 3] + 0.5 * rows[peak, 2]
        label(ax, (x, top), f"{cases[0][2]}: {top - radius:.2f} m above the radius", (0, 8), va="bottom")
        # how far the surface bulges out, as a dimension between the two curves instead of a line at the radius,
        # which would lie on the curve with further sections; the leader below is set apart from it
        ax.plot([x, x], [radius, top], color=MUTED, lw=LINE["reference"], zorder=2)
        _callout(ax, (15.0, radius), cases[1][2], (0, -22), va="top")
        ax.set_xlim(-0.5, 28.5)
        ax.set_ylim(0.0, 2.15)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("upper edge z [m]")
        save_figure(fig, FIGURES / "fuselageLoftPitch.png")


# --------------------------------------------------------------------- example
def element_xml(section):
    name, _, width, height, zc = section
    return "\n".join([
        f'<element uID="{FUSELAGE_UID}_{name}_element">', f"    <name>{_title(name)} element</name>",
        f"    <profileUID>{FUSELAGE_PROFILE_UID}</profileUID>",
        indent(transformation_xml(scaling=(1.0, width, height), translation=(0.0, 0.0, zc)), 1), "</element>",
    ])


def _title(name):
    stem = name.rstrip("0123456789")
    number = name[len(stem):]
    return stem.capitalize() + (f" {number}" if number else "")


def section_xml(section):
    name, x = section[0], section[1]
    return "\n".join([
        f'<section uID="{FUSELAGE_UID}_{name}">', f"    <name>{_title(name)} section</name>",
        indent(transformation_xml(translation=(x, 0.0, 0.0)), 1),
        "    <elements>", indent(element_xml(section), 2), "    </elements>", "</section>",
    ])


def segment_xml(index):
    inner, outer = SECTIONS[index][0], SECTIONS[index + 1][0]
    return "\n".join([
        f'<segment uID="{FUSELAGE_UID}_segment{index + 1}">', f"    <name>Segment {index + 1}</name>",
        f"    <fromElementUID>{FUSELAGE_UID}_{inner}_element</fromElementUID>",
        f"    <toElementUID>{FUSELAGE_UID}_{outer}_element</toElementUID>", "</segment>",
    ])


def collection(tag, items):
    return "\n".join([f"<{tag}>", *(indent(item, 1) for item in items), f"</{tag}>"])


def segments_xml(indices=None):
    return collection("segments", [segment_xml(i) for i in (indices or range(len(SECTIONS) - 1))])


def fuselage_xml():
    """The fuselage of the examples, with its sections and segments."""
    return "\n".join([
        f'<fuselage uID="{FUSELAGE_UID}">', "    <name>Fuselage</name>",
        "    <description>Fuselage of a short-range airliner with a pointed nose and an upswept tail</description>",
        indent(transformation_xml(), 1),
        indent(collection("sections", [section_xml(s) for s in SECTIONS]), 1),
        indent(segments_xml(), 1),
        "</fuselage>",
    ])


def circle_profile_xml():
    return "\n".join([
        f'<fuselageProfile uID="{FUSELAGE_PROFILE_UID}">', "    <name>Circle</name>", "    <standardProfile>",
        "        <superEllipse>", "            <mUpper>2</mUpper>", "            <nUpper>2</nUpper>",
        "            <mLower>2</mLower>", "            <nLower>2</nLower>",
        "            <lowerHeightFraction>0.5</lowerHeightFraction>", "        </superEllipse>",
        "    </standardProfile>", "</fuselageProfile>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Fuselage geometry",
        description="A fuselage built from sections, elements and segments, with a pointed nose and an upswept tail.",
        model_uid="FuselageGeometryAircraft",
        model_name="Fuselage geometry example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
    )


def excerpt_fuselage_xml():
    return "\n".join([
        f'<fuselage uID="{FUSELAGE_UID}">', "    <name>Fuselage</name>",
        *indent(transformation_xml(), 1).splitlines(),
        "    <sections>",
        f'        <section uID="{FUSELAGE_UID}_{SECTIONS[0][0]}">', "            ...", "        </section>",
        "        ...",
        "    </sections>",
        "    <segments>", "        ...", "    </segments>",
        "</fuselage>",
    ])


EXCERPT_SECTION = next(s for s in SECTIONS if s[0] == "tail2")


def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    size, centre = cylinder_deviation()
    print(f"Loft between x = {CYLINDER[0]:g} m and x = {CYLINDER[1]:g} m: width and height deviate from the "
          f"diameter {DIAMETER:g} m by at most {size * 1000:.1f} mm ({size / DIAMETER * 100:.2f} %), "
          f"the centre from the axis by at most {centre * 1000:.1f} mm")
    print(f"Length {SECTIONS[-1][1] - SECTIONS[0][1]:g} m, volume {LOFT.volume():.3f} m^3")
    for name, sections in (("sparse", PITCH_SPARSE), ("dense", PITCH_DENSE)):
        size, _ = cylinder_deviation(Loft(sections), (PITCH_SPARSE[1][1], PITCH_SPARSE[2][1]))
        print(f"Illustration {name}: diameter deviates by at most {size:.3f} m between the ends of the cylinder")


def main():
    figure_parts()
    figure_geometry()
    figure_profile_transformation()
    figure_loft_pitch()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in [
        ("fuselageType", excerpt_fuselage_xml()),
        ("fuselageSectionType", section_xml(EXCERPT_SECTION)),
        ("fuselageElementType", collection("elements", [element_xml(EXCERPT_SECTION)])),
        ("fuselageSegmentType", segments_xml([0, 1]).replace("</segments>", "    ...\n</segments>")),
    ]:
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

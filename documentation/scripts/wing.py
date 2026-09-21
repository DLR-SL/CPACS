# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of the wing geometry
(wingType, wingSectionType, wingElementType, positioningType, wingSegmentType).
The component segment of the example wing is defined here as well; its figures
and equations are written by componentSegment.py.

Run from the repository root:

    uv run documentation/scripts/wing.py

The script writes

    documentation/figures/wingParts.png
    documentation/figures/wingSplitWingtip.png
    documentation/figures/wingGeometry.png
    documentation/figures/wingProfileTransformation.png
    documentation/figures/wingElementCoordinates.png
    documentation/figures/positioningVector.png
    documentation/equations/wingProfilePoint.{tex,png}
    documentation/equations/positioningVector.{tex,png}
    examples/wingGeometry.xml

and prints the excerpts shown in the documentation. The schema documentation is
not written by this script; copy the printed excerpts there when the example changes.

Definition shown (as in the documentation): a point p of an airfoil is placed in the
wing coordinate system at
    P = t_positioning + T_section T_element p,
where T_section and T_element are the transformations (scaling, then rotation about
z, y and x, then translation) and t_positioning is the end point of the positioning
chain of the section. A positioning vector is
    v = L (sin(sweep), cos(sweep) cos(dihedral), cos(sweep) sin(dihedral)),
i.e. the y-axis rotated by -sweep about z, then by dihedral about x.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Polygon

from example_xml import indent, transformation_xml, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_equation, save_figure
from nacaProfile import naca4

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "wingGeometry.xml"

PROFILE = COLORS["series1"]
POSITIONING = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
WING_UID = "Wing"
WING_TRANSLATION = (10.0, 0.0, -0.5)  # relative to the fuselage, the parent of the wing
AIRFOIL_UID = "NACA2412"

# Fuselage the wing is attached to (parentUID): (uID suffix, x, diameter) of its circular sections
FUSELAGE_UID = "Fuselage"
FUSELAGE_PROFILE_UID = "Circle"
FUSELAGE_SECTIONS = [("nose", 0.0, 0.8), ("front", 6.0, 3.2), ("rear", 20.0, 3.2), ("tail", 28.0, 1.0)]

# Sections: (uID suffix, chord = element scaling in x and z, twist = section rotation about y [deg])
SECTIONS = [("root", 5.0, 0.0), ("kink", 3.4, -1.5), ("tip", 1.4, -3.0)]

# Positionings: (to section, from section or None, length, sweepAngle, dihedralAngle)
POSITIONINGS = [("root", None, 0.0, 0.0, 0.0), ("kink", "root", 6.0, 20.0, 6.0), ("tip", "kink", 9.0, 28.0, 6.0)]

# Component segment: (uID suffix, from section, to section)
COMPONENT_SEGMENT = ("componentSegment", "root", "tip")


# -------------------------------------------------------------------- geometry
def rotation_x(angle):
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rotation_y(angle):
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rotation_z(angle):
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def transform(points, rotation=(0.0, 0.0, 0.0), scaling=(1.0, 1.0, 1.0), translation=(0.0, 0.0, 0.0)):
    """transformationType: scaling, then rotation about z, y and x, then translation."""
    matrix = rotation_x(rotation[0]) @ rotation_y(rotation[1]) @ rotation_z(rotation[2]) @ np.diag(scaling)
    return np.asarray(points, dtype=float) @ matrix.T + np.asarray(translation)


def positioning_vector(length, sweep, dihedral):
    return rotation_x(dihedral) @ rotation_z(-sweep) @ np.array([0.0, length, 0.0])


def positioning_ends(positionings=POSITIONINGS):
    """End point of the positioning chain of each section, in the wing coordinate system."""
    by_section = {to: (start, length, sweep, dihedral) for to, start, length, sweep, dihedral in positionings}

    def end(section):
        start, length, sweep, dihedral = by_section[section]
        origin = end(start) if start else np.zeros(3)
        return origin + positioning_vector(length, sweep, dihedral)

    return {section: end(section) for section in by_section}


def _airfoil():
    """Closed NACA 2412 contour from the trailing edge over the lower side, as (x, z)."""
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, 81)))  # 1 ... 0
    (xu, zu), (xl, zl), _, _ = naca4("2412", x, 0.0)
    return np.column_stack([np.concatenate([xl, xu[::-1][1:]]), np.concatenate([zl, zu[::-1][1:]])])


AIRFOIL = _airfoil()


def airfoil_points_xml(n=13):
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, n)))  # 1 ... 0
    (xu, zu), (xl, zl), _, _ = naca4("2412", x, 0.0)
    xs = list(xl) + list(xu[::-1][1:])
    zs = list(zl) + list(zu[::-1][1:])
    return [round(float(v), 4) + 0.0 for v in xs], [round(float(v), 4) + 0.0 for v in zs]


def section_airfoil(section, airfoil=AIRFOIL, positionings=POSITIONINGS):
    """Airfoil of the element of a section in the wing coordinate system."""
    name, chord, twist = section
    p = np.column_stack([airfoil[:, 0], np.zeros(len(airfoil)), airfoil[:, 1]])
    p = transform(p, scaling=(chord, 1.0, chord))  # element
    p = transform(p, rotation=(0.0, twist, 0.0))  # section
    return p + positioning_ends(positionings)[name]


def leading_trailing_edge(section):
    """Leading and trailing edge point of the airfoil of a section in the wing coordinate system."""
    points = section_airfoil(section, np.array([[0.0, 0.0], [1.0, 0.0]]))
    return points[0], points[1]


# ------------------------------------------------------------------- equations
PROFILE_POINT_LINES = [
    r"P = t_\mathrm{positioning} + T_\mathrm{section}\,T_\mathrm{element}\,p",
]
POSITIONING_VECTOR_LINES = [
    r"v = L\,\left(\sin\varphi,\ \cos\varphi\,\cos\nu,\ \cos\varphi\,\sin\nu\right)",
]


# --------------------------------------------------------------------- helpers
def arrow(ax, start, end, color=INK, lw=None, head=7):
    ax.annotate("", xy=end, xytext=start, zorder=5, arrowprops={
        "arrowstyle": "-|>", "lw": lw or LINE["secondary"], "mutation_scale": head, "shrinkA": 0, "shrinkB": 0,
        "color": color})
    ax.plot(*np.array([start, end]).T, alpha=0)  # include the arrow in the axis limits


def label(ax, xy, text, offset=(0, 0), ha="center", va="center", color=INK):
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=color,
                zorder=7)


def dot(ax, xy, color=INK, size=4.5, marker="o"):
    ax.plot(*xy, ls="none", marker=marker, ms=size, color=color, mec=COLORS["surface"], mew=1.0, zorder=6)


def axes_cross(ax, origin, directions, names, length, offsets):
    for direction, name, offset in zip(directions, names, offsets, strict=True):
        tip = np.asarray(origin) + length * np.asarray(direction)
        arrow(ax, origin, tip, color=INK2, lw=LINE["reference"], head=6)
        label(ax, tip, name, offset, color=INK2)


# --------------------------------------------------------------------- figures
def figure_parts():
    """Oblique view of the example wing with its sections, elements, positionings and segments."""
    ends = positioning_ends()
    z_scale = 3.0  # vertical scale exaggerated so that airfoils, twist and dihedral are visible

    def project(p):  # oblique view: x to the right, z up, the span (y) running up to the right into the depth
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 0] + 0.6 * p[..., 1], z_scale * p[..., 2] + 0.32 * p[..., 1]]).T

    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.9))

        # segments: upper surface between the airfoils
        for inner, outer in zip(SECTIONS[:-1], SECTIONS[1:]):
            le0, te0 = leading_trailing_edge(inner)
            le1, te1 = leading_trailing_edge(outer)
            ax.add_patch(Polygon(project([le0, le1, te1, te0]), closed=True, facecolor=PROFILE, alpha=0.08,
                                 edgecolor="none", zorder=0))
            for a, b in ((le0, le1), (te0, te1)):
                ax.plot(*project([a, b]).T, color=MUTED, lw=LINE["reference"], zorder=1)

        # elements: airfoils; sections: coordinate systems at the section origins
        z_axis_middle = {}
        for section in SECTIONS:
            name, chord, twist = section
            ax.plot(*project(section_airfoil(section)).T, color=PROFILE, zorder=3)
            origin = ends[name]
            # axes of the section coordinate system, labelled once at the root. The x-axis follows the drawn
            # chord; the z-axis is drawn perpendicular to it, since the exaggerated vertical scale would
            # otherwise distort the right angle.
            start = project(origin)
            x_tip = project(origin + 0.3 * chord * (rotation_y(twist) @ np.array([1.0, 0.0, 0.0])))
            x_dir = (x_tip - start) / np.linalg.norm(x_tip - start)
            z_tip = start + z_scale * 0.9 * np.array([-x_dir[1], x_dir[0]])
            z_axis_middle[name] = 0.5 * (start + z_tip)
            for tip, text, offset in ((x_tip, "x", (5, 0)), (z_tip, "z", (0, 7))):
                arrow(ax, start, tip, color=INK2, lw=LINE["reference"], head=6)
                if name == "root":
                    label(ax, tip, text, offset, color=INK2)

        # positionings
        for to, start, length, _, _ in POSITIONINGS:
            if length > 0.0:
                arrow(ax, project(ends[start]), project(ends[to]), color=POSITIONING, lw=LINE["data"], head=9)
        for section in SECTIONS:
            dot(ax, project(ends[section[0]]))

        # labels with leader lines
        def callout(xy, text, offset, ha="center", va="center"):
            ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE,
                        color=INK, zorder=7, arrowprops=leader())

        callout(project(ends["root"]), "origin of the wing coordinate system\nand of the root section", (-12, -22),
                ha="right", va="top")
        callout(project(section_airfoil(SECTIONS[1])[30]), "element: airfoil placed in the kink section",
                (30, -40), ha="left", va="top")
        callout(z_axis_middle["tip"], "section: coordinate system at the tip",
                (-40, 22), ha="right", va="bottom")
        middle = 0.35 * ends["tip"] + 0.65 * ends["kink"]
        callout(project(middle), "positioning of the tip section,\nstarting at the end of the kink positioning",
                (-30, 44), ha="right", va="bottom")
        for index, (inner, outer) in enumerate(zip(SECTIONS[:-1], SECTIONS[1:]), start=1):
            le0, te0 = leading_trailing_edge(inner)
            le1, te1 = leading_trailing_edge(outer)
            label(ax, project(0.05 * (le0 + le1) + 0.45 * (te0 + te1)), f"segment {index}", color=INK2)
        ax.annotate(f"vertical scale exaggerated {z_scale:g}:1", xy=(1.0, 0.0), xycoords="axes fraction", ha="right", va="bottom",
                    fontsize=NOTE, color=INK2)
        ax.set_aspect("equal")
        ax.axis("off")
        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=POSITIONING),
                   Line2D([], [], color=PROFILE, lw=6, alpha=0.15)]
        fig.legend(handles, ["airfoil of an element", "positioning", "segment"], loc="lower center", ncol=3,
                   bbox_to_anchor=(0.5, -0.02), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "wingParts.png")


# Illustrative split wingtip: two segments start at the kink section. TiGL does not load such a wing, so it is not
# part of the example file. Sections: name -> (from section or None, length, sweepAngle, dihedralAngle, chord);
# segments: (inner section, outer section).
SPLIT_WING = {
    "root": (None, 0.0, 0.0, 0.0, 5.0),
    "kink": ("root", 6.0, 20.0, 6.0, 3.4),
    "upper tip": ("kink", 6.0, 30.0, 28.0, 1.4),
    "lower tip": ("kink", 6.0, 45.0, -30.0, 1.4),
}
SPLIT_SEGMENTS = [("root", "kink"), ("kink", "upper tip"), ("kink", "lower tip")]


def figure_split_wingtip():
    """Oblique view of a split wingtip: two segments start at the kink section and lead to two tip sections."""
    z_scale = 3.0  # vertical scale exaggerated as in wingParts
    positionings = [(to, start, length, sweep, dihedral) for to, (start, length, sweep, dihedral, _) in SPLIT_WING.items()]
    ends = positioning_ends(positionings)
    edges = np.array([[0.0, 0.0], [1.0, 0.0]])

    def project(p):
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 0] + 0.6 * p[..., 1], z_scale * p[..., 2] + 0.32 * p[..., 1]]).T

    def airfoil(section, points=AIRFOIL):
        chord = SPLIT_WING[section][4]
        return np.column_stack([points[:, 0] * chord, np.zeros(len(points)), points[:, 1] * chord]) + ends[section]

    def callout(xy, text, offset, ha="center", va="center"):
        ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE,
                    color=INK, zorder=7, arrowprops=leader())

    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.9))
        for inner, outer in SPLIT_SEGMENTS:
            (le0, te0), (le1, te1) = airfoil(inner, edges), airfoil(outer, edges)
            ax.add_patch(Polygon(project([le0, le1, te1, te0]), closed=True, facecolor=PROFILE, alpha=0.08,
                                 edgecolor="none", zorder=0))
            for a, b in ((le0, le1), (te0, te1)):
                ax.plot(*project([a, b]).T, color=MUTED, lw=LINE["reference"], zorder=1)
        for section, (start, _, _, _, chord) in SPLIT_WING.items():
            ax.plot(*project(airfoil(section)).T, color=PROFILE, zorder=3)
            origin = project(ends[section])
            for tip in (project(ends[section] + np.array([0.3 * chord, 0.0, 0.0])),
                        origin + np.array([0.0, z_scale * 0.9])):
                arrow(ax, origin, tip, color=INK2, lw=LINE["reference"], head=6)
            if start:
                arrow(ax, project(ends[start]), origin, color=POSITIONING, lw=LINE["data"], head=9)
            dot(ax, origin)

        for index, (inner, outer) in enumerate(SPLIT_SEGMENTS[1:], start=2):
            middle = project(0.25 * (airfoil(inner, edges).sum(axis=0) + airfoil(outer, edges).sum(axis=0)))
            offset = (50, 10) if outer == "upper tip" else (70, 30)
            callout(middle, f"segment {index} to the {outer}", offset, ha="left", va="center")
        callout(project(ends["kink"]), "kink section: both segments start here", (-60, 50), ha="right", va="bottom")

        ax.annotate(f"vertical scale exaggerated {z_scale:g}:1", xy=(0.0, 1.0), xycoords="axes fraction", ha="left",
                    va="top", fontsize=NOTE, color=INK2)
        ax.set_aspect("equal")
        ax.axis("off")
        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=POSITIONING),
                   Line2D([], [], color=PROFILE, lw=6, alpha=0.15)]
        fig.legend(handles, ["airfoil of an element", "positioning", "segment"], loc="lower center", ncol=3,
                   bbox_to_anchor=(0.5, -0.02), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "wingSplitWingtip.png")


def figure_geometry():
    """Top and front view of the example wing: sections, positionings and segments."""
    ends = positioning_ends()
    with figure_style():
        fig, (top, front) = plt.subplots(2, 1, figsize=(FULL_WIDTH, 5.6), gridspec_kw={"height_ratios": [2.3, 1.0],
                                                                                       "hspace": 0.25})

        views = ((top, lambda p: np.array([p[1], -p[0]]), "(a) Top view"),
                 (front, lambda p: np.array([p[1], p[2]]), "(b) Front view"))
        for ax, view, title in views:
            # segments: area between the airfoils in the top view
            for inner, outer in zip(SECTIONS[:-1], SECTIONS[1:]):
                le0, te0 = leading_trailing_edge(inner)
                le1, te1 = leading_trailing_edge(outer)
                if ax is top:  # in the front view, the edges would lie on top of the positionings
                    ax.add_patch(Polygon([view(le0), view(le1), view(te1), view(te0)], closed=True,
                                         facecolor=PROFILE, alpha=0.08, edgecolor="none", zorder=0))
                    for a, b in ((le0, le1), (te0, te1)):
                        ax.plot(*np.array([view(a), view(b)]).T, color=MUTED, lw=LINE["reference"], zorder=1)
                else:  # front view: the area between the highest and lowest points of the airfoils
                    z0, z1 = section_airfoil(inner)[:, 2], section_airfoil(outer)[:, 2]
                    y0, y1 = le0[1], le1[1]
                    ax.add_patch(Polygon([(y0, z0.max()), (y1, z1.max()), (y1, z1.min()), (y0, z0.min())],
                                         closed=True, facecolor=PROFILE, alpha=0.08, edgecolor="none", zorder=0))
            for section in SECTIONS:
                if ax is top:
                    le, te = leading_trailing_edge(section)
                    ax.plot(*np.array([view(le), view(te)]).T, color=PROFILE, zorder=2)
                else:
                    ax.plot(*np.array([view(q) for q in section_airfoil(section)]).T, color=PROFILE, zorder=2,
                            lw=LINE["secondary"])
            for to, start, length, _, _ in POSITIONINGS:
                if length == 0.0:
                    continue
                arrow(ax, view(ends[start]), view(ends[to]), color=POSITIONING, lw=LINE["data"], head=9)
            for section in SECTIONS:
                dot(ax, view(ends[section[0]]))
            ax.set_aspect("equal")
            ax.set_anchor("E")
            ax.axis("off")
            ax.set_title(title)

        # labels, top view
        view = views[0][1]
        axes_cross(top, view((-0.6, 12.0, 0.0)), [(0, -1), (1, 0)], ["x", "y"], 1.2, [(0, -7), (6, 0)])
        for section in SECTIONS:
            _, te = leading_trailing_edge(section)
            label(top, view(te), f"{section[0]} section", (0, -8), va="top", color=INK2)
        segment_labels = ("segment 1", "segment 2")
        for text, inner, outer in zip(segment_labels, SECTIONS[:-1], SECTIONS[1:]):
            le0, te0 = leading_trailing_edge(inner)
            le1, te1 = leading_trailing_edge(outer)
            label(top, view(0.25 * (le0 + le1) + 0.25 * (te0 + te1)), text, (0, -6), color=INK2)
        for to, start, length, sweep, dihedral in POSITIONINGS[1:]:
            middle = 0.5 * (view(ends[start]) + view(ends[to]))
            label(top, middle, f"positioning {to}\nlength {length:g}, sweep {sweep:g}°", (8, 10), ha="left",
                  va="bottom")
        label(top, view((0, 0, 0)), "origin of the wing\ncoordinate system", (-8, 0), ha="right", color=INK2)

        # labels, front view
        view = views[1][1]
        axes_cross(front, view((0.0, -2.0, 0.0)), [(1, 0), (0, 1)], ["y", "z"], 1.2, [(6, 0), (0, 7)])
        sections = {section[0]: section for section in SECTIONS}
        for to, start, length, sweep, dihedral in POSITIONINGS[1:]:
            # above the middle of the upper edge of the wing, so that the labels keep the same distance to it
            top_inner, top_outer = (section_airfoil(sections[name])[:, 2].max() for name in (start, to))
            middle = (0.5 * (ends[start][1] + ends[to][1]), 0.5 * (top_inner + top_outer))
            label(front, middle, f"dihedral {dihedral:g}°", (0, 6), va="bottom")

        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=POSITIONING),
                   Line2D([], [], ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"])]
        fig.legend(handles, ["airfoil of the section element", "positioning", "origin of the section"],
                   loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "wingGeometry.png")


def figure_profile_transformation():
    """Side view of the steps from the airfoil to the section: element scaling, then section rotation."""
    _, chord, _ = SECTIONS[0]
    twist = -12.0  # exaggerated so that the rotation is visible
    c, s = np.cos(np.radians(twist)), np.sin(np.radians(twist))
    scaled = AIRFOIL * chord
    rotated = scaled @ np.array([[c, s], [-s, c]]).T  # rotation about y, seen in the x-z plane
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 1.9), gridspec_kw={"wspace": 0.12})
        # (title, points, chord, view): view is the length each panel is scaled to. The airfoil in (a) is
        # drawn shorter than the scaled one, though not at the true ratio, so that the scaling is visible.
        steps = [("(a) Airfoil", AIRFOIL, 1.0, 1.6), (f"(b) Element: scaling {chord:g}", scaled, chord, chord),
                 ("(c) Section: rotation about y", rotated, chord, chord)]
        for ax, (title, points, _, view) in zip(axes, steps, strict=True):
            ax.plot(points[:, 0], points[:, 1], color=PROFILE, zorder=3)
            axes_cross(ax, (0.0, 0.0), [(1, 0), (0, 1)], ["x", "z"], 0.25 * view, [(0, -12), (0, 6)])
            ax.set_xlim(-0.1 * view, 1.25 * view)
            ax.set_ylim(-0.38 * view, 0.4 * view)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(title, fontsize=FONT_SIZE["base"])
        for ax, (_, _, size, view) in zip(axes[:2], steps[:2]):
            y = -0.25 * view
            ax.plot([0.0, size], [y, y], color=MUTED, lw=LINE["reference"])
            for x in (0.0, size):
                ax.plot([x, x], [y - 0.03 * view, y + 0.03 * view], color=MUTED, lw=LINE["reference"])
            label(ax, (0.5 * size, y), f"chord {size:g}", (0, -3), va="top", color=INK2)
        radius = 1.05 * chord
        axes[2].plot([0.0, radius], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=1)
        axes[2].add_patch(Arc((0, 0), 2 * radius, 2 * radius, theta1=0.0, theta2=-twist, color=INK2,
                              lw=LINE["reference"]))
        label(axes[2], (radius, 0.0), f"rotation {twist:g}°\n(exaggerated)", (4, -3), ha="left", va="top",
              color=INK2)
        save_figure(fig, FIGURES / "wingProfileTransformation.png")


# Illustrative element transformation within its section, not part of the example file:
# scaling of the airfoil, rotation about y [deg] and translation (x, z) in the section coordinate system
ELEMENT_SCALING = 3.0
ELEMENT_ROTATION = -12.0
ELEMENT_TRANSLATION = (2.4, 0.9)


def figure_element_coordinates():
    """Side view of an element coordinate system, translated and rotated within the section coordinate system."""
    c, s = np.cos(np.radians(ELEMENT_ROTATION)), np.sin(np.radians(ELEMENT_ROTATION))
    rotation = np.array([[c, s], [-s, c]])  # rotation about y, seen in the x-z plane
    origin = np.array(ELEMENT_TRANSLATION)
    airfoil = (AIRFOIL * ELEMENT_SCALING) @ rotation.T + origin  # scaling, rotation, translation
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.9))
        # section coordinate system
        # the x-axis runs past the trailing edge of the scaled airfoil, like the x-axis of the element
        x_length = 1.3 * ELEMENT_SCALING
        for tip, text, offset in (((x_length, 0.0), "x", (6, 0)), ((0.0, 1.0), "z", (0, 7))):
            arrow(ax, (0.0, 0.0), tip, color=INK2, lw=LINE["reference"], head=6)
            label(ax, tip, text, offset, color=INK2)
        dot(ax, (0.0, 0.0))
        label(ax, (0.0, 0.0), "section coordinate system", (-10, 0), ha="right", color=INK2)
        # translation of the element
        arrow(ax, (0.0, 0.0), origin * (1.0 - 0.1 / np.linalg.norm(origin)), color=INK2, lw=LINE["reference"], head=6)
        label(ax, 0.62 * origin, "translation", (8, -6), ha="left", va="top", color=INK2)
        # element coordinate system
        z_tip = origin + 1.0 * (rotation @ (0.0, 1.0))
        for tip, text, offset in ((origin + 1.3 * ELEMENT_SCALING * (rotation @ (1.0, 0.0)), "x", (6, 0)),
                                  (z_tip, "z", (0, 7))):
            arrow(ax, origin, tip, color=INK, lw=LINE["secondary"], head=7)
            label(ax, tip, text, offset)
        label(ax, z_tip, "element coordinate system", (-10, 0), ha="right")
        dot(ax, origin)
        # rotation about y, measured from a line parallel to the x-axis of the section behind the trailing edge
        radius = 1.2 * ELEMENT_SCALING
        ax.plot([origin[0], origin[0] + radius + 0.25], [origin[1], origin[1]], color=MUTED, lw=LINE["reference"],
                zorder=1)
        ax.add_patch(Arc(origin, 2 * radius, 2 * radius, theta1=0.0, theta2=-ELEMENT_ROTATION, color=INK2,
                         lw=LINE["reference"]))
        arc_middle = origin + radius * np.array([np.cos(np.radians(-ELEMENT_ROTATION / 2)),
                                                 np.sin(np.radians(-ELEMENT_ROTATION / 2))])
        label(ax, arc_middle, "rotation about y", (8, 0), ha="left", color=INK2)
        # the scaled airfoil before rotation and translation, i.e. with the element coordinate system on the
        # section coordinate system (a pale solid line; the figure style has no dashed lines)
        original = AIRFOIL * ELEMENT_SCALING
        for points, text, index, offset, ha in (
                (AIRFOIL, "airfoil with chord length 1", 30, (-20, -30), "right"),
                (original, f"scaled by {ELEMENT_SCALING:g}, without rotation and translation", 25, (20, -26), "left")):
            ax.plot(*points.T, color=COLORS["series1Light"], lw=LINE["secondary"], zorder=2)
            ax.annotate(text, xy=points[index], xytext=offset, textcoords="offset points", ha=ha, va="top",
                        fontsize=NOTE, color=INK2, zorder=7, arrowprops=leader())
        # airfoil placed in the element coordinate system
        ax.plot(*airfoil.T, color=PROFILE, zorder=3)
        label(ax, airfoil[120], f"airfoil, scaled by {ELEMENT_SCALING:g}", (0, 10), va="bottom")
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "wingElementCoordinates.png")


def figure_positioning():
    """(a) Construction of a positioning vector, (b) a chain of positionings with a section translation."""
    length, sweep, dihedral = 4.0, 35.0, 30.0  # exaggerated angles for readability
    with figure_style():
        fig, (construction, chain) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.3),
                                                  gridspec_kw={"width_ratios": [1.0, 1.0], "wspace": 0.15})

        # (a) oblique view: y to the right, z up, x backwards into the depth, drawn up to the right. The plane of
        # the sweep angle then lies below the swept y-axis and the plane of the dihedral angle above it.
        def project(p):
            p = np.asarray(p, dtype=float)
            return np.array([p[..., 1] + 0.35 * p[..., 0], p[..., 2] + 0.55 * p[..., 0]]).T

        def wash(points):
            construction.add_patch(Polygon(project(points), closed=True, facecolor=PROFILE, alpha=0.1,
                                           edgecolor="none", zorder=0))

        v_swept = rotation_z(-sweep) @ np.array([0.0, length, 0.0])  # the y-axis rotated by the sweep angle
        v = positioning_vector(length, sweep, dihedral)
        center = np.array([v[0], 0.0, 0.0])  # the dihedral rotates about the x-axis, around this point
        o = project((0.0, 0.0, 0.0))
        for direction, size, text, offset in (((1, 0, 0), 0.75, "x", (-4, 6)), ((0, 1, 0), 1.1, "y", (6, 0)),
                                              ((0, 0, 1), 0.55, "z", (0, 7))):
            tip = project(size * length * np.array(direction, dtype=float))
            arrow(construction, o, tip, color=INK2, lw=LINE["reference"], head=6)
            label(construction, tip, text, offset, color=INK2)

        # step 1: sweep angle in the x-y plane, from the y-axis to the swept y-axis
        sweep_arc = np.array([rotation_z(-a) @ np.array([0.0, length, 0.0]) for a in np.linspace(0.0, sweep, 40)])
        wash([np.zeros(3), *sweep_arc])
        construction.plot(*project(sweep_arc).T, color=INK2, lw=LINE["reference"], zorder=2)
        label(construction, project(rotation_z(-sweep / 2) @ np.array([0.0, length, 0.0])), "φ", (8, -2), ha="left")
        construction.plot(*project([np.zeros(3), v_swept]).T, color=MUTED, lw=LINE["secondary"], zorder=1)
        label(construction, project(v_swept), "rotated y-axis", (10, 0), ha="left", color=INK2)

        # step 2: dihedral angle about the x-axis, from the swept y-axis to the positioning vector
        dihedral_arc = np.array([rotation_x(a) @ v_swept for a in np.linspace(0.0, dihedral, 40)])
        wash([center, *dihedral_arc])
        construction.plot(*project(dihedral_arc).T, color=INK2, lw=LINE["reference"], zorder=2)
        for end in (v_swept, v):  # radii from the x-axis, so that the apex of the sector is visible on the axis
            construction.plot(*project([center, end]).T, color=MUTED, lw=LINE["reference"], zorder=1)
        label(construction, project(center + 0.72 * (rotation_x(dihedral / 2) @ v_swept - center)), "ν")

        arrow(construction, o, project(v), color=POSITIONING, lw=LINE["data"], head=9)
        label(construction, project(v), "v, length L", (0, 7), va="bottom")
        dot(construction, o)
        label(construction, o, "start", (-6, 4), ha="right", va="bottom", color=INK2)
        construction.set_aspect("equal")
        construction.set_anchor("N")
        construction.axis("off")
        construction.set_title("(a) Positioning vector")

        # (b) top view of a chain A -> B -> C, section B additionally translated
        def top(p):
            return np.array([p[1], -p[0]])

        chain_positionings = [("A", None, 0.0, 0.0, 0.0), ("B", "A", 4.0, 25.0, 0.0), ("C", "B", 4.0, 25.0, 0.0)]
        translation_b = np.array([1.4, 0.0, 0.0])
        ends = positioning_ends(chain_positionings)
        for to, start, _, _, _ in chain_positionings[1:]:
            arrow(chain, top(ends[start]), top(ends[to]), color=POSITIONING, lw=LINE["data"], head=9)
            label(chain, 0.5 * (top(ends[start]) + top(ends[to])), f"positioning {to}", (6, 6), ha="left",
                  va="bottom")
        arrow(chain, top(ends["B"]), top(ends["B"] + translation_b), color=INK2, lw=LINE["reference"])
        label(chain, top(ends["B"] + 0.5 * translation_b), "translation\nof section B", (-6, 0), ha="right",
              color=INK2)
        for name, origin, offset, ha, va in (("A", ends["A"], (-6, 0), "right", "center"),
                                             ("B", ends["B"] + translation_b, (0, -8), "center", "top"),
                                             ("C", ends["C"], (0, -8), "center", "top")):
            dot(chain, top(origin))
            label(chain, top(origin), f"section {name}", offset, ha=ha, va=va)
        dot(chain, top(ends["B"]), color=POSITIONING)
        label(chain, top(ends["B"]), "end of positioning B", (8, 6), ha="left", va="bottom", color=INK2)
        corner = top((-0.6, 6.4, 0.0))  # free area above the end of the chain
        axes_cross(chain, corner, [(0, -1), (1, 0)], ["x", "y"], 0.8, [(0, -7), (6, 0)])
        bottom, top_limit = chain.get_ylim()
        chain.set_ylim(bottom, top_limit + 1.0)  # space between the title and the chain
        chain.set_aspect("equal")
        chain.set_anchor("N")
        chain.axis("off")
        chain.set_title("(b) Chain of positionings, top view")
        save_figure(fig, FIGURES / "positioningVector.png")


# --------------------------------------------------------------------- example
def element_xml(section):
    name, chord, _ = section
    return "\n".join([
        f'<element uID="{WING_UID}_{name}_element">', f"    <name>{name.capitalize()} element</name>",
        f"    <airfoilUID>{AIRFOIL_UID}</airfoilUID>",
        indent(transformation_xml(scaling=(chord, 1.0, chord)), 1), "</element>",
    ])


def section_xml(section):
    name, _, twist = section
    return "\n".join([
        f'<section uID="{WING_UID}_{name}">', f"    <name>{name.capitalize()} section</name>",
        indent(transformation_xml(rotation=(0.0, twist, 0.0)), 1),
        "    <elements>", indent(element_xml(section), 2), "    </elements>", "</section>",
    ])


def positioning_xml(positioning):
    to, start, length, sweep, dihedral = positioning
    lines = [f'<positioning uID="{WING_UID}_{to}_positioning">', f"    <name>{to.capitalize()} positioning</name>",
             f"    <length>{length:g}</length>", f"    <sweepAngle>{sweep:g}</sweepAngle>",
             f"    <dihedralAngle>{dihedral:g}</dihedralAngle>"]
    if start:
        lines.append(f"    <fromSectionUID>{WING_UID}_{start}</fromSectionUID>")
    lines += [f"    <toSectionUID>{WING_UID}_{to}</toSectionUID>", "</positioning>"]
    return "\n".join(lines)


def segment_xml(index):
    inner, outer = SECTIONS[index][0], SECTIONS[index + 1][0]
    return "\n".join([
        f'<segment uID="{WING_UID}_segment{index + 1}">', f"    <name>Segment {index + 1}</name>",
        f"    <fromElementUID>{WING_UID}_{inner}_element</fromElementUID>",
        f"    <toElementUID>{WING_UID}_{outer}_element</toElementUID>", "</segment>",
    ])


def component_segments_xml(control_surfaces=None, structure=None):
    """Component segments of the example wing.

    control_surfaces and structure are the XML of a controlSurfaces and a structure element, if any.
    """
    uid, start, end = COMPONENT_SEGMENT
    return "\n".join([
        "<componentSegments>", f'    <componentSegment uID="{WING_UID}_{uid}">', "        <name>Component segment</name>",
        f"        <fromElementUID>{WING_UID}_{start}_element</fromElementUID>",
        f"        <toElementUID>{WING_UID}_{end}_element</toElementUID>",
        *([indent(structure, 2)] if structure else []),
        *([indent(control_surfaces, 2)] if control_surfaces else []),
        "    </componentSegment>", "</componentSegments>",
    ])


def collection(tag, items):
    return "\n".join([f"<{tag}>", *(indent(item, 1) for item in items), f"</{tag}>"])


def positionings_xml():
    return collection("positionings", [positioning_xml(p) for p in POSITIONINGS])


def segments_xml():
    return collection("segments", [segment_xml(i) for i in range(len(SECTIONS) - 1)])


def wing_xml(control_surfaces=None, structure=None):
    return "\n".join([
        f'<wing uID="{WING_UID}" symmetry="x-z-plane">', "    <name>Wing</name>",
        "    <description>Wing with a kink, swept and with dihedral outboard of the kink</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(transformation_xml(translation=WING_TRANSLATION), 1),
        indent(collection("sections", [section_xml(s) for s in SECTIONS]), 1),
        indent(positionings_xml(), 1),
        indent(segments_xml(), 1),
        indent(component_segments_xml(control_surfaces, structure), 1),
        "</wing>",
    ])


def airfoil_xml():
    xs, zs = airfoil_points_xml()
    return "\n".join([
        f'<wingAirfoil uID="{AIRFOIL_UID}">', "    <name>NACA 2412 with closed trailing edge</name>",
        "    <pointList>", f"        <x>{vector(xs)}</x>", f"        <y>{vector([0.0] * len(xs))}</y>",
        f"        <z>{vector(zs)}</z>", "    </pointList>", "</wingAirfoil>",
    ])


def fuselage_xml():
    """A simple fuselage with circular sections, the parent of the wing."""
    sections, segments = [], []
    for name, x, diameter in FUSELAGE_SECTIONS:
        sections.append("\n".join([
            f'<section uID="{FUSELAGE_UID}_{name}">', f"    <name>{name.capitalize()} section</name>",
            indent(transformation_xml(translation=(x, 0.0, 0.0)), 1),
            "    <elements>", f'        <element uID="{FUSELAGE_UID}_{name}_element">',
            f"            <name>{name.capitalize()} element</name>",
            f"            <profileUID>{FUSELAGE_PROFILE_UID}</profileUID>",
            indent(transformation_xml(scaling=(1.0, diameter, diameter)), 3),
            "        </element>", "    </elements>", "</section>",
        ]))
    for index, (inner, outer) in enumerate(zip(FUSELAGE_SECTIONS[:-1], FUSELAGE_SECTIONS[1:]), start=1):
        segments.append("\n".join([
            f'<segment uID="{FUSELAGE_UID}_segment{index}">', f"    <name>Segment {index}</name>",
            f"    <fromElementUID>{FUSELAGE_UID}_{inner[0]}_element</fromElementUID>",
            f"    <toElementUID>{FUSELAGE_UID}_{outer[0]}_element</toElementUID>", "</segment>",
        ]))
    return "\n".join([
        f'<fuselage uID="{FUSELAGE_UID}">', "    <name>Fuselage</name>",
        indent(transformation_xml(), 1),
        indent(collection("sections", sections), 1),
        indent(collection("segments", segments), 1),
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


def excerpt_wing_xml():
    translation = indent(transformation_xml(translation=WING_TRANSLATION), 1).splitlines()
    return "\n".join([
        f'<wing uID="{WING_UID}" symmetry="x-z-plane">', "    <name>Wing</name>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        *translation,
        "    <sections>",
        f'        <section uID="{WING_UID}_root">', "            ...", "        </section>",
        "        ...",
        "    </sections>",
        "    <positionings>", "        ...", "    </positionings>",
        "    <segments>", "        ...", "    </segments>",
        "    <componentSegments>", "        ...", "    </componentSegments>",
        "</wing>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Wing geometry",
        description="A wing built from sections, elements, positionings, segments and a component segment, attached to a fuselage.",
        model_uid="WingGeometryAircraft",
        model_name="Wing geometry example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml())],
        extra_profiles=[("wingAirfoils", airfoil_xml())],
    )


# ------------------------------------------------------------------------ main
def main():
    save_equation(PROFILE_POINT_LINES, EQUATIONS / "wingProfilePoint")
    save_equation(POSITIONING_VECTOR_LINES, EQUATIONS / "positioningVector")
    figure_parts()
    figure_split_wingtip()
    figure_geometry()
    figure_profile_transformation()
    figure_element_coordinates()
    figure_positioning()
    write_example()
    ends = positioning_ends()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for section in SECTIONS:
        le, te = leading_trailing_edge(section)
        print(f"{section[0]}: section origin {np.round(ends[section[0]], 4)}, "
              f"leading edge {np.round(le + WING_TRANSLATION, 4)}, trailing edge {np.round(te + WING_TRANSLATION, 4)}"
              " (global)")
    print("\nExcerpt for the wingType documentation:\n")
    print(excerpt_wing_xml())
    print("\nExcerpt for the wingSectionType documentation:\n")
    print(section_xml(SECTIONS[1]))
    print("\nExcerpt for the wingElementType documentation:\n")
    print(collection("elements", [element_xml(SECTIONS[1])]))
    print("\nExcerpt for the positioningType documentation:\n")
    print(positionings_xml())
    print("\nExcerpt for the wingSegmentType documentation:\n")
    print(segments_xml())


if __name__ == "__main__":
    main()

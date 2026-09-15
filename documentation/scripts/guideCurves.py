# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equation and example data for the documentation of guide curves
(guideCurveType, guideCurveProfileGeometryType).

Run from the repository root:

    uv run documentation/scripts/guideCurves.py

The script writes

    documentation/figures/guideCurveCoordinates.png
    documentation/figures/guideCurveSegments.png
    documentation/figures/guideCurveProfile.png
    documentation/equations/guideCurvePoint.{tex,png}
    examples/guideCurves.xml

and prints the excerpts shown in the documentation. The schema documentation is
not written by this script; copy the printed excerpts there when the example changes.

Definition shown (as in the documentation): a guide curve point is
    P = P0 + rY (P1 - P0) + s (rX ex + rZ ez),   s = (1 - rY) s0 + rY s1,
with ex the rX direction, ez the unit vector along ex x (P1 - P0), and s the chord
length (wing) or height (fuselage) of the start and end profile.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from example_xml import indent, transformation_xml, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_equation, save_figure
from nacaProfile import naca4

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "guideCurves.xml"

PROFILE = COLORS["series1"]
GUIDE = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
# Wing sections: (uID suffix, y, x of the leading edge, chord)
WING_SECTIONS = [("root", 0.0, 0.0, 2.0), ("kink", 3.0, 0.8, 1.6), ("tip", 6.0, 1.8, 1.0)]
# Fuselage sections: (uID suffix, x, diameter)
FUSELAGE_SECTIONS = [("front", 0.0, 1.2), ("middle", 4.0, 2.0), ("rear", 10.0, 1.4)]

# Guide curve profiles: uID -> (name, rX, rY, rZ)
GUIDE_CURVE_PROFILES = {
    "GCP_straight": ("Straight guide curve", [0.0], [0.5], [0.0]),
    "GCP_leadingEdgeBulge": ("Leading edge moved forward", [-0.04, -0.06, -0.04], [0.25, 0.5, 0.75], [0, 0, 0]),
    "GCP_trailingEdgeBulge": ("Trailing edge moved backward", [0.04, 0.06, 0.04], [0.25, 0.5, 0.75], [0, 0, 0]),
    "GCP_canopy": ("Canopy hump", [0.1, 0.14, 0.08], [0.3, 0.55, 0.8], [0, 0, 0]),
}

# Guide curves: name -> list per segment of (guide curve profile, from, to, continuity).
# "from" is a relative circumference in the first segment and the previous guide curve afterwards.
WING_GUIDE_CURVES = {
    "leadingEdge": [("GCP_leadingEdgeBulge", 0.0, 0.0, None), ("GCP_straight", None, 0.0, None)],
    "trailingEdgeUpper": [("GCP_straight", 1.0, 1.0, None), ("GCP_trailingEdgeBulge", None, 1.0, "C0")],
    "trailingEdgeLower": [("GCP_straight", -1.0, -1.0, None), ("GCP_trailingEdgeBulge", None, -1.0, "C0")],
}
FUSELAGE_GUIDE_CURVES = {
    "top": [("GCP_canopy", 0.0, 0.0, None), ("GCP_straight", None, 0.0, None)],
    "right": [("GCP_straight", 0.25, 0.25, None), ("GCP_straight", None, 0.25, None)],
    "bottom": [("GCP_straight", 0.5, 0.5, None), ("GCP_straight", None, 0.5, None)],
    "left": [("GCP_straight", 0.75, 0.75, None), ("GCP_straight", None, 0.75, None)],
}


# -------------------------------------------------------------------- geometry
def _airfoil_sides():
    x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 400)))
    (xu, zu), (xl, zl), _, _ = naca4("0012", x, 0.0)
    lower = np.column_stack([xl[::-1], zl[::-1]])  # trailing edge -> leading edge
    upper = np.column_stack([xu, zu])  # leading edge -> trailing edge
    return lower, upper


LOWER_SIDE, UPPER_SIDE = _airfoil_sides()


def along(polyline, fraction):
    """Point at a relative arc length on a polyline."""
    steps = np.hypot(*np.diff(polyline, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(steps)])
    return np.array([np.interp(fraction * s[-1], s, polyline[:, i]) for i in range(polyline.shape[1])])


def airfoil_point(c):
    """Point (x, z) of the normalized airfoil at relative circumference c in [-1, 1]."""
    return along(LOWER_SIDE, c + 1.0) if c <= 0.0 else along(UPPER_SIDE, c)


def airfoil_points_xml(n=13):
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, n)))  # 1 ... 0
    (_, zu), (_, zl), _, _ = naca4("0012", x, 0.0)
    xs = list(x) + list(x[::-1][1:])
    zs = list(zl) + list(zu[::-1][1:])
    return [round(float(v), 4) + 0.0 for v in xs], [round(float(v), 4) + 0.0 for v in zs]


def wing_point(section, c):
    _, y, x_le, chord = section
    xa, za = airfoil_point(c)
    return np.array([x_le + chord * xa, y, chord * za])


def fuselage_point(section, c):
    """Point on a circular fuselage profile at relative circumference c (0 at the top, over +y)."""
    _, x, diameter = section
    r = 0.5 * diameter
    return np.array([x, r * np.sin(2 * np.pi * c), r * np.cos(2 * np.pi * c)])


def guide_curve_points(p0, p1, s0, s1, profile_uid, ex):
    """P0, the points of the guide curve profile and P1, in world coordinates."""
    _, rx, ry, rz = GUIDE_CURVE_PROFILES[profile_uid]
    ez = np.cross(ex, p1 - p0)
    ez /= np.linalg.norm(ez)
    points = [p0]
    for a, b, g in zip(rx, ry, rz, strict=True):
        s = (1 - b) * s0 + b * s1
        points.append(p0 + b * (p1 - p0) + s * (a * ex + g * ez))
    points.append(p1)
    return np.array(points)


def spline(points, n=200):
    """Smooth curve through points (centripetal Catmull-Rom), for drawing only."""
    points = np.asarray(points, dtype=float)
    if len(points) == 2:
        return np.linspace(points[0], points[1], n)
    padded = np.vstack([2 * points[0] - points[1], points, 2 * points[-1] - points[-2]])
    result = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1:i + 3]
        t = np.linspace(0.0, 1.0, n // (len(points) - 1), endpoint=(i == len(padded) - 3))[:, None]
        m1, m2 = 0.5 * (p2 - p0), 0.5 * (p3 - p1)
        h = [2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2]
        result.append(h[0] * p1 + h[1] * m1 + h[2] * p2 + h[3] * m2)
    return np.vstack(result)


# ------------------------------------------------------------------- equations
EQUATION_LINES = [
    r"P = P_0 + r_Y\,(P_1 - P_0) + s\,\left(r_X\,e_x + r_Z\,e_z\right)",
    r"s = (1 - r_Y)\,s_0 + r_Y\,s_1,\qquad e_z = \dfrac{e_x \times (P_1 - P_0)}{\left|e_x \times (P_1 - P_0)\right|}",
]


# --------------------------------------------------------------------- figures
def arrow(ax, start, end, color=INK, lw=None):
    ax.annotate("", xy=end, xytext=start, zorder=5, arrowprops={
        "arrowstyle": "-|>", "lw": lw or LINE["secondary"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
        "color": color})
    ax.plot(*np.array([start, end]).T, alpha=0)  # include the arrow in the axis limits


def label(ax, xy, text, offset=(0, 0), ha="center", va="center", color=INK):
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=color,
                zorder=7)


def dot(ax, xy, marker="o", color=INK, size=4.5):
    ax.plot(*xy, ls="none", marker=marker, ms=size, color=color, mec=COLORS["surface"], mew=1.0, zorder=6)


def construction_panel(ax, project, outline, connections, p0, p1, s0, s1, ex, r, frame_length, labels):
    """Profiles, the local directions at P0 and the construction of one guide curve point P.

    labels maps each label to its offset in points and its horizontal alignment.
    """
    for points in outline:
        xy = np.array([project(q) for q in points])
        ax.plot(*xy.T, color=PROFILE, zorder=3)
    for a, b in connections:
        ax.plot(*np.array([project(a), project(b)]).T, color=MUTED, lw=LINE["reference"], zorder=1)

    rx, ry, rz = r
    ez = np.cross(ex, p1 - p0)
    ez /= np.linalg.norm(ez)
    s = (1 - ry) * s0 + ry * s1
    q = p0 + ry * (p1 - p0)
    a = q + s * rx * ex
    p = a + s * rz * ez
    ax.plot(*np.array([project(p0), project(p1)]).T, color=MUTED, lw=LINE["reference"], zorder=2)
    curve = np.array([project(c) for c in spline([p0, p, p1])])
    ax.plot(*curve.T, color=GUIDE, zorder=4)

    def put(key, xy, text, color=INK):
        offset, ha = labels[key]
        label(ax, xy, text, offset, ha=ha, color=color)

    for direction, key, text in ((ex, "ex", labels["exText"][0]), (ez, "ez", "$e_z$")):
        tip = project(p0 + frame_length * direction)
        arrow(ax, project(p0), tip)
        put(key, tip, text)
    arrow(ax, project(p0), project(q), color=INK2, lw=LINE["reference"])
    arrow(ax, project(q), project(a), color=INK2, lw=LINE["reference"])
    arrow(ax, project(a), project(p), color=INK2, lw=LINE["reference"])
    put("ry", project(p0 + labels["ryAt"] * (q - p0)), "$r_Y\\,(P_1-P_0)$", INK2)
    put("rx", project(0.5 * (q + a)), "$r_X\\,s$", INK2)
    put("rz", project(0.5 * (a + p)), "$r_Z\\,s$", INK2)
    for point, key, text in ((p0, "p0", "$P_0$"), (p1, "p1", "$P_1$")):
        dot(ax, project(point))
        put(key, project(point), text)
    dot(ax, project(p), marker="D", color=GUIDE, size=5.5)
    put("p", project(p), "$P$")


def figure_coordinates():
    with figure_style():
        fig, (wing, fuselage) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.0), gridspec_kw={"wspace": 0.12})

        # (a) wing segment, seen from the side with the span running into the depth; the airfoil is drawn
        # thicker than in the example so that the construction is visible
        def project_wing(p):
            return np.array([p[0] + 0.45 * p[1], p[2] + 0.5 * p[1]])

        inner, outer = (0.0, 0.0, 1.6), (2.2, 0.5, 1.0)  # y, x of the leading edge, chord

        def thick_point(section, c):
            y, x_le, chord = section
            xa, za = airfoil_point(c)
            return np.array([x_le + chord * xa, y, 2.5 * chord * za])

        airfoil = np.vstack([LOWER_SIDE, UPPER_SIDE])
        outline = [[(x_le + chord * xa, y, 2.5 * chord * za) for xa, za in airfoil] for y, x_le, chord in (inner, outer)]
        connections = [(thick_point(inner, c), thick_point(outer, c)) for c in (0.0, 1.0)]
        construction_panel(
            wing, project_wing, outline, connections, thick_point(inner, 0.6), thick_point(outer, 0.6),
            inner[2], outer[2], np.array([1.0, 0.0, 0.0]), (0.22, 0.5, 0.25), 0.45, {
                "exText": ("$e_x$ (x-axis)", None), "ex": ((4, 0), "left"), "ez": ((0, 7), "center"),
                "ry": ((6, -4), "left"), "ryAt": 0.5, "rx": ((0, -8), "center"), "rz": ((5, 0), "left"),
                "p0": ((-6, 4), "right"), "p1": ((-6, 5), "right"), "p": ((-7, 6), "right")})
        label(wing, project_wing(thick_point(inner, -0.5)), "start profile", (0, -8), va="top", color=INK2)
        label(wing, project_wing(thick_point(outer, 1.0)), "end profile", (6, 0), ha="left", color=INK2)
        wing.set_aspect("equal", adjustable="datalim")
        wing.axis("off")
        wing.set_title("(a) Wing segment")

        # (b) fuselage segment, seen from the side with y running into the depth
        def project_fuselage(p):
            return np.array([p[0] + 0.5 * p[1], p[2] + 0.3 * p[1]])

        front, rear = ("front", 0.0, 1.2), ("rear", 2.6, 1.8)
        cs = np.linspace(0.0, 1.0, 200)
        outline = [[fuselage_point(section, c) for c in cs] for section in (front, rear)]
        connections = [(fuselage_point(front, c), fuselage_point(rear, c)) for c in (0.25, 0.5, 0.75)]
        construction_panel(
            fuselage, project_fuselage, outline, connections, fuselage_point(front, 0.0), fuselage_point(rear, 0.0),
            front[2], rear[2], np.array([0.0, 0.0, 1.0]), (0.2, 0.5, 0.35), 0.7, {
                "exText": ("$e_x$ (z-axis)", None), "ex": ((0, 7), "center"), "ez": ((5, -4), "left"),
                "ry": ((0, -9), "center"), "ryAt": 1.0, "rx": ((-4, 0), "right"), "rz": ((6, -4), "left"),
                "p0": ((-6, 2), "right"), "p1": ((7, 4), "left"), "p": ((0, 9), "center")})
        label(fuselage, project_fuselage(fuselage_point(front, 0.5)), "start profile", (0, -8), va="top",
              color=INK2)
        label(fuselage, project_fuselage(fuselage_point(rear, 0.5)), "end profile", (0, -8), va="top", color=INK2)
        fuselage.set_aspect("equal", adjustable="datalim")
        fuselage.axis("off")
        fuselage.set_title("(b) Fuselage segment")

        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=GUIDE),
                   Line2D([], [], ls="none", marker="D", ms=5.5, color=GUIDE, mec=COLORS["surface"])]
        fig.legend(handles, ["profile", "guide curve", "point P of the guide curve"], loc="lower center", ncol=3,
                   bbox_to_anchor=(0.5, -0.06), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "guideCurveCoordinates.png")


def figure_segments():
    """Planform of the example wing: leading edge smooth over the kink, trailing edge with continuity C0."""
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.4))
        ex = np.array([1.0, 0.0, 0.0])

        def planform(p):  # y to the right, flight direction up
            return np.array([p[1], -p[0]])

        for i in range(len(WING_SECTIONS) - 1):
            for c in (0.0, 1.0):
                a, b = planform(wing_point(WING_SECTIONS[i], c)), planform(wing_point(WING_SECTIONS[i + 1], c))
                ax.plot(*np.array([a, b]).T, color=MUTED, lw=LINE["reference"], zorder=1)
        for name, circumference in (("leadingEdge", 0.0), ("trailingEdgeUpper", 1.0)):
            parts, current = [], []
            for i, (profile_uid, _, to, continuity) in enumerate(WING_GUIDE_CURVES[name]):
                start, end = WING_SECTIONS[i], WING_SECTIONS[i + 1]
                points = list(guide_curve_points(wing_point(start, circumference), wing_point(end, to), start[3],
                                                 end[3], profile_uid, ex))
                if continuity == "C0":
                    parts.append(current)
                    current = []
                current = points if not current else current + points[1:]
            parts.append(current)
            for part in parts:
                ax.plot(*np.array([planform(q) for q in spline(part, 300)]).T, color=GUIDE, zorder=3)
                for q in part[1:-1]:
                    if not any(np.allclose(q, wing_point(s, circumference)) for s in WING_SECTIONS):
                        dot(ax, planform(q), marker="D", color=GUIDE, size=4)
        for section in WING_SECTIONS:
            le, te = planform(wing_point(section, 0.0)), planform(wing_point(section, 1.0))
            ax.plot(*np.array([le, te]).T, color=PROFILE, zorder=2)
            label(ax, le, f"{section[0]} section", (4, 8), ha="left", va="bottom", color=INK2)
        for i in range(len(WING_SECTIONS) - 1):
            a, b = WING_SECTIONS[i], WING_SECTIONS[i + 1]
            middle = 0.5 * (planform(wing_point(a, 1.0)) + planform(wing_point(b, 1.0)))
            label(ax, middle, f"segment {i + 1}", (0, -14), va="top", color=INK2)

        kink = WING_SECTIONS[1]
        label(ax, planform(wing_point(kink, 0.0)), "leading edge without continuity:\nsmooth over the section",
              (-8, -12), ha="right", va="top")
        label(ax, planform(wing_point(kink, 1.0)), "trailing edge with continuity C0:\nmay have a kink at the section",
              (8, 12), ha="left", va="bottom")
        ax.set_aspect("equal")
        ax.axis("off")
        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=GUIDE),
                   Line2D([], [], ls="none", marker="D", ms=4, color=GUIDE, mec=COLORS["surface"]),
                   Line2D([], [], color=MUTED, lw=LINE["reference"])]
        fig.legend(handles, ["profile chord", "guide curve", "guide curve point", "straight connection"],
                   loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.03), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "guideCurveSegments.png")


def figure_profile():
    """The canopy guide curve profile in relative coordinates and as top guide curve of the example fuselage."""
    profile_uid = "GCP_canopy"
    _, rx, ry, rz = GUIDE_CURVE_PROFILES[profile_uid]
    with figure_style():
        fig, (rel, side) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9),
                                        gridspec_kw={"width_ratios": [1.0, 1.25], "wspace": 0.3})

        # (a) guide curve profile: rX over rY, start and end point implied at (0, 0) and (1, 0)
        points = np.array([[0.0, 0.0], *zip(ry, rx, strict=True), [1.0, 0.0]])
        rel.axhline(0.0, color=MUTED, lw=LINE["reference"], zorder=1)
        rel.plot(*spline(points).T, color=GUIDE, zorder=3)
        for y, x in zip(ry, rx, strict=True):
            dot(rel, (y, x), marker="D", color=GUIDE, size=5.5)
            label(rel, (y, x), f"{x:g}", (-7 if y < 0.5 else 7 if y > 0.6 else 0, 7), va="bottom",
                  ha="right" if y < 0.5 else "left" if y > 0.6 else "center")
        for y, text, ha in ((0.0, "start point", "left"), (1.0, "end point", "right")):
            dot(rel, (y, 0.0))
            label(rel, (y, 0.0), text, (0, -8), ha=ha, va="top", color=INK2)
        rel.set_xlim(-0.05, 1.05)
        rel.set_ylim(-0.05, 0.19)
        rel.set_xticks([0.0, *ry, 1.0], ["0", *(f"{v:g}" for v in ry), "1"])
        rel.set_yticks([0.0, 0.05, 0.1, 0.15])
        rel.set_xlabel("rY")
        rel.set_ylabel("rX")
        rel.set_title("(a) Guide curve profile (rZ = 0)")

        # (b) the profile as top guide curve of the front fuselage segment, side view
        front, rear = FUSELAGE_SECTIONS[0], FUSELAGE_SECTIONS[1]
        ex = np.array([0.0, 0.0, 1.0])
        p0, p1 = fuselage_point(front, 0.0), fuselage_point(rear, 0.0)
        curve = guide_curve_points(p0, p1, front[2], rear[2], profile_uid, ex)

        def xz(p):
            return np.array([p[0], p[2]])

        bottom = 0.42  # lower edge of the detail shown; the profiles continue below
        for section in (front, rear):
            top = xz(fuselage_point(section, 0.0))
            side.plot([top[0], top[0]], [top[1], bottom], color=PROFILE, zorder=2)
        side.plot(*np.array([xz(p0), xz(p1)]).T, color=MUTED, lw=LINE["reference"], zorder=1)
        side.plot(*np.array([xz(q) for q in spline(curve)]).T, color=GUIDE, zorder=3)
        for q, b in zip(curve[1:-1], ry, strict=True):
            base = xz(p0 + b * (p1 - p0))
            arrow(side, base, xz(q), color=INK2, lw=LINE["reference"])
            dot(side, xz(q), marker="D", color=GUIDE, size=5.5)
        middle = 1
        base = xz(p0 + ry[middle] * (p1 - p0))
        label(side, 0.5 * (base + xz(curve[middle + 1])), "$r_X\\,s$", (4, 0), ha="left", color=INK2)
        for point, text, offset, ha in ((p0, "$P_0$", (-6, 0), "right"), (p1, "$P_1$", (6, 0), "left")):
            dot(side, xz(point))
            label(side, xz(point), text, offset, ha=ha)
        for section, name, ha, dx in ((front, "start profile", "left", 5), (rear, "end profile", "right", -5)):
            label(side, (section[1], bottom), f"{name}\nheight {section[2]:g}", (dx, 2), ha=ha, va="bottom",
                  color=INK2)
        label(side, (2.0, bottom), "vertical scale exaggerated", (0, -2), va="top", color=INK2)
        side.set_xlim(-0.35, 4.35)
        side.set_ylim(bottom - 0.08, 1.15)
        side.axis("off")
        side.set_title("(b) Top guide curve of a fuselage segment")

        handles = [Line2D([], [], color=PROFILE), Line2D([], [], color=GUIDE),
                   Line2D([], [], ls="none", marker="D", ms=5.5, color=GUIDE, mec=COLORS["surface"]),
                   Line2D([], [], color=MUTED, lw=LINE["reference"])]
        fig.legend(handles, ["profile (side view)", "guide curve", "point of the guide curve profile",
                             "straight connection"], loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.12),
                   handlelength=1.4, columnspacing=1.4)
        save_figure(fig, FIGURES / "guideCurveProfile.png")


# --------------------------------------------------------------------- example
def guide_curve_xml(uid, name, profile_uid, start, to, continuity):
    lines = [f'<guideCurve uID="{uid}">', f"    <name>{name}</name>",
             f"    <guideCurveProfileUID>{profile_uid}</guideCurveProfileUID>"]
    if isinstance(start, str):
        lines.append(f"    <fromGuideCurveUID>{start}</fromGuideCurveUID>")
        if continuity:
            lines.append(f"    <continuity>{continuity}</continuity>")
    else:
        lines.append(f"    <fromRelativeCircumference>{start:g}</fromRelativeCircumference>")
    lines += [f"    <toRelativeCircumference>{to:g}</toRelativeCircumference>", "</guideCurve>"]
    return "\n".join(lines)


def segment_guide_curves(component_uid, curves, segment, readable):
    lines = ["<guideCurves>"]
    for name, parts in curves.items():
        profile_uid, start, to, continuity = parts[segment]
        uid = f"{component_uid}_{name}_{segment + 1}"
        previous = f"{component_uid}_{name}_{segment}" if segment > 0 else start
        lines.append(indent(guide_curve_xml(uid, f"{readable[name]}, segment {segment + 1}", profile_uid,
                                            previous, to, continuity), 1))
    lines.append("</guideCurves>")
    return "\n".join(lines)


def section_xml(uid, name, profile_tag, profile_uid, translation, scaling):
    return "\n".join([
        f'<section uID="{uid}">', f"    <name>{name}</name>",
        indent(transformation_xml(translation=translation), 1),
        "    <elements>", f'        <element uID="{uid}_element">', f"            <name>{name} element</name>",
        f"            <{profile_tag}>{profile_uid}</{profile_tag}>",
        indent(transformation_xml(scaling=scaling), 3),
        "        </element>", "    </elements>", "</section>",
    ])


WING_NAMES = {"leadingEdge": "Leading edge", "trailingEdgeUpper": "Trailing edge, upper side",
              "trailingEdgeLower": "Trailing edge, lower side"}
FUSELAGE_NAMES = {"top": "Top", "right": "Right side", "bottom": "Bottom", "left": "Left side"}


def segment_xml(component_uid, sections, index, guide_curves):
    start, end = sections[index][0], sections[index + 1][0]
    return "\n".join([
        f'<segment uID="{component_uid}_segment{index + 1}">',
        f"    <name>Segment {index + 1}</name>",
        f"    <fromElementUID>{component_uid}_{start}_element</fromElementUID>",
        f"    <toElementUID>{component_uid}_{end}_element</toElementUID>",
        indent(guide_curves, 1),
        "</segment>",
    ])


def component_xml(tag, uid, name, description, sections_xml, segments_xml, attributes=""):
    return "\n".join([
        f'<{tag} uID="{uid}"{attributes}>', f"    <name>{name}</name>", f"    <description>{description}</description>",
        indent(transformation_xml(), 1),
        "    <sections>", *(indent(s, 2) for s in sections_xml), "    </sections>",
        "    <segments>", *(indent(s, 2) for s in segments_xml), "    </segments>",
        f"</{tag}>",
    ])


def wing_xml():
    uid = "GuideCurveWing"
    sections = [section_xml(f"{uid}_{name}", f"{name.capitalize()} section", "airfoilUID", "NACA0012_points",
                            (x, y, 0.0), (chord, 1.0, chord)) for name, y, x, chord in WING_SECTIONS]
    segments = [segment_xml(uid, WING_SECTIONS, i, segment_guide_curves(uid, WING_GUIDE_CURVES, i, WING_NAMES))
                for i in range(len(WING_SECTIONS) - 1)]
    return component_xml("wing", uid, "Wing with guide curves",
                         "Leading edge moved forward in the inner segment and continued smoothly; trailing edge "
                         "moved backward in the outer segment with a kink (continuity C0) at the kink section.",
                         sections, segments, ' symmetry="x-z-plane"')


def fuselage_xml():
    uid = "GuideCurveFuselage"
    sections = [section_xml(f"{uid}_{name}", f"{name.capitalize()} section", "profileUID", "CircleProfile",
                            (x, 0.0, 0.0), (1.0, d, d)) for name, x, d in FUSELAGE_SECTIONS]
    segments = [segment_xml(uid, FUSELAGE_SECTIONS, i,
                            segment_guide_curves(uid, FUSELAGE_GUIDE_CURVES, i, FUSELAGE_NAMES))
                for i in range(len(FUSELAGE_SECTIONS) - 1)]
    return component_xml("fuselage", uid, "Fuselage with guide curves",
                         "Circular profiles with guide curves at top, sides and bottom; the top guide curve forms "
                         "a canopy hump in the front segment.", sections, segments)


def guide_curve_profile_xml(uid):
    name, rx, ry, rz = GUIDE_CURVE_PROFILES[uid]
    return "\n".join([
        f'<guideCurveProfile uID="{uid}">', f"    <name>{name}</name>", "    <pointList>",
        f"        <rX>{vector(rx)}</rX>", f"        <rY>{vector(ry)}</rY>", f"        <rZ>{vector(rz)}</rZ>",
        "    </pointList>", "</guideCurveProfile>",
    ])


def airfoil_xml():
    xs, zs = airfoil_points_xml()
    return "\n".join([
        '<wingAirfoil uID="NACA0012_points">', "    <name>NACA 0012 with closed trailing edge</name>",
        "    <pointList>", f"        <x>{vector(xs)}</x>", f"        <y>{vector([0.0] * len(xs))}</y>",
        f"        <z>{vector(zs)}</z>", "    </pointList>", "</wingAirfoil>",
    ])


def circle_profile_xml():
    return "\n".join([
        '<fuselageProfile uID="CircleProfile">', "    <name>Circle</name>", "    <standardProfile>",
        "        <superEllipse>", "            <mUpper>2</mUpper>", "            <nUpper>2</nUpper>",
        "            <mLower>2</mLower>", "            <nLower>2</nLower>",
        "            <lowerHeightFraction>0.5</lowerHeightFraction>", "        </superEllipse>",
        "    </standardProfile>", "</fuselageProfile>",
    ])


def excerpt_segments_xml():
    """Wing segments with the leading edge and upper trailing edge guide curves."""
    uid = "GuideCurveWing"
    shown = {k: WING_GUIDE_CURVES[k] for k in ("leadingEdge", "trailingEdgeUpper")}
    lines = ["<segments>"]
    for i in range(len(WING_SECTIONS) - 1):
        start, end = WING_SECTIONS[i][0], WING_SECTIONS[i + 1][0]
        guide_curves = segment_guide_curves(uid, shown, i, WING_NAMES).splitlines()
        guide_curves.insert(-1, "    ...")
        lines += [
            f'    <segment uID="{uid}_segment{i + 1}">',
            f"        <name>Segment {i + 1}</name>",
            f"        <fromElementUID>{uid}_{start}_element</fromElementUID>",
            f"        <toElementUID>{uid}_{end}_element</toElementUID>",
            indent("\n".join(guide_curves), 2),
            "    </segment>",
        ]
    lines.append("</segments>")
    return "\n".join(lines)


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Guide curves",
        description="A wing and a fuselage whose surfaces are shaped by guide curves.",
        model_uid="GuideCurveAircraft",
        model_name="Guide curve example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml())],
        extra_profiles=[("wingAirfoils", airfoil_xml()),
                        ("guideCurves", "\n".join(guide_curve_profile_xml(u) for u in GUIDE_CURVE_PROFILES))],
    )


# ------------------------------------------------------------------------ main
def main():
    save_equation(EQUATION_LINES, EQUATIONS / "guideCurvePoint")
    figure_coordinates()
    figure_segments()
    figure_profile()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the guideCurveType documentation:\n")
    print(excerpt_segments_xml())
    print("\nExcerpt for the guideCurveProfileGeometryType documentation:\n")
    profiles = "\n".join(guide_curve_profile_xml(uid) for uid in ("GCP_straight", "GCP_canopy"))
    print("<guideCurves>\n" + indent(profiles, 1) + "\n    ...\n</guideCurves>")


if __name__ == "__main__":
    main()

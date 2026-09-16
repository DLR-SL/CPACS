# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of two-dimensional profiles
(profileGeometry2DType), e.g. nacelle profiles and curve profiles.

Run from the repository root:

    uv run documentation/scripts/profileGeometry2D.py

The script writes

    documentation/figures/profileGeometry2D.png
    documentation/figures/profileGeometry2DNacelle.png
    examples/nacelleProfiles.xml

and prints the excerpt shown in the documentation. The schema documentation is
not written by this script; copy the printed excerpt there when the example changes.

Definitions shown (as in the documentation):
- A closed profile runs from the trailing edge along the lower side to the leading edge
  and along the upper side back to the trailing edge (clockwise with x to the right and
  y upwards). The relative coordinate zeta is -1 at the first point, 0 at the leading
  edge and +1 at the last point; it is proportional to the arc length on the lower side
  (zeta in [-1, 0]) and on the upper side (zeta in [0, 1]).
- A curve runs through its points from the first to the last point.
- In a nacelle section at angle phi, +x of the profile points along +x of the nacelle and
  +y of the profile radially away from the nacelle axis; the lower side faces the axis.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from example_xml import indent, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_figure
from nacaProfile import naca4

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "nacelleProfiles.xml"

CURVE = COLORS["series1"]
SECOND = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
NACA_CODE = "4412"  # cambered, so that the outer (upper) side bulges out like a nacelle lip
POINTS_PER_SIDE = 7  # including the leading edge
PROFILE_UID = "NacelleProfile_points"
CURVE_UID = "RotationCurve_points"
# nacelle section of the example: angle about the nacelle axis [deg], radius and chord [m]
SECTIONS = [("top", 0.0), ("right", 90.0), ("bottom", 180.0), ("left", 270.0)]
RADIUS = 0.6
CHORD = 2.0
# rotation curve of the example: zeta range replaced by the surface of revolution
ROTATION_CURVE = {"startZeta": -0.8, "endZeta": -0.3, "startZetaBlending": -0.9, "endZetaBlending": -0.2}


def sides(n):
    """Lower side (trailing edge -> leading edge) and upper side (leading edge -> trailing edge)."""
    x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n)))
    (xu, yu), (xl, yl), _, _ = naca4(NACA_CODE, x, 0.0)
    lower = np.column_stack([xl, yl])[::-1]
    upper = np.column_stack([xu, yu])
    return lower, upper


def profile_points():
    lower, upper = sides(POINTS_PER_SIDE)
    points = np.vstack([lower, upper[1:]])
    return np.round(points, 4) + 0.0


def curve_points():
    """The lower side of the profile, from the trailing edge to the leading edge."""
    return profile_points()[:POINTS_PER_SIDE]


def along(polyline, fraction):
    steps = np.hypot(*np.diff(polyline, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(steps)])
    return np.array([np.interp(fraction * s[-1], s, polyline[:, i]) for i in range(2)])


DENSE_LOWER, DENSE_UPPER = sides(400)


def zeta_point(zeta):
    """Point of the profile at the relative coordinate zeta (arc length on lower and upper side)."""
    return along(DENSE_LOWER, zeta + 1.0) if zeta <= 0.0 else along(DENSE_UPPER, zeta)


def section_transform(points, angle_deg):
    """Profile (x, y) -> nacelle (x, z) in the plane of a section at the given angle, seen from the side."""
    phi = np.radians(angle_deg)
    radial = RADIUS + CHORD * points[:, 1]
    return np.column_stack([CHORD * points[:, 0], np.cos(phi) * radial])


# --------------------------------------------------------------------- figures
def label(ax, xy, text, offset=(0, 0), ha="center", va="center", color=INK, **kwargs):
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=color,
                zorder=7, **kwargs)


def dot(ax, xy, color=INK, size=4.5, marker="o"):
    ax.plot(*xy, ls="none", marker=marker, ms=size, color=color, mec=COLORS["surface"], mew=1.0, zorder=6)


def order_arrow(ax, start, end, rad):
    ax.annotate("", xy=end, xytext=start, zorder=5, arrowprops={
        "arrowstyle": "-|>", "lw": LINE["secondary"], "mutation_scale": 8, "color": INK2,
        "connectionstyle": f"arc3,rad={rad}", "shrinkA": 0, "shrinkB": 0})


def figure_profile():
    points = profile_points()
    curve = curve_points()
    dense = np.vstack([DENSE_LOWER, DENSE_UPPER[1:]])
    n = len(points)
    le = POINTS_PER_SIDE - 1
    with figure_style():
        fig, (closed, open_) = plt.subplots(2, 1, figsize=(FULL_WIDTH, 5.6),
                                            gridspec_kw={"hspace": 0.35, "height_ratios": [1.45, 1.0]})

        # (a) closed profile
        closed.fill(*dense.T, color=CURVE, alpha=0.08, lw=0)
        closed.plot(*dense.T, color=CURVE, zorder=3)
        closed.plot([0.0, 1.0], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=2)
        label(closed, (0.62, 0.0), "chord line", (0, 4), va="bottom", color=INK2)
        for p in points:
            dot(closed, p)
        label(closed, points[0], f"points 1 and {n}: trailing edge\nζ = −1 at point 1, ζ = +1 at point {n}", (8, 0),
              ha="left")
        label(closed, points[le], f"point {le + 1}: leading edge\nζ = 0", (-8, 0), ha="right")
        for zeta, offset, va in ((-0.5, (70, -22), "top"), (0.5, (70, 18), "bottom")):
            p = zeta_point(zeta)
            dot(closed, p, color=SECOND, size=5.5, marker="D")
            label(closed, p, f"ζ = {zeta:g}", offset, ha="left", va=va, arrowprops=leader())
        label(closed, zeta_point(0.2), "upper side", (-8, 8), ha="right", va="bottom", color=INK2)
        label(closed, zeta_point(-0.2), "lower side", (-8, -8), ha="right", va="top", color=INK2)
        order_arrow(closed, (0.8, -0.075), (0.3, -0.09), -0.12)
        label(closed, (0.55, -0.095), "point order", (0, -10), va="top", color=INK2)
        closed.set_aspect(2.5)
        closed.set_xlim(-0.5, 1.9)
        closed.set_ylim(-0.16, 0.14)
        closed.set_xticks([0.0, 0.5, 1.0])
        closed.set_yticks([-0.1, 0.0, 0.1])
        closed.set_xlabel("x")
        closed.set_ylabel("y")
        closed.set_title("(a) Closed profile (y stretched)")

        # (b) curve through the lower side of the profile
        x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 200)))
        _, (xl, yl), _, _ = naca4(NACA_CODE, x, 0.0)
        open_.plot(xl, yl, color=CURVE, zorder=3)
        for p in curve:
            dot(open_, p)
        label(open_, curve[0], "point 1: first point", (8, 0), ha="left")
        label(open_, curve[-1], f"point {len(curve)}: last point", (-8, 0), ha="right")
        order_arrow(open_, (0.8, -0.045), (0.3, -0.06), -0.12)
        label(open_, (0.55, -0.065), "point order", (0, -10), va="top", color=INK2)
        open_.set_aspect(2.5)
        open_.set_xlim(-0.5, 1.9)
        open_.set_ylim(-0.11, 0.05)
        open_.set_xticks([0.0, 0.5, 1.0])
        open_.set_yticks([-0.1, 0.0])
        open_.set_xlabel("x")
        open_.set_ylabel("y")
        open_.set_title("(b) Curve (y stretched)")
        save_figure(fig, FIGURES / "profileGeometry2D.png")


def figure_nacelle():
    """Side view of the nacelle: the sections at 0 and 180 degrees in the x-z plane."""
    dense = np.vstack([DENSE_LOWER, DENSE_UPPER[1:]])
    arrow_length = 0.4
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.2))
        ax.plot([-0.3, CHORD + 0.3], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=1)
        label(ax, (-0.3, 0.0), "nacelle axis", (-4, 0), ha="right", color=INK2)
        for angle in (0.0, 180.0):
            sign = np.cos(np.radians(angle))
            shape = section_transform(dense, angle)
            ax.fill(*shape.T, color=CURVE, alpha=0.08, lw=0)
            ax.plot(*shape.T, color=CURVE, zorder=3)
            ax.plot(*section_transform(DENSE_LOWER, angle).T, color=SECOND, zorder=4)
            le = section_transform(np.array([[0.0, 0.0]]), angle)[0]
            for direction, text, offset, ha, va in (
                    ((1.0, 0.0), "$x_\\mathrm{profile}$", (4, 0), "left", "center"),
                    ((0.0, sign), "$y_\\mathrm{profile}$", (-4, 0), "right", "center")):
                tip = le + arrow_length * np.array(direction)
                ax.plot(*np.array([le, tip]).T, alpha=0)
                ax.annotate("", xy=tip, xytext=le, zorder=5, arrowprops={
                    "arrowstyle": "-|>", "lw": LINE["secondary"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
                    "color": INK})
                label(ax, tip, text, offset, ha=ha, va=va)
            label(ax, section_transform(np.array([[1.0, 0.0]]), angle)[0], f"section at {angle:g}°", (8, 0),
                  ha="left")
        zeta_label = -0.45
        text_at = (section_transform(np.array([zeta_point(zeta_label)]), 0.0)[0][0], 0.27)
        for angle in (0.0, 180.0):
            ax.annotate("lower side (ζ from −1 to 0) faces the nacelle axis" if angle == 0.0 else "",
                        xy=section_transform(np.array([zeta_point(zeta_label)]), angle)[0], xytext=text_at,
                        textcoords="data", ha="center", va="center", fontsize=NOTE, arrowprops=leader(), zorder=7)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "profileGeometry2DNacelle.png")


# --------------------------------------------------------------------- example
def profile_xml(tag, uid, name, points):
    return "\n".join([
        f'<{tag} uID="{uid}">', f"    <name>{name}</name>", "    <pointList>",
        f"        <x>{vector(points[:, 0])}</x>", f"        <y>{vector(points[:, 1])}</y>",
        "    </pointList>", f"</{tag}>",
    ])


def nacelle_profile_xml():
    return profile_xml("nacelleProfile", PROFILE_UID, f"NACA {NACA_CODE}, {len(profile_points())} points",
                       profile_points())


def curve_profile_xml():
    return profile_xml("curveProfile", CURVE_UID, "Lower side of the nacelle profile", curve_points())


def section_xml(name, angle):
    return "\n".join([
        f'<section uID="ExampleEngine_fanCowl_{name}">', f"    <name>Section at {angle:g} deg</name>",
        "    <transformation>", "        <scaling>", f"            <x>{CHORD:g}</x>", f"            <y>{CHORD:g}</y>",
        f"            <z>{CHORD:g}</z>", "        </scaling>", "        <translation>",
        f"            <x>{angle:g}</x>", "            <y>0</y>", f"            <z>{RADIUS:g}</z>",
        "        </translation>", "    </transformation>", f"    <profileUID>{PROFILE_UID}</profileUID>",
        "</section>",
    ])


def engine_xml():
    rc = ROTATION_CURVE
    return "\n".join([
        '<engine uID="ExampleEngine">', "    <name>Engine with a nacelle built from nacelle and curve profiles</name>",
        '    <nacelle uID="ExampleEngine_nacelle">', '        <fanCowl uID="ExampleEngine_fanCowl">',
        "            <sections>", *(indent(section_xml(n, a), 4) for n, a in SECTIONS), "            </sections>",
        '            <rotationCurve uID="ExampleEngine_fanCowl_rotationCurve">',
        f"                <referenceSectionUID>ExampleEngine_fanCowl_{SECTIONS[0][0]}</referenceSectionUID>",
        f"                <curveProfileUID>{CURVE_UID}</curveProfileUID>",
        *(f"                <{key}>{value:g}</{key}>" for key, value in rc.items()),
        "            </rotationCurve>", "        </fanCowl>", "    </nacelle>", "</engine>",
    ])


MODEL_UID = "NacelleProfileAircraft"


def engine_position_xml():
    return "\n".join([
        '<engine uID="ExampleEngine_installed">', "    <name>Installed example engine</name>",
        "    <engineUID>ExampleEngine</engineUID>",
        "    <!--",
        "        An engine is mounted to a component, e.g. a wing or an engine pylon, which should be referenced here.",
        "        For the sake of clarity, this example contains no such component and references the aircraft model",
        "        instead, so that the nacelle can be displayed and its parameters can be varied, e.g. in TiGL.",
        "    -->",
        f"    <parentUID>{MODEL_UID}</parentUID>",
        "    <transformation>", "        <translation>", "            <x>0</x>", "            <y>0</y>",
        "            <z>0</z>", "        </translation>", "    </transformation>", "</engine>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Nacelle and curve profiles",
        description="A nacelle profile and a curve profile, used by the fan cowl of an engine nacelle.",
        model_uid=MODEL_UID,
        model_name="Nacelle profile example",
        components_tag="engines",
        components=engine_position_xml(),
        profiles_tag="curveProfiles",
        profiles=curve_profile_xml(),
        extra_profiles=[("nacelleProfiles", nacelle_profile_xml())],
        extra_vehicles=[("engines", engine_xml())],
    )


def excerpt_xml():
    return "\n".join(["<profiles>", "    <curveProfiles>", indent(curve_profile_xml(), 2), "    </curveProfiles>",
                      "    <nacelleProfiles>", indent(nacelle_profile_xml(), 2), "    </nacelleProfiles>",
                      "</profiles>"])


# ------------------------------------------------------------------------ main
def main():
    figure_profile()
    figure_nacelle()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the profileGeometry2DType documentation:\n")
    print(excerpt_xml())


if __name__ == "__main__":
    main()

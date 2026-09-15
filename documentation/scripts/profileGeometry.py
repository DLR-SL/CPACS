# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the point order of profiles (profileGeometryType) and the
relative circumference of guide curves (guideCurveProfileGeometryType).

Run from the repository root:

    uv run documentation/scripts/profileGeometry.py

The script writes

    documentation/figures/profilePointOrder.png
    documentation/figures/guideCurveCircumference.png
    examples/profiles_pointOrder.xml

and prints the profiles excerpt shown in the profileGeometryType documentation.
The schema documentation is not written by this script; copy the printed excerpt
there when the example changes.

Point order shown (as defined in the documentation): plotted with the horizontal
profile axis to the right and z upwards, the points run clockwise. A wing profile
starts at the trailing edge and runs along the lower side; a fuselage profile
starts at its highest point and runs over the positive y side first.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

from example_xml import indent, transformation_xml, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure
from standardProfile import SuperEllipse

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "profiles_pointOrder.xml"

CURVE = COLORS["series1"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# The fuselage point list samples this superellipse, so that the example fuselage can
# connect it with the superellipse itself.
FUSELAGE_SHAPE = SuperEllipse("FuselageProfile_points", "Fuselage profile, point list", 2, 2, 2.5, 2, 0.4)
AIRFOIL_THICKNESS = 0.12


# ---------------------------------------------------------------------- shapes
def naca00xx(x, thickness=AIRFOIL_THICKNESS):
    """Half thickness of a symmetric NACA 4-digit airfoil with closed trailing edge."""
    return 5 * thickness * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)


def airfoil_points():
    """13 points: trailing edge, lower side, leading edge (point 7), upper side, trailing edge."""
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, 7)))  # 1 ... 0
    lower = [(xi, -naca00xx(xi)) for xi in x]
    upper = [(xi, naca00xx(xi)) for xi in x[::-1][1:]]
    return [(round(float(a), 4) + 0.0, round(float(b), 4) + 0.0) for a, b in lower + upper]


def airfoil_curve():
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, 200)))
    return np.concatenate([x, x[::-1]]), np.concatenate([-naca00xx(x), naca00xx(x[::-1])])


def fuselage_points():
    """13 points of FUSELAGE_SHAPE: top, right side (widest point is point 4), bottom (7), left side, top."""
    shape = FUSELAGE_SHAPE
    right = [(0.0, 0.5)]
    for y in (0.3, 0.45):
        right.append((y, float(shape.z(y, True))))
    right.append((0.5, shape.z0))
    for y in (0.45, 0.3):
        right.append((y, float(shape.z(y, False))))
    right.append((0.0, -0.5))
    left = [(-y, z) for y, z in right[-2::-1]]
    return [(round(y, 4) + 0.0, round(z, 4) + 0.0) for y, z in right + left]


WIDEST_INDICES = [4, 10]  # given the parameters of the superellipse's widest points


# --------------------------------------------------------------------- figures
def numbered_points(ax, points, positions):
    for index, (a, b) in enumerate(points[:-1], start=1):
        ax.plot(a, b, ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"], mew=1.0, zorder=4)
        if index in positions:
            text, dx, dy, ha, va = positions[index]
            ax.text(a + dx, b + dy, text, fontsize=NOTE, ha=ha, va=va)


def order_arrow(ax, start, end, rad):
    ax.add_patch(FancyArrowPatch(start, end, connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
                                 mutation_scale=8, lw=LINE["secondary"], color=INK2))


def figure_point_order():
    with figure_style():
        fig, (wing, fuselage) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.8),
                                             gridspec_kw={"width_ratios": [1.45, 1.0], "wspace": 0.32})

        # (a) wing profile in the x-z plane
        cx, cz = airfoil_curve()
        wing.fill(cx, cz, color=CURVE, alpha=0.08, lw=0)
        wing.plot(cx, cz, color=CURVE)
        points = airfoil_points()
        positions = {
            1: ("1, 13\n(trailing edge)", 0.04, 0.0, "left", "center"),
            4: ("4", 0.0, -0.012, "center", "top"),
            7: ("7\n(leading edge)", -0.04, 0.0, "right", "center"),
            10: ("10", 0.0, 0.012, "center", "bottom"),
        }
        numbered_points(wing, points, positions)
        order_arrow(wing, (0.9, -0.06), (0.35, -0.09), -0.08)
        wing.text(0.62, -0.1, "point order", fontsize=NOTE, color=INK2, ha="center", va="top")
        # z is stretched, so that the thin airfoil and its points stay readable
        wing.set_xlim(-0.6, 1.42)
        wing.set_ylim(-0.17, 0.12)
        wing.set_xticks([0.0, 0.5, 1.0])
        wing.set_yticks([-0.1, 0.0, 0.1])
        wing.set_xlabel("x")
        wing.set_ylabel("z")
        wing.set_title("(a) Wing profile, x to the right (z stretched)")

        # (b) fuselage profile in the y-z plane, viewed from behind
        (ur, ul), (lr, ll) = FUSELAGE_SHAPE.half(True), FUSELAGE_SHAPE.half(False)
        contour = FUSELAGE_SHAPE.contour()
        fuselage.fill(contour[:, 0], contour[:, 1], color=CURVE, alpha=0.08, lw=0)
        fuselage.plot(contour[:, 0], contour[:, 1], color=CURVE)
        points = fuselage_points()
        positions = {
            1: ("1, 13 (highest point)", 0.0, 0.07, "center", "bottom"),
            4: ("4", 0.06, 0.0, "left", "center"),
            7: ("7 (lowest point)", 0.0, -0.07, "center", "top"),
            10: ("10", -0.06, 0.0, "right", "center"),
        }
        numbered_points(fuselage, points, positions)
        order_arrow(fuselage, (0.1, 0.32), (0.36, 0.02), -0.3)
        fuselage.text(0.02, 0.2, "point\norder", fontsize=NOTE, color=INK2, ha="right", va="center")
        fuselage.set_aspect("equal")
        fuselage.set_xlim(-0.8, 0.8)
        fuselage.set_ylim(-0.72, 0.72)
        fuselage.set_xticks([-0.5, 0.0, 0.5])
        fuselage.set_yticks([-0.5, 0.0, 0.5])
        fuselage.set_xlabel("y")
        fuselage.set_ylabel("z")
        fuselage.set_title("(b) Fuselage profile, y to the right")

        save_figure(fig, FIGURES / "profilePointOrder.png")


def figure_guide_curve_circumference():
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.6),
                                 gridspec_kw={"width_ratios": [1.5, 1.0, 1.0], "wspace": 0.25})

        # (a) wing profile: -1 at the trailing edge of the lower side, 0 at the leading edge, 1 upper side
        ax = axes[0]
        cx, cz = airfoil_curve()
        ax.plot(cx, cz, color=CURVE)
        for x, z, text, ha, va in ((1.0, 0.0, "−1 and 1", "left", "center"), (0.0, 0.0, "0", "right", "center")):
            ax.plot(x, z, ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"], mew=1.0, zorder=4)
            ax.text(x + (0.04 if ha == "left" else -0.04), z, text, fontsize=NOTE, ha=ha, va=va)
        ax.text(0.5, -0.19, "lower side: −1 … 0", fontsize=NOTE, ha="center", va="top")
        ax.text(0.5, 0.19, "upper side: 0 … 1", fontsize=NOTE, ha="center", va="bottom")
        order_arrow(ax, (0.75, -0.12), (0.25, -0.12), 0.0)
        order_arrow(ax, (0.25, 0.12), (0.75, 0.12), 0.0)
        ax.set_aspect("equal")
        ax.set_xlim(-0.2, 1.35)
        ax.set_ylim(-0.32, 0.32)
        ax.axis("off")
        ax.set_title("(a) Wing profile")

        # (b) full and (c) half fuselage profile, here circles of diameter 1
        angle = np.linspace(0.0, 2.0 * np.pi, 400)
        for ax, full in ((axes[1], True), (axes[2], False)):
            shown = angle if full else angle[angle <= np.pi]
            ax.plot(0.5 * np.sin(shown), 0.5 * np.cos(shown), color=CURVE)
            if not full:
                ax.plot([0.0, 0.0], [-0.5, 0.5], color=MUTED, lw=LINE["reference"])
                ax.text(-0.04, 0.0, "symmetry\nplane", fontsize=NOTE, color=INK2, ha="right", va="center")
            marks = ((0.0, "0" if not full else "0 and 1"), (0.5, "0.5"), (1.0, "1")) if not full else \
                ((0.0, "0 and 1"), (0.25, "0.25"), (0.5, "0.5"), (0.75, "0.75"))
            for c, text in marks:
                a = (2.0 * np.pi if full else np.pi) * c
                y, z = 0.5 * np.sin(a), 0.5 * np.cos(a)
                ax.plot(y, z, ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"], mew=1.0, zorder=4)
                ax.text(1.22 * y + (0.0 if abs(y) < 1e-9 else 0.03 * np.sign(y)), 1.25 * z, text, fontsize=NOTE,
                        ha="center" if abs(y) < 1e-9 else ("left" if y > 0 else "right"), va="center")
            order_arrow(ax, (0.12, 0.38), (0.38, 0.12), -0.25)
            ax.set_aspect("equal")
            ax.set_xlim(-0.85, 0.85)
            ax.set_ylim(-0.75, 0.75)
            ax.axis("off")
            ax.set_title("(b) Fuselage profile" if full else "(c) Half fuselage profile")

        save_figure(fig, FIGURES / "guideCurveCircumference.png")


# --------------------------------------------------------------------- example
def wing_airfoil_xml():
    points = airfoil_points()
    return "\n".join([
        '<wingAirfoil uID="NACA0012_points">',
        "    <name>NACA 0012, 13 points</name>",
        "    <pointList>",
        f"        <x>{vector(x for x, _ in points)}</x>",
        f"        <y>{vector([0.0] * len(points))}</y>",
        f"        <z>{vector(z for _, z in points)}</z>",
        "    </pointList>",
        "</wingAirfoil>",
    ])


def fuselage_profile_xml(tigl_workaround=False):
    """fuselageProfile element; with tigl_workaround the point indices are counted from 0 as TiGL 3.5
    reads them, and the CPACS-conform indices are kept in a comment (see curvePointListXYZ.py)."""
    points = fuselage_points()
    lines = [
        f'<fuselageProfile uID="{FUSELAGE_SHAPE.uid}">',
        f"    <name>{FUSELAGE_SHAPE.name}</name>",
        "    <pointList>",
        f"        <x>{vector([0.0] * len(points))}</x>",
        f"        <y>{vector(y for y, _ in points)}</y>",
        f"        <z>{vector(z for _, z in points)}</z>",
        "        <parameterMap>",
    ]
    if tigl_workaround:
        lines += [
            "            <!-- TiGL workaround: CPACS counts point indices from 1, but TiGL 3.5 reads",
            "                 parameterMap/pointIndices counted from 0. The indices below are therefore reduced by 1,",
            "                 so that TiGL shows the geometry described in the documentation. CPACS-conform is:",
            f"                 <pointIndices>{vector(WIDEST_INDICES)}</pointIndices>",
            "                 Restore this value once TiGL counts from 1. -->",
        ]
    offset = 1 if tigl_workaround else 0
    lines += [
        f"            <pointIndices>{vector(i - offset for i in WIDEST_INDICES)}</pointIndices>",
        "            <paramOnCurve>0.25;0.75</paramOnCurve>",
        "        </parameterMap>",
        "    </pointList>",
        "</fuselageProfile>",
    ]
    return "\n".join(lines)


def super_ellipse_profile_xml():
    shape = SuperEllipse("FuselageProfile_superEllipse", "Fuselage profile, superellipse",
                         FUSELAGE_SHAPE.m_upper, FUSELAGE_SHAPE.n_upper, FUSELAGE_SHAPE.m_lower,
                         FUSELAGE_SHAPE.n_lower, FUSELAGE_SHAPE.lower_height_fraction)
    return "\n".join([
        f'<fuselageProfile uID="{shape.uid}">',
        f"    <name>{shape.name}</name>",
        "    <standardProfile>",
        indent(shape.xml(), 2),
        "    </standardProfile>",
        "</fuselageProfile>",
    ])


def excerpt_xml():
    return "\n".join([
        "<profiles>",
        "    <wingAirfoils>",
        indent(wing_airfoil_xml(), 2),
        "    </wingAirfoils>",
        "    <fuselageProfiles>",
        indent(fuselage_profile_xml(), 2),
        "    </fuselageProfiles>",
        "</profiles>",
    ])


def section_xml(uid, name, profile_tag, profile_uid, translation, scaling):
    return "\n".join([
        f'<section uID="{uid}">',
        f"    <name>{name}</name>",
        indent(transformation_xml(translation=translation), 1),
        "    <elements>",
        f'        <element uID="{uid}_element">',
        f"            <name>{name} element</name>",
        f"            <{profile_tag}>{profile_uid}</{profile_tag}>",
        indent(transformation_xml(scaling=scaling), 3),
        "        </element>",
        "    </elements>",
        "</section>",
    ])


def component_xml(tag, uid, name, description, sections, profile_tag, extra_attributes=""):
    lines = [
        f'<{tag} uID="{uid}"{extra_attributes}>',
        f"    <name>{name}</name>",
        f"    <description>{description}</description>",
        indent(transformation_xml(), 1),
        "    <sections>",
    ]
    lines += [indent(section_xml(s_uid, s_name, profile_tag, p_uid, translation, scaling), 2)
              for s_uid, s_name, p_uid, translation, scaling in sections]
    lines += [
        "    </sections>",
        "    <segments>",
        f'        <segment uID="{uid}_segment">',
        "            <name>Segment</name>",
        f"            <fromElementUID>{sections[0][0]}_element</fromElementUID>",
        f"            <toElementUID>{sections[1][0]}_element</toElementUID>",
        "        </segment>",
        "    </segments>",
        f"</{tag}>",
    ]
    return "\n".join(lines)


def write_example():
    fuselage = component_xml(
        "fuselage", "PointOrderFuselage", "Fuselage combining a point list and a superellipse",
        "Front: point list sampled from the superellipse at the rear, both scaled to 2 m. Since both profiles start "
        "at the top and run over the positive y side first, and the point list gives its widest points the "
        "parameters 0.25 and 0.75, the loft connects corresponding points and has a constant cross section.",
        [("PointOrderFuselage_front", "Front section", FUSELAGE_SHAPE.uid, (0.0, 0.0, 0.0), (1.0, 2.0, 2.0)),
         ("PointOrderFuselage_rear", "Rear section", "FuselageProfile_superEllipse", (5.0, 0.0, 0.0),
          (1.0, 2.0, 2.0))],
        "profileUID",
    )
    wing = component_xml(
        "wing", "PointOrderWing", "Wing with a point list airfoil",
        "Rectangular wing with the NACA 0012 point list of the documentation, chord 1.5 m, semi-span 4 m.",
        [("PointOrderWing_root", "Root section", "NACA0012_points", (1.0, 1.0, 0.5), (1.5, 1.0, 1.5)),
         ("PointOrderWing_tip", "Tip section", "NACA0012_points", (1.0, 5.0, 0.5), (1.5, 1.0, 1.5))],
        "airfoilUID", ' symmetry="x-z-plane"',
    )
    # One CPACS file with both profile collections: written via write_cpacs_file for the
    # fuselage part, with the wing and the airfoil inserted into the same model and profiles.
    write_cpacs_file(
        EXAMPLE_FILE,
        name="Point order of profiles",
        description="Wing airfoil and fuselage profile defined by point lists in the order of the documentation, "
        "a superellipse fuselage profile, and a wing and a fuselage using them. "
        "The point indices are written for TiGL 3.5, which counts them from 0; see the comment in the profile. "
        "Generated by documentation/scripts/profileGeometry.py.",
        model_uid="PointOrderAircraft",
        model_name="Point order example",
        components_tag="fuselages",
        components=fuselage,
        profiles_tag="fuselageProfiles",
        profiles="\n".join([fuselage_profile_xml(tigl_workaround=True), super_ellipse_profile_xml()]),
    )
    text = EXAMPLE_FILE.read_text(encoding="utf-8")
    text = text.replace("                </fuselages>\n",
                        "                </fuselages>\n                <wings>\n" + indent(wing, 5) +
                        "\n                </wings>\n", 1)
    text = text.replace("        <profiles>\n",
                        "        <profiles>\n            <wingAirfoils>\n" + indent(wing_airfoil_xml(), 4) +
                        "\n            </wingAirfoils>\n", 1)
    EXAMPLE_FILE.write_text(text, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------ main
def main():
    figure_point_order()
    figure_guide_curve_circumference()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the profileGeometryType documentation:\n")
    print(excerpt_xml())


if __name__ == "__main__":
    main()

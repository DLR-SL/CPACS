# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure and example data for the documentation of curvePointListXYZType.

Run from the repository root:

    uv run documentation/scripts/curvePointListXYZ.py

The script writes

    documentation/figures/curvePointListXYZ.png
    examples/fuselageProfiles_pointList.xml

and prints the fuselageProfile excerpt shown in the curvePointListXYZType
documentation. The excerpt is CPACS-conform; in the example file the point
indices are counted from 0 as TiGL 3.5 reads them, with the CPACS-conform values
in a comment (see fuselage_profile_xml). The schema documentation is not written by this script; copy the
printed excerpt there when the example changes.

The example is a fuselage profile with a flat cabin floor: a straight floor
between two kinks and a circular arc above it. Point indices in CPACS start at 1.
"""

from __future__ import annotations

from math import atan2, cos, pi, sin
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

from example_xml import indent, transformation_xml, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageProfiles_pointList.xml"

CURVE = COLORS["series1"]
KINK = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]

# Curve parameters of the point list: arc (1-5), floor (5-9) and arc (9-13).
# Points 5, 7 and 9 are the ones listed in the parameter map.
KINK_INDICES = [5, 9]
MAPPED_INDICES = [5, 7, 9]
MAPPED_PARAMETERS = [0.4, 0.5, 0.6]
POINT_PARAMETERS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0]

# Floor half-widths of the two profiles; both are 2 high (z from -1 to 1).
WIDE, NARROW = 0.8, 0.4


def profile_point(t, floor_half_width):
    """Point (y, z) at curve parameter t of the floor profile.

    The profile starts at the top (t = 0) and runs down the arc on the positive y
    side to the right corner (t = 0.4), along the floor over the bottom center
    (t = 0.5) to the left corner (t = 0.6) and up the arc back to the top (t = 1).
    Between these points, t is proportional to the arc angle or the floor length.
    """
    if t > 0.5:  # mirror image of the first half
        y, z = profile_point(1.0 - t, floor_half_width)
        return -y, z
    w = floor_half_width
    center = -w * w / 4.0  # circle through both corners (±w, -1) and the top (0, 1)
    radius = 1.0 - center
    corner = atan2(-1.0 - center, w)
    if t >= 0.4:
        return w * (0.5 - t) / 0.1, -1.0
    angle = pi / 2 - (pi / 2 - corner) * t / 0.4
    return radius * cos(angle), center + radius * sin(angle)


def point_list(floor_half_width):
    points = [profile_point(t, floor_half_width) for t in POINT_PARAMETERS]
    # rounded, and -0 written as 0
    return [(round(y, 4) + 0.0, round(z, 4) + 0.0) for y, z in points]


# ----------------------------------------------------------------------- figure
def figure():
    ts = np.linspace(0.0, 1.0, 801)
    note = FONT_SIZE["annotation"]

    with figure_style():
        fig, (ax, loft) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.1), gridspec_kw={"width_ratios": [1.0, 1.25]})

        # ------------------------------------------- (a) point list of one profile
        curve = np.array([profile_point(t, WIDE) for t in ts])
        points = point_list(WIDE)
        ax.plot(curve[:, 0], curve[:, 1], color=CURVE, zorder=2)

        for index, (y, z) in enumerate(points[:-1], start=1):  # the last point coincides with point 1
            is_kink = index in KINK_INDICES
            ax.plot(y, z, ls="none", marker="D" if is_kink else "o", ms=6.5 if is_kink else 4.5,
                    color=KINK if is_kink else INK, mec=COLORS["surface"], mew=1.0, zorder=4)
            label = f"1, {len(points)}" if index == 1 else str(index)
            if index in MAPPED_INDICES:
                label += f"  (t = {MAPPED_PARAMETERS[MAPPED_INDICES.index(index)]:g})"
            if index == 1:  # top: above the point
                position, ha, va = (y, z + 0.1), "center", "bottom"
            elif index == MAPPED_INDICES[1]:  # bottom center: below the point
                position, ha, va = (y, z - 0.13), "center", "top"
            elif z <= -0.999 and not is_kink:  # floor: above the point, inside the profile
                position, ha, va = (y, z + 0.11), "center", "bottom"
            elif is_kink:  # corners: diagonally below, outwards
                position, ha, va = (y + 0.1 * np.sign(y), z - 0.1), "left" if y > 0 else "right", "top"
            else:  # arc: radially outwards
                direction = np.array([y, z + 0.16]) / np.hypot(y, z + 0.16)
                position, ha, va = (y + 0.17 * direction[0], z + 0.17 * direction[1]), "center", "center"
            ax.text(*position, label, fontsize=note, ha=ha, va=va)

        ax.add_patch(FancyArrowPatch((0.12, 0.62), (0.72, 0.1), connectionstyle="arc3,rad=-0.3",
                                     arrowstyle="-|>", mutation_scale=8, lw=LINE["secondary"], color=INK2))
        ax.text(-0.02, 0.45, "point\norder", fontsize=note, color=INK2, ha="right", va="center")

        ax.set_aspect("equal")
        ax.set_xlim(-2.0, 2.0)
        ax.set_ylim(-1.45, 1.45)
        ax.set_xticks([-1.0, 0.0, 1.0])
        ax.set_yticks([-1.0, 0.0, 1.0])
        ax.set_xlabel("y")
        ax.set_ylabel("z")
        ax.set_title("(a) Point list, kinks and parameters")

        # ------------------------------------ (b) two consecutive profiles, oblique
        # x points towards the viewer (drawn to the lower left), y to the right, z up
        def project(y, z, x):
            return y - 0.36 * x, z - 0.2 * x

        # (floor half-width, x, scale) as in the example file, in units of the rear scaling
        sections = [
            (NARROW, 0.0, 1.1 / 1.5),
            (WIDE, 4.0, 1.0),
        ]

        def section_point(t, section):
            w, x, scale = section
            y, z = profile_point(t, w)
            return project(scale * y, scale * z, x)

        generator_parameters = [0.0, 0.1, 0.2, 0.3, 0.45, 0.5, 0.55, 0.7, 0.8, 0.9]
        for t in generator_parameters + MAPPED_PARAMETERS[::2]:
            is_kink = t in MAPPED_PARAMETERS[::2]
            (y0, z0), (y1, z1) = section_point(t, sections[0]), section_point(t, sections[1])
            loft.plot([y0, y1], [z0, z1], color=KINK if is_kink else MUTED,
                      lw=LINE["data"] if is_kink else LINE["reference"], zorder=3 if is_kink else 1)

        for section in sections:
            outline = np.array([section_point(t, section) for t in ts])
            loft.plot(outline[:, 0], outline[:, 1], color=CURVE, zorder=2)
            for t in MAPPED_PARAMETERS:
                y, z = section_point(t, section)
                loft.plot(y, z, ls="none", marker="D" if t != 0.5 else "o", ms=6.5 if t != 0.5 else 4.5,
                          color=KINK if t != 0.5 else INK, mec=COLORS["surface"], mew=1.0, zorder=4)

        near_right = section_point(0.4, sections[1])
        near_left = section_point(0.6, sections[1])
        near_bottom = section_point(0.5, sections[1])
        loft.text(near_right[0] + 0.12, near_right[1] - 0.06, "t = 0.4 (kink)", fontsize=note, ha="left", va="top")
        loft.text(near_left[0] - 0.12, near_left[1] - 0.06, "t = 0.6 (kink)", fontsize=note, ha="right", va="top")
        loft.text(near_bottom[0], near_bottom[1] - 0.14, "t = 0.5", fontsize=note, ha="center", va="top")

        # coordinate triad
        origin = np.array([1.75, -1.35])
        for (dy, dz), name in (((-0.36 * 0.9, -0.2 * 0.9), "x"), ((0.45, 0.0), "y"), ((0.0, 0.45), "z")):
            loft.annotate("", xy=origin + (dy, dz), xytext=origin,
                          arrowprops={"arrowstyle": "-|>", "lw": LINE["reference"], "mutation_scale": 7,
                                      "color": INK2, "shrinkA": 0, "shrinkB": 0})
            loft.text(origin[0] + 1.25 * dy + (0.06 if name != "z" else 0.0),
                      origin[1] + 1.25 * dz + (0.0 if name != "x" else -0.02), name, fontsize=note,
                      color=INK2, ha="center", va="center")

        loft.set_aspect("equal")
        loft.set_xlim(-3.2, 2.3)
        loft.set_ylim(-2.0, 1.4)
        loft.axis("off")
        loft.set_title("(b) Consecutive profiles, connected at equal t")

        handles = [
            Line2D([], [], color=CURVE),
            Line2D([], [], ls="none", marker="o", ms=4.5, color=INK),
            Line2D([], [], ls="none", marker="D", ms=6.5, color=KINK),
            Line2D([], [], color=MUTED, lw=LINE["reference"]),
        ]
        fig.legend(handles, ["curve through the points", "point with index", "kink", "line of equal parameter t"],
                   loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04), handlelength=1.4, columnspacing=1.6)

        save_figure(fig, FIGURES / "curvePointListXYZ.png")


# ---------------------------------------------------------------------- example
PROFILES = [
    ("FloorProfile_wide", "Fuselage profile with flat floor, wide", WIDE,
     "Flat cabin floor between two kinks and a circular arc above it. Points 5 and 9 are kinks; "
     "points 5, 7 and 9 have fixed curve parameters so that they match the narrow profile."),
    ("FloorProfile_narrow", "Fuselage profile with flat floor, narrow", NARROW,
     "Same point order, kinks and curve parameters as the wide profile, but with a narrower floor."),
]


def fuselage_profile_xml(uid, name, floor_half_width, description=None, tigl_workaround=False):
    """fuselageProfile element.

    With tigl_workaround, the indices are written counted from 0, as TiGL 3.5
    reads them, and the CPACS-conform indices (counted from 1) are kept in a
    comment. The schema documentation shows the CPACS-conform form.
    """
    points = point_list(floor_half_width)
    offset = 1 if tigl_workaround else 0
    lines = [f'<fuselageProfile uID="{uid}">', f"    <name>{name}</name>"]
    if description:
        lines.append(f"    <description>{description}</description>")
    lines += [
        "    <pointList>",
        f"        <x>{vector([0.0] * len(points))}</x>",
        f"        <y>{vector(y for y, _ in points)}</y>",
        f"        <z>{vector(z for _, z in points)}</z>",
    ]
    if tigl_workaround:
        lines += [
            "        <!-- TiGL workaround: CPACS counts point indices from 1, but TiGL 3.5 reads kinkIndices and",
            "             parameterMap/pointIndices counted from 0. The indices below are therefore reduced by 1,",
            "             so that TiGL shows the geometry described in the documentation. CPACS-conform are:",
            f"             <kinkIndices>{vector(KINK_INDICES)}</kinkIndices>",
            f"             <pointIndices>{vector(MAPPED_INDICES)}</pointIndices>",
            "             Restore these values once TiGL counts from 1. -->",
        ]
    lines += [
        f"        <kinkIndices>{vector(i - offset for i in KINK_INDICES)}</kinkIndices>",
        "        <parameterMap>",
        f"            <pointIndices>{vector(i - offset for i in MAPPED_INDICES)}</pointIndices>",
        f"            <paramOnCurve>{vector(MAPPED_PARAMETERS)}</paramOnCurve>",
        "        </parameterMap>",
        "    </pointList>",
        "</fuselageProfile>",
    ]
    return "\n".join(lines)


def section_xml(uid, name, profile_uid, translation, scaling):
    lines = [f'<section uID="{uid}">', f"    <name>{name}</name>"]
    lines.append(indent(transformation_xml(translation=translation), 1))
    lines += [
        "    <elements>",
        f'        <element uID="{uid}_element">',
        f"            <name>{name} element</name>",
        f"            <profileUID>{profile_uid}</profileUID>",
    ]
    lines.append(indent(transformation_xml(scaling=scaling), 3))
    lines += ["        </element>", "    </elements>", "</section>"]
    return "\n".join(lines)


def fuselage_xml():
    """Fuselage widening from the narrow front profile to the wide rear profile.

    The size of each profile is set by the element scaling (y and z), the
    position of the rear section by its translation.
    """
    lines = [
        '<fuselage uID="FloorFuselage">',
        "    <name>Fuselage with flat floor</name>",
        "    <description>Front: narrow floor profile, scaled by 1.1. Rear: wide floor profile, scaled by 1.5, "
        "6 m behind. The kinks of both profiles are connected along the fuselage.</description>",
        indent(transformation_xml(), 1),
        "    <sections>",
        indent(section_xml("FloorFuselage_front", "Front section", "FloorProfile_narrow",
                           (0.0, 0.0, 0.0), (1.0, 1.1, 1.1)), 2),
        indent(section_xml("FloorFuselage_rear", "Rear section", "FloorProfile_wide",
                           (6.0, 0.0, 0.0), (1.0, 1.5, 1.5)), 2),
        "    </sections>",
        "    <segments>",
        '        <segment uID="FloorFuselage_segment">',
        "            <name>Segment</name>",
        "            <fromElementUID>FloorFuselage_front_element</fromElementUID>",
        "            <toElementUID>FloorFuselage_rear_element</toElementUID>",
        "        </segment>",
        "    </segments>",
        "</fuselage>",
    ]
    return "\n".join(lines)


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        name="Fuselage profiles defined by point lists",
        description="Fuselage profiles with kinks and a parameter map, and a fuselage using them. "
        "The point indices are written for TiGL 3.5, which counts them from 0; see the comments in the profiles. "
        "Generated by documentation/scripts/curvePointListXYZ.py.",
        model_uid="PointListAircraft",
        model_name="Point list example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles="\n".join(fuselage_profile_xml(uid, name, w, description, tigl_workaround=True)
                           for uid, name, w, description in PROFILES),
    )


# -------------------------------------------------------------------------- main
def main():
    figure()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the curvePointListXYZType documentation:\n")
    print(fuselage_profile_xml(*PROFILES[0][:3]))


if __name__ == "__main__":
    main()

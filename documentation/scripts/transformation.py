# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of transformations
(transformationType, pointAbsRelType).

Run from the repository root:

    uv run documentation/scripts/transformation.py

The script writes

    documentation/figures/transformationOrder.png
    documentation/figures/transformationRotation.png
    documentation/equations/transformationPoint.{tex,png}
    documentation/equations/transformationParent.{tex,png}
    examples/transformation.xml

and prints the excerpts shown in the documentation. The schema documentation is
not written by this script; copy the printed excerpts there when the example changes.

Definition shown (as in the documentation): a point p given in the local coordinate
system is placed in the coordinate system of the parent at
    P = t + Rx(phi_x) Ry(phi_y) Rz(phi_z) S p,  S = diag(s_x, s_y, s_z),
i.e. scaled along the local axes, rotated about x, the rotated y-axis y' and the twice
rotated z-axis z'' (angles in degrees, right-hand rule), then translated. A component
that references a parent with parentUID and a translation with refType absLocal is
additionally translated by the origin o_parent of the parent coordinate system; the
rotation and scaling of the parent do not apply.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Polygon

from example_xml import indent, transformation_xml, vector, write_cpacs_file
from figure_style import COLORS, FULL_WIDTH, LINE, figure_style, save_equation, save_figure
from nacaProfile import naca4
from wing import (FUSELAGE_UID, INK, INK2, MUTED, arrow, circle_profile_xml, dot, fuselage_xml, label, rotation_x,
                  rotation_y, rotation_z, transform)

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "transformation.xml"

SERIES1 = COLORS["series1"]
LIGHT = COLORS["series1Light"]
WASH = 0.1

# ------------------------------------------------------------------ example data
# Vertical tail attached to the fuselage of wing.py: its wing coordinate system is rotated by 90° about x,
# so that the span (y) points upwards (z), and translated relative to the origin of the fuselage.
TAIL_UID = "VerticalTail"
TAIL_ROTATION = (90.0, 0.0, 0.0)
TAIL_TRANSLATION = (22.0, 0.0, 0.8)
TAIL_AIRFOIL_UID = "NACA0012"
# Sections: (uID suffix, chord = element scaling in x and z); positioning of the tip: (length, sweepAngle)
TAIL_SECTIONS = [("root", 4.0), ("tip", 1.8)]
TAIL_TIP_POSITIONING = (4.5, 35.0)

# Illustrative transformation for the order of scaling, rotation and translation (side view, not in the example)
ORDER_SCALING = (3.0, 1.0, 3.0)
ORDER_ROTATION = (0.0, 12.0, 0.0)
ORDER_TRANSLATION = (1.2, 0.0, 1.0)

# Illustrative rotation angles for the rotation sequence (not in the example)
ROTATION_ANGLES = (40.0, 35.0, 45.0)

# ------------------------------------------------------------------- equations
POINT_LINES = [r"P = t + R_x(\varphi_x)\,R_y(\varphi_y)\,R_z(\varphi_z)\,S\,p"]
PARENT_LINES = [r"P = o_\mathrm{parent} + t + R_x(\varphi_x)\,R_y(\varphi_y)\,R_z(\varphi_z)\,S\,p"]


# -------------------------------------------------------------------- geometry
def _airfoil(code, n=81):
    """Closed NACA 4-digit contour from the trailing edge over the lower side, as (x, z)."""
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, n)))  # 1 ... 0
    (xu, zu), (xl, zl), _, _ = naca4(code, x, 0.0)
    return np.column_stack([np.concatenate([xl, xu[::-1][1:]]), np.concatenate([zl, zu[::-1][1:]])])


def tail_tip_origin():
    """Origin of the tip section in the wing coordinate system of the tail (sweep only, no dihedral)."""
    length, sweep = TAIL_TIP_POSITIONING
    return rotation_z(-sweep) @ np.array([0.0, length, 0.0])


def tail_leading_trailing_edges():
    """Global leading and trailing edge of root and tip; the fuselage is not transformed, so o_parent = 0."""
    origins = {"root": np.zeros(3), "tip": tail_tip_origin()}
    result = {}
    for name, chord in TAIL_SECTIONS:
        local = origins[name] + np.array([[0.0, 0.0, 0.0], [chord, 0.0, 0.0]])
        result[name] = transform(local, rotation=TAIL_ROTATION, translation=TAIL_TRANSLATION)
    return result


# --------------------------------------------------------------------- figures
def _side(points):
    """Side view (x to the right, z up) of 3D points."""
    points = np.asarray(points, dtype=float)
    return points[..., [0, 2]]


def figure_order():
    """Side view of an airfoil scaled, rotated about y and translated, one step per panel."""
    airfoil = _airfoil("2412")
    unit = np.column_stack([airfoil[:, 0], np.zeros(len(airfoil)), airfoil[:, 1]])
    scaled = transform(unit, scaling=ORDER_SCALING)
    rotated = transform(scaled, rotation=ORDER_ROTATION)
    translated = rotated + np.asarray(ORDER_TRANSLATION)
    origin = np.array(ORDER_TRANSLATION)[[0, 2]]
    angle = ORDER_ROTATION[1]
    # the operation of each step is named in the panel title, so that the panels need no loose annotations
    steps = [(f"(a) Scaling by {ORDER_SCALING[0]:g}", unit, scaled),
             ("(b) Rotation about y", scaled, rotated),
             ("(c) Translation by t", rotated, translated)]
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 1.75), gridspec_kw={"wspace": 0.08})
        for ax, (title, before, after) in zip(axes, steps, strict=True):
            for tip, text, offset in (((4.5, 0.0), "x", (6, 0)), ((0.0, 1.8), "z", (0, 7))):
                arrow(ax, (0.0, 0.0), tip, color=INK2, lw=LINE["reference"], head=6)
                label(ax, tip, text, offset, color=INK2)
            # y points into the page: the usual symbol of an axis seen from behind, below the origin
            ax.plot(-0.32, -0.42, ls="none", marker="o", ms=6.5, mfc="none", mec=INK2, mew=LINE["reference"])
            ax.plot(-0.32, -0.42, ls="none", marker="x", ms=4.0, mec=INK2, mew=LINE["reference"])
            label(ax, (-0.32, -0.42), "y", (-8, 0), ha="right", color=INK2)
            ax.plot(*_side(before).T, color=LIGHT, lw=LINE["secondary"], zorder=2)
            ax.plot(*_side(after).T, color=SERIES1, lw=LINE["data"], zorder=3)
            ax.set_title(title)
            ax.set_xlim(-0.9, 5.0)
            ax.set_ylim(-0.9, 2.2)
            ax.set_aspect("equal")
            ax.axis("off")
        # rotation about y: a positive angle turns x towards -z. The rotated x-axis is drawn only behind the
        # trailing edge, so that it does not run along the chord.
        radius = 4.0
        direction = np.array([np.cos(np.radians(-angle)), np.sin(np.radians(-angle))])
        axes[1].plot(*np.array([ORDER_SCALING[0] * 1.08 * direction, (radius + 0.3) * direction]).T, color=MUTED,
                     lw=LINE["reference"], zorder=1)
        axes[1].add_patch(Arc((0.0, 0.0), 2 * radius, 2 * radius, theta1=-angle + 1.5, theta2=0.0, color=INK2,
                              lw=LINE["reference"]))
        arc_end = [radius * np.array([np.cos(np.radians(a)), np.sin(np.radians(a))]) for a in (-angle + 1.5, -angle)]
        arrow(axes[1], arc_end[0], arc_end[1], color=INK2, lw=LINE["reference"], head=6)
        middle = radius * np.array([np.cos(np.radians(-angle / 2)), np.sin(np.radians(-angle / 2))])
        label(axes[1], middle, f"{angle:g}°", (5, 0), ha="left", color=INK2)
        # translation: the airfoil moves by t, which is neither scaled nor rotated
        arrow(axes[2], (0.0, 0.0), origin, color=INK, lw=LINE["secondary"], head=7)
        dot(axes[2], origin)
        label(axes[2], 0.5 * origin, "t", (-7, 5), ha="right", va="bottom")
        save_figure(fig, FIGURES / "transformationOrder.png")


def figure_rotation():
    """Oblique views of the rotation sequence about x, the rotated y-axis y' and the twice rotated z-axis z''."""
    ax_angle, ay_angle, az_angle = ROTATION_ANGLES
    stages = [np.eye(3), rotation_x(ax_angle), rotation_x(ax_angle) @ rotation_y(ay_angle),
              rotation_x(ax_angle) @ rotation_y(ay_angle) @ rotation_z(az_angle)]
    primes = ["", "′", "″", "‴"]

    def project(p):  # oblique view: y to the right, z up, x towards the viewer, drawn down to the left
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 1] - 0.5 * p[..., 0], p[..., 2] - 0.38 * p[..., 0]]).T

    # (panel, rotation axis index, axis that sweeps the shaded sector, angle, name of the angle)
    panels = [(0, 0, 1, ax_angle, "φ$_x$"), (1, 1, 2, ay_angle, "φ$_y$"), (2, 2, 0, az_angle, "φ$_z$")]
    titles = ["(a) Rotation about x", "(b) Rotation about y′", "(c) Rotation about z″"]
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.7), gridspec_kw={"wspace": 0.05})
        for ax, (k, about, swept, angle, name), title in zip(axes, panels, titles, strict=True):
            before, after = stages[k], stages[k + 1]
            partial = [rotation_x, rotation_y, rotation_z][about]
            o = project(np.zeros(3))
            # sector swept by one axis in the plane normal to the rotation axis
            arc = np.array([before @ partial(a) @ np.eye(3)[swept] for a in np.linspace(0.0, angle, 40)])
            ax.add_patch(Polygon(project([np.zeros(3), *(0.62 * arc)]), closed=True, facecolor=SERIES1, alpha=WASH,
                                 edgecolor="none", zorder=0))
            # the arc ends in an arrowhead, which shows the positive sense of the rotation
            ax.plot(*project(0.62 * arc[:-1]).T, color=INK2, lw=LINE["reference"], zorder=2)
            arrow(ax, project(0.62 * arc[-4]), project(0.62 * arc[-1]), color=INK2, lw=LINE["reference"], head=6)
            label(ax, project(0.45 * arc[len(arc) // 2]), name, (0, 0))
            for i, axis_name in enumerate("xyz"):
                if i != about:  # axes before the rotation, pale
                    tip = before[:, i]
                    ax.plot(*project([np.zeros(3), tip]).T, color=LIGHT, lw=LINE["secondary"], zorder=1)
                    label(ax, project(tip), axis_name + primes[k], _offset(project(tip) - o), color=INK2)
                tip = after[:, i]
                # the axis of the rotation keeps its position and is drawn in ink, the turned axes in series 1
                arrow(ax, o, project(tip), color=INK if i == about else SERIES1, lw=LINE["data"], head=8)
                label(ax, project(tip), axis_name + primes[k + 1] if i != about else axis_name + primes[k],
                      _offset(project(tip) - o))
            dot(ax, o, size=3.5)
            ax.set_xlim(-1.05, 1.15)
            ax.set_ylim(-1.05, 1.2)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(title)
        save_figure(fig, FIGURES / "transformationRotation.png")


def _offset(direction, distance=9.0):
    """Label offset in points, away from the origin along the projected axis."""
    norm = np.linalg.norm(direction)
    return tuple(distance * direction / norm) if norm > 1e-9 else (0.0, distance)


# --------------------------------------------------------------------- example
def tail_transformation_xml():
    """Transformation of the tail: rotation and translation; the scaling has its default and is omitted."""
    lines = ["<transformation>", "    <rotation>"]
    lines += [f"        <{axis}>{value:g}</{axis}>" for axis, value in zip("xyz", TAIL_ROTATION, strict=True)]
    lines += ["    </rotation>", '    <translation refType="absLocal">']
    lines += [f"        <{axis}>{value:g}</{axis}>" for axis, value in zip("xyz", TAIL_TRANSLATION, strict=True)]
    lines += ["    </translation>", "</transformation>"]
    return "\n".join(lines)


def tail_section_xml(section):
    name, chord = section
    element = "\n".join([
        f'<element uID="{TAIL_UID}_{name}_element">', f"    <name>{name.capitalize()} element</name>",
        f"    <airfoilUID>{TAIL_AIRFOIL_UID}</airfoilUID>",
        indent(transformation_xml(scaling=(chord, 1.0, chord)), 1), "</element>",
    ])
    return "\n".join([
        f'<section uID="{TAIL_UID}_{name}">', f"    <name>{name.capitalize()} section</name>",
        indent(transformation_xml(), 1),
        "    <elements>", indent(element, 2), "    </elements>", "</section>",
    ])


def tail_xml():
    length, sweep = TAIL_TIP_POSITIONING
    (root, _), (tip, _) = TAIL_SECTIONS
    return "\n".join([
        f'<wing uID="{TAIL_UID}">', "    <name>Vertical tail</name>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(tail_transformation_xml(), 1),
        "    <sections>", *(indent(tail_section_xml(s), 2) for s in TAIL_SECTIONS), "    </sections>",
        "    <positionings>",
        f'        <positioning uID="{TAIL_UID}_{root}_positioning">', "            <name>Root positioning</name>",
        "            <length>0</length>", "            <sweepAngle>0</sweepAngle>",
        "            <dihedralAngle>0</dihedralAngle>",
        f"            <toSectionUID>{TAIL_UID}_{root}</toSectionUID>", "        </positioning>",
        f'        <positioning uID="{TAIL_UID}_{tip}_positioning">', "            <name>Tip positioning</name>",
        f"            <length>{length:g}</length>", f"            <sweepAngle>{sweep:g}</sweepAngle>",
        "            <dihedralAngle>0</dihedralAngle>",
        f"            <fromSectionUID>{TAIL_UID}_{root}</fromSectionUID>",
        f"            <toSectionUID>{TAIL_UID}_{tip}</toSectionUID>", "        </positioning>",
        "    </positionings>",
        "    <segments>",
        f'        <segment uID="{TAIL_UID}_segment1">', "            <name>Segment 1</name>",
        f"            <fromElementUID>{TAIL_UID}_{root}_element</fromElementUID>",
        f"            <toElementUID>{TAIL_UID}_{tip}_element</toElementUID>", "        </segment>",
        "    </segments>",
        "</wing>",
    ])


def airfoil_xml():
    x = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, 13)))  # 1 ... 0
    (xu, zu), (xl, zl), _, _ = naca4("0012", x, 0.0)
    xs = [round(float(v), 4) + 0.0 for v in list(xl) + list(xu[::-1][1:])]
    zs = [round(float(v), 4) + 0.0 for v in list(zl) + list(zu[::-1][1:])]
    return "\n".join([
        f'<wingAirfoil uID="{TAIL_AIRFOIL_UID}">', "    <name>NACA 0012 with closed trailing edge</name>",
        "    <pointList>", f"        <x>{vector(xs)}</x>", f"        <y>{vector([0.0] * len(xs))}</y>",
        f"        <z>{vector(zs)}</z>", "    </pointList>", "</wingAirfoil>",
    ])


def excerpt_tail_xml():
    return "\n".join([
        f'<wing uID="{TAIL_UID}">', "    <name>Vertical tail</name>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(tail_transformation_xml(), 1),
        "    <sections>", "        ...", "    </sections>",
        "    <positionings>", "        ...", "    </positionings>",
        "    <segments>", "        ...", "    </segments>",
        "</wing>",
    ])


def excerpt_translation_xml():
    """The translation of the tail, without the enclosing transformation."""
    lines = tail_transformation_xml().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("<translation"))
    return "\n".join(line[4:] for line in lines[start:start + 5])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Transformation",
        description="A vertical tail attached to a fuselage, rotated by 90 degrees about the x-axis and translated relative to the fuselage.",
        model_uid="TransformationAircraft",
        model_name="Transformation example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", tail_xml())],
        extra_profiles=[("wingAirfoils", airfoil_xml())],
    )


# ------------------------------------------------------------------------ main
def main():
    save_equation(POINT_LINES, EQUATIONS / "transformationPoint")
    save_equation(PARENT_LINES, EQUATIONS / "transformationParent")
    figure_order()
    figure_rotation()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for name, (le, te) in tail_leading_trailing_edges().items():
        print(f"{name}: leading edge {np.round(le, 4)}, trailing edge {np.round(te, 4)} (global)")
    print("\nExcerpt for the transformationType documentation:\n")
    print(excerpt_tail_xml())
    print("\nExcerpt for the pointAbsRelType documentation:\n")
    print(excerpt_translation_xml())


if __name__ == "__main__":
    main()

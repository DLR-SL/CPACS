# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of two-dimensional structural
profiles (structuralProfileType).

Run from the repository root:

    uv run documentation/scripts/structuralProfile.py

The script writes

    documentation/figures/structuralProfile.png
    documentation/figures/structuralProfileSheet.png
    examples/structuralProfiles.xml

and prints the excerpt shown in the documentation. The schema documentation is
not written by this script; copy the printed excerpt there when the example changes.

Definition shown (as in the documentation): the points lie in the x-y plane of the
profile; a sheet runs from its fromPointUID to its toPointUID. Its coordinate system
has y_s along the sheet, z_s normal to the sheet in the profile plane (y_s rotated by
+90 degrees about the profile z-axis) and x_s = y_s x z_s along the profile z-axis.
The orthotropy direction is x_s rotated by orthotropyDirection about z_s.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from example_xml import indent, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "structuralProfiles.xml"

SHEET = COLORS["series1"]
FIBER = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
PROFILE_UID = "TStringerProfile"
# T-shaped stringer: flange of 30 mm on the skin side, web of 25 mm height, all in metres
POINTS = {"P1": (0.0, 0.0), "P2": (0.015, 0.0), "P3": (-0.015, 0.0), "P4": (0.0, 0.025)}
# Sheets: name -> (from point, to point, readable name). All sheets start at P1, where they meet.
SHEETS = {
    "S1": ("P1", "P2", "Right flange"),
    "S2": ("P1", "P3", "Left flange"),
    "S3": ("P1", "P4", "Web"),
}
THICKNESS = {"S1": 0.0016, "S2": 0.0016, "S3": 0.0012}
REINFORCEMENT = ("P4", 0.00002)  # point, cross-section area [m^2] of an additional stiffener at the web tip
MATERIAL_UID = "Aluminium2024"
ELEMENT_UID = "TStringer"
ORTHOTROPY_ANGLE = 30.0  # degrees, only for the figure


def uid(name):
    return f"{PROFILE_UID}_{name}"


def sheet_axes(name):
    """Unit vectors y_s and z_s of a sheet in the profile plane."""
    start, end = SHEETS[name][:2]
    y_s = np.subtract(POINTS[end], POINTS[start])
    y_s = y_s / np.linalg.norm(y_s)
    z_s = np.array([-y_s[1], y_s[0]])  # y_s rotated by +90 degrees about the profile z-axis
    return y_s, z_s


# --------------------------------------------------------------------- figures
def arrow(ax, start, end, color=INK, lw=None, head=True):
    ax.annotate("", xy=end, xytext=start, zorder=5, arrowprops={
        "arrowstyle": "-|>" if head else "-", "lw": lw or LINE["secondary"], "mutation_scale": 7, "shrinkA": 0,
        "shrinkB": 0, "color": color})
    ax.plot(*np.array([start, end]).T, alpha=0)  # include the arrow in the axis limits


def label(ax, xy, text, offset=(0, 0), ha="center", va="center", color=INK, **kwargs):
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=color,
                zorder=7, **kwargs)


def dot(ax, xy, color=INK, size=4.5):
    ax.plot(*xy, ls="none", marker="o", ms=size, color=color, mec=COLORS["surface"], mew=1.0, zorder=6)


def out_of_plane(ax, xy, radius_pt=3.2):
    """Symbol for an axis pointing out of the drawing plane (circle with a dot)."""
    ax.plot(*xy, ls="none", marker="o", ms=2 * radius_pt, mfc=COLORS["surface"], mec=INK, mew=LINE["secondary"],
            zorder=6)
    ax.plot(*xy, ls="none", marker="o", ms=1.6, color=INK, zorder=7)


def draw_sheets(ax, color, with_direction):
    for name, (start, end, _) in SHEETS.items():
        a, b = np.array(POINTS[start]), np.array(POINTS[end])
        ax.plot(*np.array([a, b]).T, color=color, zorder=3)
        if with_direction:
            arrow(ax, a + 0.45 * (b - a), a + 0.62 * (b - a), color=color, lw=LINE["data"])


def figure_profile():
    """(a) points and sheets with their direction, (b) the coordinate system of each sheet."""
    with figure_style():
        fig, (pts, axes) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.1), gridspec_kw={"wspace": 0.3})

        # (a) points and sheets in profile coordinates
        pts.axhline(0.0, color=COLORS["grid"], lw=LINE["reference"], zorder=0)
        pts.axvline(0.0, color=COLORS["grid"], lw=LINE["reference"], zorder=0)
        draw_sheets(pts, SHEET, with_direction=True)
        point_labels = {"P1": ((0, -8), "center", "top"), "P2": ((0, -8), "center", "top"),
                        "P3": ((0, -8), "center", "top"), "P4": ((7, 0), "left", "center")}
        for name, xy in POINTS.items():
            dot(pts, xy)
            offset, ha, va = point_labels[name]
            label(pts, xy, name, offset, ha=ha, va=va)
        sheet_labels = {"S1": ((0, 7), "center", "bottom"), "S2": ((0, 7), "center", "bottom"),
                        "S3": ((-7, 0), "right", "center")}
        for name, (start, end, _) in SHEETS.items():
            middle = 0.5 * (np.array(POINTS[start]) + np.array(POINTS[end]))
            offset, ha, va = sheet_labels[name]
            label(pts, middle, name, offset, ha=ha, va=va, color=INK2)
        pts.set_aspect("equal")
        pts.set_xlim(-0.022, 0.022)
        pts.set_ylim(-0.008, 0.03)
        pts.set_xticks([-0.02, -0.01, 0.0, 0.01, 0.02])
        pts.set_yticks([0.0, 0.01, 0.02, 0.03])
        pts.set_xlabel("x [m]")
        pts.set_ylabel("y [m]")
        pts.set_title("(a) Points and sheets")

        # (b) sheet coordinate systems
        draw_sheets(axes, MUTED, with_direction=False)
        for name in POINTS:
            dot(axes, POINTS[name], color=MUTED, size=3.5)
        length = 0.0075
        axis_labels = {  # sheet -> (offset of y_s label, ha), (offset of z_s label, ha)
            "S1": (((0, -8), "center"), ((0, 7), "center")),
            "S2": (((0, 8), "center"), ((0, -7), "center")),
            "S3": (((7, 0), "left"), ((-6, 0), "right")),
        }
        for name, (start, end, _) in SHEETS.items():
            origin = 0.5 * (np.array(POINTS[start]) + np.array(POINTS[end]))
            y_s, z_s = sheet_axes(name)
            arrow(axes, origin, origin + length * y_s)
            arrow(axes, origin, origin + length * z_s)
            out_of_plane(axes, origin)
            (y_off, y_ha), (z_off, z_ha) = axis_labels[name]
            label(axes, origin + length * y_s, f"$y_{{{name}}}$", y_off, ha=y_ha)
            label(axes, origin + length * z_s, f"$z_{{{name}}}$", z_off, ha=z_ha)
        label(axes, (0.0075, 0.0), "$x_{S1}$ out of the plane", (18, -26), ha="left", va="top", color=INK2,
              arrowprops=leader())
        axes.set_aspect("equal")
        axes.set_xlim(-0.022, 0.022)
        axes.set_ylim(-0.008, 0.03)
        axes.axis("off")
        axes.set_title("(b) Coordinate system of each sheet")

        handles = [Line2D([], [], color=SHEET),
                   Line2D([], [], ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"]),
                   Line2D([], [], ls="none", marker="o", ms=6.4, mfc=COLORS["surface"], mec=INK,
                          mew=LINE["secondary"])]
        fig.legend(handles, ["sheet, arrow from fromPointUID to toPointUID", "point", "axis out of the plane"],
                   loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.08), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "structuralProfile.png")


def figure_sheet():
    """The profile extruded along its z-axis, with the coordinate system and orthotropy direction of the web.

    Oblique view: the profile z-axis to the right, y up and x into the depth, so that the
    right-handed axes also look right-handed and the web faces the viewer.
    """
    length = 0.04

    def project(p):
        x, y, z = p
        return np.array([z + 0.5 * x, y + 0.35 * x])

    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.9))

        # sheets as surfaces between the profile at z = 0 and z = length; the web is highlighted
        for name in ("S1", "S3", "S2"):  # back to front
            start, end, _ = SHEETS[name]
            a, b = POINTS[start], POINTS[end]
            corners = [(*a, 0.0), (*b, 0.0), (*b, length), (*a, length)]
            web = name == "S3"
            ax.add_patch(Polygon([project(c) for c in corners], closed=True, lw=LINE["secondary"],
                                 ec=SHEET if web else MUTED, fc=(SHEET, 0.08) if web else "none",
                                 zorder=2, joinstyle="round"))
        label(ax, project((0.0, 0.025, 0.0)), "web S3", (-6, 0), ha="right", color=INK2)
        label(ax, project((-0.015, 0.0, 0.0)), "flange S2", (-6, 0), ha="right", color=INK2)
        label(ax, project((0.015, 0.0, length)), "flange S1", (6, 0), ha="left", va="center", color=INK2)

        # profile axes, drawn beside the stringer
        o = np.array([0.0, 0.004, -0.022])
        for direction, text, offset, ha in (((1, 0, 0), "x", (4, 3), "left"), ((0, 1, 0), "y", (0, 6), "center"),
                                            ((0, 0, 1), "z", (5, 0), "left")):
            tip = project(o + 0.009 * np.array(direction))
            arrow(ax, project(o), tip, color=INK2, lw=LINE["reference"])
            label(ax, tip, text, offset, ha=ha, color=INK2)
        label(ax, project(o), "profile axes", (0, -8), va="top", color=INK2)

        # coordinate system of the web S3 in the middle of its surface
        center = np.array([0.0, 0.0145, 0.5 * length])
        y_s = np.array([0.0, 1.0, 0.0])
        z_s = np.array([-1.0, 0.0, 0.0])
        x_s = np.cross(y_s, z_s)
        axis_length = 0.008
        for vector, text, offset, ha in ((x_s, "$x_{S3}$", (8, -1), "left"), (y_s, "$y_{S3}$", (0, 7), "center"),
                                         (z_s, "$z_{S3}$", (-5, -3), "right")):
            tip = project(center + axis_length * vector)
            arrow(ax, project(center), tip)
            label(ax, tip, text, offset, ha=ha)
        phi = np.radians(ORTHOTROPY_ANGLE)
        fiber = np.cos(phi) * x_s + np.sin(phi) * y_s
        tip = project(center + 1.3 * axis_length * fiber)
        arrow(ax, project(center), tip, color=FIBER, lw=LINE["data"])
        label(ax, tip, "orthotropy direction", (5, 0), ha="left", va="center")
        angles = np.linspace(0.0, phi, 30)
        arc = np.array([project(center + 0.6 * axis_length * (np.cos(a) * x_s + np.sin(a) * y_s)) for a in angles])
        ax.plot(*arc.T, color=INK, lw=LINE["reference"], zorder=5)
        middle = project(center + 0.6 * axis_length * (np.cos(phi / 2) * x_s + np.sin(phi / 2) * y_s))
        label(ax, middle, "angle orthotropyDirection", (10, -26), ha="left", va="top", arrowprops=leader())

        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "structuralProfileSheet.png")


# --------------------------------------------------------------------- example
def profile_xml(sheets=tuple(SHEETS)):
    lines = [f'<structuralProfile2D uID="{PROFILE_UID}">', "    <name>T-stringer</name>",
             "    <description>Flange of 30 mm and web of 25 mm height</description>", "    <pointList>"]
    for name, (x, y) in POINTS.items():
        lines += [f'        <point uID="{uid(name)}">', f"            <x>{x:g}</x>", f"            <y>{y:g}</y>",
                  "        </point>"]
    lines += ["    </pointList>", "    <sheetList>"]
    for name in sheets:
        start, end, readable = SHEETS[name]
        lines += [f'        <sheet uID="{uid(name)}">', f"            <name>{readable}</name>",
                  f"            <fromPointUID>{uid(start)}</fromPointUID>",
                  f"            <toPointUID>{uid(end)}</toPointUID>", "        </sheet>"]
    if len(sheets) < len(SHEETS):
        lines.append("        ...")
    lines += ["    </sheetList>", "</structuralProfile2D>"]
    return "\n".join(lines)


def element_xml(sheets=tuple(SHEETS)):
    lines = [f'<profileBasedStructuralElement uID="{ELEMENT_UID}">', "    <name>T-stringer</name>"]
    for name in sheets:
        lines += ["    <sheetProperties>", f"        <sheetUID>{uid(name)}</sheetUID>",
                  f"        <materialUID>{MATERIAL_UID}</materialUID>",
                  f"        <thickness>{THICKNESS[name]:g}</thickness>", "    </sheetProperties>"]
    if len(sheets) < len(SHEETS):
        lines.append("    ...")
    point, area = REINFORCEMENT
    lines += [f"    <structuralProfileUID>{PROFILE_UID}</structuralProfileUID>", "    <pointProperties>",
              f"        <pointUID>{uid(point)}</pointUID>", f"        <materialUID>{MATERIAL_UID}</materialUID>",
              f"        <crossSectionArea>{area:g}</crossSectionArea>", "    </pointProperties>",
              "</profileBasedStructuralElement>"]
    return "\n".join(lines)


def material_xml():
    return "\n".join([
        f'<material uID="{MATERIAL_UID}">', "    <name>Aluminium 2024-T3</name>", "    <description>Typical values</description>", "    <rho>2770</rho>",
        "    <isotropicProperties>", "        <E>72400000000</E>", "        <G>27600000000</G>",
        "    </isotropicProperties>", "</material>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Structural profiles",
        description="A T-shaped stringer profile and the profile-based structural element that assigns material and "
                    "thickness to its sheets.",
        model_uid=None,
        model_name="",
        components_tag=None,
        components="",
        profiles_tag="structuralProfiles",
        profiles=profile_xml(),
        extra_vehicles=[("structuralElements", "<profileBasedStructuralElements>\n"
                         + indent(element_xml(), 1) + "\n</profileBasedStructuralElements>"),
                        ("materials", material_xml())],
    )


# ------------------------------------------------------------------------ main
def main():
    figure_profile()
    figure_sheet()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the structuralProfileType documentation:\n")
    print(profile_xml())
    print()
    print(element_xml(sheets=("S1",)))


if __name__ == "__main__":
    main()

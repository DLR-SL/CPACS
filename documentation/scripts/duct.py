# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the ducts
(ductsType, ductType, ductAssemblyType).

Run from the repository root:

    uv run documentation/scripts/duct.py

The script writes

    documentation/figures/ductIntake.png
    documentation/equations/ductPoint.tex / .png
    examples/ducts.xml

and prints the excerpts shown in the documentation together with the derived
quantities the example has to get right: the wall between the ducts and the skin of
the fuselage, the overlap of the ducts that form one channel, and the volume the
ducts take out of the fuselage. The schema documentation is not written by this
script; copy the printed excerpts there when the example changes.

The example is a single-engine fighter with two intakes at the sides of its
fuselage, whose ducts merge into one channel in front of the engine. The intake duct
is defined once, on the side y > 0, and mirrored at the x-z plane; the channel is a
second duct on the axis. One duct assembly fuses the three bodies and cuts them out
of the fuselage.

Each body, the fuselage and both ducts, is lofted like the fuselage of fuselage.py:
its sections lie at stations along the x-axis, each holds the circle of diameter 1
scaled to width (y) and height (z) and translated in y and z, and the surface is one
loft through all profiles, continuous in curvature across the sections. A cross
section at the station x is therefore the circle scaled to the width and height and
moved to the centre that a cubic spline through the values of the sections gives
there (fuselage.interpolation, with the centripetal parameters of the sections).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch, Polygon
from matplotlib.path import Path as MplPath

from example_xml import indent, transformation_xml, write_cpacs_file
from figure_style import (COLORS, FONT_SIZE, FULL_WIDTH, LINE, axes_cross, figure_style, label, leader, save_equation,
                          save_figure)
from fuselage import circle_profile_xml, collection, interpolation

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "ducts.xml"

DUCT = COLORS["series1"]
MIRRORED = COLORS["mirrored"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
PROFILE_UID = "Circle"
FUSELAGE_UID = "Fuselage"
INTAKE_UID = "IntakeDuct"
CHANNEL_UID = "ChannelDuct"
ASSEMBLY_UID = "IntakeDuctAssembly"

# Sections of the fuselage of a single-engine fighter, 14.5 m long: (uID suffix, x, y of the centre, width, height,
# z of the centre). The fuselage is narrow at the cockpit and widens behind it to take the two intakes at its sides;
# behind the engine face it narrows again to the nozzle.
FUSELAGE = [
    ("nose", 0.0, 0.0, 0.0, 0.0, 0.0),
    ("nose1", 1.0, 0.0, 0.55, 0.55, 0.0),
    ("nose2", 2.2, 0.0, 0.95, 0.9, 0.05),
    ("cockpit", 3.5, 0.0, 1.3, 1.4, 0.2),
    ("intake", 5.0, 0.0, 2.5, 1.5, 0.05),
    ("center1", 6.5, 0.0, 2.6, 1.5, 0.05),
    ("center2", 8.0, 0.0, 2.55, 1.5, 0.05),
    ("center3", 9.5, 0.0, 2.3, 1.45, 0.05),
    ("engine1", 11.0, 0.0, 1.8, 1.3, 0.05),
    ("engine2", 12.8, 0.0, 1.35, 1.15, 0.05),
    ("nozzle", 14.5, 0.0, 1.05, 1.0, 0.05),
]

# The intake duct on the side y > 0, mirrored at the x-z plane. It starts in front of the fuselage, so that the cut
# opens the side of the fuselage where it widens, and runs inwards to the channel, into which it reaches.
INTAKE = [
    ("entry", 3.9, 0.95, 0.5, 0.7, -0.1),
    ("lip", 5.0, 0.95, 0.5, 0.7, -0.1),
    ("bend", 7.0, 0.72, 0.55, 0.68, -0.05),
    ("merge", 9.0, 0.33, 0.62, 0.66, 0.0),
]

# The channel on the axis, from where the intake ducts merge to the engine face.
CHANNEL = [
    ("front", 8.2, 0.0, 0.9, 0.85, 0.0),
    ("engineFace", 10.6, 0.0, 0.9, 0.85, 0.0),
]

ENGINE_FACE = CHANNEL[-1][1]
STATIONS = (6.5, 8.8)  # cross sections shown in the figure


# ------------------------------------------------------------------ loft model
def _circle(n=64):
    """Points of the circle of diameter 1 in the y-z plane, starting at the top."""
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.column_stack([0.5 * np.sin(t), 0.5 * np.cos(t)])


class Body:
    """Body lofted through the profiles of its sections; each cross section is the circle, scaled and moved."""

    def __init__(self, sections, mirror=False):
        sign = -1.0 if mirror else 1.0
        self.sections = [(s[0], s[1], sign * s[2], *s[3:]) for s in sections]
        circle = _circle()
        points = np.array([np.column_stack([np.full(len(circle), x), yc + w * circle[:, 0], zc + h * circle[:, 1]])
                           for _, x, yc, w, h, zc in self.sections])
        steps = np.sqrt(np.linalg.norm(np.diff(points, axis=0), axis=2))
        params = np.vstack([np.zeros(steps.shape[1]), np.cumsum(steps, axis=0)])
        self.params = (params / params[-1]).mean(axis=1)
        self._spline = interpolation(self.params, [s[1:] for s in self.sections])  # x, yc, width, height, zc
        self.rows = self._spline(np.linspace(0.0, 1.0, 4001))

    @property
    def span(self):
        return self.sections[0][1], self.sections[-1][1]

    def station(self, x):
        """(y of the centre, width, height, z of the centre) at the station x, or None outside the body."""
        if not self.span[0] <= x <= self.span[1]:
            return None
        return np.array([np.interp(x, self.rows[:, 0], self.rows[:, k]) for k in (1, 2, 3, 4)])

    def inside(self, x, y, z):
        """Whether the points (y, z) at the station x lie inside the body."""
        s = self.station(x)
        if s is None:
            return np.zeros(np.broadcast(y, z).shape, dtype=bool)
        yc, w, h, zc = s
        if w <= 0.0 or h <= 0.0:
            return np.zeros(np.broadcast(y, z).shape, dtype=bool)
        return ((y - yc) / (0.5 * w)) ** 2 + ((z - zc) / (0.5 * h)) ** 2 < 1.0


FUSELAGE_BODY = Body(FUSELAGE)
INTAKE_BODY = Body(INTAKE)
MIRRORED_BODY = Body(INTAKE, mirror=True)
CHANNEL_BODY = Body(CHANNEL)
DUCT_BODIES = (INTAKE_BODY, MIRRORED_BODY, CHANNEL_BODY)


def _grid(x, step=0.004, margin=0.05):
    s = FUSELAGE_BODY.station(x)
    yc, w, h, zc = s
    y = np.arange(-0.5 * w - margin, 0.5 * w + margin, step)
    z = np.arange(zc - 0.5 * h - margin, zc + 0.5 * h + margin, step)
    return np.meshgrid(y, z)


def removed_area(x, step=0.004):
    """Area of the cross section of the fuselage at x that lies inside a duct [m^2]."""
    y, z = _grid(x, step)
    duct = np.any([b.inside(x, y, z) for b in DUCT_BODIES], axis=0)
    return float(np.count_nonzero(duct & FUSELAGE_BODY.inside(x, y, z))) * step * step


def removed_volume(dx=0.02):
    xs = np.arange(INTAKE[0][1], CHANNEL[-1][1] + dx / 2, dx)
    areas = [removed_area(x) for x in xs]
    return float(np.trapezoid(areas, xs))


def wall(x, body=INTAKE_BODY, n=720):
    """Smallest distance between the contour of the duct and the contour of the fuselage at the station x [m],
    negative where the duct leaves the fuselage."""
    yc, w, h, zc = body.station(x)
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    y, z = yc + 0.5 * w * np.sin(t), zc + 0.5 * h * np.cos(t)
    fy, fw, fh, fz = FUSELAGE_BODY.station(x)
    # outside the fuselage by the ellipse function, scaled to a distance with the smaller half axis
    level = np.sqrt(((y - fy) / (0.5 * fw)) ** 2 + ((z - fz) / (0.5 * fh)) ** 2)
    return float(np.min((1.0 - level) * 0.5 * min(fw, fh)))


# --------------------------------------------------------------------- figures
def _ellipse(yc, w, h, zc, n=361):
    t = np.linspace(0.0, 2.0 * np.pi, n)
    return np.column_stack([yc + 0.5 * w * np.sin(t), zc + 0.5 * h * np.cos(t)])


def _band(body, column_centre, column_size):
    """Outline of the projection of a body in a top or side view, closed at its end profiles."""
    rows = body.rows
    upper = np.column_stack([rows[:, 0], rows[:, column_centre] + 0.5 * rows[:, column_size]])
    lower = np.column_stack([rows[:, 0], rows[:, column_centre] - 0.5 * rows[:, column_size]])
    return np.vstack([upper, lower[::-1], upper[:1]])


def _union_contour(ax, x, bodies, color, lw, zorder, step=0.002):
    """Contour of the union of the cross sections of the bodies at x, without the inner lines of the overlap."""
    y, z = _grid(x, step, margin=0.1)
    inside = np.any([b.inside(x, y, z) for b in bodies], axis=0).astype(float)
    ax.contour(y, z, inside, levels=[0.5], colors=[color], linewidths=lw, zorder=zorder)


def _section_patch(x):
    """Cross section of the fuselage at x with the holes the ducts cut, as one patch (holes left open)."""
    y, z = _grid(x, 0.002, margin=0.1)
    fuselage = FUSELAGE_BODY.inside(x, y, z)
    duct = np.any([b.inside(x, y, z) for b in DUCT_BODIES], axis=0)
    return y, z, (fuselage & ~duct).astype(float)


def figure_intake():
    """(a) Top view of the fuselage and the ducts; (b), (c) cross sections of the fuselage after the cut."""
    with figure_style():
        fig = plt.figure(figsize=(FULL_WIDTH, 4.5))
        grid = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.18, wspace=0.05)
        top = fig.add_subplot(grid[0, :])
        sections = [fig.add_subplot(grid[1, k]) for k in range(2)]

        # (a) top view: the fuselage as context, the ducts as data, the mirrored side in amber
        fuselage = _band(FUSELAGE_BODY, 1, 2)
        top.plot(*fuselage.T, color=MUTED, lw=LINE["reference"], zorder=1)
        for body, color in ((MIRRORED_BODY, MIRRORED), (CHANNEL_BODY, DUCT), (INTAKE_BODY, DUCT)):
            band = _band(body, 1, 2)
            top.add_patch(Polygon(band, closed=True, facecolor=color, alpha=0.10, edgecolor="none", zorder=2))
            top.add_patch(Polygon(band, closed=True, fill=False, edgecolor=color, lw=LINE["data"], zorder=3,
                                  joinstyle="round"))
        # stations of the cross sections, as short ticks beside the fuselage, named by their panel
        for x, name in zip(STATIONS, ("b", "c"), strict=True):
            half = 0.5 * FUSELAGE_BODY.station(x)[1]
            for sign in (1.0, -1.0):
                top.plot([x, x], [sign * (half + 0.12), sign * (half + 0.42)], color=INK2, lw=LINE["secondary"])
            label(top, (x, -(half + 0.42)), f"({name})", (0, -3), va="top", color=INK2)
        # names of the ducts at their ends, outside the fuselage where there is room
        entry = INTAKE_BODY.sections[0]
        label(top, (entry[1], entry[2] + 0.5 * entry[3]), "intake duct", (-2, 6), ha="right", va="bottom")
        label(top, (entry[1], -entry[2] - 0.5 * entry[3]), "intake duct, mirrored at the x-z plane", (-2, -6),
              ha="right", va="top")
        # the channel is named beside its end, inside the fuselage, where no line runs
        label(top, (ENGINE_FACE, 0.0), "channel duct,\nup to the engine face", (5, 0), ha="left")
        top.annotate("fuselage", xy=(12.8, 0.5 * FUSELAGE_BODY.station(12.8)[1]), xytext=(13.3, 1.15),
                     textcoords="data", ha="left", va="center", fontsize=NOTE, color=INK2, zorder=7,
                     arrowprops={**leader(), "relpos": (0.0, 0.5)})
        axes_cross(top, (14.6, -1.75),[(1, 0), (0, 1)], ["x", "y"], 0.6, [(6, 0), (0, 7)])
        top.set_xlim(-0.4, 15.6)
        top.set_ylim(-2.0, 2.05)
        top.set_aspect("equal")
        top.axis("off")
        top.set_title("(a) Top view")

        # (b), (c) cross sections seen from behind: the fuselage with the holes cut by the duct assembly
        for ax, x, name in zip(sections, STATIONS, ("b", "c"), strict=True):
            y, z, solid = _section_patch(x)
            ax.contourf(y, z, solid, levels=[0.5, 1.5], colors=[MUTED], alpha=0.18, zorder=1)
            fy, fw, fh, fz = FUSELAGE_BODY.station(x)
            ax.plot(*_ellipse(fy, fw, fh, fz).T, color=MUTED, lw=LINE["reference"], zorder=2)
            _union_contour(ax, x, DUCT_BODIES, DUCT, LINE["data"], 3)
            axes_cross(ax, (-1.45, fz - 0.5 * fh), [(1, 0), (0, 1)], ["y", "z"], 0.3, [(6, 0), (0, 7)])
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-0.78, 0.85)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(f"({name}) Section at x = {x:g} m, seen from behind", fontsize=FONT_SIZE["base"])

        handles = [Line2D([], [], color=DUCT, lw=LINE["data"]), Line2D([], [], color=MIRRORED, lw=LINE["data"]),
                   Line2D([], [], color=MUTED, lw=6, alpha=0.3)]
        fig.legend(handles, ["duct", "mirrored side of a duct", "fuselage after the cut"], loc="lower center",
                   ncol=3, bbox_to_anchor=(0.5, -0.02), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "ductIntake.png")


def equation_point():
    save_equation([r"P = t_{\mathrm{parent}} + T_{\mathrm{assembly}}\,M\,T_{\mathrm{duct}}\,p"],
                  EQUATIONS / "ductPoint")


# --------------------------------------------------------------------- example
def _title(name):
    stem = name.rstrip("0123456789")
    number = name[len(stem):]
    words = "".join(f" {c.lower()}" if c.isupper() else c for c in stem)
    return words[:1].upper() + words[1:] + (f" {number}" if number else "")


def section_xml(uid, section):
    name, x, yc, width, height, zc = section
    element = "\n".join([
        f'<element uID="{uid}_{name}_element">', f"    <name>{_title(name)} element</name>",
        f"    <profileUID>{PROFILE_UID}</profileUID>",
        indent(transformation_xml(scaling=(1.0, width, height), translation=(0.0, yc, zc)), 1), "</element>",
    ])
    return "\n".join([
        f'<section uID="{uid}_{name}">', f"    <name>{_title(name)} section</name>",
        indent(transformation_xml(translation=(x, 0.0, 0.0)), 1),
        "    <elements>", indent(element, 2), "    </elements>", "</section>",
    ])


def segments_xml(uid, sections):
    items = []
    for k in range(len(sections) - 1):
        items.append("\n".join([
            f'<segment uID="{uid}_segment{k + 1}">', f"    <name>Segment {k + 1}</name>",
            f"    <fromElementUID>{uid}_{sections[k][0]}_element</fromElementUID>",
            f"    <toElementUID>{uid}_{sections[k + 1][0]}_element</toElementUID>", "</segment>",
        ]))
    return collection("segments", items)


def body_xml(tag, uid, name, description, sections, attributes="", parent=None):
    return "\n".join([
        f'<{tag} uID="{uid}"{attributes}>', f"    <name>{name}</name>", f"    <description>{description}</description>",
        *([f"    <parentUID>{parent}</parentUID>"] if parent else []),
        indent(transformation_xml(), 1),
        indent(collection("sections", [section_xml(uid, s) for s in sections]), 1),
        indent(segments_xml(uid, sections), 1),
        f"</{tag}>",
    ])


def fuselage_xml():
    return body_xml("fuselage", FUSELAGE_UID, "Fuselage",
                    "Fuselage of a single-engine fighter with an intake at each side", FUSELAGE)


def intake_xml():
    return body_xml("duct", INTAKE_UID, "Intake duct",
                    "Intake duct from the intake at the right side of the fuselage to the channel, mirrored to the "
                    "left side", INTAKE, attributes=' symmetry="x-z-plane"')


def channel_xml():
    return body_xml("duct", CHANNEL_UID, "Channel duct",
                    "Channel in which the two intake ducts merge, up to the engine face", CHANNEL)


def assembly_xml():
    return "\n".join([
        f'<ductAssembly uID="{ASSEMBLY_UID}">', "    <name>Intake ducts</name>",
        "    <description>Air intake of the engine, cut out of the fuselage</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(transformation_xml(), 1),
        "    <ductUIDs>", f"        <uID>{INTAKE_UID}</uID>", f"        <uID>{CHANNEL_UID}</uID>", "    </ductUIDs>",
        "</ductAssembly>",
    ])


def ducts_xml():
    return "\n".join([intake_xml(), channel_xml(), assembly_xml()])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Ducts",
        description="The intake ducts of a single-engine fighter, cut out of its fuselage by one duct assembly.",
        model_uid="DuctsAircraft",
        model_name="Ducts example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("ducts", ducts_xml())],
    )


def excerpt_ducts_xml():
    """Excerpt for ductsType: the two ducts with their sections folded, and the assembly in full."""

    def folded(text):
        lines = text.splitlines()
        return "\n".join([*lines[:2], "    ...", lines[-1]])

    return collection("ducts", [folded(intake_xml()), folded(channel_xml()), assembly_xml()])


# --------------------------------------------------------------------- report
def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    print("Wall between the intake duct and the skin of the fuselage (negative: duct outside, the side is open):")
    for x in (3.9, 4.3, 4.6, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0):
        print(f"  x = {x:4.1f} m: {wall(x) * 1000:7.0f} mm")
    for x in (8.2, 9.0, 10.0, 10.6):
        print(f"  channel x = {x:4.1f} m: {wall(x, CHANNEL_BODY) * 1000:7.0f} mm")
    # the intake ducts reach into the channel, so that the three bodies form one channel
    x = INTAKE[-1][1]
    yc, w, h, zc = INTAKE_BODY.station(x)
    cy, cw, ch, cz = CHANNEL_BODY.station(x)
    print(f"Overlap at x = {x:g} m: inner edge of the intake duct at y = {yc - 0.5 * w:.3f} m, "
          f"channel to y = {cy + 0.5 * cw:.3f} m")
    print(f"Volume cut out of the fuselage: {removed_volume():.3f} m^3")
    for x in STATIONS:
        print(f"Removed area at x = {x:g} m: {removed_area(x):.4f} m^2")


def main():
    figure_intake()
    equation_point()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in (("ductsType", excerpt_ducts_xml()), ("ductAssemblyType", assembly_xml())):
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

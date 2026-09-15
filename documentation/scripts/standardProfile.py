# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of standardProfileType,
rectangleProfileType and superEllipseProfileType.

Run from the repository root:

    uv run documentation/scripts/standardProfile.py

The script writes

    documentation/figures/standardProfile.png
    documentation/figures/rectangleProfile.png
    documentation/figures/superEllipseProfile.png
    documentation/equations/rectangleProfile.{tex,png}
    documentation/equations/superEllipseProfile.{tex,png}
    examples/fuselageProfiles.xml

and prints the fuselageProfiles excerpt shown in the standardProfileType
documentation. The schema documentation is not written by this script; copy the
printed excerpt there when the example changes.

Conventions shown (as defined in the documentation): a standard profile lies in
the y-z plane, starts at the top and runs over the positive y side first; the
curve parameter is 0 at the top, 0.25 at the right, 0.5 at the bottom and 0.75
at the left.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch

from example_xml import indent, transformation_xml, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_equation, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageProfiles.xml"

CURVE = COLORS["series1"]
LOWER = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]


# ---------------------------------------------------------------------- shapes
@dataclass
class Rectangle:
    uid: str
    name: str
    height_to_width_ratio: float
    corner_radius: float = 0.0

    def contour(self):
        """Points (y, z) in profile order: top center, right, bottom, left, top."""
        r, c = self.height_to_width_ratio, self.corner_radius
        h = r / 2.0

        def arc(yc, zc, a0, a1):
            a = np.linspace(a0, a1, 60)
            return np.column_stack([yc + c * np.cos(a), zc + c * np.sin(a)])

        parts = [
            np.array([[0.0, h], [0.5 - c, h]]),
            arc(0.5 - c, h - c, np.pi / 2, 0.0),
            np.array([[0.5, h - c], [0.5, -h + c]]),
            arc(0.5 - c, -h + c, 0.0, -np.pi / 2),
            np.array([[0.5 - c, -h], [-0.5 + c, -h]]),
            arc(-0.5 + c, -h + c, -np.pi / 2, -np.pi),
            np.array([[-0.5, -h + c], [-0.5, h - c]]),
            arc(-0.5 + c, h - c, np.pi, np.pi / 2),
            np.array([[-0.5 + c, h], [0.0, h]]),
        ]
        return np.vstack(parts)

    def quarter_points(self):
        h = self.height_to_width_ratio / 2.0
        return [(0.0, h), (0.5, 0.0), (0.0, -h), (-0.5, 0.0)]

    def xml(self):
        lines = ["<rectangle>"]
        if self.corner_radius:
            lines.append(f"    <cornerRadius>{self.corner_radius:g}</cornerRadius>")
        lines += [f"    <heightToWidthRatio>{self.height_to_width_ratio:g}</heightToWidthRatio>", "</rectangle>"]
        return "\n".join(lines)


@dataclass
class SuperEllipse:
    uid: str
    name: str
    m_upper: float
    n_upper: float
    m_lower: float
    n_lower: float
    lower_height_fraction: float

    @property
    def z0(self):
        return self.lower_height_fraction - 0.5

    def z(self, y, upper):
        z0 = self.z0
        if upper:
            return z0 + (0.5 - z0) * np.clip(1.0 - np.abs(2.0 * y) ** self.m_upper, 0.0, None) ** (1.0 / self.n_upper)
        return z0 - (0.5 + z0) * np.clip(1.0 - np.abs(2.0 * y) ** self.m_lower, 0.0, None) ** (1.0 / self.n_lower)

    def half(self, upper):
        """Right and left part of one semi-superellipse, from the top or bottom point outwards."""
        y = 0.5 * np.sin(np.linspace(0.0, np.pi / 2, 400))
        right = np.column_stack([y, self.z(y, upper)])
        left = np.column_stack([-y, self.z(y, upper)])
        return right, left

    def contour(self):
        (ur, ul), (lr, ll) = self.half(True), self.half(False)
        return np.vstack([ur, lr[::-1], ll, ul[::-1]])

    def quarter_points(self):
        return [(0.0, 0.5), (0.5, self.z0), (0.0, -0.5), (-0.5, self.z0)]

    def xml(self):
        return "\n".join([
            "<superEllipse>",
            f"    <mUpper>{self.m_upper:g}</mUpper>",
            f"    <nUpper>{self.n_upper:g}</nUpper>",
            f"    <mLower>{self.m_lower:g}</mLower>",
            f"    <nLower>{self.n_lower:g}</nLower>",
            f"    <lowerHeightFraction>{self.lower_height_fraction:g}</lowerHeightFraction>",
            "</superEllipse>",
        ])


# Profiles of the figures; the first two are the ones of the documentation excerpt.
RECTANGLE = Rectangle("RectangleProfile", "Rectangle with rounded corners", 0.75, 0.15)
SUPER_ELLIPSE = SuperEllipse("SuperEllipseProfile", "Superellipse with flattened lower half", 2, 2, 3, 2, 0.4)
RECTANGLE_EXAMPLE = Rectangle("RectangleProfile_example", "Rectangle, corner radius 0.125", 0.5, 0.125)
RECTANGLE_LARGEST_RADIUS = Rectangle("RectangleProfile_largestRadius", "Rectangle with the largest corner radius", 0.5, 0.25)
SUPER_ELLIPSE_EXAMPLES = [
    SuperEllipse("SuperEllipseProfile_example1", "Superellipse with pointed top and boxy bottom", 0.5, 2, 5, 3, 0.25),
    SuperEllipse("CircleProfile", "Circle", 2, 2, 2, 2, 0.5),
    SuperEllipse("DiamondProfile", "Diamond", 1, 1, 1, 1, 0.5),
]


# ------------------------------------------------------------------- equations
EQUATION_FILES = {
    "rectangleProfile": [
        r"\max\left(|y| - \dfrac{1}{2} + c,\ 0\right)^2 + \max\left(|z| - \dfrac{r}{2} + c,\ 0\right)^2 = c^2",
    ],
    "superEllipseProfile": [
        r"|2y|^{m_\mathrm{upper}} + \left|\dfrac{z - z_0}{0.5 - z_0}\right|^{n_\mathrm{upper}} = 1"
        r"\quad \mathrm{for}\ z \geq z_0",
        r"|2y|^{m_\mathrm{lower}} + \left|\dfrac{z - z_0}{0.5 + z_0}\right|^{n_\mathrm{lower}} = 1"
        r"\quad \mathrm{for}\ z < z_0",
        r"z_0 = \mathrm{lowerHeightFraction} - 0.5",
    ],
}


def write_equations():
    for name, lines in EQUATION_FILES.items():
        save_equation(lines, EQUATIONS / name)


# --------------------------------------------------------------------- figures
def style_profile_axes(ax, xlim, ylim, title):
    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks([-0.5, 0.0, 0.5])
    ax.set_yticks([-0.5, 0.0, 0.5])
    ax.set_xlabel("y")
    ax.set_ylabel("z")
    ax.set_title(title)


def dimension(ax, start, end, label, side):
    """Dimension arrow between two points with a label beside its middle."""
    ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "<|-|>", "lw": LINE["reference"],
                                                     "mutation_scale": 6, "shrinkA": 0, "shrinkB": 0, "color": INK})
    middle = (0.5 * (start[0] + end[0]), 0.5 * (start[1] + end[1]))
    offsets = {"below": (0.0, -0.05, "center", "top"), "left": (-0.05, 0.0, "right", "center"),
               "right": (0.05, 0.0, "left", "center")}
    dx, dy, ha, va = offsets[side]
    ax.text(middle[0] + dx, middle[1] + dy, label, fontsize=FONT_SIZE["annotation"], ha=ha, va=va,
            linespacing=1.05)


def figure_standard_profile():
    """Order and curve parameter of both standard profiles."""
    note = FONT_SIZE["annotation"]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.0), gridspec_kw={"wspace": 0.25})
        panels = [
            (axes[0], RECTANGLE, "(a) Rectangle", "t = 0.25"),
            (axes[1], SUPER_ELLIPSE, "(b) Superellipse", "t = 0.25\n(widest point)"),
        ]
        for ax, shape, title, right_label in panels:
            contour = shape.contour()
            ax.fill(contour[:, 0], contour[:, 1], color=CURVE, alpha=0.08, lw=0)
            ax.plot(contour[:, 0], contour[:, 1], color=CURVE)
            top, right, bottom, left = shape.quarter_points()
            for y, z in (top, right, bottom, left):
                ax.plot(y, z, ls="none", marker="o", ms=4.5, color=INK, mec=COLORS["surface"], mew=1.0, zorder=4)
            ax.text(top[0] - 0.05, top[1] + 0.07, "t = 0 (start)", fontsize=note, ha="right", va="bottom")
            ax.text(right[0] + 0.06, right[1], right_label, fontsize=note, ha="left", va="center")
            ax.text(bottom[0], bottom[1] - 0.07, "t = 0.5", fontsize=note, ha="center", va="top")
            ax.text(left[0] - 0.06, left[1], "t = 0.75", fontsize=note, ha="right", va="center")
            # direction of the contour: from the top over the positive y side
            ax.add_patch(FancyArrowPatch((0.05, top[1] + 0.1), (0.36, top[1] + 0.02),
                                         connectionstyle="arc3,rad=-0.25", arrowstyle="-|>", mutation_scale=8,
                                         lw=LINE["secondary"], color=INK2))
            style_profile_axes(ax, (-1.0, 1.1), (-0.72, 0.78), title)
        save_figure(fig, FIGURES / "standardProfile.png")


def figure_rectangle():
    note = FONT_SIZE["annotation"]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.6), gridspec_kw={"wspace": 0.25})
        panels = [
            (axes[0], RECTANGLE_EXAMPLE, "(a) cornerRadius = 0.125"),
            (axes[1], RECTANGLE_LARGEST_RADIUS, "(b) Largest radius, half the height"),
        ]
        for ax, shape, title in panels:
            r, c = shape.height_to_width_ratio, shape.corner_radius
            h = r / 2.0
            contour = shape.contour()
            ax.fill(contour[:, 0], contour[:, 1], color=CURVE, alpha=0.08, lw=0)
            ax.plot(contour[:, 0], contour[:, 1], color=CURVE, zorder=3)
            # corner circle and radius
            center = (0.5 - c, h - c)
            ax.add_patch(Circle(center, c, fill=False, ec=MUTED, lw=LINE["reference"], zorder=2))
            ax.plot(*center, ls="none", marker="o", ms=3, color=INK, zorder=4)
            ax.plot([center[0], 0.5], [center[1], center[1]], color=INK, lw=LINE["reference"], zorder=4)
            ax.text(0.54, center[1], "cornerRadius", fontsize=note, ha="left", va="center")
            # width and height
            ax.plot([-0.5, -0.5], [-h, -h - 0.16], color=INK, lw=0.5)
            ax.plot([0.5, 0.5], [-h, -h - 0.16], color=INK, lw=0.5)
            dimension(ax, (-0.5, -h - 0.12), (0.5, -h - 0.12), "1", "below")
            ax.plot([-0.5, -0.66], [h, h], color=INK, lw=0.5)
            ax.plot([-0.5, -0.66], [-h, -h], color=INK, lw=0.5)
            dimension(ax, (-0.62, -h), (-0.62, h), "heightToWidthRatio", "left")
            ax.set_aspect("equal")
            ax.set_xlim(-1.5, 1.1)
            ax.set_ylim(-0.62, 0.42)
            ax.axis("off")
            ax.set_title(title)
        save_figure(fig, FIGURES / "rectangleProfile.png")


def figure_super_ellipse():
    note = FONT_SIZE["annotation"]
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.9),
                                 gridspec_kw={"wspace": 0.2, "width_ratios": [1.3, 1.0, 1.0]})
        titles = ["(a) Example 1", "(b) Circle", "(c) Diamond"]
        for index, (ax, shape, title) in enumerate(zip(axes, SUPER_ELLIPSE_EXAMPLES, titles, strict=True)):
            (ur, ul), (lr, ll) = shape.half(True), shape.half(False)
            for part in (ur, ul):
                ax.plot(part[:, 0], part[:, 1], color=CURVE, zorder=3)
            for part in (lr, ll):
                ax.plot(part[:, 0], part[:, 1], color=LOWER, zorder=3)
            ax.plot([-0.7, 0.7], [shape.z0, shape.z0], color=MUTED, lw=LINE["reference"], zorder=1)
            ax.text(-0.66, shape.z0 + 0.03, "$z_0$", fontsize=note, color=INK2, ha="left", va="bottom")
            style_profile_axes(ax, (-0.7, 0.7), (-0.62, 0.62), title)
            if index:  # the z axis is the same in all panels
                ax.set_ylabel("")
                ax.set_yticklabels([])
        # lowerHeightFraction in the first example, inside its flat lower part
        z0 = SUPER_ELLIPSE_EXAMPLES[0].z0
        axes[0].plot([0.5, 0.66], [-0.5, -0.5], color=INK, lw=0.5)
        dimension(axes[0], (0.62, -0.5), (0.62, z0), "lower-\nHeight-\nFraction", "right")
        axes[0].set_xlim(-0.7, 1.12)
        handles = [Line2D([], [], color=CURVE), Line2D([], [], color=LOWER), Line2D([], [], color=MUTED,
                                                                                     lw=LINE["reference"])]
        fig.legend(handles, ["upper semi-superellipse (mUpper, nUpper)", "lower semi-superellipse (mLower, nLower)",
                             "$z = z_0$"], loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.06),
                   handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "superEllipseProfile.png")


# --------------------------------------------------------------------- example
def fuselage_profile_xml(shape):
    return "\n".join([
        f'<fuselageProfile uID="{shape.uid}">',
        f"    <name>{shape.name}</name>",
        "    <standardProfile>",
        indent(shape.xml(), 2),
        "    </standardProfile>",
        "</fuselageProfile>",
    ])


def excerpt_xml():
    return "\n".join(["<fuselageProfiles>", indent(fuselage_profile_xml(RECTANGLE), 1),
                      indent(fuselage_profile_xml(SUPER_ELLIPSE), 1), "</fuselageProfiles>"])


def section_xml(uid, name, profile_uid, x, scaling):
    lines = [f'<section uID="{uid}">', f"    <name>{name}</name>"]
    lines.append(indent(transformation_xml(translation=(x, 0.0, 0.0)), 1))
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
    """Fuselage through a circle, the superellipse and the rectangle of the documentation excerpt."""
    sections = [
        ("StandardFuselage_front", "Front section", "CircleProfile", 0.0, (1.0, 1.0, 1.0)),
        ("StandardFuselage_middle", "Middle section", SUPER_ELLIPSE.uid, 3.0, (1.0, 2.0, 2.0)),
        ("StandardFuselage_rear", "Rear section", RECTANGLE.uid, 7.0, (1.0, 1.6, 1.6)),
    ]
    lines = [
        '<fuselage uID="StandardFuselage">',
        "    <name>Fuselage with standard profiles</name>",
        "    <description>Circle (diameter 1 m), superellipse (2 m wide and high) and rectangle with rounded corners "
        "(1.6 m wide, 1.2 m high). Top, sides and bottom of the profiles are connected along the fuselage."
        "</description>",
        indent(transformation_xml(), 1),
        "    <sections>",
    ]
    lines += [indent(section_xml(*section), 2) for section in sections]
    lines += ["    </sections>", "    <segments>"]
    for (from_uid, *_), (to_uid, *_) in zip(sections[:-1], sections[1:], strict=True):
        lines += [
            f'        <segment uID="{from_uid}_segment">',
            "            <name>Segment</name>",
            f"            <fromElementUID>{from_uid}_element</fromElementUID>",
            f"            <toElementUID>{to_uid}_element</toElementUID>",
            "        </segment>",
        ]
    lines += ["    </segments>", "</fuselage>"]
    return "\n".join(lines)


def write_example():
    shapes = [RECTANGLE, SUPER_ELLIPSE, RECTANGLE_EXAMPLE, RECTANGLE_LARGEST_RADIUS, *SUPER_ELLIPSE_EXAMPLES]
    write_cpacs_file(
        EXAMPLE_FILE,
        name="Fuselage standard profiles",
        description="Fuselage profiles defined by rectangles and superellipses, and a fuselage using some of them. "
        "Generated by documentation/scripts/standardProfile.py.",
        model_uid="StandardProfileAircraft",
        model_name="Standard profile example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles="\n".join(fuselage_profile_xml(shape) for shape in shapes),
    )


# ------------------------------------------------------------------------ main
def main():
    write_equations()
    figure_standard_profile()
    figure_rectangle()
    figure_super_ellipse()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the standardProfileType documentation:\n")
    print(excerpt_xml())


if __name__ == "__main__":
    main()

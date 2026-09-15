# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure, equations and example data for the documentation of nacaProfileType.

Run from the repository root:

    uv run documentation/scripts/nacaProfile.py

The script writes

    documentation/figures/nacaProfile.png
    documentation/equations/nacaProfile4Digit.{tex,png}
    examples/wingAirfoils_naca.xml

and prints the wingAirfoils excerpt shown in the nacaProfileType documentation.
The schema documentation is not written by this script; copy the printed excerpt
there when the example changes.

Definition shown (4-digit series, NACA Report 460): thickness distribution
applied perpendicular to the camber line; the coefficient a4 of x^4 is -0.1015
without trailingEdgeThickness and chosen to reach the given total thickness at
x = 1 otherwise.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from example_xml import indent, transformation_xml, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_equation, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "wingAirfoils_naca.xml"

INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]


# ------------------------------------------------------------------ definition
def a4(thickness, trailing_edge_thickness=None):
    if trailing_edge_thickness is None:
        return -0.1015
    return trailing_edge_thickness / (10.0 * thickness) - 0.1036


def naca4(code, x, trailing_edge_thickness=None):
    """Upper and lower surface and camber line of a NACA 4-digit airfoil."""
    m, p, t = int(code[0]) / 100.0, int(code[1]) / 10.0, int(code[2:]) / 100.0
    zt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3
                  + a4(t, trailing_edge_thickness) * x**4)
    if m == 0.0 or p == 0.0:
        zc, dzc = np.zeros_like(x), np.zeros_like(x)
    else:
        zc = np.where(x <= p, m / p**2 * (2 * p * x - x**2), m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x**2))
        dzc = np.where(x <= p, 2 * m / p**2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    theta = np.arctan(dzc)
    upper = (x - zt * np.sin(theta), zc + zt * np.cos(theta))
    lower = (x + zt * np.sin(theta), zc - zt * np.cos(theta))
    return upper, lower, zc, zt


EQUATION_LINES = [
    r"z_t = 5\,t\,\left(0.2969\sqrt{x} - 0.1260\,x - 0.3516\,x^2 + 0.2843\,x^3 + a_4\,x^4\right)",
    r"a_4 = -0.1015\quad \mathrm{without\ trailingEdgeThickness},\qquad"
    r"a_4 = \dfrac{\Delta z_\mathrm{TE}}{10\,t} - 0.1036\quad \mathrm{otherwise}",
    r"z_c = \dfrac{m}{p^2}\left(2px - x^2\right)\quad \mathrm{for}\ x \leq p,\qquad"
    r"z_c = \dfrac{m}{(1-p)^2}\left(1 - 2p + 2px - x^2\right)\quad \mathrm{for}\ x > p",
    r"x_\mathrm{U,L} = x \mp z_t \sin\theta,\qquad z_\mathrm{U,L} = z_c \pm z_t \cos\theta,\qquad"
    r"\theta = \arctan\dfrac{dz_c}{dx}",
]


# ---------------------------------------------------------------------- figure
def figure():
    x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 400)))
    with figure_style():
        fig, (ax, zoom) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9),
                                       gridspec_kw={"width_ratios": [2.3, 1.3], "wspace": 0.3})

        # (a) meaning of the digits of NACA 2412
        (xu, zu), (xl, zl), zc, zt = naca4("2412", x)
        ax.fill(np.concatenate([xu, xl[::-1]]), np.concatenate([zu, zl[::-1]]), color=COLORS["series1"],
                alpha=0.08, lw=0)
        ax.plot(xu, zu, color=COLORS["series1"])
        ax.plot(xl, zl, color=COLORS["series1"])
        ax.plot([0.0, 1.0], [0.0, 0.0], color=MUTED, lw=LINE["reference"])
        ax.plot(x, zc, color=INK2, lw=LINE["secondary"])
        dim = {"arrowstyle": "<|-|>", "lw": LINE["reference"], "mutation_scale": 6, "shrinkA": 0, "shrinkB": 0,
               "color": INK}
        # maximum camber m at p
        ax.annotate("", xy=(0.4, 0.02), xytext=(0.4, 0.0), arrowprops=dim)
        ax.text(0.415, 0.004, "m = 0.02", fontsize=NOTE, ha="left", va="bottom")
        ax.plot([0.4, 0.4], [-0.1, 0.0], color=INK, lw=0.5)
        ax.plot([0.0, 0.0], [-0.1, 0.0], color=INK, lw=0.5)
        ax.annotate("", xy=(0.4, -0.085), xytext=(0.0, -0.085), arrowprops=dim)
        ax.text(0.2, -0.09, "p = 0.4", fontsize=NOTE, ha="center", va="top")
        # maximum thickness t, measured perpendicular to the camber line
        i = int(np.argmax(zt))
        ax.annotate("", xy=(xu[i], zu[i]), xytext=(xl[i], zl[i]), arrowprops=dim)
        ax.text(xu[i] - 0.015, 0.5 * (zu[i] + zc[i]), "t = 0.12", fontsize=NOTE, ha="right", va="center")
        ax.text(0.58, zc[np.searchsorted(x, 0.58)] + 0.005, "camber line", fontsize=NOTE, color=INK2,
                ha="left", va="bottom")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.12, 0.1)
        ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticks([-0.1, 0.0, 0.1])
        ax.set_xlabel("x")
        ax.set_ylabel("z")
        ax.set_title("(a) NACA 2412, z stretched")

        # (b) trailing edge of NACA 0012 for the three cases
        xz = x[x >= 0.93]
        cases = [
            (None, COLORS["series1"], "without trailingEdgeThickness", "0.00252"),
            (0.0, COLORS["series2"], "trailingEdgeThickness = 0", "0"),
            (0.006, COLORS["series3"], "trailingEdgeThickness = 0.006", "0.006"),
        ]
        zoom.plot([0.955, 1.0], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=1)  # chord, ends at the labels
        for te, color, _, value in cases:
            (xu, zu), (xl, zl), _, _ = naca4("0012", xz, te)
            zoom.plot(xu, zu, color=color, zorder=3)
            zoom.plot(xl, zl, color=color, zorder=3)
            # the blunt trailing edge itself, and its total thickness beside its upper end
            zoom.plot([xu[-1], xl[-1]], [zu[-1], zl[-1]], color=color, lw=LINE["secondary"], zorder=3)
            zoom.text(1.006, zu[-1], value, fontsize=NOTE, ha="left", va="center")
        zoom.text(1.006, 0.0068, "total\nthickness", fontsize=NOTE, color=INK2, ha="left", va="top", linespacing=1.05)
        zoom.set_xlim(0.955, 1.045)
        zoom.set_ylim(-0.0075, 0.0075)
        zoom.set_xticks([0.96, 1.0])
        zoom.set_yticks([-0.005, 0.0, 0.005])
        zoom.set_xlabel("x")
        zoom.set_title("(b) Trailing edge, NACA 0012")
        for spine in zoom.spines.values():
            spine.set_visible(True)

        fig.legend([Line2D([], [], color=c) for _, c, _, _ in cases], [label for _, _, label, _ in cases],
                   loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.14), handlelength=1.4, columnspacing=1.6)
        save_figure(fig, FIGURES / "nacaProfile.png")


# --------------------------------------------------------------------- example
AIRFOILS = [
    ("NACA2412", "NACA 2412", "naca4DigitCode", "2412", None),
    ("NACA0012_closedTE", "NACA 0012 with closed trailing edge", "naca4DigitCode", "0012", 0.0),
    ("NACA23012", "NACA 23012", "naca5DigitCode", "23012", None),
]


def wing_airfoil_xml(uid, name, element, code, trailing_edge_thickness):
    lines = [f'<wingAirfoil uID="{uid}">', f"    <name>{name}</name>", "    <nacaProfile>",
             f"        <{element}>{code}</{element}>"]
    if trailing_edge_thickness is not None:
        lines.append(f"        <trailingEdgeThickness>{trailing_edge_thickness:g}</trailingEdgeThickness>")
    lines += ["    </nacaProfile>", "</wingAirfoil>"]
    return "\n".join(lines)


def excerpt_xml():
    return "\n".join(["<wingAirfoils>", *(indent(wing_airfoil_xml(*a), 1) for a in AIRFOILS), "</wingAirfoils>"])


def section_xml(uid, name, airfoil_uid, translation, scaling):
    return "\n".join([
        f'<section uID="{uid}">',
        f"    <name>{name}</name>",
        indent(transformation_xml(translation=translation), 1),
        "    <elements>",
        f'        <element uID="{uid}_element">',
        f"            <name>{name} element</name>",
        f"            <airfoilUID>{airfoil_uid}</airfoilUID>",
        indent(transformation_xml(scaling=scaling), 3),
        "        </element>",
        "    </elements>",
        "</section>",
    ])


def wing_xml():
    return "\n".join([
        '<wing uID="NACAWing" symmetry="x-z-plane">',
        "    <name>Wing with NACA airfoils</name>",
        "    <description>Root: NACA 2412, chord 2 m. Tip: NACA 0012 with closed trailing edge, chord 1 m, "
        "0.5 m behind. Semi-span 5 m. The NACA 23012 airfoil is defined but not used.</description>",
        indent(transformation_xml(), 1),
        "    <sections>",
        indent(section_xml("NACAWing_root", "Root section", "NACA2412", (0.0, 0.0, 0.0), (2.0, 1.0, 2.0)), 2),
        indent(section_xml("NACAWing_tip", "Tip section", "NACA0012_closedTE", (0.5, 5.0, 0.0), (1.0, 1.0, 1.0)), 2),
        "    </sections>",
        "    <segments>",
        '        <segment uID="NACAWing_segment">',
        "            <name>Segment</name>",
        "            <fromElementUID>NACAWing_root_element</fromElementUID>",
        "            <toElementUID>NACAWing_tip_element</toElementUID>",
        "        </segment>",
        "    </segments>",
        "</wing>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Wing with NACA airfoils",
        description="Wing airfoils defined by NACA codes and a wing using them.",
        model_uid="NACAAircraft",
        model_name="NACA example",
        components_tag="wings",
        components=wing_xml(),
        profiles_tag="wingAirfoils",
        profiles="\n".join(wing_airfoil_xml(*a) for a in AIRFOILS),
    )


# ------------------------------------------------------------------------ main
def main():
    save_equation(EQUATION_LINES, EQUATIONS / "nacaProfile4Digit")
    figure()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the nacaProfileType documentation:\n")
    print(excerpt_xml())


if __name__ == "__main__":
    main()

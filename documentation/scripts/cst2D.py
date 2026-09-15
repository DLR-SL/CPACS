# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of cst2DType.

Run from the repository root:

    uv run documentation/scripts/cst2D.py

The script writes

    documentation/figures/cst2D_airfoil.png
    documentation/figures/cst2D_construction.png
    documentation/equations/cst2D_surfaces.{tex,png}
    documentation/equations/cst2D_classFunction.{tex,png}
    documentation/equations/cst2D_shapeFunction.{tex,png}
    examples/wingAirfoils_cst.xml

and prints the wingAirfoil excerpt shown in the cst2DType documentation. The
schema documentation is not written by this script; copy the printed excerpt
there when the example changes.

The example airfoils are least-squares fits of the NACA 2412 and NACA 0012
airfoils (original definition with finite trailing edge thickness), so the
coefficients are derived here rather than typed in. The figures show NACA 2412.

Sign convention (as in the CPACS documentation and TiGL):

    zeta_upper(psi) =  C_upper(psi) * S_upper(psi) + psi * dzeta_TE / 2
    zeta_lower(psi) = -C_lower(psi) * S_lower(psi) - psi * dzeta_TE / 2
"""

from __future__ import annotations

from math import comb
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_equation, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "wingAirfoils_cst.xml"

UPPER = COLORS["series1"]
LOWER = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]

# Example airfoil
N1 = 0.5
N2 = 1.0
ORDER = 5  # six coefficients per side
PSI_EXAMPLE = [0.0, 0.005, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


# --------------------------------------------------------------------------- CST
def class_function(psi, n1, n2):
    return psi**n1 * (1.0 - psi) ** n2


def bernstein(i, n, psi):
    return comb(n, i) * psi**i * (1.0 - psi) ** (n - i)


def shape_function(psi, coefficients):
    n = len(coefficients) - 1
    return sum(b * bernstein(i, n, psi) for i, b in enumerate(coefficients))


def zeta_upper(psi, n1, n2, coefficients, te_thickness):
    return class_function(psi, n1, n2) * shape_function(psi, coefficients) + psi * te_thickness / 2.0


def zeta_lower(psi, n1, n2, coefficients, te_thickness):
    return -class_function(psi, n1, n2) * shape_function(psi, coefficients) - psi * te_thickness / 2.0


# ------------------------------------------------------------------ NACA 4-digit
def naca4(m, p, t, x):
    """Upper and lower surface of a NACA 4-digit airfoil (original definition)."""
    yt = 5.0 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    if m == 0.0 or p == 0.0:  # symmetric airfoil
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    else:
        yc = np.where(x <= p, m / p**2 * (2 * p * x - x**2), m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x**2))
        dyc = np.where(x <= p, 2 * m / p**2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    theta = np.arctan(dyc)
    return (
        (x - yt * np.sin(theta), yc + yt * np.cos(theta)),
        (x + yt * np.sin(theta), yc - yt * np.cos(theta)),
    )


def fit_naca4(code):
    """Fit CST coefficients to a NACA 4-digit airfoil with fixed N1, N2 and trailing edge thickness."""
    m, p, t = int(code[0]) / 100.0, int(code[1]) / 10.0, int(code[2:]) / 100.0
    x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 401)))
    (xu, zu), (xl, zl) = naca4(m, p, t, x)
    te_thickness = round(float(zu[-1] - zl[-1]), 4)

    def fit(psi, target):
        mask = (psi > 1e-6) & (psi < 1.0 - 1e-6)
        psi = psi[mask]
        rhs = target[mask] - psi * te_thickness / 2.0
        basis = np.column_stack([class_function(psi, N1, N2) * bernstein(i, ORDER, psi) for i in range(ORDER + 1)])
        coefficients, *_ = np.linalg.lstsq(basis, rhs, rcond=None)
        return [round(float(c), 4) for c in coefficients]

    upper_b = fit(xu, zu)
    lower_b = fit(xl, -zl)  # lower side: zeta = -C*S - psi*dzeta/2

    # Compared where psi = x lies on [0, 1]; near the leading edge the cambered
    # NACA upper side reaches slightly negative x, which CST cannot represent.
    valid_u = (xu >= 0.0) & (xu <= 1.0)
    valid_l = (xl >= 0.0) & (xl <= 1.0)
    error = max(
        np.max(np.abs(zeta_upper(xu[valid_u], N1, N2, upper_b, te_thickness) - zu[valid_u])),
        np.max(np.abs(zeta_lower(xl[valid_l], N1, N2, lower_b, te_thickness) - zl[valid_l])),
    )
    return upper_b, lower_b, te_thickness, float(error)


# --------------------------------------------------------------------- equations
EQUATION_FILES = {
    "cst2D_surfaces": [
        r"\zeta_\mathrm{upper}(\psi) = C_\mathrm{upper}(\psi)\,S_\mathrm{upper}(\psi) + \psi\,\dfrac{\Delta\zeta_\mathrm{TE}}{2}",
        r"\zeta_\mathrm{lower}(\psi) = -\,C_\mathrm{lower}(\psi)\,S_\mathrm{lower}(\psi) - \psi\,\dfrac{\Delta\zeta_\mathrm{TE}}{2}",
    ],
    "cst2D_classFunction": [
        r"C(\psi) = \psi^{N_1}\,\left(1-\psi\right)^{N_2}",
    ],
    "cst2D_shapeFunction": [
        r"S(\psi) = \sum_{i=0}^{n} B_i\,\dfrac{n!}{i!\,(n-i)!}\,\psi^{i}\,\left(1-\psi\right)^{n-i}",
    ],
}


def write_equations():
    for name, lines in EQUATION_FILES.items():
        save_equation(lines, EQUATIONS / name)


# ----------------------------------------------------------------------- figures
def figure_airfoil(upper_b, lower_b, te_thickness):
    psi = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 600)))
    zu = zeta_upper(psi, N1, N2, upper_b, te_thickness)
    zl = zeta_lower(psi, N1, N2, lower_b, te_thickness)
    note = FONT_SIZE["annotation"]

    with figure_style():
        width_ratio = 3.1
        fig, (ax, zoom) = plt.subplots(
            1, 2, figsize=(FULL_WIDTH, 2.6), gridspec_kw={"width_ratios": [width_ratio, 1.0], "wspace": 0.22}
        )

        # ---------------------------------------------------------- main view
        ax.fill_between(psi, zl, zu, color=UPPER, alpha=0.08, lw=0, zorder=1)
        ax.axhline(0.0, color=MUTED, lw=LINE["reference"], zorder=2)
        ax.plot(psi, zu, color=UPPER, zorder=3)
        ax.plot(psi, zl, color=LOWER, zorder=3)
        ax.plot([1.0, 1.0], [zl[-1], zu[-1]], color=INK, lw=LINE["secondary"], zorder=3)

        # psi sampling positions on the chord
        ax.plot(PSI_EXAMPLE, np.zeros(len(PSI_EXAMPLE)), ls="none", marker="|", ms=6, mew=LINE["secondary"],
                color=INK, zorder=4)
        ax.annotate("psi: sampling positions", xy=(0.1, -0.005), xytext=(0.0, -0.118), arrowprops=leader(),
                    ha="left", va="center", fontsize=note)

        # leading and trailing edge
        ax.plot([0.0], [0.0], marker="o", ms=4, color=INK, zorder=5)
        ax.annotate("leading edge (0, 0)", xy=(0.0, 0.0), xytext=(-0.07, 0.15), arrowprops=leader(),
                    ha="left", va="center", fontsize=note)
        ax.annotate("trailing edge (1, 0)", xy=(1.0, 0.0), xytext=(1.06, -0.075), arrowprops=leader(),
                    ha="right", va="center", fontsize=note)
        ax.text(0.75, 0.009, "chord", color=INK2, fontsize=note, ha="center", va="bottom")

        # zeta_upper and zeta_lower at one station: colored arrows, ink labels
        station = 0.3
        zu_s = zeta_upper(station, N1, N2, upper_b, te_thickness)
        zl_s = zeta_lower(station, N1, N2, lower_b, te_thickness)
        arrow = {"arrowstyle": "-|>", "lw": LINE["secondary"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0}
        ax.annotate("", xy=(station, zu_s), xytext=(station, 0.0), arrowprops={**arrow, "color": UPPER}, zorder=4)
        ax.annotate("", xy=(station, zl_s), xytext=(station, 0.0), arrowprops={**arrow, "color": LOWER}, zorder=4)
        ax.text(station + 0.012, 0.5 * zu_s, r"$\zeta_\mathrm{upper}(\psi) > 0$", va="center", fontsize=note)
        ax.text(station + 0.012, zl_s - 0.025, r"$\zeta_\mathrm{lower}(\psi) < 0$", va="center", fontsize=note)

        # legend: identity by line key, parameters in ink
        handles = [Line2D([], [], color=UPPER), Line2D([], [], color=LOWER)]
        ax.legend(handles, ["upper side: upperN1, upperN2, upperB", "lower side: lowerN1, lowerN2, lowerB"],
                  loc="upper right", bbox_to_anchor=(1.0, 1.0), handlelength=1.6, borderaxespad=0.0,
                  labelspacing=0.3)

        xlim, ylim = (-0.08, 1.1), (-0.135, 0.215)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.set_xlabel(r"$\psi = x/c$")
        ax.set_ylabel(r"$\zeta = z/c$")
        ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([-0.1, 0.0, 0.1])
        ax.set_title("CST profile in normalized coordinates")

        # zoom window
        window = (0.93, 1.012, -0.012, 0.012)
        ax.add_patch(plt.Rectangle((window[0], window[2]), window[1] - window[0], window[3] - window[2],
                                   fill=False, ec=MUTED, lw=LINE["reference"], zorder=6))

        # ---------------------------------------------------------- TE zoom
        mask = psi >= window[0] - 0.01
        zoom.fill_between(psi[mask], zl[mask], zu[mask], color=UPPER, alpha=0.08, lw=0)
        zoom.axhline(0.0, color=MUTED, lw=LINE["reference"])
        zoom.plot(psi[mask], zu[mask], color=UPPER)
        zoom.plot(psi[mask], zl[mask], color=LOWER)
        zoom.plot([1.0, 1.0], [zl[-1], zu[-1]], color=INK, lw=LINE["secondary"])
        dim = {"arrowstyle": "<|-|>", "lw": LINE["reference"], "mutation_scale": 6, "shrinkA": 0, "shrinkB": 0,
               "color": INK}
        zoom.annotate("", xy=(1.006, zu[-1]), xytext=(1.006, zl[-1]), arrowprops=dim)
        for z in (zu[-1], zl[-1]):
            zoom.plot([1.0, 1.009], [z, z], color=INK, lw=0.5)
        zoom.annotate(r"$\Delta\zeta_\mathrm{TE}$ =" + "\ntrailingEdgeThickness",
                      xy=(1.006, -0.0004), xytext=(0.935, -0.0092), arrowprops=leader(),
                      ha="left", va="center", fontsize=note)
        zoom.set_xlim(window[0], window[1])
        zoom.set_ylim(window[2], window[3])
        zoom.set_xticks([0.95, 1.0])
        zoom.set_yticks([-0.01, 0.0, 0.01])
        zoom.set_title("Trailing edge (zoomed)")
        for spine in zoom.spines.values():
            spine.set_visible(True)
        # same height as the equal-aspect main view
        zoom.set_box_aspect((ylim[1] - ylim[0]) / (xlim[1] - xlim[0]) * width_ratio)

        save_figure(fig, FIGURES / "cst2D_airfoil.png")


def figure_construction(upper_b, te_thickness):
    psi = np.linspace(0.0, 1.0, 600)
    note = FONT_SIZE["annotation"]

    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.5), gridspec_kw={"wspace": 0.62})

        # (a) class function: the used one highlighted, alternatives in neutral gray
        ax = axes[0]
        ax.plot(psi, class_function(psi, 0.5, 0.5), color=MUTED, lw=LINE["secondary"])
        ax.plot(psi, class_function(psi, 1.0, 1.0), color=MUTED, lw=LINE["secondary"])
        ax.plot(psi, class_function(psi, N1, N2), color=UPPER)
        ax.text(0.5, 0.515, "elliptic (0.5, 0.5)", ha="center", va="bottom", fontsize=note, color=INK2)
        ax.text(0.5, 0.2, "biconvex\n(1.0, 1.0)", ha="center", va="top", fontsize=note, color=INK2)
        # no leader line here: it would look like one of the gray comparison curves
        ax.legend([Line2D([], [], color=UPPER)], ["round nose\n(0.5, 1.0)"], loc="upper right",
                  bbox_to_anchor=(1.0, 1.0), borderaxespad=0.0, handlelength=1.6, fontsize=note)
        ax.set_title(r"(a) Class function $C(\psi)$")
        ax.set_ylim(0.0, 0.78)
        ax.set_yticks([0.0, 0.25, 0.5])

        # (b) shape function: weighted Bernstein terms in the light step, sum in series 1
        ax = axes[1]
        n = len(upper_b) - 1
        for i, b in enumerate(upper_b):
            ax.plot(psi, b * bernstein(i, n, psi), color=COLORS["series1Light"], lw=LINE["secondary"])
            peak = i / n
            ha = "left" if i == 0 else "right" if i == n else "center"
            x = {"left": 0.03, "right": 0.97}.get(ha, peak)
            ax.text(x, b * bernstein(i, n, peak) + 0.005, f"$B_{i}$", fontsize=note - 0.5, color=INK2,
                    ha=ha, va="bottom")
        ax.plot(psi, shape_function(psi, upper_b), color=UPPER)
        ax.text(0.5, shape_function(0.5, upper_b) + 0.012, r"$S(\psi)=\sum\, B_i\, b_{i,n}(\psi)$",
                ha="center", va="bottom", fontsize=note)
        ax.set_title(r"(b) Shape function $S_\mathrm{upper}(\psi)$")
        ax.set_ylim(0.0, 0.3)
        ax.set_yticks([0.0, 0.1, 0.2, 0.3])

        # (c) upper side
        ax = axes[2]
        zu = zeta_upper(psi, N1, N2, upper_b, te_thickness)
        ax.fill_between(psi, 0.0, zu, color=UPPER, alpha=0.08, lw=0)
        ax.axhline(0.0, color=MUTED, lw=LINE["reference"])
        ax.plot(psi, zu, color=UPPER)
        ax.set_title(r"(c) Upper side $\zeta_\mathrm{upper}(\psi)$")
        ax.set_ylim(-0.01, 0.1)
        ax.set_yticks([0.0, 0.05, 0.1])

        for ax in axes:
            ax.set_xlim(0.0, 1.0)
            ax.set_xticks([0.0, 0.5, 1.0])
            ax.set_xlabel(r"$\psi$")

        # operators between the panels
        for left, right, symbol in [(axes[0], axes[1], "×"), (axes[1], axes[2], "=")]:
            # left part of the gap; the right part holds the tick labels of the next panel
            x = left.get_position().x1 + 0.3 * (right.get_position().x0 - left.get_position().x1)
            y = 0.5 * (left.get_position().y0 + left.get_position().y1)
            fig.text(x, y, symbol, fontsize=FONT_SIZE["operator"], ha="center", va="center", color=INK2)

        save_figure(fig, FIGURES / "cst2D_construction.png")


# ----------------------------------------------------------------------- example
EXAMPLE_AIRFOILS = [
    (
        "2412",
        "Cambered NACA 2412 airfoil with finite trailing edge thickness. "
        "Upper and lower side have different coefficients; positive lowerB values place the lower side below the chord.",
    ),
    (
        "0012",
        "Symmetric NACA 0012 airfoil with finite trailing edge thickness. "
        "Upper and lower side have identical parameters.",
    ),
]


def wing_airfoil_xml(code, upper_b, lower_b, te_thickness, description=None):
    """wingAirfoil element, starting at column 0 and indented by four spaces per level."""
    vector = lambda values: ";".join(f"{v:g}" for v in values)  # noqa: E731
    lines = [
        f'<wingAirfoil uID="NACA{code}_CST">',
        f"    <name>NACA {code} (CST)</name>",
    ]
    if description:
        lines.append(f"    <description>{description}</description>")
    lines += [
        "    <cst2D>",
        f"        <psi>{vector(PSI_EXAMPLE)}</psi>",
        f"        <upperN1>{N1}</upperN1>",
        f"        <upperN2>{N2}</upperN2>",
        f"        <upperB>{vector(upper_b)}</upperB>",
        f"        <lowerN1>{N1}</lowerN1>",
        f"        <lowerN2>{N2}</lowerN2>",
        f"        <lowerB>{vector(lower_b)}</lowerB>",
        f"        <trailingEdgeThickness>{te_thickness}</trailingEdgeThickness>",
        "    </cst2D>",
        "</wingAirfoil>",
    ]
    return "\n".join(lines)


def transformation_xml(rotation=(0.0, 0.0, 0.0), scaling=(1.0, 1.0, 1.0), translation=(0.0, 0.0, 0.0)):
    parts = ["<transformation>"]
    for name, values in (("rotation", rotation), ("scaling", scaling), ("translation", translation)):
        parts.append(f"    <{name}>")
        parts += [f"        <{axis}>{value:g}</{axis}>" for axis, value in zip("xyz", values, strict=True)]
        parts.append(f"    </{name}>")
    parts.append("</transformation>")
    return parts


def section_xml(uid, name, airfoil_uid, section_translation, element_rotation, element_scaling):
    lines = [f'<section uID="{uid}">', f"    <name>{name}</name>"]
    lines += ["    " + line for line in transformation_xml(translation=section_translation)]
    lines += [
        "    <elements>",
        f'        <element uID="{uid}_element">',
        f"            <name>{name} element</name>",
        f"            <airfoilUID>{airfoil_uid}</airfoilUID>",
    ]
    lines += ["            " + line for line in transformation_xml(rotation=element_rotation, scaling=element_scaling)]
    lines += ["        </element>", "    </elements>", "</section>"]
    return lines


def wing_xml():
    """Tapered, swept wing with the cambered airfoil at the root and the symmetric one at the tip.

    Chord lengths are set by the element scaling (x and z), span, sweep and
    dihedral by the section translation, twist by the element rotation about y.
    """
    lines = [
        '<wing uID="CSTWing" symmetry="x-z-plane">',
        "    <name>Wing with CST airfoils</name>",
        "    <description>Root: NACA 2412 (CST), chord 2 m. Tip: NACA 0012 (CST), chord 0.8 m, "
        "twisted by -2 deg about y (nose down). Semi-span 6 m.</description>",
    ]
    lines += ["    " + line for line in transformation_xml()]
    lines.append("    <sections>")
    for section in (
        section_xml("CSTWing_root", "Root section", "NACA2412_CST", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 1.0, 2.0)),
        section_xml("CSTWing_tip", "Tip section", "NACA0012_CST", (1.2, 6.0, 0.3), (0.0, -2.0, 0.0), (0.8, 1.0, 0.8)),
    ):
        lines += ["        " + line for line in section]
    lines += [
        "    </sections>",
        "    <segments>",
        '        <segment uID="CSTWing_segment">',
        "            <name>Segment</name>",
        "            <fromElementUID>CSTWing_root_element</fromElementUID>",
        "            <toElementUID>CSTWing_tip_element</toElementUID>",
        "        </segment>",
        "    </segments>",
        "</wing>",
    ]
    return "\n".join(lines)


def write_example(fits):
    indent = " " * 16
    airfoils = "\n".join(
        "\n".join(indent + line for line in wing_airfoil_xml(code, *fits[code][:3], description).splitlines())
        for code, description in EXAMPLE_AIRFOILS
    )
    wing = "\n".join(" " * 20 + line for line in wing_xml().splitlines())
    EXAMPLE_FILE.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<cpacs xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:noNamespaceSchemaLocation="../schema/cpacs_schema.xsd">
    <header>
        <name>Wing with CST airfoils</name>
        <description>Wing airfoils defined by the class-shape transformation (CST) and a wing using them. Generated by documentation/scripts/cst2D.py.</description>
        <version>1.0.0</version>
        <versionInfos>
            <versionInfo version="1.0.0">
                <creator>DLR-SL</creator>
                <timestamp>2026-09-15T12:00:00</timestamp>
                <description>Initial data set</description>
                <cpacsVersion>3.5</cpacsVersion>
            </versionInfo>
        </versionInfos>
    </header>
    <vehicles>
        <aircraft>
            <model uID="CSTAircraft">
                <name>CST example</name>
                <wings>
{wing}
                </wings>
            </model>
        </aircraft>
        <profiles>
            <wingAirfoils>
{airfoils}
            </wingAirfoils>
        </profiles>
    </vehicles>
</cpacs>
""",
        encoding="utf-8",
        newline="\n",
    )


# -------------------------------------------------------------------------- main
def main():
    fits = {code: fit_naca4(code) for code, _ in EXAMPLE_AIRFOILS}
    upper_b, lower_b, te_thickness, _ = fits["2412"]

    write_equations()
    figure_airfoil(upper_b, lower_b, te_thickness)
    figure_construction(upper_b, te_thickness)
    write_example(fits)

    for code, (_, _, _, error) in fits.items():
        print(f"NACA {code}: max. deviation of the CST fit {error:.2e} (relative to chord)")
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the cst2DType documentation:\n")
    print(wing_airfoil_xml("2412", upper_b, lower_b, te_thickness))


if __name__ == "__main__":
    main()

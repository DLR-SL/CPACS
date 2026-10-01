# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure for the documentation of local coordinate systems via parentUID (cpacsType, section 4.3).

Run from the repository root:

    uv run documentation/scripts/componentHierarchy.py

The script writes

    documentation/figures/componentHierarchy.png

Definition shown (as in the documentation): a component without parentUID is placed by its
transformation directly in the CPACS coordinate system, and any number of components may be
without parentUID. A component with parentUID follows the translation of its parent. The figure
shows two such hierarchies of one aircraft: the fuselage with the vertical and the horizontal
tail, and the main wing with the engine pylons and the engines on them. The aircraft is the one of
aeroPerformance.py.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch, Polygon

from aeroPerformance import (FIN, TAILPLANE, WING, fin_side, fuselage_side, lifting_surface_section,
                             lifting_surface_side, nacelle_center_z, nacelle_side, pylon_side, NACELLE)
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure

FIGURES = Path(__file__).resolve().parents[1] / "figures"

INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
PLATE = COLORS["surface"]
NOTE = FONT_SIZE["annotation"]
# One color per hierarchy: everything that hangs on the fuselage, and everything that hangs on the main wing.
FUSELAGE_TREE = COLORS["series1"]
WING_TREE = COLORS["series2"]

# Hierarchy as rows of the tree: each row is a chain of (component, parentUID) from a component without parent.
CHAINS = [
    (FUSELAGE_TREE, [("fuselage", None), ("vertical tail", "fuselage"), ("horizontal tail", "vertical tail")]),
    (WING_TREE, [("main wing", None), ("engine pylons", "main wing"), ("engines", "engine pylons")]),
]


def part(ax, outline, color, zorder):
    """A component: opaque in the plate color, so that it hides what lies behind it, with the wash of its color."""
    ax.add_patch(Polygon(outline, closed=True, lw=0, fc=PLATE, zorder=zorder))
    ax.add_patch(Polygon(outline, closed=True, lw=LINE["secondary"], ec=color, fc=(color, 0.10),
                         joinstyle="round", zorder=zorder + 0.01))


def side_view(ax):
    """Side view seen from the left, x to the right, z upwards; each component labelled at itself."""
    part(ax, fin_side(), FUSELAGE_TREE, 1)
    part(ax, fuselage_side(), FUSELAGE_TREE, 2)
    part(ax, lifting_surface_side(TAILPLANE), FUSELAGE_TREE, 3)
    part(ax, pylon_side(), WING_TREE, 3)
    part(ax, lifting_surface_side(WING), WING_TREE, 4)
    part(ax, nacelle_side(), WING_TREE, 5)

    def name(xy, text, ha="left", va="center"):
        ax.text(*xy, text, ha=ha, va=va, fontsize=NOTE, color=INK, zorder=8)

    (_, fin_tip_te) = FIN["tip"]
    (x_tip, z_tip), chord_tip = lifting_surface_section(WING, WING["semi_span"])
    (x_ht, z_ht), chord_ht = lifting_surface_section(TAILPLANE, TAILPLANE["semi_span"])
    name((3.5, 0.6), "fuselage")
    name((fin_tip_te[0] + 0.8, fin_tip_te[1] - 0.6), "vertical tail")
    name((x_ht + chord_ht + 1.0, z_ht), "horizontal tail")
    name((x_tip + chord_tip + 0.6, z_tip), "main wing")
    name((sum(NACELLE["x"]) / 2, nacelle_center_z() - NACELLE["radius"] - 0.5), "engines", ha="center",
         va="top")
    # color key: text in ink, the color shown by a swatch (one entry per hierarchy)
    handles = [Patch(fc=(color, 0.10), ec=color, lw=LINE["secondary"]) for color, _ in CHAINS]
    texts = [f"hierarchy {k + 1}: {chain[0][0]} and the components below it" for k, (_, chain) in enumerate(CHAINS)]
    ax.legend(handles, texts, loc="upper left", bbox_to_anchor=(0.0, 0.96), frameon=False, fontsize=NOTE,
              handlelength=1.6, handleheight=0.9, labelcolor=INK, borderaxespad=0.0)
    ax.set_xlim(-1.0, 47.0)
    ax.set_ylim(-5.6, 7.2)
    ax.set_aspect("equal")
    ax.axis("off")


def tree(ax, height):
    """Hierarchy from left to right: the CPACS coordinate system, then one row per chain of components.

    The axes are laid out in inches (ax spans the full figure width), so that boxes fit their text.
    """
    first_w, box_w, box_h, gap, row = 1.25, 1.78, 0.46, 0.22, 0.62
    y0 = -0.32

    def box(x, y, w, color, title, note=None):
        ax.add_patch(FancyBboxPatch((x, y - box_h / 2), w, box_h, boxstyle="round,pad=0,rounding_size=0.05",
                                    lw=LINE["secondary"], ec=color, fc=(color, 0.10), zorder=2))
        if note is None:
            ax.text(x + 0.09, y, title, ha="left", va="center", fontsize=NOTE, color=INK, zorder=3)
            return
        ax.text(x + 0.09, y + 0.09, title, ha="left", va="center", fontsize=NOTE, color=INK, zorder=3)
        ax.text(x + 0.09, y - 0.1, note, ha="left", va="center", fontsize=NOTE - 1.0, color=INK2, zorder=3,
                family="DejaVu Sans Mono")

    def connector(points):
        ax.plot(*zip(*points), color=MUTED, lw=LINE["reference"], zorder=1, solid_capstyle="butt")

    box(0.0, y0, first_w, MUTED, "CPACS coordinate system" if first_w > 1.6 else "CPACS coordinate\nsystem")
    trunk = first_w + gap / 2
    for k, (color, chain) in enumerate(CHAINS):
        y = y0 - k * row
        start = first_w + gap
        if k:
            connector([(trunk, y0), (trunk, y), (start, y)])
        else:
            connector([(first_w, y0), (start, y0)])
        for j, (component, parent) in enumerate(chain):
            x = start + j * (box_w + gap)
            box(x, y, box_w, color, component, "no parentUID" if parent is None else f"parentUID: {parent}")
            if j:
                connector([(x - gap, y), (x, y)])
    ax.set_xlim(0.0, FULL_WIDTH)
    ax.set_ylim(-height, 0.0)
    ax.set_aspect("equal")
    ax.axis("off")


def figure():
    with figure_style():
        fig = plt.figure(figsize=(FULL_WIDTH, 3.9))
        top = fig.add_axes((0.0, 0.42, 1.0, 0.52))
        bottom = fig.add_axes((0.0, 0.0, 1.0, 0.33))
        side_view(top)
        tree(bottom, 0.33 * fig.get_figheight())
        fig.text(0.0, 0.98, "(a) components of the aircraft, side view", ha="left", va="top",
                 fontsize=FONT_SIZE["base"], color=INK)
        fig.text(0.0, 0.38, "(b) hierarchy via parentUID", ha="left", va="top", fontsize=FONT_SIZE["base"], color=INK)
        save_figure(fig, FIGURES / "componentHierarchy.png")


def main():
    figure()


if __name__ == "__main__":
    main()

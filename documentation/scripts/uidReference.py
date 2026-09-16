# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure for the documentation of references to symmetric components
(symmetry attribute of stringUIDBaseType).

Run from the repository root:

    uv run documentation/scripts/uidReference.py

The script writes

    documentation/figures/uidReferenceSymmetry.png

Definition shown (as in the documentation): a wing with symmetry="x-z-plane" consists
of its defined side and its mirrored side. An engine pylon references the wing as parent;
the symmetry attribute of the reference selects the side the pylon belongs to:
def = defined side, symm = mirrored side, full = both sides (default).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure

FIGURES = Path(__file__).resolve().parents[1] / "figures"

DEFINED = COLORS["series1"]
MIRRORED = COLORS["mirrored"]
PYLON = COLORS["series3"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# Wing of the defined side in (x, y): leading and trailing edge at root and tip
WING = np.array([(0.0, 0.0), (1.6, 5.0), (2.4, 5.0), (2.2, 0.0)])
# Engine nacelle below the wing, in (x, y): front and rear end, lateral position and width
NACELLE = {"x": (-1.1, 1.0), "y": 2.0, "width": 0.7}

CASES = [("def", "defined side only"), ("symm", "mirrored side only"), ("full", "both sides (default)")]


def mirror(points):
    return points * np.array([1.0, -1.0])


def top_view(points):
    """Top view with the flight direction up: y to the right, x downwards."""
    points = np.atleast_2d(points)
    return np.column_stack([points[:, 1], -points[:, 0]])


def nacelle_outline():
    (x0, x1), y, w = NACELLE["x"], NACELLE["y"], NACELLE["width"]
    return np.array([(x0, y - 0.35 * w), (x0 + 0.3, y - 0.5 * w), (x1, y - 0.5 * w), (x1, y + 0.5 * w),
                     (x0 + 0.3, y + 0.5 * w), (x0, y + 0.35 * w)])


def draw_polygon(ax, points, color, zorder):
    ax.add_patch(Polygon(top_view(points), closed=True, lw=LINE["data"], ec=color, fc=(color, 0.08),
                         joinstyle="round", zorder=zorder))


def figure():
    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.0), gridspec_kw={"wspace": 0.06})
        for ax, (value, meaning) in zip(axes, CASES, strict=True):
            ax.plot([0.0, 0.0], [1.7, -2.8], color=MUTED, lw=LINE["reference"], zorder=1)
            draw_polygon(ax, WING, DEFINED, 2)
            draw_polygon(ax, mirror(WING), MIRRORED, 2)
            sides = {"def": [nacelle_outline()], "symm": [mirror(nacelle_outline())],
                     "full": [nacelle_outline(), mirror(nacelle_outline())]}[value]
            for outline in sides:
                draw_polygon(ax, outline, PYLON, 3)
            ax.set_title(f'symmetry="{value}"\n{meaning}', loc="center", linespacing=1.5)
            ax.set_xlim(-5.3, 5.3)
            ax.set_ylim(-2.9, 2.0)
            ax.set_aspect("equal")
            ax.axis("off")

        first = axes[0]
        first.annotate("x-z plane", xy=(0.0, 1.7), xytext=(4, 0), textcoords="offset points", ha="left",
                       va="center", fontsize=NOTE, color=INK2)
        # axes of the top view
        origin = np.array([-5.0, 1.6])
        for direction, text, offset, ha, va in (((0.0, -1.0), "x", (0, -3), "center", "top"),
                                                ((1.0, 0.0), "y", (3, 0), "left", "center")):
            tip = origin + 0.9 * np.array(direction)
            first.annotate("", xy=tip, xytext=origin, arrowprops={
                "arrowstyle": "-|>", "lw": LINE["reference"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
                "color": INK2})
            first.annotate(text, xy=tip, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE,
                           color=INK2)

        handles = [Polygon([(0, 0)], closed=True, lw=LINE["data"], ec=DEFINED, fc=(DEFINED, 0.08)),
                   Polygon([(0, 0)], closed=True, lw=LINE["data"], ec=MIRRORED, fc=(MIRRORED, 0.08)),
                   Polygon([(0, 0)], closed=True, lw=LINE["data"], ec=PYLON, fc=(PYLON, 0.08))]
        fig.legend(handles, ['wing with symmetry="x-z-plane": defined side', "mirrored side",
                             "engine pylon with nacelle referencing the wing"], loc="lower center", ncol=3,
                   bbox_to_anchor=(0.5, -0.02), handlelength=1.4, columnspacing=1.4)
        save_figure(fig, FIGURES / "uidReferenceSymmetry.png")


def main():
    figure()


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure for the documentation of the center fuselage area of a low-wing aircraft
(centerFuselageAreaType, centerFuselageLowWingConfigurationType and its parts).

Run from the repository root:

    uv run documentation/scripts/fuselageCenterArea.py

The script writes

    documentation/figures/centerFuselageArea.png

The figure is an illustration of the layout the definition describes (Scherer and
Kohlgrüber 2016; Scherer et al. 2013), placed in the fuselage and the wing of the
other examples: the main frames at the front and the rear spar of the wing box and at
the rear end of the bay of the main landing gear, flat pressure bulkheads at the first
and the third main frame, the pressure floor over the bay, the side boxes between the
pressure floor and the skin, the lateral panels between the side boxes and the rear
spar, and the keel beam along the bottom. Its dimensions are not part of an example
file: several parameters of the definition are not specified yet, and the figure
shows the parts, not their parameters.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon, Rectangle

from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, axes_cross, figure_style, label, save_figure
from fuselageBulkheadWall import BAY_AFT_X, REAR_SPAR_X, root_section
from fuselageCutOut import FLOOR_Z
import fuselageStructure as shell
from wing import AIRFOIL, SECTIONS, WING_TRANSLATION

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"

PART = COLORS["series1"]
FRAME = COLORS["series3"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
WASH = 0.13
RADIUS = shell.RADIUS

# ------------------------------------------------------------------ illustration
FRONT_SPAR_XSI = 0.15  # at the root, as in wingStructure.py
MAIN_FRAMES = (WING_TRANSLATION[0] + FRONT_SPAR_XSI * SECTIONS[0][1], REAR_SPAR_X, BAY_AFT_X)  # 10.75, 13.25, 15.4
STRINGER_PITCH = 15.0
PRESSURE_FLOOR_ANGLE = 120.0  # the stringer that gives the height of the pressure floor
KEEL_HEIGHT_ANGLE = 150.0  # the stringer at the top of the keel beam
KEEL_WIDTH_ANGLE = 165.0  # the stringer at the side of the keel beam
KEEL_END = 0.5  # length of the triangular ends of the keel beam beyond the first and the third main frame [m]
SIDEBOX_WIDTH = 0.3  # inwards from the skin at the height of the pressure floor [m]


def stringer_yz(angle):
    a = np.radians(angle)
    return np.array([-RADIUS * np.sin(a), RADIUS * np.cos(a)])  # referenceAngle: 90 deg towards -y


PRESSURE_FLOOR_Z = float(stringer_yz(PRESSURE_FLOOR_ANGLE)[1])  # -0.8
KEEL_TOP_Z = float(stringer_yz(KEEL_HEIGHT_ANGLE)[1])  # -1.386
KEEL_HALF_WIDTH = float(abs(stringer_yz(KEEL_WIDTH_ANGLE)[0]))  # 0.414


def wing_root():
    """Upper and lower side of the root airfoil as (x, z), each sorted by x."""
    root = root_section()
    n = len(AIRFOIL) // 2
    lower, upper = root[:n + 1], root[n:]
    return lower[np.argsort(lower[:, 0])], upper[np.argsort(upper[:, 0])]


# --------------------------------------------------------------------- figure
SIDE_X = (MAIN_FRAMES[0] - 1.25, MAIN_FRAMES[2] + 1.45)
SIDE_Z = (-1.72, -0.28)
EXAGGERATION = 2.0  # vertical scale of the side view
SECTION_Y = (-1.95, 1.95)
SECTION_Z = (-1.72, -0.3)
SECTION_X = round(0.5 * (MAIN_FRAMES[1] + MAIN_FRAMES[2]), 2)


def figure_center_area():
    """(a) the section y = 0 with the vertical scale exaggerated; (b) the section through the bay, true to scale."""
    with figure_style():
        side_w = SIDE_X[1] - SIDE_X[0]
        side_h = EXAGGERATION * (SIDE_Z[1] - SIDE_Z[0]) / side_w * FULL_WIDTH
        sec_w = 0.52 * FULL_WIDTH
        sec_h = (SECTION_Z[1] - SECTION_Z[0]) / (SECTION_Y[1] - SECTION_Y[0]) * sec_w
        gap = 0.55
        fig = plt.figure(figsize=(FULL_WIDTH, side_h + sec_h + gap))
        total = side_h + sec_h + gap
        side = fig.add_axes((0.0, (sec_h + gap) / total, 1.0, side_h / total))
        back = fig.add_axes(((1.0 - sec_w / FULL_WIDTH) / 2, 0.0, sec_w / FULL_WIDTH, sec_h / total))
        _side(side)
        _section(back)
        save_figure(fig, FIGURES / "centerFuselageArea.png")


def _side(ax):
    x0, x1 = SIDE_X
    ax.plot([x0, x1], [-RADIUS, -RADIUS], color=MUTED, lw=LINE["secondary"], zorder=1)
    ax.plot([x0, x1], [FLOOR_Z, FLOOR_Z], color=MUTED, lw=LINE["secondary"], zorder=1)
    label(ax, (x1, FLOOR_Z), "cabin floor", (0, 3), ha="right", va="bottom", color=INK2)
    label(ax, (x1, -RADIUS), "skin", (0, 3), ha="right", va="bottom", color=INK2)
    # the wing box between the spars, muted
    lower, upper = wing_root()
    keep = lambda p: p[(p[:, 0] >= MAIN_FRAMES[0]) & (p[:, 0] <= MAIN_FRAMES[1])]  # noqa: E731
    box = np.vstack([keep(upper), keep(lower)[::-1]])
    ax.add_patch(Polygon(box, closed=True, facecolor=to_rgba(MUTED, 0.18), edgecolor="none", zorder=0))
    label(ax, (0.5 * (MAIN_FRAMES[0] + MAIN_FRAMES[1]), float(np.mean(box[:, 1]))), "wing box", (0, 0), color=INK2)
    # main frames, from the skin up to the cabin floor, named above the cabin floor
    for i, x in enumerate(MAIN_FRAMES, 1):
        ax.plot([x, x], [-RADIUS, FLOOR_Z], color=FRAME, lw=2.0, solid_capstyle="butt", zorder=3)
        label(ax, (x, FLOOR_Z), f"main frame {i}", (0, 4), va="bottom")
    # flat pressure bulkheads at the first and the third main frame, from the keel beam up to the wing box and the
    # pressure floor, named outside the center fuselage area
    top1 = float(np.interp(MAIN_FRAMES[0], *upper.T))
    for x, top, side, dx in ((MAIN_FRAMES[0], top1, -1, 0.09), (MAIN_FRAMES[2], PRESSURE_FLOOR_Z, 1, -0.09)):
        ax.plot([x + dx, x + dx], [KEEL_TOP_Z, top], color=PART, lw=2.6, solid_capstyle="butt", zorder=4)
        label(ax, (x, 0.5 * (KEEL_TOP_Z + top)), "pressure\nbulkhead", (side * 7, 0), ha="left" if side > 0 else "right")
    # pressure floor over the bay
    ax.plot([MAIN_FRAMES[1], MAIN_FRAMES[2]], [PRESSURE_FLOOR_Z, PRESSURE_FLOOR_Z], color=PART, lw=2.6,
            solid_capstyle="butt", zorder=4)
    label(ax, (0.5 * (MAIN_FRAMES[1] + MAIN_FRAMES[2]), PRESSURE_FLOOR_Z), "pressure floor", (0, 4), va="bottom")
    # keel beam along the bottom, with triangular ends beyond the first and the third main frame
    keel = [(MAIN_FRAMES[0] - KEEL_END, -RADIUS), (MAIN_FRAMES[0], KEEL_TOP_Z), (MAIN_FRAMES[2], KEEL_TOP_Z),
            (MAIN_FRAMES[2] + KEEL_END, -RADIUS)]
    ax.add_patch(Polygon(keel, closed=True, facecolor=to_rgba(PART, 0.22), edgecolor=PART, lw=LINE["secondary"],
                         zorder=2))
    label(ax, (0.5 * (MAIN_FRAMES[0] + MAIN_FRAMES[1]), 0.5 * (KEEL_TOP_Z - RADIUS)), "keel beam", (0, 0))
    # lateral panel, seen through the side: from the lower edge of the side box to the rear spar
    lower_rear = float(np.interp(MAIN_FRAMES[1], *lower.T))
    panel = [(MAIN_FRAMES[1], PRESSURE_FLOOR_Z), (MAIN_FRAMES[1] + 0.9, PRESSURE_FLOOR_Z),
             (MAIN_FRAMES[1], lower_rear)]
    ax.add_patch(Polygon(panel, closed=True, facecolor=to_rgba(PART, 0.2), edgecolor="none",
                         zorder=1))
    ax.annotate("lateral panel", xy=(MAIN_FRAMES[1] + 0.25, PRESSURE_FLOOR_Z - 0.12),
                xytext=(MAIN_FRAMES[1] + 1.1, 0.5 * (PRESSURE_FLOOR_Z + KEEL_TOP_Z) - 0.05),
                fontsize=FONT_SIZE["annotation"], color=INK, ha="left", va="center",
                arrowprops={"arrowstyle": "-", "color": MUTED, "lw": LINE["reference"], "shrinkA": 2, "shrinkB": 1})
    axes_cross(ax, (x0 + 0.1, SIDE_Z[0] + 0.03), [(1, 0), (0, 1)], ["x", "z"], 0.3, [(6, 0), (0, 7)])
    ax.set_xlim(*SIDE_X)
    ax.set_ylim(*SIDE_Z)
    ax.set_aspect(EXAGGERATION)
    ax.axis("off")
    ax.set_title(f"(a) Section at y = 0, seen from the left (vertical scale exaggerated {EXAGGERATION:g}:1)",
                 fontsize=FONT_SIZE["base"])


def _section(ax):
    t = np.linspace(0.0, 2.0 * np.pi, 721)
    ax.plot(RADIUS * np.sin(t), RADIUS * np.cos(t), color=MUTED, lw=LINE["secondary"], zorder=1)
    half = float(np.sqrt(RADIUS**2 - FLOOR_Z**2))
    ax.plot([-half, half], [FLOOR_Z, FLOOR_Z], color=MUTED, lw=LINE["secondary"], zorder=1)
    # side boxes between the pressure floor and the skin, the pressure floor between them
    edge = float(np.sqrt(RADIUS**2 - PRESSURE_FLOOR_Z**2))
    inner = edge - SIDEBOX_WIDTH
    for s in (-1, 1):
        zs = np.linspace(PRESSURE_FLOOR_Z, FLOOR_Z, 30)
        skin = np.column_stack([s * np.sqrt(RADIUS**2 - zs**2), zs])
        box = np.vstack([[[s * inner, PRESSURE_FLOOR_Z]], skin, [[s * inner, FLOOR_Z]]])
        ax.add_patch(Polygon(box, closed=True, facecolor=to_rgba(PART, 0.22), edgecolor=PART, lw=LINE["secondary"],
                             zorder=2))
    ax.plot([-inner, inner], [PRESSURE_FLOOR_Z, PRESSURE_FLOOR_Z], color=PART, lw=2.6, solid_capstyle="butt",
            zorder=3)
    label(ax, (0.0, PRESSURE_FLOOR_Z), "pressure floor", (0, 4), va="bottom")
    label(ax, (inner + 0.5 * SIDEBOX_WIDTH, FLOOR_Z), "side box", (0, 4), va="bottom")
    # keel beam at the bottom: between the stringers at its sides and below the stringer at its top
    w = KEEL_HALF_WIDTH
    ys = np.linspace(-w, w, 30)
    keel = np.vstack([np.column_stack([ys, -np.sqrt(RADIUS**2 - ys**2)]), [[w, KEEL_TOP_Z]], [[-w, KEEL_TOP_Z]]])
    ax.add_patch(Polygon(keel, closed=True, facecolor=to_rgba(PART, 0.22), edgecolor=PART, lw=LINE["secondary"],
                         zorder=2))
    label(ax, (0.0, KEEL_TOP_Z), "keel beam", (0, 4), va="bottom")
    label(ax, (0.0, 0.5 * (PRESSURE_FLOOR_Z + KEEL_TOP_Z)), "bay of the main landing gear", (0, 0), color=INK2)
    label(ax, (-half, FLOOR_Z), "cabin floor", (0, 3), ha="left", va="bottom", color=INK2)
    axes_cross(ax, (SECTION_Y[0] + 0.1, SECTION_Z[0] + 0.03), [(1, 0), (0, 1)], ["y", "z"], 0.3, [(6, 0), (0, 7)])
    ax.set_xlim(*SECTION_Y)
    ax.set_ylim(*SECTION_Z)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"(b) Section at x = {SECTION_X:g} m, seen from behind", fontsize=FONT_SIZE["base"])


def report():
    print(f"Main frames at x = {[round(x, 4) for x in MAIN_FRAMES]}")
    print(f"Pressure floor at z = {PRESSURE_FLOOR_Z:.4f} (stringer {PRESSURE_FLOOR_ANGLE:g} deg), keel beam up to "
          f"z = {KEEL_TOP_Z:.4f}, y = +-{KEEL_HALF_WIDTH:.4f}")
    lower, upper = wing_root()
    print(f"Wing box upper side at the rear spar z = {np.interp(MAIN_FRAMES[1], *upper.T):.4f}, lower side "
          f"{np.interp(MAIN_FRAMES[1], *lower.T):.4f}")


def main():
    figure_center_area()
    report()


if __name__ == "__main__":
    main()

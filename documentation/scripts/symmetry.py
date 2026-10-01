# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures for the documentation of symmetry (cpacsType, section 8): the symmetry attribute of
components and the symmetry attribute of references to them (stringUIDBaseType).

Run from the repository root:

    uv run documentation/scripts/symmetry.py

The script writes

    documentation/figures/symmetryInheritance.png
    documentation/figures/uidReferenceSymmetry.png

Definitions shown (as in the documentation):

- A component with symmetry="x-y-plane", "x-z-plane" or "y-z-plane" is mirrored at that plane of the
  CPACS coordinate system. "inherit", the default, takes the symmetry of the parent (parentUID); a
  component without parent is not mirrored. "none" switches the symmetry off. A component with
  parentUID follows the translation of its parent (refType="absLocal"), not its rotation.
  symmetryInheritance.png shows four wings of the documentation example, seen from behind.
- A wing with symmetry="x-z-plane" consists of its defined side and its mirrored side. An engine pylon
  references the wing as parent; the symmetry attribute of the reference selects the side the pylon
  belongs to: def = defined side, symm = mirrored side, full = both sides (default).
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

# Wings of the inheritance example, as in examples/wings_symmetry.xml: uID, parentUID, @symmetry (None = not
# set), translation of the wing coordinate system (refType="absLocal": from the origin of the parent, along the
# CPACS axes), rotation about x [deg], and the span along the y-axis of the wing coordinate system [m].
BOX_WINGS = [
    {"uid": "wing1", "parent": None, "symmetry": "x-z-plane", "translation": (0.0, 0.0, 0.0), "rotation": 0.0,
     "span": 1.0},
    {"uid": "wing2", "parent": "wing1", "symmetry": "none", "translation": (0.0, 1.0, 0.0), "rotation": 90.0,
     "span": 1.0},
    {"uid": "wing3", "parent": "wing2", "symmetry": "x-y-plane", "translation": (0.0, 0.0, 1.0), "rotation": 0.0,
     "span": 1.0},
    {"uid": "wing4", "parent": "wing3", "symmetry": None, "translation": (0.0, 1.0, 0.0), "rotation": -90.0,
     "span": 1.0},
]
# Thickness of a wing seen from behind, only to give the lines a body [m]
BOX_THICKNESS = 0.06


def box_wings():
    """Placement of the inheritance example in the CPACS coordinate system.

    Returns per wing its root and tip in (y, z) and the plane it is mirrored at (None if it is not).
    Only the translation is passed on along parentUID; the symmetry is inherited where it is not set.
    """
    by_uid = {wing["uid"]: wing for wing in BOX_WINGS}

    def origin(wing):
        own = np.asarray(wing["translation"])
        return own if wing["parent"] is None else origin(by_uid[wing["parent"]]) + own

    def symmetry(wing):
        if wing["symmetry"] not in (None, "inherit"):
            return None if wing["symmetry"] == "none" else wing["symmetry"]
        return None if wing["parent"] is None else symmetry(by_uid[wing["parent"]])

    placed = []
    for wing in BOX_WINGS:
        _, y0, z0 = origin(wing)
        angle = np.radians(wing["rotation"])
        tip = np.array([y0, z0]) + wing["span"] * np.array([np.cos(angle), np.sin(angle)])
        placed.append({"uid": wing["uid"], "root": np.array([y0, z0]), "tip": tip, "mirror": symmetry(wing)})
    return placed


def mirrored_yz(points, plane):
    """Mirror points given in (y, z) at a plane of the CPACS coordinate system."""
    factor = {"x-z-plane": (-1.0, 1.0), "x-y-plane": (1.0, -1.0), "y-z-plane": (1.0, 1.0)}[plane]
    return np.asarray(points) * np.array(factor)


def band(root, tip, ends=(0.0, 0.0), thickness=BOX_THICKNESS):
    """Outline of a wing seen from behind: a band of the given thickness from root to tip.

    ends lengthens (positive) or shortens (negative) the band at root and tip, so that wings meeting at a
    corner abut instead of overlapping.
    """
    direction = (tip - root) / np.linalg.norm(tip - root)
    root, tip = root - ends[0] * direction, tip + ends[1] * direction
    normal = np.array([-direction[1], direction[0]]) * thickness / 2
    return np.array([root - normal, tip - normal, tip + normal, root + normal])


def band_ends(wing, wings, thickness=BOX_THICKNESS):
    """Where a horizontal and a vertical wing meet, the vertical one runs through the corner."""
    vertical = abs(wing["tip"][0] - wing["root"][0]) < 1e-9
    ends = []
    for point in (wing["root"], wing["tip"]):
        others = [other for other in wings if other is not wing
                  and any(np.allclose(point, end) for end in (other["root"], other["tip"]))]
        meets_other = any((abs(other["tip"][0] - other["root"][0]) < 1e-9) != vertical for other in others)
        ends.append((thickness / 2 if vertical else -thickness / 2) if meets_other else 0.0)
    return tuple(ends)


def figure_inheritance():
    """Rear view (looking in x-direction, y to the right, z upwards) of the four wings of the example."""
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 5.0))
        wings = box_wings()
        # symmetry planes, behind the wings
        ax.plot([0.0, 0.0], [-1.35, 1.4], color=MUTED, lw=LINE["reference"], zorder=1)
        ax.plot([-1.15, 2.85], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=1)
        ax.text(0.04, 1.4, "x-z plane", ha="left", va="top", fontsize=NOTE, color=INK2)
        ax.text(2.85, 0.04, "x-y plane", ha="right", va="bottom", fontsize=NOTE, color=INK2)

        def part(outline, color):
            ax.add_patch(Polygon(outline, closed=True, lw=0, fc=COLORS["surface"], zorder=2))
            ax.add_patch(Polygon(outline, closed=True, lw=LINE["data"], ec=color, fc=(color, 0.10),
                                 joinstyle="round", zorder=2.1))

        for wing in wings:
            outline = band(wing["root"], wing["tip"], band_ends(wing, wings))
            part(outline, DEFINED)
            if wing["mirror"]:
                part(mirrored_yz(outline, wing["mirror"]), MIRRORED)

        # names at the wings: the defined side with its attribute, the mirrored side named after it. Each
        # placement is (position along the wing from root to tip, offset in points, alignment); the names of
        # wing1 and its mirrored side start at the root, beside the x-z plane, so that the plane passes between them.
        settings = {wing["uid"]: wing["symmetry"] for wing in BOX_WINGS}
        placements = {"wing1": (0.0, (8, -9), "left", "top"), "wing2": (0.5, (-9, 0), "right", "center"),
                      "wing3": (0.5, (0, 9), "center", "bottom"), "wing4": (0.5, (9, 0), "left", "center")}
        mirrored_placements = {"wing1": (0.0, (-8, -9), "right", "top"), "wing3": (0.5, (0, -9), "center", "top"),
                               "wing4": (0.5, (9, 0), "left", "center")}
        for wing in wings:
            at, offset, ha, va = placements[wing["uid"]]
            setting = settings[wing["uid"]]
            note = "no symmetry attribute" if setting is None else f'symmetry="{setting}"'
            ax.annotate(f'{wing["uid"]}\n{note}', xy=wing["root"] + at * (wing["tip"] - wing["root"]),
                        xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=INK,
                        linespacing=1.4, zorder=7)
            if wing["mirror"]:
                at, offset, ha, va = mirrored_placements[wing["uid"]]
                point = mirrored_yz(wing["root"] + at * (wing["tip"] - wing["root"]), wing["mirror"])
                ax.annotate(f'mirrored side of {wing["uid"]}', xy=point, xytext=offset, textcoords="offset points",
                            ha=ha, va=va, fontsize=NOTE, color=INK2, zorder=7)

        # axes of the rear view: y to the right, z upwards, x into the drawing plane
        origin = np.array([2.45, -1.3])
        for direction, text, offset, ha, va in (((1.0, 0.0), "y", (3, 0), "left", "center"),
                                                ((0.0, 1.0), "z", (0, 3), "center", "bottom")):
            tip = origin + 0.3 * np.array(direction)
            ax.annotate("", xy=tip, xytext=origin, arrowprops={
                "arrowstyle": "-|>", "lw": LINE["reference"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
                "color": INK2})
            ax.annotate(text, xy=tip, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE,
                        color=INK2)
        ax.plot(*origin, ls="none", marker="o", ms=6.5, mfc=COLORS["surface"], mec=INK2, mew=LINE["reference"],
                zorder=5)
        ax.plot(*origin, ls="none", marker="x", ms=3.5, mec=INK2, mew=LINE["reference"], zorder=6)
        ax.annotate("x", xy=origin, xytext=(-6, -6), textcoords="offset points", ha="right", va="top",
                    fontsize=NOTE, color=INK2)

        handles = [Polygon([(0, 0)], closed=True, lw=LINE["data"], ec=DEFINED, fc=(DEFINED, 0.10)),
                   Polygon([(0, 0)], closed=True, lw=LINE["data"], ec=MIRRORED, fc=(MIRRORED, 0.10))]
        ax.legend(handles, ["defined side", "mirrored side"], loc="upper center", bbox_to_anchor=(0.5, 0.0),
                  ncol=2, handlelength=1.4, columnspacing=1.4, borderaxespad=0.0)
        ax.set_xlim(-1.2, 2.95)
        ax.set_ylim(-1.45, 1.5)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "symmetryInheritance.png")


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


def figure_reference():
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
    figure_inheritance()
    figure_reference()


if __name__ == "__main__":
    main()

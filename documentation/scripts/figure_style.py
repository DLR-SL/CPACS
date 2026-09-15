"""Shared style for generated documentation figures and equation images.

Import it from a figure script in this directory:

    from figure_style import COLORS, figure_style, save_figure, save_equation

The values are the ones recorded in development/developmentGuidelines.md
(section "Figures and equations"); change them there and here together.

Figures are rendered with a transparent background. The documentation viewer
places every image on a light plate (#fefdfb in the light theme, #edeff1 in
the dark theme), so all colors are chosen for a light surface in both themes.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

COLORS = {
    # Series, assigned in this order. Validated as categorical palette
    # (lightness band, chroma, CVD and normal-vision separation, all pairs) and
    # >= 3:1 against #fefdfb; aqua is 2.95:1 on #edeff1, so it is always
    # accompanied by a text label.
    "series1": "#2a78d6",  # blue
    "series2": "#d95926",  # orange
    "series3": "#199e70",  # aqua
    # Lighter step of series 1, for secondary marks of the same entity
    # (e.g. the terms of a sum whose total is drawn in series1).
    "series1Light": "#86b6ef",
    # Ink: all text uses these, never a series color.
    "ink": "#0b0b0b",  # titles, labels, annotations
    "inkSecondary": "#52514e",  # tick labels, secondary annotations
    # Chrome and neutral marks.
    "muted": "#898781",  # reference lines (e.g. chord), leader lines, neutral comparison curves
    "axis": "#c3c2b7",  # axis lines and ticks
    "grid": "#e1e0d9",  # optional gridlines
    # Light-theme plate; used as a thin ring around markers so that they stay
    # legible where they sit on a line.
    "surface": "#fefdfb",
}

# Line widths in points. Figures are laid out at 100 dpi nominal size, so
# 1.5 pt is about 2 px on screen.
LINE = {"data": 1.5, "secondary": 1.0, "reference": 0.75, "axis": 0.75}

FONT_SIZE = {"base": 9, "title": 10, "annotation": 8.5, "operator": 16}

# Nominal width of a full-width figure in inches (at 100 dpi = 760 px, the
# width of the documentation's detail pane).
FULL_WIDTH = 7.6

# Saved at twice the nominal resolution for sharp display on high-density
# screens; the viewer scales images down to the column width.
DPI = 200

# PNG metadata carries the matplotlib version by default; dropping it keeps
# repeated runs byte-identical.
_PNG_METADATA = {"Software": None}

_RC = {
    # DejaVu Sans ships with matplotlib, so the output does not depend on the
    # fonts installed on the machine.
    "font.family": "DejaVu Sans",
    "font.size": FONT_SIZE["base"],
    "mathtext.fontset": "dejavusans",
    "text.color": COLORS["ink"],
    "axes.labelcolor": COLORS["ink"],
    "axes.titlecolor": COLORS["ink"],
    "axes.titlesize": FONT_SIZE["title"],
    "axes.titlelocation": "left",
    "axes.titlepad": 8,
    "axes.edgecolor": COLORS["axis"],
    "axes.linewidth": LINE["axis"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.facecolor": "none",
    "figure.facecolor": "none",
    "xtick.color": COLORS["axis"],
    "ytick.color": COLORS["axis"],
    "xtick.labelcolor": COLORS["inkSecondary"],
    "ytick.labelcolor": COLORS["inkSecondary"],
    "xtick.major.width": LINE["axis"],
    "ytick.major.width": LINE["axis"],
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "grid.color": COLORS["grid"],
    "grid.linewidth": LINE["axis"],
    "grid.linestyle": "-",
    "lines.linewidth": LINE["data"],
    "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round",
    "legend.frameon": False,
    "legend.fontsize": FONT_SIZE["annotation"],
}


@contextmanager
def figure_style():
    with plt.rc_context(_RC):
        yield


def leader(color=None):
    """Arrow properties for a thin leader line from a label to a feature."""
    return {"arrowstyle": "-", "color": color or COLORS["muted"], "lw": LINE["reference"], "shrinkA": 2, "shrinkB": 1}


def save_figure(fig, path: Path):
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.08, transparent=True, metadata=_PNG_METADATA)
    plt.close(fig)


def save_equation(lines: list[str], path_without_suffix: Path):
    """Write an equation as LaTeX source (.tex) and as image (.png).

    The LaTeX lines must stay within the subset matplotlib's mathtext
    understands; they are rendered in Computer Modern like typeset formulas.
    """
    path_without_suffix.with_suffix(".tex").write_text(" \\\\\n\n".join(lines) + "\n", encoding="utf-8")
    with plt.rc_context({"mathtext.fontset": "cm", "text.color": COLORS["ink"]}):
        fig = plt.figure(figsize=(6.0, 0.75 * len(lines)))
        for k, line in enumerate(lines):
            fig.text(0.0, 1.0 - (k + 0.5) / len(lines), f"${line}$", fontsize=16, va="center", ha="left")
        fig.savefig(path_without_suffix.with_suffix(".png"), dpi=110, bbox_inches="tight", pad_inches=0.04,
                    transparent=True, metadata=_PNG_METADATA)
        plt.close(fig)

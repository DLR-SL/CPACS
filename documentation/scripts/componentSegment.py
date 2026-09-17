# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and equations for the relative coordinates of wing segments and component segments
(wingSegmentType, componentSegmentsType, componentSegmentType).

Run from the repository root:

    uv run documentation/scripts/componentSegment.py

The script writes

    documentation/figures/componentSegments.png
    documentation/figures/segmentEtaXsi.png
    documentation/figures/componentSegmentEta.png
    documentation/figures/componentSegmentEtaXsi.png
    documentation/equations/segmentEtaXsi.{tex,png}
    documentation/equations/componentSegmentEta.{tex,png}
    documentation/equations/componentSegmentToSegment.{tex,png}

and prints the excerpts shown in the documentation. The example wing, including its component
segment, is defined in wing.py, which also writes the example file examples/wingGeometry.xml.

Definition shown (as in the documentation):
  segment coordinates: the bilinear surface between the chord lines of the start and end element,
      P(eta, xsi) = (1 - eta) [(1 - xsi) LE_from + xsi TE_from] + eta [(1 - xsi) LE_to + xsi TE_to];
  component segment coordinates: the element k lies at
      eta_k = (l_1 + ... + l_k) / (l_1 + ... + l_n),  l_j = |M_j - M_(j-1)|,  M = (LE + TE) / 2,
  and inside segment k the segment coordinates are
      eta_segment = (eta - eta_(k-1)) / (eta_k - eta_(k-1)),  xsi_segment = xsi.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from example_xml import indent
from figure_style import COLORS, FONT_SIZE, LINE, figure_style, save_equation, save_figure
from wing import (COMPONENT_SEGMENT, EQUATIONS, FIGURES, INK, INK2, MUTED, NOTE, SECTIONS, WING_UID, arrow,
                  axes_cross, component_segments_xml, leading_trailing_edge)

SERIES1 = COLORS["series1"]
SERIES2 = COLORS["series2"]
WASH = 0.08

# Illustrative point, e.g. on a rear spar: segment and segment coordinates (eta, xsi)
POINT_SEGMENT = 1
POINT = (0.5, 0.75)


# -------------------------------------------------------------------- geometry
def edges():
    """Leading and trailing edge points of the elements from root to tip, in the wing coordinate system."""
    return [leading_trailing_edge(section) for section in SECTIONS]


def segment_point(segment, eta, xsi):
    """Point of segment k (1-based) at segment coordinates (eta, xsi)."""
    (le0, te0), (le1, te1) = edges()[segment - 1], edges()[segment]
    return (1.0 - eta) * ((1.0 - xsi) * le0 + xsi * te0) + eta * ((1.0 - xsi) * le1 + xsi * te1)


def element_etas():
    """Component segment eta of the elements: cumulative lengths of the mid-chord line, normalized."""
    middles = [0.5 * (le + te) for le, te in edges()]
    lengths = [float(np.linalg.norm(b - a)) for a, b in zip(middles[:-1], middles[1:])]
    return np.concatenate([[0.0], np.cumsum(lengths)]) / sum(lengths), lengths


def to_segment(eta, xsi):
    """Segment (1-based) and segment coordinates of a component segment point."""
    etas, _ = element_etas()
    k = min(int(np.searchsorted(etas, eta, side="right")), len(etas) - 1)
    return k, (eta - etas[k - 1]) / (etas[k] - etas[k - 1]), xsi


def to_component_segment(segment, eta, xsi):
    etas, _ = element_etas()
    return etas[segment - 1] + eta * (etas[segment] - etas[segment - 1]), xsi


def component_segment_point(eta, xsi):
    return segment_point(*to_segment(eta, xsi))


def view(p):
    """Top view: span (y) to the right, x downwards."""
    p = np.asarray(p, dtype=float)
    return np.array([p[..., 1], -p[..., 0]]).T


# ------------------------------------------------------------------- equations
SEGMENT_ETA_XSI_LINES = [
    r"P(\eta,\xi) = (1-\eta)\,\left[(1-\xi)\,P_\mathrm{LE,from} + \xi\,P_\mathrm{TE,from}\right]"
    r" + \eta\,\left[(1-\xi)\,P_\mathrm{LE,to} + \xi\,P_\mathrm{TE,to}\right]",
]
COMPONENT_SEGMENT_ETA_LINES = [
    r"\eta_k = \dfrac{l_1 + \dots + l_k}{l_1 + \dots + l_n},\quad l_j = \left|M_j - M_{j-1}\right|,"
    r"\quad M_j = \frac{1}{2}\left(P_{\mathrm{LE},j} + P_{\mathrm{TE},j}\right)",
]
COMPONENT_SEGMENT_TO_SEGMENT_LINES = [
    r"\eta_\mathrm{segment} = \dfrac{\eta - \eta_{k-1}}{\eta_k - \eta_{k-1}},\quad \xi_\mathrm{segment} = \xi",
]


# --------------------------------------------------------------------- layout
# Every figure is one top view at the same scale and with the same horizontal extent, so that the wing has the same
# size in all figures and labels keep the same distances from the lines they belong to.
SCALE = 0.38  # inches per metre
XLIM = (-2.8, 16.0)
LEGEND_SPACE = 0.4  # inches below the view

CHORD = SERIES1
ISO = COLORS["series1Light"]
MID = SERIES2

GAP = 8  # distance of a label from its line [pt]
GAP_WIDE = 22  # distance of a label from a line that carries values as well [pt]
AXES_ORIGIN_OFFSET = (14.6, -0.4)  # position of the axes cross relative to (x, top of the view) [m]


def make_figure(ylim):
    """Figure with one top view at the common scale; ylim is (bottom, top) in metres of the view."""
    width = (XLIM[1] - XLIM[0]) * SCALE
    height = (ylim[1] - ylim[0]) * SCALE
    total = height + LEGEND_SPACE
    fig = plt.figure(figsize=(width, total))
    ax = fig.add_axes((0.0, LEGEND_SPACE / total, 1.0, height / total))
    ax.set_xlim(*XLIM)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def legend(fig, handles, labels, ncol=None):
    fig.legend(handles, labels, loc="lower center", ncol=ncol or len(handles), bbox_to_anchor=(0.5, 0.0),
               handlelength=1.6, columnspacing=1.8, borderaxespad=0.1)


def text(ax, xy, content, offset=(0, 0), ha="center", va="center", color=INK, rotation=0.0, size=NOTE):
    ax.annotate(content, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=size, color=color,
                rotation=rotation, rotation_mode="anchor", annotation_clip=False, zorder=7)


def edge_frame(p, q, up=True):
    """Unit direction from p to q in the view and the unit normal pointing up (or down)."""
    d = np.asarray(q, dtype=float) - np.asarray(p, dtype=float)
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    if (n[1] < 0) == up:
        n = -n
    return d, n


def edge_text(ax, p, q, at, content, distance=GAP, up=True, rotate=False, color=INK):
    """Text centred at a fixed distance from the edge p-q, perpendicular to it."""
    d, n = edge_frame(p, q, up)
    angle = np.degrees(np.arctan2(d[1], d[0])) if rotate else 0.0
    text(ax, at, content, tuple(distance * n), color=color, rotation=angle)


# --------------------------------------------------------------------- drawing
def planform(ax, segments=(1, 2), wash=SERIES1, alpha=WASH):
    """Area of consecutive segments in the top view."""
    e = edges()
    first, last = segments[0] - 1, segments[-1]
    leading = [view(e[i][0]) for i in range(first, last + 1)]
    trailing = [view(e[i][1]) for i in range(last, first - 1, -1)]
    ax.add_patch(Polygon(leading + trailing, closed=True, facecolor=wash, alpha=alpha, edgecolor="none", zorder=0))


def outline(ax):
    """Leading and trailing edges in muted gray, the chords of the elements in series 1."""
    e = edges()
    for a, b in zip(e[:-1], e[1:]):
        for p, q in ((a[0], b[0]), (a[1], b[1])):
            line(ax, [p, q], MUTED, LINE["reference"], zorder=2)
    for le, te in e:
        line(ax, [le, te], CHORD, LINE["data"], zorder=3)


def element_labels(ax, distance=GAP, extra=None):
    for i, ((name, _, _), (_, te)) in enumerate(zip(SECTIONS, edges())):
        content = f"{name} element" + (f"\n{extra[i]}" if extra else "")
        text(ax, view(te), content, (0, -distance), va="top", color=INK2)


def line(ax, points, color, lw, zorder=1.5):
    ax.plot(*view(np.array(points)).T, color=color, lw=lw, zorder=zorder, clip_on=False, solid_capstyle="butt")


def point_marker(ax, xy):
    ax.plot(*xy, ls="none", marker="o", ms=5.0, color=INK, mec=COLORS["surface"], mew=1.0, zorder=6, clip_on=False)


def axes_mark(ax):
    origin = (AXES_ORIGIN_OFFSET[0], ax.get_ylim()[1] + AXES_ORIGIN_OFFSET[1])
    axes_cross(ax, origin, [(0, -1), (1, 0)], ["x", "y"], 1.2, [(0, -7), (6, 0)])


def handle_line(color, lw):
    return Line2D([], [], color=color, lw=lw)


def handle_point(color=None):
    return Line2D([], [], ls="-" if color else "none", color=color or INK, lw=LINE["secondary"], marker="o", ms=5.0,
                  markerfacecolor=INK, markeredgecolor=COLORS["surface"])


def mid_chord_points():
    return [view(0.5 * (le + te)) for le, te in edges()]


# --------------------------------------------------------------------- figures
def figure_component_segments():
    """Top view of the example wing with two ways to divide it: (a) one component segment, (b) two."""
    e = edges()
    stations = [view(le) for le, _ in e]
    rows = {"a": 2.6, "b": 1.1}  # height of the brackets above the root leading edge [m]
    with figure_style():
        fig, ax = make_figure((-8.3, 3.7))
        planform(ax)
        outline(ax)
        element_labels(ax)

        # hairlines from the highest bracket at each element down to the leading edge
        for station, top in zip(stations, (rows["a"], rows["b"], rows["a"])):
            ax.plot([station[0]] * 2, [top, station[1] + 0.3], color=COLORS["axis"], lw=LINE["reference"], zorder=1)

        def bracket(row, first, last, color, label, gap=(0.0, 0.0)):
            y0, y1 = stations[first - 1][0] + gap[0], stations[last][0] - gap[1]
            ax.plot([y0, y1], [rows[row]] * 2, color=color, lw=3.0, solid_capstyle="butt", zorder=4)
            text(ax, (0.5 * (y0 + y1), rows[row]), label, (0, GAP), va="bottom")

        bracket("a", 1, 2, SERIES1, "component segment")
        bracket("b", 1, 1, SERIES1, "component segment 1", gap=(0.0, 0.1))
        bracket("b", 2, 2, SERIES2, "component segment 2", gap=(0.1, 0.0))
        for row, y in rows.items():
            text(ax, (stations[0][0], y), f"({row})", (-GAP - 2, 0), ha="right")
        axes_mark(ax)

        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(MUTED, LINE["reference"])],
               ["chord of an element", "leading and trailing edge"])
        save_figure(fig, FIGURES / "componentSegments.png")


def figure_segment_eta_xsi():
    """Top view of the example wing with the lines of constant eta and xsi of each segment and a point."""
    ticks = (0.25, 0.5, 0.75)
    e = edges()
    with figure_style():
        fig, ax = make_figure((-9.0, 2.2))
        planform(ax)
        for segment in (1, 2):
            for s in ticks:
                line(ax, [segment_point(segment, s, 0.0), segment_point(segment, s, 1.0)], ISO, LINE["reference"])
                line(ax, [segment_point(segment, 0.0, s), segment_point(segment, 1.0, s)], ISO, LINE["reference"])

        eta, xsi = POINT
        for points in ([segment_point(POINT_SEGMENT, eta, 0.0), segment_point(POINT_SEGMENT, eta, 1.0)],
                       [segment_point(POINT_SEGMENT, 0.0, xsi), segment_point(POINT_SEGMENT, 1.0, xsi)]):
            line(ax, points, MID, LINE["secondary"], zorder=2.5)
        outline(ax)
        point_marker(ax, view(segment_point(POINT_SEGMENT, eta, xsi)))

        for segment in (1, 2):
            le0, le1 = view(e[segment - 1][0]), view(e[segment][0])
            te0, te1 = view(e[segment - 1][1]), view(e[segment][1])
            # eta: arrow parallel to the leading edge, values along the trailing edge
            _, n = edge_frame(le0, le1)
            start, end = le0 + 0.12 * (le1 - le0) + 0.6 * n, le0 + 0.58 * (le1 - le0) + 0.6 * n
            arrow(ax, start, end, color=INK, lw=LINE["secondary"], head=7)
            edge_text(ax, le0, le1, 0.5 * (start + end), f"η of segment {segment}", distance=GAP + 1, rotate=True)
            for s in ticks:
                edge_text(ax, te0, te1, view(segment_point(segment, s, 1.0)), f"{s:g}", distance=GAP + 3, up=False,
                          color=INK2)

        # xsi: values beside the root chord, arrow further out
        root_le = view(e[0][0])
        start, end = root_le + np.array([-1.9, -0.4]), root_le + np.array([-1.9, -2.3])
        arrow(ax, start, end, color=INK, lw=LINE["secondary"], head=7)
        text(ax, 0.5 * (start + end), "ξ", (-GAP, 0), ha="right")
        for s in ticks:
            text(ax, view(segment_point(1, 0.0, s)), f"{s:g}", (-GAP, 0), ha="right", color=INK2)

        element_labels(ax, distance=GAP_WIDE)
        axes_mark(ax)
        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(ISO, LINE["reference"]), handle_point(MID)],
               ["chord of an element", "lines of constant η and ξ", f"η = {eta:g}, ξ = {xsi:g} in segment {POINT_SEGMENT}"])
        save_figure(fig, FIGURES / "segmentEtaXsi.png")


def figure_component_segment_eta():
    """Top view of the example wing: element eta from the lengths of the mid-chord line."""
    etas, lengths = element_etas()
    middles = mid_chord_points()
    with figure_style():
        fig, ax = make_figure((-8.6, 1.2))
        planform(ax)
        outline(ax)
        ax.plot(*np.array(middles).T, color=MID, lw=LINE["data"], zorder=4)
        for m in middles:
            point_marker(ax, m)
        for j, length in enumerate(lengths, start=1):
            edge_text(ax, middles[j - 1], middles[j], 0.5 * (middles[j - 1] + middles[j]),
                      f"l{chr(0x2080 + j)} = {length:.2f} m", distance=GAP + 3, rotate=True)
        element_labels(ax, extra=[f"η = {eta:.3f}" if 0.0 < eta < 1.0 else f"η = {eta:g}" for eta in etas])
        axes_mark(ax)
        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(MID, LINE["data"])],
               ["chord of an element", "mid-chord line, lengths measured in space"])
        save_figure(fig, FIGURES / "componentSegmentEta.png")


def figure_component_segment_eta_xsi():
    """Top view of the example wing: lines of constant eta and xsi of the component segment, and a point."""
    e = edges()
    etas, _ = element_etas()
    middles = mid_chord_points()
    with figure_style():
        fig, ax = make_figure((-8.6, 2.0))
        planform(ax)
        for s in np.linspace(0.0, 1.0, 11)[1:-1]:
            line(ax, [component_segment_point(s, 0.0), component_segment_point(s, 1.0)], ISO, LINE["reference"])
        for s in (0.25, 0.75):
            line(ax, [component_segment_point(t, s) for t in etas], ISO, LINE["reference"])
        ax.plot(*np.array(middles).T, color=MID, lw=LINE["data"], zorder=4)
        outline(ax)
        for s in np.linspace(0.0, 1.0, 6):
            k, _, _ = to_segment(min(s, 0.999), 0.0)
            edge_text(ax, view(e[k - 1][0]), view(e[k][0]), view(component_segment_point(s, 0.0)), f"η = {s:g}"
                      if s == 0.0 else f"{s:g}", distance=GAP + 3, color=INK2)
        element_labels(ax)

        eta, xsi = to_component_segment(POINT_SEGMENT, *POINT)
        on_middle, point = view(component_segment_point(eta, 0.5)), view(component_segment_point(eta, xsi))
        arrow(ax, on_middle, point, color=INK, lw=LINE["secondary"], head=7)
        for xy, number in ((on_middle, "A"), (point, "B")):
            point_marker(ax, xy)
            text(ax, xy, number, (GAP, 0), ha="left", size=FONT_SIZE["base"])
        text(ax, (8.4, 1.7),
             f"A   η = {eta:.3f} on the mid-chord line\n"
             f"B   η = {eta:.3f}, ξ = {xsi:g}\n"
             f"     (η = {POINT[0]:g}, ξ = {POINT[1]:g} in segment {POINT_SEGMENT})",
             ha="left", va="top", size=NOTE)

        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(MID, LINE["data"]), handle_line(ISO, LINE["reference"])],
               ["chord of an element", "mid-chord line", "lines of constant η and ξ"])
        save_figure(fig, FIGURES / "componentSegmentEtaXsi.png")


# ------------------------------------------------------------------- excerpts
def spar_position_xml(uid, eta, xsi, reference):
    return "\n".join([
        f'<sparPosition uID="{uid}">', "    <sparPositionEtaXsi>", f"        <eta>{eta:g}</eta>",
        f"        <xsi>{xsi:g}</xsi>", f"        <referenceUID>{reference}</referenceUID>", "    </sparPositionEtaXsi>",
        "</sparPosition>",
    ])


def excerpt_spar_positions():
    """The illustrative point, once in component segment and once in segment coordinates."""
    eta, xsi = to_component_segment(POINT_SEGMENT, *POINT)
    return "\n".join([
        "<sparPositions>",
        indent(spar_position_xml(f"{WING_UID}_sparPosition_componentSegment", round(eta, 4), xsi,
                                 f"{WING_UID}_{COMPONENT_SEGMENT[0]}"), 1),
        indent(spar_position_xml(f"{WING_UID}_sparPosition_segment", POINT[0], POINT[1],
                                 f"{WING_UID}_segment{POINT_SEGMENT}"), 1),
        "</sparPositions>",
    ])


# ------------------------------------------------------------------------ main
def main():
    save_equation(SEGMENT_ETA_XSI_LINES, EQUATIONS / "segmentEtaXsi")
    save_equation(COMPONENT_SEGMENT_ETA_LINES, EQUATIONS / "componentSegmentEta")
    save_equation(COMPONENT_SEGMENT_TO_SEGMENT_LINES, EQUATIONS / "componentSegmentToSegment")
    figure_component_segments()
    figure_segment_eta_xsi()
    figure_component_segment_eta()
    figure_component_segment_eta_xsi()

    etas, lengths = element_etas()
    print("Mid-chord lengths:", [round(v, 4) for v in lengths], " element etas:", [round(float(v), 6) for v in etas])
    print("Point:", f"segment {POINT_SEGMENT} {POINT} -> component segment", to_component_segment(POINT_SEGMENT, *POINT))
    print("\nExcerpt for the componentSegmentType documentation:\n")
    print(component_segments_xml())
    print("\nExcerpt for the componentSegmentType documentation (spar positions):\n")
    print(excerpt_spar_positions())


if __name__ == "__main__":
    main()

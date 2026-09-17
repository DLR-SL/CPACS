# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of control surfaces
(controlSurfacesType, trailingEdgeDeviceType, leadingEdgeDeviceType, spoilerType, their outer shapes,
borders and deflection paths).

Run from the repository root:

    uv run documentation/scripts/controlSurface.py

The script writes the figures and equations listed in main() and the example file
examples/controlSurfaces.xml, and prints the excerpts shown in the documentation. The wing and its
component segment are defined in wing.py; the relative coordinates of the component segment in
componentSegment.py.

Definitions shown (as in the documentation):
  border: the plane through the points P_LE and P_TE of the chord surface of the component segment that
      contains the normal of the component segment; e.g. P_LE = CS(etaLE, xsiLE), P_TE = CS(etaTE, 1) for a
      trailing edge device;
  hinge point: P = P_lower + h (P_upper - P_lower) + t, where P_lower and P_upper are the points of the lower
      and upper wing surface on the normal of the component segment mid plane through CS(etaLE, hingeXsi);
  deflection: the hinge points are translated in the axes of the wing coordinate system, the control
      surface is placed on the translated hinge line and rotated about it by hingeLineRotation (right-handed
      about the direction from the inner to the outer hinge point); all values are interpolated linearly
      between the steps.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from componentSegment import (GAP, GAP_WIDE, LEGEND_SPACE, CHORD, SERIES1, SERIES2, WASH, axes_mark, component_segment_point,
                              edges, element_etas, element_labels, handle_line, handle_point, legend, make_figure,
                              outline, planform, point_marker, text, to_segment, view)
from example_xml import indent, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, LINE, figure_style, leader, save_equation, save_figure
from wing import (AIRFOIL, COMPONENT_SEGMENT, DOCUMENTATION, EQUATIONS, FIGURES, INK, INK2, MUTED, NOTE, SECTIONS, WING_UID,
                  airfoil_xml, arrow, circle_profile_xml, fuselage_xml, section_airfoil, wing_xml)

EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "controlSurfaces.xml"
CS_UID = f"{WING_UID}_{COMPONENT_SEGMENT[0]}"

# ------------------------------------------------------------------ example data
# Borders: (etaLE, etaTE or None, xsi values); hinge points: (hingeXsi, hingeRelHeight);
# steps: (controlParameter, hingeLineRotation [deg], translation of both hinge points (x, y, z) [m] or None)
FLAP = {
    "uid": f"{WING_UID}_flap", "name": "Inner flap",
    "borders": {"inner": (0.14, None, 0.70), "outer": (0.38, None, 0.72)},
    "leadingEdgeShape": (0.5, 0.9, 0.7),  # relHeightLE, xsiUpperSkin, xsiLowerSkin
    "hinges": {"inner": (0.75, 0.2), "outer": (0.76, 0.2)},
    "steps": [(0.0, 0.0, None), (0.5, 10.0, (0.2, 0.0, -0.05)), (1.0, 30.0, (0.5, 0.0, -0.15))],
}
SLAT = {
    "uid": f"{WING_UID}_slat", "name": "Outer slat",
    "borders": {"inner": (0.45, None, (0.15, 0.12)), "outer": (0.9, None, (0.15, 0.12))},  # xsiTEUpper, xsiTELower
    "innerShape": (0.45, 0.04),  # relHeightTE, xsiTE
    "hinges": {"inner": (0.05, 0.5), "outer": (0.05, 0.5)},
    "steps": [(0.0, 0.0, None), (1.0, -20.0, (-0.3, 0.0, -0.15))],
}
SPOILER = {
    "uid": f"{WING_UID}_spoiler", "name": "Inner spoiler",
    "borders": {"inner": (0.17, None, (0.55, 0.69)), "outer": (0.36, None, (0.56, 0.70))},  # xsiLE, xsiTE
    "relHeightLE": 0.8,
    "hinges": {"inner": (0.56, 0.95), "outer": (0.57, 0.95)},
    "steps": [(0.0, 0.0, None), (1.0, -45.0, None)],
}

# Cut-outs of the wing (controlSurfaceWingCutOutType). The chordwise position of the cut on the upper and the
# lower skin is given as (inner border, outer border) in xsi of the component segment; the borders of the cut-out
# are (etaLE, etaTE) and default to the borders of the control surface; the control point is (relHeight, xsi).
FLAP_CUTOUT = {
    "upperSkin": (0.68, 0.70), "lowerSkin": (0.64, 0.66),
}
SLAT_CUTOUT = {
    "upperSkin": (0.17, 0.17), "lowerSkin": (0.14, 0.14),
    "controlPoint": {"inner": (0.45, 0.06), "outer": (0.45, 0.06)},
    "borders": {"inner": (0.43, 0.43), "outer": (0.92, 0.92)},
}


# --------------------------------------------------------------------------- XML
def iso_xml(tag, kind, value):
    return "\n".join([f"<{tag}>", f"    <{kind}>{value:g}</{kind}>", f"    <referenceUID>{CS_UID}</referenceUID>",
                      f"</{tag}>"])


def path_xml(device, translations=True):
    lines = ["<path>"]
    for side in ("inner", "outer"):
        xsi, height = device["hinges"][side]
        lines += [f"    <{side}HingePoint>", f"        <hingeXsi>{xsi:g}</hingeXsi>",
                  f"        <hingeRelHeight>{height:g}</hingeRelHeight>", f"    </{side}HingePoint>"]
    lines.append("    <steps>")
    for parameter, rotation, translation in device["steps"]:
        lines += ["        <step>", f"            <controlParameter>{parameter:g}</controlParameter>"]
        if translations and translation:
            x, y, z = translation
            lines += ["            <innerHingeTranslation>", f"                <x>{x:g}</x>", f"                <y>{y:g}</y>",
                      f"                <z>{z:g}</z>", "            </innerHingeTranslation>",
                      "            <outerHingeTranslation>", f"                <x>{x:g}</x>", f"                <z>{z:g}</z>",
                      "            </outerHingeTranslation>"]
        lines += [f"            <hingeLineRotation>{rotation:g}</hingeLineRotation>", "        </step>"]
    lines += ["    </steps>", "</path>"]
    return "\n".join(lines)


def flap_border_xml(side):
    eta_le, eta_te, xsi_le = FLAP["borders"][side]
    height, upper, lower = FLAP["leadingEdgeShape"]
    return "\n".join([
        f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1),
        *([indent(iso_xml("etaTE", "eta", eta_te), 1)] if eta_te is not None else []),
        indent(iso_xml("xsiLE", "xsi", xsi_le), 1),
        "    <leadingEdgeShape>", f"        <relHeightLE>{height:g}</relHeightLE>",
        f"        <xsiUpperSkin>{upper:g}</xsiUpperSkin>", f"        <xsiLowerSkin>{lower:g}</xsiLowerSkin>",
        "    </leadingEdgeShape>", f"</{side}Border>",
    ])


def slat_border_xml(side):
    eta_le, eta_te, (upper, lower) = SLAT["borders"][side]
    height, xsi = SLAT["innerShape"]
    return "\n".join([
        f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1),
        *([indent(iso_xml("etaTE", "eta", eta_te), 1)] if eta_te is not None else []),
        f"    <xsiTEUpper>{upper:g}</xsiTEUpper>", f"    <xsiTELower>{lower:g}</xsiTELower>",
        "    <innerShape>", f"        <relHeightTE>{height:g}</relHeightTE>", f"        <xsiTE>{xsi:g}</xsiTE>",
        "    </innerShape>", f"</{side}Border>",
    ])


def spoiler_border_xml(side):
    eta_le, eta_te, (xsi_le, xsi_te) = SPOILER["borders"][side]
    return "\n".join([
        f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1),
        *([indent(iso_xml("etaTE", "eta", eta_te), 1)] if eta_te is not None else []),
        indent(iso_xml("xsiLE", "xsi", xsi_le), 1), indent(iso_xml("xsiTE", "xsi", xsi_te), 1),
        f"    <relHeightLE>{SPOILER['relHeightLE']:g}</relHeightLE>", f"</{side}Border>",
    ])


def device_xml(tag, device, border_xml, translations=True):
    return "\n".join([
        f'<{tag} uID="{device["uid"]}">', f"    <name>{device['name']}</name>", f"    <parentUID>{CS_UID}</parentUID>",
        "    <outerShape>", indent(border_xml("inner"), 2), indent(border_xml("outer"), 2), "    </outerShape>",
        indent(path_xml(device, translations), 1), f"</{tag}>",
    ])


def control_surfaces_xml():
    return "\n".join([
        "<controlSurfaces>",
        "    <leadingEdgeDevices>", indent(device_xml("leadingEdgeDevice", SLAT, slat_border_xml), 2),
        "    </leadingEdgeDevices>",
        "    <trailingEdgeDevices>", indent(device_xml("trailingEdgeDevice", FLAP, flap_border_xml), 2),
        "    </trailingEdgeDevices>",
        "    <spoilers>", indent(device_xml("spoiler", SPOILER, spoiler_border_xml, translations=False), 2),
        "    </spoilers>",
        "</controlSurfaces>",
    ])


def excerpt_control_surfaces_xml():
    def short(tag, device):
        return [f'        <{tag} uID="{device["uid"]}">', "            ...", f"        </{tag}>"]
    return "\n".join([
        "<componentSegment uID=\"" + CS_UID + "\">", "    ...", "    <controlSurfaces>",
        "        <leadingEdgeDevices>", *(" " * 4 + line for line in short("leadingEdgeDevice", SLAT)), "        </leadingEdgeDevices>",
        "        <trailingEdgeDevices>", *(" " * 4 + line for line in short("trailingEdgeDevice", FLAP)), "        </trailingEdgeDevices>",
        "        <spoilers>", *(" " * 4 + line for line in short("spoiler", SPOILER)), "        </spoilers>",
        "    </controlSurfaces>", "</componentSegment>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Control surfaces",
        description="A flap, a slat and a spoiler on the component segment of the example wing, with deflection paths.",
        model_uid="ControlSurfacesAircraft",
        model_name="Control surfaces example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml(control_surfaces_xml()))],
        extra_profiles=[("wingAirfoils", airfoil_xml())],
    )


# ---------------------------------------------------------------------- geometry
# All geometry in the wing coordinate system. The wing surface of a segment is the ruled surface between the
# airfoil contours of its elements, point by point.
CONTOURS = [section_airfoil(section) for section in SECTIONS]
LE_INDEX = int(np.argmin(AIRFOIL[:, 0]))  # contours run from the trailing edge over the lower side to the upper side


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def cs_normal():
    """Normal of the component segment: from its corner points (eta, xsi) = (0, 0), (0, 1), (1, 0)."""
    p00, p01, p10 = (component_segment_point(e, x) for e, x in ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    return unit(np.cross(p01 - p00, p10 - p00))


def midplane_normal(eta):
    """Normal of the mid plane at eta: chord direction crossed with the leading edge direction in the y-z plane."""
    k, _, _ = to_segment(min(eta, 0.999999), 0.0)
    le0, le1 = edges()[k - 1][0], edges()[k][0]
    span = unit([0.0, le1[1] - le0[1], le1[2] - le0[2]])
    chord = unit(component_segment_point(eta, 1.0) - component_segment_point(eta, 0.0))
    return unit(np.cross(chord, span))


class Frame:
    """Plane through origin, spanned by the unit vector u and the direction up (made orthogonal to u)."""

    def __init__(self, origin, u, up):
        self.origin, self.u = np.asarray(origin, dtype=float), unit(u)
        self.v = unit(up - (up @ self.u) * self.u)
        self.w = np.cross(self.u, self.v)

    def to2d(self, points):
        d = np.atleast_2d(points) - self.origin
        return np.column_stack([d @ self.u, d @ self.v])

    def to3d(self, points2d):
        p = np.atleast_2d(points2d)
        return self.origin + np.outer(p[:, 0], self.u) + np.outer(p[:, 1], self.v)

    def section(self, segment):
        """Upper and lower side of the wing surface of a segment cut by the plane, as (a, b) sorted by a."""
        a, b = CONTOURS[segment - 1], CONTOURS[segment]
        s = ((self.origin - a) @ self.w) / ((b - a) @ self.w)
        points = self.to2d(a + s[:, None] * (b - a))
        lower, upper = points[: LE_INDEX + 1][::-1], points[LE_INDEX:]
        return upper[np.argsort(upper[:, 0])], lower[np.argsort(lower[:, 0])]


def border_frame(eta_le, xsi_le, eta_te, xsi_te):
    """Plane of a border through P_LE and P_TE containing the normal of the component segment."""
    p_le, p_te = component_segment_point(eta_le, xsi_le), component_segment_point(eta_te, xsi_te)
    return Frame(p_le, p_te - p_le, cs_normal()), np.linalg.norm(p_te - p_le)


def skin(side, a):
    return float(np.interp(a, side[:, 0], side[:, 1]))


def hinge_point(eta, xsi, height, translation=(0.0, 0.0, 0.0)):
    """Point at the relative height between the lower and upper surface on the mid plane normal through CS(eta, xsi)."""
    c = component_segment_point(eta, xsi)
    n = midplane_normal(eta)
    chord = unit(component_segment_point(eta, 1.0) - component_segment_point(eta, 0.0))
    frame = Frame(c, np.cross(n, np.cross(chord, n)), n)  # plane containing the normal, u along the chord
    upper, lower = frame.section(to_segment(min(eta, 0.999999), 0.0)[0])
    # the normal is the v axis of the frame, i.e. a = 0
    b_lower, b_upper = skin(lower, 0.0), skin(upper, 0.0)
    return frame.to3d([[0.0, b_lower + height * (b_upper - b_lower)]])[0] + np.asarray(translation)


def rotation(axis, angle):
    k = unit(axis)
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    a = np.radians(angle)
    return np.eye(3) + np.sin(a) * K + (1.0 - np.cos(a)) * K @ K


def device_hinges(device):
    etas = {side: device["borders"][side][0] for side in ("inner", "outer")}
    return [hinge_point(etas[side], *device["hinges"][side]) for side in ("inner", "outer")]


def deflect(points, device, parameter):
    """Points of a control surface at a control parameter: steps interpolated linearly."""
    steps = device["steps"]
    params = [s[0] for s in steps]
    angle = np.interp(parameter, params, [s[1] for s in steps])
    shift = np.array([np.interp(parameter, params, [(s[2] or (0.0, 0.0, 0.0))[i] for s in steps]) for i in range(3)])
    p1, p2 = device_hinges(device)
    q1, q2 = p1 + shift, p2 + shift
    e, f = unit(p2 - p1), unit(q2 - q1)
    length = np.linalg.norm(p2 - p1)
    c = np.cross(e, f)
    align = rotation(c, np.degrees(np.arctan2(np.linalg.norm(c), e @ f))) if np.linalg.norm(c) > 1e-14 else np.eye(3)
    r = rotation(f, angle) @ align
    return 0.5 * (q1 + q2) - 0.5 * length * f + (np.atleast_2d(points) - p1) @ r.T


def hermite(p0, t0, p1, t1, n=24):
    s = np.linspace(0.0, 1.0, n)[:, None]
    h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1


def skin_polyline(side, a0, a1):
    inside = side[(side[:, 0] > min(a0, a1)) & (side[:, 0] < max(a0, a1))]
    ends = np.array([[a0, skin(side, a0)], [a1, skin(side, a1)]])
    points = np.vstack([ends[:1], inside, ends[1:]])
    return points[np.argsort(points[:, 0])][:: 1 if a1 > a0 else -1]


def skin_tangent(side, a, toward):
    d = 1e-3 * np.sign(toward)
    return unit([d, skin(side, a + d) - skin(side, a)])


def flap_section(device=None):
    """Section of the flap at its inner border: frame, chord length, wing sides and flap contour (2D)."""
    device = device or FLAP
    eta, _, xsi_le = device["borders"]["inner"]
    frame, chord = border_frame(eta, xsi_le, eta, 1.0)
    upper, lower = frame.section(to_segment(eta, 0.0)[0])
    height, x_upper, x_lower = device["leadingEdgeShape"]
    a_upper, a_lower = chord * (1.0 - x_upper), chord * (1.0 - x_lower)  # measured from the trailing edge
    nose = np.array([0.0, skin(lower, 0.0) + height * (skin(upper, 0.0) - skin(lower, 0.0))])
    p_lower, p_upper = np.array([a_lower, skin(lower, a_lower)]), np.array([a_upper, skin(upper, a_upper)])
    scale = 0.6 * np.linalg.norm(p_upper - nose)
    curve = np.vstack([hermite(p_lower, scale * skin_tangent(lower, a_lower, -1), nose, scale * np.array([0.0, 1.0])),
                       hermite(nose, scale * np.array([0.0, 1.0]), p_upper, scale * skin_tangent(upper, a_upper, 1))[1:]])
    contour = np.vstack([curve, skin_polyline(upper, a_upper, chord)[1:], skin_polyline(lower, chord, a_lower)[1:]])
    points = {"nose": nose, "upper": p_upper, "lower": p_lower}
    return frame, chord, upper, lower, contour, points


def slat_section(device=None):
    device = device or SLAT
    xsi = device["borders"]["inner"][2]
    x_te_upper, x_te_lower = xsi if isinstance(xsi, tuple) else (xsi, xsi)
    eta = device["borders"]["inner"][0]
    x_te = max(x_te_upper, x_te_lower)
    frame, chord = border_frame(eta, 0.0, eta, x_te)
    upper, lower = frame.section(to_segment(eta, 0.0)[0])
    height, x_inner = device["innerShape"]
    a_upper, a_lower, a_inner = (chord * x / x_te for x in (x_te_upper, x_te_lower, x_inner))  # xsi of the component segment
    inner = np.array([a_inner, skin(lower, a_inner) + height * (skin(upper, a_inner) - skin(lower, a_inner))])
    p_upper, p_lower = np.array([a_upper, skin(upper, a_upper)]), np.array([a_lower, skin(lower, a_lower)])
    scale = 0.6 * np.linalg.norm(p_upper - inner)
    curve = np.vstack([hermite(p_upper, scale * skin_tangent(upper, a_upper, -1), inner, scale * np.array([0.0, -1.0])),
                       hermite(inner, scale * np.array([0.0, -1.0]), p_lower, scale * skin_tangent(lower, a_lower, 1))[1:]])
    lo = skin_polyline(lower, a_lower, lower[0, 0])
    up = skin_polyline(upper, upper[0, 0], a_upper)
    contour = np.vstack([up, curve[1:], lo[1:]])
    points = {"inner": inner, "upper": p_upper, "lower": p_lower}
    return frame, chord, upper, lower, contour, points


def spoiler_section(device=None):
    device = device or SPOILER
    eta, _, (x_le, x_te) = device["borders"]["inner"]
    frame, chord = border_frame(eta, x_le, eta, x_te)
    upper, lower = frame.section(to_segment(eta, 0.0)[0])
    le_low = np.array([0.0, skin(lower, 0.0) + device["relHeightLE"] * (skin(upper, 0.0) - skin(lower, 0.0))])
    top = skin_polyline(upper, 0.0, chord)
    contour = np.vstack([top, le_low[None, :]])
    return frame, chord, upper, lower, contour, {"le": le_low}


def planform_outline(device, kind):
    """Top view outline of a control surface in wing coordinates."""
    (e_in, _, x_in), (e_out, _, x_out) = device["borders"]["inner"], device["borders"]["outer"]
    kink = [e for e in element_etas()[0] if e_in < e < e_out]
    if kind == "flap":
        front = [component_segment_point(e_in, x_in), component_segment_point(e_out, x_out)]
        rear = [component_segment_point(e, 1.0) for e in [e_out, *kink[::-1], e_in]]
        return np.array(front + rear)
    if kind == "slat":
        te_in, te_out = max(x_in), max(x_out)
        front = [component_segment_point(e, 0.0) for e in [e_in, *kink, e_out]]
        return np.array(front + [component_segment_point(e_out, te_out), component_segment_point(e_in, te_in)])
    return np.array([component_segment_point(e_in, x_in[0]), component_segment_point(e_out, x_out[0]),
                     component_segment_point(e_out, x_out[1]), component_segment_point(e_in, x_in[1])])


# ------------------------------------------------------------------- equations
HINGE_POINT_LINES = [r"P_\mathrm{hinge} = P_\mathrm{lower} + h\,\left(P_\mathrm{upper} - P_\mathrm{lower}\right) + t"]
DEFLECTION_LINES = [r"p' = m' - \dfrac{L}{2}\,e' + R_{e'}(\alpha)\,R_{e \rightarrow e'}\,\left(p - P_\mathrm{inner}\right)"]


# --------------------------------------------------------------------- figures
DEVICE_COLOR = SERIES2
SECTION_SCALE = 2.1  # inches per metre in section views


def figure_planform():
    """Top view of the example wing with flap, slat and spoiler and the points defining a border."""
    devices = ((FLAP, "flap"), (SLAT, "slat"), (SPOILER, "spoiler"))
    with figure_style():
        fig, ax = make_figure((-8.3, 1.4))
        planform(ax)
        outline(ax)
        for device, kind in devices:
            points = view(planform_outline(device, kind))
            ax.add_patch(Polygon(points, closed=True, facecolor=DEVICE_COLOR, alpha=0.12, edgecolor="none", zorder=4))
            ax.plot(*np.vstack([points, points[:1]]).T, color=DEVICE_COLOR, lw=LINE["data"], zorder=4.1)
        # the border points of the flap; the outer border is built in the same way as the inner one
        for side in ("inner", "outer"):
            eta, _, xsi = FLAP["borders"][side]
            for x in (xsi, 1.0):
                point_marker(ax, view(component_segment_point(eta, x)))
        eta, _, xsi = FLAP["borders"]["inner"]
        text(ax, view(component_segment_point(eta, xsi)), r"$P_\mathrm{LE}$", (-GAP, GAP), ha="right", va="bottom")
        text(ax, view(component_segment_point(eta, 1.0)), r"$P_\mathrm{TE}$", (-GAP, -GAP), ha="right", va="top")
        for device, kind in devices:
            text(ax, view(planform_outline(device, kind)).mean(axis=0), kind, color=INK)
        element_labels(ax)
        axes_mark(ax)
        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(DEVICE_COLOR, LINE["data"]), handle_point()],
               ["chord of an element", "control surface", "border point of the inner border"])
        save_figure(fig, FIGURES / "controlSurfacePlanform.png")


def section_axes(panels):
    """Stacked section panels at a common scale, aligned at a = 0; panels are (xlim, ylim) in metres."""
    left = min(xl[0] for xl, _ in panels)
    right = max(xl[1] for xl, _ in panels)
    width = (right - left) * SECTION_SCALE
    heights = [(yl[1] - yl[0]) * SECTION_SCALE for _, yl in panels]
    title_space, gap = 0.42, 0.15
    total = sum(heights) + len(panels) * title_space + gap * (len(panels) - 1) + LEGEND_SPACE
    fig = plt.figure(figsize=(width, total))
    axes, y = [], total
    for (xl, yl), h in zip(panels, heights):
        y -= title_space + h
        ax = fig.add_axes(((xl[0] - left) * SECTION_SCALE / width, y / total, (xl[1] - xl[0]) * SECTION_SCALE / width,
                           h / total))
        ax.set_xlim(*xl)
        ax.set_ylim(*yl)
        ax.set_aspect("equal")
        ax.axis("off")
        axes.append(ax)
        y -= gap
    return fig, axes


def panel_title(ax, content, left):
    ax.annotate(content, xy=(left, ax.get_ylim()[1]), xycoords="data", xytext=(0, 12), textcoords="offset points",
                ha="left", va="bottom", fontsize=FONT_SIZE["title"], color=INK, annotation_clip=False)


def draw_wing_section(ax, upper, lower, a_range, chord=None):
    """Wing section as a washed body with its outline; optionally the chord of the control surface."""
    parts = []
    for side in (upper, lower):
        part = side[(side[:, 0] >= a_range[0]) & (side[:, 0] <= a_range[1])]
        parts.append(part)
        ax.plot(*part.T, color=MUTED, lw=LINE["secondary"], zorder=2)
    ax.add_patch(Polygon(np.vstack([parts[0], parts[1][::-1]]), closed=True, facecolor=SERIES1, alpha=WASH,
                         edgecolor="none", zorder=0))
    if chord is not None:
        ax.plot([0.0, chord], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=4.2)
        for a in (0.0, chord):
            point_marker(ax, (a, 0.0))


def draw_device(ax, contour, color=DEVICE_COLOR, alpha=0.16, lw=None, zorder=4, line_alpha=1.0):
    if alpha:
        ax.add_patch(Polygon(contour, closed=True, facecolor=color, alpha=alpha, edgecolor="none", zorder=zorder))
    ax.plot(*np.vstack([contour, contour[:1]]).T, color=color, lw=lw or LINE["data"], alpha=line_alpha,
            zorder=zorder + 0.1)


def dimension(ax, a0, a1, b, content, above=True):
    """Dimension line with end ticks along a, labelled in ink."""
    tick = 0.03
    ax.plot([a0, a1], [b, b], color=INK2, lw=LINE["reference"], zorder=5)
    for a in (a0, a1):
        ax.plot([a, a], [b - tick, b + tick], color=INK2, lw=LINE["reference"], zorder=5)
    text(ax, (0.5 * (a0 + a1), b), content, (0, GAP - 3 if above else -(GAP - 3)), va="bottom" if above else "top")


def leader_line(ax, a, b_from, b_to):
    ax.plot([a, a], [b_from, b_to], color=COLORS["axis"], lw=LINE["reference"], zorder=1)


def figure_sections():
    """Sections at the inner borders: flap with leadingEdgeShape, slat with innerShape, spoiler with relHeightLE."""
    f_frame, f_chord, f_up, f_lo, f_contour, f_pts = flap_section()
    s_frame, s_chord, s_up, s_lo, s_contour, s_pts = slat_section()
    p_frame, p_chord, p_up, p_lo, p_contour, p_pts = spoiler_section()
    height, x_upper, x_lower = FLAP["leadingEdgeShape"]
    panels = [((-1.2, f_chord + 0.6), (-0.6, 0.55)), ((-0.2, 2.6), (-0.3, 0.35)), ((-1.2, p_chord + 1.6), (-0.35, 0.45))]
    with figure_style():
        fig, (flap_ax, slat_ax, spoiler_ax) = section_axes(panels)

        # (a) flap
        ax = flap_ax
        draw_wing_section(ax, f_up, f_lo, (-1.2, f_chord), chord=f_chord)
        draw_device(ax, f_contour)
        text(ax, (0.0, 0.0), r"$P_\mathrm{LE}$", (-GAP, -2), ha="right", va="top", color=INK2)
        text(ax, (f_chord, 0.0), r"$P_\mathrm{TE}$", (GAP, 0), ha="left", color=INK2)
        for key in ("nose", "upper", "lower"):
            point_marker(ax, f_pts[key])
        text(ax, f_pts["nose"], f"relHeightLE = {height:g}", (-GAP, 2), ha="right", va="bottom")
        top, bottom = 0.42, -0.47
        leader_line(ax, f_pts["upper"][0], f_pts["upper"][1], top)
        leader_line(ax, f_chord, 0.0, top)
        dimension(ax, f_pts["upper"][0], f_chord, top, f"xsiUpperSkin = {x_upper:g}")
        leader_line(ax, f_pts["lower"][0], f_pts["lower"][1], bottom)
        leader_line(ax, f_chord, 0.0, bottom)
        dimension(ax, f_pts["lower"][0], f_chord, bottom, f"xsiLowerSkin = {x_lower:g}", above=False)
        panel_title(ax, "(a) Flap: leading edge shape", -1.2)

        # (b) slat
        ax = slat_ax
        draw_wing_section(ax, s_up, s_lo, (-0.2, 2.6))
        draw_device(ax, s_contour)
        x_up, x_lo = SLAT["borders"]["inner"][2]
        h, xi = SLAT["innerShape"]
        for key, content, offset, ha, va in (("upper", f"xsiTEUpper = {x_up:g}", (GAP, GAP), "left", "bottom"),
                                             ("lower", f"xsiTELower = {x_lo:g}", (GAP, -GAP), "left", "top"),
                                             ("inner", f"innerShape: xsiTE = {xi:g}, relHeightTE = {h:g}", (GAP + 4, 0),
                                              "left", "center")):
            point_marker(ax, s_pts[key])
            text(ax, s_pts[key], content, offset, ha=ha, va=va)
        panel_title(ax, "(b) Slat: hollow rear side", -1.2)

        # (c) spoiler
        ax = spoiler_ax
        draw_wing_section(ax, p_up, p_lo, (-1.2, p_chord + 1.6))
        draw_device(ax, p_contour)
        x_le, x_te = SPOILER["borders"]["inner"][2]
        point_marker(ax, p_pts["le"])
        text(ax, (0.0, skin(p_up, 0.0)), f"xsiLE = {x_le:g}", (0, GAP), va="bottom")
        text(ax, (p_chord, skin(p_up, p_chord)), f"xsiTE = {x_te:g}", (GAP, GAP), ha="left", va="bottom")
        text(ax, p_pts["le"], f"relHeightLE = {SPOILER['relHeightLE']:g}", (-GAP, 0), ha="right")
        panel_title(ax, "(c) Spoiler: height of the leading edge", -1.2)

        legend(fig, [handle_line(MUTED, LINE["secondary"]), handle_line(DEVICE_COLOR, LINE["data"]), handle_point()],
               ["wing section at the inner border", "control surface", "defining point"])
        save_figure(fig, FIGURES / "controlSurfaceSections.png")


def figure_path():
    """Flap in the section of its inner border at the steps of its deflection path, with the hinge point."""
    f_frame, f_chord, f_up, f_lo, f_contour, _ = flap_section()
    p1 = device_hinges(FLAP)[0]
    eta, _, _ = FLAP["borders"]["inner"]
    hinge_xsi, hinge_height = FLAP["hinges"]["inner"]
    with figure_style():
        fig, (ax,) = section_axes([((-1.3, f_chord + 1.9), (-1.0, 0.45))])
        draw_wing_section(ax, f_up, f_lo, (-1.3, f_chord + 0.1))
        contour3d = f_frame.to3d(f_contour)
        hinges = []
        for parameter, angle, shift in FLAP["steps"]:
            moved = f_frame.to2d(deflect(contour3d, FLAP, parameter))
            undeflected = parameter == FLAP["steps"][0][0]
            draw_device(ax, moved, alpha=0.16 if undeflected else 0.0, zorder=4 if undeflected else 3.5,
                        line_alpha=1.0 if undeflected else 0.55)
            tail = moved[np.argmax(moved[:, 0])]
            text(ax, tail, f"controlParameter {parameter:g}", (GAP, 0), ha="left")
            hinges.append(f_frame.to2d(deflect(p1, FLAP, parameter))[0])
        # hinge point and its translation
        low, up = skin(f_lo, hinges[0][0]), skin(f_up, hinges[0][0])
        ax.plot([hinges[0][0]] * 2, [low, up], color=INK2, lw=LINE["reference"], zorder=5)
        arrow(ax, hinges[0], hinges[-1], color=INK, lw=LINE["secondary"], head=7)
        for hinge in hinges:
            point_marker(ax, hinge)
        lines = []
        for parameter, angle, shift in FLAP["steps"]:
            moved = "" if shift is None else f",   x {shift[0]:+g} m,   z {shift[2]:+g} m"
            lines.append(f"controlParameter {parameter:g}:   hingeLineRotation {angle:g}°{moved}")
        ax.annotate("\n".join(lines), xy=(-1.2, -0.58), xycoords="data", ha="left", va="top", fontsize=NOTE, color=INK,
                    linespacing=1.6, annotation_clip=False)
        legend(fig, [handle_line(MUTED, LINE["secondary"]), handle_line(DEVICE_COLOR, LINE["data"]), handle_point()],
               ["wing section at the inner border", "flap, undeflected and at the steps of its path",
                f"hinge point and its translation (hingeXsi {hinge_xsi:g}, hingeRelHeight {hinge_height:g})"])
        save_figure(fig, FIGURES / "controlSurfacePath.png")


# ------------------------------------------------------------------- variants
# A second example file showing the ways to describe the contour of a control surface. The devices sit on the
# same wing; the airfoil variants reference contours that this script computes from the parametric description,
# so that both ways describe the same shape.
VARIANTS_FILE = DOCUMENTATION.parent / "examples" / "controlSurfaceShapes.xml"

VARIANT_FLAPS = [
    {"uid": f"{WING_UID}_flap_plain", "name": "Flap with a straight leading edge",
     "borders": {"inner": (0.14, None, 0.72), "outer": (0.26, None, 0.72)},
     "hinges": {"inner": (0.76, 0.2), "outer": (0.76, 0.2)},
     "steps": [(0.0, 0.0, None), (1.0, 25.0, None)]},
    {"uid": f"{WING_UID}_flap_leadingEdgeShape", "name": "Flap with a rounded leading edge",
     "borders": {"inner": (0.28, None, 0.72), "outer": (0.40, None, 0.72)},
     "leadingEdgeShape": (0.5, 0.9, 0.7),
     "hinges": {"inner": (0.76, 0.2), "outer": (0.76, 0.2)},
     "steps": [(0.0, 0.0, None), (1.0, 25.0, None)]},
    {"uid": f"{WING_UID}_flap_airfoil", "name": "Flap with an airfoil contour",
     "borders": {"inner": (0.42, None, 0.72), "outer": (0.54, None, 0.72)},
     "leadingEdgeShape": (0.5, 0.9, 0.7), "airfoil": f"{WING_UID}_flapContour",
     "hinges": {"inner": (0.76, 0.2), "outer": (0.76, 0.2)},
     "steps": [(0.0, 0.0, None), (1.0, 25.0, None)]},
]
VARIANT_SLATS = [
    {"uid": f"{WING_UID}_slat_xsiTE", "name": "Slat with one trailing edge position",
     "borders": {"inner": (0.50, None, 0.15), "outer": (0.62, None, 0.15)},
     "innerShape": (0.45, 0.04),
     "hinges": {"inner": (0.05, 0.5), "outer": (0.05, 0.5)},
     "steps": [(0.0, 0.0, None), (1.0, -20.0, (-0.25, 0.0, -0.12))]},
    {"uid": f"{WING_UID}_slat_upperLower", "name": "Slat with separate upper and lower trailing edge positions",
     "borders": {"inner": (0.64, None, (0.15, 0.12)), "outer": (0.78, None, (0.15, 0.12))},
     "innerShape": (0.45, 0.04),
     "hinges": {"inner": (0.05, 0.5), "outer": (0.05, 0.5)},
     "steps": [(0.0, 0.0, None), (1.0, -20.0, (-0.25, 0.0, -0.12))]},
    {"uid": f"{WING_UID}_slat_airfoil", "name": "Slat with an airfoil contour",
     "borders": {"inner": (0.80, None, (0.15, 0.12)), "outer": (0.94, None, (0.15, 0.12))},
     "innerShape": (0.45, 0.04), "airfoil": f"{WING_UID}_slatContour",
     "hinges": {"inner": (0.05, 0.5), "outer": (0.05, 0.5)},
     "steps": [(0.0, 0.0, None), (1.0, -20.0, (-0.25, 0.0, -0.12))]},
]
VARIANT_SPOILER = {
    "uid": f"{WING_UID}_spoiler_variant", "name": "Spoiler",
    "borders": {"inner": (0.16, None, (0.55, 0.69)), "outer": (0.26, None, (0.56, 0.70))},
    "relHeightLE": 0.8,
    "hinges": {"inner": (0.56, 0.95), "outer": (0.57, 0.95)},
    "steps": [(0.0, 0.0, None), (1.0, -45.0, None)],
}


def device_profile(contour, chord, points=61):
    """Closed contour of a control surface as an airfoil: x along its chord, both normalized with the chord."""
    order = np.roll(contour, -int(np.argmax(contour[:, 0])), axis=0)
    if order[1, 1] > order[-1, 1]:  # run over the lower side first, as for a wing airfoil
        order = np.vstack([order[:1], order[1:][::-1]])
    index = np.linspace(0, len(order) - 1, points).round().astype(int)
    normalized = order[np.unique(index)] / chord
    return np.vstack([normalized, normalized[:1]])


def airfoil_from_points(uid, name, points):
    xs, zs = (points[:, 0], points[:, 1])
    return "\n".join([
        f'<wingAirfoil uID="{uid}">', f"    <name>{name}</name>", "    <pointList>",
        f"        <x>{vector(round(float(v), 6) + 0.0 for v in xs)}</x>",
        f"        <y>{vector([0.0] * len(xs))}</y>",
        f"        <z>{vector(round(float(v), 6) + 0.0 for v in zs)}</z>",
        "    </pointList>", "</wingAirfoil>",
    ])


def variant_profiles():
    """The contours of the airfoil variants, computed from their parametric description."""
    flap = next(d for d in VARIANT_FLAPS if "airfoil" in d)
    slat = next(d for d in VARIANT_SLATS if "airfoil" in d)
    _, f_chord, _, _, f_contour, _ = flap_section(flap)
    _, s_chord, _, _, s_contour, _ = slat_section(slat)
    return "\n".join([
        airfoil_from_points(flap["airfoil"], "Contour of the flap with a rounded leading edge",
                            device_profile(f_contour, f_chord)),
        airfoil_from_points(slat["airfoil"], "Contour of the slat with a hollow rear side",
                            device_profile(s_contour, s_chord)),
    ])


def airfoil_reference_xml(uid, chord=None):
    """Reference to an airfoil contour.

    TiGL 3.5 scales the thickness of the airfoil with scalZ alone, so that the contour only fits the wing if
    scalZ is the length of the chord of the border. By the definition of scalZ the value would be 1, because
    the airfoil is placed on that chord and scaled with it.
    """
    lines = ["<airfoil>", f"    <airfoilUID>{uid}</airfoilUID>", "    <rotX>90</rotX>", "    <scalY>1</scalY>"]
    if chord is not None:
        lines += ["    <!-- scalZ = 1: the airfoil is placed on the chord between the leading and the trailing",
                  "         edge point of this border and is scaled with it, here a chord of "
                  f"{chord:.4f} m.",
                  "         TiGL 3.5 scales the thickness with scalZ alone, as a length in metres instead of a",
                  "         fraction of that chord, and does not cut the control surface out of the wing. It",
                  "         therefore shows the contour far too thick, the more so the shorter the chord is.",
                  "         Setting scalZ to the length of the chord shows the contour correctly in TiGL; the",
                  "         point is being clarified with the TiGL developers. -->"]
    lines.append("    <scalZ>1</scalZ>")
    return "\n".join(lines + ["</airfoil>"])


def variant_flap_border_xml(side, device=None):
    device = device or FLAP
    eta_le, eta_te, xsi_le = device["borders"][side]
    lines = [f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1)]
    if eta_te is not None:
        lines.append(indent(iso_xml("etaTE", "eta", eta_te), 1))
    lines.append(indent(iso_xml("xsiLE", "xsi", xsi_le), 1))
    if "airfoil" in device:
        _, chord = border_frame(eta_le, xsi_le, eta_te if eta_te is not None else eta_le, 1.0)
        lines.append(indent(airfoil_reference_xml(device["airfoil"], chord), 1))
    elif "leadingEdgeShape" in device:
        height, upper, lower = device["leadingEdgeShape"]
        lines += ["    <leadingEdgeShape>", f"        <relHeightLE>{height:g}</relHeightLE>",
                  f"        <xsiUpperSkin>{upper:g}</xsiUpperSkin>", f"        <xsiLowerSkin>{lower:g}</xsiLowerSkin>",
                  "    </leadingEdgeShape>"]
    lines.append(f"</{side}Border>")
    return "\n".join(lines)


def variant_slat_border_xml(side, device=None):
    device = device or SLAT
    eta_le, eta_te, xsi = device["borders"][side]
    lines = [f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1)]
    if eta_te is not None:
        lines.append(indent(iso_xml("etaTE", "eta", eta_te), 1))
    if isinstance(xsi, tuple):
        lines += [f"    <xsiTEUpper>{xsi[0]:g}</xsiTEUpper>", f"    <xsiTELower>{xsi[1]:g}</xsiTELower>"]
    else:
        lines.append(indent(iso_xml("xsiTE", "xsi", xsi), 1))
    if "airfoil" in device:
        xsi_te = max(xsi) if isinstance(xsi, tuple) else xsi
        _, chord = border_frame(eta_le, 0.0, eta_te if eta_te is not None else eta_le, xsi_te)
        lines.append(indent(airfoil_reference_xml(device["airfoil"], chord), 1))
    else:
        height, inner_xsi = device["innerShape"]
        lines += ["    <innerShape>", f"        <relHeightTE>{height:g}</relHeightTE>",
                  f"        <xsiTE>{inner_xsi:g}</xsiTE>", "    </innerShape>"]
    lines.append(f"</{side}Border>")
    return "\n".join(lines)


def variant_device_xml(tag, device, border_xml, translations=True):
    return "\n".join([
        f'<{tag} uID="{device["uid"]}">', f"    <name>{device['name']}</name>", f"    <parentUID>{CS_UID}</parentUID>",
        "    <outerShape>", indent(border_xml("inner", device), 2), indent(border_xml("outer", device), 2),
        "    </outerShape>", indent(path_xml(device, translations), 1), f"</{tag}>",
    ])


def variant_control_surfaces_xml():
    leading = [variant_device_xml("leadingEdgeDevice", d, variant_slat_border_xml) for d in VARIANT_SLATS]
    trailing = [variant_device_xml("trailingEdgeDevice", d, variant_flap_border_xml) for d in VARIANT_FLAPS]
    spoiler = variant_device_xml("spoiler", VARIANT_SPOILER, spoiler_border_variant_xml, translations=False)
    return "\n".join([
        "<controlSurfaces>",
        "    <leadingEdgeDevices>", *(indent(x, 2) for x in leading), "    </leadingEdgeDevices>",
        "    <trailingEdgeDevices>", *(indent(x, 2) for x in trailing), "    </trailingEdgeDevices>",
        "    <spoilers>", indent(spoiler, 2), "    </spoilers>",
        "</controlSurfaces>",
    ])


def spoiler_border_variant_xml(side, device=None):
    device = device or SPOILER
    eta_le, eta_te, (xsi_le, xsi_te) = device["borders"][side]
    lines = [f"<{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 1)]
    if eta_te is not None:
        lines.append(indent(iso_xml("etaTE", "eta", eta_te), 1))
    lines += [indent(iso_xml("xsiLE", "xsi", xsi_le), 1), indent(iso_xml("xsiTE", "xsi", xsi_te), 1),
              f"    <relHeightLE>{device['relHeightLE']:g}</relHeightLE>", f"</{side}Border>"]
    return "\n".join(lines)


def write_variants():
    write_cpacs_file(
        VARIANTS_FILE,
        generator=Path(__file__),
        name="Control surface shapes",
        description="Flaps, slats and a spoiler on one wing, showing the ways to describe the contour of a control surface.",
        model_uid="ControlSurfaceShapesAircraft",
        model_name="Control surface shapes example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml(variant_control_surfaces_xml()))],
        extra_profiles=[("wingAirfoils", airfoil_xml() + "\n" + variant_profiles())],
    )


# ------------------------------------------------------------------- cut-outs
# The cut-out in the wing (controlSurfaceWingCutOutType): at each of its borders the cut runs from the point of
# the lower skin at lowerSkin/xsi to the point of the upper skin at upperSkin/xsi, straight or, with a control
# point, as a curve tangential to the skin through that point. Between the two borders the cut-out is a ruled
# surface, as the outer shape of a control surface is. All xsi are xsi of the component segment.
CUTOUT_COLOR = COLORS["series3"]
CUT_OUTS_FILE = DOCUMENTATION.parent / "examples" / "controlSurfaceCutOuts.xml"

FLAP_CUT_OUT_COMMENT = [
    "Cut-out in the wing for the flap: the cut lies ahead of the leading edge of the flap on both",
    "skins. Without innerBorder and outerBorder the cut-out ends at the borders of the flap.",
]
SLAT_CUT_OUT_COMMENT = [
    "Cut-out in the wing for the slat: the cut lies behind the trailing edge of the slat on both",
    "skins, and the control point places the nose of the remaining wing inside the hollow rear side",
    "of the slat. Its borders are 0.02 further in and out than the borders of the slat.",
]
TIGL_CUT_OUT_COMMENT = [
    "TiGL 3.5 reads this file and builds the clean wing, but aborts as soon as it builds the wing",
    "with its cut-outs, whatever a wingCutOut contains; the wing can therefore be neither shown nor",
    "exported with that version. The point is being clarified with the TiGL developers.",
    "examples/controlSurfaces.xml shows the same wing without cut-outs.",
]


def comment_xml(lines):
    return "\n".join(["<!-- " + lines[0]] + ["     " + line for line in lines[1:-1]]
                     + ["     " + lines[-1] + " -->"]) if len(lines) > 1 else f"<!-- {lines[0]} -->"


def cut_out_xml(cutout):
    lines = ["<wingCutOut>"]
    for tag in ("upperSkin", "lowerSkin"):
        inner, outer = cutout[tag]
        lines += [f"    <{tag}>", f"        <xsiInnerBorder>{inner:g}</xsiInnerBorder>",
                  f"        <xsiOuterBorder>{outer:g}</xsiOuterBorder>", f"    </{tag}>"]
    if "controlPoint" in cutout:
        lines.append("    <cutOutProfileControlPoint>")
        for side in ("inner", "outer"):
            height, xsi = cutout["controlPoint"][side]
            lines += [f"        <{side}Border>", f"            <relHeight>{height:g}</relHeight>",
                      f"            <xsi>{xsi:g}</xsi>", f"        </{side}Border>"]
        lines.append("    </cutOutProfileControlPoint>")
    for side in ("inner", "outer"):
        if "borders" not in cutout:
            continue
        eta_le, eta_te = cutout["borders"][side]
        lines += [f"    <{side}Border>", indent(iso_xml("etaLE", "eta", eta_le), 2),
                  indent(iso_xml("etaTE", "eta", eta_te), 2), f"    </{side}Border>"]
    lines.append("</wingCutOut>")
    return "\n".join(lines)


def cut_out_device_xml(tag, device, border_xml, cutout, comment):
    return "\n".join([
        f'<{tag} uID="{device["uid"]}">', f"    <name>{device['name']}</name>", f"    <parentUID>{CS_UID}</parentUID>",
        "    <outerShape>", indent(border_xml("inner"), 2), indent(border_xml("outer"), 2), "    </outerShape>",
        indent(comment_xml(comment), 1), indent(cut_out_xml(cutout), 1), indent(path_xml(device), 1), f"</{tag}>",
    ])


def cut_outs_control_surfaces_xml():
    return "\n".join([
        comment_xml(TIGL_CUT_OUT_COMMENT),
        "<controlSurfaces>",
        "    <leadingEdgeDevices>",
        indent(cut_out_device_xml("leadingEdgeDevice", SLAT, slat_border_xml, SLAT_CUTOUT, SLAT_CUT_OUT_COMMENT), 2),
        "    </leadingEdgeDevices>",
        "    <trailingEdgeDevices>",
        indent(cut_out_device_xml("trailingEdgeDevice", FLAP, flap_border_xml, FLAP_CUTOUT, FLAP_CUT_OUT_COMMENT), 2),
        "    </trailingEdgeDevices>",
        "</controlSurfaces>",
    ])


def write_cut_outs():
    write_cpacs_file(
        CUT_OUTS_FILE,
        generator=Path(__file__),
        name="Control surface cut-outs",
        description="A flap and a slat with the cut-outs they need in the wing.",
        model_uid="ControlSurfaceCutOutsAircraft",
        model_name="Control surface cut-outs example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml(cut_outs_control_surfaces_xml()))],
        extra_profiles=[("wingAirfoils", airfoil_xml())],
    )


def cut_out_etas(device, cutout, side):
    """Border of a cut-out as (etaLE, etaTE); without innerBorder and outerBorder it is the border of the device."""
    if "borders" in cutout:
        return cutout["borders"][side]
    eta = device["borders"][side][0]
    return eta, eta


def cut_out_frame(device, cutout, kind, side):
    """Frame of a cut-out border and the position along its axis of a xsi of the component segment.

    The border of the cut-out is built like the border of the control surface: its plane runs through the two
    points of the chord surface at the eta values of the cut-out and the chordwise positions of the
    corresponding border of the control surface.
    """
    eta_le, eta_te = cut_out_etas(device, cutout, side)
    if kind == "flap":
        xsi_le = device["borders"][side][2]
        frame, chord = border_frame(eta_le, xsi_le, eta_te, 1.0)
        return frame, chord, lambda xsi: chord * (xsi - xsi_le) / (1.0 - xsi_le)
    xsi = device["borders"][side][2]
    xsi_te = max(xsi) if isinstance(xsi, tuple) else xsi
    frame, chord = border_frame(eta_le, 0.0, eta_te, xsi_te)
    return frame, chord, lambda value: chord * value / xsi_te


def cut_out_section(device, cutout, kind, side, points=41):
    """Cut of a cut-out at one of its borders: the frame of the border, the cut (2D in that frame) and the
    indices of its defining points in the cut."""
    frame, chord, axis = cut_out_frame(device, cutout, kind, side)
    eta_le, _ = cut_out_etas(device, cutout, side)
    upper, lower = frame.section(to_segment(min(eta_le, 0.999999), 0.0)[0])
    index = 0 if side == "inner" else 1
    a_upper, a_lower = axis(cutout["upperSkin"][index]), axis(cutout["lowerSkin"][index])
    p_upper = np.array([a_upper, skin(upper, a_upper)])
    p_lower = np.array([a_lower, skin(lower, a_lower)])
    if "controlPoint" in cutout:
        height, xsi = cutout["controlPoint"][side]
        a_nose = axis(xsi)
        nose = np.array([a_nose, skin(lower, a_nose) + height * (skin(upper, a_nose) - skin(lower, a_nose))])
        scale = 0.6 * np.linalg.norm(p_upper - nose)
        half = points // 2 + 1
        cut = np.vstack([hermite(p_lower, scale * skin_tangent(lower, a_lower, -1), nose,
                                 scale * np.array([0.0, 1.0]), half),
                         hermite(nose, scale * np.array([0.0, 1.0]), p_upper,
                                 scale * skin_tangent(upper, a_upper, 1), half)[1:]])
        marks = {"lower": 0, "nose": half - 1, "upper": len(cut) - 1}
    else:
        step = np.linspace(0.0, 1.0, points)[:, None]
        cut = p_lower + step * (p_upper - p_lower)
        marks = {"lower": 0, "upper": len(cut) - 1}
    return frame, cut, marks


def cut_out_in_plane(device, cutout, kind, frame):
    """The cut of a cut-out in a plane between its borders.

    Between its two borders the cut-out is the ruled surface through the two cuts, so the cut in any plane in
    between is the intersection of that surface with the plane. At a border itself the result is the cut there.
    """
    contours = []
    for side in ("inner", "outer"):
        border, cut, marks = cut_out_section(device, cutout, kind, side)  # both cuts have the same points
        contours.append(border.to3d(cut))
    inner, outer = contours
    distance_inner = (inner - frame.origin) @ frame.w
    distance_outer = (outer - frame.origin) @ frame.w
    share = distance_inner / (distance_inner - distance_outer)
    return frame.to2d(inner + share[:, None] * (outer - inner)), marks


def removed_region(kind, upper, lower, cut):
    """Polygon of the part of the wing section that the cut-out removes: behind the cut for a trailing edge
    device, ahead of it for a leading edge device."""
    a_lower, a_upper = cut[0, 0], cut[-1, 0]
    end_upper, end_lower = (upper[-1, 0], lower[-1, 0]) if kind == "flap" else (upper[0, 0], lower[0, 0])
    return np.vstack([cut, skin_polyline(upper, a_upper, end_upper)[1:],
                      skin_polyline(lower, end_lower, a_lower)[1:]])


def cut_out_planform(device, cutout, kind):
    """Top view outline of a cut-out in wing coordinates."""
    etas = [cut_out_etas(device, cutout, side)[0] for side in ("inner", "outer")]
    front = [min(cutout["upperSkin"][i], cutout["lowerSkin"][i]) for i in (0, 1)]
    rear = [max(cutout["upperSkin"][i], cutout["lowerSkin"][i]) for i in (0, 1)]
    kink = [e for e in element_etas()[0] if etas[0] < e < etas[1]]
    if kind == "flap":
        return np.array([component_segment_point(etas[0], front[0]), component_segment_point(etas[1], front[1])]
                        + [component_segment_point(e, 1.0) for e in [etas[1], *kink[::-1], etas[0]]])
    return np.array([component_segment_point(e, 0.0) for e in [etas[0], *kink, etas[1]]]
                    + [component_segment_point(etas[1], rear[1]), component_segment_point(etas[0], rear[0])])


def figure_cut_out_planform():
    """Top view of the wing with the flap and the slat and the cut-outs they need in the wing."""
    devices = ((FLAP, FLAP_CUTOUT, "flap"), (SLAT, SLAT_CUTOUT, "slat"))
    with figure_style():
        fig, ax = make_figure((-8.3, 1.4))
        planform(ax)
        outline(ax)
        for device, cutout, kind in devices:
            cut = view(cut_out_planform(device, cutout, kind))
            ax.add_patch(Polygon(cut, closed=True, facecolor=CUTOUT_COLOR, alpha=0.14, edgecolor="none", zorder=3.8))
            ax.plot(*np.vstack([cut, cut[:1]]).T, color=CUTOUT_COLOR, lw=LINE["data"], zorder=3.9)
            shape = view(planform_outline(device, kind))
            ax.plot(*np.vstack([shape, shape[:1]]).T, color=DEVICE_COLOR, lw=LINE["data"], zorder=4.1)
            text(ax, shape.mean(axis=0), kind, color=INK)
        # the borders of the slat cut-out; the flap cut-out ends at the borders of the flap
        for side in ("inner", "outer"):
            eta = SLAT_CUTOUT["borders"][side][0]
            point = view(component_segment_point(eta, 0.0))
            point_marker(ax, point)
            text(ax, point, f"{side} border: etaLE = {eta:g}", (GAP, GAP), ha="left", va="bottom")
        element_labels(ax)
        axes_mark(ax)
        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(DEVICE_COLOR, LINE["data"]),
                     handle_line(CUTOUT_COLOR, LINE["data"]), handle_point()],
               ["chord of an element", "control surface", "cut-out in the wing", "border point of the cut-out"])
        save_figure(fig, FIGURES / "controlSurfaceCutOutPlanform.png")


def figure_cut_out_sections():
    """Sections at the inner borders of the flap and the slat: the cut-out and the control surface in it."""
    f_frame, f_chord, f_up, f_lo, f_contour, _ = flap_section()
    s_frame, s_chord, s_up, s_lo, s_contour, _ = slat_section()
    f_cut, f_marks = cut_out_in_plane(FLAP, FLAP_CUTOUT, "flap", f_frame)
    s_cut, s_marks = cut_out_in_plane(SLAT, SLAT_CUTOUT, "slat", s_frame)
    panels = [((-1.0, f_chord + 0.25), (-0.26, 0.36)), ((-0.42, 1.3), (-0.36, 0.26))]
    with figure_style():
        fig, (flap_ax, slat_ax) = section_axes(panels)

        # (a) flap: the cut is the straight line between the two points on the skin
        ax = flap_ax
        draw_wing_section(ax, f_up, f_lo, (-1.0, f_chord + 0.25))
        draw_device(ax, removed_region("flap", f_up, f_lo, f_cut), color=CUTOUT_COLOR, alpha=0.16, zorder=3)
        draw_device(ax, f_contour, alpha=0.0, zorder=3.6)
        ax.plot(*f_cut.T, color=CUTOUT_COLOR, lw=LINE["data"], zorder=4.2)
        top, bottom = 0.29, -0.2
        for key, content, level, va in (("upper", f"upperSkin: xsiInnerBorder = {FLAP_CUTOUT['upperSkin'][0]:g}",
                                         top, "bottom"),
                                        ("lower", f"lowerSkin: xsiInnerBorder = {FLAP_CUTOUT['lowerSkin'][0]:g}",
                                         bottom, "top")):
            point = f_cut[f_marks[key]]
            leader_line(ax, point[0], point[1], level)
            point_marker(ax, point)
            text(ax, (point[0], level), content, (0, GAP - 3 if va == "bottom" else -(GAP - 3)), va=va)
        panel_title(ax, "(a) Flap: cut in the upper and the lower skin", -1.0)

        # (b) slat: the cut runs through the control point, so the wing keeps a nose
        ax = slat_ax
        draw_wing_section(ax, s_up, s_lo, (-0.15, 1.3))
        draw_device(ax, removed_region("slat", s_up, s_lo, s_cut), color=CUTOUT_COLOR, alpha=0.16, zorder=3)
        draw_device(ax, s_contour, alpha=0.0, zorder=3.6)
        ax.plot(*s_cut.T, color=CUTOUT_COLOR, lw=LINE["data"], zorder=4.2)
        height, xsi = SLAT_CUTOUT["controlPoint"]["inner"]
        for key, content, offset, ha, va in (("upper", f"upperSkin: xsiInnerBorder = {SLAT_CUTOUT['upperSkin'][0]:g}",
                                              (GAP, GAP), "left", "bottom"),
                                             ("lower", f"lowerSkin: xsiInnerBorder = "
                                              f"{SLAT_CUTOUT['lowerSkin'][0]:g}", (GAP, -GAP), "left", "top")):
            point = s_cut[s_marks[key]]
            point_marker(ax, point)
            text(ax, point, content, offset, ha=ha, va=va)
        nose = s_cut[s_marks["nose"]]
        leader_line(ax, nose[0], nose[1], -0.3)
        point_marker(ax, nose)
        text(ax, (nose[0], -0.3), f"cutOutProfileControlPoint: xsi = {xsi:g}, relHeight = {height:g}",
             (0, -(GAP - 3)), va="top")
        panel_title(ax, "(b) Slat: cut through a control point", -0.42)

        legend(fig, [handle_line(MUTED, LINE["secondary"]), handle_line(CUTOUT_COLOR, LINE["data"]),
                     handle_line(DEVICE_COLOR, LINE["data"]), handle_point()],
               ["wing section at the inner border", "cut and the part of the wing it removes", "control surface",
                "defining point"])
        save_figure(fig, FIGURES / "controlSurfaceCutOutSections.png")


# ------------------------------------------------------------------------ main
def main():
    save_equation(HINGE_POINT_LINES, EQUATIONS / "controlSurfaceHingePoint")
    save_equation(DEFLECTION_LINES, EQUATIONS / "controlSurfaceDeflection")
    figure_planform()
    figure_sections()
    figure_path()
    figure_cut_out_planform()
    figure_cut_out_sections()
    write_example()
    write_variants()
    write_cut_outs()
    for path in (EXAMPLE_FILE, VARIANTS_FILE, CUT_OUTS_FILE):
        print(f"Written {path.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for controlSurfacesType:\n")
    print(excerpt_control_surfaces_xml())
    for tag, device, border in (("trailingEdgeDevice", FLAP, flap_border_xml), ("leadingEdgeDevice", SLAT, slat_border_xml),
                                ("spoiler", SPOILER, spoiler_border_xml)):
        print(f"\nExcerpt for {tag}Type:\n")
        print(device_xml(tag, device, border, translations=tag != "spoiler"))
    for name, cutout in (("the flap", FLAP_CUTOUT), ("the slat", SLAT_CUTOUT)):
        print(f"\nExcerpt for controlSurfaceWingCutOutType ({name}):\n")
        print(cut_out_xml(cutout))


if __name__ == "__main__":
    main()

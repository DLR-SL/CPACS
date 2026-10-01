# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of the aerodynamic
coordinate system (cpacsType, section 3) and of the aerodynamic maps
(aeroPerformanceType, aeroPerformanceMapType).

Run from the repository root:

    uv run documentation/scripts/aeroPerformance.py

The script writes

    documentation/figures/aeroAxesSide.png
    documentation/figures/aeroAxesTop.png
    documentation/equations/aeroAxes.{tex,png}
    documentation/equations/aeroCoefficients.{tex,png}
    examples/aeroPerformance.xml

and prints the excerpt shown in the documentation. The schema documentation is not
written by this script; copy the printed excerpt there when the example changes.

Definition shown (as in the documentation): the axes d, s and l of the aerodynamic
coordinate system, given in the CPACS coordinate system (x to the rear, y to the right,
z upwards), are

    e_d = ( cos(a) cos(b), -sin(b), sin(a) cos(b))   direction of the free stream
    e_s = ( cos(a) sin(b),  cos(b), sin(a) sin(b))
    e_l = (-sin(a),         0,      cos(a)       )

with the angle of attack a and the sideslip angle b. Both are positive about their axes
(right-hand rule) from the free stream to the CPACS axes: turning e_d by b about e_l
and then by a about the y-axis gives the x-axis. A positive angle of attack means a
free stream from below, a positive sideslip angle a free stream from the right.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Wedge

from example_xml import indent, vector, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, dot, figure_style, label, save_equation, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "aeroPerformance.xml"

AERO = COLORS["series1"]
FLOW = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]
# Opaque fill of the aircraft (muted at 10 % on white), so that a component hides the parts behind it.
AIRCRAFT_FILL = "#f3f3f2"

# --- Aircraft: a generic short-range airliner in the CPACS coordinate system, nose at the origin [m] ---
FUSELAGE_LENGTH = 37.6
FUSELAGE_RADIUS = 1.98
NOSE_LENGTH = 6.5
TAIL_START = 25.0
TAIL_END_UPPER, TAIL_END_LOWER, TAIL_END_HALF_WIDTH = 1.43, 1.05, 0.25
NOSE_DROOP = 0.45  # the nose tip lies below the fuselage axis

WING = {"x_root": 12.5, "z_root": -1.65, "semi_span": 17.05, "root_chord": 6.0, "tip_chord": 1.6,
        "sweep": 27.0, "dihedral": 5.0, "thickness": (0.13, 0.10), "y_body": 1.2}
TAILPLANE = {"x_root": 32.0, "z_root": 1.1, "semi_span": 6.2, "root_chord": 4.0, "tip_chord": 1.8,
             "sweep": 32.0, "dihedral": 6.0, "thickness": (0.10, 0.09), "y_body": 0.8}
FIN = {"root": ((30.5, 1.89), (37.3, 1.5)), "tip": ((34.2, 6.6), (36.2, 6.6)), "thickness": 0.10}
NACELLE = {"x": (12.4, 17.0), "y": 5.75, "radius": 0.98, "drop": 1.35}

# --- Angles of the figures (drawn larger than in cruise, so that the construction is legible) ---
ALPHA_FIGURE = 15.0
BETA_FIGURE = 15.0
AXIS_LENGTH = 8.0
FLOW_LENGTH = 7.5


# --- The aerodynamic axes -------------------------------------------------------------------------------

def aero_axes(alpha_deg, beta_deg):
    """Unit vectors e_d, e_s, e_l of the aerodynamic axes in the CPACS coordinate system."""
    a, b = np.radians(alpha_deg), np.radians(beta_deg)
    e_d = np.array([np.cos(a) * np.cos(b), -np.sin(b), np.sin(a) * np.cos(b)])
    e_s = np.array([np.cos(a) * np.sin(b), np.cos(b), np.sin(a) * np.sin(b)])
    e_l = np.array([-np.sin(a), 0.0, np.cos(a)])
    return e_d, e_s, e_l


def rotation(axis, angle_deg):
    """Rotation matrix about a unit axis by an angle, right-hand rule (Rodrigues)."""
    k = np.asarray(axis, dtype=float)
    t = np.radians(angle_deg)
    kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + np.sin(t) * kx + (1.0 - np.cos(t)) * kx @ kx


def check_aero_axes():
    """The axes are orthonormal and right-handed, the angles turn the free stream onto the x-axis as the text
    says, and the free stream agrees with the aerospace convention (LN 9300 / ISO 1151, x forward, z down)."""
    worst = 0.0
    for alpha in np.linspace(-30.0, 30.0, 13):
        for beta in np.linspace(-30.0, 30.0, 13):
            e_d, e_s, e_l = aero_axes(alpha, beta)
            m = np.column_stack([e_d, e_s, e_l])
            worst = max(worst, np.abs(m.T @ m - np.eye(3)).max(), abs(np.linalg.det(m) - 1.0))
            # beta about the l-axis, then alpha about the y-axis: free stream onto the x-axis
            turned = rotation((0.0, 1.0, 0.0), alpha) @ rotation(e_l, beta) @ e_d
            worst = max(worst, np.abs(turned - (1.0, 0.0, 0.0)).max())
            # flight velocity in body axes of the norm: V (cos a cos b, sin b, sin a cos b); CPACS axes are the
            # norm axes turned by 180 deg about y, and the free stream is the negative flight velocity
            a, b = np.radians(alpha), np.radians(beta)
            v_norm = np.array([np.cos(a) * np.cos(b), np.sin(b), np.sin(a) * np.cos(b)])
            worst = max(worst, np.abs(-v_norm * (-1.0, 1.0, -1.0) - e_d).max())
    assert worst < 1e-12, worst
    # signs as stated in the documentation
    e_d, _, _ = aero_axes(10.0, 0.0)
    assert e_d[2] > 0.0  # positive angle of attack: the free stream moves upwards, i.e. comes from below
    e_d, _, _ = aero_axes(0.0, 10.0)
    assert e_d[1] < 0.0  # positive sideslip angle: the free stream moves to the left, i.e. comes from the right
    return worst


# --- Example data: a linear model of a short-range airliner at low speed ----------------------------------

def wing_reference():
    """Reference area (trapezoidal planform through the fuselage), mean aerodynamic chord and the x-coordinate
    of its leading edge, computed from the planform of the figures."""
    s, cr, ct = WING["semi_span"], WING["root_chord"], WING["tip_chord"]
    taper = ct / cr
    area = s * (cr + ct)
    mac = 2.0 / 3.0 * cr * (1.0 + taper + taper**2) / (1.0 + taper)
    y_mac = s / 3.0 * (1.0 + 2.0 * taper) / (1.0 + taper)
    x_mac = WING["x_root"] + y_mac * np.tan(np.radians(WING["sweep"]))
    return area, mac, x_mac


ALTITUDE = 1200.0
MACH = 0.2
ANGLES_OF_ATTACK = (-2.0, 0.0, 2.0, 4.0, 6.0)
SIDESLIP_ANGLES = (0.0, 4.0)
# Linear aerodynamics [1/rad]; the moments refer to the reference point at the leading edge of the mean
# aerodynamic chord and are normalized with the mean aerodynamic chord, as the documentation states.
LIFT_SLOPE = 5.0
ZERO_LIFT_ANGLE = -2.5
ZERO_LIFT_DRAG, INDUCED_DRAG_FACTOR, SIDESLIP_DRAG = 0.022, 0.045, 0.3
SIDE_FORCE_SLOPE = -0.9  # free stream from the right pushes the aircraft to the left
PITCH_AT_NEUTRAL_POINT = 0.10
NEUTRAL_POINT = 0.45  # aft of the reference point, in mean aerodynamic chords
# Lateral moments about the d- and l-axis. With one reference length (the chord instead of the span) and the
# axes d and l pointing backwards and upwards, these are the norm values Cl_beta = -0.1 and Cn_beta = +0.12
# multiplied by -span/chord: a free stream from the right lifts the right wing (cmd > 0) and turns the nose to
# the right into the wind (cml < 0).
ROLL_SLOPE = 0.8
YAW_SLOPE = -1.0


def aero_map():
    """Vectors of the aerodynamic map: one entry per combination of sideslip angle and angle of attack."""
    rows = []
    for beta in SIDESLIP_ANGLES:
        for alpha in ANGLES_OF_ATTACK:
            a, b = np.radians(alpha), np.radians(beta)
            cl = LIFT_SLOPE * (a - np.radians(ZERO_LIFT_ANGLE))
            cd = ZERO_LIFT_DRAG + INDUCED_DRAG_FACTOR * cl**2 + SIDESLIP_DRAG * b**2
            cs = SIDE_FORCE_SLOPE * b
            cms = PITCH_AT_NEUTRAL_POINT - NEUTRAL_POINT * cl
            rows.append({"altitude": ALTITUDE, "machNumber": MACH, "angleOfSideslip": beta, "angleOfAttack": alpha,
                         "cd": cd, "cs": cs, "cl": cl, "cmd": ROLL_SLOPE * b, "cms": cms, "cml": YAW_SLOPE * b})
    return rows


def rounded(values, digits=4):
    return [round(float(v), digits) + 0.0 for v in values]  # + 0.0 turns -0.0 into 0.0


def aero_performance_map_xml():
    rows = aero_map()
    names = ("altitude", "machNumber", "angleOfSideslip", "angleOfAttack", "cd", "cs", "cl", "cmd", "cms", "cml")
    return "\n".join(f'<{name}>{vector(rounded(row[name] for row in rows))}</{name}>'
                     for name in names)


def reference_xml():
    area, mac, x_mac = wing_reference()
    return "\n".join([
        f"<area>{area:.2f}</area>",
        f"<length>{mac:.3f}</length>",
        '<point uID="referencePoint">',
        f"    <x>{x_mac:.3f}</x>",
        "    <y>0</y>",
        "    <z>0</z>",
        "</point>"])


def aero_performance_xml():
    return "\n".join([
        "<aeroPerformance>",
        '    <aeroMap uID="aeroMap_clean">',
        "        <name>Clean configuration, low speed</name>",
        "        <description>Linear model of a short-range airliner, control surfaces in neutral position</description>",
        "        <boundaryConditions>",
        "            <atmosphericModel>ISA</atmosphericModel>",
        "        </boundaryConditions>",
        "        <aeroPerformanceMap>",
        indent(aero_performance_map_xml(), 3),
        "        </aeroPerformanceMap>",
        "    </aeroMap>",
        "</aeroPerformance>"])


def write_example():
    write_cpacs_file(EXAMPLE_FILE, generator=Path(__file__), name="Aerodynamic map",
                     description="Aerodynamic coefficients in the aerodynamic coordinate system",
                     model_uid="aircraft", model_name="Short-range airliner", components_tag=None, components="",
                     profiles_tag=None, profiles=None,
                     extra_components=[("reference", reference_xml()), ("analyses", aero_performance_xml())])


# --- Aircraft outlines -----------------------------------------------------------------------------------

def clustered(start, end, n, towards_start=True):
    """Samples between start and end, closer together towards the start (where the nose bends most)."""
    u = np.linspace(0.0, 1.0, n)
    t = 1.0 - np.cos(0.5 * np.pi * u) if towards_start else np.sin(0.5 * np.pi * u)
    return start + (end - start) * t


def fuselage_stations():
    return np.concatenate([clustered(0.0, NOSE_LENGTH, 60), np.linspace(NOSE_LENGTH, TAIL_START, 3)[1:],
                           np.linspace(TAIL_START, FUSELAGE_LENGTH, 40)[1:]])


def fuselage_side():
    """Closed outline of the fuselage in the x-z plane."""
    x = fuselage_stations()
    upper, lower = np.empty_like(x), np.empty_like(x)
    for i, xi in enumerate(x):
        if xi <= NOSE_LENGTH:
            t = xi / NOSE_LENGTH
            h = FUSELAGE_RADIUS * np.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2))
            zc = -NOSE_DROOP * (1.0 - t) ** 2
            upper[i], lower[i] = zc + h, zc - h
        elif xi <= TAIL_START:
            upper[i], lower[i] = FUSELAGE_RADIUS, -FUSELAGE_RADIUS
        else:
            t = (xi - TAIL_START) / (FUSELAGE_LENGTH - TAIL_START)
            upper[i] = FUSELAGE_RADIUS - (FUSELAGE_RADIUS - TAIL_END_UPPER) * t**2.2
            lower[i] = -FUSELAGE_RADIUS + (FUSELAGE_RADIUS + TAIL_END_LOWER) * t**1.8
    return np.vstack([np.column_stack([x, upper]), np.column_stack([x[::-1], lower[::-1]])])


def fuselage_top():
    """Closed outline of the fuselage in the x-y plane."""
    x = fuselage_stations()
    half = np.empty_like(x)
    for i, xi in enumerate(x):
        if xi <= NOSE_LENGTH:
            half[i] = FUSELAGE_RADIUS * np.sqrt(max(0.0, 1.0 - (1.0 - xi / NOSE_LENGTH) ** 2))
        elif xi <= TAIL_START:
            half[i] = FUSELAGE_RADIUS
        else:
            t = (xi - TAIL_START) / (FUSELAGE_LENGTH - TAIL_START)
            half[i] = FUSELAGE_RADIUS - (FUSELAGE_RADIUS - TAIL_END_HALF_WIDTH) * t**1.8
    return np.vstack([np.column_stack([x, half]), np.column_stack([x[::-1], -half[::-1]])])


def thickness(xc):
    """Thickness distribution of a symmetric NACA four-digit airfoil of unit thickness."""
    return 5.0 * (0.2969 * np.sqrt(xc) - 0.1260 * xc - 0.3516 * xc**2 + 0.2843 * xc**3 - 0.1036 * xc**4)


def airfoil(leading_edge, chord, relative_thickness, plane):
    """Points of a symmetric airfoil; plane "xz" for a horizontal surface seen from the side, "xy" for a
    vertical one seen from above."""
    xc = clustered(0.0, 1.0, 50)
    t = relative_thickness * chord * thickness(xc)
    x = leading_edge[0] + chord * xc
    if plane == "xz":
        return np.vstack([np.column_stack([x, leading_edge[1] + t]), np.column_stack([x, leading_edge[1] - t])])
    return np.vstack([np.column_stack([x, t]), np.column_stack([x, -t])])


def convex_hull(points):
    """Convex hull (monotone chain), counter-clockwise."""

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    pts = sorted(map(tuple, np.round(points, 9)))

    def half(sequence):
        hull = []
        for p in sequence:
            while len(hull) >= 2 and cross(hull[-2], hull[-1], p) <= 0:
                hull.pop()
            hull.append(p)
        return hull

    lower, upper = half(pts), half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1])


def lifting_surface_section(surface, y):
    """Leading edge (x, z) and chord of a horizontal lifting surface at the lateral position y."""
    s = surface["semi_span"]
    chord = surface["root_chord"] + (surface["tip_chord"] - surface["root_chord"]) * y / s
    x = surface["x_root"] + y * np.tan(np.radians(surface["sweep"]))
    z = surface["z_root"] + y * np.tan(np.radians(surface["dihedral"]))
    return (x, z), chord


def lifting_surface_side(surface):
    """Outline of a horizontal lifting surface seen from the side: hull of its sections at the body and the tip."""
    sections = []
    for y, t in zip((surface["y_body"], surface["semi_span"]), surface["thickness"], strict=True):
        le, chord = lifting_surface_section(surface, y)
        sections.append(airfoil(le, chord, t, "xz"))
    return convex_hull(np.vstack(sections))


def lifting_surface_top(surface):
    """Planform of the right half of a horizontal lifting surface, from the plane of symmetry to the tip."""
    (x0, _), c0 = lifting_surface_section(surface, 0.0)
    (x1, _), c1 = lifting_surface_section(surface, surface["semi_span"])
    s = surface["semi_span"]
    return np.array([(x0, 0.0), (x1, s), (x1 + c1, s), (x0 + c0, 0.0)])


def fin_side():
    (rle, rte), (tle, tte) = FIN["root"], FIN["tip"]
    return np.array([rle, tle, tte, rte])


def fin_top():
    (rle, rte) = FIN["root"]
    return airfoil((rle[0], 0.0), rte[0] - rle[0], FIN["thickness"], "xy")


def nacelle_center_z():
    (_, z), _ = lifting_surface_section(WING, NACELLE["y"])
    return z - NACELLE["drop"]


def nacelle_side():
    (x0, x1), r, zc = NACELLE["x"], NACELLE["radius"], nacelle_center_z()
    profile = [(x0, 0.86 * r), (x0 + 0.15, 0.97 * r), (x0 + 0.6, r), (x1 - 1.2, 0.9 * r), (x1, 0.55 * r)]
    upper = [(x, zc + h) for x, h in profile]
    lower = [(x, zc - h) for x, h in reversed(profile)]
    return np.array(upper + lower)


def nacelle_top(side=1.0):
    (x0, x1), r, y = NACELLE["x"], NACELLE["radius"], side * NACELLE["y"]
    profile = [(x0, 0.86 * r), (x0 + 0.15, 0.97 * r), (x0 + 0.6, r), (x1 - 1.2, 0.9 * r), (x1, 0.55 * r)]
    return np.array([(x, y + h) for x, h in profile] + [(x, y - h) for x, h in reversed(profile)])


def pylon_side():
    zc, r = nacelle_center_z(), NACELLE["radius"]
    (xw, zw), chord = lifting_surface_section(WING, NACELLE["y"])
    return np.array([(NACELLE["x"][0] + 1.2, zc + 0.9 * r), (xw + 0.15 * chord, zw - 0.15),
                     (xw + 0.55 * chord, zw - 0.15), (NACELLE["x"][1] - 0.4, zc + 0.7 * r)])


def draw_part(ax, outline, zorder):
    ax.add_patch(Polygon(outline, closed=True, lw=LINE["reference"], ec=MUTED, fc=AIRCRAFT_FILL,
                         joinstyle="round", zorder=zorder))


def draw_aircraft_side(ax):
    draw_part(ax, fin_side(), 1)
    draw_part(ax, fuselage_side(), 2)
    draw_part(ax, lifting_surface_side(TAILPLANE), 3)
    draw_part(ax, pylon_side(), 3)
    draw_part(ax, lifting_surface_side(WING), 4)
    draw_part(ax, nacelle_side(), 5)


def draw_aircraft_top(ax):
    for side in (1.0, -1.0):
        scale = np.array([1.0, side])
        draw_part(ax, lifting_surface_top(WING) * scale, 1)
        draw_part(ax, lifting_surface_top(TAILPLANE) * scale, 1)
        draw_part(ax, nacelle_top(side), 0.5)  # below the wing, seen from above
    draw_part(ax, fuselage_top(), 2)
    draw_part(ax, fin_top(), 3)


# --- Figures -------------------------------------------------------------------------------------------

def point_on(origin, direction, length):
    return np.asarray(origin) + length * np.asarray(direction)


def angle_wedge(ax, origin, from_deg, to_deg, radius, text, text_radius):
    lo, hi = sorted((from_deg, to_deg))
    ax.add_patch(Wedge(origin, radius, lo, hi, lw=0, fc=(AERO, 0.12), zorder=3))
    ax.add_patch(Wedge(origin, radius, lo, hi, width=0.0, lw=LINE["reference"], ec=AERO, fc="none", zorder=3))
    mid = np.radians(0.5 * (lo + hi))
    ax.text(*point_on(origin, (np.cos(mid), np.sin(mid)), text_radius), text, ha="center", va="center",
            fontsize=FONT_SIZE["base"], color=INK, zorder=7)


def moment_arc(ax, origin, radius, start_deg, end_deg, text, text_offset):
    """Curved arrow around the origin from start_deg to end_deg (the direction gives the positive sense)."""
    t = np.radians(np.linspace(start_deg, end_deg, 40))
    pts = np.column_stack([origin[0] + radius * np.cos(t), origin[1] + radius * np.sin(t)])
    ax.plot(*pts[:-3].T, color=AERO, lw=LINE["secondary"], zorder=5)
    ax.annotate("", xy=pts[-1], xytext=pts[-4], zorder=5, arrowprops={
        "arrowstyle": "-|>", "lw": LINE["secondary"], "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0,
        "color": AERO})
    mid = np.radians(0.5 * (start_deg + end_deg))
    label(ax, point_on(origin, (np.cos(mid), np.sin(mid)), radius), text, text_offset, ha="left")


def axis_through_page(ax, origin, towards_viewer):
    """Axis perpendicular to the drawing plane: a circle with a dot (towards the viewer) or a cross (away)."""
    ax.plot(*origin, marker="o", ms=7.5, mfc=COLORS["surface"], mec=AERO, mew=LINE["secondary"], zorder=6)
    ax.plot(*origin, marker="." if towards_viewer else "x", ms=4.0 if towards_viewer else 4.5, color=AERO,
            mew=LINE["secondary"], zorder=7)


def axes_pair(ax, origin, cpacs_names, cpacs_offsets, aero_dirs, aero_names, aero_offsets):
    """CPACS axes (secondary ink) and aerodynamic axes (series 1) from a common origin, in the drawing plane."""
    for direction, name, offset in zip(((1.0, 0.0), (0.0, 1.0)), cpacs_names, cpacs_offsets, strict=True):
        tip = point_on(origin, direction, AXIS_LENGTH)
        arrow(ax, origin, tip, color=INK2, lw=LINE["reference"], head=6)
        label(ax, tip, name, offset, color=INK2)
    for direction, name, offset in zip(aero_dirs, aero_names, aero_offsets, strict=True):
        tip = point_on(origin, direction, AXIS_LENGTH)
        arrow(ax, origin, tip, color=AERO, lw=LINE["data"], head=8)
        label(ax, tip, name, offset)


def free_stream(ax, origin, direction):
    start = point_on(origin, direction, -(FLOW_LENGTH + 1.2))
    end = point_on(origin, direction, -1.2)
    arrow(ax, start, end, color=FLOW, lw=LINE["data"], head=8)
    ax.text(*start, r"$V_\infty$", ha="right", va="center", fontsize=FONT_SIZE["base"], color=INK, zorder=7,
            transform=ax.transData)
    return start


def reference_point(ax):
    """Moment reference point on the plane of symmetry, labelled inside the fuselage (no leader line needed)."""
    _, _, x_ref = wing_reference()
    dot(ax, (x_ref, 0.0), color=INK)
    label(ax, (x_ref, 0.0), "reference point", (-6, 0), ha="right", color=INK2)


def figure_side():
    """Side view (x-z plane, seen from the left): angle of attack, axes d and l, positive pitching moment."""
    e_d, _, e_l = aero_axes(ALPHA_FIGURE, 0.0)
    d, l = e_d[[0, 2]], e_l[[0, 2]]
    origin = np.array([-12.0, -7.5])
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.6))
        draw_aircraft_side(ax)
        reference_point(ax)
        angle_wedge(ax, origin, 0.0, ALPHA_FIGURE, 5.6, r"$\alpha$", 6.4)
        axes_pair(ax, origin, ("x", "z"), ((6, 0), (0, 7)), (d, l), ("d", "l"), ((7, 0), (-6, 4)))
        axis_through_page(ax, origin, towards_viewer=False)
        label(ax, origin, "s", (-9, 7))
        free_stream(ax, origin, d)
        moment_arc(ax, origin, 2.8, 330.0, 262.0, "cms > 0", (5, -6))
        ax.set_xlim(-23.5, 39.0)
        ax.set_ylim(-12.0, 7.6)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "aeroAxesSide.png")


def figure_top():
    """Top view (x-y plane, seen from above): sideslip angle, axes d and s, positive yawing moment."""
    e_d, e_s, _ = aero_axes(0.0, BETA_FIGURE)
    d, s = e_d[[0, 1]], e_s[[0, 1]]
    origin = np.array([-12.0, -9.0])
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 4.6))
        draw_aircraft_top(ax)
        reference_point(ax)
        angle_wedge(ax, origin, -BETA_FIGURE, 0.0, 5.6, r"$\beta$", 6.4)
        axes_pair(ax, origin, ("x", "y"), ((6, 0), (0, 7)), (d, s), ("d", "s"), ((7, -2), (6, 5)))
        axis_through_page(ax, origin, towards_viewer=True)
        label(ax, origin, "l", (-7, 12))
        free_stream(ax, origin, d)
        moment_arc(ax, origin, 2.8, 200.0, 258.0, "cml > 0", (6, -9))
        (x_tip, _), chord_tip = lifting_surface_section(WING, WING["semi_span"])
        ax.text(x_tip + chord_tip + 1.0, WING["semi_span"] - 0.6, "right wing", ha="left", va="center",
                fontsize=NOTE, color=INK2)
        ax.set_xlim(-23.5, 39.0)
        ax.set_ylim(-18.0, 18.0)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "aeroAxesTop.png")


# --- Equations -----------------------------------------------------------------------------------------

AXES_LINES = [
    r"\mathbf{e}_d = \left(\cos\alpha\,\cos\beta,\;\; -\sin\beta,\;\; \sin\alpha\,\cos\beta\right)",
    r"\mathbf{e}_s = \left(\cos\alpha\,\sin\beta,\;\; \cos\beta,\;\; \sin\alpha\,\sin\beta\right)",
    r"\mathbf{e}_l = \left(-\sin\alpha,\;\; 0,\;\; \cos\alpha\right)",
]

COEFFICIENT_LINES = [
    r"c_d = \dfrac{\mathbf{F}\cdot\mathbf{e}_d}{q_\infty\,S},\quad c_s = \dfrac{\mathbf{F}\cdot\mathbf{e}_s}"
    r"{q_\infty\,S},\quad c_l = \dfrac{\mathbf{F}\cdot\mathbf{e}_l}{q_\infty\,S}",
    r"c_{md} = \dfrac{\mathbf{M}\cdot\mathbf{e}_d}{q_\infty\,S\,l},\quad c_{ms} = \dfrac{\mathbf{M}\cdot\mathbf{e}_s}"
    r"{q_\infty\,S\,l},\quad c_{ml} = \dfrac{\mathbf{M}\cdot\mathbf{e}_l}{q_\infty\,S\,l}",
    r"q_\infty = \dfrac{1}{2}\,\rho_\infty V_\infty^2",
]


def main():
    deviation = check_aero_axes()
    print(f"Aerodynamic axes checked: largest deviation {deviation:.1e}")
    save_equation(AXES_LINES, EQUATIONS / "aeroAxes")
    save_equation(COEFFICIENT_LINES, EQUATIONS / "aeroCoefficients")
    figure_side()
    figure_top()
    write_example()
    area, mac, x_mac = wing_reference()
    print(f"Reference area {area:.2f} m^2, length (MAC) {mac:.3f} m, point x = {x_mac:.3f} m")
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the aeroPerformanceMapType documentation:\n")
    print(aero_performance_map_xml())


if __name__ == "__main__":
    main()

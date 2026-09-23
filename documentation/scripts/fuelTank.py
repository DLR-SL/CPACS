# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures, equations and example data for the documentation of fuelTanksType
and the vessel types it contains.

Run from the repository root:

    uv run documentation/scripts/fuelTank.py

The script writes

    documentation/figures/fuelTankVessels.png
    documentation/figures/vesselParameters.png
    documentation/figures/vesselDomeTypes.png
    documentation/equations/vesselTorisphericalDome.{tex,png}
    documentation/equations/vesselIsotensoidDome.{tex,png}
    examples/fuelTanks.xml

and prints the excerpts shown in the documentation together with the derived
quantities that the example has to get right (clearance between the vessels of
the rear tank, clearance to the fuselage, volumes). The schema documentation is
not written by this script; copy the printed excerpts there when the example
changes.

Geometry of a vessel given by design parameters, as defined in the documentation
of vesselType. The meridian contour lies in the local x-z plane and is revolved
about the local x-axis. It starts at the apex of the forward dome, which is the
origin of the vessel coordinate system:

    x = 0 .. h          dome, from the apex to the cylinder
    x = h .. h + L      cylinder of radius R
    x = h + L .. L + 2h  aft dome, the mirror image of the forward one

so the vessel is L + 2h long, where L is cylinderLength and h the dome height:

    ellipsoid       h = R * halfAxisFraction
    torispherical   h = R1 - sqrt((R1 - R2)^2 - c^2),  c = R - R2
    isotensoid      no closed form; h follows from integrating the contour

The isotensoid contour is the solution of the differential equation given in
the documentation. It is integrated here with a fine step, so that the figures
and the volumes show the contour the standard defines rather than a particular
numerical realisation of it.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc

from example_xml import indent, transformation_xml, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_equation, save_figure
from wing import (FUSELAGE_PROFILE_UID, FUSELAGE_SECTIONS, FUSELAGE_UID, INK, INK2, MUTED, arrow, circle_profile_xml,
                  collection, dot, fuselage_xml, label)

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EQUATIONS = DOCUMENTATION / "equations"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuelTanks.xml"

SERIES1 = COLORS["series1"]
SERIES2 = COLORS["series2"]
SERIES3 = COLORS["series3"]
LIGHT = COLORS["series1Light"]
NOTE = FONT_SIZE["annotation"]

# Colors of the parts, as recorded in developmentGuidelines.md (section "Figures and equations"):
# the vessel wall in series 1, a second vessel of the same tank in series 2, the fuselage muted.

# ------------------------------------------------------------------ example data
# A liquid hydrogen tank in the rear of the fuselage of wing.py (constant cross
# section of 3.2 m diameter up to x = 20 m): a pressure vessel with torispherical
# domes inside a vacuum jacket with ellipsoidal domes.
REAR_TANK_UID = "rearTank"
REAR_TANK_TRANSLATION = (13.6, 0.0, 0.0)
REAR_TANK_DESCRIPTION = ("Liquid hydrogen tank behind the cabin: a pressure vessel with torispherical domes "
                         "inside a vacuum jacket with ellipsoidal domes.")

# (uID suffix, cylinderRadius, cylinderLength, dome)
REAR_OUTER = ("outerVessel", 1.45, 4.0, ("ellipsoid", 0.65))
REAR_INNER = ("innerVessel", 1.30, 4.0, ("torispherical", 2.40, 0.40))

# Four filament-wound cylinders for gaseous hydrogen, low in the forward fuselage.
# One tank holds the two vessels of the right side; symmetry mirrors it to the left.
BELLY_TANK_UID = "bellyTank"
BELLY_TANK_TRANSLATION = (9.3, 0.62, -1.02)
BELLY_VESSEL = ("vessel", 0.28, 1.60, ("isotensoid", 0.05))
BELLY_SPACING = 2.05  # distance between the two vessels of the tank, along x

# A tank that follows a shape of its own, built from sections and segments like a
# fuselage: (uID suffix, x, diameter) of its circular sections.
FORWARD_TANK_UID = "forwardTank"
FORWARD_TANK_TRANSLATION = (6.2, 0.0, -0.95)
FORWARD_SECTIONS = [("front", 0.0, 0.50), ("middle", 0.9, 1.10), ("rear", 2.4, 0.80)]

# Skin layers of the pressure vessel, from the inside outwards: (uID, name, material, thickness [m])
SKIN_LAYERS = [
    ("liner", "Aluminium liner", "Aluminium2219", 0.0012),
    ("overwrap", "Carbon fibre overwrap", "CFRPQuasiIsotropic", 0.0085),
]
MATERIALS = [
    ("Aluminium2219", "Aluminium 2219-T87", 2840, 73.1e9, 27.0e9),
    ("CFRPQuasiIsotropic", "CFRP, quasi-isotropic laminate", 1570, 54.0e9, 20.6e9),
]

REAR_BURST_PRESSURE = 900000.0  # 9 bar, about three times the operating pressure of an LH2 tank
BELLY_BURST_PRESSURE = 175000000.0  # 1750 bar, a 700 bar cylinder with a safety factor of 2.5

# Fraction of the geometric volume that is really available, and of that the part
# that can be used in operation; both are written into the example as factors.
REAL_VOLUME_FACTOR = 0.97
USABLE_VOLUME_FACTOR = 0.95

# Illustrations (§33): shapes that only explain the parameters and are not written
# into the example file.
ILLUSTRATION_RADIUS = 1.0
ILLUSTRATION_LENGTH = 2.4
ILLUSTRATION_DOME = ("ellipsoid", 0.65)
ELLIPSOID_FRACTIONS = [0.5, 1.0, 1.5]
ELLIPSOID_HIGHLIGHT = 1.0
TORISPHERICAL_ILLUSTRATION = (1.6, 0.50)  # dishRadius, knuckleRadius for R = 1
ISOTENSOID_OPENINGS = [0.30]
ISOTENSOID_HIGHLIGHT = 0.30

# ------------------------------------------------------------------- equations
TORISPHERICAL_LINES = [
    r"h = R_1 - \sqrt{(R_1 - R_2)^2 - c^2}, \qquad c = R - R_2, \qquad \sin\alpha = \frac{c}{R_1 - R_2}",
]
ISOTENSOID_LINES = [
    r"\frac{dr}{dx} = -\tan\varphi, \qquad "
    r"\frac{d\varphi}{dx} = \frac{1}{r}\left(2 - \frac{r_p^{\,2}}{r^2 - r_p^{\,2}}\right)",
]


# -------------------------------------------------------------------- geometry
def ellipsoid_dome(radius, fraction, n=400):
    """Quarter of an ellipse from the apex (0, 0) to the cylinder (h, R)."""
    h = radius * fraction
    # Sampled in the parameter of the ellipse, so the points crowd where it bends most.
    t = np.linspace(0.0, math.pi / 2, n)
    return h, h - h * np.cos(t), radius * np.sin(t)


def torispherical_dome(radius, dish_radius, knuckle_radius, n=400):
    """Spherical dish at the apex, knuckle torus at the cylinder."""
    if dish_radius <= radius:
        raise ValueError("dishRadius must be larger than cylinderRadius")
    if not 0.0 < knuckle_radius < radius:
        raise ValueError("knuckleRadius must lie between 0 and cylinderRadius")
    c = radius - knuckle_radius
    h = dish_radius - math.sqrt((dish_radius - knuckle_radius) ** 2 - c**2)
    alpha = math.asin(c / (dish_radius - knuckle_radius))

    # Both arcs sampled in their own angle, in proportion to the arc length.
    n_dish = max(2, int(round(n * alpha * dish_radius / (alpha * dish_radius + (math.pi / 2 - alpha) * knuckle_radius))))
    phi = np.linspace(0.0, alpha, n_dish)
    psi = np.linspace(alpha, math.pi / 2, n - n_dish + 1)[1:]
    x = np.concatenate([dish_radius * (1 - np.cos(phi)), h - knuckle_radius * np.cos(psi)])
    r = np.concatenate([dish_radius * np.sin(phi), c + knuckle_radius * np.sin(psi)])
    return h, x, r


def isotensoid_dome(radius, polar_opening_radius, steps=20000):
    """Contour of an isotensoid dome, from the apex plane to the cylinder.

    Integrates dphi/dx = (2 - rp^2/(r^2 - rp^2)) / r and dr/dx = -tan(phi)
    from the cylinder (x = 0, r = R, phi = 0) towards the pole, and returns the
    contour turned round so that x = 0 is the plane of the polar opening.

    The equation is singular at r = sqrt(3/2) rp, where the meridian angle stops
    turning: below that radius it has no solution. The dome is therefore carried
    on from that point to the polar opening along the tangent, which closes it
    without a kink.
    """
    if not 0.0 < polar_opening_radius < radius:
        raise ValueError("polarOpeningRadius must lie between 0 and cylinderRadius")
    rp2 = polar_opening_radius**2
    if 2.0 - rp2 / (radius**2 - rp2) <= 0.0:
        raise ValueError("polarOpeningRadius too large for a dome to exist")

    d_phi = 1.0 / steps
    xs, rs = [0.0], [radius]
    phi, x, r = 0.0, 0.0, radius
    while True:
        res = 2.0 - rp2 / (r * r - rp2)
        if res <= 0.0:
            break
        dx = r * d_phi / res
        dr = dx * math.tan(phi)
        phi += d_phi
        x += dx
        r -= dr
        xs.append(x)
        rs.append(r)

    # Straight tangent from the singular radius down to the polar opening.
    slope = math.tan(phi)  # -dr/dx at the last point of the solution
    xs.append(xs[-1] + (rs[-1] - polar_opening_radius) / slope)
    rs.append(polar_opening_radius)

    h = xs[-1]
    return h, np.array([h - v for v in xs])[::-1], np.array(rs)[::-1]


def dome(radius, spec):
    """Dome contour (h, x, r) for a (kind, *parameters) specification."""
    kind, *parameters = spec
    if kind == "ellipsoid":
        return ellipsoid_dome(radius, *parameters)
    if kind == "torispherical":
        return torispherical_dome(radius, *parameters)
    if kind == "isotensoid":
        return isotensoid_dome(radius, *parameters)
    raise ValueError(f"unknown dome type {kind!r}")


def meridian(radius, length, spec):
    """Full meridian contour of a vessel, from the forward apex to the aft apex."""
    h, x_dome, r_dome = dome(radius, spec)
    x = np.concatenate([x_dome, [h + length], (length + 2 * h) - x_dome[::-1]])
    r = np.concatenate([r_dome, [radius], r_dome[::-1]])
    return h, x, r


def vessel_length(radius, length, spec):
    return length + 2 * dome(radius, spec)[0]


def vessel_volume(radius, length, spec):
    """Volume of the revolved meridian contour."""
    _, x, r = meridian(radius, length, spec)
    return float(np.trapezoid(math.pi * r**2, x))


def vessel_surface(radius, length, spec):
    """Outer surface of the revolved meridian contour, including a flat polar lid."""
    h, x, r = meridian(radius, length, spec)
    ds = np.hypot(np.diff(x), np.diff(r))
    area = float(np.sum(math.pi * (r[:-1] + r[1:]) * ds))
    if spec[0] == "isotensoid":
        area += 2 * math.pi * spec[1] ** 2  # the two polar openings are closed by flat disks
    return area


def clearance(outer, inner, offset):
    """Smallest distance between the meridian contours of two coaxial vessels.

    outer and inner are (radius, length, dome) tuples, offset the translation of
    the inner vessel along x relative to the outer one. Measured from every point
    of the inner contour to the whole outer contour.
    """
    _, xo, ro = meridian(*outer)
    _, xi, ri = meridian(*inner)
    xi = xi + offset
    points = np.column_stack([xi, ri])
    outline = np.column_stack([xo, ro])
    distances = np.hypot(points[:, None, 0] - outline[None, :, 0], points[:, None, 1] - outline[None, :, 1])
    return float(np.min(distances.min(axis=1)))


def concentric_offset(outer, inner):
    """Translation in x that centres the inner vessel inside the outer one."""
    return 0.5 * (vessel_length(*outer) - vessel_length(*inner))


REAR_INNER_OFFSET = round(concentric_offset(REAR_OUTER[1:], REAR_INNER[1:]), 4)


def placements():
    """Every vessel of the example as (name, x0, x1, y, z, radius) in fuselage coordinates.

    A parametric vessel is a body of revolution about a line parallel to the
    fuselage x-axis, so its largest radius and the offset of that line are
    enough to check the layout. A vessel built from sections is covered by the
    largest of its section diameters. Mirrored vessels are included.
    """
    out = []
    tx, ty, tz = REAR_TANK_TRANSLATION
    for suffix, radius, length, spec in (REAR_OUTER, REAR_INNER):
        offset = REAR_INNER_OFFSET if suffix == REAR_INNER[0] else 0.0
        out.append((f"{REAR_TANK_UID}_{suffix}", tx + offset, tx + offset + vessel_length(radius, length, spec),
                    ty, tz, radius))

    tx, ty, tz = BELLY_TANK_TRANSLATION
    suffix, radius, length, spec = BELLY_VESSEL
    for index in range(2):
        x0 = tx + index * BELLY_SPACING
        for side in (1, -1):  # the tank is mirrored at the x-z plane
            name = f"{BELLY_TANK_UID}_{suffix}{index + 1}" + ("" if side > 0 else " (mirrored)")
            out.append((name, x0, x0 + vessel_length(radius, length, spec), side * ty, tz, radius))

    tx, ty, tz = FORWARD_TANK_TRANSLATION
    stations = [x for _, x, _ in FORWARD_SECTIONS]
    out.append((f"{FORWARD_TANK_UID}_vessel", tx + min(stations), tx + max(stations), ty, tz,
                max(diameter for _, _, diameter in FORWARD_SECTIONS) / 2))
    return out


def check_layout():
    """No vessel leaves the fuselage, no two vessels intersect.

    The example is read as a model of how tanks are placed (§19), so the
    quantities that follow from the data are checked rather than eyeballed.
    """
    inside, apart = [], []
    for name, x0, x1, y, z, radius in placements():
        x = np.linspace(x0, x1, 200)
        margin = float(np.min(fuselage_radius(x) - (math.hypot(y, z) + radius)))
        inside.append((name, margin))
        if margin <= 0.0:
            raise ValueError(f"{name} reaches out of the fuselage by {-margin:.3f} m")

    for i, first in enumerate(placements()):
        for second in placements()[i + 1:]:
            if first[2] <= second[1] or second[2] <= first[1]:
                continue  # they do not overlap along x
            if first[0].startswith(REAR_TANK_UID) and second[0].startswith(REAR_TANK_UID):
                continue  # the pressure vessel sits inside the jacket on purpose; measured by clearance()
            gap = math.hypot(first[3] - second[3], first[4] - second[4]) - first[5] - second[5]
            apart.append((first[0], second[0], gap))
            if gap <= 0.0:
                raise ValueError(f"{first[0]} and {second[0]} intersect by {-gap:.3f} m")
    return inside, apart


def fuselage_radius(x):
    """Radius of the fuselage of wing.py at station x, linear between its sections."""
    stations = [station for _, station, _ in FUSELAGE_SECTIONS]
    radii = [diameter / 2 for _, _, diameter in FUSELAGE_SECTIONS]
    return np.interp(x, stations, radii)


# --------------------------------------------------------------------- figures
def _dimension(ax, start, end, text, offset=(0, 0), ticks=0.05, color=INK2, va="center", ha="center"):
    """Distance between two points, with end ticks perpendicular to it (§24)."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    direction = end - start
    normal = np.array([-direction[1], direction[0]])
    normal = normal / np.hypot(*normal) * ticks
    ax.plot(*np.column_stack([start, end]), color=color, lw=LINE["reference"], zorder=4)
    for point in (start, end):
        ax.plot(*np.column_stack([point - normal, point + normal]), color=color, lw=LINE["reference"], zorder=4)
    label(ax, 0.5 * (start + end), text, offset, color=INK, ha=ha, va=va)


def _hairline(ax, x, r0, r1, color=MUTED, horizontal=False):
    """Thin extension line, vertical at x from r0 to r1, or horizontal at height x."""
    if horizontal:
        ax.plot([r0, r1], [x, x], color=color, lw=LINE["reference"], zorder=2)
    else:
        ax.plot([x, x], [r0, r1], color=color, lw=LINE["reference"], zorder=2)


def _silhouette(ax, x, r, color, lw=None, alpha=1.0, fill=False, offset=0.0):
    """Meridian contour and its mirror image, about an axis at height offset."""
    for sign in (1, -1):
        ax.plot(x, offset + sign * r, color=color, lw=lw or LINE["data"], alpha=alpha, zorder=3,
                solid_capstyle="round", solid_joinstyle="round")
    if fill:
        ax.fill_between(x, offset - r, offset + r, color=color, alpha=0.08, lw=0, zorder=1)


def figure_vessel_parameters():
    """The design parameters of a vessel, and what cylinderLength = 0 gives."""
    radius, length, spec = ILLUSTRATION_RADIUS, ILLUSTRATION_LENGTH, ILLUSTRATION_DOME
    h, x, r = meridian(radius, length, spec)
    h0, x0, r0 = meridian(radius, 0.0, spec)
    total, total0 = x[-1], x0[-1]

    top = radius + 0.55        # dimension line above the body
    bottom = -radius - 0.75    # dimension line below the body

    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.7), width_ratios=[total + 3.05, total0 + 2.15])

        # ------------------------------------------------------------- panel (a)
        ax = axes[0]
        ax.set_title("(a) cylinderLength > 0")
        _silhouette(ax, x, r, SERIES1, fill=True)

        # axis of revolution, which is the x-axis of the vessel
        ax.plot([-0.55, total + 0.75], [0, 0], color=MUTED, lw=LINE["reference"], zorder=2)
        label(ax, (total + 0.75, 0.0), "x", (6, 0), ha="left", color=INK2)
        dot(ax, (0.0, 0.0))
        label(ax, (-0.28, -0.42), "origin of the vessel", (0, 0), ha="right", color=INK)
        ax.annotate("", xy=(-0.04, -0.05), xytext=(-0.3, -0.38), arrowprops=leader())

        # extension lines from the two dome junctions up to the dimension line
        for station in (h, h + length):
            _hairline(ax, station, radius, top + 0.05)
        _dimension(ax, (0.0, top), (h, top), "h", (0, 7))
        _dimension(ax, (h, top), (h + length, top), "cylinderLength", (0, 7))
        _dimension(ax, (0.0, bottom), (total, bottom), "cylinderLength + 2h", (0, -8))
        _dimension(ax, (h + 0.13 * length, 0.0), (h + 0.13 * length, radius), "cylinderRadius", (6, 0),
                   ticks=0.10, ha="left")

        # a cross section, to show that the contour is revolved about the x-axis
        ax.add_patch(Arc((h + 0.72 * length, 0.0), 0.36, 2 * radius, theta1=0, theta2=360,
                         color=LIGHT, lw=LINE["secondary"], zorder=4))

        # ------------------------------------------------------------- panel (b)
        ax = axes[1]
        ax.set_title("(b) cylinderLength = 0")
        _silhouette(ax, x0, r0, SERIES1, fill=True)
        ax.plot([-0.55, total0 + 0.75], [0, 0], color=MUTED, lw=LINE["reference"], zorder=2)
        label(ax, (total0 + 0.75, 0.0), "x", (6, 0), ha="left", color=INK2)
        dot(ax, (0.0, 0.0))

        _hairline(ax, h0, radius, top + 0.05)
        _dimension(ax, (0.0, top), (h0, top), "h", (0, 7))
        _dimension(ax, (h0, top), (total0, top), "h", (0, 7))
        label(ax, (h0, -radius), "the two domes meet here", (0, -16), color=INK)
        ax.annotate("", xy=(h0, -radius - 0.03), xytext=(h0, -radius - 0.26), arrowprops=leader())

        for ax, width in zip(axes, [total, total0], strict=True):
            ax.set_aspect("equal")
            ax.set_xlim(-1.9 if width == total else -1.0, width + 1.15)
            ax.set_ylim(bottom - 0.45, top + 0.55)
            ax.axis("off")

        fig.subplots_adjust(wspace=0.04)
        save_figure(fig, FIGURES / "vesselParameters.png")


def figure_dome_types():
    """The three dome shapes and the parameters that define them.

    Each panel shows the meridian section of the forward dome above the axis of
    revolution, all three at the same cylinder radius and the same scale.
    """
    radius = ILLUSTRATION_RADIUS
    stub = 0.30  # a piece of the cylinder, so that the junction is visible
    base = -0.30  # dimension line for the dome height, below the axis

    with figure_style():
        fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.5), width_ratios=[2.55, 2.20, 2.30])

        # ------------------------------------------------------ (a) ellipsoid
        ax = axes[0]
        ax.set_title("(a) ellipsoid")
        for fraction in ELLIPSOID_FRACTIONS:
            h, xd, rd = ellipsoid_dome(radius, fraction)
            highlight = fraction == ELLIPSOID_HIGHLIGHT
            if highlight:
                xd, rd = np.append(xd, h + stub), np.append(rd, radius)
            ax.plot(xd, rd, color=SERIES1 if highlight else MUTED,
                    lw=LINE["data"] if highlight else LINE["secondary"], zorder=4 if highlight else 3)
            label(ax, (h, radius), f"{fraction:g}", (0, 8), color=INK)
        _dimension(ax, (0.0, base), (radius * ELLIPSOID_HIGHLIGHT, base), "h = R · halfAxisFraction", (0, -8))
        label(ax, (0.5 * radius * max(ELLIPSOID_FRACTIONS), radius), "halfAxisFraction", (0, 24), color=INK2)

        # -------------------------------------------------- (b) torispherical
        ax = axes[1]
        ax.set_title("(b) torispherical")
        dish_radius, knuckle_radius = TORISPHERICAL_ILLUSTRATION
        h, xd, rd = torispherical_dome(radius, dish_radius, knuckle_radius)
        c = radius - knuckle_radius
        alpha = math.asin(c / (dish_radius - knuckle_radius))
        transition = (dish_radius * (1 - math.cos(alpha)), dish_radius * math.sin(alpha))

        # the two radii, drawn from their centres to the point where dish and knuckle meet
        ax.plot([dish_radius, transition[0]], [0.0, transition[1]], color=MUTED, lw=LINE["reference"], zorder=2)
        ax.plot([h, transition[0]], [c, transition[1]], color=MUTED, lw=LINE["reference"], zorder=2)
        ax.add_patch(Arc((dish_radius, 0.0), 0.70, 0.70, theta1=180 - math.degrees(alpha), theta2=180,
                         color=INK2, lw=LINE["reference"], zorder=3))
        ax.plot(np.append(xd, h + stub), np.append(rd, radius), color=SERIES1, lw=LINE["data"], zorder=4)
        dot(ax, transition, color=INK, size=3.5)
        dot(ax, (dish_radius, 0.0), color=INK2, size=3.0)
        dot(ax, (h, c), color=INK2, size=3.0)
        # both radii lie on one line: the centres and the transition point are collinear
        label(ax, (0.5 * (dish_radius + h), 0.5 * c), "R₁", (5, 8), color=INK)
        label(ax, (0.5 * (h + transition[0]), 0.5 * (c + transition[1])), "R₂", (3, -11), ha="left", color=INK)
        label(ax, (dish_radius - 0.44, 0.12), "α", (0, 0), color=INK)
        label(ax, (0.0, 1.22), "dish meets knuckle", (0, 0), ha="left", color=INK2)
        ax.annotate("", xy=transition, xytext=(0.32, 1.14), arrowprops=leader())
        _dimension(ax, (0.0, base), (h, base), "h", (0, -8))

        # ----------------------------------------------------- (c) isotensoid
        ax = axes[2]
        ax.set_title("(c) isotensoid")
        opening = ISOTENSOID_HIGHLIGHT
        h, xd, rd = isotensoid_dome(radius, opening)
        ax.plot(np.append(xd, h + stub), np.append(rd, radius), color=SERIES1, lw=LINE["data"], zorder=4)
        ax.plot([0.0, 0.0], [0.0, opening], color=SERIES1, lw=LINE["data"], zorder=4)
        _dimension(ax, (-0.13, 0.0), (-0.13, opening), "polarOpeningRadius", (-6, 0), ticks=0.05, ha="right")
        _dimension(ax, (0.0, base), (h, base), "h", (0, -8))

        for ax, span in zip(axes, [(-0.42, 2.13), (-0.30, 1.90), (-1.32, 0.98)], strict=True):
            ax.plot([max(span[0] + 0.07, -0.20), span[1] - 0.05], [0, 0], color=MUTED, lw=LINE["reference"], zorder=2)
            ax.set_aspect("equal")
            ax.set_xlim(*span)
            ax.set_ylim(base - 0.35, radius + 0.62)
            ax.axis("off")

        fig.subplots_adjust(wspace=0.22)
        save_figure(fig, FIGURES / "vesselDomeTypes.png")


def figure_tank_vessels():
    """Where the tanks of the example sit, and how a tank groups its vessels."""
    outer_x0 = REAR_TANK_TRANSLATION[0]
    inner_x0 = outer_x0 + REAR_INNER_OFFSET
    _, xo, ro = meridian(*REAR_OUTER[1:])
    _, xi, ri = meridian(*REAR_INNER[1:])

    with figure_style():
        fig, axes = plt.subplots(2, 1, figsize=(FULL_WIDTH, 3.5), height_ratios=[1.0, 1.55])

        # ------------------------------------- (a) the three tanks in the fuselage
        ax = axes[0]
        ax.set_title("(a) the tanks of the example in the fuselage")
        x_fuselage = np.linspace(0.0, 28.0, 600)
        for sign in (1, -1):
            ax.plot(x_fuselage, sign * fuselage_radius(x_fuselage), color=MUTED, lw=LINE["secondary"], zorder=2)

        # forward tank: a vessel built from sections, drawn through its section radii
        tx, _, tz = FORWARD_TANK_TRANSLATION
        stations = np.array([tx + x for _, x, _ in FORWARD_SECTIONS])
        radii = np.array([diameter / 2 for _, _, diameter in FORWARD_SECTIONS])
        fine = np.linspace(stations[0], stations[-1], 160)
        # the loft through three sections is smooth, so the outline is drawn as the
        # parabola through the three radii rather than as straight segments (§21)
        smooth = np.polyval(np.polyfit(stations, radii, 2), fine)
        _silhouette(ax, fine, smooth, SERIES1, offset=tz)
        for edge, edge_radius in ((stations[0], radii[0]), (stations[-1], radii[-1])):
            ax.plot([edge, edge], [tz - edge_radius, tz + edge_radius], color=SERIES1, lw=LINE["data"], zorder=3)

        # belly tank: two vessels, drawn at the height of their axis
        tx, _, tz = BELLY_TANK_TRANSLATION
        radius, length, spec = BELLY_VESSEL[1:]
        _, xb, rb = meridian(radius, length, spec)
        for index in range(2):
            _silhouette(ax, xb + tx + index * BELLY_SPACING, rb, SERIES1, offset=tz)

        # rear tank
        _silhouette(ax, xo + outer_x0, ro, SERIES1)
        _silhouette(ax, xi + inner_x0, ri, SERIES2)

        dot(ax, (0.0, 0.0), color=INK2, size=3.5)
        _dimension(ax, (0.0, 2.72), (outer_x0, 2.72), "translation of rearTank", (0, 7), ticks=0.18)
        _hairline(ax, outer_x0, 1.45, 2.78)
        label(ax, (0.30, 2.05), "origin of the fuselage", (0, 0), ha="left", color=INK2)
        ax.annotate("", xy=(0.04, 0.07), xytext=(0.26, 1.90), arrowprops=leader())

        label(ax, (FORWARD_TANK_TRANSLATION[0] + 1.2, -1.62), "forwardTank", (0, -11), color=INK)
        label(ax, (BELLY_TANK_TRANSLATION[0] + 2.0, -1.62), "bellyTank", (0, -23), color=INK)
        ax.annotate("", xy=(BELLY_TANK_TRANSLATION[0] + 2.0, -1.42), xytext=(BELLY_TANK_TRANSLATION[0] + 2.0, -2.0),
                    arrowprops=leader())
        label(ax, (outer_x0 + 2.9, 1.45), "rearTank", (0, 8), color=INK)

        ax.set_xlim(-1.5, 29.5)
        ax.set_ylim(-2.65, 3.45)

        # -------------------------------------------- (b) the rear tank in detail
        ax = axes[1]
        ax.set_title("(b) the rear tank: one tank, two vessels")
        _silhouette(ax, xo + outer_x0, ro, SERIES1, fill=True)
        _silhouette(ax, xi + inner_x0, ri, SERIES2, fill=True)
        ax.plot([outer_x0 - 0.85, outer_x0 + xo[-1] + 0.5], [0, 0], color=MUTED, lw=LINE["reference"], zorder=2)

        dot(ax, (outer_x0, 0.0))
        dot(ax, (inner_x0, 0.0), color=SERIES2)
        label(ax, (outer_x0 - 0.55, 0.95), "origin of the tank and\nof the outer vessel", (0, 0), ha="right",
              color=INK)
        ax.annotate("", xy=(outer_x0 - 0.03, 0.06), xytext=(outer_x0 - 0.62, 0.72), arrowprops=leader())
        label(ax, (outer_x0 - 0.55, -0.95), "origin of the inner vessel", (0, 0), ha="right", color=INK)
        ax.annotate("", xy=(inner_x0 - 0.02, -0.06), xytext=(outer_x0 - 0.62, -0.78), arrowprops=leader())

        label(ax, (outer_x0 + 0.62 * xo[-1], ro.max()), "outer vessel", (0, 9), color=INK)
        label(ax, (inner_x0 + 0.52 * xi[-1], 0.62), "inner vessel", (0, 0), color=INK)

        ax.set_xlim(outer_x0 - 4.3, outer_x0 + xo[-1] + 0.6)
        ax.set_ylim(-1.95, 2.05)

        for ax in axes:
            ax.set_aspect("equal")
            ax.axis("off")

        fig.subplots_adjust(hspace=0.60)
        save_figure(fig, FIGURES / "fuelTankVessels.png")


def write_equations():
    save_equation(TORISPHERICAL_LINES, EQUATIONS / "vesselTorisphericalDome")
    save_equation(ISOTENSOID_LINES, EQUATIONS / "vesselIsotensoidDome")


# ----------------------------------------------------------------------- example
def translation_xml(translation):
    """A transformation that is a pure translation; rotation and scaling stay at their defaults."""
    lines = ["<transformation>", "    <translation>"]
    lines += [f"        <{axis}>{value:g}</{axis}>" for axis, value in zip("xyz", translation, strict=True)]
    lines += ["    </translation>", "</transformation>"]
    return "\n".join(lines)


def dome_xml(spec):
    kind, *parameters = spec
    if kind == "ellipsoid":
        inner = [f"    <halfAxisFraction>{parameters[0]:g}</halfAxisFraction>"]
    elif kind == "torispherical":
        inner = [f"    <dishRadius>{parameters[0]:g}</dishRadius>",
                 f"    <knuckleRadius>{parameters[1]:g}</knuckleRadius>"]
    else:
        inner = [f"    <polarOpeningRadius>{parameters[0]:g}</polarOpeningRadius>"]
    return "\n".join(["<domeType>", f"    <{kind}>", *[indent(line, 1) for line in inner], f"    </{kind}>",
                      "</domeType>"])


def volume_xml(optimal_volume):
    return "\n".join([
        "<volume>",
        f"    <optimalVolume>{optimal_volume:.3f}</optimalVolume>",
        f"    <useableVolumeFactor>{USABLE_VOLUME_FACTOR:g}</useableVolumeFactor>",
        f"    <realVolumeFactor>{REAL_VOLUME_FACTOR:g}</realVolumeFactor>",
        "</volume>",
    ])


def skin_layers_xml():
    """The layers of the vessel wall, from the inside outwards.

    A skinLayer has neither a uID nor a name, so the order is what tells the
    layers apart; the sheet element it names carries material and thickness.
    """
    layers = []
    for uid, _, _, _ in SKIN_LAYERS:
        layers.append("\n".join([
            "<skinLayer>",
            f"    <standardSheetElementUID>{uid}Sheet</standardSheetElementUID>",
            "</skinLayer>",
        ]))
    return collection("skinLayers", layers)


def parametric_vessel_xml(tank_uid, vessel, translation, burst_pressure=None, structure=None):
    suffix, radius, length, spec = vessel
    readable = re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", suffix).replace("  ", " ")
    readable = readable[0].upper() + readable[1:].lower() if readable else readable
    lines = [f'<vessel uID="{tank_uid}_{suffix}">', f"    <name>{readable}</name>"]
    lines.append(indent(translation_xml(translation), 1))
    lines += [
        f"    <cylinderRadius>{radius:g}</cylinderRadius>",
        f"    <cylinderLength>{length:g}</cylinderLength>",
        indent(dome_xml(spec), 1),
    ]
    if structure:
        lines.append(indent(collection("structure", [structure]), 1))
    if burst_pressure is not None:
        lines.append(indent(volume_xml(vessel_volume(radius, length, spec)), 1))
        lines.append(f"    <burstPressure>{burst_pressure:.0f}</burstPressure>")
    lines.append("</vessel>")
    return "\n".join(lines)


def segment_vessel_xml(tank_uid, suffix):
    """A vessel built from sections and segments, like a fuselage."""
    sections, segments = [], []
    for name, x, diameter in FORWARD_SECTIONS:
        sections.append("\n".join([
            f'<section uID="{tank_uid}_{name}">', f"    <name>{name.capitalize()} section</name>",
            indent(translation_xml((x, 0.0, 0.0)), 1),
            "    <elements>", f'        <element uID="{tank_uid}_{name}_element">',
            f"            <name>{name.capitalize()} element</name>",
            f"            <profileUID>{FUSELAGE_PROFILE_UID}</profileUID>",
            indent(transformation_xml(scaling=(1.0, diameter, diameter)), 3),
            "        </element>", "    </elements>", "</section>",
        ]))
    for index, (front, rear) in enumerate(zip(FORWARD_SECTIONS[:-1], FORWARD_SECTIONS[1:]), start=1):
        segments.append("\n".join([
            f'<segment uID="{tank_uid}_segment{index}">', f"    <name>Segment {index}</name>",
            f"    <fromElementUID>{tank_uid}_{front[0]}_element</fromElementUID>",
            f"    <toElementUID>{tank_uid}_{rear[0]}_element</toElementUID>", "</segment>",
        ]))
    return "\n".join([
        f'<vessel uID="{tank_uid}_{suffix}">', "    <name>Vessel</name>",
        indent(translation_xml((0.0, 0.0, 0.0)), 1),
        indent(collection("sections", sections), 1),
        indent(collection("segments", segments), 1),
        "</vessel>",
    ])


def rear_tank_xml():
    structure = skin_layers_xml()
    vessels = [
        parametric_vessel_xml(REAR_TANK_UID, REAR_OUTER, (0.0, 0.0, 0.0)),
        parametric_vessel_xml(REAR_TANK_UID, REAR_INNER, (REAR_INNER_OFFSET, 0.0, 0.0), REAR_BURST_PRESSURE,
                              structure=structure),
    ]
    return "\n".join([
        f'<fuelTank uID="{REAR_TANK_UID}">', "    <name>Rear tank</name>",
        f"    <description>{REAR_TANK_DESCRIPTION}</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(translation_xml(REAR_TANK_TRANSLATION), 1),
        indent(collection("vessels", vessels), 1),
        "</fuelTank>",
    ])


def belly_tank_xml():
    suffix, radius, length, spec = BELLY_VESSEL
    vessels = [
        parametric_vessel_xml(BELLY_TANK_UID, (f"{suffix}{index + 1}", radius, length, spec),
                              (index * BELLY_SPACING, 0.0, 0.0), BELLY_BURST_PRESSURE)
        for index in range(2)
    ]
    return "\n".join([
        f'<fuelTank uID="{BELLY_TANK_UID}" symmetry="x-z-plane">', "    <name>Belly tank</name>",
        "    <description>Two filament-wound cylinders for gaseous hydrogen below the cabin floor, mirrored to "
        "the left-hand side by the symmetry attribute.</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(translation_xml(BELLY_TANK_TRANSLATION), 1),
        indent(collection("vessels", vessels), 1),
        "</fuelTank>",
    ])


def forward_tank_xml():
    return "\n".join([
        f'<fuelTank uID="{FORWARD_TANK_UID}">', "    <name>Forward tank</name>",
        "    <description>A tank whose vessel is built from sections and segments instead of design parameters, "
        "so that its cross sections and their spacing can be chosen freely.</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(translation_xml(FORWARD_TANK_TRANSLATION), 1),
        indent(collection("vessels", [segment_vessel_xml(FORWARD_TANK_UID, "vessel")]), 1),
        "</fuelTank>",
    ])


def sheet_elements_xml():
    """One sheet element per skin layer; the type carries no name, only a uID."""
    elements = []
    for uid, _, material, thickness in SKIN_LAYERS:
        elements.append("\n".join([
            f'<sheetBasedStructuralElement uID="{uid}Sheet">',
            "    <materialDefinition>", f"        <materialUID>{material}</materialUID>",
            f"        <thickness>{thickness:g}</thickness>", "    </materialDefinition>",
            "</sheetBasedStructuralElement>",
        ]))
    return collection("sheetBasedStructuralElements", elements)


def materials_xml():
    materials = []
    for uid, name, rho, e_modulus, g_modulus in MATERIALS:
        materials.append("\n".join([
            f'<material uID="{uid}">', f"    <name>{name}</name>", f"    <rho>{rho:g}</rho>",
            "    <isotropicProperties>", f"        <E>{e_modulus:g}</E>", f"        <G>{g_modulus:g}</G>",
            "    </isotropicProperties>", "</material>",
        ]))
    return "\n".join(materials)


def write_example():
    tanks = "\n".join([rear_tank_xml(), belly_tank_xml(), forward_tank_xml()])
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Fuel tanks",
        description="Hydrogen tanks in a fuselage: vessels given by design parameters with the three dome types, "
                    "and a vessel built from sections and segments.",
        model_uid="TankAircraft",
        model_name="Fuel tank example",
        components_tag="fuselages",
        components=fuselage_xml(),
        extra_components=[("fuelTanks", tanks)],
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_vehicles=[("structuralElements", sheet_elements_xml()), ("materials", materials_xml())],
    )


# -------------------------------------------------------------------- excerpts
# Every excerpt below is a literal excerpt of examples/fuelTanks.xml, shortened
# with "..." where the detail does not matter to the point being made (§19).
def excerpt_tank_xml():
    """The rear tank: how a tank is placed and what it holds."""
    lines = [
        f'<fuelTank uID="{REAR_TANK_UID}">',
        "    <name>Rear tank</name>",
        f"    <description>{REAR_TANK_DESCRIPTION}</description>",
        f"    <parentUID>{FUSELAGE_UID}</parentUID>",
        indent(translation_xml(REAR_TANK_TRANSLATION), 1),
        "    <vessels>",
        f'        <vessel uID="{REAR_TANK_UID}_{REAR_OUTER[0]}">',
        "            <name>Outer vessel</name>",
        "            ...",
        "        </vessel>",
        f'        <vessel uID="{REAR_TANK_UID}_{REAR_INNER[0]}">',
        "            <name>Inner vessel</name>",
        "            ...",
        "        </vessel>",
        "    </vessels>",
        "</fuelTank>",
    ]
    return "\n".join(lines)


def excerpt_parametric_vessel_xml():
    """The outer vessel of the rear tank, given by design parameters."""
    suffix, radius, length, spec = REAR_OUTER
    return "\n".join([
        f'<vessel uID="{REAR_TANK_UID}_{suffix}">',
        "    <name>Outer vessel</name>",
        indent(translation_xml((0.0, 0.0, 0.0)), 1),
        f"    <cylinderRadius>{radius:g}</cylinderRadius>",
        f"    <cylinderLength>{length:g}</cylinderLength>",
        indent(dome_xml(spec), 1),
        "</vessel>",
    ])


def excerpt_segment_vessel_xml():
    """The vessel of the forward tank, built from sections and segments."""
    return "\n".join([
        f'<vessel uID="{FORWARD_TANK_UID}_vessel">',
        "    <name>Vessel</name>",
        indent(translation_xml((0.0, 0.0, 0.0)), 1),
        "    <sections>",
        f'        <section uID="{FORWARD_TANK_UID}_{FORWARD_SECTIONS[0][0]}">', "            ...",
        "        </section>",
        "        ...",
        "    </sections>",
        "    <segments>",
        f'        <segment uID="{FORWARD_TANK_UID}_segment1">',
        f"            <fromElementUID>{FORWARD_TANK_UID}_{FORWARD_SECTIONS[0][0]}_element</fromElementUID>",
        f"            <toElementUID>{FORWARD_TANK_UID}_{FORWARD_SECTIONS[1][0]}_element</toElementUID>",
        "        </segment>",
        "        ...",
        "    </segments>",
        "</vessel>",
    ])


def excerpt_dome_xml(uid, spec):
    """The domeType element of one of the vessels of the example."""
    return "\n".join([f'<vessel uID="{uid}">', "    ...", indent(dome_xml(spec), 1), "    ...", "</vessel>"])


def excerpt_skin_layers_xml():
    return skin_layers_xml()


def excerpt_volume_xml():
    radius, length, spec = REAR_INNER[1:]
    return volume_xml(vessel_volume(radius, length, spec))


# -------------------------------------------------------------------- main
def report():
    """Quantities that follow from the example data and have to come out right."""
    outer, inner = REAR_OUTER[1:], REAR_INNER[1:]
    print("Rear tank")
    for name, (radius, length, spec) in [("outer vessel", outer), ("inner vessel", inner)]:
        h = dome(radius, spec)[0]
        print(f"  {name:13s} R = {radius:.2f} m, L = {length:.2f} m, h = {h:.4f} m, "
              f"total length {vessel_length(radius, length, spec):.4f} m, "
              f"V = {vessel_volume(radius, length, spec):.3f} m^3, A = {vessel_surface(radius, length, spec):.3f} m^2")
    print(f"  inner vessel centred in the outer one at x = {REAR_INNER_OFFSET:g} m")
    print(f"  clearance between the two vessels: {clearance(outer, inner, REAR_INNER_OFFSET):.4f} m")

    x0 = REAR_TANK_TRANSLATION[0]
    _, x, r = meridian(*outer)
    margin = float(np.min(fuselage_radius(x + x0) - r))
    print(f"  outer vessel from x = {x0 + x[0]:.2f} m to x = {x0 + x[-1]:.2f} m, "
          f"smallest clearance to the fuselage {margin:.4f} m")

    radius, length, spec = BELLY_VESSEL[1:]
    h = dome(radius, spec)[0]
    print("Belly tank")
    print(f"  vessel        R = {radius:.2f} m, L = {length:.2f} m, h = {h:.4f} m, "
          f"total length {vessel_length(radius, length, spec):.4f} m, "
          f"V = {vessel_volume(radius, length, spec):.4f} m^3")
    y, z = BELLY_TANK_TRANSLATION[1:]
    x_belly = np.linspace(BELLY_TANK_TRANSLATION[0], BELLY_TANK_TRANSLATION[0] + BELLY_SPACING
                          + vessel_length(radius, length, spec), 200)
    reach = math.hypot(y, z) + radius
    print(f"  vessels reach {reach:.4f} m from the fuselage axis, "
          f"smallest fuselage radius over their length {float(np.min(fuselage_radius(x_belly))):.4f} m")

    print("Forward tank")
    radius = max(diameter for _, _, diameter in FORWARD_SECTIONS) / 2
    x_forward = FORWARD_TANK_TRANSLATION[0] + np.array([x for _, x, _ in FORWARD_SECTIONS])
    print(f"  sections from x = {x_forward[0]:.2f} m to x = {x_forward[-1]:.2f} m, largest radius {radius:.2f} m")

    inside, apart = check_layout()
    print("Layout (all checked, the script stops if one of them fails)")
    for name, margin in inside:
        print(f"  {name:34s} clearance to the fuselage {margin:7.4f} m")
    for first, second, gap in apart:
        print(f"  {first:20s} to {second:22s} {gap:7.4f} m")


def main():
    write_equations()
    figure_vessel_parameters()
    figure_dome_types()
    figure_tank_vessels()
    write_example()

    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in [
        ("fuelTankType", excerpt_tank_xml()),
        ("vesselType, vessel given by design parameters", excerpt_parametric_vessel_xml()),
        ("vesselType, vessel built from sections and segments", excerpt_segment_vessel_xml()),
        ("ellipsoidDomeType", excerpt_dome_xml(f"{REAR_TANK_UID}_{REAR_OUTER[0]}", REAR_OUTER[3])),
        ("torisphericalDomeType", excerpt_dome_xml(f"{REAR_TANK_UID}_{REAR_INNER[0]}", REAR_INNER[3])),
        ("isotensoidDomeType", excerpt_dome_xml(f"{BELLY_TANK_UID}_{BELLY_VESSEL[0]}1", BELLY_VESSEL[3])),
        ("vesselSkinLayersType", excerpt_skin_layers_xml()),
        ("fuelTankVolumeType", excerpt_volume_xml()),
    ]:
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure and example data for the documentation of the fuselage cut-outs
(fuselageCutOutsType, fuselageCutOutType). The cut-outs are placed in the
fuselage of the other examples, imported from fuselage.py.

Run from the repository root:

    uv run documentation/scripts/fuselageCutOut.py

The script writes

    documentation/figures/fuselageCutOut.png
    examples/fuselageCutOuts.xml

and prints the excerpt shown in the documentation together with the derived
quantities the example has to get right: the centre of each cut-out, and that
its rectangle lies on the fuselage. The schema documentation is not written by
this script; copy the printed excerpt there when the example changes.

Definition shown (as in the documentation), all in the fuselage coordinate system:
the reference point r = (positionX, referenceY, referenceZ) and the direction
d = (0, -sin a, cos a), the z-axis rotated about the x-axis by the referenceAngle a,
define a ray r + s d, s > 0. The centre of the cut-out is the point where the ray
pierces the fuselage surface. At the centre, the cut-out coordinate system has its
x-axis along the orientationVector, pointing out of the fuselage, its y-axis along
the alignmentVector, projected onto the plane normal to the x-axis, and its z-axis
x cross y. The cut-out is the rectangle deltaY wide along y and deltaZ high along z,
with corners rounded by filletRadius, extruded along x; it removes the fuselage
surface around the centre.

The fuselage cross section at a station is an ellipse (fuselage.py), so the centre
is found in closed form.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon

from example_xml import indent, write_cpacs_file
from figure_style import (COLORS, FONT_SIZE, FULL_WIDTH, LINE, arrow, axes_cross, dot, figure_style, label,
                          save_figure)
from fuselage import CYLINDER, DIAMETER, FUSELAGE_UID, LOFT, circle_profile_xml, fuselage_xml

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "fuselageCutOuts.xml"

POSITION = COLORS["series1"]
CUTOUT = COLORS["series2"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# ------------------------------------------------------------------ example data
FLOOR_Z = -0.55  # cabin floor of the example fuselage; the passenger doors have their sill at the floor
LEFT, RIGHT = (0.0, -1.0, 0.0), (0.0, 1.0, 0.0)
ALONG_X = (1.0, 0.0, 0.0)


def _normal_right(z):
    """Outward normal of the cylindrical part at the height z on the side y > 0, rounded to four decimals."""
    y = np.sqrt((DIAMETER / 2) ** 2 - z ** 2)
    n = np.array([0.0, y, z]) / (DIAMETER / 2)
    return tuple(round(float(v), 4) for v in n)


# Cut-outs of a short-range airliner: (uID suffix, name, cutoutType, positionX, referenceY, referenceZ,
# referenceAngle, orientationVector, alignmentVector, deltaY = width, deltaZ = height, filletRadius).
# Passenger doors on the left side (Type I, 0.81 m x 1.85 m) with the sill at the floor, one over-wing emergency exit
# on each side (Type III, 0.51 m x 0.92 m) above the wing root (x = 10 to 15 m), and the door of the forward cargo
# hold on the right side of the lower lobe, turned with the surface.
CUTOUTS = [
    ("paxDoorL1", "Forward passenger door", "paxDoor", 6.2, 0.0, FLOOR_Z + 1.85 / 2, 90.0, LEFT, ALONG_X,
     0.81, 1.85, 0.2),
    ("emergencyExitL", "Over-wing exit left", "emergencyDoor", 12.5, 0.0, 0.35, 90.0, LEFT, ALONG_X,
     0.51, 0.92, 0.15),
    ("emergencyExitR", "Over-wing exit right", "emergencyDoor", 12.5, 0.0, 0.35, -90.0, RIGHT, ALONG_X,
     0.51, 0.92, 0.15),
    ("paxDoorL2", "Aft passenger door", "paxDoor", 18.3, 0.0, FLOOR_Z + 1.85 / 2, 90.0, LEFT, ALONG_X,
     0.81, 1.85, 0.2),
    ("cargoDoorFwd", "Forward cargo door", "cargoDoor", 8.0, 0.0, -1.0, -90.0, _normal_right(-1.0), ALONG_X,
     1.0, 0.7, 0.15),
]
FIELDS = ("uid", "name", "kind", "x", "ref_y", "ref_z", "angle", "orientation", "alignment", "width", "height",
          "fillet")
EXCERPT_CUTOUT = CUTOUTS[0]


def cutout(row):
    return dict(zip(FIELDS, row, strict=True))


# ------------------------------------------------------------------ geometry
def ray_direction(angle):
    """The z-axis rotated about the x-axis by the angle [deg]: 0 up, 90 towards -y."""
    a = np.radians(angle)
    return np.array([0.0, -np.sin(a), np.cos(a)])


def centre(c, loft=LOFT):
    """Point where the ray from the reference point pierces the surface, and the ray parameter s."""
    width, height, zc = loft.station(c["x"])
    d = ray_direction(c["angle"])
    p = np.array([c["ref_y"], c["ref_z"] - zc])  # relative to the centre of the cross section
    a2, b2 = (width / 2) ** 2, (height / 2) ** 2
    qa = d[1] ** 2 / a2 + d[2] ** 2 / b2
    qb = 2.0 * (p[0] * d[1] / a2 + p[1] * d[2] / b2)
    qc = p[0] ** 2 / a2 + p[1] ** 2 / b2 - 1.0
    assert qc < 0.0, f"reference point of {c['uid']} is not inside the fuselage"
    s = (-qb + np.sqrt(qb * qb - 4.0 * qa * qc)) / (2.0 * qa)
    return np.array([c["x"], c["ref_y"], c["ref_z"]]) + s * d, s


def frame(c):
    """Axes x, y, z of the cut-out coordinate system."""
    x = np.asarray(c["orientation"], dtype=float)
    x /= np.linalg.norm(x)
    a = np.asarray(c["alignment"], dtype=float)
    y = a - (a @ x) * x
    y /= np.linalg.norm(y)
    return x, y, np.cross(x, y)


def rounded_rectangle(width, height, radius, n=24):
    """Outline of the cut-out in its y-z plane, counter-clockwise, corners rounded by the radius."""
    corners = [(width / 2 - radius, height / 2 - radius, 0.0), (-width / 2 + radius, height / 2 - radius, 90.0),
               (-width / 2 + radius, -height / 2 + radius, 180.0), (width / 2 - radius, -height / 2 + radius, 270.0)]
    points = []
    for cy, cz, start in corners:
        t = np.radians(np.linspace(start, start + 90.0, n))
        points += list(zip(cy + radius * np.cos(t), cz + radius * np.sin(t)))
    return np.array(points)


def on_surface(point, direction, loft=LOFT):
    """Whether the line through the point along the direction meets the fuselage surface, i.e. the rectangle point
    lies over the fuselage, and the distance along the line to the surface."""
    width, height, zc = loft.station(point[0])
    p, d = np.array([point[1], point[2] - zc]), np.asarray(direction[1:])
    a2, b2 = (width / 2) ** 2, (height / 2) ** 2
    qa = d[0] ** 2 / a2 + d[1] ** 2 / b2
    qb = 2.0 * (p[0] * d[0] / a2 + p[1] * d[1] / b2)
    qc = p[0] ** 2 / a2 + p[1] ** 2 / b2 - 1.0
    disc = qb * qb - 4.0 * qa * qc
    if qa == 0.0 or disc < 0.0:
        return False, np.inf
    roots = [(-qb - np.sqrt(disc)) / (2.0 * qa), (-qb + np.sqrt(disc)) / (2.0 * qa)]
    return True, min(roots, key=abs)


# --------------------------------------------------------------------- figure
def figure_cutout():
    """(a) The section at positionX, seen from behind: reference point, angle, ray, centre and the cut-out.
    (b) The cut-out seen from outside along the orientationVector: its coordinate system, width, height, radius."""
    c = cutout(EXCERPT_CUTOUT)
    point, _ = centre(c)
    width, height = c["width"], c["height"]
    radius = DIAMETER / 2
    with figure_style():
        fig, (sec, side) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.5),
                                        gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.05})

        # (a) section at positionX, seen from behind: y to the right, z up, so that -y (the left side) is on the left
        t = np.linspace(0.0, 2.0 * np.pi, 721)
        sec.add_patch(Polygon(np.column_stack([radius * np.sin(t), radius * np.cos(t)]), closed=True,
                              facecolor=to_rgba(MUTED, 0.06), edgecolor=MUTED, lw=LINE["reference"], zorder=1))
        ref = np.array([c["ref_y"], c["ref_z"]])
        hit = point[1:]
        # the cut-out in the section plane: the strip of the extruded rectangle, and the arc of the contour it removes
        _, _, ez = frame(c)
        lo, hi = hit - 0.5 * height * ez[1:], hit + 0.5 * height * ez[1:]
        outward = np.asarray(c["orientation"], dtype=float)[1:]
        strip = np.array([lo - 0.3 * outward, lo + 0.25 * outward, hi + 0.25 * outward, hi - 0.3 * outward])
        sec.add_patch(Polygon(strip, closed=True, facecolor=CUTOUT, alpha=0.12, edgecolor="none", zorder=2))
        z_arc = np.linspace(lo[1], hi[1], 200)
        sec.plot(-np.sqrt(radius ** 2 - z_arc ** 2), z_arc, color=CUTOUT, lw=3.0, solid_capstyle="butt", zorder=3)
        # angle from the z direction to the ray, as a pale area in the section plane
        wedge = np.radians(np.linspace(0.0, c["angle"], 60))
        r_angle = 0.55
        sec.add_patch(Polygon(np.vstack([ref, ref + r_angle * np.column_stack([-np.sin(wedge), np.cos(wedge)])]),
                              closed=True, facecolor=POSITION, alpha=0.14, edgecolor="none", zorder=2))
        # the z direction at the reference point, from which the angle is measured
        sec.plot(*np.array([ref, ref + (0.0, 0.8)]).T, color=MUTED, lw=LINE["reference"], zorder=3)
        label(sec, ref + (0.0, 0.55), f"referenceAngle {c['angle']:g}°", (6, 0), ha="left")
        # the ray from the reference point to the centre, and the orientationVector beyond it
        arrow(sec, ref, hit, color=POSITION, lw=LINE["data"], head=8)
        arrow(sec, hit, hit + 1.0 * outward, color=CUTOUT, lw=LINE["data"], head=8)
        label(sec, hit + 1.0 * outward, "orientationVector", (0, 6), va="bottom")
        dot(sec, ref)
        label(sec, ref, f"reference point\n(referenceY, referenceZ)\n= ({c['ref_y']:g}, {c['ref_z']:g})", (0, -8),
              va="top")
        dot(sec, hit, color=CUTOUT)
        label(sec, hit, "centre", (8, 5), ha="left", va="bottom")
        label(sec, hi, "cut-out", (0, 4), va="bottom")
        axes_cross(sec, (1.35, -1.95), [(1, 0), (0, 1)], ["y", "z"], 0.45, [(6, 0), (0, 7)])
        sec.set_xlim(-3.2, 2.0)
        sec.set_ylim(-2.1, 2.2)
        sec.set_aspect("equal")
        sec.axis("off")
        sec.set_title(f"(a) Section at positionX = {c['x']:g} m, seen from behind", fontsize=FONT_SIZE["base"])

        # (b) seen from outside along the orientationVector, i.e. the left side of the fuselage: x to the right, z up
        x0 = c["x"]
        for z in (radius, -radius):
            side.plot([x0 - 1.35, x0 + 1.35], [z, z], color=MUTED, lw=LINE["reference"], zorder=1)
        side.fill_between([x0 - 1.35, x0 + 1.35], -radius, radius, color=MUTED, alpha=0.06, lw=0, zorder=0)
        outline = rounded_rectangle(width, height, c["fillet"]) + (x0, hit[1])
        side.add_patch(Polygon(outline, closed=True, facecolor=to_rgba(CUTOUT, 0.12), edgecolor=CUTOUT,
                               lw=LINE["data"], joinstyle="round", zorder=3))
        dot(side, (x0, hit[1]), color=CUTOUT)
        # cut-out coordinate system at the centre: y along the alignmentVector, z up
        for direction, name, offset in (((0.5, 0.0), "y  (alignmentVector)", (4, -8)), ((0.0, 0.5), "z", (0, 7))):
            tip = np.array([x0, hit[1]]) + direction
            arrow(side, (x0, hit[1]), tip, color=INK, lw=LINE["secondary"], head=6)
            label(side, tip, name, offset, ha="left" if direction[0] else "center", color=INK2)
        # width below and height beside the cut-out
        y_dim = hit[1] - height / 2 - 0.22
        side.plot([x0 - width / 2, x0 + width / 2], [y_dim, y_dim], color=MUTED, lw=LINE["reference"])
        for xx in (x0 - width / 2, x0 + width / 2):
            side.plot([xx, xx], [y_dim - 0.07, y_dim + 0.07], color=MUTED, lw=LINE["reference"])
        label(side, (x0, y_dim), f"deltaY {width:g}", (0, -4), va="top", color=INK2)
        x_dim = x0 - width / 2 - 0.22
        side.plot([x_dim, x_dim], [hit[1] - height / 2, hit[1] + height / 2], color=MUTED, lw=LINE["reference"])
        for zz in (hit[1] - height / 2, hit[1] + height / 2):
            side.plot([x_dim - 0.07, x_dim + 0.07], [zz, zz], color=MUTED, lw=LINE["reference"])
        label(side, (x_dim, hit[1]), f"deltaZ\n{height:g}", (-4, 0), ha="right", color=INK2)
        # corner radius at the upper right corner, with a leader through free space
        corner = np.array([x0 + width / 2 - c["fillet"], hit[1] + height / 2 - c["fillet"]])
        tip = corner + c["fillet"] * np.array([np.cos(np.pi / 4), np.sin(np.pi / 4)])
        side.annotate(f"filletRadius {c['fillet']:g}", xy=tip, xytext=(tip[0] + 0.3, tip[1] + 0.12),
                      textcoords="data", ha="left", va="center", fontsize=NOTE, color=INK, zorder=7,
                      arrowprops={"arrowstyle": "-", "color": MUTED, "lw": LINE["reference"], "shrinkA": 2,
                                  "shrinkB": 1, "relpos": (0.0, 0.5)})
        axes_cross(side, (x0 + 0.75, -1.95), [(1, 0), (0, 1)], ["x", "z"], 0.45, [(6, 0), (0, 7)])
        side.set_xlim(x0 - 1.6, x0 + 1.6)
        side.set_ylim(-2.1, 2.2)
        side.set_aspect("equal")
        side.axis("off")
        side.set_title("(b) Seen from outside, from the left", fontsize=FONT_SIZE["base"])
        save_figure(fig, FIGURES / "fuselageCutOut.png")


# --------------------------------------------------------------------- example
def _point(tag, values):
    return "\n".join([f"<{tag}>", *(f"    <{axis}>{v:g}</{axis}>" for axis, v in zip("xyz", values, strict=True)),
                      f"</{tag}>"])


def cutout_xml(row):
    c = cutout(row)
    return "\n".join([
        f'<element uID="{FUSELAGE_UID}_{c["uid"]}">', f"    <name>{c['name']}</name>",
        f"    <positionX>{c['x']:g}</positionX>", f"    <referenceY>{c['ref_y']:g}</referenceY>",
        f"    <referenceZ>{c['ref_z']:g}</referenceZ>", f"    <referenceAngle>{c['angle']:g}</referenceAngle>",
        indent(_point("orientationVector", c["orientation"]), 1), indent(_point("alignmentVector", c["alignment"]), 1),
        f"    <deltaY>{c['width']:g}</deltaY>", f"    <deltaZ>{c['height']:g}</deltaZ>",
        f"    <filletRadius>{c['fillet']:g}</filletRadius>", f"    <cutoutType>{c['kind']}</cutoutType>",
        "</element>",
    ])


def cutouts_xml(rows=CUTOUTS):
    return "\n".join(["<cutOuts>", *(indent(cutout_xml(r), 1) for r in rows), "</cutOuts>"])


def fuselage_with_cutouts_xml():
    body = fuselage_xml()
    assert body.endswith("\n</fuselage>")
    return body[: -len("</fuselage>")] + indent(cutouts_xml(), 1) + "\n</fuselage>"


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Fuselage cut-outs",
        description="Doors and emergency exits of a short-range airliner fuselage as cut-outs.",
        model_uid="FuselageCutOutsAircraft",
        model_name="Fuselage cut-outs example",
        components_tag="fuselages",
        components=fuselage_with_cutouts_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
    )


def excerpt_xml():
    return cutouts_xml([EXCERPT_CUTOUT]).replace("</cutOuts>", "    ...\n</cutOuts>")


def report():
    """Quantities that follow from the example data and have to come out right (§19)."""
    for row in CUTOUTS:
        c = cutout(row)
        point, s = centre(c)
        ex, ey, ez = frame(c)
        # the rectangle has to lie over the fuselage: every point of its outline meets the surface along x
        outline = rounded_rectangle(c["width"], c["height"], c["fillet"])
        gaps = []
        for v, w in outline:
            q = point + v * ey + w * ez
            hits, gap = on_surface(q, ex)
            assert hits, f"outline of {c['uid']} leaves the fuselage"
            gaps.append(gap)
        inside = CYLINDER[0] <= c["x"] - c["width"] / 2 and c["x"] + c["width"] / 2 <= CYLINDER[1]
        print(f"{c['uid']:15s} centre ({point[0]:.3f}, {point[1]:.4f}, {point[2]:.4f}), ray length {s:.4f} m, "
              f"x-axis {np.round(ex, 4)}, z-axis {np.round(ez, 4)}, outline {min(gaps):+.3f}..{max(gaps):+.3f} m "
              f"from the surface along x, {'within' if inside else 'OUTSIDE'} the constant cross section")
        if c["kind"] == "paxDoor":
            print(f"{'':15s} sill at z = {point[2] - c['height'] / 2:.3f} m, floor at {FLOOR_Z:g} m")
    # neighbouring cut-outs on the same side must not overlap
    rows = sorted((cutout(r) for r in CUTOUTS), key=lambda c: c["x"])
    for a, b in zip(rows, rows[1:]):
        same_side = np.sign(ray_direction(a["angle"])[1]) == np.sign(ray_direction(b["angle"])[1])
        if same_side:
            gap = (b["x"] - b["width"] / 2) - (a["x"] + a["width"] / 2)
            assert gap > 0.3, (a["uid"], b["uid"], gap)


def main():
    figure_cutout()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the fuselageCutOutType documentation:\n")
    print(excerpt_xml())


if __name__ == "__main__":
    main()

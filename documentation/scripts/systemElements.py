# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the geometry of system elements: the primitives
cuboidType, cylinderType, coneType, ellipsoidType and torusType, and an element
composed of several of them.

Run from the repository root:

    uv run documentation/scripts/systemElements.py

The script writes

    documentation/figures/systemElementCuboid.png
    documentation/figures/systemElementCylinderCone.png
    documentation/figures/systemElementEllipsoid.png
    documentation/figures/systemElementTorus.png
    examples/simpleSystems.xml

and prints the excerpts shown in the documentation together with the volumes
and centroids that follow from the example data. The schema documentation is
not written by this script; copy the printed excerpts there when the example
changes.

The example file is a catalogue of shapes: one generic element per variant of
a primitive, each installed once as a component, in rows of the same primitive
along x. It adds an element composed of several primitives (a hydraulic
accumulator), a multi-segment shape and a component without position.

The figures draw each primitive in its own coordinate system, as the
documentation defines it, in an oblique view. The solids are shaded meshes drawn
from back to front; edges and outlines are drawn where no nearer face covers
them.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.patches import Polygon

from example_xml import indent, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, leader, save_figure
from wing import FUSELAGE_PROFILE_UID, arrow, circle_profile_xml, collection, dot, label

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "simpleSystems.xml"

SERIES1 = COLORS["series1"]
LIGHT = COLORS["series1Light"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]
WASH = 0.08

# ------------------------------------------------------------------ example data
# Every shape of the catalogue: (uID suffix, name, primitive, parameters). The
# parameters are the elements of the primitive in schema order; None is omitted.
DENSITY = 600.0  # kg/m^3, a typical mean density of a box of equipment

CUBOIDS = [
    ("box", "Box", dict(lengthX=1.2, depthY=0.8, heightZ=0.6)),
    ("taperedBox", "Tapered box", dict(lengthX=1.2, depthY=0.8, heightZ=0.6, upperFaceXmin=0.3, upperFaceXmax=1.0,
                                       upperFaceYmin=0.15, upperFaceYmax=0.65)),
    ("wedge", "Wedge", dict(lengthX=1.2, depthY=0.8, heightZ=0.6, upperFaceXmin=0.6, upperFaceXmax=0.6,
                            upperFaceYmin=0.0, upperFaceYmax=0.8)),
    ("pyramid", "Pyramid", dict(lengthX=1.2, depthY=0.8, heightZ=0.6, upperFaceXmin=0.6, upperFaceXmax=0.6,
                                upperFaceYmin=0.4, upperFaceYmax=0.4)),
]
CYLINDERS = [("cylinder", "Cylinder", dict(radius=0.3, height=0.8))]
CONES = [
    ("frustum", "Truncated cone", dict(lowerRadius=0.4, upperRadius=0.2, height=0.6)),
    ("cone", "Cone", dict(lowerRadius=0.4, height=0.6)),
]
ELLIPSOIDS = [
    ("sphere", "Sphere", dict(radiusX=0.4)),
    ("ellipsoid", "Ellipsoid", dict(radiusX=0.6, radiusY=0.4, radiusZ=0.3)),
    ("ellipsoidSector", "Ellipsoid sector", dict(radiusX=0.6, radiusY=0.4, radiusZ=0.3, revolutionAngle=1.5 * math.pi)),
]
TORI = [
    ("torus", "Torus", dict(majorRadius=0.5, minorRadius=0.12)),
    ("torusSector", "Torus sector", dict(majorRadius=0.5, minorRadius=0.12, revolutionAngle=math.pi)),
]

# Hydraulic accumulator: a cylindrical shell closed by two half ellipsoids. An
# ellipsoid with revolutionAngle pi is the half y >= 0; rotated about x by +90 deg
# it becomes the half z >= 0 (the upper dome), by -90 deg the half z <= 0 (the
# lower dome). The primitives touch but do not overlap, so that the volume and a
# mass from density would both be right; the mass is given directly anyway.
ACCUMULATOR_UID = "accumulator"
ACCUMULATOR_RADIUS = 0.12
ACCUMULATOR_LENGTH = 0.36  # cylindrical part
ACCUMULATOR_DOME = 0.08  # height of each dome
ACCUMULATOR_MASS = 14.0
ACCUMULATOR_INERTIA = (0.20, 0.20, 0.09)  # about the centre of gravity, kg m^2

# Multi-segment shape: a duct of circular cross section that tapers along x.
DUCT_SECTIONS = [("inlet", 0.0, 0.30), ("outlet", 1.0, 0.22)]  # (name, x, diameter)

SYSTEM_UID = "shapeCatalogue"
ROW_SPACING = 2.0  # m, along y between the primitives
COLUMN_SPACING = 2.0  # m, along x between the variants


def uid(suffix):
    return f"element_{suffix}"


def component_uid(suffix):
    return f"component_{suffix}"


def _value(v):
    return f"{v:.10g}"


def primitive_xml(tag, params, transformation=None):
    lines = [f"<{tag}>"] + [f"    <{k}>{_value(v)}</{k}>" for k, v in params.items() if v is not None]
    if transformation:
        lines.append(indent(transformation, 1))
    return "\n".join(lines + [f"</{tag}>"])


def se3_xml(rotation=None, translation=None):
    """transformationSE3Type with only the given, non-zero parts."""
    parts = ["<transformation>"]
    for name, values in (("rotation", rotation), ("translation", translation)):
        if values is None:
            continue
        parts.append(f"    <{name}>")
        parts += [f"        <{axis}>{_value(v)}</{axis}>" for axis, v in zip("xyz", values, strict=True)]
        parts.append(f"    </{name}>")
    return "\n".join(parts + ["</transformation>"])


def element_xml(tag, suffix, name, geometry, mass):
    return "\n".join([f'<{tag} uID="{uid(suffix)}">', f"    <name>{name}</name>", indent(geometry, 1),
                      indent(mass, 1), f"</{tag}>"])


def geometry_xml(primitives, representation=None):
    attribute = f' representation="{representation}"' if representation else ""
    return "\n".join([f"<geometry{attribute}>", *(indent(p, 1) for p in primitives), "</geometry>"])


def density_xml(density=DENSITY):
    return f"<mass>\n    <density>{_value(density)}</density>\n</mass>"


def catalogue_elements():
    """(suffix, name, xml) of the generic elements of the shape catalogue, row by row."""
    rows = []
    for plural, tag, shapes in [("cuboids", "cuboid", CUBOIDS), ("cylinders", "cylinder", CYLINDERS),
                                ("cones", "cone", CONES), ("ellipsoids", "ellipsoid", ELLIPSOIDS),
                                ("tori", "torus", TORI)]:
        row = []
        for suffix, name, params in shapes:
            geometry = geometry_xml([collection(plural, [primitive_xml(tag, params)])])
            row.append((suffix, name, element_xml("genericElement", suffix, name, geometry, density_xml())))
        rows.append(row)
    return rows


# Cylinder rows and cone rows share one row in the catalogue.
def catalogue_rows():
    rows = catalogue_elements()
    return [rows[0], rows[1] + rows[2], rows[3], rows[4]]


def accumulator_primitives():
    r, length, h = ACCUMULATOR_RADIUS, ACCUMULATOR_LENGTH, ACCUMULATOR_DOME
    dome = dict(radiusX=r, radiusY=h, radiusZ=r, revolutionAngle=math.pi)
    return {
        "cylinders": [primitive_xml("cylinder", dict(radius=r, height=length))],
        "ellipsoids": [
            primitive_xml("ellipsoid", dome, se3_xml(rotation=(90, 0, 0), translation=(0, 0, length))),
            primitive_xml("ellipsoid", dome, se3_xml(rotation=(-90, 0, 0))),
        ],
    }


def accumulator_centroid():
    """Centre of the volume of the accumulator, on its axis."""
    r, length, h = ACCUMULATOR_RADIUS, ACCUMULATOR_LENGTH, ACCUMULATOR_DOME
    v_cylinder = math.pi * r * r * length
    v_dome = 2.0 / 3.0 * math.pi * r * r * h
    # centroid of a half ellipsoid lies 3/8 of its height from the cut
    z = (v_cylinder * length / 2 + v_dome * (length + 3 * h / 8) + v_dome * (-3 * h / 8)) / (v_cylinder + 2 * v_dome)
    return z, v_cylinder + 2 * v_dome


def accumulator_xml():
    primitives = accumulator_primitives()
    geometry = geometry_xml([collection(tag, items) for tag, items in primitives.items()])
    z, _ = accumulator_centroid()
    jxx, jyy, jzz = ACCUMULATOR_INERTIA
    mass = "\n".join([
        "<mass>", f"    <mass>{_value(ACCUMULATOR_MASS)}</mass>", "    <location>", "        <x>0</x>", "        <y>0</y>",
        f"        <z>{z:.3f}</z>", "    </location>", "    <massInertia>", f"        <Jxx>{_value(jxx)}</Jxx>",
        f"        <Jyy>{_value(jyy)}</Jyy>", f"        <Jzz>{_value(jzz)}</Jzz>", "    </massInertia>", "</mass>",
    ])
    return element_xml("accumulator", ACCUMULATOR_UID, "Hydraulic accumulator", geometry, mass)


def duct_xml():
    sections, segments = [], []
    for name, x, diameter in DUCT_SECTIONS:
        sections.append("\n".join([
            f'<section uID="{uid("duct")}_{name}">', f"    <name>{name.capitalize()}</name>",
            indent(se3_xml(translation=(x, 0, 0)).replace("<transformation>", "<transformation>"), 1),
            "    <elements>", f'        <element uID="{uid("duct")}_{name}_element">',
            f"            <name>{name.capitalize()}</name>", f"            <profileUID>{FUSELAGE_PROFILE_UID}</profileUID>",
            "            <transformation>", "                <scaling>", "                    <x>1</x>",
            f"                    <y>{_value(diameter)}</y>", f"                    <z>{_value(diameter)}</z>",
            "                </scaling>", "            </transformation>", "        </element>", "    </elements>",
            "</section>",
        ]))
    (first, *_), (last, *_) = DUCT_SECTIONS[0], DUCT_SECTIONS[-1]
    segments.append("\n".join([
        f'<segment uID="{uid("duct")}_segment">', "    <name>Duct</name>",
        f"    <fromElementUID>{uid('duct')}_{first}_element</fromElementUID>",
        f"    <toElementUID>{uid('duct')}_{last}_element</toElementUID>", "</segment>",
    ]))
    shape = "\n".join(["<multiSegmentShape>", indent(collection("sections", sections), 1),
                       indent(collection("segments", segments), 1), "</multiSegmentShape>"])
    geometry = geometry_xml([collection("multiSegmentShapes", [shape])])
    return element_xml("genericElement", "duct", "Duct", geometry, density_xml(250.0))


def component_xml(suffix, name, element_suffix, translation=None, rotation=None):
    lines = [f'<component uID="{component_uid(suffix)}">', f"    <name>{name}</name>",
             f"    <systemElementUID>{uid(element_suffix)}</systemElementUID>"]
    if translation is not None or rotation is not None:
        lines.append(indent(se3_xml(rotation=rotation, translation=translation), 1))
    return "\n".join(lines + ["</component>"])


def placements():
    """(component suffix, name, element suffix, translation) of all positioned components."""
    result = []
    for i, row in enumerate(catalogue_rows()):
        for j, (suffix, name, _) in enumerate(row):
            result.append((suffix, name, suffix, (j * COLUMN_SPACING, i * ROW_SPACING, 0.0)))
    last = len(catalogue_rows())
    result.append((ACCUMULATOR_UID, "Hydraulic accumulator", ACCUMULATOR_UID, (0.0, last * ROW_SPACING, 0.0)))
    result.append(("duct", "Duct", "duct", (COLUMN_SPACING, last * ROW_SPACING, 0.0)))
    return result


def systems_xml():
    components = [component_xml(s, n, e, translation=t) for s, n, e, t in placements()]
    components.append(component_xml("spareBox", "Spare box, place not yet known", "box"))
    system = "\n".join([f'<genericSystem uID="{SYSTEM_UID}">', "    <name>Shape catalogue</name>",
                        "    <description>Every shape of the example library, each installed once</description>",
                        indent(collection("components", components), 1), "</genericSystem>"])
    return collection("genericSystems", [system])


def system_elements_xml():
    generic = [xml for row in catalogue_rows() for _, _, xml in row] + [duct_xml()]
    hydraulic = collection("hydraulicElements", [collection("storageElements", [
        collection("accumulators", [accumulator_xml()])])])
    return "\n".join([indent(collection("genericElements", generic), 0), hydraulic])


def write_example():
    systems = systems_xml()
    elements = system_elements_xml()
    # systemElements is a collection of vehicles; its children are passed without the outer tag
    write_cpacs_file(
        EXAMPLE_FILE, generator=Path(__file__), name="System element shapes",
        description="Catalogue of the geometry primitives of system elements, each installed once",
        model_uid="shapeCatalogueAircraft", model_name="Shape catalogue", components_tag="systems",
        components=systems, profiles_tag="fuselageProfiles", profiles=circle_profile_xml(),
        extra_vehicles=[("systemElements", elements)],
    )


# ------------------------------------------------------------------ volumes
def cuboid_volume(p):
    lx, dy, hz = p["lengthX"], p["depthY"], p["heightZ"]
    ux = p.get("upperFaceXmax", lx) - p.get("upperFaceXmin", 0.0)
    uy = p.get("upperFaceYmax", dy) - p.get("upperFaceYmin", 0.0)
    # the cross section is a rectangle whose sides vary linearly with z: prismatoid formula
    mid = (lx + ux) / 2 * (dy + uy) / 2
    return hz / 6 * (lx * dy + 4 * mid + ux * uy)


def cone_volume(p):
    r0, r1, h = p["lowerRadius"], p.get("upperRadius", 0.0), p["height"]
    return math.pi * h / 3 * (r0 * r0 + r0 * r1 + r1 * r1)


def ellipsoid_volume(p):
    a = p["radiusX"]
    b, c = p.get("radiusY", a), p.get("radiusZ", a)
    return 4 / 3 * math.pi * a * b * c * p.get("revolutionAngle", 2 * math.pi) / (2 * math.pi)


def torus_volume(p):
    return 2 * math.pi ** 2 * p["majorRadius"] * p["minorRadius"] ** 2 * p.get("revolutionAngle", 2 * math.pi) / (
        2 * math.pi)


def expected_volumes():
    """Volume of every element of the catalogue, for the comparison with an implementation."""
    result = {}
    for suffix, _, p in CUBOIDS:
        result[suffix] = cuboid_volume(p)
    for suffix, _, p in CYLINDERS:
        result[suffix] = math.pi * p["radius"] ** 2 * p["height"]
    for suffix, _, p in CONES:
        result[suffix] = cone_volume(p)
    for suffix, _, p in ELLIPSOIDS:
        result[suffix] = ellipsoid_volume(p)
    for suffix, _, p in TORI:
        result[suffix] = torus_volume(p)
    result[ACCUMULATOR_UID] = accumulator_centroid()[1]
    (_, _, d0), (_, x1, d1) = DUCT_SECTIONS
    r0, r1 = d0 / 2, d1 / 2
    result["duct"] = math.pi * x1 / 3 * (r0 * r0 + r0 * r1 + r1 * r1)
    return result


# ------------------------------------------------------------------ 3D drawing
class View:
    """Orthographic view: azimuth about z from the x-axis, elevation above the x-y plane."""

    def __init__(self, azimuth, elevation):
        a, e = math.radians(azimuth), math.radians(elevation)
        self.toward = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])  # to the viewer
        self.right = np.array([-math.sin(a), math.cos(a), 0.0])
        self.up = np.cross(self.toward, self.right)
        self.light = _unit(0.35 * self.toward + 0.55 * self.up - 0.45 * self.right)

    def __call__(self, points):
        p = np.asarray(points, dtype=float)
        return np.stack([p @ self.right, p @ self.up], axis=-1)

    def depth(self, points):
        return np.asarray(points, dtype=float) @ self.toward  # larger is nearer


def _unit(v):
    return v / np.linalg.norm(v)


class Mesh:
    """Polygons over shared vertices, with the edges that are drawn as lines.

    feature edges are sharp edges and borders, drawn where visible; smooth
    surfaces also get their outline, the edges between a front and a back face.
    """

    def __init__(self, vertices, faces, features=(), smooth=True):
        self.vertices = np.asarray(vertices, dtype=float)
        self.faces = [list(f) for f in faces]
        self.features = [tuple(e) for e in features]
        self.smooth = smooth

    def normals(self):
        result = []
        for f in self.faces:
            p = self.vertices[f]
            n = np.zeros(3)
            for i in range(len(p)):  # Newell's method, robust for degenerate quads
                a, b = p[i], p[(i + 1) % len(p)]
                n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]),
                               (a[0] - b[0]) * (a[1] + b[1])])
            norm = np.linalg.norm(n)
            result.append(n / norm if norm > 1e-12 else n)
        return np.array(result)


def _grid_faces(nu, nv, closed_u=False):
    faces = []
    for i in range(nu if closed_u else nu - 1):
        for j in range(nv - 1):
            i1 = (i + 1) % nu
            faces.append([i * nv + j, i1 * nv + j, i1 * nv + j + 1, i * nv + j + 1])
    return faces


def cuboid_mesh(p):
    lx, dy, hz = p["lengthX"], p["depthY"], p["heightZ"]
    x0, x1 = p.get("upperFaceXmin", 0.0), p.get("upperFaceXmax", lx)
    y0, y1 = p.get("upperFaceYmin", 0.0), p.get("upperFaceYmax", dy)
    v = [(0, 0, 0), (lx, 0, 0), (lx, dy, 0), (0, dy, 0), (x0, y0, hz), (x1, y0, hz), (x1, y1, hz), (x0, y1, hz)]
    faces = [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    return Mesh(v, faces, edges, smooth=False)


def revolved_mesh(r0, r1, h, n=144):
    """Cylinder or cone about z, from radius r0 at z = 0 to r1 at z = h."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    bottom = np.stack([r0 * np.cos(t), r0 * np.sin(t), np.zeros(n)], axis=1)
    top = np.stack([r1 * np.cos(t), r1 * np.sin(t), np.full(n, h)], axis=1)
    v = np.concatenate([bottom, top])
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    faces.append(list(range(n - 1, -1, -1)))
    edges = [(i, (i + 1) % n) for i in range(n)]
    if r1 > 1e-9:
        faces.append(list(range(n, 2 * n)))
        edges += [(n + i, n + (i + 1) % n) for i in range(n)]
    return Mesh(v, faces, edges)


def ellipsoid_mesh(a, b, c, angle=2 * np.pi, nu=144, nv=72):
    full = angle >= 2 * np.pi - 1e-9
    u = np.linspace(0, angle, nu, endpoint=not full)
    phi = np.linspace(0, np.pi, nv)
    uu, pp = np.meshgrid(u, phi, indexing="ij")
    v = np.stack([a * np.sin(pp) * np.cos(uu), b * np.sin(pp) * np.sin(uu), c * np.cos(pp)], axis=-1).reshape(-1, 3)
    faces = _grid_faces(nu, nv, closed_u=full)
    edges = []
    if not full:
        for i in (0, nu - 1):  # the two cut faces, closed along the z-axis
            ring = [i * nv + j for j in range(nv)]
            faces.append(ring if i else ring[::-1])
            edges += list(zip(ring[:-1], ring[1:]))
        edges.append((0, nv - 1))  # the z-axis between the poles
    return Mesh(v, faces, edges)


def torus_mesh(major, minor, angle=2 * np.pi, nu=240, nv=72):
    full = angle >= 2 * np.pi - 1e-9
    u = np.linspace(0, angle, nu, endpoint=not full)
    w = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    uu, ww = np.meshgrid(u, w, indexing="ij")
    rho = major + minor * np.cos(ww)
    v = np.stack([rho * np.cos(uu), rho * np.sin(uu), minor * np.sin(ww)], axis=-1).reshape(-1, 3)
    faces = []
    for i in range(nu if full else nu - 1):
        for j in range(nv):
            i1, j1 = (i + 1) % nu, (j + 1) % nv
            faces.append([i * nv + j, i1 * nv + j, i1 * nv + j1, i * nv + j1])
    edges = []
    if not full:
        for i in (0, nu - 1):
            ring = [i * nv + j for j in range(nv)]
            faces.append(ring[::-1] if i == 0 else ring)
            edges += [(ring[j], ring[(j + 1) % nv]) for j in range(nv)]
    return Mesh(v, faces, edges)


def _shade(normal, view):
    base, paper = np.array(to_rgb(LIGHT)), np.array(to_rgb(COLORS["surface"]))
    lambert = max(0.0, float(normal @ view.light))
    return tuple(paper + (base - paper) * (0.9 - 0.45 * lambert))


def _covered(points2d, depth, tris2d, tri_depth, eps):
    """For each point, whether a triangle in front of it covers it."""
    a, b, c = tris2d[:, 0], tris2d[:, 1], tris2d[:, 2]
    p = points2d[:, None, :]
    v0, v1, v2 = c - a, b - a, p - a
    d00 = np.sum(v0 * v0, -1)
    d01 = np.sum(v0 * v1, -1)
    d11 = np.sum(v1 * v1, -1)
    d20 = np.sum(v2 * v0, -1)
    d21 = np.sum(v2 * v1, -1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-14
    den = np.where(ok, den, 1.0)
    s = (d11 * d20 - d01 * d21) / den  # weight of c
    t = (d00 * d21 - d01 * d20) / den  # weight of b
    inside = ok & (s > 1e-9) & (t > 1e-9) & (s + t < 1 - 1e-9)
    z = tri_depth[:, 0] + t * (tri_depth[:, 1] - tri_depth[:, 0]) + s * (tri_depth[:, 2] - tri_depth[:, 0])
    return np.any(inside & (z > depth[:, None] + eps), axis=1)


class Occluder:
    """The front faces of a mesh, to test whether points lie behind it."""

    def __init__(self, mesh, view, front):
        tris = np.array([(f[0], f[i], f[i + 1]) for k, f in enumerate(mesh.faces) if front[k]
                         for i in range(1, len(f) - 1)])
        self.view = view
        self.tris2d, self.depth = view(mesh.vertices[tris]), view.depth(mesh.vertices[tris])
        self.eps = 1e-3 * np.ptp(view(mesh.vertices), axis=0).max()

    def hidden(self, points):
        points = np.asarray(points, float)
        result = np.zeros(len(points), dtype=bool)
        for start in range(0, len(points), 400):
            chunk = slice(start, start + 400)
            result[chunk] = _covered(self.view(points[chunk]), self.view.depth(points[chunk]), self.tris2d, self.depth,
                                     self.eps)
        return result


def draw_mesh(ax, mesh, view, color=SERIES1, lw=None, zorder=2):
    """Shaded faces from back to front, then the visible edges and outlines. Returns the occluder."""
    lw = lw or LINE["secondary"]
    normals = mesh.normals()
    front = normals @ view.toward > 1e-9
    depth = np.array([view.depth(mesh.vertices[f]).mean() for f in mesh.faces])
    order = np.argsort(depth)
    polys = [view(mesh.vertices[mesh.faces[i]]) for i in order]
    colors = [_shade(normals[i], view) for i in order]
    ax.add_collection(PolyCollection(polys, facecolors=colors, edgecolors=colors, linewidths=0.3, zorder=zorder))

    # outline of a smooth surface: edges between a front and a back face
    owner = {}
    for k, f in enumerate(mesh.faces):
        for i in range(len(f)):
            owner.setdefault(tuple(sorted((f[i], f[(i + 1) % len(f)]))), []).append(k)
    lines = [(e, lw) for e in mesh.features]
    if mesh.smooth:
        lines += [(e, LINE["data"]) for e, ks in owner.items() if len(ks) == 2 and front[ks[0]] != front[ks[1]]]

    occluder = Occluder(mesh, view, front)
    mids = np.array([(mesh.vertices[a] + mesh.vertices[b]) / 2 for (a, b), _ in lines])
    for ((a, b), width), h in zip(lines, occluder.hidden(mids), strict=True):
        if not h:
            ax.plot(*view(mesh.vertices[[a, b]]).T, color=color, lw=width, zorder=zorder + 1)
    return occluder


def visible_polyline(ax, view, points, occluder, color=INK2, lw=None, zorder=6):
    """A 3D polyline, drawn only where the solid does not cover it. Returns the visible mask."""
    points = np.asarray(points, float)
    hidden = occluder.hidden(points)
    lw = lw or LINE["reference"]
    start = None
    for i in range(len(points) + 1):
        if i < len(points) and not hidden[i]:
            start = i if start is None else start
        elif start is not None:
            if i - start > 1:
                ax.plot(*view(points[start:i]).T, color=color, lw=lw, zorder=zorder)
            start = None
    return ~hidden


def dimension(ax, view, a, b, offset, text, text_offset=(0, 0), ha="center", va="center", ext_a=None, ext_b=None):
    """Distance between the 3D points a and b, drawn shifted by the 3D vector offset.

    Extension lines run from the feature points ext_a and ext_b (default a and b) to
    a little beyond the dimension line.
    """
    a, b, offset = np.asarray(a, float), np.asarray(b, float), np.asarray(offset, float)
    a1, b1 = a + offset, b + offset
    for p, q in ((a if ext_a is None else np.asarray(ext_a, float), a1),
                 (b if ext_b is None else np.asarray(ext_b, float), b1)):
        if np.linalg.norm(q - p) > 1e-9:
            gap = 0.04 * _unit(q - p)
            ax.plot(*view([p + gap, q + 1.5 * gap]).T, color=MUTED, lw=LINE["reference"], zorder=4)
    mid = 0.5 * (a1 + b1)
    arrow(ax, view(mid), view(a1), color=INK2, lw=LINE["reference"], head=6)
    arrow(ax, view(mid), view(b1), color=INK2, lw=LINE["reference"], head=6)
    label(ax, view(mid), text, text_offset, ha=ha, va=va)


def axes_cross(ax, view, origin, length, names=("x", "y", "z")):
    o = np.asarray(origin, float)
    for i, name in enumerate(names):
        if not name:
            continue
        tip = o + length * np.eye(3)[i]
        arrow(ax, view(o), view(tip), color=INK2, lw=LINE["reference"], head=6)
        d = view(tip) - view(o)
        label(ax, view(tip), name, tuple(8 * d / np.linalg.norm(d)), color=INK2)
    dot(ax, view(o), color=INK, size=4)


def angle_above(ax, view, occluder, height, radius_x, radius_y, angle, text, text_at, text_offset, ha="center",
                va="center"):
    """The revolution angle about the z-axis, drawn in a plane parallel to x-y above the solid.

    The z-axis is drawn up to that plane, and a line parallel to the x-axis marks
    where the angle starts. The arc follows the parameter of the ellipse with the
    semi-axes radius_x and radius_y, as the revolution angle of an ellipsoid does.
    """
    top = np.array([0.0, 0.0, height])
    visible_polyline(ax, view, np.linspace((0, 0, 0), top + (0, 0, 0.12), 200), occluder)
    arrow(ax, view(top + (0, 0, 0.06)), view(top + (0, 0, 0.14)), color=INK2, lw=LINE["reference"], head=6)
    label(ax, view(top + (0, 0, 0.14)), "z", (0, 7), color=INK2)
    reference = 1.25 * radius_x
    ax.plot(*view([top, top + (reference, 0, 0)]).T, color=INK2, lw=LINE["reference"], zorder=6)
    label(ax, view(top + (reference, 0, 0)), "parallel to x", (5, 0), ha="left", color=INK2)
    t = np.linspace(0, angle, 240)
    arc = top + np.stack([radius_x * np.cos(t), radius_y * np.sin(t), np.zeros_like(t)], axis=1)
    ax.add_patch(Polygon(view(np.vstack([top, arc])), closed=True, facecolor=SERIES1, alpha=2 * WASH,
                         edgecolor="none", zorder=5))
    ax.plot(*view(arc[:-6]).T, color=INK2, lw=LINE["reference"], zorder=6)
    arrow(ax, view(arc[-8]), view(arc[-1]), color=INK2, lw=LINE["reference"], head=6)
    at = top + (radius_x * math.cos(text_at), radius_y * math.sin(text_at), 0.0)
    label(ax, view(at), text, text_offset, ha=ha, va=va)


def _titles(fig, axes, titles):
    """Panel titles on one line, above the highest panel."""
    fig.canvas.draw()
    top = max(ax.get_position().y1 for ax in axes)
    for ax, title in zip(axes, titles, strict=True):
        fig.text(ax.get_position().x0, top + 0.03, title, fontsize=FONT_SIZE["base"], color=INK, ha="left",
                 va="bottom")


def _panel(ax):
    ax.set_aspect("equal")
    ax.axis("off")


# ------------------------------------------------------------------ figures
VIEW = View(azimuth=-58, elevation=24)


def _silhouette_point(r, z, sign=1.0):
    """Point of the circle of radius r at height z that lies on the right (sign 1) or left outline."""
    return np.array([sign * r * VIEW.right[0], sign * r * VIEW.right[1], z])


def figure_cuboid():
    p = CUBOIDS[1][2]
    lx, dy, hz = p["lengthX"], p["depthY"], p["heightZ"]
    x0, x1, y0, y1 = p["upperFaceXmin"], p["upperFaceXmax"], p["upperFaceYmin"], p["upperFaceYmax"]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
        ax = axes[0]
        _panel(ax)
        draw_mesh(ax, cuboid_mesh(p), VIEW)
        axes_cross(ax, VIEW, (0, 0, 0), 0.3)
        dimension(ax, VIEW, (0, 0, 0), (lx, 0, 0), (0, -0.3, 0), "lengthX", (-6, -8), ha="right")
        dimension(ax, VIEW, (lx, 0, 0), (lx, dy, 0), (0.3, 0, 0), "depthY", (8, -4), ha="left")
        dimension(ax, VIEW, (lx, dy, 0), (lx, dy, hz), (0.3, 0.3, 0), "heightZ", (6, 0), ha="left",
                  ext_b=(x1, y1, hz))

        ax = axes[1]
        _panel(ax)
        lower = [(0, 0), (lx, 0), (lx, dy), (0, dy)]
        upper = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        ax.add_patch(Polygon(lower, closed=True, facecolor=SERIES1, alpha=WASH, edgecolor="none", zorder=2))
        ax.add_patch(Polygon(lower, closed=True, facecolor="none", edgecolor=SERIES1, lw=LINE["secondary"], zorder=3))
        ax.add_patch(Polygon(upper, closed=True, facecolor=LIGHT, alpha=0.6, edgecolor="none", zorder=3))
        ax.add_patch(Polygon(upper, closed=True, facecolor="none", edgecolor=SERIES1, lw=LINE["data"], zorder=4))
        for a, b in zip(lower, upper, strict=True):
            ax.plot(*np.array([a, b]).T, color=SERIES1, lw=LINE["secondary"], zorder=3)
        label(ax, ((x0 + x1) / 2, (y0 + y1) / 2), "upper face")
        label(ax, (lx / 2, dy), "lower face", (0, 7), va="bottom", color=INK2)
        # axes with the coordinates of the upper face
        reach_x, reach_y = lx + 0.25, dy + 0.12
        arrow(ax, (0, 0), (reach_x, 0), color=INK2, lw=LINE["reference"], head=6)
        arrow(ax, (0, 0), (0, reach_y), color=INK2, lw=LINE["reference"], head=6)
        label(ax, (reach_x, 0), "x", (7, 0), color=INK2)
        label(ax, (0, reach_y), "y", (0, 7), color=INK2)
        dot(ax, (0, 0), size=4)
        below, right = -0.09, lx + 0.09
        for value, name in [(x0, "upperFaceXmin"), (x1, "upperFaceXmax")]:
            ax.plot([value, value], [y0, below], color=MUTED, lw=LINE["reference"], zorder=1)
            label(ax, (value, below), name, (0, -3), ha="center", va="top")
        for value, name in [(y0, "upperFaceYmin"), (y1, "upperFaceYmax")]:
            ax.plot([x1, right], [value, value], color=MUTED, lw=LINE["reference"], zorder=1)
            label(ax, (right, value), name, (3, 0), ha="left", va="center")
        for a in axes:
            a.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99, wspace=0.12)
        _titles(fig, axes, ["(a) oblique view", "(b) top view"])
        save_figure(fig, FIGURES / "systemElementCuboid.png")


def _revolved_panel(ax, r0, r1, h, top_name, bottom_name=None):
    _panel(ax)
    draw_mesh(ax, revolved_mesh(r0, r1, h), VIEW)
    axes_cross(ax, VIEW, (0, 0, 0), 0.55 * min(r0, max(r1, r0)))
    # radii as horizontal dimensions in the image, from the axis to the right-hand outline
    lift = np.array([0, 0, 0.18])
    if r1 > 0:
        dimension(ax, VIEW, (0, 0, h), _silhouette_point(r1, h), lift + (0, 0, r1 * 0.35), top_name, (0, 6),
                  va="bottom")
    if bottom_name:
        dimension(ax, VIEW, (0, 0, 0), _silhouette_point(r0, 0), -lift - (0, 0, r0 * 0.45), bottom_name, (0, -6),
                  va="top")
    side = _silhouette_point(max(r0, r1), 0)
    shift = 0.22 * _unit(side)
    dimension(ax, VIEW, side, side + (0, 0, h), shift, "height", (6, 0), ha="left",
              ext_a=_silhouette_point(r0, 0), ext_b=_silhouette_point(r1, h))


def figure_cylinder_cone():
    cylinder, frustum = CYLINDERS[0][2], CONES[0][2]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.4))
        r, h = cylinder["radius"], cylinder["height"]
        _revolved_panel(axes[0], r, r, h, "radius")
        _revolved_panel(axes[1], frustum["lowerRadius"], frustum["upperRadius"], frustum["height"], "upperRadius",
                        "lowerRadius")
        for a in axes:
            a.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99, wspace=0.1)
        _titles(fig, axes, ["(a) cylinder", "(b) cone"])
        save_figure(fig, FIGURES / "systemElementCylinderCone.png")


def figure_ellipsoid():
    full, sector = ELLIPSOIDS[1][2], ELLIPSOIDS[2][2]
    a, b, c = full["radiusX"], full["radiusY"], full["radiusZ"]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.0))
        ax = axes[0]
        _panel(ax)
        draw_mesh(ax, ellipsoid_mesh(a, b, c), VIEW)
        for end in [(a, 0, 0), (0, b, 0), (0, 0, c)]:
            arrow(ax, VIEW((0, 0, 0)), VIEW(end), color=INK2, lw=LINE["reference"], head=6)
        dot(ax, VIEW((0, 0, 0)), color=INK, size=4)
        label(ax, VIEW((0.55 * a, 0, 0)), "radiusX", (0, -9), va="top")
        label(ax, VIEW((0, 0.7 * b, 0)), "radiusY", (6, -6), ha="left")
        label(ax, VIEW((0, 0, 0.6 * c)), "radiusZ", (-5, 0), ha="right")

        ax = axes[1]
        _panel(ax)
        occluder = draw_mesh(ax, ellipsoid_mesh(a, b, c, sector["revolutionAngle"]), VIEW)
        dot(ax, VIEW((0, 0, 0)), color=INK, size=4)
        angle_above(ax, VIEW, occluder, c + 0.22, 0.55 * a, 0.55 * b, sector["revolutionAngle"], "revolutionAngle",
                    math.pi, (-6, 0), ha="right")
        for a_ in axes:
            a_.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99, wspace=0.1)
        _titles(fig, axes, ["(a) semi-axes", "(b) revolutionAngle 3π/2"])
        save_figure(fig, FIGURES / "systemElementEllipsoid.png")


def figure_torus():
    full, sector = TORI[0][2], TORI[1][2]
    major, minor = full["majorRadius"], full["minorRadius"]
    with figure_style():
        fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9))
        ax = axes[0]
        _panel(ax)
        draw_mesh(ax, torus_mesh(major, minor), VIEW)
        axes_cross(ax, VIEW, (0, 0, 0), 0.22)

        ax = axes[1]
        _panel(ax)
        occluder = draw_mesh(ax, torus_mesh(major, minor, sector["revolutionAngle"]), VIEW)
        # the radii on the end face in the x-z plane, which faces the viewer
        centre = np.array([major, 0.0, 0.0])
        dot(ax, VIEW((0, 0, 0)), color=INK, size=4)
        arrow(ax, VIEW((0, 0, 0)), VIEW(centre), color=INK2, lw=LINE["reference"], head=6)
        label(ax, VIEW(centre / 2), "majorRadius", (-4, -8), ha="right", va="top")
        dot(ax, VIEW(centre), color=INK, size=3.5)
        arrow(ax, VIEW(centre), VIEW(centre + (0, 0, minor)), color=INK2, lw=LINE["reference"], head=5)
        ax.annotate("minorRadius", xy=VIEW(centre + (0, 0, 0.6 * minor)), xytext=(34, -22), textcoords="offset points",
                    ha="left", va="center", fontsize=NOTE, color=INK, zorder=7, arrowprops=leader())
        angle_above(ax, VIEW, occluder, minor + 0.42, 0.3, 0.3, sector["revolutionAngle"], "revolutionAngle",
                    0.75 * math.pi, (-6, 2), ha="right", va="bottom")
        for a_ in axes:
            a_.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99, wspace=0.1)
        _titles(fig, axes, ["(a) torus", "(b) revolutionAngle π"])
        save_figure(fig, FIGURES / "systemElementTorus.png")


# ------------------------------------------------------------------ excerpts
def excerpt_catalogue_element(suffix):
    for row in catalogue_rows():
        for s, _, xml in row:
            if s == suffix:
                return xml
    raise KeyError(suffix)


def report():
    print("Volumes of the elements (m^3), for the comparison with an implementation")
    for suffix, volume in expected_volumes().items():
        print(f"  {suffix:16s} {volume:.6f}")
    z, _ = accumulator_centroid()
    print(f"Accumulator: centroid of the volume at z = {z:.4f} m, overall length "
          f"{ACCUMULATOR_LENGTH + 2 * ACCUMULATOR_DOME:.2f} m from z = {-ACCUMULATOR_DOME:.2f} m")


def excerpts():
    """(type, excerpt) for the documentation, each as it is shown there."""
    return [
        ("cuboidType", excerpt_catalogue_element("taperedBox")),
        ("ellipsoidType", excerpt_catalogue_element("ellipsoidSector")),
        ("elementGeometryType", accumulator_xml()),
    ]


def main():
    figure_cuboid()
    figure_cylinder_cone()
    figure_ellipsoid()
    figure_torus()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in excerpts():
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

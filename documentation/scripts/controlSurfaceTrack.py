# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure and example data for the documentation of the mechanism of a control surface
(controlSurfaceTrackTypeType and the types below it, controlSurfaceActuatorType, cruiseRollerType,
interconnectionStrutType, zCouplingType).

Run from the repository root:

    uv run documentation/scripts/controlSurfaceTrack.py

The script writes the figure controlSurfaceTrackTypes and the example file examples/controlSurfaceTracks.xml,
and prints the excerpts shown in the documentation. The wing, its component segment and the control surfaces
are defined in wing.py, componentSegment.py and controlSurface.py.

The figure shows the four track types on the section of the example wing at the inner border of its flap. The
shapes of the wing and of the flap are the ones of that example; the members of the mechanism are schematic,
as in the drawings the figure replaces, because the schema describes no shape for them.

The joint coordinates of the example are computed:
  the deflection path leads (see controlSurfacePathType), so a joint on the control surface is moved with it;
  a joint on the wing that carries a strut is placed on the perpendicular bisector plane of the two positions
  of the joint at its other end, so that the strut has the same length at both control parameters;
  the straight track of a track type 3 runs through the two positions of the joint of its carriage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from componentSegment import GAP, component_segment_point, handle_line, handle_point, legend, point_marker, text
from controlSurface import (CS_UID, FLAP, SLAT, SPOILER, Frame, DEVICE_COLOR, device_hinges, deflect, device_xml,
                            draw_device, draw_wing_section, flap_border_xml, flap_section, iso_xml, panel_title,
                            path_xml, section_axes, slat_border_xml, spoiler_border_xml, unit)
from example_xml import indent, write_cpacs_file
from figure_style import COLORS, LINE, figure_style, save_figure
from structuralProfile import MATERIAL_UID, PROFILE_UID, material_xml as structural_material_xml, profile_xml
from wing import (DOCUMENTATION, FIGURES, INK, INK2, MUTED, WING_UID, airfoil_xml, circle_profile_xml,
                  fuselage_xml, wing_xml)

EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "controlSurfaceTracks.xml"
TRACK_COLOR = COLORS["series3"]

# Spanwise positions of the tracks and of the parts attached to the flap.
FLAP_TRACK_ETAS = (0.20, 0.32)
SPOILER_TRACK_ETA = 0.26
CRUISE_ROLLER_ETA = 0.26
ACTUATOR_ETA = 0.5  # relative spanwise position on the outer flap
ACTUATOR_PARENT = (0.66, 0.45)  # parentXsi and parentHeight on the wing
ACTUATOR_SURFACE = (0.30, 0.50)  # parentXsi and parentHeight on the control surface


# --------------------------------------------------------------- the example data
def xz_frame(eta, xsi=0.0):
    """Plane y = const at a spanwise position, with the x-axis of the wing as first and the z-axis as second
    axis. The whole chord of the component segment at this eta lies in it."""
    return Frame(component_segment_point(eta, xsi), (1.0, 0.0, 0.0), np.array([0.0, 0.0, 1.0]))


def ruled_in_plane(inner, outer, frame):
    """Intersection of the ruled surface through two contours (3D, point by point) with the plane of a frame."""
    distance_inner = (inner - frame.origin) @ frame.w
    distance_outer = (outer - frame.origin) @ frame.w
    share = distance_inner / (distance_inner - distance_outer)
    return inner + share[:, None] * (outer - inner)


def border_contour_3d(device, section, side):
    """Contour of a control surface at one of its borders, in space."""
    borders = dict(device["borders"])
    borders["inner"] = device["borders"][side]
    frame, _, _, _, contour, _ = section({**device, "borders": borders})
    return frame.to3d(contour)


def contour_in_plane(device, section, frame):
    """Contour of a control surface in a plane between its borders, in space."""
    return ruled_in_plane(border_contour_3d(device, section, "inner"),
                          border_contour_3d(device, section, "outer"), frame)


def hinge_line_point(device, frame):
    """The point of the hinge line of a control surface that lies in the plane of a frame."""
    inner, outer = device_hinges(device)
    share = ((inner - frame.origin) @ frame.w) / ((inner - outer) @ frame.w)
    return inner + share * (outer - inner)


def moved_with_flap(point):
    """The positions of a point of the flap at the first and the last control parameter of its path."""
    return [deflect(point, FLAP, parameter)[0] for parameter in (FLAP["steps"][0][0], FLAP["steps"][-1][0])]


def strut_base(positions, frame, distance):
    """Point below the wing from which a strut reaches a moving joint with the same length at both positions.

    The point lies in the plane of the frame, on the perpendicular bisector of the two positions of the joint.
    """
    first, second = positions
    normal = second - first
    offset = 0.5 * (second @ second - first @ first) - frame.origin @ normal
    line = np.array([frame.u @ normal, frame.v @ normal])  # line @ (a, b) = offset in the plane
    middle = frame.to2d(0.5 * (first + second))[0]
    closest = middle + (offset - line @ middle) / (line @ line) * line
    along = unit(np.array([-line[1], line[0]]))
    if along[1] > 0.0:
        along = -along
    return frame.to3d([closest + distance * along])[0]


def flap_xsi(eta):
    """Relative chordwise coordinate of the leading edge of the flap at a spanwise position."""
    return float(np.interp(eta, [FLAP["borders"][side][0] for side in ("inner", "outer")],
                           [FLAP["borders"][side][2] for side in ("inner", "outer")]))


def flap_track_joints(eta):
    """The joints of a track type 3 of the flap, as {name: [position at controlParameter 0, at 1]}.

    P1 sits at the rear spar of the wing and carries the rotary drive, P2 is the lower joint of the forward
    link, P3 its joint on the flap, P4 the joint between the carriage and the flap, and P5 and P6 are the ends
    of the straight track on which the carriage runs.
    """
    frame = xz_frame(eta, flap_xsi(eta))
    upper, lower = wing_sides(frame, eta)
    flap = frame.to2d(contour_in_plane(FLAP, flap_section, frame))
    nose, chord = flap[:, 0].min(), flap[:, 0].max() - flap[:, 0].min()

    def on_flap(share, offset):
        """Point at a fraction of the flap chord, measured from the lower side of the flap."""
        a = nose + share * chord
        near = flap[(flap[:, 0] > a - 0.05) & (flap[:, 0] < a + 0.05)]
        return frame.to3d([[a, near[:, 1].min() + offset]])[0]

    p3 = moved_with_flap(on_flap(0.10, 0.03))
    p4 = moved_with_flap(on_flap(0.32, -0.09))
    p2 = strut_base(p3, frame, 0.30)
    track = [p4[0] + share * (p4[1] - p4[0]) for share in (-0.3, 1.3)]
    spar = frame.to3d([[-0.22, 0.5 * (skin_at(upper, -0.22) + skin_at(lower, -0.22))]])[0]
    return {"P1": [spar, spar], "P2": [p2, p2], "P3": p3, "P4": p4, "P5": [track[0]] * 2, "P6": [track[1]] * 2}


def wing_sides(frame, eta):
    """Upper and lower side of the wing in the plane of a frame, as 2D points sorted along the x-axis."""
    from controlSurface import to_segment
    return frame.section(to_segment(min(eta, 0.999999), 0.0)[0])


def skin_at(side, a):
    return float(np.interp(a, side[:, 0], side[:, 1]))


# ------------------------------------------------------------------------- XML
def point_xml(name, point, frame):
    """A joint of a track: x and z in the axes of the wing coordinate system, dy from the plane of the track."""
    return "\n".join([
        "<jointCoordinates>", f"    <name>{name}</name>", f"    <x>{point[0]:.4f}</x>",
        *([f"    <dy>{point[1] - frame.origin[1]:.4f}</dy>"] if abs(point[1] - frame.origin[1]) >= 5e-5 else []),
        f"    <z>{point[2]:.4f}</z>", "</jointCoordinates>",
    ])


def joint_positions_xml(joints, frame, parameters):
    lines = ["<jointPositions>"]
    for index, parameter in enumerate(parameters):
        for name, positions in joints.items():
            lines += ["    <jointPosition>", f"        <controlParameters>{parameter:g}</controlParameters>",
                      indent(point_xml(name, positions[index], frame), 2), "    </jointPosition>"]
    lines.append("</jointPositions>")
    return "\n".join(lines)


def material_xml(tag="material", levels=0):
    return indent("\n".join([f"<{tag}>", f"    <materialUID>{MATERIAL_UID}</materialUID>", f"</{tag}>"]), levels)


def struts_xml(names):
    lines = ["<struts>"]
    for name in names:
        lines += ["    <strut>", f"        <name>{name}</name>", f"        <materialUID>{MATERIAL_UID}</materialUID>",
                  f"        <profileUID>{PROFILE_UID}</profileUID>", "    </strut>"]
    lines.append("</struts>")
    return "\n".join(lines)


def secondary_xml(tag):
    return "\n".join([f"<{tag}>", f"    <materialUID>{MATERIAL_UID}</materialUID>", f"</{tag}>"])


def track_xml(uid, eta, track_type, sub_type, joints, frame, parameters, struts, actuator_uid=None):
    lines = [f'<track uID="{uid}">', indent(iso_xml("etaPosition", "eta", eta), 1),
             f"    <trackType>trackType{track_type}</trackType>",
             f"    <trackSubType>trackSubType{sub_type}</trackSubType>"]
    if actuator_uid:
        lines += [f'    <actuator uID="{uid}_actuator">', f"        <actuatorUID>{actuator_uid}</actuatorUID>",
                  "        <material>", f"            <materialUID>{MATERIAL_UID}</materialUID>",
                  "        </material>", "    </actuator>"]
    lines.append("    <trackStructure>")
    lines.append(indent(struts_xml(struts), 2))
    lines.append(indent(joint_positions_xml(joints, frame, parameters), 2))
    for tag in ("controlSurfaceAttachment", "carriage", "sidePanels", "fairing"):
        lines.append(indent(secondary_xml(tag), 2))
    lines += ["    </trackStructure>", "</track>"]
    return "\n".join(lines)


# ---------------------------------------------------------------------- figure
# Schematic placement of the members in the section at the inner border of the flap. Positions along the
# chord of the flap are fractions of that chord, heights are lengths in metres from the surface they sit on.
SCHEMATIC = {
    2: {"joints": {"P1": ("spar", 0.0), "P2": ("below", -0.05, -0.20), "P3": ("flap", 0.10, 0.03),
                   "P4": ("flap", 0.33, -0.03)},
        "members": [("P1", "P2"), ("P2", "P3"), ("P2", "P4")],
        "fixed": ("P1", "P2"),
        "labels": {"strut1": ("P1", "P2"), "strut2": ("P2", "P4")}},
    3: {"joints": {"P1": ("spar", 0.0), "P2": ("beam", 0.04, 0.45), "P3": ("flap", 0.10, 0.03),
                   "P4": ("flap", 0.36, 0.0), "P5": ("beam", 0.16), "P6": ("beam", 0.74)},
        "members": [("P1", "P2"), ("P2", "P3"), ("P4", "carriage")],
        "fixed": ("P1", "P2", "P5", "P6"),
        "track": ("P5", "P6"), "carriage": "P4",
        "labels": {"strut1": ("P2", "P3"), "strut2": ("P1", "P2")}},
    4: {"joints": {"P1": ("spar", 0.0), "P2": ("beam", 0.04, 0.45), "P3": ("flap", 0.10, 0.03),
                   "P4": ("flap", 0.36, 0.0), "P5": ("flap", 0.90, 0.0), "P6": ("beam", 0.80),
                   "P7": ("beam", 0.16), "P8": ("beam", 0.60)},
        "members": [("P1", "P2"), ("P2", "P3"), ("P4", "carriage"), ("P5", "P6")],
        "fixed": ("P1", "P2", "P6", "P7", "P8"),
        "track": ("P7", "P8"), "carriage": "P4",
        "labels": {"strut1": ("P2", "P3"), "strut2": ("P1", "P2"), "strut3": ("P5", "P6")}},
}


BEAM_FRONT, BEAM_REAR = -0.30, 0.82  # fractions of the flap chord
BEAM_DEPTH = (0.12, 0.50)  # depth of the beam below the lower side of the wing, front and rear


def beam_edges(lower, chord):
    """Upper and lower edge of the track beam, the fixed structure under the wing that carries the track.

    The beam follows the lower side of the wing, deepens towards the rear and ends before the trailing edge of
    the control surface, as such a beam does.
    """
    shares = np.linspace(BEAM_FRONT, BEAM_REAR, 24)
    top = np.array([[share * chord, skin_at(lower, share * chord)] for share in shares])
    depth = np.linspace(*BEAM_DEPTH, len(shares))
    return top, top - np.column_stack([np.zeros_like(depth), depth])


def beam_polygon(lower, chord):
    top, bottom = beam_edges(lower, chord)
    return np.vstack([top, bottom[::-1]])


def on_beam(lower, chord, share, depth=1.0):
    """Point in the beam at a fraction of the flap chord; depth 0 is its upper and 1 its lower edge."""
    top, bottom = beam_edges(lower, chord)
    a = share * chord
    high, low = (np.interp(a, edge[:, 0], edge[:, 1]) for edge in (top, bottom))
    return np.array([a, high + depth * (low - high)])


def schematic_joints(kind, chord, upper, lower, flap):
    """The joints of one track type in the section, from their schematic places."""
    points = {}
    for name, place in SCHEMATIC[kind]["joints"].items():
        if place[0] == "spar":
            a = -0.22
            points[name] = np.array([a, 0.5 * (skin_at(upper, a) + skin_at(lower, a))])
        elif place[0] == "beam":
            points[name] = on_beam(lower, chord, *place[1:])
        elif place[0] == "below":
            a = place[1] * chord
            points[name] = np.array([a, skin_at(lower, a) + place[2]])
        elif place[0] == "flap":
            a = place[1] * chord
            near = flap[(flap[:, 0] > a - 0.05) & (flap[:, 0] < a + 0.05)]
            points[name] = np.array([a, near[:, 1].min() + place[2]])
    return points


def joint_marker(ax, point, fixed):
    """A joint: filled where it moves with the control surface, open where it sits on the wing or the beam."""
    if fixed:
        ax.plot(*point, ls="none", marker="o", ms=5.6, markerfacecolor=COLORS["surface"], markeredgecolor=INK,
                mew=1.4, zorder=6, clip_on=False)
    else:
        point_marker(ax, point)


def draw_track(ax, kind, chord, upper, lower, flap):
    """The members, the carriage and the joints of one track type."""
    points = schematic_joints(kind, chord, upper, lower, flap)
    spec = SCHEMATIC[kind]
    if "track" in spec:
        start, end = (points[name] for name in spec["track"])
        ax.plot(*np.array([start, end]).T, color=TRACK_COLOR, lw=2.2, solid_capstyle="round", zorder=4.3)
        along = unit(end - start)
        across = np.array([-along[1], along[0]])
        if across[1] < 0.0:
            across = -across
        share = np.clip(np.linalg.norm(points[spec["carriage"]] - start) / np.linalg.norm(end - start), 0.0, 1.0)
        centre = start + share * (end - start) + 0.045 * across  # the carriage sits on the track
        box = [centre + s * 0.11 * along + t * 0.045 * across for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ax.add_patch(Polygon(box, closed=True, facecolor=COLORS["surface"], edgecolor=TRACK_COLOR,
                             lw=LINE["secondary"], zorder=4.4))
        points["carriage"] = centre
    for first, second in spec["members"]:
        ax.plot(*np.array([points[first], points[second]]).T, color=INK, lw=LINE["data"], zorder=4.5,
                solid_capstyle="round")
    for name, point in points.items():
        if name != "carriage":
            joint_marker(ax, point, name in spec["fixed"])
    return points


def label_joints(ax, points, offsets):
    for name, offset in offsets.items():
        ha = "left" if offset[0] > 0 else "right" if offset[0] < 0 else "center"
        va = "bottom" if offset[1] > 0 else "top" if offset[1] < 0 else "center"
        text(ax, points[name], name, offset, ha=ha, va=va, color=INK2)


JOINT_LABELS = {
    2: {"P1": (-GAP, 0), "P2": (-GAP, 0), "P3": (0, GAP), "P4": (GAP, -GAP)},
    3: {"P1": (-GAP, 0), "P2": (-GAP, 0), "P3": (0, GAP), "P4": (GAP, GAP), "P5": (0, -GAP), "P6": (0, -GAP)},
    4: {"P1": (-GAP, 0), "P2": (-GAP, 0), "P3": (0, GAP), "P4": (GAP, GAP), "P5": (0, GAP), "P6": (GAP, 0),
        "P7": (0, -GAP), "P8": (0, -GAP)},
}
STRUT_LABELS = {
    2: {"strut1": (-GAP, -GAP - 5), "strut2": (GAP, -GAP)},
    3: {"strut1": (GAP, -GAP), "strut2": (-GAP, 0)},
    4: {"strut1": (GAP, -GAP), "strut2": (-GAP, 0), "strut3": (GAP, 0)},
}
TITLES = {
    1: "(a) trackType1: revolute joint on the hinge line of the control surface",
    2: "(b) trackType2: dropped hinge below the wing",
    3: "(c) trackType3: forward link and a carriage on a straight track",
    4: "(d) trackType4: like trackType3, with an upright link as aft support",
}


def figure_track_types():
    """The four track types in the section of the example wing at the inner border of its flap."""
    frame, chord, upper, lower, flap, _ = flap_section()
    left, right, top = -0.9, chord + 0.3, 0.32
    bottoms = {1: -0.16, 2: -0.38, 3: -0.66, 4: -0.66}
    hinge = frame.to2d(device_hinges(FLAP)[0])[0]
    with figure_style():
        fig, axes = section_axes([((left, right), (bottoms[kind], top)) for kind in (1, 2, 3, 4)])
        for ax, kind in zip(axes, (1, 2, 3, 4)):
            draw_wing_section(ax, upper, lower, (left, chord + 0.3))
            draw_device(ax, flap, alpha=0.12)
            if kind in (3, 4):
                beam = beam_polygon(lower, chord)
                ax.add_patch(Polygon(beam, closed=True, facecolor=MUTED, alpha=0.18, edgecolor=MUTED,
                                     lw=LINE["secondary"], zorder=2.5))
                text(ax, on_beam(lower, chord, -0.16, 0.86), "track beam", (0, 0), color=INK2)
            if kind == 1:
                joint_marker(ax, hinge, fixed=True)
                text(ax, hinge, "P1", (0, -GAP), va="top", color=INK2)
            else:
                points = draw_track(ax, kind, chord, upper, lower, flap)
                label_joints(ax, points, JOINT_LABELS[kind])
                for name, (first, second) in SCHEMATIC[kind]["labels"].items():
                    middle = 0.5 * (points[first] + points[second])
                    text(ax, middle, name, STRUT_LABELS[kind][name], color=INK2,
                         ha="left" if STRUT_LABELS[kind][name][0] > 0 else "right")
                if "carriage" in points:
                    text(ax, points["carriage"], "carriage", (0, -GAP - 4), va="top", color=INK2)
            panel_title(ax, TITLES[kind], left)
        legend(fig, [handle_line(MUTED, LINE["secondary"]), handle_line(DEVICE_COLOR, LINE["data"]),
                     handle_line(INK, LINE["data"]), handle_line(TRACK_COLOR, 2.2), handle_point(),
                     Line2D([], [], ls="none", marker="o", ms=5.6, markerfacecolor=COLORS["surface"],
                            markeredgecolor=INK, mew=1.4)],
               ["wing section", "control surface", "strut", "track of the carriage",
                "joint on the control surface", "joint on the wing or the beam"], ncol=3)
        save_figure(fig, FIGURES / "controlSurfaceTrackTypes.png")




# ---------------------------------------------------- the parts beside the track
OUTER_FLAP = {
    "uid": f"{WING_UID}_flapOuter", "name": "Outer flap",
    "borders": {"inner": (0.40, None, 0.72), "outer": (0.60, None, 0.74)},
    "leadingEdgeShape": (0.5, 0.9, 0.7),
    "hinges": {"inner": (0.76, 0.2), "outer": (0.77, 0.2)},
    "steps": FLAP["steps"],
}
SURFACE_ACTUATOR_UID = "FlapLinearActuator"
FLAP_ACTUATOR_UID = "FlapRotaryActuator"


def relative_point_xml(tag, eta, xsi, height):
    return "\n".join([f"<{tag}>", f"    <eta>{eta:g}</eta>", f"    <xsi>{xsi:g}</xsi>",
                      f"    <relHeight>{height:g}</relHeight>", f"    <referenceUID>{CS_UID}</referenceUID>",
                      f"</{tag}>"])


def actuators_xml(uid, eta, parent, surface):
    return "\n".join([
        "<actuators>", f'    <actuator uID="{uid}">', f"        <actuatorUID>{SURFACE_ACTUATOR_UID}</actuatorUID>",
        "        <attachment>", f"            <etaControlSurface>{eta:g}</etaControlSurface>",
        "            <parentAttachment>", f"                <parentXsi>{parent[0]:g}</parentXsi>",
        f"                <parentHeight>{parent[1]:g}</parentHeight>",
        indent(material_xml(), 4), "            </parentAttachment>",
        "            <controlSurfaceAttachment>", f"                <parentXsi>{surface[0]:g}</parentXsi>",
        f"                <parentHeight>{surface[1]:g}</parentHeight>",
        indent(material_xml(), 4), "            </controlSurfaceAttachment>",
        "        </attachment>", "    </actuator>", "</actuators>",
    ])


def cruise_rollers_xml(uid, eta, xsi, height):
    return "\n".join([
        "<cruiseRollers>", f'    <cruiseRoller uID="{uid}">', indent(relative_point_xml("position", eta, xsi, height), 2),
        indent(material_xml("parentAttachment"), 2), indent(material_xml("controlSurfaceAttachment"), 2),
        "        <blockedDOF>", "            <positive>true</positive>", "            <negative>false</negative>",
        "        </blockedDOF>", "    </cruiseRoller>", "</cruiseRollers>",
    ])


def connection_xml(container, element, uid, to_uid, from_point, to_point, free_path=None):
    lines = [f"<{container}>", f'    <{element} uID="{uid}">', f"        <toControlSurfaceUID>{to_uid}</toControlSurfaceUID>",
             indent(material_xml(), 2)]
    for tag, point in (("fromAttachment", from_point), ("toAttachment", to_point)):
        lines += [f"        <{tag}>", indent(relative_point_xml("position", *point), 3), indent(material_xml(), 3),
                  f"        </{tag}>"]
    if free_path is not None:
        lines += ["        <freePath>", f"            <positive>{free_path:g}</positive>",
                  f"            <negative>{free_path:g}</negative>", "        </freePath>"]
    lines += [f"    </{element}>", f"</{container}>"]
    return "\n".join(lines)


def mechanism_device_xml(tag, device, border_xml, extras, translations=True):
    """A control surface with its mechanism; the parts follow the deflection path in the schema order."""
    body = device_xml(tag, device, border_xml, translations).splitlines()
    return "\n".join(body[:-1] + [indent(extra, 1) for extra in extras] + body[-1:])


def control_surfaces_xml():
    """The flaps with their tracks and the parts between them, and the spoiler with its track and actuator."""
    from controlSurface import variant_flap_border_xml
    tracks = []
    for index, eta in enumerate(FLAP_TRACK_ETAS, start=1):
        joints = flap_track_joints(eta)
        frame = xz_frame(eta, flap_xsi(eta))
        tracks.append(track_xml(f"{FLAP['uid']}_track{index}", eta, 3, 1, joints, frame,
                                (FLAP["steps"][0][0], FLAP["steps"][-1][0]), ("strut1", "strut2"),
                                actuator_uid=FLAP_ACTUATOR_UID))
    spoiler_frame = xz_frame(SPOILER_TRACK_ETA)
    spoiler_joint = hinge_line_point(SPOILER, spoiler_frame)
    spoiler_track = track_xml(f"{SPOILER['uid']}_track", SPOILER_TRACK_ETA, 1, 1,
                              {"P1": [spoiler_joint, spoiler_joint]}, spoiler_frame,
                              (SPOILER["steps"][0][0], SPOILER["steps"][-1][0]), ("strut1",))
    flap_extras = [
        "<tracks>\n" + "\n".join(indent(track, 1) for track in tracks) + "\n</tracks>",
        cruise_rollers_xml(f"{FLAP['uid']}_cruiseRoller", CRUISE_ROLLER_ETA, 0.68, 0.1),
        connection_xml("interconnectionStruts", "interconnectionStrut", f"{FLAP['uid']}_strut", OUTER_FLAP["uid"],
                       (0.37, 0.80, 0.3), (0.41, 0.80, 0.3), free_path=0.004),
        connection_xml("zCouplings", "zCoupling", f"{FLAP['uid']}_zCoupling", OUTER_FLAP["uid"],
                       (0.37, 0.95, 0.5), (0.41, 0.95, 0.5)),
    ]
    spoiler_extras = ["<tracks>\n" + indent(spoiler_track, 1) + "\n</tracks>"]
    outer_extras = [actuators_xml(f"{OUTER_FLAP['uid']}_actuator", ACTUATOR_ETA, ACTUATOR_PARENT, ACTUATOR_SURFACE)]
    return "\n".join([
        "<controlSurfaces>",
        "    <trailingEdgeDevices>",
        indent(mechanism_device_xml("trailingEdgeDevice", FLAP, flap_border_xml, flap_extras), 2),
        indent(mechanism_device_xml("trailingEdgeDevice", OUTER_FLAP,
                                    lambda side: variant_flap_border_xml(side, OUTER_FLAP), outer_extras), 2),
        "    </trailingEdgeDevices>",
        "    <spoilers>",
        indent(mechanism_device_xml("spoiler", SPOILER, spoiler_border_xml, spoiler_extras, translations=False), 2),
        "    </spoilers>",
        "</controlSurfaces>",
    ])


def actuator_library_xml():
    """The actuators that the tracks and the spoiler reference, in the library of system elements."""
    actuators = []
    for uid, name in ((FLAP_ACTUATOR_UID, "Rotary actuator of the flap tracks"),
                      (SURFACE_ACTUATOR_UID, "Actuator of the outer flap")):
        actuators += [f'<hydraulicActuator uID="{uid}">', f"    <name>{name}</name>", "    <geometry>",
                      "        <cylinders>", "            <cylinder>",
                      "                <radius>0.04</radius>", "                <height>0.35</height>",
                      "            </cylinder>", "        </cylinders>", "    </geometry>",
                      "</hydraulicActuator>"]
    return "\n".join([
        "<mechanicalElements>", "    <conversionElements>", "        <hydraulicActuators>",
        *(indent(line, 3) for line in actuators), "        </hydraulicActuators>",
        "    </conversionElements>", "</mechanicalElements>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Control surface tracks",
        description="Two flaps and a spoiler with their tracks, an actuator, a cruise roller, an interconnection "
                    "strut and a z-coupling.",
        model_uid="ControlSurfaceTracksAircraft",
        model_name="Control surface tracks example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml(control_surfaces_xml()))],
        extra_profiles=[("wingAirfoils", airfoil_xml()), ("structuralProfiles", profile_xml())],
        extra_vehicles=[("materials", structural_material_xml()),
                        ("systemElements", actuator_library_xml())],
    )


def figure_actuator():
    """The actuator of the outer flap between its attachment on the wing and its attachment on the flap."""
    device = {**OUTER_FLAP, "borders": {"inner": OUTER_FLAP["borders"]["inner"],
                                        "outer": OUTER_FLAP["borders"]["outer"]}}
    frame, chord, upper, lower, flap, _ = flap_section(device)
    eta = OUTER_FLAP["borders"]["inner"][0]
    chord_le = component_segment_point(eta, 0.0)
    chord_te = component_segment_point(eta, 1.0)
    full = np.linalg.norm(chord_te - chord_le)
    le_offset = frame.to2d(chord_le)[0][0]

    def on_wing(xsi, height):
        """parentXsi and parentHeight of the parent attachment: on the chord of the component segment."""
        a = le_offset + xsi * full
        low, high = skin_at(lower, a), skin_at(upper, a)
        return np.array([a, low + height * (high - low)])

    def on_flap(xsi, height):
        """The same values for the attachment on the control surface: on the chord of the control surface."""
        nose, length = flap[:, 0].min(), flap[:, 0].max() - flap[:, 0].min()
        a = nose + xsi * length
        near = flap[(flap[:, 0] > a - 0.04) & (flap[:, 0] < a + 0.04)]
        return np.array([a, near[:, 1].min() + height * (near[:, 1].max() - near[:, 1].min())])

    parent, surface = on_wing(*ACTUATOR_PARENT), on_flap(*ACTUATOR_SURFACE)
    left, right = -1.3, chord + 0.3
    with figure_style():
        fig, (ax,) = section_axes([((left, right), (-0.26, 0.3))])
        draw_wing_section(ax, upper, lower, (left, right))
        draw_device(ax, flap, alpha=0.12)
        ax.plot(*np.array([parent, surface]).T, color=INK, lw=2.2, solid_capstyle="round", zorder=4.5)
        for point, content, offset, ha in ((parent, f"parentAttachment:\nparentXsi {ACTUATOR_PARENT[0]:g}, "
                                            f"parentHeight {ACTUATOR_PARENT[1]:g}", (-GAP, GAP), "right"),
                                           (surface, f"controlSurfaceAttachment:\nparentXsi "
                                            f"{ACTUATOR_SURFACE[0]:g}, parentHeight {ACTUATOR_SURFACE[1]:g}",
                                            (GAP, -GAP - 4), "left")):
            point_marker(ax, point)
            text(ax, point, content, offset, ha=ha, va="bottom" if offset[1] > 0 else "top")
        panel_title(ax, "Actuator of a control surface that is not placed within a track", left)
        legend(fig, [handle_line(MUTED, LINE["secondary"]), handle_line(DEVICE_COLOR, LINE["data"]),
                     handle_line(INK, 2.2), handle_point()],
               ["wing section", "control surface", "actuator", "attachment"])
        save_figure(fig, FIGURES / "controlSurfaceActuator.png")


# ------------------------------------------------------------------------ main
def excerpt_track_xml():
    """The first track of the flap, with the joint positions shortened to the first two joints."""
    eta = FLAP_TRACK_ETAS[0]
    joints = flap_track_joints(eta)
    short = {name: joints[name] for name in ("P1", "P2")}
    track = track_xml(f"{FLAP['uid']}_track1", eta, 3, 1, short, xz_frame(eta, flap_xsi(eta)),
                      (FLAP["steps"][0][0],), ("strut1", "strut2"), actuator_uid=FLAP_ACTUATOR_UID)
    lines = []
    for line in track.splitlines():
        lines.append(line)
        if line.strip() == "</jointPosition>" and lines[-2].strip() == "</jointCoordinates>" and                 sum(1 for l in lines if l.strip() == "</jointPosition>") == 2:
            lines.append(" " * 12 + "...")
    return "\n".join(lines)


def report():
    """What the construction of the joint coordinates guarantees, checked on the data that is written."""
    for index, eta in enumerate(FLAP_TRACK_ETAS, start=1):
        joints = flap_track_joints(eta)
        lengths = [np.linalg.norm(joints["P2"][i] - joints["P3"][i]) for i in (0, 1)]
        direction = joints["P6"][0] - joints["P5"][0]
        offsets = [np.linalg.norm(np.cross(direction, joints["P4"][i] - joints["P5"][0])) / np.linalg.norm(direction)
                   for i in (0, 1)]
        print(f"track {index} at eta {eta:g}: strut1 (P2-P3) {lengths[0]:.6f} m and {lengths[1]:.6f} m, "
              f"difference {abs(lengths[0] - lengths[1]):.1e} m; "
              f"P4 off the track P5-P6 by {max(offsets):.1e} m")
    frame = xz_frame(SPOILER_TRACK_ETA)
    joint = hinge_line_point(SPOILER, frame)
    moved = max(np.linalg.norm(deflect(joint, SPOILER, parameter)[0] - joint) for parameter in (0.0, 0.5, 1.0))
    print(f"spoiler track at eta {SPOILER_TRACK_ETA:g}: P1 moves by {moved:.1e} m over the deflection")


def main():
    figure_track_types()
    figure_actuator()
    write_example()
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}\n")
    report()
    print("\nExcerpt for controlSurfaceTrackTypeType:\n")
    print(excerpt_track_xml())


if __name__ == "__main__":
    main()

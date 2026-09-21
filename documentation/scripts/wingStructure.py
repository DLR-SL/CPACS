# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the documentation of the structure of a wing: the spars
(wingSparType, sparPositionsType, sparPositionType, sparSegmentsType, sparSegmentType,
sparCrossSectionType, capType, webType, sparCellsType, sparCellType) and the ribs
(wingRibsDefinitionsType, wingRibsDefinitionType, wingRibsPositioningType,
wingRibExplicitPositioningType, ribRotationType, wingRibCrossSectionType, wingRibCellType).

Run from the repository root:

    uv run documentation/scripts/wingStructure.py

The script writes the figures listed in main() and the example file examples/wingStructure.xml, and
prints the excerpts shown in the documentation. The wing and its component segment are defined in
wing.py, the relative coordinates of the component segment in componentSegment.py.

Definitions shown (as in the documentation):
  spar position: a point of the chord surface of the component segment, given in eta/xsi, on a rib or
      on another spar; eta = 0 and eta = 1 put the point on the inner and the outer section element;
  spar: the surface through the spar positions of a spar segment, bounded by the wing; between two
      consecutive positions it is plane;
  eta on a spar: relative arc length along the spar mid line, the line of the spar on the chord
      surface, from the first to the last spar position;
  rotation: the angle between the chord surface and web1, measured about the spar axis in the
      direction of increasing eta; 90 degrees puts web1 perpendicular to the chord surface;
  rib set: its ribs sit on a reference line (an edge of the wing or a spar), spaced by a number of
      ribs or by a distance along that line, the first rib at the start of the set;
  rib: a plane through the point on the reference line, turned by the angle z about the normal of
      the chord surface from the direction given by the rotation reference and tilted by the angle x
      against the chord surface, bounded by the spars or edges named in ribStart and ribEnd.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from componentSegment import (CHORD, GAP, SERIES1, SERIES2, WASH, axes_mark, component_segment_point, edge_text, edges, element_etas,
                              element_labels, handle_line, handle_point, legend, line, make_figure, outline, planform,
                              point_marker, segment_point, text, to_component_segment, to_segment, view)
from controlSurface import (CONTOURS, Frame, LE_INDEX, draw_wing_section, midplane_normal,
                            panel_title, section_axes)
from example_xml import indent, write_cpacs_file
from figure_style import COLORS, FULL_WIDTH, LINE, figure_style, leader, save_figure
from structuralProfile import ELEMENT_UID, MATERIAL_UID, element_xml as structural_element_xml, material_xml, profile_xml
from wing import (AIRFOIL, DOCUMENTATION, FIGURES, INK, INK2, MUTED, NOTE, WING_UID, airfoil_xml,
                  circle_profile_xml,
                  fuselage_xml, wing_xml)

EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "wingStructure.xml"
CS_UID = f"{WING_UID}_componentSegment"
STRUCTURE_UID = f"{CS_UID}_structure"

SPAR = SERIES2  # spars in the figures; the chords of the elements stay in series 1
RIB = SERIES3 = COLORS["series3"]  # ribs
CELL = COLORS["series1"]  # cells and stringers of a shell

# --------------------------------------------------------------- example data
# Spar positions: uID suffix -> (eta, xsi, segment). segment None means the coordinates of the
# component segment; a segment number means the coordinates of that segment of the wing. The front
# spar bends at the kink of the wing, which is the outer element of segment 1: given in the
# coordinates of that segment the position is exact, without the rounded eta of the component
# segment (ETA_KINK).
ETA_KINK = float(element_etas()[0][1])

POSITIONS = {
    "frontSpar_root": (0.0, 0.15, None),
    "frontSpar_kink": (1.0, 0.20, 1),
    "frontSpar_tip": (1.0, 0.25, None),
    "rearSpar_root": (0.0, 0.65, None),
    "rearSpar_kink": (1.0, 0.66, 1),
    "rearSpar_tip": (1.0, 0.70, None),
    "auxSpar_outer": (0.25, 0.80, None),
}

# Spars: uID suffix -> name, the spar positions it runs through and its cross section.
# A cross section is (upper cap area, lower cap area, relPos of web1, relPos of web2 or None) [m^2, -].
SPARS = {
    "frontSpar": {
        "name": "Front spar",
        "positions": ["frontSpar_root", "frontSpar_kink", "frontSpar_tip"],
        "cross_section": (0.0024, 0.0024, 0.5, None),
        "web_thickness": 0.004,
        "cap_thickness": 0.006,
    },
    "rearSpar": {
        "name": "Rear spar",
        "positions": ["rearSpar_root", "rearSpar_kink", "rearSpar_tip"],
        "cross_section": (0.0018, 0.0018, 0.0, 1.0),
        "web_thickness": 0.003,
        "cap_thickness": 0.005,
        # A spar cell with a thicker web over the inner part of the spar; its borders are eta of the spar.
        "cell": {"from": 0.0, "to": 0.45, "web_thickness": 0.006},
    },
    "auxSpar": {
        "name": "Auxiliary spar",
        "positions": ["rearSpar_root", "auxSpar_outer"],
        "cross_section": (None, None, 0.5, None),
        "web_thickness": 0.003,
        "cap_thickness": None,
    },
}

# Ribs: uID suffix -> name, where the rib or the rib set starts and ends, what bounds it forward and
# aft, how many ribs there are and how they are turned. A set has a reference line ("reference") on
# which its ribs are spaced; a definition without one is a single rib. The start and the end are
# given as ("sparPosition", uID suffix), ("curve", (spar uID suffix, eta)) or ("etaXsi", (eta, xsi)).
# rotation is (reference of the zero angle or None, angle z [deg]).
RIBS = {
    "innerRibs": {
        "name": "Inner ribs",
        # the set ends before the kink, where the kink rib stands
        "start": ("sparPosition", "rearSpar_root"), "end": ("curve", ("rearSpar", 0.35)),
        "ribStart": "frontSpar", "ribEnd": "rearSpar",
        "count": ("spacing", 0.8), "reference": "rearSpar", "crossing": "cross",
        "rotation": ("globalX", 0.0),  # the ribs of the inner wing run in flight direction
        "thickness": 0.003, "cap_area": 0.0008, "cap_thickness": 0.004, "x_rotation": None,
        # the first three ribs carry the landing gear and have stronger caps
        "cell": {"from": 1, "to": 3, "thickness": 0.005, "cap_area": 0.0016},
    },
    "outerRibs": {
        "name": "Outer ribs",
        # the set ends short of the tip, where a rib perpendicular to the rear spar would reach past
        # the end of the front spar; the point is given on the rear spar itself
        "start": ("curve", ("rearSpar", 0.47)), "end": ("curve", ("rearSpar", 0.95)),
        "ribStart": "frontSpar", "ribEnd": "rearSpar",
        "count": ("numberOfRibs", 8), "reference": "rearSpar", "crossing": "cross",
        "rotation": ("rearSpar", 90.0),  # perpendicular to the rear spar
        "thickness": 0.0025, "cap_area": 0.0006, "cap_thickness": 0.003, "x_rotation": None,
    },
    "kinkRib": {
        "name": "Kink rib",
        "start": ("sparPosition", "frontSpar_kink"), "end": ("sparPosition", "rearSpar_kink"),
        "ribStart": "frontSpar", "ribEnd": "rearSpar",
        "thickness": 0.005, "cap_area": 0.0020, "cap_thickness": 0.006, "x_rotation": 90.0,
    },
}

# Shells: the skin of the upper and the lower side of the wing, its stringers and its cells.
# A stringer is given either by a pitch, a reference point it runs through and an angle, or
# explicitly by a number of stringers that fan out between four chordwise borders.
# A cell is bounded by four borders; each of them is given as ("spar", uID suffix),
# ("rib", (uID suffix, rib number)), ("xsi", (inner, outer)), ("eta", (at the leading edge, at the
# trailing edge)) or ("contour", value).
SHELLS = {
    "upperShell": {
        "skin_thickness": 0.003,
        "stringer": {"pitch": 0.18, "refPoint": (0.2, 0.35, 1.0), "angle": 8.0},
        "cells": {
            "upperPanel": {
                "skin_thickness": 0.005,
                "stringer": {"pitch": 0.12, "refPoint": (0.2, 0.35, 1.0), "angle": 8.0},
                "leadingEdge": ("spar", "frontSpar"), "trailingEdge": ("spar", "rearSpar"),
                "innerBorder": ("rib", ("innerRibs", 3)), "outerBorder": ("rib", ("innerRibs", 6)),
            },
            "outerPanel": {
                "skin_thickness": 0.002,
                "leadingEdge": ("xsi", (0.30, 0.34)), "trailingEdge": ("xsi", (0.58, 0.62)),
                "innerBorder": ("eta", (0.60, 0.62)), "outerBorder": ("eta", (0.84, 0.86)),
            },
        },
    },
    "lowerShell": {
        "skin_thickness": 0.0035,
        "stringer": {"numberOfStringers": 6, "angle": 8.0,
                     # in the order of the schema: the two leading edge borders, then the two at the trailing edge
                     "borders": {"innerBorderXsiLE": 0.22, "outerBorderXsiLE": 0.28,
                                 "innerBorderXsiTE": 0.62, "outerBorderXsiTE": 0.66}},
        "cells": {
            "accessPanel": {
                "skin_thickness": 0.004,
                # the borders of this cell run along the skin itself, not on the chord surface
                "leadingEdge": ("contour", 0.30), "trailingEdge": ("contour", 0.52),
                "innerBorder": ("contour", 0.24), "outerBorder": ("contour", 0.33),
            },
        },
    },
}

# The filling between the two shells and the cut-outs of the wing, both bounded like a cell of a
# shell. They sit at the same place along the span, so that one section shows both.
INTERMEDIATE = {
    "outerBay": {
        "leadingEdge": ("spar", "frontSpar"), "trailingEdge": ("spar", "rearSpar"),
        "innerBorder": ("rib", ("outerRibs", 2)), "outerBorder": ("rib", ("outerRibs", 5)),
        "thickness": 0.02, "rotX": 0.0, "rotZ": 8.0,
    },
}

CUT_OUTS = {
    "inspectionOpening": {
        "leadingEdge": ("xsi", (0.40, 0.40)), "trailingEdge": ("xsi", (0.55, 0.55)),
        "innerBorder": ("eta", (0.60, 0.60)), "outerBorder": ("eta", (0.66, 0.66)),
        "sides": "lower",
    },
}

# Station and rotation of the illustrative cross section; the values are not in the example file.
SECTION_ETA = 0.25
SECTION_ROTATION = 70.0


# ---------------------------------------------------------------------- XML
def material_definition_xml(thickness):
    return "\n".join([
        "<material>", f"    <materialUID>{MATERIAL_UID}</materialUID>", f"    <thickness>{thickness:g}</thickness>",
        "</material>",
    ])


def cap_xml(tag, uid, area, thickness):
    return "\n".join([
        f'<{tag} uID="{uid}">', f"    <area>{area:g}</area>", indent(material_definition_xml(thickness), 1),
        f"</{tag}>",
    ])


def web_xml(tag, thickness, rel_pos):
    return "\n".join([
        f"<{tag}>", indent(material_definition_xml(thickness), 1), f"    <relPos>{rel_pos:g}</relPos>", f"</{tag}>",
    ])


def eta_iso_line_xml(tag, eta, reference):
    return "\n".join([
        f"<{tag}>", f"    <eta>{eta:g}</eta>", f"    <referenceUID>{reference}</referenceUID>", f"</{tag}>",
    ])


def spar_cells_xml(uid, spar):
    cell = spar["cell"]
    return "\n".join([
        "<sparCells>", f'    <sparCell uID="{WING_UID}_{uid}_innerCell">',
        indent(eta_iso_line_xml("fromEta", cell["from"], f"{WING_UID}_{uid}"), 2),
        indent(eta_iso_line_xml("toEta", cell["to"], f"{WING_UID}_{uid}"), 2),
        indent(web_xml("web1", cell["web_thickness"], spar["cross_section"][2]), 2),
        "        <rotation>90</rotation>", "    </sparCell>", "</sparCells>",
    ])


def cross_section_xml(uid, spar):
    upper_area, lower_area, rel_pos1, rel_pos2 = spar["cross_section"]
    parts = ["<sparCrossSection>"]
    for tag, area in (("upperCap", upper_area), ("lowerCap", lower_area)):
        if area is not None:
            parts.append(indent(cap_xml(tag, f"{WING_UID}_{uid}_{tag}", area, spar["cap_thickness"]), 1))
    parts.append(indent(web_xml("web1", spar["web_thickness"], rel_pos1), 1))
    if rel_pos2 is not None:
        parts.append(indent(web_xml("web2", spar["web_thickness"], rel_pos2), 1))
    if "cell" in spar:
        parts.append(indent(spar_cells_xml(uid, spar), 1))
    parts += ["    <rotation>90</rotation>", "</sparCrossSection>"]
    return "\n".join(parts)


def reference_uid(segment):
    return CS_UID if segment is None else f"{WING_UID}_segment{segment}"


def spar_position_xml(uid):
    eta, xsi, segment = POSITIONS[uid]
    return "\n".join([
        f'<sparPosition uID="{WING_UID}_{uid}">', "    <sparPositionEtaXsi>", f"        <eta>{eta:g}</eta>",
        f"        <xsi>{xsi:g}</xsi>", f"        <referenceUID>{reference_uid(segment)}</referenceUID>",
        "    </sparPositionEtaXsi>", "</sparPosition>",
    ])


def spar_segment_xml(uid, spar):
    uids = "\n".join(f"        <sparPositionUID>{WING_UID}_{p}</sparPositionUID>" for p in spar["positions"])
    return "\n".join([
        f'<sparSegment uID="{WING_UID}_{uid}">', f"    <name>{spar['name']}</name>", "    <sparPositionUIDs>", uids,
        "    </sparPositionUIDs>", indent(cross_section_xml(uid, spar), 1), "</sparSegment>",
    ])


def spars_xml():
    positions = "\n".join(indent(spar_position_xml(uid), 1) for uid in POSITIONS)
    segments = "\n".join(indent(spar_segment_xml(uid, spar), 1) for uid, spar in SPARS.items())
    return "\n".join([
        "<spars>", "    <sparPositions>", indent(positions, 1), "    </sparPositions>", "    <sparSegments>",
        indent(segments, 1), "    </sparSegments>", "</spars>",
    ])


def stringer_xml(stringer):
    """A stringer definition: either by pitch, reference point and angle, or explicitly."""
    lines = ["<stringer>", f"    <stringerStructureUID>{ELEMENT_UID}</stringerStructureUID>"]
    if "pitch" in stringer:
        eta, xsi, height = stringer["refPoint"]
        lines += [f"    <pitch>{stringer['pitch']:g}</pitch>", "    <refPoint>", f"        <eta>{eta:g}</eta>",
                  f"        <xsi>{xsi:g}</xsi>", f"        <relHeight>{height:g}</relHeight>",
                  f"        <referenceUID>{CS_UID}</referenceUID>", "    </refPoint>",
                  f"    <angle>{stringer['angle']:g}</angle>"]
    else:
        lines.append(f"    <numberOfStringers>{stringer['numberOfStringers']}</numberOfStringers>")
        lines.append(f"    <angle>{stringer['angle']:g}</angle>")
        for tag, xsi in stringer["borders"].items():
            lines += [f"    <{tag}>", f"        <xsi>{xsi:g}</xsi>", f"        <referenceUID>{CS_UID}</referenceUID>",
                      f"    </{tag}>"]
    lines.append("</stringer>")
    return "\n".join(lines)


def cell_border_xml(tag, border):
    """One of the four borders of a cell."""
    kind, value = border
    if kind == "spar":
        return f"<{tag}>\n    <sparUID>{WING_UID}_{value}</sparUID>\n</{tag}>"
    if kind == "rib":
        ribs, number = value
        return "\n".join([f"<{tag}>", f"    <ribNumber>{number}</ribNumber>",
                           f"    <ribDefinitionUID>{WING_UID}_{ribs}</ribDefinitionUID>", f"</{tag}>"])
    if kind == "xsi":
        inner, outer = value
        return f"<{tag}>\n    <xsi1>{inner:g}</xsi1>\n    <xsi2>{outer:g}</xsi2>\n</{tag}>"
    if kind == "eta":
        front, rear = value
        return "\n".join([f"<{tag}>",
                           indent(eta_iso_line_xml("eta1", front, CS_UID), 1),
                           indent(eta_iso_line_xml("eta2", rear, CS_UID), 1), f"</{tag}>"])
    return f"<{tag}>\n    <contourCoordinate>{value:g}</contourCoordinate>\n</{tag}>"


def skin_xml(thickness):
    return "\n".join(["<skin>", indent(material_definition_xml(thickness), 1), "</skin>"])


def cell_xml(uid, cell):
    parts = [f'<cell uID="{WING_UID}_{uid}">', indent(skin_xml(cell["skin_thickness"]), 1)]
    if "stringer" in cell:
        parts.append(indent(stringer_xml(cell["stringer"]), 1))
    for tag, key in (("positioningLeadingEdge", "leadingEdge"), ("positioningTrailingEdge", "trailingEdge"),
                     ("positioningInnerBorder", "innerBorder"), ("positioningOuterBorder", "outerBorder")):
        parts.append(indent(cell_border_xml(tag, cell[key]), 1))
    parts.append("</cell>")
    return "\n".join(parts)


def shell_xml(tag):
    shell = SHELLS[tag]
    parts = [f'<{tag} uID="{STRUCTURE_UID}_{tag}">', indent(skin_xml(shell["skin_thickness"]), 1),
             indent(stringer_xml(shell["stringer"]), 1)]
    if shell["cells"]:
        parts.append("    <cells>")
        parts += [indent(cell_xml(uid, cell), 2) for uid, cell in shell["cells"].items()]
        parts.append("    </cells>")
    parts.append(f"</{tag}>")
    return "\n".join(parts)


def cap_pair_xml(uid, area, thickness):
    return "\n".join([cap_xml("upperCap", f"{uid}_upperCap", area, thickness),
                      cap_xml("lowerCap", f"{uid}_lowerCap", area, thickness)])


def rib_cell_xml(uid, ribs):
    cell = ribs["cell"]
    return "\n".join([
        f'<ribCell uID="{WING_UID}_{uid}_cell">', f"    <fromRib>{cell['from']}</fromRib>",
        f"    <toRib>{cell['to']}</toRib>", "    <ribRotation>", "        <x>90</x>", "    </ribRotation>",
        indent(material_definition_xml(cell["thickness"]), 1),
        indent(cap_pair_xml(f"{WING_UID}_{uid}_cell", cell["cap_area"], ribs["cap_thickness"]), 1), "</ribCell>",
    ])


def rib_cross_section_xml(uid, ribs):
    parts = ["<ribCrossSection>", indent(material_definition_xml(ribs["thickness"]), 1)]
    if ribs.get("x_rotation") is not None:
        parts += ["    <ribRotation>", f"        <x>{ribs['x_rotation']:g}</x>", "    </ribRotation>"]
    if "cell" in ribs:
        parts.append(indent(rib_cell_xml(uid, ribs), 1))
    parts.append(indent(cap_pair_xml(f"{WING_UID}_{uid}", ribs["cap_area"], ribs["cap_thickness"]), 1))
    parts.append("</ribCrossSection>")
    return "\n".join(parts)


def rib_end_xml(tag, end):
    """Start or end of a rib or of a rib set: a spar position, a point on a curve or an eta/xsi point."""
    kind, value = end
    if kind == "sparPosition":
        return f"<{tag}SparPositionUID>{WING_UID}_{value}</{tag}SparPositionUID>"
    if kind == "curve":
        curve, eta = value
        return "\n".join([f"<{tag}CurvePoint>", f"    <eta>{eta:g}</eta>",
                          f"    <referenceUID>{WING_UID}_{curve}</referenceUID>", f"</{tag}CurvePoint>"])
    eta, xsi = value
    return "\n".join([f"<{tag}EtaXsiPoint>", f"    <eta>{eta:g}</eta>", f"    <xsi>{xsi:g}</xsi>",
                      f"    <referenceUID>{CS_UID}</referenceUID>", f"</{tag}EtaXsiPoint>"])


RIB_KEYWORDS = ("leadingEdge", "trailingEdge", "globalX", "globalY")


def rib_reference(name):
    """A rib reference, start, end or rotation reference: a spar of the example or one of the keywords."""
    return name if name in RIB_KEYWORDS else f"{WING_UID}_{name}"


def ribs_positioning_xml(ribs):
    reference, angle = ribs["rotation"]
    count = (f"    <spacing>{ribs['count'][1]:g}</spacing>" if ribs["count"][0] == "spacing"
             else f"    <numberOfRibs>{ribs['count'][1]}</numberOfRibs>")
    return "\n".join([
        "<ribsPositioning>", indent(rib_end_xml("start", ribs["start"]), 1), indent(rib_end_xml("end", ribs["end"]), 1),
        f"    <ribStart>{rib_reference(ribs['ribStart'])}</ribStart>",
        f"    <ribEnd>{rib_reference(ribs['ribEnd'])}</ribEnd>", count,
        f"    <ribReference>{rib_reference(ribs['reference'])}</ribReference>",
        f"    <ribCrossingBehaviour>{ribs['crossing']}</ribCrossingBehaviour>", "    <ribRotation>",
        *([f"        <ribRotationReference>{rib_reference(reference)}</ribRotationReference>"] if reference else []),
        f"        <z>{angle:g}</z>", "    </ribRotation>", "</ribsPositioning>",
    ])


def rib_explicit_positioning_xml(ribs):
    return "\n".join([
        "<ribExplicitPositioning>", indent(rib_end_xml("start", ribs["start"]), 1),
        indent(rib_end_xml("end", ribs["end"]), 1),
        f"    <ribStart>{rib_reference(ribs['ribStart'])}</ribStart>",
        f"    <ribEnd>{rib_reference(ribs['ribEnd'])}</ribEnd>", "</ribExplicitPositioning>",
    ])


def ribs_definition_xml(uid, ribs):
    positioning = ribs_positioning_xml(ribs) if "reference" in ribs else rib_explicit_positioning_xml(ribs)
    return "\n".join([
        f'<ribsDefinition uID="{WING_UID}_{uid}">', f"    <name>{ribs['name']}</name>", indent(positioning, 1),
        indent(rib_cross_section_xml(uid, ribs), 1), "</ribsDefinition>",
    ])


def ribs_definitions_xml():
    return "\n".join([
        "<ribsDefinitions>",
        *(indent(ribs_definition_xml(uid, ribs), 1) for uid, ribs in RIBS.items()),
        "</ribsDefinitions>",
    ])


def intermediate_structure_xml():
    parts = ["<intermediateStructure>"]
    for uid, cell in INTERMEDIATE.items():
        parts.append(f'    <cell uID="{WING_UID}_{uid}">')
        for tag, key in (("positioningLeadingEdge", "leadingEdge"), ("positioningTrailingEdge", "trailingEdge"),
                         ("positioningInnerBorder", "innerBorder"), ("positioningOuterBorder", "outerBorder")):
            parts.append(indent(cell_border_xml(tag, cell[key]), 2))
        parts.append(indent(material_definition_xml(cell["thickness"]), 2))
        parts += [f"        <rotX>{cell['rotX']:g}</rotX>", f"        <rotZ>{cell['rotZ']:g}</rotZ>", "    </cell>"]
    parts.append("</intermediateStructure>")
    return "\n".join(parts)


def wing_cut_outs_xml():
    parts = ["<wingCutOuts>"]
    for uid, cut_out in CUT_OUTS.items():
        parts.append(f'    <cutOut uID="{WING_UID}_{uid}">')
        for tag, key in (("positioningLeadingEdge", "leadingEdge"), ("positioningTrailingEdge", "trailingEdge"),
                         ("positioningInnerBorder", "innerBorder"), ("positioningOuterBorder", "outerBorder")):
            parts.append(indent(cell_border_xml(tag, cut_out[key]), 2))
        parts += [f"        <cutOutSides>{cut_out['sides']}</cutOutSides>", "    </cutOut>"]
    parts.append("</wingCutOuts>")
    return "\n".join(parts)


def structure_xml():
    return "\n".join([
        "<structure>", indent(shell_xml("upperShell"), 1), indent(shell_xml("lowerShell"), 1),
        indent(intermediate_structure_xml(), 1), indent(ribs_definitions_xml(), 1), indent(spars_xml(), 1),
        indent(wing_cut_outs_xml(), 1), "</structure>",
    ])


def write_example():
    write_cpacs_file(
        EXAMPLE_FILE,
        generator=Path(__file__),
        name="Wing structure",
        description="The structure of a wing: spars and ribs of its component segment, the skin of the upper and "
                    "the lower side with their stringers and cells, a filling between the two shells and a cut-out "
                    "in the lower one.",
        model_uid="WingStructureAircraft",
        model_name="Wing structure example",
        components_tag="fuselages",
        components=fuselage_xml(),
        profiles_tag="fuselageProfiles",
        profiles=circle_profile_xml(),
        extra_components=[("wings", wing_xml(structure=structure_xml()))],
        extra_profiles=[("wingAirfoils", airfoil_xml()), ("structuralProfiles", profile_xml())],
        extra_vehicles=[("structuralElements", "<profileBasedStructuralElements>\n"
                         + indent(structural_element_xml(), 1) + "\n</profileBasedStructuralElements>"),
                        ("materials", material_xml())],
    )


def excerpt_spars():
    """The front spar with its positions and its cross section, for the wingSparType documentation."""
    positions = "\n".join(indent(spar_position_xml(uid), 1) for uid in SPARS["frontSpar"]["positions"])
    return "\n".join([
        "<spars>", "    <sparPositions>", indent(positions, 1), "    </sparPositions>", "    <sparSegments>",
        indent(indent(spar_segment_xml("frontSpar", SPARS["frontSpar"]), 1), 1), "    </sparSegments>", "</spars>",
    ])


def excerpt_ribs():
    """The outer rib set with its positioning and its cross section, for the rib documentation."""
    return "\n".join([
        "<ribsDefinitions>", indent(ribs_definition_xml("outerRibs", RIBS["outerRibs"]), 1), "</ribsDefinitions>",
    ])


def excerpt_shell():
    """The upper shell with its skin, its stringers and its first cell, for the documentation."""
    shell = SHELLS["upperShell"]
    uid, cell = next(iter(shell["cells"].items()))
    return "\n".join([
        f'<upperShell uID="{STRUCTURE_UID}_upperShell">', indent(skin_xml(shell["skin_thickness"]), 1),
        indent(stringer_xml(shell["stringer"]), 1), "    <cells>", indent(cell_xml(uid, cell), 2), "        ...",
        "    </cells>", "</upperShell>",
    ])


# ------------------------------------------------------------------ geometry
def position_point(uid):
    eta, xsi, segment = POSITIONS[uid]
    return component_segment_point(eta, xsi) if segment is None else segment_point(segment, eta, xsi)


def position_eta(uid):
    """Eta of a spar position in the coordinates of the component segment."""
    eta, xsi, segment = POSITIONS[uid]
    return eta if segment is None else to_component_segment(segment, eta, xsi)[0]


def spar_points(uid):
    return [position_point(p) for p in SPARS[uid]["positions"]]


def plan_crossing(p0, p1, le, te):
    """Point where the vertical plane through p0 and p1 crosses the chord line of an element."""
    m = np.column_stack([np.asarray(p1[:2]) - np.asarray(p0[:2]), np.asarray(le[:2]) - np.asarray(te[:2])])
    _, s = np.linalg.solve(m, np.asarray(le[:2]) - np.asarray(p0[:2]))
    return np.asarray(le) + s * (np.asarray(te) - np.asarray(le))


def spar_mid_line(uid):
    """The mid line of a spar: its positions and the points where it crosses an element in between."""
    points, etas = spar_points(uid), [position_eta(p) for p in SPARS[uid]["positions"]]
    element_eta = element_etas()[0]
    vertices = [points[0]]
    for (p0, e0), (p1, e1) in zip(zip(points, etas), zip(points[1:], etas[1:])):
        for index, eta in enumerate(element_eta[1:-1], start=1):
            if min(e0, e1) < eta < max(e0, e1):
                vertices.append(plan_crossing(p0, p1, *edges()[index]))
        vertices.append(np.asarray(p1, dtype=float))
    unique = [vertices[0]]
    for v in vertices[1:]:
        if np.linalg.norm(v - unique[-1]) > 1e-9:
            unique.append(v)
    return np.array(unique)


def arc_lengths(vertices):
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(vertices, axis=0), axis=1))])


def line_point(vertices, eta):
    """Point at the relative arc length eta along a polyline, and the direction there."""
    lengths = arc_lengths(vertices)
    target = eta * lengths[-1]
    k = int(np.clip(np.searchsorted(lengths, target, side="right") - 1, 0, len(vertices) - 2))
    direction = vertices[k + 1] - vertices[k]
    return vertices[k] + (target - lengths[k]) / np.linalg.norm(direction) * direction / 1.0, direction / np.linalg.norm(direction)


def line_eta(vertices, point):
    """Relative arc length of a point that lies on the polyline."""
    lengths = arc_lengths(vertices)
    for k, (a, b) in enumerate(zip(vertices[:-1], vertices[1:])):
        d = b - a
        t = float((np.asarray(point) - a) @ d / (d @ d))
        if -1e-9 <= t <= 1 + 1e-9 and np.linalg.norm(a + t * d - point) < 1e-6:
            return float((lengths[k] + t * np.linalg.norm(d)) / lengths[-1])
    raise ValueError("point is not on the line")


def chord_surface_eta(point):
    """Eta of a point of the chord surface in the coordinates of the component segment."""
    return chord_surface_eta_xsi(point)[0]


def chord_surface_eta_xsi(point):
    """Eta and xsi of a point of the chord surface in the coordinates of the component segment."""
    for segment in (1, 2):
        (le0, te0), (le1, te1) = edges()[segment - 1], edges()[segment]
        e, x = 0.5, 0.5
        for _ in range(40):
            inner, outer = (1 - x) * le0 + x * te0, (1 - x) * le1 + x * te1
            residual = ((1 - e) * inner + e * outer - point)[:2]
            d_e = (outer - inner)[:2]
            d_x = ((1 - e) * (te0 - le0) + e * (te1 - le1))[:2]
            step = np.linalg.solve(np.column_stack([d_e, d_x]), -residual)
            e, x = e + step[0], x + step[1]
            if np.linalg.norm(step) < 1e-12:
                break
        if -1e-6 <= e <= 1 + 1e-6:
            return to_component_segment(segment, min(max(e, 0.0), 1.0), x)
    raise ValueError("point is not on the chord surface")


def rib_direction(ribs, point, tangent):
    """Direction of a rib: the zero direction given by the rotation reference, turned by the angle z."""
    reference, angle = ribs["rotation"]
    if reference == "globalX":
        zero = np.array([-1.0, 0.0, 0.0])
        turned = rotation_z(angle) @ zero
    else:
        up = midplane_normal(chord_surface_eta(point))
        zero = tangent if reference else midplane_eta_direction(point)
        turned = rotate_about(zero, up, angle)
    return -turned / np.linalg.norm(turned)


def rotate_about(vector, axis, angle):
    """Rodrigues rotation of a vector about a unit axis by an angle in degrees."""
    a, k = np.radians(angle), axis / np.linalg.norm(axis)
    return vector * np.cos(a) + np.cross(k, vector) * np.sin(a) + k * (k @ vector) * (1 - np.cos(a))


def rotation_z(angle):
    a = np.radians(angle)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


def midplane_eta_direction(point):
    """Direction of growing eta on the chord surface at a point, in the wing coordinate system."""
    eta = chord_surface_eta(point)
    step = 1e-4
    a = component_segment_point(max(eta - step, 0.0), 0.5)
    b = component_segment_point(min(eta + step, 1.0), 0.5)
    return (b - a) / np.linalg.norm(b - a)


def rib_end_eta(ribs, end):
    """Relative arc length on the reference line at which a rib set starts or ends."""
    vertices = spar_mid_line(ribs["reference"])
    kind, value = end
    if kind == "curve":
        return value[1] if value[0] == ribs["reference"] else line_eta(vertices, line_point(spar_mid_line(value[0]), value[1])[0])
    return line_eta(vertices, position_point(value))


def rib_etas(ribs):
    """Relative arc lengths of the ribs of a set on their reference line."""
    vertices = spar_mid_line(ribs["reference"])
    start = rib_end_eta(ribs, ribs["start"])
    end = rib_end_eta(ribs, ribs["end"])
    kind, value = ribs["count"]
    if kind == "numberOfRibs":
        return [start + (end - start) * i / (value - 1) for i in range(value)]
    step = value / arc_lengths(vertices)[-1]
    count = int((arc_lengths(vertices)[-1] * abs(end - start) + 1e-9) / value) + 1
    return [start + step * i for i in range(count)]


def rib_line(ribs, eta=None):
    """A rib from its forward to its aft end, cut at the spars given by ribStart and ribEnd."""
    if "reference" not in ribs:  # a single rib runs from its start point to its end point
        return np.array([position_point(ribs["start"][1]), position_point(ribs["end"][1])])
    vertices = spar_mid_line(ribs["reference"])
    point, tangent = line_point(vertices, eta)
    direction = rib_direction(ribs, point, tangent)
    up = midplane_normal(chord_surface_eta(point))
    normal = np.cross(direction, up)
    forward = intersect_with_spar(point, normal, ribs["ribStart"])
    aft = point if ribs["ribEnd"] == ribs["reference"] else intersect_with_spar(point, normal, ribs["ribEnd"])
    return np.array([forward, aft])


def intersect_with_spar(point, normal, spar):
    """Point where the plane of a rib crosses the mid line of a spar."""
    vertices = spar_mid_line(spar)
    for a, b in zip(vertices[:-1], vertices[1:]):
        da, db = (a - point) @ normal, (b - point) @ normal
        if da == db or not min(da, db) - 1e-9 <= 0.0 <= max(da, db) + 1e-9:
            continue
        return a + da / (da - db) * (b - a)
    raise ValueError(f"the rib does not reach {spar}")


def cell_corner(cell, spanwise, chordwise):
    """A corner of a cell: the point where its spanwise and its chordwise border meet.

    Only the combinations used by the example are built here: a rib border with a spar border,
    where the corner is the end of that rib on that spar, and an eta border with a xsi border.
    """
    span_kind, span_value = cell[spanwise]
    chord_kind, chord_value = cell[chordwise]
    if span_kind == "rib" and chord_kind == "spar":
        ribs_uid, number = span_value
        ribs = RIBS[ribs_uid]
        rib = rib_line(ribs, rib_etas(ribs)[number - 1])
        return rib[0] if chord_value == ribs["ribStart"] else rib[1]
    if span_kind == "eta" and chord_kind == "xsi":
        eta = span_value[0] if chordwise == "leadingEdge" else span_value[1]
        xsi = chord_value[0] if spanwise == "innerBorder" else chord_value[1]
        return component_segment_point(eta, xsi)
    raise ValueError(f"combination {span_kind}/{chord_kind} is not built here")


def cell_outline(cell):
    """The four corners of a cell, in the order leading edge inner, outer, trailing edge outer, inner."""
    return np.array([cell_corner(cell, "innerBorder", "leadingEdge"),
                     cell_corner(cell, "outerBorder", "leadingEdge"),
                     cell_corner(cell, "outerBorder", "trailingEdge"),
                     cell_corner(cell, "innerBorder", "trailingEdge")])


def upper_skin_point(eta, xsi):
    """Point of the upper surface of the wing above the chord surface point (eta, xsi)."""
    segment, e, x = to_segment(eta, xsi)
    upper = AIRFOIL[LE_INDEX:, 0]  # chordwise positions of the upper side of the profile, from 0 to 1
    k = int(np.clip(np.searchsorted(upper, x) - 1, 0, len(upper) - 2))
    s = (x - upper[k]) / (upper[k + 1] - upper[k])
    points = []
    for contour in (CONTOURS[segment - 1], CONTOURS[segment]):
        a, b = contour[LE_INDEX + k], contour[LE_INDEX + k + 1]
        points.append(a + s * (b - a))
    return (1 - e) * points[0] + e * points[1]


def reference_direction():
    """The zero direction of the stringer angle: from the leading edge point of the first element to the last."""
    first, last = edges()[0][0], edges()[-1][0]
    return (last - first) / np.linalg.norm(last - first)


def stringer_path(offset, angle, inside=None, samples=160):
    """One stringer on the upper skin: a straight line in the top view, lifted onto the skin.

    offset is the distance from the reference point, measured perpendicular to the stringer.
    """
    direction = rotation_z(angle) @ reference_direction()
    across = np.array([-direction[1], direction[0], 0.0])
    eta, xsi, _ = SHELLS["upperShell"]["stringer"]["refPoint"]
    start = component_segment_point(eta, xsi) + offset * across
    points = []
    for t in np.linspace(-20.0, 20.0, samples):
        try:
            eta, xsi = chord_surface_eta_xsi(start + t * direction)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if 0.0 <= eta <= 1.0 and 0.0 <= xsi <= 1.0 and (inside is None or inside(eta)):
            points.append(upper_skin_point(eta, xsi))
    return np.array(points)


def section_frame(eta):
    """Plane of a chordwise cut at eta: a along the chord, b along the normal of the chord surface."""
    origin, trailing = component_segment_point(eta, 0.0), component_segment_point(eta, 1.0)
    frame = Frame(origin, trailing - origin, midplane_normal(eta))
    return frame, float(np.linalg.norm(trailing - origin))


def spar_in_plane(uid, frame):
    """Chordwise position where the mid line of the spar crosses the plane of a chordwise section.

    The mid line runs on the chord surface, and a section at constant eta cuts the chord surface
    along a straight line, so the chordwise coordinate of the crossing is all that is needed.
    """
    points = spar_points(uid)
    for p0, p1 in zip(points[:-1], points[1:]):
        d0, d1 = (p0 - frame.origin) @ frame.w, (p1 - frame.origin) @ frame.w
        if d0 == d1 or not min(d0, d1) <= 0.0 <= max(d0, d1):
            continue
        return float(frame.to2d(p0 + d0 / (d0 - d1) * (p1 - p0))[0][0])
    raise ValueError(f"{uid} does not cross the plane")


def web_line(a, rotation, upper, lower):
    """End points of a web through the chord point a, at the given angle to the chord surface."""
    direction = np.array([np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))])
    ends = []
    for side, sign in ((upper, -1.0), (lower, 1.0)):
        t = np.linspace(0.0, sign * 2.0, 400)
        points = np.array([a, 0.0]) + np.outer(t, direction)
        height = np.interp(points[:, 0], side[:, 0], side[:, 1])
        crossing = np.argmax(np.sign(points[:, 1] - height) != np.sign(points[0, 1] - height + 1e-9))
        ends.append(points[max(crossing, 1)])
    return np.array(ends)


# ------------------------------------------------------------------- figures
def callout(ax, at, content, offset, ha, va, color=INK2):
    """Free-standing note with a thin leader to the point it belongs to."""
    ax.annotate(content, xy=at, xytext=offset, textcoords="offset points", ha=ha, va=va, fontsize=NOTE, color=color,
                arrowprops=leader(), annotation_clip=False, zorder=7)


# Where the name of a spar sits: the index of the end point of the part it labels (so that the part
# runs from root to tip and the name is not upside down) and the side it is placed on (True towards
# the leading edge). The auxiliary spar is labelled towards the trailing edge, so that its name keeps
# clear of the rear spar running above it.
SPAR_LABELS = {"frontSpar": (-1, True), "rearSpar": (-1, True), "auxSpar": (1, False)}


def figure_spars():
    """Top view of the example wing with its three spars, their positions and the shared position."""
    with figure_style():
        fig, ax = make_figure((-8.8, 1.3))
        planform(ax)
        outline(ax)
        # the element names sit clear of the trailing edge, which slopes away behind the kink
        element_labels(ax, distance=20)

        for uid, spar in SPARS.items():
            points = spar_points(uid)
            line(ax, points, SPAR, LINE["data"], zorder=4)
            part, up = SPAR_LABELS[uid]
            p, q = view(points[part - 1]), view(points[part])
            edge_text(ax, p, q, 0.5 * (p + q), spar["name"], up=up, rotate=True)

        for uid in POSITIONS:
            point_marker(ax, view(position_point(uid)))

        # the two ways of writing a position, each at the position that uses it in the example
        callout(ax, view(position_point("frontSpar_root")), "η = 0, ξ = 0.15\nin the component segment",
                (-6, 30), "center", "bottom")
        callout(ax, view(position_point("frontSpar_kink")), "η = 1, ξ = 0.2\nin segment 1", (34, 26), "left", "bottom")
        callout(ax, view(position_point("rearSpar_root")), "one position,\ntwo spars", (-14, -10), "right", "top")
        axes_mark(ax)

        legend(fig, [handle_line(CHORD, LINE["data"]), handle_line(SPAR, LINE["data"]), handle_point()],
               ["chord of an element", "spar", "spar position"])
        save_figure(fig, FIGURES / "wingSpars.png")


WEB_DISTANCE = 0.34  # chordwise distance of web2 from web1 in the illustrative cross section [m]


def spacing_bracket(ax, vertices, eta_a, eta_b, label_text, distance=0.42):
    """The distance between two ribs, marked on the reference line where it is measured."""
    a, b = view(line_point(vertices, eta_a)[0]), view(line_point(vertices, eta_b)[0])
    direction = (b - a) / np.linalg.norm(b - a)
    normal = np.array([-direction[1], direction[0]])
    if normal[1] > 0:
        normal = -normal
    p, q = a + distance * normal, b + distance * normal
    ax.plot(*np.array([p, q]).T, color=INK2, lw=LINE["reference"], zorder=6)
    for at in (p, q):  # end ticks, perpendicular to the reference line
        ax.plot(*np.array([at - 0.16 * normal, at + 0.16 * normal]).T, color=INK2, lw=LINE["reference"], zorder=6)
    edge_text(ax, p, q, 0.5 * (p + q), label_text, distance=GAP + 4, up=False, rotate=True, color=INK2)


def band_text(ax, spar, at, content, up=True, distance=GAP, color=INK):
    """A name written along a spar, in the empty band beside it."""
    vertices = spar_mid_line(spar)
    before, after = line_point(vertices, max(at - 0.03, 0.0))[0], line_point(vertices, min(at + 0.03, 1.0))[0]
    edge_text(ax, view(before), view(after), view(line_point(vertices, at)[0]), content, distance=distance, up=up,
              rotate=True, color=color)


def figure_ribs():
    """Top view of the example wing with its two rib sets and the single rib at the kink."""
    with figure_style():
        fig, ax = make_figure((-8.8, 1.3))
        planform(ax)
        outline(ax)
        element_labels(ax, distance=20)

        for uid in SPARS:
            line(ax, spar_points(uid), SPAR, LINE["data"], zorder=3)
        for uid, ribs in RIBS.items():
            lines = [rib_line(ribs, eta) for eta in rib_etas(ribs)] if "reference" in ribs else [rib_line(ribs)]
            for rib in lines:
                line(ax, rib, RIB, LINE["data"], zorder=4)

        # the names stand in the band between the leading edge and the front spar, above their ribs
        for uid, at in (("innerRibs", 0.17), ("kinkRib", 0.41), ("outerRibs", 0.72)):
            band_text(ax, "frontSpar", at, RIBS[uid]["name"])

        # the rear spar carries both rib sets, and the spacing is measured on it
        reference = spar_mid_line("rearSpar")
        band_text(ax, "rearSpar", 0.66, "reference line", up=False, color=INK2)
        etas = rib_etas(RIBS["innerRibs"])
        spacing_bracket(ax, reference, etas[-2], etas[-1], "spacing 0.8 m")

        # start and end of the outer set on the reference line; the legend names them
        for end in ("start", "end"):
            point_marker(ax, view(line_point(reference, rib_end_eta(RIBS["outerRibs"], RIBS["outerRibs"][end]))[0]))
        axes_mark(ax)

        legend(fig, [handle_line(SPAR, LINE["data"]), handle_line(RIB, LINE["data"]), handle_line(CHORD, LINE["data"]),
                     handle_point()],
               ["spar", "rib", "chord of an element", "start and end of a rib set"])
        save_figure(fig, FIGURES / "wingRibs.png")


def figure_cells():
    """Top view of the wing with the two cells of the upper shell and the borders that define them."""
    cells = SHELLS["upperShell"]["cells"]
    with figure_style():
        fig, ax = make_figure((-8.8, 1.3))
        planform(ax)
        outline(ax)
        element_labels(ax, distance=20)

        for uid in SPARS:
            line(ax, spar_points(uid), SPAR, LINE["data"], zorder=3)
        for uid, ribs in RIBS.items():
            for eta in (rib_etas(ribs) if "reference" in ribs else [None]):
                line(ax, rib_line(ribs, eta), RIB, LINE["secondary"], zorder=3)

        corners = {}
        for uid, cell in cells.items():
            corners[uid] = view(cell_outline(cell))
            ax.add_patch(Polygon(corners[uid], closed=True, facecolor=CELL, alpha=0.22, edgecolor="none", zorder=5))
            ax.plot(*np.vstack([corners[uid], corners[uid][:1]]).T, color=CELL, lw=LINE["data"], zorder=6)

        # the name of each cell is written along it; the corners run leading edge inner, outer,
        # trailing edge outer, inner
        for uid, name in (("upperPanel", "Upper panel"), ("outerPanel", "Outer panel")):
            c = corners[uid]
            inner, outer = 0.5 * (c[0] + c[3]), 0.5 * (c[1] + c[2])
            edge_text(ax, inner, outer, 0.5 * (inner + outer), name, distance=0, up=True, rotate=True)

        # what bounds the first cell: two spars and two ribs of the inner set
        c = corners["upperPanel"]
        for a, b, label_text, up in ((c[0], c[1], "front spar", True), (c[3], c[2], "rear spar", False)):
            edge_text(ax, a, b, 0.5 * (a + b), label_text, distance=GAP, up=up, rotate=True, color=INK2)
        text(ax, 0.5 * (c[0] + c[3]), "rib 3", (-GAP, 0), ha="right", color=INK2)
        text(ax, 0.5 * (c[1] + c[2]), "rib 6", (GAP, 0), ha="left", color=INK2)
        axes_mark(ax)

        legend(fig, [handle_line(SPAR, LINE["data"]), handle_line(RIB, LINE["secondary"]),
                     handle_line(CELL, LINE["data"])], ["spar", "rib", "cell of a shell"])
        save_figure(fig, FIGURES / "wingCells.png")


STRINGER_PATCH = (0.10, 0.42)  # the part of the span shown in the figure of the stringers


def figure_stringers():
    """Oblique view of a part of the upper skin with the stringers, their reference direction, angle and pitch."""
    stringer = SHELLS["upperShell"]["stringer"]
    angle, pitch = stringer["angle"], stringer["pitch"]
    eta_a, eta_b = STRINGER_PATCH

    def project(p):
        """Oblique view from ahead and above: span to the right, chord downwards, z upwards."""
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 1] + 0.30 * p[..., 0], p[..., 2] - 0.80 * p[..., 0]]).T

    def inside(eta):
        return eta_a <= eta <= eta_b

    with figure_style():
        fig = plt.figure(figsize=(FULL_WIDTH, 3.6))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))

        # the patch of the upper skin, drawn as its outline
        etas, xsis = np.linspace(eta_a, eta_b, 40), np.linspace(0.0, 1.0, 40)
        leading = np.array([upper_skin_point(eta, 0.0) for eta in etas])
        trailing = np.array([upper_skin_point(eta, 1.0) for eta in etas])
        inner = np.array([upper_skin_point(eta_a, xsi) for xsi in xsis])
        outer = np.array([upper_skin_point(eta_b, xsi) for xsi in xsis])
        ax.add_patch(Polygon(project(np.vstack([leading, outer, trailing[::-1], inner[::-1]])), closed=True,
                             facecolor=SERIES1, alpha=WASH, edgecolor="none", zorder=0))
        for curve in (leading, trailing, inner, outer):
            ax.plot(*project(curve).T, color=MUTED, lw=LINE["reference"], zorder=1)

        # the stringers: one runs through the reference point, the others at the pitch from it
        paths = {}
        for k in range(-14, 15):
            path = stringer_path(pitch * k, angle, inside)
            if len(path) > 1:
                paths[k] = path
                ax.plot(*project(path).T, color=CELL, lw=LINE["secondary"], zorder=2)

        # the reference direction of the angle, from the reference point of the stringers
        reference = reference_direction()
        corner = component_segment_point(*stringer["refPoint"][:2])
        span = 3.6  # length of the drawn reference direction [m]
        ax.plot(*project(np.array([corner, corner + span * reference])).T, color=INK2, lw=LINE["secondary"], zorder=3)
        sector = np.array([corner + 0.82 * span * (rotation_z(a) @ reference) for a in np.linspace(0.0, angle, 40)])
        ax.plot(*project(sector).T, color=INK2, lw=LINE["reference"], zorder=3)
        text(ax, project(corner + span * reference), "reference direction", (GAP, 2), ha="left", va="bottom",
             color=INK2)
        text(ax, project(corner + 0.92 * span * (rotation_z(0.5 * angle) @ reference)), f"angle {angle:g}°",
             (-GAP, -GAP - 2), ha="right", va="top", color=INK2)
        point_marker(ax, project(corner))
        text(ax, project(corner), "refPoint", (-GAP, 0), ha="right", color=INK2)

        # the pitch, measured perpendicular to the stringers
        a, b = paths[2], paths[3]
        i, j = int(0.5 * len(a)), int(0.5 * len(b))
        ax.plot(*project(np.array([a[i], b[j]])).T, color=INK2, lw=LINE["reference"], zorder=4)
        text(ax, project(0.5 * (a[i] + b[j])), "pitch", (GAP, -2), ha="left", va="top", color=INK2)
        text(ax, project(upper_skin_point(eta_a, 0.85)), "upper skin", (-GAP, -GAP), ha="right", va="top",
             color=INK)

        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "wingStringers.png")


SECTION_OF_THE_BOX = 0.63  # spanwise station of the section through the wing box


def figure_structure_section():
    """Section through the wing box: the filling between the shells and a cut-out in the lower skin."""
    frame, chord = section_frame(SECTION_OF_THE_BOX)
    segment = to_segment(SECTION_OF_THE_BOX, 0.0)[0]
    upper, lower = frame.section(segment)
    front, rear = spar_in_plane("frontSpar", frame), spar_in_plane("rearSpar", frame)
    cut_out = CUT_OUTS["inspectionOpening"]
    opening = (chord * cut_out["leadingEdge"][1][0], chord * cut_out["trailingEdge"][1][0])

    def skin(side, a0, a1, color, width):
        part = side[(side[:, 0] >= a0) & (side[:, 0] <= a1)]
        ax.plot(*part.T, color=color, lw=width, zorder=4, solid_capstyle="butt")

    with figure_style():
        fig, (ax,) = section_axes([((-0.3, chord + 0.3), (-0.32, 0.34))])

        # the section of the wing, and the two spars that close the box
        draw_wing_section(ax, upper, lower, (0.0, chord))
        ax.plot([0.0, chord], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=3)
        webs = {}
        for a, name in ((front, "front spar"), (rear, "rear spar")):
            webs[name] = ends = web_line(a, 90.0, upper, lower)
            ax.plot(*ends.T, color=SPAR, lw=LINE["data"], zorder=5)

        # the filling between the shells, between the two spars
        inside = np.linspace(front, rear, 60)
        top = np.interp(inside, upper[:, 0], upper[:, 1])
        bottom = np.interp(inside, lower[:, 0], lower[:, 1])
        ax.add_patch(Polygon(np.vstack([np.column_stack([inside, top]), np.column_stack([inside, bottom])[::-1]]),
                             closed=True, facecolor=MUTED, alpha=0.18, edgecolor="none", zorder=1))
        text(ax, (0.5 * (front + rear), 0.0), "intermediate structure", (0, 14), va="bottom", color=INK)

        # the skins, and the gap that the cut-out leaves in the lower one
        skin(upper, 0.0, chord, CELL, LINE["data"])
        skin(lower, 0.0, opening[0], CELL, LINE["data"])
        skin(lower, opening[1], chord, CELL, LINE["data"])
        for a in opening:
            b = float(np.interp(a, lower[:, 0], lower[:, 1]))
            ax.plot([a, a], [b - 0.03, b + 0.03], color=INK2, lw=LINE["reference"], zorder=6)
        text(ax, (0.5 * sum(opening), float(np.interp(0.5 * sum(opening), lower[:, 0], lower[:, 1]))),
             "cut-out in the lower shell", (0, -GAP), va="top", color=INK)
        text(ax, (0.25 * chord, float(np.interp(0.25 * chord, upper[:, 0], upper[:, 1]))), "upper shell", (0, GAP),
             va="bottom", color=INK2)
        text(ax, webs["front spar"][1], "front spar", (-GAP, -2), ha="right", va="top", color=INK2)
        text(ax, webs["rear spar"][1], "rear spar", (GAP, -2), ha="left", va="top", color=INK2)

        legend(fig, [handle_line(CELL, LINE["data"]), handle_line(SPAR, LINE["data"])], ["skin of a shell", "spar"])
        save_figure(fig, FIGURES / "wingStructureSection.png")


RIB_X_ROTATION = 65.0  # illustrative tilt of the rib plane in the figure of the rotations


def figure_rib_rotation():
    """Oblique view of one rib: (a) the angle z in the chord surface, (b) the angle x against it."""
    eta_a, eta_b, xsi_a, xsi_b = 0.635, 0.725, 0.12, 0.78
    ribs = RIBS["outerRibs"]
    eta = rib_etas(ribs)[3]
    reference = spar_mid_line(ribs["reference"])
    point, tangent = line_point(reference, eta)
    direction = rib_direction(ribs, point, tangent)
    up = midplane_normal(chord_surface_eta(point))
    rib = rib_line(ribs, eta)
    across = np.cross(up, direction)  # in the chord surface, perpendicular to the rib

    def project(p):
        """Oblique view from above and ahead: span to the right, chord to the lower left, z upwards."""
        p = np.asarray(p, dtype=float)
        return np.array([p[..., 1] - 0.50 * p[..., 0], p[..., 2] - 0.32 * p[..., 0]]).T

    def surface(ax):
        quad = [component_segment_point(e, x) for e, x in
                ((eta_a, xsi_a), (eta_a, xsi_b), (eta_b, xsi_b), (eta_b, xsi_a))]
        ax.add_patch(Polygon(project(quad), closed=True, facecolor=SERIES1, alpha=WASH, edgecolor="none", zorder=0))
        ax.plot(*project([*quad, quad[0]]).T, color=MUTED, lw=LINE["reference"], zorder=1)
        return quad

    def draw(ax, points, color, lw=None, zorder=3):
        ax.plot(*project(points).T, color=color, lw=lw or LINE["data"], zorder=zorder, solid_capstyle="round")

    def arc(ax, start, axis, angle, radius, steps=48):
        return np.array([point + radius * rotate_about(start, axis, a) for a in np.linspace(0.0, angle, steps)])

    with figure_style():
        fig, (left, right) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 3.1), gridspec_kw={"wspace": 0.05})

        # (a) the angle z, measured in the chord surface from the reference line to the rib
        surface(left)
        draw(left, [point - 0.8 * tangent, point + 0.8 * tangent], SPAR)
        draw(left, rib, RIB)
        sector = arc(left, tangent, up, ribs["rotation"][1], 0.45)
        left.add_patch(Polygon(project([point, *sector]), closed=True, facecolor=SERIES2, alpha=0.10,
                               edgecolor="none", zorder=1))
        left.plot(*project(sector).T, color=INK2, lw=LINE["reference"], zorder=2)
        text(left, project(point + 1.15 * rotate_about(tangent, up, 0.5 * ribs["rotation"][1])),
             f"z = {ribs['rotation'][1]:g}°", (0, 0), color=INK2)
        text(left, project(point + 0.8 * tangent), "reference line", (GAP, -GAP), ha="left", va="top", color=INK)
        text(left, project(rib[0]), "rib", (-GAP, 0), ha="right", color=INK)
        point_marker(left, project(point))
        left.set_title("(a) the angle z in the chord surface")

        # (b) the angle x, measured from the chord surface to the plane of the rib
        surface(right)
        draw(right, rib, RIB)
        tilted = rotate_about(up, direction, 90.0 - RIB_X_ROTATION)
        height = 0.24
        for base in (rib[0], rib[1]):
            draw(right, [base, base + height * tilted], RIB, lw=LINE["secondary"], zorder=4)
        draw(right, [rib[0] + height * tilted, rib[1] + height * tilted], RIB, lw=LINE["secondary"], zorder=4)
        right.add_patch(Polygon(project([rib[0], rib[1], rib[1] + height * tilted, rib[0] + height * tilted]),
                                closed=True, facecolor=SERIES3, alpha=0.12, edgecolor="none", zorder=2))
        sector = arc(right, -across, direction, -RIB_X_ROTATION, 0.3)
        right.plot(*project(sector).T, color=INK2, lw=LINE["reference"], zorder=3)
        draw(right, [point, point - 0.5 * across], MUTED, lw=LINE["reference"], zorder=3)
        text(right, project(point + 0.42 * rotate_about(-across, direction, -RIB_X_ROTATION / 2)),
             f"x = {RIB_X_ROTATION:g}°", (0, 0), color=INK2)
        text(right, project(0.5 * (rib[0] + rib[1]) + height * tilted), "plane of the rib", (0, GAP), va="bottom",
             color=INK)
        text(right, project(point - 0.5 * across), "chord surface", (0, -GAP), ha="center", va="top", color=INK2)
        point_marker(right, project(point))
        right.set_title("(b) the angle x against the chord surface")

        for ax in (left, right):
            ax.set_aspect("equal")
            ax.set_anchor("N")
            ax.axis("off")
        bottom = min(left.get_ylim()[0], right.get_ylim()[0])
        top = max(left.get_ylim()[1], right.get_ylim()[1])
        for ax in (left, right):
            ax.set_ylim(bottom, top)
        save_figure(fig, FIGURES / "ribRotation.png")


def figure_cross_section():
    """Section through the wing at the spars and the cross section of the rear spar."""
    frame, chord = section_frame(SECTION_ETA)
    segment = to_segment(SECTION_ETA, 0.0)[0]
    upper, lower = frame.section(segment)
    front, rear = spar_in_plane("frontSpar", frame), spar_in_plane("rearSpar", frame)
    limits = ((-0.3, chord + 0.3), (-0.36, 0.40))
    zoom = ((rear - 0.75, rear + 0.95), (-0.34, 0.40))

    def cap(ax, side, a0, a1):
        aa = np.linspace(a0, a1, 40)
        bb = np.interp(aa, side[:, 0], side[:, 1])
        ax.plot(aa, bb, color=SPAR, lw=3.2, solid_capstyle="butt", zorder=6)
        return float(bb[-1])

    with figure_style():
        fig, (ax_a, ax_b) = section_axes([limits, zoom])

        # (a) the section with both spars, web1 perpendicular to the chord surface
        draw_wing_section(ax_a, upper, lower, (0.0, chord))
        ax_a.plot([0.0, chord], [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=3)
        text(ax_a, (chord, 0.0), "chord surface of the\ncomponent segment", (-8, -GAP), ha="right", va="top",
             color=INK2)
        for a, name in ((front, "front spar"), (rear, "rear spar")):
            ends = web_line(a, 90.0, upper, lower)
            ax_a.plot(*ends.T, color=SPAR, lw=LINE["data"], zorder=5)
            point_marker(ax_a, (a, 0.0))
            text(ax_a, (a, ends[0][1]), name, (0, GAP), color=INK)
        text(ax_a, (front, 0.0), "mid line of the spar", (-GAP, -GAP), ha="right", va="top", color=INK2)
        panel_title(ax_a, "(a) section at η = 0.25, both spars with rotation 90°", limits[0][0])

        # (b) the rear spar with caps, two webs and a rotation other than 90 degrees
        draw_wing_section(ax_b, upper, lower, zoom[0])
        ax_b.plot(list(zoom[0]), [0.0, 0.0], color=MUTED, lw=LINE["reference"], zorder=3)
        webs = {}
        for tag, offset in (("web1", 0.0), ("web2", WEB_DISTANCE)):
            ends = webs[tag] = web_line(rear + offset, SECTION_ROTATION, upper, lower)
            ax_b.plot(*ends.T, color=SPAR, lw=LINE["data"], zorder=5)
        text(ax_b, webs["web1"][0], "web1", (-GAP, GAP), ha="right", va="bottom", color=INK)
        text(ax_b, webs["web2"][1], "web2", (GAP, -GAP), ha="left", va="top", color=INK)
        # the caps sit on the skins between the webs; labels to the right above and to the left below,
        # so that they keep clear of the labels of the webs
        for side, tag, index, at, offset, align in ((upper, "upperCap", 0, 1.0, (GAP, 2), ("left", "bottom")),
                                                    (lower, "lowerCap", 1, 0.0, (-GAP, -2), ("right", "top"))):
            a0, a1 = webs["web1"][index][0], webs["web2"][index][0]
            cap(ax_b, side, a0, a1)
            a = a0 + at * (a1 - a0)
            text(ax_b, (a, float(np.interp(a, side[:, 0], side[:, 1]))), tag, offset, ha=align[0], va=align[1],
                 color=INK)
        point_marker(ax_b, (rear, 0.0))

        # The rotation is the angle between the chord surface and web1; it is marked in the wedge above the
        # chord surface, where the section leaves room, and is the same angle as below it.
        radius = 0.13
        angles = np.radians(np.linspace(180.0, 180.0 - SECTION_ROTATION, 60))
        ax_b.plot(rear + radius * np.cos(angles), radius * np.sin(angles), color=INK2, lw=LINE["reference"], zorder=5)
        middle = np.radians(180.0 - 0.5 * SECTION_ROTATION)
        text(ax_b, (rear + 1.75 * radius * np.cos(middle), 1.75 * radius * np.sin(middle)), "rotation", (0, 0),
             ha="center", va="center", color=INK2)
        panel_title(ax_b, f"(b) cross section of the rear spar, rotation {SECTION_ROTATION:g}° (illustrative values)",
                    zoom[0][0])

        legend(fig, [handle_line(SPAR, LINE["data"]), handle_line(MUTED, LINE["reference"]), handle_point()],
               ["spar", "chord surface", "mid line of the spar"])
        save_figure(fig, FIGURES / "sparCrossSection.png")


# ---------------------------------------------------------------------- main
def main():
    figure_spars()
    figure_cross_section()
    figure_ribs()
    figure_rib_rotation()
    figure_cells()
    figure_stringers()
    figure_structure_section()
    write_example()
    print(f"eta of the kink element: {ETA_KINK:.6f}")
    print(f"Written {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    print("\nExcerpt for the wingSparType documentation:\n")
    print(excerpt_spars())
    print("\nExcerpt for the rib documentation:\n")
    print(excerpt_ribs())
    print("\nExcerpt for the shell documentation:\n")
    print(excerpt_shell())
    print("\nExcerpt for the intermediate structure:\n")
    print(intermediate_structure_xml())
    print("\nExcerpt for the cut-outs:\n")
    print(wing_cut_outs_xml())


if __name__ == "__main__":
    main()

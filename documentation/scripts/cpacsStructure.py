# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures for the overview of CPACS (cpacsType, sections 1 and 2).

Run from the repository root:

    uv run documentation/scripts/cpacsStructure.py

The script writes

    documentation/figures/basicPrinciple.png
    documentation/figures/dataHierarchy.png

Definitions shown (as in the documentation):

- basicPrinciple.png: the schema defines the structure of a CPACS dataset and carries the documentation,
  which is generated from it. Tools and users write and read the dataset; an XML processor validates the
  dataset against the schema.
- dataHierarchy.png: the top levels of the data structure. The element names are read from
  schema/cpacs_schema.xsd; the script only assigns them to groups and fails if the schema has an element that
  belongs to no group, so that the figure cannot fall behind the schema unnoticed.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon

from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "documentation" / "figures"
SCHEMA = ROOT / "schema" / "cpacs_schema.xsd"
XSD = "{http://www.w3.org/2001/XMLSchema}"

INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
PLATE = COLORS["surface"]
NOTE = FONT_SIZE["annotation"]
MONO = "DejaVu Sans Mono"

# Groups of the data hierarchy. Every child element of the listed types is assigned to exactly one group;
# SKIPPED lists the children that every model has and that the figure leaves out.
VEHICLE_INSTANCES = ["aircraft", "rotorcraft"]
LIBRARY = ["engines", "profiles", "structuralElements", "deckElements", "systemElements", "materials",
           "energyCarriers", "performanceCases", "flightPoints"]
COMPONENTS = ["fuselages", "wings", "ducts", "engines", "enginePylons", "landingGears", "fuelTanks", "systems",
              "genericGeometryComponents"]
MODEL_DATA = ["reference", "configurationDefinitions", "global", "analyses", "performanceRequirements",
              "systemArchitectures"]
SKIPPED = ["name", "description"]

GROUP_COLORS = {"components": COLORS["series1"], "model data": COLORS["series2"], "library": COLORS["series3"]}


def children(type_name):
    """Names of the child elements of a complex type of the schema, in schema order."""
    schema = ET.parse(SCHEMA).getroot()
    for complex_type in schema.findall(f"{XSD}complexType"):
        if complex_type.get("name") == type_name:
            return [element.get("name") for element in complex_type.iter(f"{XSD}element")]
    raise KeyError(type_name)


def assigned(names, groups):
    """Check that every name is in exactly one of the groups."""
    for name in names:
        hits = [group for group in groups if name in group]
        assert len(hits) == 1, f"{name} is assigned to {len(hits)} groups; update the groups in this script"
    for group in groups:
        for name in group:
            assert name in names, f"{name} is no longer a child in the schema; update the groups in this script"


def box(ax, x, y, w, h, color, fill=0.10, lw=None, zorder=2):
    ax.add_patch(FancyBboxPatch((x, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.04",
                                lw=lw or LINE["secondary"], ec=color, fc=(color, fill) if fill else PLATE,
                                zorder=zorder))


def connector(ax, points, zorder=1):
    ax.plot(*zip(*points), color=MUTED, lw=LINE["reference"], zorder=zorder, solid_capstyle="butt",
            solid_joinstyle="miter")


def flow_arrow(ax, points, text=None, text_at=None, ha="center", va="center"):
    """Orthogonal arrow along the points, with an optional label in secondary ink."""
    if len(points) > 2:
        connector(ax, points[:-1], zorder=1)
    ax.annotate("", xy=points[-1], xytext=points[-2], zorder=1, arrowprops={
        "arrowstyle": "-|>", "lw": LINE["reference"], "mutation_scale": 8, "shrinkA": 0, "shrinkB": 0,
        "color": MUTED})
    if text:
        ax.text(*text_at, text, ha=ha, va=va, fontsize=NOTE, color=INK2, linespacing=1.3, zorder=3)


# Symbols of the boxes in the middle row, drawn as line glyphs in a square of side 1 centred at the origin.
# Right half of an airliner in top view, nose up: fuselage, swept wing, horizontal tail.
AIRLINER_HALF = [(0.0, 0.5), (0.035, 0.45), (0.05, 0.36), (0.05, 0.1), (0.47, -0.15), (0.47, -0.22), (0.05, -0.08),
                 (0.05, -0.3), (0.19, -0.41), (0.19, -0.46), (0.035, -0.43), (0.0, -0.49)]


def symbol_schema(ax, center, size, color):
    """A sheet with a folded corner, carrying a small tree: the schema as a hierarchy."""
    cx, cy = center
    w, h, fold = 0.66 * size, 0.86 * size, 0.2 * size
    x0, y0 = cx - w / 2, cy - h / 2
    outline = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h - fold), (x0 + w - fold, y0 + h), (x0, y0 + h)]
    ax.add_patch(Polygon(outline, closed=True, lw=LINE["secondary"], ec=color, fc=PLATE, joinstyle="round",
                         zorder=4))
    ax.plot([x0 + w - fold, x0 + w - fold, x0 + w], [y0 + h, y0 + h - fold, y0 + h - fold], color=color,
            lw=LINE["secondary"], solid_joinstyle="round", zorder=4)
    # tree: a root and two children, connected by an elbow
    root = (x0 + 0.22 * w, y0 + 0.66 * h)
    children = [(x0 + 0.62 * w, y0 + 0.45 * h), (x0 + 0.62 * w, y0 + 0.2 * h)]
    ax.plot([root[0], root[0]], [root[1], children[-1][1]], color=color, lw=LINE["reference"], zorder=4)
    for child in children:
        ax.plot([root[0], child[0]], [child[1], child[1]], color=color, lw=LINE["reference"], zorder=4)
    for node in [root, *children]:
        ax.plot(*node, ls="none", marker="s", ms=2.6, mfc=color, mec=color, zorder=5)


def symbol_aircraft(ax, center, size, color):
    """An airliner in top view, nose up, drawn like the components in the other figures."""
    half = np.array(AIRLINER_HALF)
    outline = np.vstack([half, (half * [-1.0, 1.0])[::-1]]) * size + np.asarray(center)
    ax.add_patch(Polygon(outline, closed=True, lw=LINE["secondary"], ec=color, fc=(color, 0.10),
                         joinstyle="round", zorder=4))


def symbol_users(ax, center, size, color, back_color):
    """Two busts, the one behind lighter: tools and their users."""
    def bust(cx, cy, edge, zorder):
        head = Circle((cx, cy + 0.2 * size), 0.15 * size, lw=LINE["secondary"], ec=edge, fc=PLATE, zorder=zorder)
        t = np.linspace(0.0, np.pi, 40)
        shoulders = np.column_stack([cx + 0.3 * size * np.cos(t), cy - 0.36 * size + 0.36 * size * np.sin(t)])
        ax.add_patch(Polygon(shoulders, closed=True, lw=LINE["secondary"], ec=edge, fc=PLATE, joinstyle="round",
                             zorder=zorder))
        ax.add_patch(head)
    cx, cy = center
    bust(cx + 0.17 * size, cy + 0.08 * size, back_color, 4)
    bust(cx - 0.1 * size, cy - 0.04 * size, color, 4.5)


def figure_basic_principle():
    """The schema, the dataset, the documentation, the tools and the XML processor, and how they relate.

    The middle row, which the figure is about, carries a symbol in each box; the documentation and the XML
    processor are context and have none.
    """
    width, height = FULL_WIDTH, 3.25
    w, h = 1.85, 0.62
    cols = {"schema": 0.12, "dataset": 2.875, "tools": 5.63}
    mid = {key: x + w / 2 for key, x in cols.items()}
    row_top, row_mid, row_bottom = 2.85, 1.6, 0.36
    symbol_size, symbol_inset, text_inset = 0.36, 0.3, 0.56

    nodes = {
        "documentation": (mid["dataset"] - w / 2, row_top, MUTED, "documentation", "HTML pages", None),
        "schema": (cols["schema"], row_mid, COLORS["series1"], "cpacs_schema.xsd", "XML schema", "schema"),
        "dataset": (cols["dataset"], row_mid, COLORS["series1"], "aircraft.xml", "CPACS dataset", "aircraft"),
        "tools": (cols["tools"], row_mid, MUTED, "tools and users", "design and analysis", "users"),
        "processor": (mid["dataset"] - w / 2, row_bottom, MUTED, "XML processor", "e.g. TiXI or xmllint", None),
    }
    with figure_style():
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        for x, y, color, title, note, symbol in nodes.values():
            box(ax, x, y, w, h, color)
            family = MONO if title.endswith((".xsd", ".xml")) else None
            if symbol is None:
                text_x, ha = x + w / 2, "center"
            else:
                text_x, ha = x + text_inset, "left"
                at = (x + symbol_inset, y)
                if symbol == "schema":
                    symbol_schema(ax, at, symbol_size, color)
                elif symbol == "aircraft":
                    symbol_aircraft(ax, at, symbol_size, color)
                else:
                    symbol_users(ax, at, symbol_size, INK2, MUTED)
            ax.text(text_x, y + 0.1, title, ha=ha, va="center", fontsize=FONT_SIZE["base"], color=INK,
                    family=family, zorder=3)
            ax.text(text_x, y - 0.12, note, ha=ha, va="center", fontsize=NOTE, color=INK2, zorder=3)

        left, right = mid["schema"], mid["tools"]
        # schema -> documentation and documentation -> tools along the top row
        flow_arrow(ax, [(left, row_mid + h / 2), (left, row_top), (mid["dataset"] - w / 2, row_top)],
                   "generates", (left + 0.12, row_top + 0.12), ha="left", va="bottom")
        flow_arrow(ax, [(mid["dataset"] + w / 2, row_top), (right, row_top), (right, row_mid + h / 2)],
                   "describes the data", (right - 0.12, row_top + 0.12), ha="right", va="bottom")
        # schema -> dataset, tools -> dataset
        flow_arrow(ax, [(cols["schema"] + w, row_mid), (cols["dataset"], row_mid)], "defines the\nstructure",
                   ((cols["schema"] + w + cols["dataset"]) / 2, row_mid + 0.08), va="bottom")
        flow_arrow(ax, [(cols["tools"], row_mid), (cols["dataset"] + w, row_mid)], "write and\nread data",
                   ((cols["tools"] + cols["dataset"] + w) / 2, row_mid + 0.08), va="bottom")
        # schema and dataset -> XML processor
        flow_arrow(ax, [(left, row_mid - h / 2), (left, row_bottom), (mid["dataset"] - w / 2, row_bottom)],
                   "schema", (left + 0.12, row_bottom + 0.1), ha="left", va="bottom")
        flow_arrow(ax, [(mid["dataset"], row_mid - h / 2), (mid["dataset"], row_bottom + h / 2)], "dataset",
                   (mid["dataset"] + 0.1, (row_mid + row_bottom) / 2), ha="left")
        ax.text(mid["dataset"] + w / 2 + 0.15, row_bottom, "checks that the dataset\nfollows the schema",
                ha="left", va="center", fontsize=NOTE, color=INK2, linespacing=1.3)

        ax.set_xlim(0.0, width)
        ax.set_ylim(0.0, height)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "basicPrinciple.png")


def figure_data_hierarchy():
    """The top levels of the data structure as a tree from left to right, the groups framed."""
    root_children = children("cpacsType")
    vehicle_children = children("vehiclesType")
    model_children = children("aircraftModelType")
    assigned(vehicle_children, [VEHICLE_INSTANCES, LIBRARY])
    assigned(model_children, [COMPONENTS, MODEL_DATA, SKIPPED])

    row, h = 0.215, 0.17  # row pitch and box height [in]
    pad, title_h = 0.07, 0.24  # frame padding and room for the title of a group [in]
    x_root, w_root = 0.0, 0.62
    x_top, w_top = 0.82, 0.98
    x_veh, w_veh = 2.15, 1.62
    x_model, w_model = 3.97, 0.72
    x_group, w_group = 5.1, 1.84

    def element(ax, x, y, w, name, color=MUTED):
        box(ax, x, y, w, h, color, fill=None, lw=LINE["reference"])
        ax.text(x + 0.07, y, name, ha="left", va="center", fontsize=NOTE - 0.5, color=INK, family=MONO, zorder=3)

    def frame(ax, x, top, w, n, color, title):
        """Group frame with its title above the first element; returns the y of the first element."""
        bottom = top - title_h - n * row - pad + (row - h) / 2
        ax.add_patch(FancyBboxPatch((x - pad, bottom), w + 2 * pad, top - bottom,
                                    boxstyle="round,pad=0,rounding_size=0.06", lw=LINE["secondary"], ec=color,
                                    fc=(color, 0.08), zorder=0))
        ax.text(x - pad + 0.08, top - 0.05, title, ha="left", va="top", fontsize=NOTE, color=INK, zorder=3)
        return top - title_h - row / 2

    with figure_style():
        n_rows = len(COMPONENTS) + len(MODEL_DATA) + 4
        height = n_rows * row + 2 * title_h + 0.3
        fig = plt.figure(figsize=(FULL_WIDTH, height))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        y0 = height - 0.15 - h / 2

        # model of an aircraft: components and model data, in two frames
        y_comp = frame(ax, x_group, height - 0.05, w_group, len(COMPONENTS), GROUP_COLORS["components"],
                       "components (geometry)")
        y_model = y0 - row * 1.5
        comp_rows = [y_comp - k * row for k in range(len(COMPONENTS))]
        data_top = comp_rows[-1] - h / 2 - pad - 0.12
        y_data = frame(ax, x_group, data_top, w_group, len(MODEL_DATA), GROUP_COLORS["model data"],
                       "model data and analyses")
        data_rows = [y_data - k * row for k in range(len(MODEL_DATA))]

        # vehicles: the vehicle instances, and the library below them
        y_vehicles = y_model
        y_aircraft = y_model
        y_rotorcraft = y_aircraft - row
        lib_top = y_rotorcraft - h / 2 - 0.25
        y_lib = frame(ax, x_veh, lib_top, w_veh, len(LIBRARY), GROUP_COLORS["library"],
                      "library, referenced by uID")
        lib_rows = [y_lib - k * row for k in range(len(LIBRARY))]

        # root and its children: header above vehicles, the rest below the library
        rest = [name for name in root_children if name not in ("header", "vehicles")]
        y_header = y_vehicles + row
        rest_rows = [lib_rows[-1] - h / 2 - pad - 0.2 - k * row for k in range(len(rest))]
        top_rows = {"header": y_header, "vehicles": y_vehicles, **dict(zip(rest, rest_rows, strict=True))}

        element(ax, x_root, y_header, w_root, "cpacs", INK2)
        trunk = x_root + w_root + 0.1
        connector(ax, [(x_root + w_root, y_header), (trunk, y_header)])
        connector(ax, [(trunk, y_header), (trunk, min(top_rows.values()))])
        for name in root_children:
            y = top_rows[name]
            connector(ax, [(trunk, y), (x_top, y)])
            element(ax, x_top, y, w_top, name)

        vtrunk = x_top + w_top + 0.1
        veh_rows = {"aircraft": y_aircraft, "rotorcraft": y_rotorcraft}
        connector(ax, [(x_top + w_top, y_vehicles), (vtrunk, y_vehicles)])
        connector(ax, [(vtrunk, y_vehicles), (vtrunk, lib_rows[-1])])
        for name in VEHICLE_INSTANCES:
            connector(ax, [(vtrunk, veh_rows[name]), (x_veh, veh_rows[name])])
            element(ax, x_veh, veh_rows[name], w_veh, name)
        for name, y in zip(LIBRARY, lib_rows, strict=True):
            connector(ax, [(vtrunk, y), (x_veh, y)], zorder=0.5)
            element(ax, x_veh, y, w_veh, name)

        connector(ax, [(x_veh + w_veh, y_aircraft), (x_model, y_aircraft)])
        element(ax, x_model, y_aircraft, w_model, "model")
        ax.text(x_model + w_model / 2, y_aircraft + h / 2 + 0.03, "1..n", ha="center", va="bottom",
                fontsize=NOTE - 1.0, color=INK2)
        mtrunk = x_model + w_model + 0.12
        connector(ax, [(x_model + w_model, y_aircraft), (mtrunk, y_aircraft)])
        connector(ax, [(mtrunk, comp_rows[0]), (mtrunk, data_rows[-1])])
        for group, rows, color in ((COMPONENTS, comp_rows, GROUP_COLORS["components"]),
                                   (MODEL_DATA, data_rows, GROUP_COLORS["model data"])):
            for name, y in zip(group, rows, strict=True):
                connector(ax, [(mtrunk, y), (x_group, y)], zorder=0.5)
                element(ax, x_group, y, w_group, name)

        ax.set_xlim(0.0, FULL_WIDTH)
        bottom = min(*rest_rows, data_rows[-1]) - h / 2 - pad - 0.05
        ax.set_ylim(bottom, height)
        fig.set_size_inches(FULL_WIDTH, height - bottom)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "dataHierarchy.png")


def main():
    figure_basic_principle()
    figure_data_hierarchy()


if __name__ == "__main__":
    main()

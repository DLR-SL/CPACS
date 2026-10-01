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
    documentation/figures/datasetAccess.png
    documentation/figures/toolInterfaces.png

Definitions shown (as in the documentation):

- datasetAccess.png: a dataset is read and written by hand in an editor with XML support, or automated in the
  pre- and post-processing of the tools of a process chain.
- toolInterfaces.png: n tools exchanging data directly need up to n(n - 1)/2 interfaces, one per pair;
  through a common format each tool needs one.
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


def symbol_documentation(ax, center, size, color):
    """A browser window with a title bar and lines of text: the documentation as HTML pages."""
    cx, cy = center
    w, h, bar = 0.9 * size, 0.72 * size, 0.18 * size
    x0, y0 = cx - w / 2, cy - h / 2
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={0.06 * size}",
                                lw=LINE["secondary"], ec=color, fc=PLATE, zorder=4))
    ax.plot([x0, x0 + w], [y0 + h - bar, y0 + h - bar], color=color, lw=LINE["reference"], zorder=4.1)
    for k in range(3):
        ax.plot(x0 + (0.1 + 0.11 * k) * w, y0 + h - bar / 2, ls="none", marker="o", ms=1.1, mfc=color, mec=color,
                zorder=4.2)
    for k, length in enumerate((0.7, 0.55, 0.62)):
        y = y0 + h - bar - (0.2 + 0.2 * k) * h
        ax.plot([x0 + 0.14 * w, x0 + (0.14 + length) * w], [y, y], color=color, lw=LINE["reference"],
                solid_capstyle="round", zorder=4.1)


def symbol_validation(ax, center, size, color):
    """A circle with a check mark: the XML processor confirms that the dataset follows the schema."""
    cx, cy = center
    ax.add_patch(Circle((cx, cy), 0.34 * size, lw=LINE["secondary"], ec=color, fc=PLATE, zorder=4))
    check = np.array([(-0.15, 0.0), (-0.045, -0.115), (0.16, 0.11)]) * size + np.asarray(center)
    ax.plot(*check.T, color=color, lw=LINE["secondary"] * 1.3, solid_capstyle="round", solid_joinstyle="round",
            zorder=4.1)


def figure_basic_principle():
    """The schema, the dataset, the documentation, the tools and the XML processor, and how they relate.

    Each box carries a symbol: the schema and the dataset, which the figure is about, in series 1, the
    documentation, the tools and users and the XML processor as context in secondary ink.
    """
    width, height = FULL_WIDTH, 3.25
    w, h = 1.85, 0.62
    cols = {"schema": 0.12, "dataset": 2.875, "tools": 5.63}
    mid = {key: x + w / 2 for key, x in cols.items()}
    row_top, row_mid, row_bottom = 2.85, 1.6, 0.36
    symbol_size, symbol_inset, text_inset = 0.36, 0.3, 0.56

    nodes = {
        "documentation": (mid["dataset"] - w / 2, row_top, MUTED, "documentation", "HTML pages", "documentation"),
        "schema": (cols["schema"], row_mid, COLORS["series1"], "cpacs_schema.xsd", "XML schema", "schema"),
        "dataset": (cols["dataset"], row_mid, COLORS["series1"], "aircraft.xml", "CPACS dataset", "aircraft"),
        "tools": (cols["tools"], row_mid, MUTED, "tools and users", "design and analysis", "users"),
        "processor": (mid["dataset"] - w / 2, row_bottom, MUTED, "XML processor", "e.g. TiXI or xmllint",
                      "validation"),
    }
    with figure_style():
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        for x, y, color, title, note, symbol in nodes.values():
            box(ax, x, y, w, h, color)
            family = MONO if title.endswith((".xsd", ".xml")) else None
            text_x, ha = x + text_inset, "left"
            at = (x + symbol_inset, y)
            if symbol == "schema":
                symbol_schema(ax, at, symbol_size, color)
            elif symbol == "aircraft":
                symbol_aircraft(ax, at, symbol_size, color)
            elif symbol == "users":
                symbol_users(ax, at, symbol_size, INK2, MUTED)
            elif symbol == "documentation":
                symbol_documentation(ax, at, symbol_size, INK2)
            else:
                symbol_validation(ax, at, symbol_size, INK2)
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


# Tools of the interface figure, one per discipline, placed on a circle starting at the top
TOOLS = ["aerodynamics", "structures", "flight mechanics", "propulsion", "mission analysis", "overall design"]


def figure_tool_interfaces():
    """Interfaces between n tools: (a) direct exchange, one per pair; (b) through a common format, one per tool.

    The numbers in the captions are computed from the list of tools.
    """
    n = len(TOOLS)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    assert len(pairs) == n * (n - 1) // 2
    radius, w, h = 1.12, 1.18, 0.3
    hub_w, hub_h = 1.34, 0.52
    panel_w, height = FULL_WIDTH / 2, 3.25
    centre_y = 1.45
    angles = np.radians(90.0 - 360.0 / n * np.arange(n))
    interface = COLORS["series2"]

    def tools(ax, cx):
        points = [(cx + radius * 1.05 * np.cos(a), centre_y + radius * np.sin(a)) for a in angles]
        for (x, y), name in zip(points, TOOLS, strict=True):
            box(ax, x - w / 2, y, w, h, MUTED, zorder=3)
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.04",
                                        lw=0, fc=PLATE, zorder=2.9))
            ax.text(x, y, name, ha="center", va="center", fontsize=NOTE, color=INK, zorder=4)
        return points

    def caption(ax, x, title, count):
        ax.text(x, height - 0.05, title, ha="left", va="top", fontsize=FONT_SIZE["base"], color=INK)
        ax.text(x, height - 0.27, count, ha="left", va="top", fontsize=NOTE, color=INK2)

    with figure_style():
        fig = plt.figure(figsize=(FULL_WIDTH, height))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        # (a) every pair of tools has an interface of its own
        cx = panel_w / 2
        points = tools(ax, cx)
        for i, j in pairs:
            ax.plot(*zip(points[i], points[j]), color=interface, lw=LINE["secondary"], zorder=1,
                    solid_capstyle="butt")
        caption(ax, 0.05, "(a) direct exchange between the tools",
                f"{len(pairs)} interfaces for {n} tools, one per pair")
        # (b) each tool has one interface, to the common dataset
        cx = panel_w + panel_w / 2
        points = tools(ax, cx)
        for x, y in points:
            ax.plot([cx, x], [centre_y, y], color=interface, lw=LINE["secondary"], zorder=1, solid_capstyle="butt")
        box(ax, cx - hub_w / 2, centre_y, hub_w, hub_h, COLORS["series1"], zorder=3)
        ax.add_patch(FancyBboxPatch((cx - hub_w / 2, centre_y - hub_h / 2), hub_w, hub_h,
                                    boxstyle="round,pad=0,rounding_size=0.04", lw=0, fc=PLATE, zorder=2.9))
        symbol_aircraft(ax, (cx - hub_w / 2 + 0.26, centre_y), 0.32, COLORS["series1"])
        ax.text(cx - hub_w / 2 + 0.5, centre_y + 0.08, "CPACS", ha="left", va="center",
                fontsize=FONT_SIZE["base"], color=INK, zorder=4)
        ax.text(cx - hub_w / 2 + 0.5, centre_y - 0.11, "dataset", ha="left", va="center", fontsize=NOTE,
                color=INK2, zorder=4)
        caption(ax, panel_w + 0.15, "(b) exchange through a common format",
                f"{n} interfaces for {n} tools, one per tool")
        ax.set_xlim(0.0, FULL_WIDTH)
        ax.set_ylim(0.0, height)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "toolInterfaces.png")


# The dataset written in the editor of figure (a): (indent level, text, folded). The cursor follows the last line.
EDITOR_LINES = [(0, "<cpacs>", False), (1, "<header>…</header>", True), (1, "<vehicles>", False),
                (2, "<aircraft>", False), (3, '<model uID="aircraft">', False),
                (4, "<name>Short-range airliner</name>", False), (4, "<wings>…</wings>", True)]
EDITOR_USED = ["name", "wings"]  # children of the model written so far
EDITOR_SUGGESTIONS = 5  # number of suggestions shown


def figure_dataset_access():
    """(a) Writing a dataset by hand in an editor with XML support; (b) reading and writing automated in a tool.

    The suggestions of the editor are the children of aircraftModelType that are not written yet, read from the
    schema; the model is an xsd:all group, so each of them is allowed at the cursor.
    """
    width, height = FULL_WIDTH, 5.6
    mono = {"family": MONO, "fontsize": NOTE - 1.0}
    pitch, char = 0.165, 0.0625  # line pitch and width of a character of the code font [in]
    leader_props = {"arrowstyle": "-", "color": MUTED, "lw": LINE["reference"], "shrinkA": 3, "shrinkB": 2}

    def note(ax, xy_text, xy_target, text):
        ax.annotate(text, xy=xy_target, xytext=xy_text, ha="left", va="center", fontsize=NOTE, color=INK2,
                    linespacing=1.3, arrowprops=leader_props, zorder=8)

    suggestions = sorted(name for name in children("aircraftModelType") if name not in EDITOR_USED)
    shown = suggestions[:EDITOR_SUGGESTIONS]

    with figure_style():
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))

        # ---- (a) editor window ----
        top = height - 0.42
        x0, w = 0.15, 3.3
        title_h, status_h, gutter = 0.24, 0.24, 0.42
        code_h = (len(EDITOR_LINES) + 1) * pitch + EDITOR_SUGGESTIONS * pitch + 0.28
        h = title_h + code_h + status_h
        bottom = top - h
        ax.text(0.0, height - 0.05, "(a) by hand, in an editor with XML support", ha="left", va="top",
                fontsize=FONT_SIZE["base"], color=INK)
        ax.add_patch(FancyBboxPatch((x0, bottom), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                    lw=LINE["secondary"], ec=MUTED, fc=PLATE, zorder=1))
        ax.plot([x0, x0 + w], [top - title_h] * 2, color=MUTED, lw=LINE["reference"], zorder=2)
        ax.plot([x0, x0 + w], [bottom + status_h] * 2, color=MUTED, lw=LINE["reference"], zorder=2)
        ax.plot([x0 + gutter] * 2, [bottom + status_h, top - title_h], color=COLORS["grid"], lw=LINE["reference"],
                zorder=2)
        for k in range(3):
            ax.plot(x0 + 0.13 + 0.1 * k, top - title_h / 2, ls="none", marker="o", ms=2.6, mfc=COLORS["axis"],
                    mec=COLORS["axis"], zorder=3)
        ax.text(x0 + w / 2, top - title_h / 2, "aircraft.xml", ha="center", va="center", color=INK, zorder=3,
                **{**mono, "fontsize": NOTE - 0.5})
        code_x = x0 + gutter + 0.1
        first = top - title_h - 0.12 - pitch / 2
        fold_y = None
        for n, (level, line, folded) in enumerate(EDITOR_LINES):
            y = first - n * pitch
            ax.text(x0 + gutter - 0.2, y, f"{n + 1}", ha="right", va="center", color=COLORS["axis"], zorder=3,
                    **mono)
            opens = n + 1 < len(EDITOR_LINES) and EDITOR_LINES[n + 1][0] > level
            if folded or opens:
                ax.plot(x0 + gutter - 0.09, y, ls="none", marker=">" if folded else "v", ms=3.2, mfc=MUTED,
                        mec=MUTED, zorder=3)
            if folded:
                fold_y = y
            ax.text(code_x + 2 * level * char, y, line, ha="left", va="center", color=INK, zorder=3, **mono)
        # the cursor, one level below the model, and the suggestions of the editor below it
        n = len(EDITOR_LINES)
        y_cursor = first - n * pitch
        ax.text(x0 + gutter - 0.2, y_cursor, f"{n + 1}", ha="right", va="center", color=COLORS["axis"], zorder=3,
                **mono)
        cursor_x = code_x + 2 * 4 * char
        ax.text(cursor_x, y_cursor, "<", ha="left", va="center", color=INK, zorder=3, **mono)
        ax.plot([cursor_x + char + 0.01] * 2, [y_cursor - 0.06, y_cursor + 0.06], color=INK, lw=0.8, zorder=3)
        pop_w, pop_h = 1.75, EDITOR_SUGGESTIONS * pitch + 0.08
        pop_x, pop_top = cursor_x, y_cursor - pitch / 2 - 0.03
        ax.add_patch(FancyBboxPatch((pop_x, pop_top - pop_h), pop_w, pop_h,
                                    boxstyle="round,pad=0,rounding_size=0.03", lw=LINE["reference"], ec=MUTED,
                                    fc=PLATE, zorder=4))
        ax.add_patch(FancyBboxPatch((pop_x + 0.03, pop_top - 0.04 - pitch), pop_w - 0.06, pitch,
                                    boxstyle="round,pad=0,rounding_size=0.02", lw=0,
                                    fc=(COLORS["series1"], 0.16), zorder=4.1))
        for k, name in enumerate(shown):
            ax.text(pop_x + 0.1, pop_top - 0.04 - (k + 0.5) * pitch, name, ha="left", va="center", color=INK,
                    zorder=5, **mono)
        # status bar: the dataset follows the schema
        y_status = bottom + status_h / 2
        symbol_validation(ax, (x0 + 0.17, y_status), 0.2, COLORS["series3"])
        ax.text(x0 + 0.32, y_status, "valid against cpacs_schema.xsd", ha="left", va="center",
                fontsize=NOTE - 1.0, color=INK2, zorder=3)
        # notes, aligned to a common left edge
        nx = x0 + w + 0.32
        note(ax, (nx, fold_y), (code_x + 2 * 4 * char + 1.08, fold_y), "hierarchy indented,\nparts folded")
        note(ax, (nx, pop_top - pop_h / 2), (pop_x + pop_w, pop_top - pop_h / 2),
             "elements the schema\nallows at the cursor")
        note(ax, (nx, y_status), (x0 + 2.1, y_status), "checked against the schema\nwhile writing")

        # ---- (b) process chain ----
        y_b = bottom - 0.42
        ax.text(0.0, y_b, "(b) automated, in a process chain", ha="left", va="top", fontsize=FONT_SIZE["base"],
                color=INK)
        row = y_b - 1.0
        bw, bh = 1.12, 0.5
        ds_x, ds_w = 0.15, 1.25
        steps = [("pre-processing", "reads the part\nit needs"), ("analysis code", "own input\nand output"),
                 ("post-processing", "writes the\nresults back")]
        sx = [ds_x + 1.6 + k * (bw + 0.3) for k in range(3)]
        # the tool frame, with two more tools of the chain behind it
        fx0, fx1 = sx[0] - 0.12, sx[-1] + bw + 0.12
        fy0, fy1 = row - bh / 2 - 0.12, row + bh / 2 + 0.3
        for k in (2, 1):
            off = 0.07 * k
            ax.add_patch(FancyBboxPatch((fx0 + off, fy0 + off), fx1 - fx0, fy1 - fy0,
                                        boxstyle="round,pad=0,rounding_size=0.06", lw=LINE["reference"], ec=MUTED,
                                        fc=PLATE, zorder=0.5 - 0.1 * k))
        ax.add_patch(FancyBboxPatch((fx0, fy0), fx1 - fx0, fy1 - fy0, boxstyle="round,pad=0,rounding_size=0.06",
                                    lw=LINE["secondary"], ec=MUTED, fc=PLATE, zorder=0.6))
        ax.text(fx0 + 0.1, fy1 - 0.07, "tool of the chain, e.g. aerodynamics", ha="left", va="top",
                fontsize=NOTE, color=INK, zorder=3)
        ax.text(fx1 + 0.3, fy1 + 0.1, "further tools\nof the chain", ha="left", va="top", fontsize=NOTE,
                color=INK2, linespacing=1.3)
        for x, (title, sub) in zip(sx, steps, strict=True):
            color = MUTED if title == "analysis code" else COLORS["series3"]
            box(ax, x, row, bw, bh, color, zorder=2)
            ax.text(x + bw / 2, row + 0.1, title, ha="center", va="center", fontsize=NOTE, color=INK, zorder=3)
            ax.text(x + bw / 2, row - 0.11, sub, ha="center", va="center", fontsize=NOTE - 1.0, color=INK2,
                    linespacing=1.15, zorder=3)
        for a, b in zip(sx[:-1], sx[1:], strict=True):
            flow_arrow(ax, [(a + bw, row), (b, row)])
        # the dataset, read before and written after the tool
        box(ax, ds_x, row, ds_w, bh + 0.08, COLORS["series1"], zorder=2)
        symbol_aircraft(ax, (ds_x + 0.25, row), 0.3, COLORS["series1"])
        ax.text(ds_x + 0.48, row + 0.09, "CPACS", ha="left", va="center", fontsize=FONT_SIZE["base"], color=INK,
                zorder=3)
        ax.text(ds_x + 0.48, row - 0.11, "dataset", ha="left", va="center", fontsize=NOTE, color=INK2, zorder=3)
        flow_arrow(ax, [(ds_x + ds_w, row), (sx[0], row)])
        y_back = fy0 - 0.25
        flow_arrow(ax, [(sx[-1] + bw / 2, fy0), (sx[-1] + bw / 2, y_back), (ds_x + ds_w / 2, y_back),
                        (ds_x + ds_w / 2, row - (bh + 0.08) / 2)])
        ax.text((ds_x + ds_w / 2 + sx[-1] + bw / 2) / 2, y_back - 0.1,
                "results written back into the same dataset, which the next tool reads", ha="center", va="top",
                fontsize=NOTE, color=INK2)
        ax.text((ds_x + ds_w / 2 + sx[-1] + bw / 2) / 2, y_back - 0.42,
                "Pre- and post-processing use libraries such as TiXI, TiGL, libxml2 or lxml.",
                ha="center", va="top", fontsize=NOTE, color=INK2)

        ax.set_xlim(0.0, width)
        ax.set_ylim(0.0, height)
        ax.set_aspect("equal")
        ax.axis("off")
        save_figure(fig, FIGURES / "datasetAccess.png")


def main():
    figure_dataset_access()
    figure_tool_interfaces()
    figure_basic_principle()
    figure_data_hierarchy()


if __name__ == "__main__":
    main()

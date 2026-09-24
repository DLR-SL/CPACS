# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figures and example data for the system description: the library of system
elements, the installed components, a system architecture and a power breakdown.

Run from the repository root:

    uv run documentation/scripts/systems.py

The script writes

    documentation/figures/systemsLevels.png
    documentation/figures/systemArchitectureGraph.png
    documentation/figures/powerBreakdownSankey.png
    examples/systems_fuelCellPod.xml

and prints the excerpts shown in the documentation together with the power
balance of every component and the clearances between the installed components.
The schema documentation is not written by this script; copy the printed
excerpts there when the example changes.

The example is one propulsion unit (pod) of a regional aircraft with hydrogen
fuel cells, after the ESBEF-CP1 in Burschyk, Alder et al., "Introduction of a
System Definition in CPACS", Aerospace 12 (2025) 373, section 4.2: a fuel cell
stack and a battery feed a power management unit, which supplies the electric
power train (inverter, motor, gearbox, propeller), the compressor of the air
supply and the electrical power supply system of the aircraft. A heat exchanger
takes the waste heat of the fuel cell to the ambient air.

The power flows are those of take-off and follow from a few design values: the
shaft power at the propeller, the efficiencies of the components on the way
back to the power management unit, the electric power of the fuel cell and its
efficiency. The battery covers the rest. The values are typical for this class
of aircraft, not those of the ESBEF-CP1.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

from example_xml import indent, write_cpacs_file
from figure_style import COLORS, FONT_SIZE, FULL_WIDTH, LINE, figure_style, save_figure
from systemElements import primitive_xml, se3_xml
from wing import collection

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "systems_fuelCellPod.xml"

SERIES1 = COLORS["series1"]
SERIES2 = COLORS["series2"]
SERIES3 = COLORS["series3"]
LIGHT = COLORS["series1Light"]
INK = COLORS["ink"]
INK2 = COLORS["inkSecondary"]
MUTED = COLORS["muted"]
NOTE = FONT_SIZE["annotation"]

# Colors of the kinds of connection, as recorded in developmentGuidelines.md
# (section "Figures and equations"): electric in series 1, mechanical in series 2,
# fluid in series 3, a connection without connectionType (heat) muted.
KIND_COLORS = {"electric": SERIES1, "mechanical": SERIES2, "fluid": SERIES3, None: MUTED}

# ------------------------------------------------------------------ design values (take-off, one pod)
PROPELLER_POWER = 400e3  # W, shaft power at the propeller
PROPELLER_SPEED = 1200.0  # rpm
MOTOR_SPEED = 6000.0  # rpm, the gearbox reduces it to the propeller speed
MOTOR_POLE_PAIRS = 4
EFFICIENCY = {"gearBox": 0.98, "electricMotor": 0.96, "inverter": 0.98, "pmu": 0.99}
DC_VOLTAGE = 800.0  # V, of the high-voltage bus of the pod
AC_VOLTAGE = 490.0  # V, effective line voltage at the motor
EPSS_VOLTAGE = 540.0  # V, of the bus of the electrical power supply system
EPSS_POWER = 20e3  # W, delivered to the electrical power supply system of the aircraft
FUEL_CELL_POWER = 370e3  # W, electric
FUEL_CELL_EFFICIENCY = 0.5  # electric power over the lower heating value of the hydrogen
HYDROGEN_LHV = 120e6  # J/kg
AIR_STOICHIOMETRY = 2.0  # air supplied over air needed for the hydrogen
OXYGEN_PER_HYDROGEN = 7.94  # kg of oxygen per kg of hydrogen
OXYGEN_IN_AIR = 0.232  # mass fraction
AMBIENT = (101325.0, 288.15)  # Pa, K at sea level, ISA
PRESSURE_RATIO = 2.5
COMPRESSOR_EFFICIENCY = 0.7  # isentropic
COMPRESSOR_DRIVE_EFFICIENCY = 0.9  # electric motor and inverter of the compressor
HYDROGEN_SUPPLY = (4.0e5, 300.0)  # Pa, K at the inlet of the fuel cell
STACK_TEMPERATURE = 353.15  # K, of the coolant leaving the stack
COOLANT_RETURN_TEMPERATURE = 343.15  # K, of the coolant leaving the heat exchanger
CP_AIR, KAPPA_AIR = 1005.0, 1.4


def design():
    """All power flows of the take-off case, derived from the design values."""
    gear_in = PROPELLER_POWER / EFFICIENCY["gearBox"]
    motor_in = gear_in / EFFICIENCY["electricMotor"]
    inverter_in = motor_in / EFFICIENCY["inverter"]
    hydrogen = FUEL_CELL_POWER / FUEL_CELL_EFFICIENCY / HYDROGEN_LHV
    air = AIR_STOICHIOMETRY * OXYGEN_PER_HYDROGEN * hydrogen / OXYGEN_IN_AIR
    p0, t0 = AMBIENT
    t1 = t0 * (1 + (PRESSURE_RATIO ** ((KAPPA_AIR - 1) / KAPPA_AIR) - 1) / COMPRESSOR_EFFICIENCY)
    compressor_shaft = air * CP_AIR * (t1 - t0)
    compressor_in = compressor_shaft / COMPRESSOR_DRIVE_EFFICIENCY
    pmu_out = inverter_in + compressor_in + EPSS_POWER
    pmu_in = pmu_out / EFFICIENCY["pmu"]
    heat = FUEL_CELL_POWER / FUEL_CELL_EFFICIENCY - FUEL_CELL_POWER
    return {
        "gear_in": gear_in, "motor_in": motor_in, "inverter_in": inverter_in, "hydrogen": hydrogen, "air": air,
        "t1": t1, "p1": p0 * PRESSURE_RATIO, "compressor_in": compressor_in, "pmu_in": pmu_in,
        "battery": pmu_in - FUEL_CELL_POWER, "heat": heat,
        "motor_torque": gear_in / (MOTOR_SPEED * math.pi / 30),
        "propeller_torque": PROPELLER_POWER / (PROPELLER_SPEED * math.pi / 30),
        "frequency": MOTOR_SPEED / 60 * MOTOR_POLE_PAIRS,
    }


D = design()

# ------------------------------------------------------------------ library
# (key, domain path, leaf container, element tag, name, primitives, mass, representation)
# The primitives are given in the element coordinate system: boxes with the origin
# at a corner, bodies of revolution about z with the origin in the centre of their
# lower face. Installed along x, the bodies of revolution are rotated by 90 deg about y.
POD = "pod1"
BOX, ROUND = "cuboid", "cylinder"
ELEMENTS = [
    ("fuelCellStack", ("electricalElements", "conversionElements"), "fuelCellStacks", "fuelCellStack",
     "Fuel cell stack, 370 kW", (BOX, dict(lengthX=0.9, depthY=0.5, heightZ=0.45)), 185.0, None),
    ("battery", ("electricalElements", "storageElements"), "batteries", "battery",
     "Battery, 30 kWh", (BOX, dict(lengthX=0.8, depthY=0.45, heightZ=0.3)), 150.0, None),
    ("pmu", ("electricalElements", "distributionElements"), "powerDistributionUnits", "powerDistributionUnit",
     "Power management unit", (BOX, dict(lengthX=0.45, depthY=0.35, heightZ=0.2)), 22.0, None),
    ("inverter", ("electricalElements", "conversionElements"), "dcacConverters", "dcacConverter",
     "Motor inverter", (BOX, dict(lengthX=0.4, depthY=0.3, heightZ=0.15)), 18.0, None),
    ("electricMotor", ("mechanicalElements", "conversionElements"), "electricMotors", "electricMotor",
     "Propulsion motor, 410 kW", (ROUND, dict(radius=0.22, height=0.35)), 80.0, None),
    ("gearBox", ("mechanicalElements", "conversionElements"), "gearBoxes", "gearBox",
     "Reduction gearbox", (ROUND, dict(radius=0.2, height=0.25)), 45.0, None),
    ("compressor", ("thermoFluidElements", "conversionElements"), "electricDrivenCompressors",
     "electricDrivenCompressor", "Air compressor of the fuel cell", (ROUND, dict(radius=0.14, height=0.4)), 28.0,
     None),
    ("heatExchanger", ("thermoFluidElements", "conversionElements"), "heatExchangers", "heatExchanger",
     "Coolant-to-air heat exchanger", (BOX, dict(lengthX=0.12, depthY=0.7, heightZ=0.5)), 40.0, None),
    ("propeller", ("genericElements",), None, "genericElement",
     "Propeller, disc swept by the blades", (ROUND, dict(radius=1.2, height=0.3)), 70.0, "envelope"),
]
ELEMENT = {e[0]: e for e in ELEMENTS}


def element_uid(key):
    return key


def element_xml(key):
    _, _, _, tag, name, (shape, params), mass, representation = ELEMENT[key]
    plural = {"cuboid": "cuboids", "cylinder": "cylinders"}[shape]
    attribute = f' representation="{representation}"' if representation else ""
    return "\n".join([
        f'<{tag} uID="{element_uid(key)}">', f"    <name>{name}</name>", f"    <geometry{attribute}>",
        indent(collection(plural, [primitive_xml(shape, params)]), 2), "    </geometry>", "    <mass>",
        f"        <mass>{mass:g}</mass>", "    </mass>", f"</{tag}>",
    ])


def library_xml(keys=None):
    """The system elements, sorted into their domain, role and leaf containers."""
    keys = keys or [e[0] for e in ELEMENTS]
    tree = {}
    for key in keys:
        _, path, leaf, *_ = ELEMENT[key]
        node = tree
        for part in path + ((leaf,) if leaf else ()):
            node = node.setdefault(part, {})
        node.setdefault(None, []).append(element_xml(key))

    def render(node):
        parts = list(node.get(None, []))
        parts += [collection(tag, [render(child)]) for tag, child in node.items() if tag is not None]
        return "\n".join(parts)

    return render(tree)


# ------------------------------------------------------------------ installed components
# (key, name, system, translation, rotated): translation in the global coordinate
# system of the aircraft, rotated = body of revolution turned to point along x.
SYSTEMS = [("fuelCellSystem", "Fuel cell system, pod 1"), ("powerTrain", "Electric power train, pod 1")]
AXIS = (4.0, 1.0)  # y, z of the pod axis
COMPONENTS = [
    ("propeller", "Propeller, pod 1", "powerTrain", (8.6, AXIS[0], AXIS[1]), True),
    ("gearBox", "Gearbox, pod 1", "powerTrain", (9.0, AXIS[0], AXIS[1]), True),
    ("electricMotor", "Motor, pod 1", "powerTrain", (9.3, AXIS[0], AXIS[1]), True),
    ("heatExchanger", "Heat exchanger, pod 1", "fuelCellSystem", (9.3, 3.65, 0.2), False),
    ("inverter", "Inverter, pod 1", "powerTrain", (9.8, 3.85, 0.925), False),
    ("pmu", "Power management unit, pod 1", "powerTrain", (10.3, 3.825, 0.9), False),
    ("fuelCellStack", "Fuel cell stack, pod 1", "fuelCellSystem", (10.9, 3.75, 0.775), False),
    ("compressor", "Compressor, pod 1", "fuelCellSystem", (10.9, AXIS[0], 0.55), True),
    ("battery", "Battery, pod 1", "powerTrain", (11.95, 3.775, 0.85), False),
]
COMPONENT = {c[0]: c for c in COMPONENTS}


def component_uid(key):
    return f"{key}_{POD}"


def component_xml(key):
    _, name, _, translation, rotated = COMPONENT[key]
    return "\n".join([
        f'<component uID="{component_uid(key)}">', f"    <name>{name}</name>",
        f"    <systemElementUID>{element_uid(key)}</systemElementUID>",
        indent(se3_xml(rotation=(0, 90, 0) if rotated else None, translation=translation), 1), "</component>",
    ])


def system_xml(system_key, keys=None):
    name = dict(SYSTEMS)[system_key]
    keys = keys or [c[0] for c in COMPONENTS if c[2] == system_key]
    return "\n".join([f'<genericSystem uID="{system_key}_{POD}">', f"    <name>{name}</name>",
                      indent(collection("components", [component_xml(k) for k in keys]), 1), "</genericSystem>"])


def bounding_box(key):
    """Axis-aligned bounds of an installed component in the global coordinate system."""
    _, _, _, translation, rotated = COMPONENT[key]
    shape, p = ELEMENT[key][5]
    if shape == BOX:
        lo, hi = np.zeros(3), np.array([p["lengthX"], p["depthY"], p["heightZ"]])
    else:
        r, h = p["radius"], p["height"]
        lo, hi = np.array([-r, -r, 0.0]), np.array([r, r, h])
    if rotated:  # rotation of 90 deg about y: (x, y, z) -> (z, y, -x)
        lo, hi = np.array([lo[2], lo[1], -hi[0]]), np.array([hi[2], hi[1], -lo[0]])
    return lo + translation, hi + translation


def clearances():
    """Smallest gap between the bounding boxes of every pair of components; the script stops on an overlap."""
    result = []
    keys = [c[0] for c in COMPONENTS]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            (lo_a, hi_a), (lo_b, hi_b) = bounding_box(a), bounding_box(b)
            gap = np.maximum(lo_b - hi_a, lo_a - hi_b).max()
            assert gap > 0.02, f"{a} and {b} overlap or touch ({gap:.3f} m)"
            result.append((a, b, gap))
    return result


# ------------------------------------------------------------------ architecture
# (key, name, connectionType, source, target, controlled); an end is a component key,
# ("external", "ambient") or ("ata", "ata28").
ARCHITECTURE_UID = f"propulsionUnit_{POD}"
CONNECTIONS = [
    ("fuelCellFeeder", "Fuel cell feeder", "electric", "fuelCellStack", "pmu", False),
    ("batteryFeeder", "Battery feeder", "electric", "battery", "pmu", True),
    ("inverterFeeder", "Inverter feeder", "electric", "pmu", "inverter", False),
    ("motorFeeder", "Motor feeder", "electric", "inverter", "electricMotor", False),
    ("motorShaft", "Motor shaft", "mechanical", "electricMotor", "gearBox", False),
    ("propellerShaft", "Propeller shaft", "mechanical", "gearBox", "propeller", False),
    ("compressorFeeder", "Compressor feeder", "electric", "pmu", "compressor", False),
    ("epssFeeder", "Feeder to the electrical power supply system", "electric", "pmu", ("ata", "ata24"), False),
    ("airIntake", "Air intake", "fluid", ("external", "ambient"), "compressor", False),
    ("airSupply", "Compressed air", "fluid", "compressor", "fuelCellStack", False),
    ("hydrogenSupply", "Hydrogen supply", "fluid", ("ata", "ata28"), "fuelCellStack", False),
    ("coolantLoop", "Coolant loop", None, "fuelCellStack", "heatExchanger", False),
    ("heatRejection", "Heat rejection", None, "heatExchanger", ("external", "ambient"), False),
]
CONNECTION = {c[0]: c for c in CONNECTIONS}
CONTROL_DEVICE_UID = f"batteryContactor_{POD}"


def connection_uid(key):
    return f"{key}_{POD}"


def end_xml(tag, end):
    if isinstance(end, tuple):
        kind, value = end
        inner = f"<externalElement>{value}</externalElement>" if kind == "external" else f"<ataChapter>{value}</ataChapter>"
    else:
        inner = f"<componentUID>{component_uid(end)}</componentUID>"
    return f"<{tag}>\n    {inner}\n</{tag}>"


def control_device_xml():
    return "\n".join([f'<controlDevices uID="{CONTROL_DEVICE_UID}">', "    <state>",
                      "        <controlParameterActive>1</controlParameterActive>",
                      "        <controlParameterInactive>0</controlParameterInactive>", "    </state>",
                      "</controlDevices>"])


def connection_xml(key):
    _, name, kind, source, target, controlled = CONNECTION[key]
    lines = [f'<connection uID="{connection_uid(key)}">', f"    <name>{name}</name>"]
    if kind:
        lines.append(f"    <connectionType>{kind}</connectionType>")
    if controlled:
        lines.append(indent(control_device_xml(), 1))
    lines += [indent(end_xml("source", source), 1), indent(end_xml("target", target), 1), "</connection>"]
    return "\n".join(lines)


def architecture_xml(keys=None):
    """The architecture of the pod; with keys only these connections, followed by '...'."""
    partial = keys is not None
    keys = keys or [c[0] for c in CONNECTIONS]
    return "\n".join([
        f'<systemArchitecture uID="{ARCHITECTURE_UID}">', "    <name>Propulsion unit, pod 1</name>",
        "    <systemType>generic</systemType>",
        indent(collection("connections", [connection_xml(k) for k in keys] + (["..."] if partial else [])), 1),
        "</systemArchitecture>",
    ])


# ------------------------------------------------------------------ power breakdown
CASE_UID = "takeOff"


def _fmt(value, digits=4):
    """A value rounded to the given number of significant digits."""
    return f"{float(f'{value:.{digits}g}'):g}"


def power_flows():
    """(connection key, category, value, detail lines) of the take-off case, in W, kg/s, Pa, K."""
    d, p0, t0 = D, *AMBIENT
    dc = [f"<directCurrent>{DC_VOLTAGE:g}</directCurrent>"]
    air = ["<massComposition>", "    <species>", "        <share>1</share>", "        <type>Air</type>",
           "    </species>", "</massComposition>"]
    return [
        ("fuelCellFeeder", "electricPower", FUEL_CELL_POWER, dc),
        ("batteryFeeder", "electricPower", d["battery"], dc),
        ("inverterFeeder", "electricPower", d["inverter_in"], dc),
        ("motorFeeder", "electricPower", d["motor_in"],
         ["<alternatingCurrent>", f"    <effectiveVoltage>{AC_VOLTAGE:g}</effectiveVoltage>",
          f"    <frequency>{d['frequency']:g}</frequency>", "</alternatingCurrent>"]),
        ("motorShaft", "mechanicalPower", d["gear_in"], [f"<torque>{_fmt(d['motor_torque'])}</torque>"]),
        ("propellerShaft", "mechanicalPower", PROPELLER_POWER, [f"<torque>{_fmt(d['propeller_torque'])}</torque>"]),
        ("compressorFeeder", "electricPower", d["compressor_in"], dc),
        ("epssFeeder", "electricPower", EPSS_POWER, [f"<directCurrent>{EPSS_VOLTAGE:g}</directCurrent>"]),
        ("airIntake", "massFlow", d["air"],
         ["<singlePhaseMassFlow>", f"    <pressure>{p0:g}</pressure>", f"    <temperature>{t0:g}</temperature>",
          *("    " + line for line in air), "</singlePhaseMassFlow>"]),
        ("airSupply", "massFlow", d["air"],
         ["<singlePhaseMassFlow>", f"    <pressure>{_fmt(d['p1'])}</pressure>",
          f"    <temperature>{_fmt(d['t1'])}</temperature>", *("    " + line for line in air),
          "</singlePhaseMassFlow>"]),
        ("hydrogenSupply", "massFlow", d["hydrogen"],
         ["<singlePhaseMassFlow>", f"    <pressure>{HYDROGEN_SUPPLY[0]:g}</pressure>",
          f"    <temperature>{HYDROGEN_SUPPLY[1]:g}</temperature>", "</singlePhaseMassFlow>"]),
        ("coolantLoop", "heatFlow", d["heat"],
         [f"<sourceTemperature>{STACK_TEMPERATURE:g}</sourceTemperature>",
          f"<sinkTemperature>{COOLANT_RETURN_TEMPERATURE:g}</sinkTemperature>"]),
        ("heatRejection", "heatFlow", d["heat"],
         [f"<sourceTemperature>{COOLANT_RETURN_TEMPERATURE:g}</sourceTemperature>",
          f"<sinkTemperature>{AMBIENT[1]:g}</sinkTemperature>"]),
    ]


VALUE_TAG = {"electricPower": "electricPowerValue", "mechanicalPower": "mechanicalPowerValue",
             "massFlow": "massFlowValue", "heatFlow": "heatFlowValue"}


def power_flow_xml(key, category, value, detail):
    digits = 4
    return "\n".join([
        "<powerFlow>", f"    <name>{CONNECTION[key][1]}</name>",
        f"    <connectionUID>{connection_uid(key)}</connectionUID>", f"    <{category}>",
        f"        <{VALUE_TAG[category]}>{_fmt(value, digits)}</{VALUE_TAG[category]}>",
        *("        " + line for line in detail), f"    </{category}>", "</powerFlow>",
    ])


def static_case_xml(keys=None):
    """The take-off case; with keys only the flows on these connections, followed by '...'."""
    flows = [f for f in power_flows() if keys is None or f[0] in keys]
    more = ["..."] if keys is not None else []
    return "\n".join([
        f'<staticCase uID="{CASE_UID}">', "    <name>Take-off</name>", "    <specification>",
        "        <altitude>0</altitude>", "        <machNumber>0.2</machNumber>", "        <environment>",
        "            <atmosphericModel>ISA</atmosphericModel>", "        </environment>", "        <configuration>",
        "            <controlElements>", "                <controlElement>",
        f"                    <controlDeviceUID>{CONTROL_DEVICE_UID}</controlDeviceUID>",
        "                    <controlParameter>1</controlParameter>", "                </controlElement>",
        "            </controlElements>", "        </configuration>", "    </specification>",
        indent(collection("powerBreakdownData", [power_flow_xml(*f) for f in flows] + more), 1), "</staticCase>",
    ])


def balances():
    """Incoming and outgoing power of each component of the electric and mechanical chain, in W."""
    flows = {k: v for k, c, v, _ in power_flows() if c in ("electricPower", "mechanicalPower")}
    result = {}
    for key in ("pmu", "inverter", "electricMotor", "gearBox"):
        incoming = sum(v for k, v in flows.items() if CONNECTION[k][4] == key)
        outgoing = sum(v for k, v in flows.items() if CONNECTION[k][3] == key)
        result[key] = (incoming, outgoing)
    return result


# ------------------------------------------------------------------ example file
def write_example():
    systems = collection("genericSystems", [system_xml(k) for k, _ in SYSTEMS])
    analyses = collection("powerBreakdowns", [collection("staticCases", [static_case_xml()])])
    write_cpacs_file(
        EXAMPLE_FILE, generator=Path(__file__), name="Fuel cell propulsion unit",
        description="Systems of one propulsion unit of a regional aircraft with hydrogen fuel cells: "
                    "library elements, installed components, system architecture and the power flows at take-off",
        model_uid="fuelCellAircraft", model_name="Regional aircraft with fuel cell propulsion",
        components_tag="systems", components=systems, profiles_tag=None, profiles=None,
        extra_components=[("analyses", analyses),
                          ("systemArchitectures", architecture_xml())],
        extra_vehicles=[("systemElements", library_xml())],
    )


# ------------------------------------------------------------------ figures
def _box(ax, center, text, width, height=0.42, face=None, edge=None, color=INK, lw=None, fontsize=NOTE):
    x, y = center
    ax.add_patch(FancyBboxPatch((x - width / 2, y - height / 2), width, height,
                                boxstyle="round,pad=0,rounding_size=0.08", facecolor=face or COLORS["surface"],
                                edgecolor=edge or MUTED, lw=lw or LINE["reference"], zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, color=color, zorder=4, linespacing=1.15)


def _connect(ax, a, b, color, lw=None, rad=0.0, shrink=(0, 0), head=8, zorder=2):
    ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>", mutation_scale=head,
                                 color=color, lw=lw or LINE["data"], shrinkA=shrink[0], shrinkB=shrink[1],
                                 zorder=zorder, joinstyle="round", capstyle="round"))


# Layout of the architecture graph: centre of each node, in units of the grid.
GRAPH_PITCH = 1.8
GRAPH_NODES = {
    ("ata", "ata28"): (0, 2),
    "fuelCellStack": (1, 2),
    "heatExchanger": (2, 2),
    ("external", "ambient", "out"): (3, 2),
    ("external", "ambient", "in"): (0, 1),
    "compressor": (1, 1),
    "pmu": (2, 1),
    "inverter": (3, 1),
    "electricMotor": (4, 1),
    "gearBox": (5, 1),
    "propeller": (6, 1),
    "battery": (1, 0),
    ("ata", "ata24"): (3, 0),
}
GRAPH_LABELS = {
    "fuelCellStack": "Fuel cell\nstack", "battery": "Battery", "pmu": "Power\nmanagement\nunit",
    "inverter": "Inverter", "electricMotor": "Motor", "gearBox": "Gearbox", "propeller": "Propeller",
    "compressor": "Compressor", "heatExchanger": "Heat\nexchanger",
    ("ata", "ata28"): "Fuel system\n(ata28)", ("ata", "ata24"): "Electric\npower\n(ata24)",
    ("external", "ambient", "in"): "ambient", ("external", "ambient", "out"): "ambient",
}
NODE_WIDTH, NODE_HEIGHT, ROW_PITCH = 1.48, 0.8, 1.3


def _graph_node(end, role):
    if isinstance(end, tuple):
        kind, value = end
        return (kind, value, role) if kind == "external" else (kind, value)
    return end


def _graph_xy(node):
    column, row = GRAPH_NODES[node]
    return np.array([column * GRAPH_PITCH, row * ROW_PITCH])


def figure_architecture():
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.0))
        ax.set_aspect("equal")
        ax.axis("off")
        for node in GRAPH_NODES:
            outside = isinstance(node, tuple)
            _box(ax, _graph_xy(node), GRAPH_LABELS[node], NODE_WIDTH, NODE_HEIGHT,
                 edge=COLORS["axis"] if outside else INK2, color=INK2 if outside else INK,
                 lw=LINE["reference"] if outside else LINE["secondary"], fontsize=NOTE - 0.5)
        for key, _, kind, source, target, controlled in CONNECTIONS:
            a, b = _graph_xy(_graph_node(source, "in")), _graph_xy(_graph_node(target, "out"))
            pa, pb = _border(a, b), _border(b, a)
            _connect(ax, pa, pb, KIND_COLORS[kind], shrink=(1, 1))
            if controlled:
                mid = (pa + pb) / 2
                ax.plot(*mid, marker="o", ms=5, mfc=COLORS["surface"], mec=INK2, mew=LINE["secondary"], zorder=5)
                ax.annotate("controlDevices", xy=mid, xytext=(-9, 0), textcoords="offset points", ha="right",
                            va="center", fontsize=NOTE, color=INK2, zorder=5)
        handles = [plt.Line2D([], [], color=KIND_COLORS[k], lw=LINE["data"]) for k in
                   ("electric", "mechanical", "fluid", None)]
        ax.legend(handles, ["electric", "mechanical", "fluid", "without connectionType (heat)"], loc="lower left",
                  bbox_to_anchor=(0.0, 1.0), ncol=4, handlelength=1.8, columnspacing=1.6, borderaxespad=0.0)
        ax.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99)
        save_figure(fig, FIGURES / "systemArchitectureGraph.png")


def _border(a, b, w=NODE_WIDTH / 2, h=NODE_HEIGHT / 2):
    """Point where the line from the centre a towards b leaves the node box around a."""
    d = b - a
    t = min(w / abs(d[0]) if d[0] else np.inf, h / abs(d[1]) if d[1] else np.inf)
    return a + t * d


# ------------------------------------------------------------------ Sankey diagram
SANKEY_LABELS = {
    "fuelCellStack": "Fuel cell stack", "battery": "Battery", "pmu": "Power\nmanagement unit",
    "inverter": "Inverter", "electricMotor": "Motor", "gearBox": "Gearbox", "propeller": "Propeller",
    "compressor": "Compressor", ("ata", "ata24"): "Electrical power (ata24)",
}
SANKEY_COLUMNS = [["fuelCellStack", "battery"], ["pmu"], ["inverter", "compressor", ("ata", "ata24")],
                  ["electricMotor"], ["gearBox"], ["propeller"]]
SANKEY_X = [0.0, 1.8, 3.6, 5.4, 6.9, 8.4]


def _band(ax, x0, y0, x1, y1, width, color, alpha=0.4, zorder=2):
    """A band of constant vertical width from (x0, y0) to (x1, y1) (upper edges), eased in between."""
    t = np.linspace(0, 1, 80)
    s = t * t * (3 - 2 * t)
    x = x0 + (x1 - x0) * t
    top = y0 + (y1 - y0) * s
    ax.add_patch(Polygon(np.vstack([np.column_stack([x, top]), np.column_stack([x[::-1], top[::-1] - width])]),
                         closed=True, facecolor=color, alpha=alpha, edgecolor="none", zorder=zorder))


def figure_sankey():
    flows = [(CONNECTION[k][3], CONNECTION[k][4], v, c) for k, c, v, _ in power_flows()
             if c in ("electricPower", "mechanicalPower")]
    losses = {k: i - o for k, (i, o) in balances().items()}
    scale = 2.0 / D["pmu_in"]  # height per W
    bar = 0.07
    gaps = {"battery": 0.3, "compressor": 0.85, ("ata", "ata24"): 0.4}
    text_height = 0.3  # a band thinner than this carries its value in the label of its target

    def throughput(node):
        incoming = sum(v for s, t, v, _ in flows if t == node)
        outgoing = sum(v for s, t, v, _ in flows if s == node) + losses.get(node, 0.0)
        return max(incoming, outgoing)

    top, x = {}, {}
    for column, cx in zip(SANKEY_COLUMNS, SANKEY_X, strict=True):
        y = 0.0
        for node in column:
            y -= gaps.get(node, 0.0)
            top[node], x[node] = y, cx
            y -= throughput(node) * scale

    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.6))
        ax.axis("off")
        out_cursor, in_cursor = dict(top), dict(top)
        thin_value = {}
        for node in [n for column in SANKEY_COLUMNS for n in column]:
            for s, t, v, c in [f for f in flows if f[0] == node]:
                w = v * scale
                _band(ax, x[s] + bar / 2, out_cursor[s], x[t] - bar / 2, in_cursor[t], w,
                      SERIES1 if c == "electricPower" else SERIES2)
                if w > text_height:
                    ax.text((x[s] + x[t]) / 2, (out_cursor[s] + in_cursor[t] - w) / 2, f"{v / 1e3:.0f} kW",
                            ha="center", va="center", fontsize=NOTE, color=INK, zorder=5)
                else:
                    thin_value[t] = v
                out_cursor[s] -= w
                in_cursor[t] -= w
            if node in losses:
                w = losses[node] * scale
                end = (x[node] + 0.3, out_cursor[node] - 0.42)
                _band(ax, x[node] + bar / 2, out_cursor[node], *end, w, MUTED, alpha=0.45)
                ax.text(end[0] + 0.02, end[1] - w - 0.03, f"loss {losses[node] / 1e3:.1f} kW", ha="center",
                        va="top", fontsize=NOTE, color=INK2)
        for node, y in top.items():
            h = throughput(node) * scale
            ax.add_patch(plt.Rectangle((x[node] - bar / 2, y - h), bar, h, facecolor=INK2, edgecolor="none",
                                       zorder=4))
            text = SANKEY_LABELS[node]
            if node in thin_value:
                text += f", {thin_value[node] / 1e3:.0f} kW"
            if node in ("fuelCellStack", "battery"):
                ax.text(x[node] - 0.1, y - h / 2, text, ha="right", va="center", fontsize=NOTE, zorder=5)
            elif node in ("compressor", ("ata", "ata24")):
                ax.text(x[node] + 0.1, y - h / 2, text, ha="left", va="center", fontsize=NOTE, zorder=5)
            else:
                ax.text(x[node], y + 0.06, text, ha="center", va="bottom", fontsize=NOTE, zorder=5)
        handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c, alpha=a, edgecolor="none") for c, a in
                   ((SERIES1, 0.4), (SERIES2, 0.4), (MUTED, 0.45))]
        ax.legend(handles, ["electric power", "mechanical power", "loss, from the balance of the component"],
                  loc="upper left", bbox_to_anchor=(0.0, -0.02), ncol=3, handlelength=1.4, borderaxespad=0.0)
        ax.set_aspect("equal")
        ax.autoscale_view()
        fig.subplots_adjust(left=0.01, right=0.99)
        save_figure(fig, FIGURES / "powerBreakdownSankey.png")


def figure_levels():
    """The chain of references from the library to the power flows, for the fuel cell of the example."""
    stages = [
        ("Library", "systemElements", f"<{ELEMENT['fuelCellStack'][3]}>", element_uid("fuelCellStack"),
         "geometry and mass"),
        ("Installed components", "genericSystems", "<component>", component_uid("fuelCellStack"), "position"),
        ("System architecture", "systemArchitectures", "<connection>", connection_uid("fuelCellFeeder"),
         "source and target"),
        ("Power breakdown", "powerBreakdowns", "<powerFlow>", f"in case {CASE_UID}", f"{FUEL_CELL_POWER / 1e3:.0f} kW"),
    ]
    references = ["systemElementUID", "componentUID", "connectionUID"]
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.3))
        ax.set_aspect("equal")
        ax.axis("off")
        width, height, pitch = 2.3, 1.05, 2.85
        for i, (title, node, tag, name, content) in enumerate(stages):
            x = i * pitch
            ax.add_patch(FancyBboxPatch((x, 0), width, height, boxstyle="round,pad=0,rounding_size=0.08",
                                        facecolor=COLORS["surface"], edgecolor=INK2, lw=LINE["secondary"], zorder=3))
            ax.text(x + width / 2, height + 0.38, title, ha="center", va="bottom", fontsize=FONT_SIZE["base"])
            ax.text(x + width / 2, height + 0.1, node, ha="center", va="bottom", fontsize=NOTE, color=INK2,
                    family="DejaVu Sans Mono")
            for k, (text, mono) in enumerate([(tag, True), (name, not name.startswith("in case")), (content, False)]):
                ax.text(x + 0.14, height - 0.17 - 0.29 * k, text, ha="left", va="top", fontsize=NOTE - 0.5,
                        color=INK if k < 2 else INK2, family="DejaVu Sans Mono" if mono else None, zorder=4)
        for i, name in enumerate(references):
            # the later stage references the earlier one: the arrow points back
            a, b = (i + 1) * pitch + 0.35, i * pitch + width - 0.35
            _connect(ax, (a, 0), (b, 0), INK2, lw=LINE["secondary"], rad=-0.45, head=7)
            ax.text((a + b) / 2, -0.42, name, ha="center", va="top", fontsize=NOTE - 1, color=INK2,
                    family="DejaVu Sans Mono")
        ax.autoscale_view()
        ax.set_ylim(-0.75, height + 0.7)
        fig.subplots_adjust(left=0.01, right=0.99)
        save_figure(fig, FIGURES / "systemsLevels.png")


# ------------------------------------------------------------------ report and excerpts
def report():
    d = D
    print("Take-off, one pod")
    print(f"  propeller {PROPELLER_POWER / 1e3:.1f} kW, gearbox input {d['gear_in'] / 1e3:.2f} kW, "
          f"motor input {d['motor_in'] / 1e3:.2f} kW, inverter input {d['inverter_in'] / 1e3:.2f} kW")
    print(f"  hydrogen {d['hydrogen'] * 1e3:.3f} g/s, air {d['air']:.4f} kg/s, compressor outlet "
          f"{d['p1']:.0f} Pa, {d['t1']:.1f} K, compressor input {d['compressor_in'] / 1e3:.2f} kW")
    print(f"  power management unit input {d['pmu_in'] / 1e3:.2f} kW: fuel cell {FUEL_CELL_POWER / 1e3:.1f} kW, "
          f"battery {d['battery'] / 1e3:.2f} kW; waste heat {d['heat'] / 1e3:.1f} kW")
    print(f"  torque motor {d['motor_torque']:.1f} N m, propeller {d['propeller_torque']:.1f} N m, "
          f"frequency {d['frequency']:.0f} Hz")
    print("Balances (in, out, loss) in kW")
    for key, (i, o) in balances().items():
        print(f"  {key:14s} {i / 1e3:8.2f} {o / 1e3:8.2f} {(i - o) / 1e3:7.2f}  efficiency {o / i:.4f}")
    print("Installed components (bounding box in the global coordinate system)")
    for key in COMPONENT:
        lo, hi = bounding_box(key)
        print(f"  {key:14s} x {lo[0]:6.3f} .. {hi[0]:6.3f}  y {lo[1]:6.3f} .. {hi[1]:6.3f}  z {lo[2]:6.3f} .. {hi[2]:6.3f}")
    gaps = sorted(clearances(), key=lambda g: g[2])
    print("Smallest clearances between components (the script stops on an overlap)")
    for a, b, gap in gaps[:4]:
        print(f"  {a:14s} {b:14s} {gap:.3f} m")
    mass = sum(ELEMENT[k][6] for k in COMPONENT)
    print(f"Mass of all components {mass:.1f} kg")


def excerpts():
    """(type, excerpt) for the documentation, each as it is shown there."""
    return [
        ("systemElementsType", collection("systemElements", [library_xml(["battery", "electricMotor"])])),
        ("geometryRepresentationType", element_xml("propeller")),
        ("genericSystemType", system_xml("fuelCellSystem")),
        ("systemArchitectureType", architecture_xml(["fuelCellFeeder", "batteryFeeder", "epssFeeder",
                                                     "airIntake"])),
        ("powerBreakdownsType", collection("powerBreakdowns", [collection("staticCases", [
            static_case_xml(["batteryFeeder", "motorShaft", "airSupply", "coolantLoop"])])])),
    ]


def main():
    clearances()
    figure_levels()
    figure_architecture()
    figure_sankey()
    write_example()
    report()
    print(f"\nWritten {EXAMPLE_FILE.relative_to(DOCUMENTATION.parent).as_posix()}")
    for title, excerpt in excerpts():
        print(f"\nExcerpt for the {title} documentation:\n")
        print(excerpt)


if __name__ == "__main__":
    main()

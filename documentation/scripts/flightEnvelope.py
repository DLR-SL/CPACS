# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy==2.2.6",
#     "matplotlib==3.10.3",
# ]
# ///
"""Figure and example data for the global data of an aircraft model (aircraftGlobalType)
and its flight envelope (flightEnvelopeType, flightEnvelopeSpeedType).

Run from the repository root:

    uv run documentation/scripts/flightEnvelope.py

The script writes

    documentation/figures/flightEnvelope.png
    examples/aircraftGlobal.xml

and prints the excerpts shown in the documentation. The schema documentation is not
written by this script; copy the printed excerpts there when the example changes.

The aircraft is a short-range airliner. Each boundary of its flight envelope is the curve
of one characteristic speed over altitude, given as true airspeed at the altitudes of
the ISA (cpacsType, section 10):

    VS   stall speed, a constant calibrated airspeed
    VMO  maximum operating speed: a constant calibrated airspeed up to the altitude at
         which it reaches the maximum operating Mach number, above that this Mach number
    VD   design diving speed, built in the same way from VD and MD

Calibrated airspeed is converted to true airspeed with the isentropic relations for
subsonic flow; all curves end at the maximum operating altitude.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from example_xml import indent, vector, write_cpacs_file
from figure_style import COLORS, FULL_WIDTH, LINE, figure_style, label, save_figure

DOCUMENTATION = Path(__file__).resolve().parents[1]
FIGURES = DOCUMENTATION / "figures"
EXAMPLE_FILE = DOCUMENTATION.parent / "examples" / "aircraftGlobal.xml"

# --- ISA (ICAO Doc 7488/3), geopotential altitude in m ------------------------------------------------
G0, R, KAPPA = 9.80665, 287.05287, 1.4
T0, P0, LAPSE, H_TROPOPAUSE = 288.15, 101325.0, -0.0065, 11000.0
A0 = np.sqrt(KAPPA * R * T0)


def isa(h):
    """Temperature [K], pressure [Pa] and speed of sound [m/s] at geopotential altitude h, up to 20 km."""
    h = np.asarray(h, dtype=float)
    t11 = T0 + LAPSE * H_TROPOPAUSE
    p11 = P0 * (t11 / T0) ** (-G0 / (LAPSE * R))
    t = np.where(h <= H_TROPOPAUSE, T0 + LAPSE * h, t11)
    p = np.where(h <= H_TROPOPAUSE, P0 * (t / T0) ** (-G0 / (LAPSE * R)),
                 p11 * np.exp(-G0 * (h - H_TROPOPAUSE) / (R * t11)))
    return t, p, np.sqrt(KAPPA * R * t)


def mach_from_cas(cas, h):
    """Mach number at altitude h for a calibrated airspeed, subsonic isentropic flow."""
    _, p, _ = isa(h)
    qc = P0 * ((1.0 + 0.2 * (cas / A0) ** 2) ** 3.5 - 1.0)
    return np.sqrt(5.0 * ((qc / p + 1.0) ** (2.0 / 7.0) - 1.0))


def tas_from_cas(cas, h):
    return mach_from_cas(cas, h) * isa(h)[2]


def crossover_altitude(cas, mach):
    """Altitude at which the calibrated airspeed reaches the Mach number, by bisection."""
    lo, hi = 0.0, 20000.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if mach_from_cas(cas, mid) < mach else (lo, mid)
    return 0.5 * (lo + hi)


# --- Aircraft data ---------------------------------------------------------------------------------------
# Top-level requirements: (group, element, required, actual). Units as in the documentation.
REQUIREMENTS = [
    (None, "designRange", 4600000, 4750000),
    ("payload", "paxSeats", 150, 150),
    ("payload", "cargoCapacity", 3000, 3400),
    ("airportCompatibility", "wingSpan", 36, 34.1),
    ("airportCompatibility", "wheelTrackWidth", 9, 7.6),
    ("airportCompatibility", "runwayLoading", 50, 44),
    ("airportCompatibility", "takeOffFieldLength", 2100, 2050),
    ("airportCompatibility", "landingFieldLength", 1600, 1500),
    ("performanceTargets", "cruiseMach", 0.78, 0.78),
    ("performanceTargets", "maximumOperatingVelocity", 180, 180),
    ("performanceTargets", "maximumOperatingMach", 0.82, 0.82),
    ("performanceTargets", "initialCruiseAltitude", 10668, 10973),
    ("performanceTargets", "timeToClimb", 1500, 1440),
    ("performanceTargets", "maxOperatingAltitude", 11887, 11887),
    ("performanceTargets", "approachSpeed", 72, 69.5),
]
REQUIRED = {name: actual for _, name, _, actual in REQUIREMENTS}

VS_CAS = 66.0  # stall speed, clean configuration [m/s CAS]
VMO_CAS, MMO = REQUIRED["maximumOperatingVelocity"], REQUIRED["maximumOperatingMach"]
VD_CAS, MD = 196.0, 0.89
H_MAX = REQUIRED["maxOperatingAltitude"]
STEP = 1000.0  # altitude step of the vectors in the example [m]


def boundary(cas, mach=None, step=STEP):
    """Altitudes and true airspeeds of a boundary: constant CAS, above the crossover constant Mach.

    The altitudes are a regular grid plus the crossover altitude and the maximum operating
    altitude, so that the kink and the end of the curve are exact samples (§21).
    """
    h = list(np.arange(0.0, H_MAX, step)) + [H_MAX]
    if mach is not None:
        h_x = crossover_altitude(cas, mach)
        if h_x < H_MAX:
            h.append(round(h_x))
    h = np.array(sorted(set(h)))
    tas = tas_from_cas(cas, h)
    if mach is not None:
        tas = np.where(mach_from_cas(cas, h) > mach + 1e-9, mach * isa(h)[2], tas)
    return h, np.round(tas, 1)


SPEEDS = [("VS", boundary(VS_CAS)), ("VMO", boundary(VMO_CAS, MMO)), ("VD", boundary(VD_CAS, MD))]


# --- Example ---------------------------------------------------------------------------------------------

def requirement_xml(name, required, actual):
    return "\n".join([f"<{name}>", f"    <required>{required:.10g}</required>", f"    <actual>{actual:.10g}</actual>",
                      f"</{name}>"])


def flight_envelope_xml():
    parts = ["<flightEnvelope>", "    <atmosphericModel>ISA</atmosphericModel>"]
    for name, (h, tas) in SPEEDS:
        parts += ["    <speed>", f"        <speedName>{name}</speedName>",
                  f"        <altitude>{vector(h)}</altitude>", f"        <trueAirSpeed>{vector(tas)}</trueAirSpeed>",
                  "    </speed>"]
    parts.append("</flightEnvelope>")
    return "\n".join(parts)


# Requirements shown in the excerpt of the documentation; the others are written as "...".
EXCERPT = {"designRange", "paxSeats", "cargoCapacity", "wingSpan", "takeOffFieldLength", "cruiseMach",
           "maxOperatingAltitude"}


def global_xml(excerpt=False):
    """The <global> content; as excerpt with a selection of the requirements and without the envelope."""
    parts = []
    for group, name, req, act in REQUIREMENTS:
        if group is None:
            parts.append(requirement_xml(name, req, act))
    for group in ("payload", "airportCompatibility", "performanceTargets"):
        members = [(n, r, a) for g, n, r, a in REQUIREMENTS if g == group]
        shown = [m for m in members if not excerpt or m[0] in EXCERPT]
        parts.append(f"<{group}>")
        parts += [indent(requirement_xml(*m), 1) for m in shown]
        if len(shown) < len(members):
            parts.append("    ...")
        parts.append(f"</{group}>")
    parts += ["<flightEnvelopes>", indent("..." if excerpt else flight_envelope_xml(), 1), "</flightEnvelopes>"]
    return "\n".join(parts)


def write_example():
    write_cpacs_file(EXAMPLE_FILE, generator=Path(__file__), name="Global data of an aircraft model",
                     description="Top-level requirements and flight envelope of a short-range airliner",
                     model_uid="aircraft", model_name="Short-range airliner", components_tag="global",
                     components=global_xml(), profiles_tag=None, profiles=None)


# --- Figure ----------------------------------------------------------------------------------------------

def flight_envelope_figure():
    # Dense curves for the drawing, the example's samples as dots on them.
    dense = {name: boundary(cas, mach, step=50.0) for name, cas, mach in
             (("VS", VS_CAS, None), ("VMO", VMO_CAS, MMO), ("VD", VD_CAS, MD))}
    colors = {"VS": COLORS["series2"], "VMO": COLORS["series1"], "VD": COLORS["series3"]}
    with figure_style():
        fig, ax = plt.subplots(figsize=(FULL_WIDTH, 3.9))
        h_vs, v_vs = dense["VS"]
        h_mo, v_mo = dense["VMO"]
        ax.fill(np.concatenate([v_vs, v_mo[::-1]]), np.concatenate([h_vs, h_mo[::-1]]) / 1000,
                color=COLORS["series1"], alpha=0.08, lw=0, zorder=1)
        for name, (h, tas) in dense.items():
            ax.plot(tas, h / 1000, color=colors[name], lw=LINE["data"], zorder=3, solid_capstyle="round")
        for name, (h, tas) in SPEEDS:
            ax.plot(tas, h / 1000, "o", ms=3.2, color=colors[name], mec=COLORS["surface"], mew=0.6, zorder=4)
        ax.axhline(H_MAX / 1000, color=COLORS["muted"], lw=LINE["reference"], zorder=2)

        # Names at the lower end of each curve, below the axis line of the data.
        for name, (h, tas) in dense.items():
            label(ax, (tas[0], 0), name, offset=(0, -1), ha="center", va="top")
        h_x = crossover_altitude(VMO_CAS, MMO)
        x_x = MMO * float(isa(h_x)[2])
        label(ax, (x_x, h_x / 1000), "constant CAS below,\nconstant Mach above", offset=(-22, 0), ha="right",
              va="center", color=COLORS["inkSecondary"])
        label(ax, (60, H_MAX / 1000), "maximum operating altitude", offset=(0, 4), ha="left", va="bottom",
              color=COLORS["inkSecondary"])

        ax.set_xlim(55, 285)
        ax.set_ylim(-0.9, 13.2)
        ax.set_xlabel("true airspeed [m/s]")
        ax.set_ylabel("altitude [km]")
        ax.spines["left"].set_bounds(0, 13)
        ax.set_yticks(range(0, 14, 2))
        save_figure(fig, FIGURES / "flightEnvelope.png")


def main():
    write_example()
    flight_envelope_figure()
    print("=== aircraftGlobalType")
    print("\n".join(["<global>", indent(global_xml(excerpt=True), 1), "</global>"]))
    print("=== flightEnvelopeType")
    print(flight_envelope_xml())
    h_x = crossover_altitude(VMO_CAS, MMO)
    print(f"=== VMO crossover {h_x:.0f} m, VD crossover {crossover_altitude(VD_CAS, MD):.0f} m")
    for name, (h, tas) in SPEEDS:
        print(name, list(zip(h.tolist(), tas.tolist())))


if __name__ == "__main__":
    main()

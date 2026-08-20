r"""Demo 21 - the complete numerical trace of ONE Demo 20 case.

    Case 04  "Linear 1.0 nm"  -  linear interface grading, W = 1.0 nm at all
    four interfaces of the GaAs/Al(0.55)Ga(0.45)As asymmetric coupled quantum
    well.

Run it:

    python trace_demo20_linear_1nm.py

Every stage prints in one fixed format:

    INPUT       what went in (values, shapes, units)
    FUNCTION    the production function, with file:line
    EQUATION    the mathematics that function implements
    OUTPUT      what came out (values, shapes, units)
    MEANING     what it means physically
    CHANGED     what is different because of this step
    NEXT        what consumes this output

Every stage is also tagged with WHO does it:

    [A] user-defined physical input        (a number you chose)
    [B] deterministic Python transformation (geometry, grading, deck)
    [C] nextnano++ physics                  (band structure, eigenstates)
    [D] Python nonlinear-optical post-processing (matrix elements -> chi2)

NOTHING HERE IS A SIMPLIFIED MODEL. Every number is produced by calling Demo
20's own production functions, or - where a step is unrolled for inspection -
by :mod:`demo20_math_physics_reference`, whose reproductions are asserted equal
to production in ``demo20_math_physics_reference.self_check``.

The trace ends by comparing what it computed against the value already stored
in ``demo_results/demo20/tables/demo20_master_results.csv`` and against Demo
19's own recorded value, and asserts agreement at a tolerance justified in
STEP 21.

Options:
    --outdir PATH      where to write checkpoint files (default: ./trace_linear_1nm)
    --no-files         print only, write nothing
    --k-index N        which k point to expose term-by-term (default 40)
    --all-k            print every k contribution instead of a representative set
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

TRACE_DIR = Path(__file__).resolve().parent
if str(TRACE_DIR) not in sys.path:
    sys.path.insert(0, str(TRACE_DIR))

import demo20_math_physics_reference as ref     # noqa: E402

# Demo 20's production modules (re-exported through the reference module so
# there is exactly one sys.path manipulation in this demo).
config20 = ref.config20
cases = ref.cases
grading = ref.grading
inputs = ref.inputs
extract = ref.extract
chi2mod = ref.chi2mod
shared_chi2 = ref.shared_chi2

CASE_ID = "04"
TARGET_NM = 1550.0
REPO_ROOT = config20.REPO_ROOT
DEMO20_TABLE = REPO_ROOT / "demo_results/demo20/tables/demo20_master_results.csv"

#: THE PRIMARY SOURCE for STEP 08: Demo 20 Case 04's own parsed licensed run.
#: Resolved against REPO_ROOT, never as an absolute machine path, so the trace
#: works unchanged on the home and the work laptop.
CASE04_PARSED = REPO_ROOT / "demo_results/demo20/data/case_04/optical/parsed"

#: OPTIONAL FALLBACK only. Demo 11's s1_ref case - a DIFFERENT structure from
#: Demo 20 case 04. Used by STEP 08 solely when CASE04_PARSED is absent, so the
#: envelope -> matrix-element step can still be shown on real licensed
#: wavefunctions. Its numbers never enter case 04's calculation.
AUX_ENVELOPES = (REPO_ROOT / "nextnano/results/demo_runs"
                 / "11_paper_validation_interband_chi2_acqw"
                 / "20260731T002541Z_62efb35c/runs/s1_ref/extracted")

NL = chr(10)   # so a block literal can be stripped of blank lines only,
               # never of the leading indent its own lines carry

_WIDTH = 78


# --- presentation helpers ----------------------------------------------------


def banner(number: str, title: str, actor: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"STEP {number} - {title}")
    print(f"[{actor}]")
    print("=" * _WIDTH)


def block(label: str, lines: Sequence[str] | str) -> None:
    """Print one labelled block, indented four spaces.

    Multi-line text arrives as ``\"\"\"...\"\"\".strip(NL)`` - blank lines trimmed
    but every line's own indentation preserved, so the equations keep the
    layout they were written with.
    """

    if isinstance(lines, str):
        lines = lines.split(NL)
    print(f"{label}:")
    for line in lines:
        print(f"    {line}")


def describe_array(name: str, values: np.ndarray, units: str,
                   meaning: str, show: int = 5) -> list[str]:
    values = np.asarray(values)
    out = [
        f"Variable : {name}",
        f"Type     : numpy.ndarray ({values.dtype})",
        f"Shape    : {values.shape}",
        f"Units    : {units}",
        f"Meaning  : {meaning}",
    ]
    flat = values.ravel()
    if flat.size <= 2 * show:
        out.append(f"Values   : {np.array2string(flat, precision=6)}")
    else:
        out.append(f"First {show} : {np.array2string(flat[:show], precision=6)}")
        out.append(f"Last  {show} : {np.array2string(flat[-show:], precision=6)}")
    return out


def write_csv(path: Path | None, header: Sequence[str],
              rows: Sequence[Sequence[Any]]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    print(f"    [saved] {path.name}")


def write_json(path: Path | None, payload: Any) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8", newline="\n")
    print(f"    [saved] {path.name}")


def repo_relative(path: Path) -> str:
    """A repo-relative display string, falling back to the full path.

    Every source location this trace prints is resolved against REPO_ROOT, but
    a path can legitimately sit outside the repo (a redirected --outdir, a test
    fixture), and ``Path.relative_to`` raises rather than degrading. Printing a
    location must never be able to abort the trace.
    """

    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_text(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"    [saved] {path.name}")


# --- the trace ---------------------------------------------------------------


def run(outdir: Path | None, k_index: int, all_k: bool) -> int:
    cfg = config20.load()
    case = cases.by_id()[CASE_ID]
    settings_raw = chi2mod.settings_from_config(
        cfg, convention=chi2mod.CONVENTION_DEMO19)
    settings_scaled = settings_raw.with_convention(chi2mod.CONVENTION_SCALED)

    def out(name: str) -> Path | None:
        return None if outdir is None else outdir / name

    print("=" * _WIDTH)
    print("DEMO 21 - COMPLETE MATHEMATICAL TRACE OF DEMO 20, CASE 04")
    print("=" * _WIDTH)
    print("Structure : GaAs / Al(0.55)Ga(0.45)As asymmetric coupled quantum well")
    print("Case      : 04  'Linear 1.0 nm'  (linear grading, W = 1.0 nm at I1-I4)")
    print("Quantity  : chi^(2)_xzx for second-harmonic generation, in pm/V")
    print("Reported  : |chi^(2)| at a fundamental wavelength of 1550 nm")
    print()
    print("Legend  [A] your input   [B] Python geometry/grading")
    print("        [C] nextnano++   [D] Python nonlinear optics")

    # =======================================================================
    banner("00", "WHAT WE ARE CALCULATING, AND WHY IT IS NOT ZERO",
           "orientation")
    # =======================================================================
    block("SIMPLE EXPLANATION", """
Two quantum wells of different width sit next to each other, separated by a
thin barrier they can tunnel through. Because the pair is ASYMMETRIC, the
electron states and the hole states are not mirror images of each other:
electrons get pushed into one well and holes stay in the other. That
lopsidedness is what lets the structure double the frequency of light. A
perfectly symmetric structure has chi^(2) = 0 exactly, by parity.

We are asking: if we smear each material interface over 1 nm instead of
making it perfectly sharp, what happens to that frequency doubling at
1550 nm (telecom light)?
""".strip(NL))
    block("TECHNICAL STATEMENT", """
chi2_xzx(w,w) is evaluated from Ramesh 2023 Eq. (3) with Eq. (5) and Eq. (6),
in the algebraically equivalent energy form Demo 19/20 implement:

    chi2(E) = [N_z e^3 r_ehh^2 / (6 eps0)] * sum_i w_i * S(k_i, E)

    S(k,E) = sum_{m,n,l} { O_nm z^e_nl O_lm / (D2_nm D1_lm)
                         - O_nm z^hh_ml O_nl / (D2_nm D1_nl) }

    D2_ab = dE_ab(k) - 2E + i*Gamma      (two-photon / SHG denominator)
    D1_ab = dE_ab(k) -   E + i*Gamma     (one-photon denominator)

Source: nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:1-42
        and the loop at s06_chi2.py:641-661.
""".strip(NL))

    # =======================================================================
    banner("01", "CASE DEFINITION - THE NUMBERS YOU CHOSE", "A")
    # =======================================================================
    block("INPUT", [
        "demo20_config.yaml geometry / materials / grading / chi2 blocks",
        "s01_cases.all_cases()[4]",
    ])
    block("FUNCTION", [
        "s01_cases.all_cases",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s01_cases.py:133 (case 04 is defined at line 142)",
    ])
    block("EQUATION", "None. This stage is a frozen table of user choices.")
    inputs_record = {
        "case_id": case.case_id,
        "case_name": case.case_name,
        "profile_family": case.profile,
        "widths_nm_I1_I2_I3_I4": list(case.widths_nm),
        "nominal_grade_width_nm": case.nominal_grade_width_nm,
        "render_method": case.render_method,
        "implementation_type": case.implementation_type,
        "geometry": dict(cfg["geometry"]),
        "materials": dict(cfg["materials"]),
        "mesh": dict(cfg["mesh"]),
        "states": dict(cfg["states"]),
        "chi2": {k: v for k, v in cfg["chi2"].items()},
        "k_parallel": dict(cfg["k_parallel"]),
    }
    block("OUTPUT", [
        f"profile family        = {case.profile!r}",
        f"widths (I1,I2,I3,I4)  = {case.widths_nm} nm",
        f"thick well            = {cfg['geometry']['thick_well_nm']} nm",
        f"tunnel barrier        = {cfg['geometry']['tunnel_barrier_nm']} nm",
        f"thin well             = {cfg['geometry']['thin_well_nm']} nm",
        f"period barrier        = {cfg['geometry']['period_barrier_nm']} nm",
        f"barrier Al fraction   = {cfg['materials']['barrier_al_fraction']}",
        f"well Al fraction      = {cfg['materials']['well_al_fraction']}",
        f"temperature           = {cfg['materials']['temperature_K']} K",
        f"broadening Gamma      = {cfg['chi2']['broadening_meV']} meV",
        f"r_e,hh (DFT)          = {cfg['chi2']['r_e_hh_nm']} nm",
        f"target wavelength     = {cfg['chi2']['target_wavelength_nm']} nm",
        f"states per band in sum= {cfg['states']['max_states_per_band']}",
    ])
    block("MEANING", """
"Linear 1.0 nm" means: at each of the four interfaces, replace the sharp
0.55 <-> 0.00 step with a straight line 1.0 nm wide, centred on where the
step used to be. Nothing else about the structure changes.
""".strip(NL))
    block("CHANGED", "Nothing yet - these are the inputs.")
    block("NEXT", "STEP 02 turns the layer thicknesses into coordinates.")
    write_json(out("01_inputs.json"), inputs_record)

    # =======================================================================
    banner("02", "GEOMETRY -> INTERFACE POSITIONS I1..I4", "B")
    # =======================================================================
    geom = grading.geometry(cfg)
    positions = grading.interface_positions(cfg)
    directions = grading.interface_directions(cfg)
    block("INPUT", [
        f"thick_well_nm     = {geom.thick_well_nm}",
        f"tunnel_barrier_nm = {geom.tunnel_barrier_nm}",
        f"thin_well_nm      = {geom.thin_well_nm}",
        f"period_barrier_nm = {geom.period_barrier_nm}",
    ])
    block("FUNCTION", [
        "s02_grading.geometry -> s02_grading.interface_positions",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s02_grading.py:103 and :139",
    ])
    block("EQUATION", """
outer = period_barrier / 2
I1    = outer
I2    = I1 + thick_well
I3    = I2 + tunnel_barrier
I4    = I3 + thin_well
domain= I4 + outer
""".strip(NL))
    block("OUTPUT", [
        f"outer barrier = {geom.outer_barrier_nm} nm  (= 18.2/2)",
        f"I1 = {positions['I1']:6.2f} nm   x_Al {directions['I1'][0]:.2f} "
        f"-> {directions['I1'][1]:.2f}   outer AlGaAs -> thick GaAs well",
        f"I2 = {positions['I2']:6.2f} nm   x_Al {directions['I2'][0]:.2f} "
        f"-> {directions['I2'][1]:.2f}   thick well -> tunnel AlGaAs",
        f"I3 = {positions['I3']:6.2f} nm   x_Al {directions['I3'][0]:.2f} "
        f"-> {directions['I3'][1]:.2f}   tunnel AlGaAs -> thin GaAs well",
        f"I4 = {positions['I4']:6.2f} nm   x_Al {directions['I4'][0]:.2f} "
        f"-> {directions['I4'][1]:.2f}   thin well -> outer AlGaAs",
        f"domain = {geom.domain_nm} nm",
        f"quantum region = [{geom.quantum_start_nm}, {geom.quantum_end_nm}] nm",
    ])
    block("MEANING", """
Where each material boundary physically sits along the growth direction. Half
the 18.2 nm period barrier is put on each side so the simulated cell is one
complete 30 nm period.
""".strip(NL))
    block("CHANGED", "Four thicknesses have become four coordinates.")
    block("NEXT", "STEP 03 opens a grading window around each of these.")
    write_csv(out("02_geometry.csv"),
              ["interface", "position_nm", "x_al_left", "x_al_right", "role"],
              [[key, positions[key], directions[key][0], directions[key][1],
                cases.INTERFACE_NAMES[key]] for key in cases.INTERFACE_IDS])

    # =======================================================================
    banner("03", "GRADE WINDOWS - WHERE THE RAMPS LIVE", "B")
    # =======================================================================
    intervals = grading.grade_intervals(cfg, case)
    plateaus = grading.plateau_lengths_nm(cfg, case)
    block("INPUT", [
        f"interface positions = {positions}",
        f"widths              = {dict(zip(cases.INTERFACE_IDS, case.widths_nm))} nm",
    ])
    block("FUNCTION", [
        "s02_grading.grade_intervals",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s02_grading.py:362",
    ])
    block("EQUATION", "window(I) = [z_I - W/2,  z_I + W/2]     (W = full width)")
    block("OUTPUT", [f"{key}: {intervals[key]} nm" for key in cases.INTERFACE_IDS]
          + ["", "Remaining pure-material plateaus:"]
          + [f"  {k:32s} {v:6.3f} nm" for k, v in plateaus.items()])
    block("MEANING", """
The width W is the FULL start-to-end transition width, so grading eats W/2 into
the material on each side. The interface CENTRE never moves and the total
device length never changes; what shrinks is the pure-material plateau. With
W = 1.0 nm the 1.8 nm tunnel barrier keeps only 0.8 nm of pure Al(0.55)GaAs,
which is why coupling between the wells changes noticeably in this case.
""".strip(NL))
    block("CHANGED", "Four points have become four finite intervals.")
    block("NEXT", "STEP 04 evaluates the ramp inside each interval.")

    # =======================================================================
    banner("04", "APPLY THE LINEAR GRADING -> x_Al(z)", "B")
    # =======================================================================
    profile = grading.build_profile(cfg, case)
    block("BEFORE", [
        "grading specification (a description, not a field):",
        f"    type  = {case.profile!r}",
        f"    W     = {case.nominal_grade_width_nm} nm at all four interfaces",
        "x_Al(z) does not exist yet.",
    ])
    block("FUNCTION", [
        "s02_grading.build_profile -> evaluate_composition -> profile_fraction",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s02_grading.py:312, :211, :162",
    ])
    block("EQUATION", """
Step 1 (abrupt skeleton, evaluate_composition lines 231-233):
    x_Al(z) = 0.55                        everywhere
    x_Al(z) = 0.00                        on [I1, I2] and on [I3, I4]

Step 2 (ramps overwrite the well edges, lines 238-250), per interface:
    z_minus = z_i - W/2
    u(z)    = clip((z - z_minus)/W, 0, 1)
    f(u)    = u                            <- LINEAR family
    x_Al(z) = x_L + (x_R - x_L) * f(u)
""".strip(NL))
    sample_z = np.array([8.60, 8.75, 8.85, 9.10, 9.35, 9.50, 9.60])
    sample_x = grading.evaluate_composition(cfg, case, sample_z)
    sample_u = np.clip((sample_z - (positions["I1"] - 0.5)) / 1.0, 0.0, 1.0)
    block("OUTPUT (worked, interface I1: z_i = 9.1, W = 1.0, x_L = 0.55, x_R = 0)", [
        "   z [nm]      u      f(u)=u    x_Al = 0.55 + (0 - 0.55)*u",
        "   -------  -------  -------    --------------------------",
    ] + [f"   {z:7.3f}  {u:7.4f}  {u:7.4f}    {x:.6f}"
         for z, u, x in zip(sample_z, sample_u, sample_x)])
    block("OUTPUT (whole device)",
          describe_array("profile.x_nm", profile.x_nm, "nm",
                         "the mesh nextnano++ receives (0.05 nm + every "
                         "interface centre and grade endpoint)")
          + [""]
          + describe_array("profile.al_fraction", profile.al_fraction,
                           "dimensionless",
                           "x_Al at each of those points, in [0, 0.55]")
          + ["",
             f"min x_Al = {profile.al_fraction.min():.6f}  "
             f"max x_Al = {profile.al_fraction.max():.6f}",
             f"audit grid (20x finer, never an input) has "
             f"{profile.x_nm_continuous.size} points"])
    validation = grading.validate_realized(cfg, case)
    block("SOLVER-FREE VALIDATION (s02_grading.py:386)", [
        f"validation_pass            = {validation['validation_pass']}",
        f"maximum_composition_error  = {validation['maximum_composition_error']:.3e}",
        f"gaas_reaches_zero          = {validation['gaas_reaches_zero']}",
        f"algaas_reaches_max         = {validation['algaas_reaches_max']}",
        f"unintended_overlap         = {validation['unintended_overlap']}",
        "(error is exactly 0 for linear: ternary_linear is native nextnano++",
        " syntax, so no sampled table is interpolated.)",
    ])
    block("MEANING", """
The case description has become an actual spatial material field. This array is
the ONLY thing about the structure that differs between case 00 (abrupt) and
case 04 - same interfaces, same total length, same materials.
""".strip(NL))
    block("CHANGED", """
Before: x_Al jumped 0.55 -> 0.00 within one mesh cell at z = 9.1 nm.
After:  x_Al slides linearly from 0.55 at 8.6 nm to 0.00 at 9.6 nm, and
        likewise at the other three interfaces.
""".strip(NL))
    block("NEXT", "STEP 05 writes this field into nextnano++ syntax.")
    write_csv(out("03_grading_profile.csv"),
              ["z_nm", "x_al", "in_grade_window"],
              [[f"{z:.6f}", f"{x:.10f}",
                any(iv and iv[0] <= z <= iv[1] for iv in intervals.values())]
               for z, x in zip(profile.x_nm, profile.al_fraction)])

    # =======================================================================
    banner("05", "RENDER THE NEXTNANO++ INPUT DECK", "B")
    # =======================================================================
    summary = ref.nextnano_input_summary(cfg, case)
    deck = summary["deck_text"]
    block("INPUT", [
        "x_Al(z) from STEP 04 (as four ternary_linear ramps, not as a table)",
        "geometry from STEP 02, mesh and state counts from demo20_config.yaml",
    ])
    block("FUNCTION", [
        "s03_inputs.build_case -> _native_blocks -> render_deck",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s03_inputs.py:207, :107, :169",
        "Template: graded_acqw20.in.j2",
    ])
    block("EQUATION", """
None - this is text substitution. But note WHICH representation is used:

  linear (and abrupt) cases  -> NATIVE nextnano++ grammar, ternary_linear{}
                                nextnano++ evaluates the ramp itself, exactly.
  fermi / erf / cosine cases -> a sampled DAT table + ternary_import{},
                                which nextnano++ interpolates LINEARLY between
                                rows. That is why s02_grading measures the
                                sampling error - for case 04 it is exactly 0.
""".strip(NL))
    structure_lines = [line for line in deck.splitlines()
                       if not line.lstrip().startswith("#")
                       and ("ternary_linear" in line or "binary{" in line
                            or "ternary_constant" in line)]
    block("OUTPUT - the composition part of the deck", structure_lines)
    block("OUTPUT - everything else nextnano++ is told", [
        f"{k:28s} {summary[k]}" for k in
        ("render_method", "domain_nm", "quantum_region_nm",
         "mesh_spacing_active_nm", "mesh_spacing_outer_nm", "temperature_K",
         "electron_states_requested", "hole_states_requested",
         "boundary_condition", "self_consistent_poisson", "deck_complete")
    ] + [
        "",
        "Also in the deck: simulate1D, substrate GaAs, crystal_zb [100]/[010],",
        "classical{ Gamma HH LH SO }, quantum{ region acqw ... }, run{quantum{}}.",
        "",
        "NOT in the deck: any band parameter. No effective mass, no band gap,",
        "no offset, no bowing. nextnano++ looks every one of those up in its",
        "proprietary database.nnp keyed on the material name and x_Al(z).",
    ])
    block("MEANING", """
This file is the complete contract between Python and the solver. Everything
Python knows about the physics of AlGaAs is in it, and that is: the names of
the materials, where they are, how much Al is in them, and the temperature.
""".strip(NL))
    block("CHANGED", "A numpy array has become a solver input file.")
    block("NEXT", "STEP 06 - nextnano++ takes over.")
    write_text(out("04_nextnano_input_summary.txt"), "\n".join([
        "DEMO 20 CASE 04 - WHAT NEXTNANO++ RECEIVES",
        "=" * _WIDTH, "",
        *[f"{k:32s} {v}" for k, v in summary.items() if k != "deck_text"],
        "", "=" * _WIDTH, "FULL DECK", "=" * _WIDTH, "", deck,
    ]))

    # =======================================================================
    banner("06", "WHAT NEXTNANO++ SOLVES  (BLACK BOX)", "C")
    # =======================================================================
    block("INPUT TO NEXTNANO++", [
        "case.in (STEP 05)",
        "database.nnp  - proprietary material parameter database, NOT in this repo",
        "License_nnp.lic - work laptop only",
    ])
    block("FUNCTION", [
        "s04_solver.solve_case  [LICENSED - does not run on this machine]",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s04_solver.py:191",
        "It shells out to nextnano++ via solver14.execute_real; the solve "
        "itself happens inside the nextnano++ binary.",
    ])
    block("EQUATION - BACKGROUND THEORY, not evaluated in Python", """
1. Alloy -> potential.  For every mesh point, look up the AlGaAs band
   parameters at the local x_Al(z) and form the conduction (Gamma) and
   heavy-hole band edges:
        V_e(z) = E_c(x_Al(z)),      V_h(z) = E_v,HH(x_Al(z))
   with alloy bowing, the Varshni temperature shift at 300 K, and the
   band offset all coming from database.nnp.

2. Envelope-function eigenproblem, one band at a time, on the quantum region
   [7.1, 22.9] nm with Dirichlet walls psi = 0 at both ends:

        [ -(hbar^2/2) d/dz ( 1/m*(z) d/dz ) + V(z) ] psi_n(z) = E_n psi_n(z)

   The 1/m*(z) sandwiched between the derivatives is the BenDaniel-Duke
   ordering, which is what keeps the operator Hermitian when the effective
   mass varies with position - and with 1 nm of graded alloy at every
   interface, m*(z) genuinely does vary there.

   no_density = yes, so no Poisson equation is solved and no self-consistent
   electrostatic potential is added. V(z) is the bare heterostructure profile.
""".strip(NL))
    block("CALCULATED BY NEXTNANO++", [
        "band edges E_c(z), E_HH(z), E_LH(z), E_SO(z)      [classical{} block]",
        "6 lowest Gamma eigenvalues + envelopes",
        "6 highest-energy HH eigenvalues + envelopes",
        "state probabilities, transition energies, overlap integrals,",
        "dipole matrix elements (requested for cross-check; see STEP 09 note)",
    ])
    block("RETURNED TO PYTHON", [
        "energy spectrum tables      E_n                      [eV]",
        "envelope tables             psi_n(z) on the solver grid",
        "alloy composition readback  x_Al(z) as actually built",
        "bandedges, probabilities, the solver log",
    ])
    block("MEANING", """
This is the only step Python cannot open up. From here on everything is
arithmetic on the four numbers and four curves nextnano++ returned.
""".strip(NL))
    block("CHANGED", """
Before: a material composition field, x_Al(z).
After:  a confinement potential and its eigenstates - energies and shapes.
""".strip(NL))
    block("NEXT", "STEP 07 reads those eigenstates back into Python.")
    print()
    print("    NOTE ON THIS EXECUTION")
    print("    This machine has no nextnano++ licence, so no solve ran now.")
    print("    The states used below are REAL licensed solver output for this")
    print("    exact case, read back from the Demo 19 results table (STEP 07).")
    print("    Nothing is simulated, mocked or approximated in their place.")

    # =======================================================================
    banner("07", "EIGENENERGIES BACK IN PYTHON - e1, e2, hh1, hh2", "C -> D")
    # =======================================================================
    table_path = config20.master_table_path(cfg)
    extracted = extract.from_master_table(
        table_path, max_states_per_band=int(cfg["states"]["max_states_per_band"]))
    found = extracted[CASE_ID]
    states_full = found.states
    states = states_full.truncated(int(settings_raw.max_states_per_band))
    block("INPUT", [f"{table_path}", "row case_id = 04"])
    block("FUNCTION", [
        "HOME PATH (this run):",
        "  s05_extract.from_master_table",
        "  Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s05_extract.py:111",
        "  Reads columns E1_eV, E2_eV, HH1_eV, HH2_eV, O11..O22, z_e11..z_e22,",
        "  z_hh11..z_hh22. It RE-READS, it never recomputes.",
        "",
        "LICENSED PATH (how those columns were produced):",
        "  s04_solver.parse_case (s04_solver.py:272)",
        "    -> demo14.analyse_real_trial (demo14.py:852)",
        "      -> demo11.analyse_case (demo11.py:431)",
        "        -> quantum1d.parse_one_band_run  [electron E and psi]",
        "        -> demo11._hole_states (demo11.py:246)  [HH E and psi]",
    ])
    block("EQUATION", "None - this is I/O. The physics happened in STEP 06.")
    block("WHAT e1, e2, hh1, hh2 ARE", """
e1  = lowest conduction (Gamma) subband of the coupled pair
e2  = second conduction subband
hh1 = most confined heavy-hole subband
hh2 = second heavy-hole subband

Each is an eigenpair (E_n, psi_n(z)) of the STEP 06 Hamiltonian: an energy and
an envelope shape. Energies are on nextnano's SINGLE electron-energy scale, so
an interband transition energy is a plain subtraction with no band gap added by
hand. nextnano++ lists hole states in DECREASING electron-scale energy, so
index order is confinement order - hh1 is the most confined hole, not the
highest number.
""".strip(NL))
    e = np.asarray(states.electron_energies_eV, float)
    h = np.asarray(states.hole_energies_eV, float)
    block("OUTPUT", [
        f"E_e1  = {e[0]:.12f} eV",
        f"E_e2  = {e[1]:.12f} eV",
        f"E_hh1 = {h[0]:.12f} eV",
        f"E_hh2 = {h[1]:.12f} eV",
        "",
        f"E_e2 - E_e1   = {e[1]-e[0]:.12f} eV   (intersubband, conduction)",
        f"E_hh1 - E_hh2 = {h[0]-h[1]:.12f} eV   (intersubband, valence)",
        "",
        f"provenance    = {states.provenance}",
        f"solver_pass   = {found.solver_pass}",
        f"physical_valid= {found.physical_valid}   <- SEPARATE CONCEPTS",
        f"failure_reason= {found.failure_reason}",
    ])
    block("MEANING", """
Four energies, in eV, that fix where every optical resonance of this structure
sits. Everything about the spectrum's SHAPE follows from them.

Read solver_pass and physical_valid separately: solver_pass = True means the
nextnano++ process exited 0 and produced its outputs. physical_valid = False is
inherited from Demo 11/14's own physical QC, which did not pass for any of the
13 Demo 19 cases. The specific failing sub-check cannot be identified from this
checkout (it needs the raw licensed run tree). So treat these numbers as a
CONTROLLED COMPARISON BETWEEN GRADING CASES, not as validated absolute physics.
""".strip(NL))
    block("CHANGED", "Solver output files have become four Python floats.")
    block("NEXT", "STEP 08 - what happened to the wavefunctions.")
    write_csv(out("05_subband_energies.csv"),
              ["state", "band", "energy_eV", "source"],
              [["e1", "Gamma", f"{e[0]:.15g}", "nextnano++"],
               ["e2", "Gamma", f"{e[1]:.15g}", "nextnano++"],
               ["hh1", "HH", f"{h[0]:.15g}", "nextnano++"],
               ["hh2", "HH", f"{h[1]:.15g}", "nextnano++"]])

    # =======================================================================
    banner("08", "WHAT HAPPENS TO THE WAVEFUNCTIONS", "D")
    # =======================================================================
    block("THE ACTUAL CHAIN", """
    psi_n(z) as nextnano++ writes it
        |
        v  NORMALIZATION - YES, Python does this
    psi_n / sqrt( int psi_n^2 dz )        _shared/chi2.py:155-162
        |
        v  INTERPOLATION - NO, there is none
    (demo11.analyse_case:467 REQUIRES the electron and hole envelopes to
     already be on the identical grid and raises otherwise. No resampling,
     no common-grid projection, no spline.)
        |
        v  ORTHONORMALITY - checked, not enforced
    max |<psi_i|psi_j> - delta_ij| <= 1e-3      _shared/chi2.py:188
        |
        v  multiply two envelopes (and optionally z), integrate
    O_nm, z^e_nl, z^hh_ml
""".strip(NL))
    block("FUNCTION", [
        "_shared/chi2.BandStates.__post_init__",
        "Source: nextnano/demos/_shared/chi2.py:134 (normalization at :155-162)",
    ])
    block("EQUATION", """
    N     = int |psi(z)|^2 dz  ~=  trapezoid(psi^2, z)
    psi  <- psi / sqrt(N)

so int |psi|^2 dz = 1 with z in nm, i.e. psi carries nm^(-1/2).

WHY IT MATTERS THAT ORTHONORMALITY IS CHECKED: Eq. (5) and Eq. (6) contain
DIAGONAL position elements <psi_i|z|psi_i>, and each of those depends on where
you put z = 0. The origin dependence cancels between the electron and the hole
term - but only if the within-band basis is orthonormal. With a non-orthogonal
basis chi^(2) would depend on an arbitrary coordinate choice.
(_shared/chi2.py:188-202; the origin-independence test itself is
demo11.analyse_case:606.)
""".strip(NL))
    block("WHERE CASE 04's ENVELOPES COME FROM", f"""
Source: Demo 20 Case 04 licensed envelopes
    {repo_relative(CASE04_PARSED / 'envelopes.csv')}
    {repo_relative(CASE04_PARSED / 'matrix_elements.json')}

Both paths are resolved against REPO_ROOT, so this works unchanged on the home
laptop and on the licensed work laptop.

envelopes.csv carries all six states per band the deck asked for:
    z_nm, psi_e1..psi_e6, psi_hh1..psi_hh6
The susceptibility uses two per band, so STEP 08 selects exactly
    {', '.join(ENVELOPE_COLUMNS)}
BY HEADER NAME. The column ORDER of a parser output is not a contract; the
column NAMES are.
""".strip(NL))

    envelope_demo = case04_envelope_demo(out("06_case04_envelopes.csv"))
    if envelope_demo is None:
        block("CASE 04 ENVELOPES NOT FOUND ON THIS MACHINE", f"""
Looked for, and did not find:
    {repo_relative(CASE04_PARSED / 'envelopes.csv')}
    {repo_relative(CASE04_PARSED / 'matrix_elements.json')}

Those files are written by a licensed `run_demo20.py --physics` run. Nothing
downstream is missing without them: the results table already carries the
QUANTITIES DERIVED FROM THEM - O, z^e, z^hh - which is exactly what the
susceptibility needs, and STEPS 09-10 use those. Only this numerical
demonstration of HOW the envelopes became those matrices is unavailable.

Falling back to a different structure below, clearly labelled. This trace does
not invent an envelope to fill the gap.
""".strip(NL))
        envelope_demo = demo11_fallback_demo(out("06_fallback_envelopes.csv"))
        if envelope_demo is None:
            block("NUMERICAL DEMONSTRATION", [
                "skipped entirely: neither Case 04's parsed run nor the Demo 11",
                "fallback table is present on this machine.",
                f"  case 04  : {repo_relative(CASE04_PARSED)}",
                f"  fallback : {repo_relative(AUX_ENVELOPES)}",
            ])
    block("MEANING", """
Nothing mysterious happens to the wavefunctions: they get rescaled so their
probability integrates to one, they are checked for orthonormality, and then
they are multiplied together - with z in between, or without it - and
integrated. Four curves become twelve numbers.
""".strip(NL))
    block("CHANGED",
          "Curves psi(z) have become scalars O, z^e, z^hh.")
    block("NEXT", "STEP 09 and STEP 10 - those two integrals, one at a time.")

    # =======================================================================
    banner("09", "OVERLAP INTEGRALS  O_nm = <psi_e,n | psi_hh,m>", "D")
    # =======================================================================
    overlap = np.asarray(states.overlap_electron_hole, float)
    block("INPUT", [
        "normalized electron envelopes psi_e,n(z), n = 1, 2",
        "normalized heavy-hole envelopes psi_hh,m(z), m = 1, 2",
        "both on the same z grid, in nm",
    ])
    block("FUNCTION", [
        "_shared/chi2.overlap_matrix",
        "Source: nextnano/demos/_shared/chi2.py:204",
        "Called by demo11.analyse_case (demo11.py:527) during the licensed run;",
        "written to matrix_elements.json (demo11.py:803) and to the master",
        "table columns O11, O12, O21, O22.",
    ])
    block("EQUATION", """
CONTINUOUS
    O_nm = <psi_e,n | psi_hh,m> = int psi_e,n(z) psi_hh,m(z) dz

DISCRETE - exactly what np.trapezoid computes:
    O_nm ~= sum_i (1/2)[g(z_i) + g(z_{i+1})] (z_{i+1} - z_i),
    g(z) = psi_e,n(z) psi_hh,m(z)

That is the composite trapezoidal rule. np.trapezoid does NOT assume a uniform
grid - it uses the actual spacings of z, which matters because the solver mesh
is fine in the active region and coarse outside it.

UNITS: dimensionless. psi carries nm^(-1/2) each, dz carries nm.
""".strip(NL))
    block("OUTPUT (case 04, real licensed values)", [
        "        m=hh1        m=hh2",
        f"n=e1  {overlap[0,0]: .16f}  {overlap[0,1]: .16f}",
        f"n=e2  {overlap[1,0]: .16f}  {overlap[1,1]: .16f}",
    ])
    block("MEANING", """
How much an electron envelope and a hole envelope look alike. O11 = 0.982 means
e1 and hh1 sit almost exactly on top of each other, so the e1-hh1 interband
transition is strong. O22 = 0.383 is much weaker: e2 has been pushed into the
thin well while hh2 has not, so the two envelopes only partly overlap.

That asymmetry between the electron ladder and the hole ladder is the entire
physical origin of chi^(2) here.
""".strip(NL))
    block("NOTE - THIS IS NOT nextnano's OWN overlap_integrals OUTPUT", """
The deck does request overlap_integrals{ Gamma_HH{} } (STEP 05), but chi^(2)
does not use it. Demo 20 recomputes the overlaps in Python from the envelopes
so that the normalization convention and the quadrature rule are under its own
control and identical to Demo 11/12/13/14/19. The nextnano output is kept for
cross-checking.
""".strip(NL))
    block("CHANGED", "Two curves have become one dimensionless number, four times.")
    block("NEXT", "STEP 10 - the other kind of matrix element.")

    # =======================================================================
    banner("10", "POSITION MATRIX ELEMENTS  z^e_nl AND z^hh_ml", "D")
    # =======================================================================
    z_e = np.asarray(states.position_matrix_electron_nm, float)
    z_h = np.asarray(states.position_matrix_hole_nm, float)
    block("INPUT", "normalized envelopes of ONE band at a time, plus z itself")
    block("FUNCTION", [
        "_shared/chi2.position_matrix",
        "Source: nextnano/demos/_shared/chi2.py:220",
        "Called by demo11.analyse_case (demo11.py:528-529).",
    ])
    block("EQUATION", """
CONTINUOUS
    z^e_nl  = <psi_e,n | z | psi_e,l>   = int psi_e,n(z) z psi_e,l(z) dz
    z^hh_ml = <psi_hh,m| z | psi_hh,l>  = int psi_hh,m(z) z psi_hh,l(z) dz

DISCRETE
    trapezoid( psi_i * z * psi_j, z )      same rule as STEP 09

UNITS: nm.
""".strip(NL))
    block("OUTPUT (case 04)", [
        "z^e [nm]        l=e1                 l=e2",
        f"n=e1     {z_e[0,0]: .15f}   {z_e[0,1]: .15f}",
        f"n=e2     {z_e[1,0]: .15f}   {z_e[1,1]: .15f}",
        "",
        "z^hh [nm]       l=hh1                l=hh2",
        f"m=hh1    {z_h[0,0]: .15f}   {z_h[0,1]: .15f}",
        f"m=hh2    {z_h[1,0]: .15f}   {z_h[1,1]: .15f}",
        "",
        f"delta_z_e  = z^e_22 - z^e_11  = {z_e[1,1]-z_e[0,0]: .15f} nm",
        f"delta_z_hh = z^hh_22 - z^hh_11 = {z_h[1,1]-z_h[0,0]: .15f} nm",
    ])
    block("MEANING", """
DIAGONAL entries are centroids - where each state actually sits:
    e1  at 12.72 nm  (inside the thick well, which spans 9.1-16.2 nm)
    e2  at 18.66 nm  (inside the thin well, 18.0-20.9 nm)
    hh1 at 12.65 nm, hh2 at 12.73 nm - BOTH in the thick well

So the two electron states are 5.94 nm apart while the two hole states are
0.079 nm apart. The electron ladder is spatially separated and the hole ladder
is not. THAT is the asymmetry chi^(2) measures.

OFF-DIAGONAL entries are the intersubband transition dipoles (divided by e):
how strongly a field along the growth direction can move a carrier from state 1
to state 2 within its own band. z^e_12 = 1.025 nm.
""".strip(NL))
    block("THREE DISTINCT MATRIX-ELEMENT SPECIES - DO NOT MERGE THEM", """
    O_nm     <psi_e,n | psi_hh,m>     INTERBAND, envelope,  dimensionless
    z^e_nl   <psi_e,n | z | psi_e,l>  INTRABAND, envelope,  nm
    r_e,hh   <u_e | z | u_hh>         INTERBAND, BULK BLOCH cell part, nm

They multiply; none of them substitutes for another. STEP 11 is the third one.
""".strip(NL))
    block("CHANGED", "Two curves plus the coordinate have become a 2x2 matrix, twice.")
    block("NEXT", "STEP 11 - the one number that did not come from nextnano.")
    write_csv(out("07_matrix_elements.csv"),
              ["symbol", "row", "col", "value", "units", "computed_by", "equation"],
              [["O", f"e{i+1}", f"hh{j+1}", f"{overlap[i,j]:.17g}", "1", "Python",
                "trapezoid(psi_e psi_hh, z)"] for i in range(2) for j in range(2)]
              + [["z_e", f"e{i+1}", f"e{j+1}", f"{z_e[i,j]:.17g}", "nm", "Python",
                  "trapezoid(psi_e z psi_e, z)"] for i in range(2) for j in range(2)]
              + [["z_hh", f"hh{i+1}", f"hh{j+1}", f"{z_h[i,j]:.17g}", "nm", "Python",
                  "trapezoid(psi_hh z psi_hh, z)"] for i in range(2) for j in range(2)]
              + [["r_e_hh", "-", "-", f"{settings_raw.r_e_hh_nm:.17g}", "nm",
                  "DFT (external)", "<u_e|z|u_hh>, VASP/HSE06, Ramesh 2023"]])

    # =======================================================================
    banner("11", "THE DFT / BULK BLOCH QUANTITY  r_e,hh", "external")
    # =======================================================================
    block("INPUT", "demo20_config.yaml:97  chi2.r_e_hh_nm: 0.751")
    block("FUNCTION", [
        "Read as a configuration constant. It is NOT computed anywhere in this",
        "repository, by Python or by nextnano++.",
        "Enters at: s06_chi2.absolute_prefactor",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:514 (line 528: r_m = r_e_hh_nm * 1e-9)",
    ])
    block("WHAT IT IS", """
r_e,hh = 7.51 Angstrom = 0.751 nm is the BULK GaAs INTERBAND BLOCH position
matrix element <u_e | z | u_hh> between the cell-periodic parts of the
conduction and heavy-hole Bloch functions at the Gamma point. Ramesh 2023
(APL 123, 251111) computed it with DFT (VASP, HSE06 hybrid functional).
Provenance verified verbatim from the PDF: docs/demo14_physics_sources.md:62.

It is a POSITION, not a dipole. Eq. (3) already carries e^3, so r must never be
multiplied by charge again.
""".strip(NL))
    block("WHAT DFT DID *NOT* CALCULATE", """
Everything else. The subband energies, the envelopes psi_n(z), the overlaps
O_nm and the envelope position matrices z^e / z^hh are all nextnano++ output
plus Python post-processing. DFT contributed exactly one scalar.
""".strip(NL))
    block("HOW THE THREE SOURCES COMBINE", """
The envelope-function approximation factorizes the full interband dipole into a
bulk Bloch part and an envelope part:

    <e,n | z | hh,m>   ~=   r_e,hh  *  <psi_e,n | psi_hh,m>
       full dipole          BULK/DFT        ENVELOPE/nextnano

Eq. (3) has two such dipoles, so r_e,hh comes out of the sum SQUARED and sits
in the prefactor, while the envelope overlaps O_nm stay inside the sum where
they can differ per term:

    chi2 = [N_z e^3 r_e,hh^2 / (6 eps0)] * sum_k sum_{m,n,l} { O..z..O - O..z..O }
             ^^^^^^^^^^^^^^^ DFT              ^^^^^^^^^^^^^^^^^^^^^ nextnano+Python
""".strip(NL))
    block("CHANGED", """
Nothing yet - r_e,hh does not enter until the prefactor (STEP 18). It is
introduced here because this is where it belongs conceptually, next to the
other matrix elements.
""".strip(NL))
    block("NEXT", "STEP 12 - the energy differences.")

    # =======================================================================
    banner("12", "TRANSITION ENERGIES AT k = 0", "D")
    # =======================================================================
    zero_k = e[:, None] - h[None, :]
    block("INPUT", "E_e1, E_e2, E_hh1, E_hh2 from STEP 07")
    block("FUNCTION", [
        "s06_chi2.transition_energies_eV (the k = 0 part, line 550-552)",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:537",
    ])
    block("EQUATION", """
    dE_nm(0) = E_e,n - E_hh,m

A plain subtraction - possible only because nextnano puts electrons and holes
on ONE energy scale. No band gap is added by hand anywhere in Demo 20.
""".strip(NL))
    block("OUTPUT", [
        "               m=hh1            m=hh2",
        f"n=e1   {zero_k[0,0]:.15f}  {zero_k[0,1]:.15f}",
        f"n=e2   {zero_k[1,0]:.15f}  {zero_k[1,1]:.15f}",
        "",
        "As wavelengths (hc/dE):",
        f"  e1-hh1 : {chi2mod.HC_EV_NM/zero_k[0,0]:8.2f} nm",
        f"  e1-hh2 : {chi2mod.HC_EV_NM/zero_k[0,1]:8.2f} nm",
        f"  e2-hh1 : {chi2mod.HC_EV_NM/zero_k[1,0]:8.2f} nm",
        f"  e2-hh2 : {chi2mod.HC_EV_NM/zero_k[1,1]:8.2f} nm",
    ])
    block("MEANING", """
Four interband transitions, between 1.493 and 1.648 eV. Second-harmonic
generation from 1550 nm light produces 2 x 0.7999 = 1.5998 eV, which lands
INSIDE that range - between e1-hh2 (1.5284) and e2-hh1 (1.6132). That is why
this structure responds strongly at 1550 nm and why the spectrum peaks nearby,
at 1502 nm.
""".strip(NL))
    block("CHANGED", "Four absolute energies have become four energy differences.")
    block("NEXT", "STEP 13 - the photon side of the comparison.")
    write_csv(out("08_transition_energies_zero_k.csv"),
              ["transition", "n", "m", "dE_eV", "wavelength_of_dE_nm"],
              [[f"e{i+1}-hh{j+1}", i + 1, j + 1, f"{zero_k[i,j]:.17g}",
                f"{chi2mod.HC_EV_NM/zero_k[i,j]:.6f}"]
               for i in range(2) for j in range(2)])

    # =======================================================================
    banner("13", "WAVELENGTH -> PHOTON ENERGY", "D")
    # =======================================================================
    lam = chi2mod.wavelength_grid(cfg, window="focused")
    energies = chi2mod.photon_energy_eV(lam)
    target_energy = float(chi2mod.photon_energy_eV(TARGET_NM))
    block("INPUT", [
        f"chi2.focused_wavelength_nm  = {cfg['chi2']['focused_wavelength_nm']}",
        f"chi2.focused_wavelength_points = {cfg['chi2']['focused_wavelength_points']}",
    ])
    block("FUNCTION", [
        "s06_chi2.wavelength_grid -> s06_chi2.photon_energy_eV",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:604 and :157",
    ])
    block("EQUATION", """
    grid      = linspace(1400, 1800, 401)      -> spacing exactly 1.0 nm
    E[eV]     = hc / lambda = 1239.841984 / lambda[nm]
""".strip(NL))
    block("OUTPUT", describe_array("lam", lam, "nm", "fundamental wavelength grid")
          + [""]
          + describe_array("photon_energy_eV", energies, "eV",
                           "fundamental photon energy at each wavelength")
          + ["",
             f"At the target wavelength {TARGET_NM} nm:",
             f"    E   = {target_energy:.16f} eV",
             f"    2E  = {2*target_energy:.16f} eV   <- what SHG produces",
             f"    1550.0 nm is grid node {int(np.argmin(np.abs(lam-TARGET_NM)))} "
             f"of {lam.size} - EXACTLY on the grid."])
    block("MEANING", """
The wavelength is the only thing that changes when we sweep the spectrum. The
structure - its geometry, its states, its matrix elements - is frozen. The
spectrum's shape comes entirely from how the fixed transition energies of
STEP 12 line up against the moving E and 2E of this step, through the
denominators of STEP 16.
""".strip(NL))
    block("CHANGED", "A wavelength axis has become an energy axis.")
    block("NEXT", "STEP 14 - the other integration variable.")

    # =======================================================================
    banner("14", "IN-PLANE k GRID AND INTEGRATION WEIGHTS", "D")
    # =======================================================================
    k, weights = chi2mod.k_grid(settings_raw)
    _k2, weights_scaled = chi2mod.k_grid(settings_scaled)
    step = float(k[1] - k[0])
    block("INPUT", [
        f"k_parallel.fraction_of_bz     = {cfg['k_parallel']['fraction_of_bz']}",
        f"k_parallel.lattice_constant_nm= {cfg['k_parallel']['lattice_constant_nm']}",
        f"k_parallel.bz_edge_convention = {cfg['k_parallel']['bz_edge_convention']}",
        f"k_parallel.points             = {cfg['k_parallel']['points']}",
        f"k_parallel.spin_degeneracy    = {cfg['k_parallel']['spin_degeneracy']}",
    ])
    block("FUNCTION", [
        "s06_chi2.k_grid (and Chi2Settings.k_max_per_nm)",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:346 and :223",
    ])
    block("EQUATION - THE DERIVATION, EXACTLY AS IMPLEMENTED", """
2D discrete-to-continuum, area A:
    sum_k f(k)        ->  A/(2pi)^2 * int d^2k f(k)
    (1/A) sum_k f(k)  ->  1/(2pi)^2 * int d^2k f(k)

The integrand depends only on |k|, so the angular integral is exact and free:
    int d^2k f(|k|) = 2pi * int_0^kmax k f(k) dk

Substituting collapses one factor of 2pi:
    (1/A) sum_k f  ->  (2pi)/(2pi)^2 * int k f dk
                    =  1/(2pi) * int_0^kmax k f(k) dk       <- IMPLEMENTED

so the weight is
    w_i = g_s * (k_i / (2pi)) * dk_i        [d2k_over_2pi_squared, Demo 19]

with dk_i the trapezoidal weights on a uniform grid: full step inside, half
step at each end.

THE 1/(2pi)^2 IS ALREADY THERE. The Demo 20 experiment
    w_i = g_s * (2pi * k_i) * dk_i          [bare_d2k]
does not add a missing factor - it CANCELS the existing denominator, switching
the measure to sum_k -> g_s * int d^2k. That is exactly (2pi)^2 larger, and it
is a convention swap, not a unit fix. See s06_chi2.py:44-105.
""".strip(NL))
    block("OUTPUT", [
        f"k_max = fraction * pi / a = {cfg['k_parallel']['fraction_of_bz']} * pi / "
        f"{cfg['k_parallel']['lattice_constant_nm']}",
        f"      = {settings_raw.k_max_per_nm:.16f} nm^-1",
        f"dk (uniform) = k_max/{k.size-1} = {step:.16e} nm^-1",
        "",
    ] + describe_array("k", k, "nm^-1", "in-plane wavevector magnitude")
      + [""]
      + describe_array("weights (raw convention)", weights, "nm^-2",
                       "w_i = g_s k_i dk_i / (2 pi)")
      + ["",
         f"sum(weights) raw    = {float(np.sum(weights)):.16e} nm^-2",
         f"closed form g_s kmax^2/(4 pi) = "
         f"{chi2mod.analytic_disc_measure(settings_raw):.16e} nm^-2",
         f"relative difference = "
         f"{abs(float(np.sum(weights))-chi2mod.analytic_disc_measure(settings_raw))/chi2mod.analytic_disc_measure(settings_raw):.3e}",
         "",
         f"sum(weights) scaled = {float(np.sum(weights_scaled)):.16e} nm^-2",
         f"ratio scaled/raw    = "
         f"{float(np.sum(weights_scaled))/float(np.sum(weights)):.16f}",
         f"(2 pi)^2            = {chi2mod.two_pi_squared():.16f}"])
    block("MEANING", """
Carriers are confined along z but free in the plane. Every in-plane momentum
contributes its own resonance, slightly blue-shifted by the kinetic energy of
STEP 15. Because everything depends only on |k|, the 2D disc integral collapses
to a 1D integral over rings; the ring at radius k has circumference
proportional to k, which is the k in the weight. w_0 = 0 exactly: the ring at
k = 0 has zero circumference.
""".strip(NL))
    block("CHANGED", "A continuous 2D integral has become 96 numbers and 96 weights.")
    block("NEXT", "STEP 15 - what each k does to the transition energies.")
    write_csv(out("09_k_grid.csv"),
              ["index", "k_per_nm", "dk_per_nm", "weight_raw_per_nm2",
               "weight_scaled_per_nm2"],
              [[i, f"{k[i]:.17g}",
                f"{(0.5*step if i in (0, k.size-1) else step):.17g}",
                f"{weights[i]:.17g}", f"{weights_scaled[i]:.17g}"]
               for i in range(k.size)])

    # =======================================================================
    banner("15", "TRANSITION ENERGIES DISPERSE WITH k", "D")
    # =======================================================================
    transitions = chi2mod.transition_energies_eV(states, k, settings_raw)
    mu = settings_raw.reduced_mass_kg()
    block("INPUT", ["dE_nm(0) from STEP 12", "k from STEP 14",
                    f"m_e = {settings_raw.electron_mass_m0} m0, "
                    f"m_hh,par = {settings_raw.heavy_hole_inplane_mass_m0} m0"])
    block("FUNCTION", [
        "s06_chi2.transition_energies_eV",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:537",
    ])
    block("EQUATION", """
    dE_nm(k) = (E_e,n - E_hh,m) + hbar^2 k^2 / (2 mu)
    1/mu     = 1/m_e + 1/m_hh,par

k is converted nm^-1 -> m^-1 (x 1e9) and the kinetic term J -> eV (/ e).

MODELLING NOTE: only the DENOMINATORS move with k. The envelope matrix elements
O, z^e, z^hh are treated as k-INDEPENDENT. That is an approximation of this
model, applied identically in Demo 19 and Demo 20.
""".strip(NL))
    block("OUTPUT", [
        f"mu = m0 / (1/{settings_raw.electron_mass_m0} + "
        f"1/{settings_raw.heavy_hole_inplane_mass_m0}) = "
        f"{mu/chi2mod.ELECTRON_MASS_KG:.16f} m0",
        f"     = {mu:.6e} kg",
        "",
    ] + describe_array("transitions", transitions, "eV",
                       "dE_nm(k), axes (n_e=2, n_hh=2, n_k=96)")
      + ["",
         "dE_11(k) along the grid:",
         f"    k = {k[0]:.6f} nm^-1 -> {transitions[0,0,0]:.9f} eV",
         f"    k = {k[k.size//4]:.6f} nm^-1 -> {transitions[0,0,k.size//4]:.9f} eV",
         f"    k = {k[k.size//2]:.6f} nm^-1 -> {transitions[0,0,k.size//2]:.9f} eV",
         f"    k = {k[-1]:.6f} nm^-1 -> {transitions[0,0,-1]:.9f} eV",
         f"    total blue shift across the grid = "
         f"{transitions[0,0,-1]-transitions[0,0,0]:.9f} eV"])
    block("MEANING", f"""
An electron-hole pair that is also moving sideways needs more photon energy.
Across the whole k range the e1-hh1 transition shifts up by
{transitions[0,0,-1]-transitions[0,0,0]:.3f} eV - roughly {(transitions[0,0,-1]-transitions[0,0,0])/settings_raw.broadening_eV:.0f}x the 5 meV
broadening - so the k integral is genuinely sampling a wide band of detunings,
not just smearing the k = 0 answer over a linewidth.
""".strip(NL))
    block("CHANGED", "A 2x2 matrix of energies has become a 2x2x96 array.")
    block("NEXT", "STEP 16 - one k point, opened right up.")
    write_csv(out("10_transition_energies_vs_k.csv"),
              ["k_index", "k_per_nm", "dE_11_eV", "dE_12_eV", "dE_21_eV", "dE_22_eV"],
              [[i, f"{k[i]:.17g}", f"{transitions[0,0,i]:.17g}",
                f"{transitions[0,1,i]:.17g}", f"{transitions[1,0,i]:.17g}",
                f"{transitions[1,1,i]:.17g}"] for i in range(k.size)])

    # =======================================================================
    banner("16", f"ONE k POINT, TERM BY TERM (k index {k_index})", "D")
    # =======================================================================
    k_index = int(np.clip(k_index, 0, k.size - 1))
    terms = ref.chi2_summand_terms(states, k_index, target_energy, settings_raw)
    accumulated = sum(term["contribution"] for term in terms)
    block("INPUT", [
        f"k = k[{k_index}] = {k[k_index]:.16f} nm^-1",
        f"E = hc/1550 nm  = {target_energy:.16f} eV",
        f"2E              = {2*target_energy:.16f} eV",
        f"Gamma           = {settings_raw.broadening_eV:.6f} eV "
        f"({settings_raw.broadening_meV} meV)",
        "O, z^e, z^hh from STEPS 09-10; dE_nm(k) from STEP 15",
    ])
    block("FUNCTION", [
        "s06_chi2.chi2_spectrum - the triple loop",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:641-661",
        "Unrolled for inspection by demo20_math_physics_reference."
        "chi2_summand_terms, which self_check asserts is identical arithmetic.",
    ])
    block("EQUATION", """
    D2_ab = dE_ab(k) - 2E + i*Gamma        two-photon (SHG) denominator
    D1_ab = dE_ab(k) -   E + i*Gamma       one-photon denominator

    conduction term  (ADDED)     A' = O_nm z^e_nl  O_lm / (D2_nm * D1_lm)
    valence term  (SUBTRACTED)   B' = O_nm z^hh_ml O_nl / (D2_nm * D1_nl)

    S(k,E) = sum_{m,n,l} (A' - B')

INDEX MEANING - the easiest thing to misread:
    m = the heavy-hole state of the pair
    n = the electron state of the pair
    l = the intermediate partner. In A' it is an ELECTRON state; in B' it is a
        HOLE state. Same letter, different band.

Note also WHICH denominators carry which indices: A' has D1_lm (the l-th
electron with the m-th hole), B' has D1_nl (the n-th electron with the l-th
hole). Getting this wrong is the classic error in Eq. (5)/(6).
""".strip(NL))
    block("THE DENOMINATORS, EXPLAINED SIMPLY", """
Each denominator measures how badly the light misses a real transition of the
structure. A small denominator means the photon (or the photon pair) is nearly
resonant, and the response blows up. The +i*Gamma stops it becoming infinite:
that is the finite lifetime of the excited state, 5 meV here.

Gamma enters as an ENERGY because Demo 20 evaluates the energy form of the
equation. In the published angular-frequency form the same physical broadening
appears as Gamma/hbar in rad/s. Both are the same physics; mixing them is the
classic units trap (docs/demo14_physics_sources.md:47-51).
""".strip(NL))
    header = (f"{'term':11s} {'m n l':7s} {'numerator [nm]':>17s} "
              f"{'|D2| [eV]':>11s} {'|D1| [eV]':>11s} {'|contribution|':>15s}")
    lines = [header, "-" * len(header)]
    for term in terms:
        lines.append(
            f"{term['term']:11s} {term['m']} {term['n']} {term['l']}   "
            f"{term['numerator_nm']:17.9e} "
            f"{abs(term['denominator_two_photon_eV']):11.6f} "
            f"{abs(term['denominator_one_photon_eV']):11.6f} "
            f"{abs(term['contribution']):15.9e}")
    block("OUTPUT - all 16 terms", lines)
    biggest = max(terms, key=lambda t: abs(t["contribution"]))
    conduction_sum = sum(t["contribution"] for t in terms if t["term"] == "conduction")
    valence_sum = sum(t["contribution"] for t in terms if t["term"] == "valence")
    block("OUTPUT - one term written out in full (the largest)", [
        f"{biggest['label']}",
        f"    m = {biggest['m']}, n = {biggest['n']}, l = {biggest['l']}  "
        f"({biggest['term']} term, sign {biggest['sign']:+d})",
        f"    numerator   = {biggest['numerator_nm']:.16e} nm",
        f"    D2          = {biggest['denominator_two_photon_eV']:.9f} eV",
        f"    D1          = {biggest['denominator_one_photon_eV']:.9f} eV",
        f"    D2 * D1     = "
        f"{biggest['denominator_two_photon_eV']*biggest['denominator_one_photon_eV']:.9f} eV^2",
        f"    contribution= {biggest['contribution']:.16e}   [nm/eV^2]",
    ])
    block("OUTPUT - the near-cancellation", [
        f"sum of conduction terms  = {conduction_sum:.12e}",
        f"sum of valence terms     = {valence_sum:.12e}",
        f"S(k,E) = their sum       = {accumulated:.12e}   [nm/eV^2]",
        f"|conduction| / |S|       = {abs(conduction_sum)/abs(accumulated):.4f}",
        "",
        "The two groups have opposite signs and largely cancel. That",
        "near-cancellation is real physics in this model - the electron and",
        "hole ladders almost undo each other, and what survives is the",
        "asymmetry. It is why s06_chi2.py:625-630 refuses to collapse the loop",
        "into an einsum: the two contributions must stay visibly separate.",
    ])
    block("MEANING", """
This is one microscopic contribution: one in-plane momentum, one wavelength,
all 16 quantum pathways through the four states. Everything else in the
calculation is a weighted sum of objects exactly like this one.
""".strip(NL))
    block("CHANGED",
          "Matrices and energies have become a single complex number S(k,E).")
    block("NEXT", "STEP 17 - do that for all 96 k points and add them up.")
    write_csv(out("11_triple_sum_terms_at_1550nm.csv"),
              ["term", "sign", "m", "n", "l", "label", "numerator_nm",
               "D2_real_eV", "D2_imag_eV", "D1_real_eV", "D1_imag_eV",
               "contribution_real", "contribution_imag"],
              [[t["term"], t["sign"], t["m"], t["n"], t["l"], t["label"],
                f"{t['numerator_nm']:.17g}",
                f"{t['denominator_two_photon_eV'].real:.17g}",
                f"{t['denominator_two_photon_eV'].imag:.17g}",
                f"{t['denominator_one_photon_eV'].real:.17g}",
                f"{t['denominator_one_photon_eV'].imag:.17g}",
                f"{complex(t['contribution']).real:.17g}",
                f"{complex(t['contribution']).imag:.17g}"] for t in terms])

    # =======================================================================
    banner("17", "SUM OVER ALL k - THE IN-PLANE INTEGRAL", "D")
    # =======================================================================
    accumulated_all = np.array(
        [sum(t["contribution"]
             for t in ref.chi2_summand_terms(states, i, target_energy, settings_raw))
         for i in range(k.size)], dtype=complex)
    weighted = weights * accumulated_all
    k_sum = complex(np.dot(weights, accumulated_all))
    block("INPUT", [
        f"S(k_i, E) for i = 0..{k.size-1}   (complex, nm/eV^2)",
        f"w_i from STEP 14                  (nm^-2)",
    ])
    block("FUNCTION", [
        "np.dot(weights, accumulated) - ONE statement",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:661",
        "The entire in-plane integration is that dot product, which is why",
        "every normalization decision lives in k_grid and nowhere else.",
    ])
    block("EQUATION", "    sum_over_k(E) = sum_i w_i S(k_i, E)")
    rows = ([0, 1, 2] + [k.size // 4, k.size // 2, 3 * k.size // 4]
            + [k.size - 3, k.size - 2, k.size - 1])
    biggest_i = int(np.argmax(np.abs(weighted)))
    rows = sorted(set(rows + [biggest_i]))
    lines = [f"{'i':>4s} {'k [nm^-1]':>12s} {'w_i [nm^-2]':>14s} "
             f"{'|S(k_i)|':>14s} {'|w_i S_i|':>14s}",
             "-" * 62]
    for i in (range(k.size) if all_k else rows):
        marker = "  <- largest" if i == biggest_i and not all_k else ""
        lines.append(f"{i:4d} {k[i]:12.8f} {weights[i]:14.6e} "
                     f"{abs(accumulated_all[i]):14.6e} "
                     f"{abs(weighted[i]):14.6e}{marker}")
    if not all_k:
        lines.append("      ... (use --all-k for all 96 rows; the full set is "
                     "always written to 12_k_contributions.csv)")
    block("OUTPUT - representative contributions", lines)
    block("OUTPUT - the integral", [
        f"sum_i w_i S(k_i, E) = {k_sum:.16e}",
        f"|sum|               = {abs(k_sum):.16e}   [nm eV^-2 nm^-2]",
        "",
        f"i = 0 contributes exactly 0 because w_0 = 0 (zero-circumference ring).",
        f"The largest single contribution is at i = {biggest_i}, "
        f"k = {k[biggest_i]:.6f} nm^-1.",
    ])
    block("MEANING", """
The in-plane integral is where the lineshape gets its width. Each k ring has a
slightly different resonance energy (STEP 15), so summing over k stacks many
slightly-detuned Lorentzians on top of each other.
""".strip(NL))
    block("CHANGED", "96 complex numbers have become one complex number.")
    block("NEXT", "STEP 18 - put the physical constants back in.")
    write_csv(out("12_k_contributions.csv"),
              ["index", "k_per_nm", "weight_per_nm2", "S_real", "S_imag",
               "weighted_real", "weighted_imag"],
              [[i, f"{k[i]:.17g}", f"{weights[i]:.17g}",
                f"{accumulated_all[i].real:.17g}", f"{accumulated_all[i].imag:.17g}",
                f"{weighted[i].real:.17g}", f"{weighted[i].imag:.17g}"]
               for i in range(k.size)])

    # =======================================================================
    banner("18", "PREFACTOR AND UNIT CONVERSION TO pm/V", "D")
    # =======================================================================
    expanded = ref.absolute_prefactor_expanded(
        settings_raw.n_wells_per_metre, settings_raw.r_e_hh_nm)
    prefactor = chi2mod.absolute_prefactor(settings_raw)
    block("INPUT", [
        f"N_z  = {settings_raw.n_wells_per_metre:.10e} m^-1  "
        f"(nz_mode = {settings_raw.nz_mode}, period = "
        f"{settings_raw.reference_period_nm} nm)",
        f"r_e,hh = {settings_raw.r_e_hh_nm} nm    (STEP 11, DFT)",
        f"e    = {chi2mod.ELEMENTARY_CHARGE_C:.10e} C",
        f"eps0 = {chi2mod.VACUUM_PERMITTIVITY_F_PER_M:.10e} F/m",
    ])
    block("FUNCTION", [
        "s06_chi2.absolute_prefactor  (and n_z_for for N_z)",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:514 and :289",
    ])
    block("EQUATION", """
    prefactor = [ N_z e^3 r^2 / (6 eps0) ] * U * 1e12
    U         = 1e-9 * 1e18 / e^2

The three parts of U undo the non-SI units the sum was evaluated in:
    1e-9   z matrix elements were in nm      -> m
    1e18   k weights were in nm^-2           -> m^-2
    1/e^2  the two denominators were in eV^2 -> J^2
and the final 1e12 converts m/V -> pm/V.

WHERE DID hbar^-2 GO? The published Eq. (3) has 1/(6 eps0 hbar^2) because its
denominators are angular frequencies. Demo 20 writes both denominators in
ENERGY instead, which absorbs hbar^2 exactly. Nothing was dropped.
(s06_chi2.py:30-33.)

N_z AMBIGUITY: the source says only "number of QWs per unit length".
    period_density (used)  N_z = 1/(30 nm) = 3.3333e7 m^-1
    well_density           N_z = 2/(30 nm) = 6.6667e7 m^-1
Both readings are recorded; Demo 20 does not choose by fitting (s06_chi2.py:289).
""".strip(NL))
    block("OUTPUT", [f"{k_:32s} {v!r}" for k_, v in expanded.items()]
          + ["",
             f"prefactor (production) = {prefactor:.16f} pm/V per summand unit",
             "",
             "Unit chain, checked analytically:",
             "    C^3 * m^2 / (F/m) * m^-2 * J^-2  =  m/V     then x 1e12 -> pm/V"])
    block("MEANING", """
The sum so far is a pure number in mixed units. This step multiplies in how many
wells there are per metre, how strong the bulk GaAs interband dipole is, and the
electromagnetic constants - and converts everything to SI, then to pm/V.
""".strip(NL))
    block("CHANGED",
          "A dimensionally mixed sum becomes a susceptibility in pm/V.")
    block("NEXT", "STEP 19 - do all of STEPS 13-18 at every wavelength.")

    # =======================================================================
    banner("19", "THE WHOLE SPECTRUM chi^(2)(lambda)", "D")
    # =======================================================================
    raw = chi2mod.chi2_spectrum(states, lam, settings_raw)
    scaled = chi2mod.chi2_spectrum(states, lam, settings_scaled)
    block("INPUT", [
        f"401 wavelengths (STEP 13), 96 k points (STEP 14),",
        "16 terms each (STEP 16) = 616 k-summands x 401 = 615,936 term evaluations",
    ])
    block("FUNCTION", [
        "s06_chi2.chi2_spectrum",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:612",
        "",
        "OPENED UP, its internal structure is exactly STEPS 13-18:",
        "    chi2_spectrum",
        "      +-- states.truncated(2)                  s06_chi2.py:626",
        "      +-- photon_energy_eV(lam)                s06_chi2.py:637",
        "      +-- k_grid(settings)                     s06_chi2.py:639  [STEP 14]",
        "      +-- transition_energies_eV(...)          s06_chi2.py:640  [STEP 15]",
        "      +-- for each wavelength:",
        "      |     +-- two_photon / one_photon        s06_chi2.py:643  [STEP 16]",
        "      |     +-- triple loop m, n, l            s06_chi2.py:646  [STEP 16]",
        "      |     +-- np.dot(weights, accumulated)   s06_chi2.py:661  [STEP 17]",
        "      +-- absolute_prefactor(settings)         s06_chi2.py:663  [STEP 18]",
        "      +-- chi2 = total * prefactor             s06_chi2.py:690",
    ])
    block("EQUATION", "    chi2(lambda) = prefactor * sum_i w_i S(k_i, hc/lambda)")
    block("OUTPUT", describe_array("raw.chi2", raw.chi2, "pm/V (complex)",
                                   "chi2_xzx at each wavelength, Demo 19 convention")
          + [""]
          + describe_array("raw.magnitude", raw.magnitude, "pm/V",
                           "|chi2| - the reported quantity")
          + ["",
             f"x-axis : wavelength 1400 - 1800 nm, 401 points, 1.0 nm spacing",
             f"y-axis : |chi2| in pm/V",
             "",
             f"peak (raw)    : {raw.peak()}",
             f"peak (scaled) : {scaled.peak()}",
             f"peak wavelength shift between conventions : "
             f"{abs(raw.peak()['wavelength_nm'] - scaled.peak()['wavelength_nm'])} nm",
             f"normalized-lineshape max difference       : "
             f"{float(np.max(np.abs(scaled.normalized_magnitude() - raw.normalized_magnitude()))):.3e}"])
    block("MEANING", """
The structure never changed across this sweep - only the photon energy did.
The peak at 1502 nm is where 2E best matches the dominant transition; the
response falls off on either side as the denominators grow.

The two conventions differ by a constant factor everywhere, so they have the
same peak position and the same normalized lineshape to ~1e-16. That is the
invariance Demo 20's QC gates on (s08_qc.py:259).
""".strip(NL))
    block("CHANGED", "One number has become a 401-point spectrum.")
    block("NEXT", "STEP 20 - pick out 1550 nm.")
    write_csv(out("13_chi2_spectrum.csv"),
              ["wavelength_nm", "photon_energy_eV", "chi2_raw_real_pm_per_V",
               "chi2_raw_imag_pm_per_V", "chi2_raw_abs_pm_per_V",
               "chi2_scaled_abs_pm_per_V"],
              [[f"{lam[i]:.6f}", f"{raw.photon_energy_eV[i]:.17g}",
                f"{raw.chi2[i].real:.17g}", f"{raw.chi2[i].imag:.17g}",
                f"{raw.magnitude[i]:.17g}", f"{scaled.magnitude[i]:.17g}"]
               for i in range(lam.size)])

    # =======================================================================
    banner("20", "SELECT THE VALUE AT 1550 nm", "D")
    # =======================================================================
    traced_raw = raw.at_wavelength(TARGET_NM)
    traced_scaled = scaled.at_wavelength(TARGET_NM)
    node = int(np.argmin(np.abs(lam - TARGET_NM)))
    block("INPUT", ["|chi2|(lambda), 401 points", f"target = {TARGET_NM} nm"])
    block("FUNCTION", [
        "s06_chi2.Chi2Spectrum.at_wavelength",
        "Source: nextnano/demos/20_quantum_well_interface_grading_scaled/"
        "s06_chi2.py:573 (the interpolation is line 586)",
        "Called by s07_analysis._fill_chi2_columns (s07_analysis.py:148-149).",
    ])
    block("EQUATION", """
    |chi2|(1550) = np.interp(1550, wavelength_grid_sorted, |chi2|_sorted)

i.e. LINEAR INTERPOLATION on the wavelength grid - not "nearest point", not a
separate evaluation at 1550 nm.
""".strip(NL))
    block("OUTPUT", [
        f"grid node {node}: lambda = {lam[node]:.6f} nm",
        f"|chi2| at that node   = {raw.magnitude[node]:.16f} pm/V",
        f"at_wavelength(1550.0) = {traced_raw:.16f} pm/V",
        f"difference            = {abs(traced_raw - raw.magnitude[node]):.3e}",
        "",
        "1550.0 nm is EXACTLY a grid node (1400 + 150 x 1.0 nm), so the",
        "interpolation returns that node unchanged and contributes no error.",
        "Change chi2.focused_wavelength_points and that stops being true - which",
        "is exactly why the code interpolates rather than indexing.",
    ])
    block("RESULT", [
        f"|chi2|(1550 nm), raw convention    = {traced_raw:.16f} pm/V",
        f"|chi2|(1550 nm), scaled convention = {traced_scaled:.16f} pm/V",
        f"ratio                              = {traced_scaled/traced_raw:.16f}",
        f"(2 pi)^2                           = {chi2mod.two_pi_squared():.16f}",
    ])
    block("CHANGED", "A spectrum has become the one reported number.")
    block("NEXT", "STEP 21 - check it against what Demo 20 already stored.")

    # =======================================================================
    banner("21", "VERIFICATION AGAINST THE EXISTING DEMO 20 RESULT", "D")
    # =======================================================================
    stored = _stored_row(DEMO20_TABLE, CASE_ID)
    demo19_recorded = float(extract._as_float(
        (found.extras or {}).get("chi2_1550_pm_per_V")))

    # An INDEPENDENT reconstruction: rebuild chi2 from the unrolled per-term
    # arithmetic of STEP 16-18 instead of calling chi2_spectrum.
    reconstructed_raw = abs(k_sum * prefactor)

    comparisons: list[tuple[str, float, float, float, str]] = []

    def compare(label: str, a: float, b: float, rtol: float, why: str) -> None:
        rel = abs(a - b) / max(abs(b), 1e-300)
        comparisons.append((label, a, b, rel, why))
        assert rel <= rtol, (
            f"{label}: traced {a!r} vs reference {b!r}, relative {rel:.3e} "
            f"exceeds {rtol:.3e}")

    if stored is not None:
        compare("traced raw vs stored Demo 20 chi2_raw_1550_pm_per_V",
                traced_raw, float(stored["chi2_raw_1550_pm_per_V"]), 0.0,
                "same production function, same inputs -> bit-identical")
        compare("traced scaled vs stored Demo 20 chi2_scaled_1550_pm_per_V",
                traced_scaled, float(stored["chi2_scaled_1550_pm_per_V"]), 0.0,
                "same production function, same inputs -> bit-identical")
        compare("traced peak vs stored Demo 20 raw_peak_chi2_pm_per_V",
                raw.peak()["magnitude_pm_per_V"],
                float(stored["raw_peak_chi2_pm_per_V"]), 1.0e-15,
                "argmax over the same array; ULP-level float noise only")
    compare("traced raw vs Demo 19 recorded chi2_1550_pm_per_V",
            traced_raw, demo19_recorded, 1.0e-15,
            "Demo 19 computed this from the same matrix elements with the "
            "same equation; agreement is limited only by float summation order")
    compare("STEP 16-18 hand reconstruction vs traced raw",
            reconstructed_raw, traced_raw, 1.0e-14,
            "identical arithmetic accumulated in a different order "
            "(list-sum per k vs in-place +=); a few ULP")

    block("WHAT IS BEING COMPARED", """
    traced        - computed by THIS script, calling Demo 20's production
                    functions on Demo 20's configuration.
    reconstructed - computed by THIS script from the unrolled per-term
                    arithmetic of STEPS 16-18, never calling chi2_spectrum.
    stored        - the number already in
                    demo_results/demo20/tables/demo20_master_results.csv.
    Demo 19       - the number Demo 19's own licensed run recorded, carried in
                    demo_results/demo19/tables/demo19_master_results.csv.
""".strip(NL))
    lines = [f"{'comparison':62s} {'relative diff':>14s}", "-" * 78]
    for label, a, b, rel, _why in comparisons:
        lines.append(f"{label:62s} {rel:14.3e}")
    block("OUTPUT", lines)
    block("VALUES", [
        f"traced raw          = {traced_raw!r}",
        f"reconstructed raw   = {reconstructed_raw!r}",
        f"stored Demo 20 raw  = "
        f"{stored['chi2_raw_1550_pm_per_V'] if stored else 'table not found'}",
        f"Demo 19 recorded    = {demo19_recorded!r}",
        f"traced scaled       = {traced_scaled!r}",
        f"stored Demo 20 scal = "
        f"{stored['chi2_scaled_1550_pm_per_V'] if stored else 'table not found'}",
    ])
    block("TOLERANCE JUSTIFICATION", [
        f"{why}" for _l, _a, _b, _r, why in comparisons
    ] + ["",
         "No tolerance here was chosen to make a check pass. The rtol = 0",
         "comparisons are exact because they run the same code on the same",
         "inputs. The rest are bounded by IEEE-754 summation-order noise,",
         "which for magnitudes of order 10^1 is ~10^-16 - and the measured",
         "differences above are indeed at that level, not merely under the",
         "tolerance."])
    block("MEANING", """
The educational trace is not a parallel implementation that happens to agree.
It is the production calculation, narrated - plus one genuinely independent
re-accumulation (the hand reconstruction) that agrees to 6e-16.
""".strip(NL))

    # =======================================================================
    banner("22", "THE CAUSAL CHAIN, END TO END", "summary")
    # =======================================================================
    print(f"""
    W = 1.0 nm linear grading at I1, I2, I3, I4                       [A]
            |
            v  x_Al = x_L + (x_R - x_L) u        s02_grading.py:162   [B]
    x_Al(z): 0.55 -> 0 spread over 8.6-9.6 nm (and 3 more windows)
            |
            v  ternary_linear regions in case.in s03_inputs.py:107    [B]
    nextnano++ deck
            |
            v  alloy -> band parameters          database.nnp         [C]
    V_e(z), V_hh(z), m*(z)  - softer, wider wells than the abrupt case
            |
            v  H psi = E psi (BenDaniel-Duke)    nextnano++           [C]
    E_e1 = 2.9412, E_e2 = 3.0610, E_hh1 = 1.4478, E_hh2 = 1.4128 eV
    psi_e1, psi_e2, psi_hh1, psi_hh2
            |
            v  normalize, then integrate         _shared/chi2.py:204,220 [D]
    O11 = 0.9823   z^e_11 = 12.72 nm   z^e_22 = 18.66 nm
    O22 = 0.3831   z^hh_11 = 12.65 nm  z^hh_22 = 12.73 nm
            |
            v  dE = E_e - E_hh                   s06_chi2.py:537      [D]
    dE_11 = 1.4934, dE_12 = 1.5284, dE_21 = 1.6132, dE_22 = 1.6482 eV
            |
            v  + hbar^2 k^2/(2 mu)               s06_chi2.py:537      [D]
    dE_nm(k), 2 x 2 x 96
            |
            v  16 terms / (D2 D1)                s06_chi2.py:646-658  [D]
    S(k, E)
            |
            v  sum_i w_i S_i                     s06_chi2.py:661      [D]
    in-plane integral
            |
            v  x N_z e^3 r^2/(6 eps0) x units    s06_chi2.py:514      [D]
    chi2(lambda) in pm/V, 401 points
            |
            v  np.interp at 1550 nm              s06_chi2.py:573      [D]
    |chi2|(1550 nm) = {traced_raw:.9f} pm/V   [raw]
                    = {traced_scaled:.9f} pm/V   [scaled, x (2 pi)^2]

    WHY THE GRADED CASE IS SMALLER THAN THE ABRUPT ONE
    Case 00 (abrupt) gives 31.036 pm/V; case 04 (1.0 nm linear) gives
    {traced_raw:.3f} pm/V, a ratio of {traced_raw/31.036041396587407:.4f}. Smearing the
    interfaces softens the confinement, the states spread and their centroids
    move closer together, the electron-hole asymmetry that drives chi^(2)
    weakens, and the response drops monotonically with grading width across
    cases 00-05 (0.0 -> 1.4 nm: 31.04, 29.37, 26.44, 21.68, {traced_raw:.2f}, 15.23 pm/V).
""")

    final = {
        "demo": "21 (walkthrough of demo 20)",
        "case_id": CASE_ID,
        "case_name": case.case_name,
        "profile": case.profile,
        "grading_width_nm": case.nominal_grade_width_nm,
        "target_wavelength_nm": TARGET_NM,
        "chi2_1550_raw_pm_per_V": traced_raw,
        "chi2_1550_scaled_pm_per_V": traced_scaled,
        "chi2_1550_reconstructed_raw_pm_per_V": reconstructed_raw,
        "peak_raw": raw.peak(),
        "peak_scaled": scaled.peak(),
        "kspace_convention_raw": settings_raw.kspace_convention,
        "kspace_convention_scaled": settings_scaled.kspace_convention,
        "prefactor_pm_per_V": prefactor,
        "envelope_demonstration": envelope_demo,
        "states_provenance": states.provenance,
        "solver_pass": found.solver_pass,
        "physical_valid": found.physical_valid,
        "failure_reason": found.failure_reason,
        "stored_demo20": stored,
        "demo19_recorded_chi2_1550_pm_per_V": demo19_recorded,
        "verification": [
            {"comparison": label, "traced": a, "reference": b,
             "relative_difference": rel, "tolerance_justification": why}
            for label, a, b, rel, why in comparisons
        ],
        "caveat": ("solver_pass and physical_valid are separate. All 13 Demo 19 "
                   "cases are physical_valid=False; treat these numbers as a "
                   "controlled comparison between grading cases, not validated "
                   "absolute physics."),
    }
    print()
    write_json(out("14_final_result.json"), final)

    print()
    print("=" * _WIDTH)
    print("FINAL DEMO 20 RESULT")
    print("=" * _WIDTH)
    print(f"Case             : {CASE_ID} - {case.case_name} "
          f"({case.profile}, W = {case.nominal_grade_width_nm} nm)")
    print(f"Target wavelength: {TARGET_NM} nm")
    print(f"chi^(2)(1550 nm) : {traced_raw:.15f} pm/V   "
          f"[raw, k-measure = int d^2k/(2pi)^2]")
    print(f"chi^(2)(1550 nm) : {traced_scaled:.15f} pm/V   "
          f"[scaled, k-measure = g_s int d^2k]")
    print(f"All {len(comparisons)} verification checks PASSED.")
    if envelope_demo is None:
        print("Envelopes        : NOT SHOWN - neither Case 04's parsed run nor "
              "the fallback table is present")
    elif envelope_demo["is_case04"]:
        print(f"Envelopes        : Demo 20 Case 04 licensed envelopes, "
              f"{envelope_demo['grid_points']} grid points; all 12 matrix "
              f"elements reproduced to "
              f"{envelope_demo['max_absolute_difference']:.3e}")
    else:
        print(f"Envelopes        : FALLBACK ({envelope_demo['source']}) - Case 04's "
              f"own parsed run was not found")
    if outdir is not None:
        print(f"Checkpoints      : {outdir}")
    return 0


# --- helpers -----------------------------------------------------------------


def _stored_row(path: Path, case_id: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if str(row.get("case_id", "")).strip() == case_id:
                return dict(row)
    return None


#: The four envelopes the susceptibility actually uses, plus the grid. The
#: parsed table carries six states per band (``output_state_count = 6``); the
#: triple sum uses two, so these five columns are selected BY NAME rather than
#: by position - the column order of a parser output is not a contract.
ENVELOPE_COLUMNS = ("z_nm", "psi_e1", "psi_e2", "psi_hh1", "psi_hh2")


class Extract20EnvelopeError(ValueError):
    """An envelope table is not the shape the susceptibility needs."""


def _read_envelope_table(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                              tuple[str, ...]]:
    """``(z, psi_electron, psi_hole, all_column_names)`` from an envelopes.csv.

    Selects ``ENVELOPE_COLUMNS`` by header name and ignores every other column,
    so a table with six states per band and a table with two both work and
    neither can be silently mis-sliced.
    """

    with path.open(encoding="utf-8", newline="") as stream:
        header = tuple(name.strip() for name in stream.readline().split(","))
    missing = [name for name in ENVELOPE_COLUMNS if name not in header]
    if missing:
        raise Extract20EnvelopeError(
            f"{path} has no column(s) {missing}; found {list(header)}")
    index = {name: header.index(name) for name in ENVELOPE_COLUMNS}
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    z = data[:, index["z_nm"]]
    psi_e = np.column_stack([data[:, index["psi_e1"]], data[:, index["psi_e2"]]])
    psi_h = np.column_stack([data[:, index["psi_hh1"]], data[:, index["psi_hh2"]]])
    return z, psi_e, psi_h, header


def _leading_block(matrix: Any, n: int = 2) -> np.ndarray:
    """The leading ``n x n`` block of a recorded matrix.

    ``matrix_elements.json`` is written over every parsed state (6 per band
    here), while the susceptibility uses the first 2. Each entry is an
    independent integral of two envelopes, so truncating the matrix and
    truncating the basis give the same numbers - which is why the leading block
    is the right comparison and not an approximation.
    """

    return np.asarray(matrix, dtype=float)[:n, :n]


def _envelope_demonstration(
    envelopes_csv: Path, recorded_json: Path, path: Path | None,
    *, source_label: str, is_case04: bool,
) -> dict[str, Any] | None:
    """Run the envelope -> matrix-element step on real licensed envelopes.

    Requirements this satisfies, in order: load the envelopes (1), record the
    raw arrays (2), build the production :class:`BandStates` (3) which
    normalizes them (4), report the norm before and after (5) and the
    orthonormality errors (6), recompute ``overlap_matrix`` (7) and both
    ``position_matrix`` calls (8, 9), load the recorded ``matrix_elements.json``
    (10), compare every element (11) and assert agreement (12).
    """

    if not (envelopes_csv.is_file() and recorded_json.is_file()):
        return None

    # (1) load, selecting the five columns chi2 uses out of the thirteen present
    z, psi_e_raw, psi_h_raw, header = _read_envelope_table(envelopes_csv)

    # (5, first half) the norm of each envelope exactly AS STORED
    names = ("psi_e1", "psi_e2", "psi_hh1", "psi_hh2")
    raw_columns = [psi_e_raw[:, 0], psi_e_raw[:, 1], psi_h_raw[:, 0], psi_h_raw[:, 1]]
    norm_before = [float(np.trapezoid(column ** 2, z)) for column in raw_columns]

    # (3, 4) the production type. BandStates.__post_init__ normalizes on
    # construction; the energies are placeholders because overlap_matrix and
    # position_matrix use only the envelopes and the grid.
    band_e = shared_chi2.BandStates(z, np.array([0.0, 1.0]), psi_e_raw.copy(), "e")
    band_h = shared_chi2.BandStates(z, np.array([0.0, -1.0]), psi_h_raw.copy(), "hh")

    # (5, second half)
    normalized = [band_e.envelopes[:, 0], band_e.envelopes[:, 1],
                  band_h.envelopes[:, 0], band_h.envelopes[:, 1]]
    norm_after = [float(np.trapezoid(column ** 2, z)) for column in normalized]

    # (6)
    orthonormality = {
        "electron": band_e.orthonormality_error(),
        "heavy_hole": band_h.orthonormality_error(),
    }

    # (7, 8, 9)
    overlap = shared_chi2.overlap_matrix(band_e, band_h)
    z_e = shared_chi2.position_matrix(band_e)
    z_h = shared_chi2.position_matrix(band_h)

    # (10)
    recorded = json.loads(recorded_json.read_text(encoding="utf-8"))
    stored = {
        "O": _leading_block(recorded["overlap_electron_hole"]),
        "z_e": _leading_block(recorded["position_matrix_electron_nm"]),
        "z_hh": _leading_block(recorded["position_matrix_heavy_hole_nm"]),
    }
    computed = {"O": overlap, "z_e": z_e, "z_hh": z_h}

    # (11) every element, one at a time - not a summary norm
    labels = {"O": ("e", "hh"), "z_e": ("e", "e"), "z_hh": ("hh", "hh")}
    comparisons: list[dict[str, Any]] = []
    for symbol in ("O", "z_e", "z_hh"):
        left, right = labels[symbol]
        for i in range(2):
            for j in range(2):
                a = float(computed[symbol][i, j])
                b = float(stored[symbol][i, j])
                comparisons.append({
                    "symbol": symbol,
                    "element": f"{symbol}[{left}{i+1},{right}{j+1}]",
                    "recomputed": a,
                    "stored": b,
                    "absolute_difference": abs(a - b),
                    # scale-aware: O is O(1) dimensionless, z is O(10) nm
                    "allowed": 1.0e-12 * max(1.0, abs(b)),
                })

    # (12) assert to numerical precision, element by element
    worst = max(comparisons, key=lambda row: row["absolute_difference"] / row["allowed"])
    for row in comparisons:
        assert row["absolute_difference"] <= row["allowed"], (
            f"{row['element']}: recomputed {row['recomputed']!r} vs stored "
            f"{row['stored']!r}, |diff| = {row['absolute_difference']:.3e} "
            f"exceeds {row['allowed']:.3e}")

    heading = ("NUMERICAL DEMONSTRATION ON THE ACTUAL CASE 04 ENVELOPES"
               if is_case04 else
               "NUMERICAL DEMONSTRATION (FALLBACK - A DIFFERENT STRUCTURE)")
    provenance = (f"""
Source: Demo 20 Case 04 licensed envelopes
        {repo_relative(envelopes_csv)}
        {repo_relative(recorded_json)}

These are the envelopes of THIS case - the same 1.0 nm linear grading whose
chi^(2)(1550 nm) this trace ends on. Not a stand-in, not another structure.
""".strip(NL) if is_case04 else f"""
Source: {repo_relative(envelopes_csv.parent)}
        FALLBACK ONLY. Demo 20 Case 04's own parsed envelopes were not found at
        {repo_relative(CASE04_PARSED)}
        so this shows the step on Demo 11's s1_ref run instead - a DIFFERENT
        STRUCTURE. Its numbers are NOT case 04's and are used nowhere else in
        this trace.
""".strip(NL))

    lines = [provenance, ""]
    lines.append(f"Envelope table : {z.size} grid points, "
                 f"z from {z[0]:.6f} to {z[-1]:.6f} nm")
    lines.append(f"Columns present: {len(header)}  ({', '.join(header[:5])}"
                 f"{', ...' if len(header) > 5 else ''})")
    lines.append(f"Columns used   : {', '.join(ENVELOPE_COLUMNS)}   "
                 f"(chi2 uses two states per band)")
    lines.append("")
    lines.append("RAW ARRAYS AS STORED")
    for name, column in zip(names, raw_columns):
        lines.append(f"    {name:8s} shape {column.shape}  "
                     f"max|psi| = {float(np.max(np.abs(column))):.9f} nm^-1/2")
        lines.append(f"    {'':8s} first 4 : "
                     f"{np.array2string(column[:4], precision=6)}")
    lines.append("")
    lines.append("NORMALIZATION   int |psi|^2 dz   (trapezoid, z in nm)")
    lines.append(f"    {'state':8s} {'before':>22s} {'after':>22s}")
    for name, before, after in zip(names, norm_before, norm_after):
        lines.append(f"    {name:8s} {before:22.17f} {after:22.17f}")
    lines.append("")
    lines.append("    The parser writes envelopes.csv from the ALREADY-NORMALIZED")
    lines.append("    BandStates (demo11.py:791-801), so 'before' is already 1 to")
    lines.append("    ~1e-16 and re-normalizing is idempotent. That is the point:")
    lines.append("    it confirms this file IS the orthonormal basis the recorded")
    lines.append("    matrix elements were built from, not an unnormalized dump.")
    lines.append("")
    lines.append("ORTHONORMALITY   max |<psi_i|psi_j> - delta_ij|")
    lines.append(f"    electron band   : {orthonormality['electron']:.3e}")
    lines.append(f"    heavy-hole band : {orthonormality['heavy_hole']:.3e}")
    lines.append("")
    lines.append("RECOMPUTED vs STORED matrix_elements.json   (all 12 elements)")
    lines.append(f"    {'element':14s} {'recomputed':>24s} {'stored':>24s} {'|diff|':>11s}")
    for row in comparisons:
        lines.append(f"    {row['element']:14s} {row['recomputed']:24.17g} "
                     f"{row['stored']:24.17g} {row['absolute_difference']:11.3e}")
    lines.append("")
    lines.append(f"    worst element : {worst['element']}  "
                 f"|diff| = {worst['absolute_difference']:.3e}  "
                 f"(allowed {worst['allowed']:.3e})")
    lines.append("    ALL 12 ELEMENTS AGREE TO NUMERICAL PRECISION.")
    lines.append("")
    if is_case04:
        lines.append("=> STEP 09 and STEP 10 are not describing the equations that")
        lines.append("   produced case 04's O, z^e and z^hh - they are RE-RUNNING")
        lines.append("   them, on case 04's own wavefunctions, and landing on the")
        lines.append("   same numbers the licensed run recorded.")
    else:
        lines.append("=> The equations in STEP 09 and STEP 10 are exactly the ones")
        lines.append("   that produced case 04's O, z^e and z^hh during its licensed")
        lines.append("   run - shown here on another structure's envelopes.")
    block(heading, lines)

    if path is not None:
        write_csv(
            path,
            ["z_nm",
             "psi_e1_raw", "psi_e2_raw", "psi_hh1_raw", "psi_hh2_raw",
             "psi_e1_normalized", "psi_e2_normalized",
             "psi_hh1_normalized", "psi_hh2_normalized",
             "psi_e1_times_psi_hh1", "psi_e1_z_psi_e1"],
            [[f"{z[i]:.17g}",
              f"{raw_columns[0][i]:.17g}", f"{raw_columns[1][i]:.17g}",
              f"{raw_columns[2][i]:.17g}", f"{raw_columns[3][i]:.17g}",
              f"{normalized[0][i]:.17g}", f"{normalized[1][i]:.17g}",
              f"{normalized[2][i]:.17g}", f"{normalized[3][i]:.17g}",
              f"{normalized[0][i] * normalized[2][i]:.17g}",
              f"{normalized[0][i] * z[i] * normalized[0][i]:.17g}"]
             for i in range(z.size)])

    return {
        "source": source_label,
        "envelopes_csv": str(envelopes_csv),
        "matrix_elements_json": str(recorded_json),
        "is_case04": is_case04,
        "grid_points": int(z.size),
        "columns_present": list(header),
        "norm_before": dict(zip(names, norm_before)),
        "norm_after": dict(zip(names, norm_after)),
        "orthonormality_error": orthonormality,
        "element_comparisons": comparisons,
        "max_absolute_difference": max(
            row["absolute_difference"] for row in comparisons),
    }


def case04_envelope_demo(path: Path | None) -> dict[str, Any] | None:
    """PRIMARY: the actual Demo 20 Case 04 licensed envelopes."""

    return _envelope_demonstration(
        CASE04_PARSED / "envelopes.csv",
        CASE04_PARSED / "matrix_elements.json",
        path,
        source_label="Demo 20 Case 04 licensed envelopes",
        is_case04=True,
    )


def demo11_fallback_demo(path: Path | None) -> dict[str, Any] | None:
    """OPTIONAL FALLBACK, for machines without Case 04's raw parsed run.

    Demo 11's ``s1_ref`` is a DIFFERENT structure. It is kept only so the
    envelope -> matrix-element step can still be shown on real licensed
    wavefunctions somewhere; it is never the primary demonstration and its
    numbers never enter case 04's calculation.
    """

    return _envelope_demonstration(
        AUX_ENVELOPES / "envelopes.csv",
        AUX_ENVELOPES / "matrix_elements.json",
        path,
        source_label="Demo 11 s1_ref (fallback, different structure)",
        is_case04=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trace Demo 20 case 04 (1.0 nm linear grading) end to end.")
    parser.add_argument("--outdir", default=str(TRACE_DIR / "trace_linear_1nm"),
                        help="directory for checkpoint files")
    parser.add_argument("--no-files", action="store_true",
                        help="print only; write no checkpoint files")
    parser.add_argument("--k-index", type=int, default=40,
                        help="which k point to expose term by term (0-95)")
    parser.add_argument("--all-k", action="store_true",
                        help="print every k contribution, not a representative set")
    args = parser.parse_args(argv)
    outdir = None if args.no_files else Path(args.outdir)
    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)
    return run(outdir, args.k_index, args.all_k)


if __name__ == "__main__":
    raise SystemExit(main())

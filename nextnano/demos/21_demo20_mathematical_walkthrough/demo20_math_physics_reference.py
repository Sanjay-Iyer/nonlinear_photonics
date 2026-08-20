r"""Demo 21 - the mathematics of Demo 20, collected in one readable file.

PURPOSE
=======
Demo 20 spreads its calculation over ten numbered stages plus a cross-demo
parser chain. That is good engineering and poor pedagogy: no single file shows
the equations in the order the physics uses them. This module is that single
file.

It is a **reference**, not a reimplementation. Demo 20's results are produced by
Demo 20. Nothing here is imported by Demo 20, and nothing here changes a Demo 20
number.

HOW TO READ THE LABELS
======================
Every public callable below carries exactly one of three labels:

``# ACTUAL PRODUCTION FUNCTION``
    The Demo 20 (or shared) function itself, re-exported under this namespace.
    Calling it here calls the same object Demo 20 calls. This is what determines
    Demo 20's results.

``# EDUCATIONAL WRAPPER AROUND PRODUCTION FUNCTION``
    Calls the production function and returns its result, adding only an
    explanatory docstring and/or extra printed/returned intermediates. The
    number comes from production code.

``# EDUCATIONAL REPRODUCTION OF THE EQUATION``
    Written out here from the equation, *not* used by Demo 20. It exists so the
    formula can be read without indirection. Every one of these names the
    production implementation it mirrors, and
    :func:`self_check` asserts that the reproduction agrees with production to
    machine precision. If a reproduction ever disagrees, the reproduction is
    wrong, not production.

WHAT DEMO 20 COMPUTES
=====================
Interband second-harmonic susceptibility chi2_xzx of a GaAs/AlGaAs asymmetric
coupled quantum well (ACQW), in pm/V, as a function of the fundamental
wavelength, for 13 interface-grading cases. The governing equation is Ramesh
2023 Eq. (3) with Eq. (5) and Eq. (6):

    chi2_xzx(w1,w2) = [N_z e^3 r_ehh^2 / (6 eps0 hbar^2)] SUM_k|| SUM_m,n,l (A - B)

Demo 20 evaluates the algebraically equivalent ENERGY form (see
``s06_chi2.py`` module docstring, lines 22-33).

DIVISION OF RESPONSIBILITY
==========================
    Python / Demo 20 :  geometry, x_Al(z), deck rendering, envelope
                        normalization, overlap and position matrix elements,
                        transition-energy dispersion, k measure, the triple
                        sum, prefactor, unit conversion, 1550 nm extraction.
    nextnano++       :  band-edge profile from x_Al(z), the 1D envelope-function
                        Schroedinger problem, eigenenergies E_n and envelopes
                        psi_n(z). BLACK BOX from Python's point of view.
    DFT (external)   :  r_e,hh = 0.751 nm only. One scalar constant, published,
                        not computed anywhere in this repository.

Run this file directly for a guided tour with the 1.0 nm linear case:

    python demo20_math_physics_reference.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

DEMO21_DIR = Path(__file__).resolve().parent
DEMOS_DIR = DEMO21_DIR.parent
DEMO20_DIR = DEMOS_DIR / "20_quantum_well_interface_grading_scaled"
SHARED_DIR = DEMOS_DIR / "_shared"

for _path in (DEMO20_DIR,):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# --- Demo 20's own modules, imported unmodified ------------------------------
import config20                        # noqa: E402
import s01_cases as cases              # noqa: E402
import s02_grading as grading          # noqa: E402
import s03_inputs as inputs            # noqa: E402
import s05_extract as extract          # noqa: E402
import s06_chi2 as chi2mod             # noqa: E402
import s07_analysis as analysis        # noqa: E402

#: The case this reference uses for every worked number.
WORKED_CASE_ID = "04"
WORKED_CASE_NAME = "Linear 1.0 nm"


# =============================================================================
# 0. PHYSICAL CONSTANTS AND THE ONE EXTERNAL (DFT) QUANTITY
# =============================================================================
# ACTUAL PRODUCTION FUNCTION (constants re-exported, not redefined)
#
# Source: nextnano/demos/20_.../s06_chi2.py:110-119 (CODATA 2018).
# These names are aliases for the same module-level floats Demo 20 multiplies
# by; there is no second copy of any constant in this file.

ELEMENTARY_CHARGE_C = chi2mod.ELEMENTARY_CHARGE_C          # e   [C]
VACUUM_PERMITTIVITY_F_PER_M = chi2mod.VACUUM_PERMITTIVITY_F_PER_M  # eps0 [F/m]
REDUCED_PLANCK_J_S = chi2mod.REDUCED_PLANCK_J_S            # hbar [J s]
ELECTRON_MASS_KG = chi2mod.ELECTRON_MASS_KG                # m0  [kg]
HC_EV_NM = chi2mod.HC_EV_NM                                # hc  [eV nm]

#: THE ONLY DFT-DERIVED NUMBER IN DEMO 20.
#:
#: r_e,hh = 7.51 Angstrom = 0.751 nm, the *bulk GaAs interband Bloch* position
#: matrix element <u_e|z|u_hh> between the cell-periodic parts of the
#: conduction and heavy-hole Bloch functions at Gamma. Ramesh 2023 (APL 123,
#: 251111) computed it with VASP/HSE06. Demo 20 reads it from
#: ``demo20_config.yaml:97 (chi2.r_e_hh_nm)``; nothing in this repository
#: recomputes it.
#:
#: It is a POSITION, not a dipole: Eq. (3) already carries e^3, so r must never
#: be multiplied by charge again. Provenance: docs/demo14_physics_sources.md:62.
#:
#: What DFT did NOT calculate: every envelope quantity below. The subband
#: energies, the envelopes psi_n(z), the overlaps O_nm and the envelope position
#: matrices z^e, z^hh all come from nextnano++ plus Python post-processing.
R_E_HH_NM_DFT = 0.751


# =============================================================================
# 1. GEOMETRY AND INTERFACE POSITIONS
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s02_grading.py
# Function: geometry (line 103), interface_positions (line 139),
#           interface_directions (line 151)
# Called by: s03_inputs.build_case, s04_solver.parse_case, s07_analysis
# Performed by: Python
#
# Mathematics
# -----------
#     outer   = period_barrier / 2
#     I1      = outer
#     I2      = I1 + thick_well
#     I3      = I2 + tunnel_barrier
#     I4      = I3 + thin_well
#     domain  = I4 + outer
#
# a cumulative sum of the four configured layer thicknesses. For Demo 20's
# frozen geometry (7.1 / 1.8 / 2.9 / 18.2 nm) this gives
# I1..I4 = 9.1, 16.2, 18.0, 20.9 nm on a [0, 30] nm domain.
#
# Interface direction pairs (x_left, x_right), from
# ``materials.barrier_al_fraction = 0.55`` and ``well_al_fraction = 0.0``:
#     I1 (0.55, 0.00)   AlGaAs -> thick GaAs well
#     I2 (0.00, 0.55)   thick well -> tunnel barrier
#     I3 (0.55, 0.00)   tunnel barrier -> thin well
#     I4 (0.00, 0.55)   thin well -> AlGaAs
#
# Units: nm throughout. Al fraction is dimensionless.

geometry = grading.geometry
interface_positions = grading.interface_positions
interface_directions = grading.interface_directions


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s02_grading.py:139
def interface_positions_from_thicknesses(
    thick_well_nm: float, tunnel_barrier_nm: float,
    thin_well_nm: float, period_barrier_nm: float,
) -> dict[str, float]:
    """The four interface coordinates, written as a bare cumulative sum.

    Physical purpose
    ----------------
    Fix where in the growth direction each material boundary sits. Everything
    downstream - grading, band edges, wavefunction shape - is positioned
    relative to these four numbers, and grading never moves them.

    Mathematics
    -----------
        outer = period_barrier / 2
        I1 = outer
        I2 = I1 + thick_well
        I3 = I2 + tunnel_barrier
        I4 = I3 + thin_well

    Units: all nm.

    Simple interpretation
    ---------------------
    Stack the layers left to right and write down where each join lands. Half
    the period barrier is put on each side so one full period is [0, 30] nm.
    """

    outer = period_barrier_nm / 2.0
    i1 = outer
    i2 = i1 + thick_well_nm
    i3 = i2 + tunnel_barrier_nm
    i4 = i3 + thin_well_nm
    return {"I1": i1, "I2": i2, "I3": i3, "I4": i4}


# =============================================================================
# 2. INTERFACE GRADING FUNCTIONS  f(u)
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s02_grading.py
# Function: profile_fraction (line 162)
# Called by: s02_grading.evaluate_composition (line 248)
# Performed by: Python
#
# Inputs:  u (array, dimensionless, clipped to [0,1]), shape name,
#          sigmoid_steepness = 10.0, erf_span_sigma = 3.0
# Outputs: f(u), dimensionless, f(0) = 0 and f(1) = 1 exactly
#
# Mathematics
# -----------
#     linear   f(u) = u
#     fermi    L(u) = 1/(1 + exp(-k(u - 1/2))),  k = 10
#              f(u) = (L(u) - L(0)) / (L(1) - L(0))
#     erf      f(u) = (erf(s(u-1/2)) - erf(-s/2)) / (erf(s/2) - erf(-s/2)), s = 3
#     cosine   f(u) = (1 - cos(pi u)) / 2
#     abrupt   f(u) = 0 for u < 1/2, else 1
#
# The 1.0 nm linear case uses ONLY the linear branch, f(u) = u -- literally the
# identity on the clipped coordinate. The other four shapes are listed because
# they share this one function; they are not evaluated for case 04.

profile_fraction = grading.profile_fraction


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s02_grading.py:162 (the
# ``key == "linear"`` branch, which returns ``x`` = the clipped u)
def linear_profile(z_nm, interface_centre_nm: float, width_nm: float,
                   x_left: float, x_right: float) -> np.ndarray:
    r"""Composition across ONE linearly graded interface.

    Physical purpose
    ----------------
    Smoothly change the Al composition from the material on the left of an
    interface to the material on the right, instead of jumping between them at
    a single grid point.

    Mathematics
    -----------
        z_minus = z_i - W/2                (grade starts here)
        z_plus  = z_i + W/2                (grade ends here)
        u(z)    = clip((z - z_minus)/W, 0, 1)
        f(u)    = u                        (linear family)
        x_Al(z) = x_L + (x_R - x_L) f(u)

    where
        z    spatial coordinate                       [nm]
        z_i  nominal interface centre                 [nm]
        W    FULL start-to-end transition width       [nm]
        x_L  Al fraction on the left of the interface [dimensionless]
        x_R  Al fraction on the right                 [dimensionless]

    Simple interpretation
    ---------------------
    Instead of the Al concentration jumping from 0.55 to 0 at exactly 9.1 nm,
    it slides down in a straight line over the 1 nm from 8.6 nm to 9.6 nm.
    The interface centre does not move; the material on either side is eaten
    into by W/2.

    Worked example (case 04, interface I1)
    --------------------------------------
        z_i = 9.1, W = 1.0, x_L = 0.55, x_R = 0.0
        z = 8.60  ->  u = 0.00  ->  x_Al = 0.550
        z = 8.85  ->  u = 0.25  ->  x_Al = 0.4125
        z = 9.10  ->  u = 0.50  ->  x_Al = 0.275
        z = 9.60  ->  u = 1.00  ->  x_Al = 0.000
    """

    z = np.asarray(z_nm, dtype=float)
    if width_nm <= 0:
        raise ValueError("linear_profile needs a positive width")
    z_minus = interface_centre_nm - width_nm / 2.0
    u = np.clip((z - z_minus) / width_nm, 0.0, 1.0)
    f = u                                        # f(u) = u
    return x_left + (x_right - x_left) * f


# =============================================================================
# 3. ALUMINIUM COMPOSITION  x_Al(z)  OVER THE WHOLE DEVICE
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s02_grading.py
# Function: evaluate_composition (line 211), profile_mesh (line 259),
#           build_profile (line 312)
# Called by: s03_inputs.build_case (line 217) -> the nextnano++ deck
# Performed by: Python
#
# Mathematics (evaluate_composition)
# ----------------------------------
# Step 1, the abrupt skeleton:
#     x_Al(z) = 0.55 everywhere
#     x_Al(z) = 0.00 on the closed interval [I1, I2]     (thick well)
#     x_Al(z) = 0.00 on the closed interval [I3, I4]     (thin well)
# Step 2, for each interface with W > 0, overwrite the window
# [z_i - W/2, z_i + W/2] with x_L + (x_R - x_L) f(u).  Later writes win, so the
# ramps overwrite the well edges laid down in step 1.
#
# ``build_profile`` samples this on two grids:
#     x_nm             the DECK mesh (0.05 nm + every interface centre and grade
#                      endpoint) -- this is what nextnano++ receives
#     x_nm_continuous  a 20x finer AUDIT grid -- never an input, used only to
#                      measure what the sampling lost
#
# Units: z in nm, x_Al dimensionless in [0, 0.55].

evaluate_composition = grading.evaluate_composition
profile_mesh = grading.profile_mesh
build_profile = grading.build_profile
grade_intervals = grading.grade_intervals
plateau_lengths_nm = grading.plateau_lengths_nm
validate_realized = grading.validate_realized


# EDUCATIONAL WRAPPER AROUND PRODUCTION FUNCTION
def composition_profile_with_breakdown(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> dict[str, Any]:
    """``build_profile`` plus the per-interface bookkeeping, in one dict.

    Adds nothing to the physics: the arrays returned are exactly
    ``grading.build_profile(cfg, case)``'s arrays. The extra keys are the
    interface centres, the grade windows and the surviving pure-material
    plateau lengths, so one call shows both the result and why it looks that
    way.
    """

    profile = build_profile(cfg, case)
    return {
        "profile": profile,
        "interfaces_nm": interface_positions(cfg),
        "directions": interface_directions(cfg),
        "grade_intervals_nm": grade_intervals(cfg, case),
        "plateau_lengths_nm": plateau_lengths_nm(cfg, case),
        "deck_mesh_points": int(profile.x_nm.size),
        "audit_mesh_points": int(profile.x_nm_continuous.size),
    }


# =============================================================================
# 4. MATERIAL / BAND-STRUCTURE QUANTITIES
# =============================================================================
# WHAT PYTHON SUPPLIES vs WHAT NEXTNANO++ LOOKS UP
#
# Demo 20 does NOT write any band parameter into the deck. It writes
#   * the alloy composition field x_Al(z), as ternary regions or a DAT table
#   * the material NAMES "Al(x)Ga(1-x)As" and "GaAs"
#   * the substrate "GaAs", the crystal orientation, and T = 300 K
#
# nextnano++ then looks up every band parameter (E_g, band offsets, effective
# masses, alloy bowing, deformation potentials, Varshni coefficients) in its
# proprietary ``database.nnp`` and interpolates them at each x_Al(z). Those
# numbers are not visible in this repository.
#
# BACKGROUND THEORY - not directly evaluated in Python:
#   the conduction and heavy-hole band edges are functions of the local alloy
#   fraction, V_e(z) = E_c(x_Al(z)) and V_h(z) = E_v(x_Al(z)), with the alloy
#   dependence and its bowing supplied by the database. Demo 20 never forms
#   V_e or V_h; it never sees them except as the ``bandedges`` output file that
#   the Demo 11 parser reads for QC.
#
# The ONE material-ish number Python does own is the pair of in-plane effective
# masses used for the k|| dispersion of the transition energy (Section 10):
#   k_parallel.electron_mass_m0            = 0.067  (GaAs Gamma electron)
#   k_parallel.heavy_hole_inplane_mass_m0  = 0.112  (GaAs in-plane HH)
# These are configured in ``demo20_config.yaml:140-141`` and are used ONLY by
# ``s06_chi2.transition_energies_eV``. They are not sent to nextnano++ and do
# not affect the eigenstates.


# ACTUAL PRODUCTION FUNCTION
# File: nextnano/demos/20_.../s06_chi2.py:235 (Chi2Settings.reduced_mass_kg)
#
# Mathematics
# -----------
#     1/mu = 1/m_e + 1/m_hh,par        (both in units of m0)
#     mu   = m0 / (1/m_e + 1/m_hh,par)
#
# For 0.067 and 0.112 this is mu = 0.0419218 m0.
def reduced_inplane_mass_kg(settings: chi2mod.Chi2Settings) -> float:
    """The in-plane reduced mass of the electron-heavy-hole pair, in kg."""

    return settings.reduced_mass_kg()


# =============================================================================
# 5. NEXTNANO++ QUANTUM-WELL CALCULATION
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s03_inputs.py
# Function: _native_blocks (line 107), render_deck (line 169), build_case (207)
# Then:     nextnano/demos/20_.../s04_solver.py:191 solve_case  [LICENSED]
# Performed by: Python renders, nextnano++ solves.
#
# WHAT PYTHON SENDS TO NEXTNANO++ (the deck, case 04)
# ---------------------------------------------------
#   global{ simulate1D{} temperature = 300.0 substrate{GaAs}
#           crystal_zb{ x_hkl=[1,0,0] y_hkl=[0,1,0] } }
#   grid{ xgrid{ control lines at 0.0/0.5nm, 9.1/0.05nm,
#                20.9/0.05nm, 30.0/0.5nm spacing } }
#   structure{ everywhere ternary_constant Al(x)Ga(1-x)As alloy_x = 0.55
#              line [9.1,16.2]  binary GaAs
#              line [18.0,20.9] binary GaAs
#              line [8.6, 9.6]  ternary_linear alloy_x = [0.55, 0.00]
#              line [15.7,16.7] ternary_linear alloy_x = [0.00, 0.55]
#              line [17.5,18.5] ternary_linear alloy_x = [0.55, 0.00]
#              line [20.4,21.4] ternary_linear alloy_x = [0.00, 0.55] }
#   classical{ Gamma{} HH{} LH{} SO{} output_bandedges output_bandgap }
#   quantum{ region{ name="acqw"  x = [7.1, 22.9]  no_density = yes
#                    boundary{ x = dirichlet }
#                    Gamma{ num_ev = 6 }  HH{ num_ev = 6 }
#                    output_states{ max_num=6 envelopes=yes probabilities=yes }
#                    transition_energies{ Gamma_HH{} }
#                    overlap_integrals{ Gamma_HH{} }
#                    dipole_moment_matrix_elements{
#                        polarization{ name="growth_z" re=[1,0,0] }
#                        Gamma{} HH{} } } }
#   run{ quantum{} }
#
# Note the coordinate naming: nextnano++ calls the growth axis ``x``; the
# susceptibility notation and every plot call the same axis ``z``.
#
# WHAT NEXTNANO++ CALCULATES  (BLACK BOX from Python)
# ---------------------------------------------------
# BACKGROUND THEORY - not evaluated anywhere in Python:
# a single-band (Gamma) envelope-function eigenproblem per band, on the quantum
# region [7.1, 22.9] nm with Dirichlet walls psi(7.1) = psi(22.9) = 0:
#
#     [ -(hbar^2/2) d/dz ( 1/m*(z) d/dz ) + V(z) ] psi_n(z) = E_n psi_n(z)
#
# with the BenDaniel-Duke ordering of the position-dependent mass, m*(z) and
# V(z) both following from x_Al(z) through the database. ``num_ev = 6`` asks
# for the six lowest Gamma states and the six highest-energy HH states;
# ``no_density = yes`` means no Poisson loop runs, so V(z) is the bare
# heterostructure potential with no self-consistent electrostatics.
# ``run{ quantum{} }`` triggers exactly that solve and nothing else.
#
# WHAT COMES BACK TO PYTHON
# -------------------------
#   energy spectrum tables    E_n for Gamma and for HH               [eV]
#   envelope tables           psi_n(z) sampled on the solver grid    [arb.]
#   band edges, alloy profile, probabilities                         [QC only]
#
# nextnano++'s own ``transition_energies`` / ``overlap_integrals`` /
# ``dipole_moment_matrix_elements`` blocks are requested for cross-checking and
# completeness, but the numbers chi2 uses are recomputed in Python from the
# envelopes (Sections 7-9). That is a deliberate choice: it keeps the
# normalization and the integration rule under Demo 20's control.

render_deck = inputs.render_deck
build_case = inputs.build_case
deck_is_complete = inputs.deck_is_complete


# EDUCATIONAL WRAPPER AROUND PRODUCTION FUNCTION
def nextnano_input_summary(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> dict[str, Any]:
    """Everything Demo 20 hands to nextnano++ for one case, as a dict.

    The deck text itself is the production output of ``inputs.build_case``;
    this only pulls out the fields worth reading one at a time.
    """

    g, profile, blocks, deck = build_case(cfg, case)
    return {
        "deck_text": deck,
        "deck_complete": deck_is_complete(deck),
        "render_method": case.render_method,
        "implementation_type": case.implementation_type,
        "imported_table_rows": len(blocks["datafile"].splitlines()),
        "domain_nm": list(g.domain_nm),
        "quantum_region_nm": [g.quantum_start_nm, g.quantum_end_nm],
        "mesh_spacing_active_nm": float(cfg["mesh"]["active_region_grid_spacing_nm"]),
        "mesh_spacing_outer_nm": float(cfg["mesh"]["outer_grid_spacing_nm"]),
        "temperature_K": float(cfg["materials"]["temperature_K"]),
        "electron_states_requested": int(cfg["states"]["number_of_electron_states"]),
        "hole_states_requested": int(cfg["states"]["number_of_hole_states"]),
        "boundary_condition": "dirichlet at both ends of the quantum region",
        "self_consistent_poisson": False,
        "composition_points_sent": int(profile.x_nm.size),
    }


# =============================================================================
# 6. EIGENENERGIES AND WAVEFUNCTIONS  (e1, e2, hh1, hh2)
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# Licensed path:  nextnano/demos/20_.../s04_solver.py:272 parse_case
#                 -> demo14.analyse_real_trial (demo14.py:852)
#                 -> demo11.analyse_case (demo11.py:431)
#                 -> quantum1d.parse_one_band_run  [electron energies+envelopes]
#                 -> demo11._hole_states (demo11.py:246) [HH energies+envelopes]
# Home path:      nextnano/demos/20_.../s05_extract.py:111 from_master_table
#                 reads the SAME numbers back out of a licensed run's results
#                 CSV (E1_eV, E2_eV, HH1_eV, HH2_eV, O11..O22, z_e.., z_hh..).
#
# WHAT THE FOUR STATES ARE
# ------------------------
#   e1   lowest conduction (Gamma) subband of the coupled pair
#   e2   second conduction subband
#   hh1  most confined heavy-hole subband
#   hh2  second heavy-hole subband
#
# Each is an eigenpair (E_n, psi_n(z)) of the envelope Hamiltonian of Section 5.
# Energies are on nextnano's SINGLE electron-energy scale, so an interband
# transition energy is a plain subtraction, E_e - E_hh, with no band gap added
# by hand. nextnano++ lists hole states in DECREASING electron-scale energy, so
# index order is confinement order and HH1 is the most confined hole; that order
# is preserved and never re-sorted (demo11.py:246-254).
#
# Demo 20 asks for 6 states per band but the susceptibility sum uses only the
# first 2 of each: ``states.max_states_per_band = 2``, enforced by
# ``s06_chi2.CaseStates.truncated`` (s06_chi2.py:490).
#
# Case 04 values (real licensed output, demo19_master_results.csv row 04):
#   E_e1  = 2.941158138088 eV
#   E_e2  = 3.061022858158 eV
#   E_hh1 = 1.447805442384 eV
#   E_hh2 = 1.412791422186 eV

from_master_table = extract.from_master_table
states_from_nextnano_metrics = extract.states_from_nextnano_metrics
CaseStates = chi2mod.CaseStates


# =============================================================================
# 7. WAVEFUNCTION NORMALIZATION / INTERPOLATION
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/_shared/chi2.py
# Class:    BandStates.__post_init__ (line 133)
# Called by: demo11._band_states (demo11.py:240) on the licensed path
# Performed by: Python (post-processing of nextnano++ output)
#
# NORMALIZATION: YES, PYTHON DOES IT.
#     norm     = trapezoid( psi_i(z)^2, z )        [chi2.py:157]
#     psi_i   <- psi_i / sqrt(norm)                [chi2.py:162]
# so that int |psi_i|^2 dz = 1 with z in nm. nextnano++'s envelope output is
# NOT assumed to be normalized on this grid; the normalization is re-imposed in
# Python before any matrix element is formed.
#
# INTERPOLATION: NO. There is none.
#     demo11.analyse_case (demo11.py:467-473) REQUIRES the electron and
#     heavy-hole envelopes to already be on the identical grid and raises
#     "electron and heavy-hole envelopes are on different grids" otherwise.
#     No resampling, no common-grid projection, no spline.
#
# ORTHONORMALITY: checked, not enforced.
#     BandStates.orthonormality_error (chi2.py:188) computes
#     max |<psi_i|psi_j> - delta_ij| and demo11 gates on it at 1e-3. This
#     matters because Eq. (5)/(6) contain DIAGONAL position elements
#     <psi_i|z|psi_i>, which individually depend on where z = 0 is put; the
#     origin dependence cancels between the electron and hole terms only if the
#     within-band basis is orthonormal.
#
# On the home (master-table) path none of this runs again: the O and z matrices
# in the CSV were produced by exactly these functions during the licensed run.

if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))
import chi2 as shared_chi2             # noqa: E402  (nextnano/demos/_shared/chi2.py)

BandStates = shared_chi2.BandStates


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/_shared/chi2.py:155-162
def normalize_envelope(psi: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
    r"""Scale one envelope so that its probability integrates to 1.

    Physical purpose
    ----------------
    A wavefunction returned by a solver has an arbitrary overall scale. Every
    matrix element below is only meaningful once that scale is fixed by the
    requirement that the particle is somewhere with probability one.

    Mathematics
    -----------
        N     = int |psi(z)|^2 dz   ~=  sum_i psi(z_i)^2 dz_i   (trapezoid)
        psi  <- psi / sqrt(N)

    Units: z in nm, so the normalized psi carries nm^(-1/2).

    Simple interpretation
    ---------------------
    Divide the curve by however tall it happens to be, so the area under
    psi-squared is exactly one.
    """

    norm = float(np.trapezoid(np.asarray(psi, float) ** 2, np.asarray(z_nm, float)))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("envelope has zero or non-finite norm")
    return np.asarray(psi, float) / math.sqrt(norm)


# =============================================================================
# 8. OVERLAP INTEGRALS  O_nm = <psi_e,n | psi_hh,m>
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/_shared/chi2.py
# Function: overlap_matrix (line 204)
# Called by: demo11.analyse_case (demo11.py:527) during the licensed run;
#            written to matrix_elements.json (demo11.py:803) and to the master
#            table columns O11, O12, O21, O22.
# Performed by: Python
#
# Mathematics
# -----------
#     O_nm = <psi_e,n | psi_hh,m> = int psi_e,n(z) psi_hh,m(z) dz
#
# discretized as ``np.trapezoid(psi_e[:,n] * psi_hh[:,m], z_nm)``, i.e.
#
#     O_nm ~= SUM_i  (1/2)(g_i + g_{i+1})(z_{i+1} - z_i),
#     g_i  =  psi_e,n(z_i) psi_hh,m(z_i)
#
# Units: DIMENSIONLESS. Both envelopes carry nm^(-1/2) and dz carries nm.
# Interpretation: how much the electron and hole envelopes look alike. O11 near
# 1 means e1 and hh1 sit on top of each other, so that interband transition is
# strong.
#
# Case 04:  O = [[ 0.9822755287674644,  0.01540332812208936],
#                [-0.08353004083929513, 0.3831404861807044 ]]
#
# THIS IS NOT THE SAME OBJECT AS SECTION 9. O_nm is a pure ENVELOPE overlap
# between two different bands; <n|z|m> in Section 9 is a WITHIN-band position
# expectation. They enter Eq. (5)/(6) in different slots and must never be
# merged into a generic "overlap".

overlap_matrix = shared_chi2.overlap_matrix


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/_shared/chi2.py:204
def envelope_overlap(psi_a: np.ndarray, psi_b: np.ndarray,
                     z_nm: np.ndarray) -> float:
    r"""``<psi_a | psi_b>`` by trapezoidal quadrature.

    Mathematics
    -----------
        I = int psi_a(z) psi_b(z) dz
          ~= sum_i (1/2)[f(z_i) + f(z_{i+1})] (z_{i+1} - z_i),  f = psi_a psi_b

    ``np.trapezoid`` is exactly that composite trapezoidal rule; it does NOT
    assume a uniform grid, it uses the actual spacings of ``z_nm``.
    """

    return float(np.trapezoid(np.asarray(psi_a, float) * np.asarray(psi_b, float),
                              np.asarray(z_nm, float)))


# =============================================================================
# 9. POSITION MATRIX ELEMENTS  z^e_nl AND z^hh_ml   (ENVELOPE, WITHIN BAND)
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/_shared/chi2.py
# Function: position_matrix (line 220)
# Called by: demo11.analyse_case (demo11.py:528-529)
# Performed by: Python
#
# Mathematics
# -----------
#     z^e_nl  = <psi_e,n | z | psi_e,l>  = int psi_e,n(z) z psi_e,l(z) dz
#     z^hh_ml = <psi_hh,m| z | psi_hh,l> = int psi_hh,m(z) z psi_hh,l(z) dz
#
# discretized as ``np.trapezoid(psi[:,i] * z_nm * psi[:,j], z_nm)``.
#
# Units: nm.
#
# Meaning:
#   diagonal  z^e_11  = the CENTROID of state e1, i.e. where that electron sits
#   off-diag  z^e_12  = the intersubband transition dipole (over e), which is
#                       what makes an ASYMMETRIC well nonlinear at all
#
# Case 04:
#   z^e  = [[12.72452731946466, 1.0251735847808658],
#           [1.0251735847808656, 18.661190322705767]]  nm
#   z^hh = [[12.65139233424412, 1.4323684065114455],
#           [1.4323684065114457, 12.73014553601777 ]]  nm
#
# Read the diagonals: e1 sits at 12.72 nm (in the thick well) and e2 at
# 18.66 nm (pushed into the thin well) - a 5.94 nm separation. Both holes sit
# at ~12.7 nm, a separation of only 0.079 nm. That asymmetry between the
# electron and hole ladders is the entire source of chi2 in this structure.
#
# THE THREE DISTINCT MATRIX-ELEMENT SPECIES IN DEMO 20
# ----------------------------------------------------
#   O_nm      <psi_e,n|psi_hh,m>     interband, ENVELOPE, dimensionless
#   z^e_nl    <psi_e,n|z|psi_e,l>    intraband, ENVELOPE, nm
#   r_e,hh    <u_e|z|u_hh>           interband, BULK BLOCH cell part, nm, DFT
#
# They multiply, they do not substitute: the full interband dipole factorizes
# (envelope-function approximation) into the bulk Bloch part r_e,hh times the
# envelope overlaps O, and Eq. (3) carries r_e,hh^2 out of the sum entirely
# while the O's stay inside.

position_matrix = shared_chi2.position_matrix


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/_shared/chi2.py:220
def position_expectation(psi_a: np.ndarray, psi_b: np.ndarray,
                         z_nm: np.ndarray) -> float:
    r"""``<psi_a | z | psi_b>`` in nm, by trapezoidal quadrature.

    Mathematics
    -----------
        I = int psi_a(z) z psi_b(z) dz
          ~= sum_i (1/2)[f(z_i) + f(z_{i+1})] (z_{i+1} - z_i),  f = psi_a z psi_b

    Simple interpretation
    ---------------------
    For a = b this is the average position of that state - its centre of mass.
    For a != b it measures how much an oscillating field along z can move the
    particle from one state into the other.
    """

    z = np.asarray(z_nm, float)
    return float(np.trapezoid(np.asarray(psi_a, float) * z * np.asarray(psi_b, float), z))


# =============================================================================
# 10. TRANSITION ENERGIES  dE_nm(k)
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py
# Function: transition_energies_eV (line 537)
# Called by: chi2_spectrum (s06_chi2.py:640)
# Performed by: Python
#
# Mathematics
# -----------
#     dE_nm(k) = (E_e,n - E_hh,m) + hbar^2 k^2 / (2 mu)
#     1/mu     = 1/m_e + 1/m_hh,par
#
# The zero-k part is a plain subtraction on nextnano's single energy scale.
# The k-dependent part is a parabolic in-plane dispersion applied to the PAIR,
# with the reduced mass, because the electron disperses up and the hole
# disperses down and the transition energy is their difference.
#
# Shape: (n_e, n_h, n_k) = (2, 2, 96) for Demo 20. Units eV.
#
# CRITICAL MODELLING POINT: the envelope matrix elements O, z^e, z^hh are
# treated as k-INDEPENDENT. Only the denominators move with k. That is an
# approximation of the model, applied identically in Demo 19 and Demo 20.
#
# Case 04 zero-k transition energies:
#     dE_11 = E_e1 - E_hh1 = 1.4933526957039998 eV
#     dE_12 = E_e1 - E_hh2 = 1.5283667159019998 eV
#     dE_21 = E_e2 - E_hh1 = 1.613217415774    eV
#     dE_22 = E_e2 - E_hh2 = 1.648231435972    eV

transition_energies_eV = chi2mod.transition_energies_eV


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:537
def transition_energy_at_k(
    e_energy_eV: float, h_energy_eV: float, k_per_nm: float,
    reduced_mass_kg: float,
) -> float:
    r"""One transition energy at one in-plane wavevector, in eV.

    Mathematics
    -----------
        dE(k) = (E_e - E_hh) + hbar^2 k^2 / (2 mu)

    with k converted nm^-1 -> m^-1 (factor 1e9) and the kinetic term converted
    J -> eV (divide by e).

    Simple interpretation
    ---------------------
    An electron-hole pair that is also moving sideways in the plane of the well
    needs more photon energy than one sitting still. This says how much more.
    """

    k_per_m = float(k_per_nm) * 1.0e9
    kinetic_J = (REDUCED_PLANCK_J_S ** 2) * k_per_m ** 2 / (2.0 * reduced_mass_kg)
    return float(e_energy_eV) - float(h_energy_eV) + kinetic_J / ELEMENTARY_CHARGE_C


# =============================================================================
# 11. k-SPACE GRID AND INTEGRATION WEIGHTS
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py
# Function: k_grid (line 346); k_max_per_nm (line 223)
# Called by: chi2_spectrum (s06_chi2.py:639)
# Performed by: Python
#
# GRID
# ----
#     k_max = fraction_of_bz * (pi / a)         [legacy_pi_over_a convention]
#           = 0.10 * pi / 0.565325 nm
#           = 0.5557144392322635 nm^-1
#     k     = linspace(0, k_max, 96)            -> dk_uniform = k_max/95
#
# WEIGHTS - the derivation, exactly as implemented
# ------------------------------------------------
#     sum_k f(k)        ->  A/(2pi)^2  int d^2k f(k)
#     (1/A) sum_k f(k)  ->  1/(2pi)^2  int d^2k f(k)
#     isotropic:        int d^2k f(|k|) = 2pi int_0^kmax k f(k) dk
#     substitute:       (1/A) sum_k f  ->  (1/(2pi)) int_0^kmax k f(k) dk
#
# so the implemented weight is
#
#     w_i = g_s * (k_i / (2pi)) * dk_i          [convention d2k_over_2pi_squared]
#
# with g_s = 2 the spin degeneracy and dk_i the trapezoidal weights on a
# uniform grid (full step inside, half step at both ends).
#
# The (2pi)^2 EXPERIMENT: the alternative convention keeps the 2pi from the
# angular integral and drops the 1/(2pi)^2 density-of-states factor,
#
#     w_i = g_s * (2pi * k_i) * dk_i            [convention bare_d2k]
#
# which is EXACTLY (2pi)^2 = 39.47841760435743 times larger, pointwise. That is
# a magnitude convention switch, not a missing factor and not a unit fix.
# See s06_chi2.py:44-105 for the full audit.
#
# Closed-form check (s06_chi2.analytic_disc_measure, line 398):
#     d2k_over_2pi_squared:  sum_i w_i = g_s k_max^2 / (4 pi)
#     bare_d2k:              sum_i w_i = g_s pi k_max^2
#
# Units: k in nm^-1, weights in nm^-2.

k_grid = chi2mod.k_grid
k_measure_total = chi2mod.k_measure_total
analytic_disc_measure = chi2mod.analytic_disc_measure
scaling_is_exact_constant = chi2mod.scaling_is_exact_constant
CONVENTION_DEMO19 = chi2mod.CONVENTION_DEMO19
CONVENTION_SCALED = chi2mod.CONVENTION_SCALED


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:346
def k_weights_demo19_convention(
    k_max_per_nm: float, points: int, spin_degeneracy: int = 2
) -> tuple[np.ndarray, np.ndarray]:
    r"""The radial grid and its ``int d^2k/(2pi)^2`` weights, written out.

    Mathematics
    -----------
        k_i  = i * k_max / (N-1),  i = 0..N-1
        dk_i = k_max/(N-1)         interior
             = k_max/(2(N-1))      at i = 0 and i = N-1   (trapezoid ends)
        w_i  = g_s * k_i/(2pi) * dk_i

    Simple interpretation
    ---------------------
    Carriers can also be moving sideways, and every sideways momentum
    contributes. Because everything only depends on |k|, the 2D integral over
    the disc collapses to a 1D integral over rings; the ring at radius k has
    circumference proportional to k, which is the factor of k in the weight.
    """

    k = np.linspace(0.0, float(k_max_per_nm), int(points))
    step = k[1] - k[0]
    dk = np.full_like(k, step)
    dk[0] = dk[-1] = 0.5 * step
    return k, (k / (2.0 * math.pi)) * dk * float(spin_degeneracy)


# =============================================================================
# 12. SUSCEPTIBILITY TERMS - THE TRIPLE SUM, TERM BY TERM
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py
# Function: chi2_spectrum (line 612); the sum itself is lines 641-661
# Performed by: Python
#
# THE EQUATION AS IMPLEMENTED (energy form)
# -----------------------------------------
#     chi2(E) = P * sum_i w_i * S(k_i, E)
#
#     S(k,E) = sum_m sum_n [ sum_l A'(n,m,l) - sum_l B'(n,m,l) ]
#
#     A'(n,m,l) = O_nm z^e_nl O_lm
#                 -----------------------------------------------
#                 [dE_nm(k) - 2E + i g] [dE_lm(k) - E + i g]
#
#     B'(n,m,l) = O_nm z^hh_ml O_nl
#                 -----------------------------------------------
#                 [dE_nm(k) - 2E + i g] [dE_nl(k) - E + i g]
#
# with m, n, l each running over {0, 1} (i.e. states 1 and 2), g = 0.005 eV,
# and E = hc/lambda the FUNDAMENTAL photon energy. Note the sign: A' is added
# (conduction/electron term) and B' is subtracted (valence/hole term). The two
# nearly cancel - that near-cancellation is real physics in this model and is
# the reason the loop is written out rather than collapsed into an einsum
# (s06_chi2.py:625-630).
#
# Term counting: 2 (m) x 2 (n) x 2 (l) = 8 conduction terms and 8 valence
# terms, 16 in all, minus any whose numerator is exactly zero (skipped at
# s06_chi2.py:650 and :656).
#
# INDEX MEANING
#     m  heavy-hole state of the pair being created
#     n  electron state of that pair
#     l  the intermediate partner state: an ELECTRON state in A', a HOLE state
#        in B'. Same letter, different band - this is the single easiest thing
#        to misread in the equation.
#
# Units of the summand: nm (from z) / eV^2 (from the two denominators). The
# k weight adds nm^-2. Section 14 converts the lot to pm/V.

chi2_spectrum = chi2mod.chi2_spectrum
chi2_both_conventions = chi2mod.chi2_both_conventions
Chi2Settings = chi2mod.Chi2Settings
settings_from_config = chi2mod.settings_from_config


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:641-661
def chi2_summand_terms(
    states: chi2mod.CaseStates, k_index: int, photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
) -> list[dict[str, Any]]:
    r"""Every individual (m, n, l) term of the triple sum at ONE k point.

    This is the production loop, unrolled into a list of records instead of
    accumulated into a complex number, so each term can be inspected. The
    arithmetic per term is character-for-character the production arithmetic.

    Mathematics
    -----------
        two_photon(n,m) = dE_nm(k) - 2E + i g
        one_photon(a,b) = dE_ab(k) -  E + i g

        conduction term (added):     O_nm z^e_nl O_lm
                                     / [two_photon(n,m) * one_photon(l,m)]
        valence term (subtracted):   O_nm z^hh_ml O_nl
                                     / [two_photon(n,m) * one_photon(n,l)]

    Returns one dict per term with its numerator, both denominators, its signed
    contribution, and enough labelling to identify it.
    """

    states = states.truncated(int(settings.max_states_per_band))
    overlap = np.asarray(states.overlap_electron_hole, float)
    z_e = np.asarray(states.position_matrix_electron_nm, float)
    z_h = np.asarray(states.position_matrix_hole_nm, float)
    k, _weights = k_grid(settings)
    transitions = transition_energies_eV(states, k, settings)
    gamma = settings.broadening_eV
    energy = float(photon_energy_eV)
    n_e, n_h = states.n_electron, states.n_hole

    two_photon = transitions[:, :, k_index] - 2.0 * energy + 1j * gamma
    one_photon = transitions[:, :, k_index] - 1.0 * energy + 1j * gamma

    records: list[dict[str, Any]] = []
    for m in range(n_h):
        for n in range(n_e):
            for l in range(n_e):
                numerator = overlap[n, m] * z_e[n, l] * overlap[l, m]
                records.append({
                    "term": "conduction",
                    "sign": +1,
                    "m": m + 1, "n": n + 1, "l": l + 1,
                    "label": f"+ O_{n+1}{m+1} z^e_{n+1}{l+1} O_{l+1}{m+1}",
                    "numerator_nm": numerator,
                    "denominator_two_photon_eV": complex(two_photon[n, m]),
                    "denominator_one_photon_eV": complex(one_photon[l, m]),
                    "contribution": (0.0 if numerator == 0.0 else
                                     complex(numerator
                                             / (two_photon[n, m] * one_photon[l, m]))),
                    "skipped_zero_numerator": numerator == 0.0,
                })
            for l in range(n_h):
                numerator = overlap[n, m] * z_h[m, l] * overlap[n, l]
                records.append({
                    "term": "valence",
                    "sign": -1,
                    "m": m + 1, "n": n + 1, "l": l + 1,
                    "label": f"- O_{n+1}{m+1} z^hh_{m+1}{l+1} O_{n+1}{l+1}",
                    "numerator_nm": numerator,
                    "denominator_two_photon_eV": complex(two_photon[n, m]),
                    "denominator_one_photon_eV": complex(one_photon[n, l]),
                    "contribution": (0.0 if numerator == 0.0 else
                                     -complex(numerator
                                              / (two_photon[n, m] * one_photon[n, l]))),
                    "skipped_zero_numerator": numerator == 0.0,
                })
    return records


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:643-644
def resonant_denominators(
    transition_energy_eV: float, photon_energy_eV: float, broadening_eV: float
) -> dict[str, complex]:
    r"""The two complex resonance denominators, for one transition and photon.

    Simple explanation
    ------------------
    The nonlinear response is huge when the light happens to match a transition
    the structure can actually make. These two numbers measure how badly the
    photon misses: small denominator = near resonance = big response. The
    imaginary part stops the answer being infinite exactly on resonance - it is
    the finite lifetime of the state.

    Mathematics
    -----------
        D2 = dE - 2 hbar w + i Gamma      two-photon (SHG) resonance
        D1 = dE -   hbar w + i Gamma      one-photon resonance

    Units: eV. Gamma = 5 meV = 0.005 eV (``chi2.broadening_meV``), entering as
    an ENERGY because Demo 20 evaluates the energy form of the equation; in the
    published angular-frequency form the same physical broadening would appear
    as Gamma/hbar in rad/s.
    """

    return {
        "two_photon": complex(transition_energy_eV - 2.0 * photon_energy_eV
                              + 1j * broadening_eV),
        "one_photon": complex(transition_energy_eV - 1.0 * photon_energy_eV
                              + 1j * broadening_eV),
    }


# =============================================================================
# 13. chi^(2) SUMMATION / k INTEGRATION
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py:661
# Statement: ``total[index] = np.dot(weights, accumulated)``
# Performed by: Python
#
# Mathematics
# -----------
#     sum_over_k(E) = sum_i w_i S(k_i, E)
#
# ONE dot product performs the whole in-plane integration, which is why every
# normalization decision is confined to ``k_grid``. ``accumulated`` is the
# complex array S(k_i, E) of shape (96,) built by the triple loop.
#
# Then, at s06_chi2.py:690:
#     chi2(E) = prefactor * sum_over_k(E)


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:661
def integrate_over_k(weights: np.ndarray, summand: np.ndarray) -> complex:
    """``sum_i w_i S(k_i)`` - the entire in-plane integral, as one dot product."""

    return complex(np.dot(np.asarray(weights, float), np.asarray(summand)))


# =============================================================================
# 14. PREFACTOR AND UNIT CONVERSION TO pm/V
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py
# Function: absolute_prefactor (line 514); n_z_for (line 289)
# Performed by: Python
#
# Mathematics
# -----------
#     prefactor = [ N_z e^3 r^2 / (6 eps0) ] * U * 1e12
#     U         = 1e-9 * 1e18 / e^2
#
# where the three factors of U undo the non-SI units the sum was evaluated in:
#     1e-9   position matrix elements were in nm     -> m
#     1e18   k-measure weights were in nm^-2         -> m^-2
#     1/e^2  the two energy denominators were in eV^2 -> J^2
# and the final 1e12 converts m/V -> pm/V.
#
# hbar^-2 does NOT appear: it is absorbed by writing both denominators in
# energy rather than angular frequency (s06_chi2.py:30-33).
#
# N_z, the sheet density of wells:
#     nz_mode = period_density  ->  N_z = 1 / (30 nm) = 3.3333333e7 m^-1
#     nz_mode = well_density    ->  N_z = 2 / (30 nm) = 6.6666667e7 m^-1
# The source text says only "number of QWs per unit length", so both readings
# exist; Demo 20 uses period_density and records the ambiguity (s06_chi2.py:289).
#
# Numerical value for Demo 20's frozen settings:
#     prefactor = 56.69816882497043   pm/V per unit of (nm / eV^2 / nm^2)
#
# Unit chain, checked analytically:  C^3 * m^2 / (F/m) * m^-2 * J^-2 = m/V.

absolute_prefactor = chi2mod.absolute_prefactor
n_z_for = chi2mod.n_z_for


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:514
def absolute_prefactor_expanded(
    n_wells_per_metre: float, r_e_hh_nm: float
) -> dict[str, float]:
    """The pm/V prefactor with every factor named separately.

    Returns the same number ``absolute_prefactor`` returns, plus the pieces.
    """

    r_m = float(r_e_hh_nm) * 1.0e-9
    physics_si = (float(n_wells_per_metre) * ELEMENTARY_CHARGE_C ** 3 * r_m ** 2
                  / (6.0 * VACUUM_PERMITTIVITY_F_PER_M))
    nm_to_m_for_z = 1.0e-9
    per_nm2_to_per_m2 = 1.0e18
    eV2_to_J2 = 1.0 / (ELEMENTARY_CHARGE_C ** 2)
    unit_conversion = nm_to_m_for_z * per_nm2_to_per_m2 * eV2_to_J2
    m_per_V_to_pm_per_V = 1.0e12
    return {
        "N_z_per_m": float(n_wells_per_metre),
        "r_e_hh_m": r_m,
        "physics_si_part": physics_si,
        "z_nm_to_m": nm_to_m_for_z,
        "k_weight_per_nm2_to_per_m2": per_nm2_to_per_m2,
        "eV_squared_to_J_squared": eV2_to_J2,
        "unit_conversion": unit_conversion,
        "m_per_V_to_pm_per_V": m_per_V_to_pm_per_V,
        "prefactor_pm_per_V": physics_si * unit_conversion * m_per_V_to_pm_per_V,
    }


# =============================================================================
# 15. WAVELENGTH GRID AND EXTRACTION AT 1550 nm
# =============================================================================
# ACTUAL PRODUCTION FUNCTION
#
# File:     nextnano/demos/20_.../s06_chi2.py
# Function: photon_energy_eV (line 157), wavelength_grid (line 604),
#           Chi2Spectrum.at_wavelength (line 573), Chi2Spectrum.peak (line 589)
# Called by: s07_analysis._fill_chi2_columns (s07_analysis.py:148-149)
# Performed by: Python
#
# Mathematics
# -----------
#     E_photon[eV] = hc/lambda = 1239.841984 / lambda[nm]
#     grid         = linspace(1400, 1800, 401)   ->  exactly 1.0 nm spacing
#     |chi2|(1550) = np.interp(1550, grid, |chi2|)
#
# HOW THE 1550 nm NUMBER IS ACTUALLY SELECTED: linear interpolation on the
# wavelength grid (``at_wavelength``, s06_chi2.py:586). Because the focused
# grid is 1400..1800 in 401 points, 1550.0 is EXACTLY a grid node, so the
# interpolation returns that node's value unchanged and no interpolation error
# is incurred for this target. Changing ``focused_wavelength_points`` could
# change that; the interpolation is what makes the extraction safe if it does.
#
# At 1550 nm:  E = 0.7998980541935484 eV,  2E = 1.5997961083870968 eV.
# Compare against case 04's transition energies (Section 10): 2E sits between
# dE_12 = 1.5284 eV and dE_21 = 1.6132 eV, i.e. the SHG two-photon resonance is
# in among the transitions, which is why |chi2| is large near 1550 nm and peaks
# at 1502 nm.

photon_energy_eV = chi2mod.photon_energy_eV
wavelength_nm_from_energy = chi2mod.wavelength_nm
wavelength_grid = chi2mod.wavelength_grid


# EDUCATIONAL REPRODUCTION OF THE EQUATION
# Production implementation: nextnano/demos/20_.../s06_chi2.py:157
def photon_energy_from_wavelength(wavelength_nm: float) -> float:
    r"""``E = hc/lambda`` with hc in eV nm.

    Simple interpretation
    ---------------------
    Light of a given colour carries a fixed packet of energy. Longer wavelength
    = lower energy. 1550 nm telecom light is 0.7999 eV per photon; two of them
    is 1.5998 eV, which is what has to line up with a transition for
    second-harmonic generation to be resonant.
    """

    return HC_EV_NM / float(wavelength_nm)


# =============================================================================
# 16. WHERE DO I CHANGE THE MATHS? - the index
# =============================================================================

#: (what you want to change) -> (equation, function, file, downstream effect)
MODIFICATION_INDEX: tuple[dict[str, str], ...] = (
    {
        "want_to_change": "the grading SHAPE f(u) (linear -> something else)",
        "equation": "x_Al = x_L + (x_R - x_L) f(u)",
        "function": "profile_fraction",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s02_grading.py:162",
        "downstream": "x_Al(z) -> deck -> band edges -> E_n, psi_n -> O, z^e, z^hh "
                      "-> chi2. Requires a licensed re-solve to see any effect.",
    },
    {
        "want_to_change": "what the grading WIDTH W means (full width vs 10-90)",
        "equation": "u = clip((z - (z_i - W/2))/W, 0, 1)",
        "function": "evaluate_composition (the lo/hi window at lines 243-247)",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s02_grading.py:211",
        "downstream": "same chain as above; also changes plateau_lengths_nm and the "
                      "overlap gate in s02_grading.overlaps.",
    },
    {
        "want_to_change": "layer thicknesses / interface positions",
        "equation": "cumulative sum of layer widths",
        "function": "geometry / interface_positions",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s02_grading.py:103",
        "downstream": "everything. Also changes the quantum region and the deck grid.",
    },
    {
        "want_to_change": "how many states enter the triple sum",
        "equation": "m, n, l ranges",
        "function": "CaseStates.truncated, via settings.max_states_per_band",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:490 "
                "(value in demo20_config.yaml:88)",
        "downstream": "more terms in chi2; needs matrix elements for the extra states, "
                      "which the master-table path does not carry (s05_extract.py:129).",
    },
    {
        "want_to_change": "the broadening Gamma",
        "equation": "dE - nE + i Gamma",
        "function": "Chi2Settings.broadening_eV",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:232 "
                "(value in demo20_config.yaml:96)",
        "downstream": "peak height and linewidth of chi2(lambda); no effect on E_n, psi_n.",
    },
    {
        "want_to_change": "k-space resolution or k_max",
        "equation": "k = linspace(0, k_max, N); k_max = frac * pi/a",
        "function": "k_grid / Chi2Settings.k_max_per_nm",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:346, :223 "
                "(values in demo20_config.yaml:134-137)",
        "downstream": "chi2 magnitude; check with k_convergence_report (s06_chi2.py:745).",
    },
    {
        "want_to_change": "the k-space NORMALIZATION convention",
        "equation": "w_i = g_s k_i dk_i/(2pi)   vs   w_i = g_s 2pi k_i dk_i",
        "function": "k_grid (the if/else at lines 380-387)",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:346",
        "downstream": "chi2 magnitude by exactly (2pi)^2; peak position, lineshape and "
                      "case ranking are invariant (gated in s08_qc.py:259).",
    },
    {
        "want_to_change": "the susceptibility FORMULA itself",
        "equation": "Eq. (3) with Eq. (5) and Eq. (6)",
        "function": "chi2_spectrum (the loop at lines 641-661)",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:612",
        "downstream": "everything downstream of the matrix elements. Breaks exact "
                      "reproduction of Demo 19 (tests/test_demo20.py:354).",
    },
    {
        "want_to_change": "the numerical integration rule for matrix elements",
        "equation": "int psi_a psi_b dz  ~=  trapezoid",
        "function": "overlap_matrix / position_matrix",
        "file": "nextnano/demos/_shared/chi2.py:204, :220",
        "downstream": "O and z^ matrices for ALL demos that share this module. "
                      "Licensed re-parse required; the master-table path only reads "
                      "the numbers these already produced.",
    },
    {
        "want_to_change": "envelope normalization",
        "equation": "psi <- psi / sqrt(int psi^2 dz)",
        "function": "BandStates.__post_init__",
        "file": "nextnano/demos/_shared/chi2.py:155-162",
        "downstream": "all matrix elements, hence chi2. Shared across demos.",
    },
    {
        "want_to_change": "the in-plane dispersion of the transition energy",
        "equation": "dE_nm(k) = dE_nm(0) + hbar^2 k^2/(2 mu)",
        "function": "transition_energies_eV",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:537",
        "downstream": "the k dependence of both denominators; chi2 lineshape and "
                      "magnitude.",
    },
    {
        "want_to_change": "the prefactor, N_z, or r_e,hh",
        "equation": "N_z e^3 r^2 / (6 eps0), plus unit conversions",
        "function": "absolute_prefactor / n_z_for",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:514, :289 "
                "(values in demo20_config.yaml:97-100)",
        "downstream": "chi2 magnitude only, linearly (r enters squared). Lineshape and "
                      "ranking unchanged.",
    },
    {
        "want_to_change": "the wavelength grid",
        "equation": "linspace(start, end, points)",
        "function": "wavelength_grid",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:604 "
                "(values in demo20_config.yaml:101-104)",
        "downstream": "resolution of the spectrum and whether 1550 nm lands on a node; "
                      "at_wavelength interpolates either way.",
    },
    {
        "want_to_change": "how the reported number is picked at 1550 nm",
        "equation": "np.interp(target, grid, |chi2|)",
        "function": "Chi2Spectrum.at_wavelength",
        "file": "nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py:573",
        "downstream": "the single reported value only.",
    },
)


# =============================================================================
# 17. FUNCTION-TO-EQUATION REFERENCE TABLE
# =============================================================================

#: One row per stage of the pipeline. ``performed_by`` is the point of the table.
DATA_FLOW: tuple[dict[str, str], ...] = (
    {"step": "1", "input": "layer thicknesses (7.1/1.8/2.9/18.2 nm)",
     "function": "s02_grading.geometry / interface_positions",
     "operation": "cumulative sum", "output": "I1..I4 = 9.1/16.2/18.0/20.9 nm",
     "units": "nm", "performed_by": "Python"},
    {"step": "2", "input": "case 04: profile='linear', widths=(1,1,1,1) nm",
     "function": "s02_grading.grade_intervals",
     "operation": "[z_i - W/2, z_i + W/2]",
     "output": "4 grade windows, e.g. I1 -> [8.6, 9.6] nm",
     "units": "nm", "performed_by": "Python"},
    {"step": "3", "input": "(z_i, W, x_L, x_R) per interface",
     "function": "s02_grading.profile_fraction + evaluate_composition",
     "operation": "x_L + (x_R - x_L) f(u), f(u) = u",
     "output": "x_Al(z) on 601 deck points", "units": "dimensionless",
     "performed_by": "Python"},
    {"step": "4", "input": "x_Al(z), geometry, state counts",
     "function": "s03_inputs.render_deck",
     "operation": "template substitution -> ternary_linear regions",
     "output": "case.in (nextnano++ deck)", "units": "text",
     "performed_by": "Python"},
    {"step": "5", "input": "case.in + database.nnp",
     "function": "nextnano++ (via s04_solver.solve_case)",
     "operation": "alloy -> band parameters -> V(z), m*(z)",
     "output": "confinement potential", "units": "eV",
     "performed_by": "nextnano++"},
    {"step": "6", "input": "V(z), m*(z), Dirichlet box [7.1, 22.9] nm",
     "function": "nextnano++ eigensolver",
     "operation": "H psi = E psi (BenDaniel-Duke, single band)",
     "output": "E_n (6 per band), psi_n(z)", "units": "eV, arb.",
     "performed_by": "nextnano++"},
    {"step": "7", "input": "psi_n(z) as written by nextnano++",
     "function": "_shared/chi2.BandStates.__post_init__",
     "operation": "psi <- psi / sqrt(int psi^2 dz)",
     "output": "normalized envelopes", "units": "nm^-1/2",
     "performed_by": "Python"},
    {"step": "8", "input": "normalized psi_e, psi_hh on one shared grid",
     "function": "_shared/chi2.overlap_matrix",
     "operation": "trapezoid(psi_e,n psi_hh,m, z)",
     "output": "O (2x2)", "units": "dimensionless", "performed_by": "Python"},
    {"step": "9", "input": "normalized psi within one band",
     "function": "_shared/chi2.position_matrix",
     "operation": "trapezoid(psi_i z psi_j, z)",
     "output": "z^e (2x2), z^hh (2x2)", "units": "nm", "performed_by": "Python"},
    {"step": "10", "input": "master results CSV row (case 04)",
     "function": "s05_extract.from_master_table",
     "operation": "column read, no recomputation",
     "output": "CaseStates(E, H, O, z^e, z^hh)", "units": "eV, -, nm",
     "performed_by": "Python"},
    {"step": "11", "input": "E_e, E_hh, k grid, mu",
     "function": "s06_chi2.transition_energies_eV",
     "operation": "dE_nm(k) = (E_e,n - E_hh,m) + hbar^2 k^2/(2 mu)",
     "output": "(2, 2, 96) array", "units": "eV", "performed_by": "Python"},
    {"step": "12", "input": "k_max, 96 points, g_s = 2",
     "function": "s06_chi2.k_grid",
     "operation": "w_i = g_s k_i dk_i/(2 pi)",
     "output": "k (96,), weights (96,)", "units": "nm^-1, nm^-2",
     "performed_by": "Python"},
    {"step": "13", "input": "lambda grid 1400-1800 nm",
     "function": "s06_chi2.photon_energy_eV",
     "operation": "E = hc/lambda", "output": "E (401,)", "units": "eV",
     "performed_by": "Python"},
    {"step": "14", "input": "O, z^e, z^hh, dE(k), E, Gamma",
     "function": "s06_chi2.chi2_spectrum (triple loop)",
     "operation": "sum_{m,n,l} [A' - B']",
     "output": "S(k, E) (96,) complex per wavelength", "units": "nm/eV^2",
     "performed_by": "Python"},
    {"step": "15", "input": "S(k, E), weights",
     "function": "np.dot inside chi2_spectrum",
     "operation": "sum_i w_i S(k_i, E)", "output": "complex per wavelength",
     "units": "nm eV^-2 nm^-2", "performed_by": "Python"},
    {"step": "16", "input": "N_z, e, r_e,hh, eps0 + unit factors",
     "function": "s06_chi2.absolute_prefactor",
     "operation": "N_z e^3 r^2/(6 eps0) * 1e-9 * 1e18/e^2 * 1e12",
     "output": "56.69816882497043", "units": "pm/V per summand unit",
     "performed_by": "Python"},
    {"step": "17", "input": "prefactor * k-sum",
     "function": "Chi2Spectrum construction",
     "operation": "multiply", "output": "chi2(lambda), 401 complex values",
     "units": "pm/V", "performed_by": "Python"},
    {"step": "18", "input": "chi2(lambda), target 1550 nm",
     "function": "Chi2Spectrum.at_wavelength",
     "operation": "np.interp on |chi2|", "output": "one number",
     "units": "pm/V", "performed_by": "Python"},
)


# =============================================================================
# 18. SELF-CHECK - every EDUCATIONAL REPRODUCTION vs its PRODUCTION original
# =============================================================================


def self_check(cfg: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Assert that each reproduction above agrees with the production function.

    Returns one record per check. Raises AssertionError on any disagreement:
    if a reproduction and production ever differ, the reproduction is the one
    that is wrong, and this file must be corrected rather than production.
    """

    cfg = dict(cfg or config20.load())
    case = cases.by_id()[WORKED_CASE_ID]
    settings = settings_from_config(cfg, convention=CONVENTION_DEMO19)
    records: list[dict[str, Any]] = []

    def record(name: str, produced: Any, reproduced: Any,
               rtol: float = 0.0, note: str = "bit-identical") -> None:
        """Compare a reproduction against production.

        ``rtol`` is nonzero only where the two expressions differ purely in
        floating-point ASSOCIATION order (production multiplies its factors in
        a different grouping), which costs a few ULP and nothing else. It is
        never loosened to absorb a real difference: 1e-15 is ~4 ULP of a double.
        """

        a = np.asarray(produced, dtype=float)
        b = np.asarray(reproduced, dtype=float)
        deviation = float(np.max(np.abs(a - b))) if a.size else 0.0
        scale = float(np.max(np.abs(a))) if a.size else 0.0
        allowed = rtol * scale
        assert deviation <= allowed, (
            f"{name}: reproduction differs by {deviation:g} "
            f"(allowed {allowed:g})")
        records.append({"check": name, "max_abs_difference": deviation,
                        "relative_tolerance": rtol, "allowed_absolute": allowed,
                        "note": note, "passed": True})

    # 1. interface positions
    production_pos = interface_positions(cfg)
    reproduced_pos = interface_positions_from_thicknesses(
        float(cfg["geometry"]["thick_well_nm"]),
        float(cfg["geometry"]["tunnel_barrier_nm"]),
        float(cfg["geometry"]["thin_well_nm"]),
        float(cfg["geometry"]["period_barrier_nm"]),
    )
    record("interface_positions",
           [production_pos[k] for k in cases.INTERFACE_IDS],
           [reproduced_pos[k] for k in cases.INTERFACE_IDS])

    # 2. linear grading over one interface window
    z_probe = np.linspace(8.6, 9.6, 21)
    record("linear_profile_at_I1",
           evaluate_composition(cfg, case, z_probe),
           linear_profile(z_probe, production_pos["I1"], 1.0, 0.55, 0.0))

    # 3. k weights
    k_prod, w_prod = k_grid(settings)
    k_repro, w_repro = k_weights_demo19_convention(
        settings.k_max_per_nm, settings.k_parallel_points, settings.spin_degeneracy)
    record("k_grid_nodes", k_prod, k_repro)
    record("k_grid_weights", w_prod, w_repro)

    # 4. prefactor
    record("absolute_prefactor",
           [absolute_prefactor(settings)],
           [absolute_prefactor_expanded(settings.n_wells_per_metre,
                                        settings.r_e_hh_nm)["prefactor_pm_per_V"]],
           rtol=1.0e-15,
           note="same factors, different multiplication grouping (~1 ULP)")

    # 5. photon energy
    record("photon_energy_1550nm",
           [float(photon_energy_eV(1550.0))],
           [photon_energy_from_wavelength(1550.0)])

    # 6. transition energy at a k point
    extracted = from_master_table(config20.master_table_path(cfg))
    states = extracted[WORKED_CASE_ID].states.truncated(settings.max_states_per_band)
    index = 40
    production_dE = transition_energies_eV(states, k_prod, settings)[0, 0, index]
    reproduced_dE = transition_energy_at_k(
        float(states.electron_energies_eV[0]), float(states.hole_energies_eV[0]),
        float(k_prod[index]), settings.reduced_mass_kg())
    record("transition_energy_dE11_at_k40", [production_dE], [reproduced_dE])

    # 7. the unrolled triple sum vs the production accumulation, at one k point
    energy = float(photon_energy_eV(1550.0))
    terms = chi2_summand_terms(states, index, energy, settings)
    unrolled = sum(term["contribution"] for term in terms)
    two_photon_all = (transition_energies_eV(states, k_prod, settings)[:, :, index]
                      - 2.0 * energy + 1j * settings.broadening_eV)
    one_photon_all = (transition_energies_eV(states, k_prod, settings)[:, :, index]
                      - 1.0 * energy + 1j * settings.broadening_eV)
    overlap = np.asarray(states.overlap_electron_hole, float)
    z_e = np.asarray(states.position_matrix_electron_nm, float)
    z_h = np.asarray(states.position_matrix_hole_nm, float)
    direct = 0j
    for m in range(states.n_hole):
        for n in range(states.n_electron):
            for l in range(states.n_electron):
                num = overlap[n, m] * z_e[n, l] * overlap[l, m]
                if num:
                    direct += num / (two_photon_all[n, m] * one_photon_all[l, m])
            for l in range(states.n_hole):
                num = overlap[n, m] * z_h[m, l] * overlap[n, l]
                if num:
                    direct -= num / (two_photon_all[n, m] * one_photon_all[n, l])
    record("triple_sum_unrolled_vs_direct",
           [direct.real, direct.imag], [unrolled.real, unrolled.imag],
           rtol=1.0e-15,
           note="same 16 terms, summed in a list instead of accumulated")

    return records


# =============================================================================
# 19. GUIDED TOUR (``python demo20_math_physics_reference.py``)
# =============================================================================


def _tour() -> int:
    cfg = config20.load()
    case = cases.by_id()[WORKED_CASE_ID]
    settings = settings_from_config(cfg, convention=CONVENTION_DEMO19)

    print("=" * 74)
    print("DEMO 21 - MATH/PHYSICS REFERENCE FOR DEMO 20")
    print(f"worked case: {WORKED_CASE_ID} '{case.case_name}' "
          f"(profile={case.profile}, widths={case.widths_nm} nm)")
    print("=" * 74)

    print("\n[1] GEOMETRY (Python)")
    for key, value in interface_positions(cfg).items():
        low, high = interface_directions(cfg)[key]
        print(f"    {key} = {value:6.2f} nm   x_Al {low:.2f} -> {high:.2f}")

    print("\n[2-3] GRADING -> x_Al(z) (Python)")
    breakdown = composition_profile_with_breakdown(cfg, case)
    for key, span in breakdown["grade_intervals_nm"].items():
        print(f"    {key} grade window: {span}")
    for z in (8.60, 8.85, 9.10, 9.35, 9.60):
        print(f"    x_Al({z:5.2f} nm) = "
              f"{float(evaluate_composition(cfg, case, [z])[0]):.6f}")

    print("\n[5] NEXTNANO++ INPUT (Python renders / nextnano++ solves)")
    summary = nextnano_input_summary(cfg, case)
    for key in ("render_method", "domain_nm", "quantum_region_nm",
                "electron_states_requested", "hole_states_requested",
                "boundary_condition", "self_consistent_poisson"):
        print(f"    {key:28s} {summary[key]}")

    print("\n[6] STATES (nextnano++, read back from the licensed results table)")
    states = from_master_table(config20.master_table_path(cfg))[
        WORKED_CASE_ID].states.truncated(settings.max_states_per_band)
    print(f"    E_e1  = {states.electron_energies_eV[0]:.12f} eV")
    print(f"    E_e2  = {states.electron_energies_eV[1]:.12f} eV")
    print(f"    E_hh1 = {states.hole_energies_eV[0]:.12f} eV")
    print(f"    E_hh2 = {states.hole_energies_eV[1]:.12f} eV")

    print("\n[8-9] MATRIX ELEMENTS (Python, from nextnano++ envelopes)")
    print(f"    O    = {np.asarray(states.overlap_electron_hole).tolist()}")
    print(f"    z^e  = {np.asarray(states.position_matrix_electron_nm).tolist()} nm")
    print(f"    z^hh = {np.asarray(states.position_matrix_hole_nm).tolist()} nm")
    print(f"    r_e,hh (DFT, external) = {R_E_HH_NM_DFT} nm")

    print("\n[11] k MEASURE (Python)")
    k, weights = k_grid(settings)
    print(f"    k_max = {settings.k_max_per_nm:.12f} nm^-1, N = {k.size}")
    print(f"    sum(w) = {float(np.sum(weights)):.12e} nm^-2 "
          f"(closed form {analytic_disc_measure(settings):.12e})")

    print("\n[14] PREFACTOR (Python)")
    for key, value in absolute_prefactor_expanded(
            settings.n_wells_per_metre, settings.r_e_hh_nm).items():
        print(f"    {key:28s} {value!r}")

    print("\n[15] RESULT (Python)")
    grid = wavelength_grid(cfg)
    raw = chi2_spectrum(states, grid, settings)
    scaled = chi2_spectrum(states, grid, settings.with_convention(CONVENTION_SCALED))
    print(f"    |chi2|(1550 nm) raw    = {raw.at_wavelength(1550.0):.12f} pm/V")
    print(f"    |chi2|(1550 nm) scaled = {scaled.at_wavelength(1550.0):.12f} pm/V")
    print(f"    peak                   = {raw.peak()}")

    print("\n[18] SELF-CHECK of every educational reproduction")
    for row in self_check(cfg):
        print(f"    {row['check']:36s} max|diff| = {row['max_abs_difference']:.3e}  OK")

    print("\nAll educational reproductions agree with production to machine "
          "precision.")
    print("For the full numbered trace run:  python trace_demo20_linear_1nm.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(_tour())

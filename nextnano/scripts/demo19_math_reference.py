"""Demo 19 - every math step in one file, in execution order.

WHAT THIS IS
============
A standalone, runnable re-implementation of ALL the mathematics behind Demo 19,
consolidated from six repository modules into one file so the math can be read
top-to-bottom without following imports.

Every function carries:

    STEP    <label>          where it sits in the pipeline
    MATH    <formula>        the equation implemented
    SOURCE  <file:line>      where the PRODUCTION code lives

This file is a READING AID and a DEBUGGING TOOL. It is NOT in the production
path. Nothing here is imported by Demo 19; edits here change nothing about a
licensed run. When this file and the SOURCE disagree, the SOURCE is correct.

It imports nothing from the repository -- only numpy and the standard library --
so it can be run anywhere, with no nextnano licence and no solver output.

HOW TO RUN
==========
    python nextnano/scripts/demo19_math_reference.py

It self-tests against known-good values from the licensed run and prints a
PASS/FAIL line for each. All checks currently pass.

PIPELINE MAP
============
    PART A   composition            build x_Al(z)              before the solver
    PART B   material model         x_Al -> band edges, mass   inside nextnano++
    PART C   quantum                Schrodinger -> E, psi      inside nextnano++
    PART D   matrix elements        psi -> O, z                after the solver
    PART E   susceptibility         O, z, E -> chi2            after the solver
    PART F   reduction and checks   chi2 -> reported numbers   after the solver

PARTS B and C are what nextnano++ does internally. They are reproduced here
because they were verified to match the solver's own output, which means the
band edges and eigenvalues can be checked WITHOUT a licence. PARTS A, D, E, F
mirror actual repository Python.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

# ---------------------------------------------------------------------------
# PHYSICAL CONSTANTS
# SOURCE: nextnano/demos/_shared/chi2.py:81-87   (CODATA 2018)
# ---------------------------------------------------------------------------
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
HC_EV_NM = 1239.841984          # photon energy [eV] = HC_EV_NM / wavelength [nm]

# ---------------------------------------------------------------------------
# FROZEN STRUCTURE
# SOURCE: nextnano/demos/19_quantum_well_interface_grading_showcase/cases19.py:16-24
# ---------------------------------------------------------------------------
THICK_WELL_NM = 7.1
TUNNEL_BARRIER_NM = 1.8
THIN_WELL_NM = 2.9
PERIOD_BARRIER_NM = 18.2        # total outer barrier; half on each side
AL_FRACTION = 0.55              # barrier composition
ACTIVE_MESH_NM = 0.05
OUTER_MESH_NM = 0.5
TEMPERATURE_K = 300.0
QUANTUM_PADDING_NM = 2.0        # SOURCE: 14_absolute.../demo.yaml, geometry block

# Optical conventions, all inherited unchanged.
# SOURCE: nextnano/demos/14_absolute_chi2_graded_acqw_bo/demo.yaml, chi2 + k_parallel
MAX_STATES_PER_BAND = 2
BROADENING_EV = 0.005           # 5.0 meV
R_E_HH_NM = 0.751               # position matrix element, NOT a dipole
REFERENCE_PERIOD_NM = 30.0
LATTICE_CONSTANT_NM = 0.565325
K_FRACTION_OF_BZ = 0.10
K_POINTS = 96
SPIN_DEGENERACY = 2
M_ELECTRON_INPLANE = 0.067      # in-plane, for the k_parallel dispersion only
M_HH_INPLANE = 0.112            # in-plane; NOT the 0.51 growth-direction mass
FOCUSED_NM = (1400.0, 1800.0)
FOCUSED_POINTS = 401


# ===========================================================================
# PART A -- COMPOSITION.  Builds x_Al(z) before the solver ever runs.
# ===========================================================================

def profile_fraction(u: np.ndarray, shape: str) -> np.ndarray:
    """STEP A1 -- the five interface shape functions.

    MATH    normalised ramp f(u) with f(0) = 0 and f(1) = 1 EXACTLY

              linear    f = u
              fermi     f = (S(k(u-1/2)) - lo) / (hi - lo),  S = logistic, k = 10
                            lo = 1/(1+e^(k/2)),  hi = 1/(1+e^(-k/2))
              erf       f = (erf(s(u-1/2)) - lo) / (hi - lo),  s = 3
                            lo = erf(-s/2),  hi = erf(s/2)
              cosine    f = 1/2 - 1/2 cos(pi u)
              abrupt    f = step at u = 1/2

            fermi and erf have INFINITE support. They are truncated to u in [0,1]
            and then endpoint-normalised, so x_Al reaches 0 and 0.55 exactly
            rather than asymptotically. The price is a slope discontinuity at
            the two interval edges.

    SOURCE  nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/grading12.py:25
            The steepness k = 10.0 and span s = 3.0 are pinned at
            nextnano/demos/19_.../demo19.py:118 (_profile_shape), not in any YAML.
    """
    x = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    key = str(shape).lower()

    if key in {"abrupt", "step"}:
        return np.where(x < 0.5, 0.0, 1.0)

    if key == "linear":
        return x

    if key in {"fermi", "sigmoid", "logistic"}:
        k = 10.0
        raw = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
        lo = 1.0 / (1.0 + math.exp(k / 2.0))
        hi = 1.0 / (1.0 + math.exp(-k / 2.0))
        return (raw - lo) / (hi - lo)

    if key == "erf":
        s = 3.0
        raw = np.vectorize(math.erf)(s * (x - 0.5))
        lo, hi = math.erf(-s / 2.0), math.erf(s / 2.0)
        return (raw - lo) / (hi - lo)

    if key == "cosine":
        return 0.5 - 0.5 * np.cos(np.pi * x)

    raise ValueError(f"unsupported grading profile {shape!r}")


def interface_positions() -> dict[str, float]:
    """STEP A2 -- the four nominal interfaces.

    MATH    cumulative layer sums from the left edge of the domain

              I1 = outer
              I2 = I1 + thick_well
              I3 = I2 + tunnel_barrier
              I4 = I3 + thin_well

            with outer = PERIOD_BARRIER_NM / 2 on each side.

    SOURCE  nextnano/demos/19_.../demo19.py:88 (geometry) and :108
    """
    outer = PERIOD_BARRIER_NM / 2.0
    i1 = outer
    i2 = i1 + THICK_WELL_NM
    i3 = i2 + TUNNEL_BARRIER_NM
    i4 = i3 + THIN_WELL_NM
    return {"I1": i1, "I2": i2, "I3": i3, "I4": i4}


def domain_nm() -> tuple[float, float]:
    """STEP A2b -- total simulation length.  MATH: 0 to I4 + outer = 30.0 nm."""
    return 0.0, interface_positions()["I4"] + PERIOD_BARRIER_NM / 2.0


# Growth direction at each interface: (x_Al before, x_Al after).
INTERFACE_DIRECTIONS = {
    "I1": (AL_FRACTION, 0.0),   # barrier -> well, Al falls
    "I2": (0.0, AL_FRACTION),   # well -> barrier, Al rises
    "I3": (AL_FRACTION, 0.0),   # barrier -> well, Al falls
    "I4": (0.0, AL_FRACTION),   # well -> barrier, Al rises
}


def evaluate_composition(z_nm, profile: str, widths_nm: dict[str, float]) -> np.ndarray:
    """STEP A3 -- the whole-device x_Al(z).

    MATH    baseline:  x_Al = 0.55 in barriers, 0.00 inside [I1,I2] and [I3,I4]

            then for each interface i with width w > 0, on [z_i - w/2, z_i + w/2]:

              u       = clip( (z - (z_i - w/2)) / w , 0 , 1 )   <-- ONLY place w enters
              x_Al(z) = x_start + (x_end - x_start) * f(u)

            The width is the FULL start-to-end transition width, centred on the
            nominal interface. Not a half width. Not a 10-90% width.

    SOURCE  nextnano/demos/19_.../demo19.py:126 (evaluate_composition)
    """
    z = np.asarray(z_nm, dtype=float)
    pos = interface_positions()

    # --- baseline: barrier everywhere, wells carved out -------------------
    x_al = np.full_like(z, AL_FRACTION)
    x_al[(z >= pos["I1"]) & (z <= pos["I2"])] = 0.0
    x_al[(z >= pos["I3"]) & (z <= pos["I4"])] = 0.0
    if profile == "abrupt":
        return x_al

    # --- one ramp per graded interface ------------------------------------
    for name in ("I1", "I2", "I3", "I4"):
        w = float(widths_nm.get(name, 0.0))
        if w <= 0:
            continue
        centre = pos[name]
        lo, hi = centre - w / 2.0, centre + w / 2.0
        mask = (z >= lo) & (z <= hi)
        if not np.any(mask):
            continue
        u = np.clip((z[mask] - lo) / w, 0.0, 1.0)
        start_x, end_x = INTERFACE_DIRECTIONS[name]
        x_al[mask] = start_x + (end_x - start_x) * profile_fraction(u, profile)
    return x_al


def composition_table(profile: str, widths_nm: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """STEP A4/A5 -- the sampled table handed to nextnano++ as al_profile.dat.

    MATH    uniform sampling at the ACTIVE mesh spacing (0.05 nm) across the
            whole 0-30 nm domain, plus forced points at every z_i and
            z_i +/- w/2. For all Demo 19 widths (multiples of 0.1 nm) those
            forced points already land on the 0.05 nm lattice, so the table
            comes out uniform: 601 rows.

            nextnano++ then interpolates this table LINEARLY between rows.
            That piecewise-linear reconstruction is the only approximation
            introduced by the import path.

    SOURCE  nextnano/demos/19_.../demo19.py:162  (profile_mesh)
            nextnano/demos/14_.../grading14.py:722 (import_datafile, the writer)
    """
    lo, hi = domain_nm()
    points = list(np.arange(lo, hi + 0.5 * ACTIVE_MESH_NM, ACTIVE_MESH_NM))
    pos = interface_positions()
    for name in ("I1", "I2", "I3", "I4"):
        points.append(pos[name])
        w = float(widths_nm.get(name, 0.0))
        if w > 0:
            points += [pos[name] - w / 2, pos[name] + w / 2]
    z = np.asarray(sorted({round(float(v), 12) for v in points}), dtype=float)
    return z, evaluate_composition(z, profile, widths_nm)


def rendering_error(profile: str, widths_nm: dict[str, float]) -> float:
    """STEP A5b -- how much the sampled table differs from the analytic profile.

    MATH    err = max | interp(table)(z_fine) - x_Al_analytic(z_fine) |
            on a grid 20x finer than the table.  Gate: 5.0e-3 in Al fraction.

    SOURCE  nextnano/demos/19_.../demo19.py:175 (build_profile), diagnostics block
    """
    z_tab, x_tab = composition_table(profile, widths_nm)
    lo, hi = domain_nm()
    z_fine = np.arange(lo, hi + 1e-12, ACTIVE_MESH_NM / 20.0)
    exact = evaluate_composition(z_fine, profile, widths_nm)
    return float(np.max(np.abs(np.interp(z_fine, z_tab, x_tab) - exact)))


# ===========================================================================
# PART B -- MATERIAL MODEL.  What nextnano++ does with x_Al(z) internally.
#
# NOT repository Python -- reproduced here from the nextnano++ material
# database and VERIFIED to match the solver's own printed band edges to 13
# significant figures. That verification is what lets you check band lineups
# without a licence.
# ===========================================================================

# SOURCE: nextnano++ 2026_07_03 database, binary_zb entries for GaAs and AlAs.
GAAS = dict(eg0=1.519, alpha=0.5405e-3, beta=204.0, vbo=1.346, dso=0.341,
            m_gamma=0.067, m_hh=0.51)
ALAS = dict(eg0=3.099, alpha=0.885e-3, beta=530.0, vbo=0.857, dso=0.28,
            m_gamma=0.15, m_hh=0.50)


def varshni(eg0: float, alpha: float, beta: float, T: float = TEMPERATURE_K) -> float:
    """STEP B1 -- temperature-dependent band gap of ONE binary.

    MATH    Eg(T) = Eg(0) - alpha * T^2 / (T + beta)
    """
    return eg0 - alpha * T * T / (T + beta)


def alloy_gamma_gap_eV(x: float, T: float = TEMPERATURE_K) -> float:
    """STEP B2 -- Al(x)Ga(1-x)As Gamma gap.

    MATH    C(x)  = -0.127 + 1.310 x                    composition-dependent bowing
            Eg(x) = x Eg_AlAs(T) + (1-x) Eg_GaAs(T) - x(1-x) C(x)

    ORDER MATTERS: Varshni is applied to each BINARY first, and the 300 K values
    are then interpolated. Verified -- this reproduces the solver's 2.1448956 eV
    at x = 0.55 exactly; interpolating at 0 K first is off by 0.057 meV.
    """
    eg_gaas = varshni(GAAS["eg0"], GAAS["alpha"], GAAS["beta"], T)
    eg_alas = varshni(ALAS["eg0"], ALAS["alpha"], ALAS["beta"], T)
    bowing = -0.127 + 1.310 * x
    return x * eg_alas + (1.0 - x) * eg_gaas - x * (1.0 - x) * bowing


def band_edges_eV(x: float, T: float = TEMPERATURE_K) -> tuple[float, float]:
    """STEP B3 -- absolute conduction and heavy-hole band edges.

    MATH    vbo(x)  = x vbo_AlAs + (1-x) vbo_GaAs          linear, no bowing
            dso(x)  = x dso_AlAs + (1-x) dso_GaAs          linear, no bowing
            E_v(HH) = vbo(x) + dso(x)/3
            E_c(G)  = E_v(HH) + Eg_Gamma(x, T)

    Returns (E_c, E_v) in eV on nextnano's absolute scale.

    At x = 0:    2.8821488095238 / 1.4596666666667   <- matches solver exactly
    At x = 0.55: 3.3244289271371 / 1.1795333333333   <- matches solver exactly

    The 61/39 conduction/valence offset split is an OUTPUT of these absolute
    valence-band offsets. There is no Q_c parameter anywhere.
    """
    vbo = x * ALAS["vbo"] + (1.0 - x) * GAAS["vbo"]
    dso = x * ALAS["dso"] + (1.0 - x) * GAAS["dso"]
    e_v = vbo + dso / 3.0
    return e_v + alloy_gamma_gap_eV(x, T), e_v


def effective_mass(x: float, band: str) -> float:
    """STEP B4 -- local effective mass, in units of m0.

    MATH    m(x) = x m_AlAs + (1-x) m_GaAs        LINEAR IN m, no bowing

            Gamma:  0.067 -> 0.11265 m0 at x = 0.55
            HH:     0.51  -> 0.50450 m0 at x = 0.55

    VERIFIED: linear-in-m reproduces the solver's E1/E2 to 0.06 meV, whereas
    harmonic (inverse-mass) interpolation misses by 2.1 and 7.7 meV.
    """
    key = "m_gamma" if band == "gamma" else "m_hh"
    return x * ALAS[key] + (1.0 - x) * GAAS[key]


# ===========================================================================
# PART C -- QUANTUM.  What nextnano++ solves.
#
# NOT repository Python. A BenDaniel-Duke discretisation of the same equation
# nextnano++ solves, included so eigenvalues can be regenerated without a
# licence. Reproduces the licensed E1/E2/HH1/HH2 to well under 0.1 meV.
# ===========================================================================

def solve_band(z_nm: np.ndarray, potential_eV: np.ndarray, mass_m0: np.ndarray,
               n_states: int = 6, electron: bool = True):
    """STEP C1 -- the one-band effective-mass Schrodinger equation.

    MATH    electrons:  [ -hbar^2/2 d/dz (1/m*(z) d/dz) + E_c(z) ] psi = E psi
            holes:      [ +hbar^2/2 d/dz (1/m*(z) d/dz) + E_v(z) ] psi = E psi

            Both on ONE electron energy scale, which is why the hole operator
            carries the opposite sign: confinement pushes hole levels DOWN, and
            an interband transition is then a plain subtraction E_e - E_hh.

            BenDaniel-Duke means the mass sits INSIDE the derivative, so psi and
            (1/m) dpsi/dz are the continuous quantities at an abrupt interface.
            Through a graded interface m*(z) varies smoothly and there is no
            interface condition at all.

            Discretised on the interior nodes with Dirichlet walls (psi = 0):

              H[i,i]   =  hbar^2/(2 h^2) (1/m_{i-1/2} + 1/m_{i+1/2}) + V_i
              H[i,i-1] = -hbar^2/(2 h^2) (1/m_{i-1/2})
              H[i,i+1] = -hbar^2/(2 h^2) (1/m_{i+1/2})

    MODEL LIMITS, all deliberate: one band (no k.p, no HH/LH mixing), strictly
    parabolic (nextnano++ 3.0.0 has no nonparabolicity option for one-band),
    no strain, no doping, no electric field, no space charge.

    SOURCE  This is the model configured at
            nextnano/demos/19_.../graded_acqw19.in.j2 (quantum block).
            nextnano++ performs the actual solve; the repository never does.
    """
    z = np.asarray(z_nm, dtype=float)
    h = float(z[1] - z[0])
    m_half = np.asarray(mass_m0, dtype=float)[:-1] * ELECTRON_MASS_KG   # cell centres
    sign = 1.0 if electron else -1.0

    n = z.size
    pref = (REDUCED_PLANCK_J_S ** 2) / (2.0 * (h * 1e-9) ** 2) / ELEMENTARY_CHARGE_C
    idx = np.arange(1, n - 1)
    H = np.zeros((idx.size, idx.size))
    for a, i in enumerate(idx):
        ml, mr = m_half[i - 1], m_half[i]
        H[a, a] = sign * pref * (1.0 / ml + 1.0 / mr) + potential_eV[i]
        if a > 0:
            H[a, a - 1] = -sign * pref / ml
        if a < idx.size - 1:
            H[a, a + 1] = -sign * pref / mr
    energies, vectors = np.linalg.eigh(H)

    if not electron:                       # holes descend on the electron scale
        energies, vectors = energies[::-1], vectors[:, ::-1]
    energies = energies[:n_states]
    psi = np.zeros((n, n_states))
    psi[1:-1, :] = vectors[:, :n_states]
    return z, energies, psi


def build_potential(z_nm: np.ndarray, x_al: np.ndarray):
    """STEP C0 -- turn x_Al(z) into the four spatial functions the solver needs.

    MATH    E_c(z), E_v(z), m_e(z), m_hh(z) evaluated pointwise from x_Al(z)
            using PART B. THIS is where grading becomes physics: a graded
            interface is a smooth ramp in all four, not a boundary condition.
    """
    ec = np.array([band_edges_eV(x)[0] for x in x_al])
    ev = np.array([band_edges_eV(x)[1] for x in x_al])
    me = np.array([effective_mass(x, "gamma") for x in x_al])
    mh = np.array([effective_mass(x, "hh") for x in x_al])
    return ec, ev, me, mh


# ===========================================================================
# PART D -- MATRIX ELEMENTS.  First step of the real post-solve Python.
# ===========================================================================

def normalise(z_nm: np.ndarray, psi: np.ndarray) -> np.ndarray:
    """STEP 1 -- normalise every envelope.

    MATH    psi_i <- psi_i / sqrt( integral psi_i^2 dz )      so integral = 1

    The integral is TRAPEZOIDAL ON A NON-UNIFORM GRID. The quantum region spans
    [7.1, 22.9] nm but the 0.05 nm uniform mesh only covers [9.1, 20.9]; outside
    that nextnano grades toward 0.5 nm. Any integral written as sum(y)*dz with a
    scalar dz is WRONG at the two ends.

    NOTE: this path does NOT apply a sign convention, so solver eigenvector signs
    pass straight through. That is why O12 flips sign between cases. |chi2| is
    unaffected -- each numerator is a product in which any single state's sign
    cancels.

    SOURCE  nextnano/demos/_shared/chi2.py:162 (inside BandStates.__post_init__)
            The OTHER normaliser, which does fix the sign, is at
            nextnano/demos/_shared/analysis.py:65 and is NOT on this path.
    """
    out = np.empty_like(psi, dtype=float)
    for i in range(psi.shape[1]):
        norm = float(np.trapezoid(psi[:, i] ** 2, z_nm))
        if not math.isfinite(norm) or norm <= 0:
            raise ValueError(f"state {i + 1} has zero norm")
        out[:, i] = psi[:, i] / math.sqrt(norm)
    return out


def truncate(energies: np.ndarray, psi: np.ndarray, n: int = MAX_STATES_PER_BAND):
    """STEP 2 -- keep only the first n states of each band.

    Six are requested from the solver; two per band enter the sum. Requesting
    more states from nextnano does NOT widen the sum -- only MAX_STATES_PER_BAND
    does. If fewer than n bound states exist the production code refuses rather
    than silently shrinking the sum.

    SOURCE  nextnano/demos/_shared/chi2.py:500-519
    """
    if energies.size < n or psi.shape[1] < n:
        raise ValueError(f"need {n} states per band, have {energies.size}")
    return energies[:n], psi[:, :n]


def gram(z_nm: np.ndarray, psi: np.ndarray) -> np.ndarray:
    """STEP 3a -- overlap of a band with itself.  MATH: G_ij = integral psi_i psi_j dz.

    SOURCE  nextnano/demos/_shared/chi2.py:171
    """
    n = psi.shape[1]
    return np.array([[float(np.trapezoid(psi[:, i] * psi[:, j], z_nm))
                      for j in range(n)] for i in range(n)])


def orthonormality_error(z_nm: np.ndarray, psi: np.ndarray) -> float:
    """STEP 3b -- max |G_ij - delta_ij|.  Gate: 1.0e-3.

    NOT housekeeping. STEP 4 produces DIAGONAL position elements, which are
    individually origin-dependent. That dependence cancels between the two terms
    of the susceptibility ONLY for an orthonormal basis. Fail this and chi2
    depends on where you put z = 0, which makes it meaningless.

    SOURCE  nextnano/demos/_shared/chi2.py:188, gate at :524-535
    """
    g = gram(z_nm, psi)
    return float(np.max(np.abs(g - np.eye(g.shape[0]))))


def overlap_matrix(z_nm: np.ndarray, psi_e: np.ndarray, psi_h: np.ndarray) -> np.ndarray:
    """STEP 4a -- interband envelope overlap.

    MATH    O[n,m] = integral psi_e,n(z) psi_hh,m(z) dz          dimensionless

    INDEXED [electron, hole] AND NOT SYMMETRIC. For the abrupt case
    O[0,1] = +0.0244 while O[1,0] = -0.0880. Transposing it is a silent bug that
    trips no assertion. This is the one asymmetric matrix in the calculation.

    SOURCE  nextnano/demos/_shared/chi2.py:204
    """
    return np.array([[float(np.trapezoid(psi_e[:, i] * psi_h[:, j], z_nm))
                      for j in range(psi_h.shape[1])] for i in range(psi_e.shape[1])])


def position_matrix(z_nm: np.ndarray, psi: np.ndarray) -> np.ndarray:
    """STEP 4b -- intra-band position matrix element.

    MATH    z[i,j] = integral psi_i(z) * z * psi_j(z) dz          nm

    MUST be symmetric. Diagonals are state centroids (12-19 nm here) and are
    large compared with the off-diagonals (~1 nm), so the susceptibility sum
    contains big terms that must cancel. STEP 11 is what tests that cancellation.

    SOURCE  nextnano/demos/_shared/chi2.py:220
    """
    n = psi.shape[1]
    return np.array([[float(np.trapezoid(psi[:, i] * z_nm * psi[:, j], z_nm))
                      for j in range(n)] for i in range(n)])


def centroid_nm(z_nm: np.ndarray, density: np.ndarray) -> float:
    """STEP 4c -- centroid from the solver's own probability density.

    MATH    <z> = integral z rho dz / integral rho dz

    Reported separately from the z-matrix diagonals and computed from
    probabilities_*.dat rather than from squared envelopes, because that is the
    quantity nextnano normalises. The two agree to ~1e-14 in practice.

    SOURCE  nextnano/demos/_shared/analysis.py:112, called via
            nextnano/demos/16E_.../demo16e.py:742 (localization)
    """
    return float(np.trapezoid(z_nm * density, z_nm) / np.trapezoid(density, z_nm))


# ===========================================================================
# PART E -- SUSCEPTIBILITY.
# ===========================================================================

def k_grid() -> tuple[np.ndarray, np.ndarray]:
    """STEP 5 -- in-plane momentum grid and its integration weights.

    MATH    k_max = fraction * pi / a                 = 0.555714439 nm^-1
            k     = linspace(0, k_max, 96)
            trapz = [h/2, h, ..., h, h/2]
            w(k)  = g_s * (k / 2pi) * trapz           units nm^-2

            The k/(2pi) is the RADIAL JACOBIAN of the reduction

              (1/A) sum_k  ->  integral d^2k/(2pi)^2  =  (1/2pi) integral k dk

            Dimensional analysis fixes this uniquely: no other normalisation
            gives m/V at the end. It is folded into the weights so the k-sum
            downstream is a bare dot product -- apply it twice and you
            double-count.

            NOTE k_max uses pi/a, not 2pi/a. That convention is a factor ~4 on
            the disc area and is named 'legacy_pi_over_a' rather than buried.

    INVARIANT   sum(w) == g_s * k_max^2 / (4 pi)      exactly (analytic)
                w[0]   == 0                           k = 0 carries zero weight

    SOURCE  nextnano/demos/_shared/chi2.py:432, k_max at :334
    """
    k_max = K_FRACTION_OF_BZ * math.pi / LATTICE_CONSTANT_NM
    k = np.linspace(0.0, k_max, K_POINTS)
    step = k[1] - k[0]
    trapz = np.full(K_POINTS, step)
    trapz[0] = trapz[-1] = 0.5 * step
    return k, (k / (2.0 * math.pi)) * trapz * SPIN_DEGENERACY


def reduced_mass_m0() -> float:
    """STEP 6a -- in-plane reduced mass.

    MATH    1/m_r = 1/m_e + 1/m_hh       ->  0.041921788 m0

    These are the IN-PLANE masses (0.067 / 0.112). They are NOT the confinement
    masses nextnano used (0.067 / 0.51 growth-direction). Heavy holes really are
    light in-plane, so both are right -- but they come from two different models
    bolted together.

    SOURCE  nextnano/demos/_shared/chi2.py:340
    """
    return 1.0 / (1.0 / M_ELECTRON_INPLANE + 1.0 / M_HH_INPLANE)


def transition_energies_eV(e_e: np.ndarray, e_hh: np.ndarray, k_per_nm: np.ndarray) -> np.ndarray:
    """STEP 6b -- transition energies with in-plane dispersion.

    MATH    E[n,m,k] = ( E_e,n - E_hh,m ) + hbar^2 k^2 / (2 m_r)

    Shape (n_e, n_h, n_k) in eV. Electrons disperse up and holes down on the
    single electron scale, so the transition energy RISES with k. At the cutoff
    the kinetic term adds 0.2807 eV.

    UNIT TRAP: k arrives in nm^-1 and must become m^-1 (x1e9) BEFORE squaring.

    APPROXIMATION: only the energies disperse. The envelopes, and therefore all
    three matrices from STEP 4, are treated as k-independent and stay outside
    the k-sum. This follows the source paper.

    SOURCE  nextnano/demos/_shared/chi2.py:454
    """
    k_m = np.asarray(k_per_nm, dtype=float) * 1.0e9
    kinetic_eV = ((REDUCED_PLANCK_J_S ** 2) * k_m ** 2
                  / (2.0 * reduced_mass_m0() * ELECTRON_MASS_KG)) / ELEMENTARY_CHARGE_C
    zero_k = e_e[:, None] - e_hh[None, :]
    return zero_k[:, :, None] + kinetic_eV[None, None, :]


def absolute_scale_pm_per_V() -> float:
    """STEP 9 -- the prefactor, including every unit conversion.

    MATH    prefactor = N_z e^3 r^2 / (6 eps0)
            N_z       = 1 / (30 nm) = 3.3333e7 m^-1     one coupled PAIR per period
            r         = 0.751 nm    a POSITION element, never multiplied by e

            The raw sum S carries   nm (from z) * nm^-2 (from w) / eV^2
                                  = nm^-1 eV^-2
            so                      x1e-9   z:  nm -> m
                                    x1e18   w:  nm^-2 -> m^-2
                                    /q^2    denominators: eV^2 -> J^2
                                    x1e12   m/V -> pm/V

    WHERE THE hbar^2 WENT: the published prefactor is N_z e^3 r^2/(6 eps0 hbar^2)
    with ANGULAR-FREQUENCY denominators. Writing the denominators in ENERGY
    contributes exactly hbar^2 and cancels it. Nothing is missing.

    INVARIANT   returns 56.698169 pm/V per unit of S

    SOURCE  nextnano/demos/_shared/chi2.py:650-663
    """
    n_z = 1.0 / (REFERENCE_PERIOD_NM * 1.0e-9)
    r_m = R_E_HH_NM * 1.0e-9
    prefactor = (n_z * ELEMENTARY_CHARGE_C ** 3 * r_m ** 2
                 / (6.0 * VACUUM_PERMITTIVITY_F_PER_M))
    unit_conversion = 1.0e-9 * 1.0e18 / (ELEMENTARY_CHARGE_C ** 2)
    return prefactor * unit_conversion * 1.0e12


def chi2_spectrum(e_e, e_hh, O, z_e, z_hh, photon_energies_eV) -> np.ndarray:
    """STEPS 7-8 -- the denominators and the triple sum.  THE core calculation.

    MATH    Gamma = 5 meV -> 0.005 eV, added to BOTH denominators

            D2[n,m,k] = E[n,m,k] - 2 hw + i Gamma       two-photon
            D1[a,b,k] = E[a,b,k] -   hw + i Gamma       one-photon

            chi2(w) = scale * sum_k w(k) * sum_m sum_n [ T_cond - T_val ]

              T_cond = sum_l   O[n,m] z_e[n,l] O[l,m]  / ( D2[n,m] D1[l,m] )
              T_val  = sum_l   O[n,m] z_hh[m,l] O[n,l] / ( D2[n,m] D1[n,l] )

            SHG: omega_1 = omega_2 = omega, so D2 resonates at 2 hw = E.
            8 conduction + 8 valence = 16 terms per (photon energy, k).

    THE FOUR PLACES A BUG HIDES HERE
      1. D1 is indexed [l,m] in the conduction term but [n,l] in the valence
         term. Writing D1[n,m] in both is the most likely error and still
         produces a plausible-looking spectrum.
      2. The valence term is SUBTRACTED. The two terms genuinely oppose each
         other; flipping the sign roughly doubles chi2 instead of cancelling.
      3. z_hh is indexed [m,l]. Harmless while it is symmetric and the sum is
         truncated at 2 states -- not harmless if either changes.
      4. Gamma must be in eV. Leaving it in meV inflates broadening 1000x and
         smooths every resonance into a hump that looks well-behaved.

    SOURCE  nextnano/demos/_shared/chi2.py:604-622 (loop), :598 (gamma),
            :607-608 (denominators), :616 (+= conduction), :621 (-= valence),
            :622 (np.dot k-sum), :650-663 (scale)
    """
    k, weights = k_grid()
    E = transition_energies_eV(e_e, e_hh, k)
    n_e, n_h = e_e.size, e_hh.size
    scale = absolute_scale_pm_per_V()

    out = np.zeros(np.size(photon_energies_eV), dtype=complex)
    for idx, hw in enumerate(np.atleast_1d(photon_energies_eV)):
        two_photon = E - 2.0 * hw + 1j * BROADENING_EV
        one_photon = E - hw + 1j * BROADENING_EV
        acc = np.zeros(k.size, dtype=complex)
        for m in range(n_h):                 # heavy-hole state
            for n in range(n_e):             # electron state
                for l in range(n_e):         # intra-conduction partner
                    num = O[n, m] * z_e[n, l] * O[l, m]
                    if num:
                        acc += num / (two_photon[n, m] * one_photon[l, m])
                for l in range(n_h):         # intra-valence partner
                    num = O[n, m] * z_hh[m, l] * O[n, l]
                    if num:
                        acc -= num / (two_photon[n, m] * one_photon[n, l])
        out[idx] = np.dot(weights, acc)
    return out * scale


# ===========================================================================
# PART F -- REDUCTION AND CHECKS.
# ===========================================================================

def focused_grid_nm() -> np.ndarray:
    """STEP 10a -- the reported wavelength grid.

    MATH    linspace(1400, 1800, 401)  ->  exactly 1.0 nm spacing
            1550 nm is an EXACT grid node (index 150).

    SOURCE  nextnano/demos/11_.../demo11.py:646
    """
    return np.linspace(FOCUSED_NM[0], FOCUSED_NM[1], FOCUSED_POINTS)


def reduce_spectrum(wavelength_nm: np.ndarray, chi2: np.ndarray) -> dict:
    """STEP 10b -- the three numbers that reach the results table.

    MATH    |chi2|(lam) = abs(complex array)
            at 1550     = np.interp(1550, lam, |chi2|)
            peak        = argmax |chi2|

    TWO DIFFERENT 1550 nm INTERPOLATIONS EXIST IN THE REPOSITORY:
      #1  chi2.py:406 at_wavelength -- interpolates REAL and IMAG separately in
          PHOTON ENERGY, then takes abs.
      #2  run_demo19.py:302        -- interpolates |chi2| directly in WAVELENGTH.

    The results table uses #2. They agree ONLY because 1550 is an exact grid
    node. Change the grid so it is not, and they diverge: for a complex quantity
    near a resonance, |interp(chi2)| != interp(|chi2|).

    SOURCE  nextnano/demos/19_.../run_demo19.py:297-307
    """
    mag = np.abs(chi2)
    peak = int(np.argmax(mag))
    return {
        "chi2_at_1550_pm_per_V": float(np.interp(1550.0, wavelength_nm, mag)),
        "peak_chi2_pm_per_V": float(mag[peak]),
        "peak_wavelength_nm": float(wavelength_nm[peak]),
    }


def origin_independence(e_e, e_hh, O, z_e, z_hh, shift_nm: float = 100.0) -> float:
    """STEP 11 -- the strongest single check in the chain.

    MATH    translate the z origin and re-evaluate:
              z_e  -> z_e  + shift * I        (diagonals move, off-diagonals do not)
              z_hh -> z_hh + shift * I
            then compare. Relative residual if |chi2| clears a 1e-9 floor,
            absolute otherwise -- so a parity-zero structure cannot manufacture
            a false failure by dividing by noise.

    Tolerance 1e-6 relative. This catches STEP 3 failures, STEP 4 index errors
    that break the cancellation, and mesh problems, all at once. Run it FIRST
    after changing anything in STEPS 4-9.

    SOURCE  nextnano/demos/_shared/chi2.py:830, called at demo11.py:605-643
    """
    hw = np.array([HC_EV_NM / 1550.0])
    ref = chi2_spectrum(e_e, e_hh, O, z_e, z_hh, hw)
    n_e, n_h = e_e.size, e_hh.size
    shifted = chi2_spectrum(e_e, e_hh, O,
                            z_e + shift_nm * np.eye(n_e),
                            z_hh + shift_nm * np.eye(n_h), hw)
    scale = float(np.max(np.abs(ref)))
    residual = float(np.max(np.abs(shifted - ref)))
    return residual / scale if scale > 1e-9 else residual


# ===========================================================================
# SELF-TEST against known-good values from the licensed run
# run demo19_20260814T150258Z_38f64513_ba3c80, case 00 (abrupt reference)
# ===========================================================================

# STEP 0 -- solver output for the abrupt case, as published in the master table.
# In production these are read from energy_spectrum_*.dat and envelopes_*.dat via
# nextnano/demos/_shared/quantum1d.py:46 and demo11.py:246.
ABRUPT = dict(
    E_e=np.array([2.937946127708, 3.047809856454]),
    E_hh=np.array([1.448520856461, 1.415463602981]),
    O=np.array([[0.9825659268894466, 0.024432908041949086],
                [-0.08804807050423832, 0.45711354825954503]]),
    z_e=np.array([[12.734585435956998, 1.0340924360961732],
                  [1.0340924360961732, 18.75911084155838]]),
    z_hh=np.array([[12.65154699565089, 1.451016947195746],
                   [1.451016947195746, 12.967036940337104]]),
)


def _check(label: str, got, want, tol: float, fmt: str = ".9g") -> bool:
    ok = abs(float(got) - float(want)) <= tol
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<46} {format(float(got), fmt):>20}"
          f"   (expected {format(float(want), fmt)})")
    return ok


def main() -> int:
    results: list[bool] = []
    print(__doc__.strip().splitlines()[0])
    print("=" * 96)

    print("\nPART A -- composition (STEPS A1-A5)")
    pos = interface_positions()
    results.append(_check("STEP A2  I1 / I2 / I3 / I4  (sum check)",
                          pos["I1"] + pos["I2"] + pos["I3"] + pos["I4"], 64.2, 1e-12))
    results.append(_check("STEP A2b total domain length [nm]", domain_nm()[1], 30.0, 1e-12))
    w07 = {k: 0.7 for k in ("I1", "I2", "I3", "I4")}
    results.append(_check("STEP A1  linear x_Al at I1 centre (9.10 nm)",
                          evaluate_composition([9.10], "linear", w07)[0], 0.275, 1e-12))
    results.append(_check("STEP A3  fermi  x_Al at 8.80 nm",
                          evaluate_composition([8.80], "fermi", w07)[0], 0.54616239, 1e-8))
    results.append(_check("STEP A1  every profile hits 0.55 at grade start",
                          min(evaluate_composition([8.75], p, w07)[0]
                              for p in ("linear", "fermi", "erf", "cosine")), 0.55, 1e-12))
    results.append(_check("STEP A1  every profile hits 0.00 at grade end",
                          max(evaluate_composition([9.45], p, w07)[0]
                              for p in ("linear", "fermi", "erf", "cosine")), 0.0, 1e-12))
    zt, _ = composition_table("fermi", w07)
    results.append(_check("STEP A4  DAT table rows", zt.size, 601, 0))
    for prof, want in (("fermi", 3.2641931e-3), ("erf", 1.5700115e-3), ("cosine", 1.7182698e-3)):
        results.append(_check(f"STEP A5b {prof:<6} table-vs-analytic max error",
                              rendering_error(prof, w07), want, 1e-8, ".6e"))

    print("\nPART B -- material model (STEPS B1-B4), vs the solver's own band edges")
    ec0, ev0 = band_edges_eV(0.0)
    ec55, ev55 = band_edges_eV(0.55)
    results.append(_check("STEP B3  GaAs      E_c [eV]", ec0, 2.8821488095238, 1e-11))
    results.append(_check("STEP B3  GaAs      E_v [eV]", ev0, 1.4596666666667, 1e-11))
    results.append(_check("STEP B3  Al0.55    E_c [eV]", ec55, 3.3244289271371, 1e-11))
    results.append(_check("STEP B3  Al0.55    E_v [eV]", ev55, 1.1795333333333, 1e-11))
    results.append(_check("STEP B2  Al0.55 Gamma gap [eV]", alloy_gamma_gap_eV(0.55), 2.1448955938038, 1e-11))
    results.append(_check("         conduction offset [meV]", (ec55 - ec0) * 1e3, 442.2801176133, 1e-7))
    results.append(_check("         valence offset [meV]", (ev0 - ev55) * 1e3, 280.1333333334, 1e-7))
    results.append(_check("STEP B4  m_Gamma at x=0.55 [m0]", effective_mass(0.55, "gamma"), 0.11265, 1e-12))
    results.append(_check("STEP B4  m_HH    at x=0.55 [m0]", effective_mass(0.55, "hh"), 0.50450, 1e-12))

    print("\nPART C -- quantum (STEP C1), vs the licensed eigenvalues")
    z = np.arange(interface_positions()["I1"] - QUANTUM_PADDING_NM,
                  interface_positions()["I4"] + QUANTUM_PADDING_NM + 1e-12, ACTIVE_MESH_NM)
    x_al = evaluate_composition(z, "abrupt", {})
    ec, ev, me, mh = build_potential(z, x_al)
    _, e_elec, _ = solve_band(z, ec, me, 2, electron=True)
    _, e_hole, _ = solve_band(z, ev, mh, 2, electron=False)
    results.append(_check("STEP C1  E1  [eV]  (mesh-limited, tol 0.5 meV)", e_elec[0], 2.937946127708, 5e-4))
    results.append(_check("STEP C1  E2  [eV]  (mesh-limited, tol 0.5 meV)", e_elec[1], 3.047809856454, 5e-4))
    results.append(_check("STEP C1  HH1 [eV]  (mesh-limited, tol 0.5 meV)", e_hole[0], 1.448520856461, 5e-4))
    results.append(_check("STEP C1  HH2 [eV]  (mesh-limited, tol 0.5 meV)", e_hole[1], 1.415463602981, 5e-4))

    print("\nPART D/E -- matrix elements and susceptibility (STEPS 4-9)")
    A = ABRUPT
    results.append(_check("STEP 4b  z_e  symmetric  (max asymmetry)",
                          np.max(np.abs(A["z_e"] - A["z_e"].T)), 0.0, 1e-12))
    results.append(_check("STEP 4b  z_hh symmetric  (max asymmetry)",
                          np.max(np.abs(A["z_hh"] - A["z_hh"].T)), 0.0, 1e-12))
    results.append(_check("STEP 4a  O NOT symmetric (must be non-zero)",
                          np.max(np.abs(A["O"] - A["O"].T)) > 1e-3, True, 0))
    k, w = k_grid()
    k_max = K_FRACTION_OF_BZ * math.pi / LATTICE_CONSTANT_NM
    results.append(_check("STEP 5   k_max [nm^-1]", k_max, 0.5557144387, 1e-9))
    results.append(_check("STEP 5   sum(w) vs analytic g_s k_max^2/(4pi)",
                          w.sum(), SPIN_DEGENERACY * k_max ** 2 / (4 * math.pi), 1e-15, ".10e"))
    results.append(_check("STEP 5   w[0] must be exactly zero", w[0], 0.0, 0.0))
    results.append(_check("STEP 6a  reduced mass [m0]", reduced_mass_m0(), 0.0419217877, 1e-9))
    results.append(_check("STEP 6b  kinetic energy at k_max [eV]",
                          transition_energies_eV(A["E_e"], A["E_hh"], k)[0, 0, -1]
                          - (A["E_e"][0] - A["E_hh"][0]), 0.2806644, 1e-6))
    results.append(_check("STEP 9   absolute scale [pm/V per unit S]",
                          absolute_scale_pm_per_V(), 56.6981690, 1e-6))

    lam = focused_grid_nm()
    results.append(_check("STEP 10a 1550 nm is an exact grid node", float(np.min(np.abs(lam - 1550.0))), 0.0, 0.0))
    chi = chi2_spectrum(A["E_e"], A["E_hh"], A["O"], A["z_e"], A["z_hh"], HC_EV_NM / lam)
    red = reduce_spectrum(lam, chi)
    results.append(_check("STEPS 7-9  |chi2| at 1550 nm [pm/V]",
                          red["chi2_at_1550_pm_per_V"], 31.036041396587407, 1e-6))
    results.append(_check("STEPS 7-9  peak |chi2| [pm/V]",
                          red["peak_chi2_pm_per_V"], 63.63186706362127, 1e-6))
    results.append(_check("STEP 10b   peak wavelength [nm]",
                          red["peak_wavelength_nm"], 1517.0, 1e-9))

    print("\nPART F -- checks (STEP 11)")
    results.append(_check("STEP 11  origin-independence residual (tol 1e-6)",
                          origin_independence(A["E_e"], A["E_hh"], A["O"], A["z_e"], A["z_hh"]),
                          0.0, 1e-6, ".3e"))

    print("=" * 96)
    passed = sum(1 for r in results if r)
    print(f"{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path
import subprocess

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# ======================================================================================
# 1_band_paper_replication_v1.py
#
# REPRODUCES Fig. 2d OF "Enhanced Interband Coupled Quantum Wells"
#
# This script exists to answer "what did the paper compute?", not "what does this
# structure do?". For the latter use 8_band_non_parabolic_v24.py, which is the same
# physics with the normalization corrected and which gives roughly 11x smaller numbers.
#
# The paper's Methods state the envelopes came from "Schrodinger-Poisson methods with
# the Nextnano software", i.e. a single-band model, so the deck here uses Gamma{} and
# HH{} rather than kp_8band{}. That choice is confirmed by the transition energies:
# single band gives 1.4933 and 1.6367 eV against the quoted 1.49 and 1.62, where
# 8-band k.p gives 1.4979 and 1.6574. The more sophisticated solver agrees with the
# paper *less* well, because it is a different model rather than a refinement.
#
# Four further choices are needed that the paper does not state. Each is isolated in
# the PAPER CONVENTIONS block below with the evidence for it. Together they reproduce
# all four peaks to within 6% in height and 1% in position, and both near-zero troughs.
#
# Read chi2_replication_findings.md before changing anything here. In particular, do
# not "fix" the conventions in this file: reproducing the published curve is its whole
# purpose, and the corrected calculation lives in the v24 script.
# ======================================================================================

# ======================================================================================
# PATHS AND SOLVER
# ======================================================================================

BASE_DIR = Path(
    r"C:\Users\mccoysa\Projects\Quantum_Wells\nextnano_standard_26.7.0.0_2026_07_03_portable\nextnano\2026_07_03\nextnano++"
)

EXE_64 = BASE_DIR / r"bin 64bit\nextnano++_Microsoft_64bit_serial.exe"
EXE_32 = BASE_DIR / r"bin 32bit\nextnano++_Microsoft_32bit_serial.exe"
EXE_PATH = EXE_64 if EXE_64.exists() else EXE_32

DATABASE_PATH = BASE_DIR / "database" / "database.nnp"
LICENSE_PATH = Path(
    r"C:\Users\mccoysa\Projects\Quantum_Wells\License_nnp_stephen20260731.lic"
)

OUTPUT_DIR_1B = BASE_DIR / "Output" / "simulation_1band"
FIG_DIR = Path(
    r"C:\Users\mccoysa\Projects\Quantum_Wells\mqw-optimization\figures_1band_paper_replication"
)

RUN_SOLVER = True

# ======================================================================================
# PAPER CONVENTIONS
#
# The four undocumented choices. Every one is required; dropping any single one breaks
# the agreement with Fig. 2d.
# ======================================================================================

# (1) Eq. 2 prints N_z e^3 r^2 / (6 eps0 hbar^2). Reproducing Fig. 2d needs the 1/6
#     absent. We cannot derive the correct constant from first principles because it
#     depends on permutation-symmetry factors entangled with how Eq. 2 enumerates its
#     terms, so this is empirical: with the 1/6 present the figure cannot be matched
#     under any other choice here. Supporting evidence that the 6 is a transcription
#     slip: Eq. 1, the general form in the same Methods section, carries 1/2, and the
#     stated simplifications do not obviously produce a factor of 3.
PREFACTOR_DIVISOR = 1.0

# (2) The 2D sum-to-integral conversion carries the Brillouin-zone density of states,
#         (1/A) sum_k = g_s/(2 pi)^2 int d2k = (1/pi) int k dk
#     Fig. 2d instead requires
#         sum_k -> g_s int d2k = 4 pi int k dk
#     which is larger by exactly (2 pi)^2 = 39.478. The Methods describe this step in
#     words without giving the measure, so it cannot be checked against the text.
#
#     THIS ONE IS NOT A CONVENTION. The 1/(2 pi)^2 is what makes the result a density
#     and is required. If this reading is right the published values are high by 39.5x.
#     It is set here only to reproduce the figure.
APPLY_BZ_NORMALIZATION = False

# (3) Fig. 2d touches zero near 605 and 1330 nm. A magnitude cannot do that unless Re
#     and Im vanish together, and at those two wavelengths our result is 99% and 100%
#     imaginary. The reason is the k continuum: with E(k) sweeping 1.49 -> 2.33 eV,
#     some k state is resonant at every fundamental in 531-830 and 1062-1661 nm, so the
#     absorptive part cannot vanish. Only Re passes through zero. Plotting |Re| puts
#     the zeros at 586 and 1321 nm and improves the peak heights.
#
#     Two readings fit and we cannot separate them: either Re was plotted and the axis
#     bars are a slip, or the computed chi(2) was real-valued (e.g. +iGamma not carried
#     as complex arithmetic), in which case the axis label is correct. The axis reads
#     "Simulated |chi(2)|" with explicit bars, so the second is at least as likely.
PLOT_REAL_PART = True

# (4) One-tenth of the GaAs Brillouin zone is 2 pi / a = 1.1114 1/nm, which puts the
#     two cutoff artefacts at 500 and 1001 nm against the published 540 and 1080. A
#     cutoff of 1.000 aligns all four peaks to better than 1%. The round value suggests
#     1.0 was used as a stand-in for one-tenth of the zone.
#
#     Note this is degenerate with the in-plane reduced mass: E(k_max) depends only on
#     E(0) + hbar^2 k_max^2 / 2 mu. We fixed mu at the textbook masses and fitted the
#     cutoff rather than the reverse, because the cutoff is the quantity the paper
#     actually describes. The hole mass is far too weak a knob to matter: 0.34 -> 0.60
#     moves the artefact by only 2%.
K_MAX_NM_INV = 1.000

# ======================================================================================
# PHYSICAL CONSTANTS
# ======================================================================================

H_PLANCK = 6.62607015e-34
C_LIGHT = 299792458.0
E_CHARGE = 1.602176634e-19
EPS0 = 8.8541878188e-12
HB = 0.0380998  # hbar^2 / 2 m0, eV nm^2

XI2_GAMMA_EV = 0.005  # stated in the paper; also 5 meV in the citing Fathi et al.
REHH_M = 7.51e-10     # unit-cell interband matrix element, 7.51 Angstrom
NZ_M_INV = 1.0 / (30.0e-9)  # one well per 30 nm period, per the Fig. 1a caption
SPIN_DEGENERACY = 2

# ======================================================================================
# STRUCTURE
#
# Unchanged from the 8-band deck: the structure was never the source of disagreement.
# The paper states its 2340 pm/V prediction is "based on abrupt composition changes at
# the interfaces", so GRADE_WIDTH_NM stays 0; the STEM-measured graded profile is used
# only later, for the red points in its Fig. 4.
# ======================================================================================

WELL1_NM = 2.9
TUNNEL_BARRIER_NM = 1.8
WELL2_NM = 7.1
AL_X = 0.55
GRADE_WIDTH_NM = 0.0
STRUCTURE_MIDDLE_NM = 18.0

GRID_FINE_SPACING_NM = 0.02
GRID_COARSE_SPACING_NM = 1.0
GRID_REFINE_MARGIN_NM = 0.7

# In-plane masses for the parabolic dispersion. A single-band model has no HH/LH
# coupling and therefore no in-plane mass reversal, so the heavy hole disperses with
# its bulk mass. These give mu = 0.0560 m0, close to the 0.0557 the 8-band fit
# produces, so the two models disagree about non-parabolicity rather than about the
# zone-centre curvature.
M_E_INPLANE = 0.067
M_HH_INPLANE = 0.34

WL_MIN_NM = 400.0
WL_MAX_NM = 1850.0
WL_POINTS = 1200

# Eq. 2 term lists, in the [e1, e2, h1, h2] index order used throughout.
XI2_BPE = np.array([
    [0, 0, 2], [0, 0, 3], [0, 1, 2], [0, 1, 3],
    [1, 0, 2], [1, 0, 3], [1, 1, 2], [1, 1, 3]
], dtype=int)

XI2_BPH = np.array([
    [2, 2, 0], [3, 3, 0], [2, 3, 0], [2, 3, 1],
    [3, 2, 0], [3, 2, 1], [2, 2, 1], [3, 3, 1]
], dtype=int)

# Digitised from Fig. 2d.
PAPER_FIG2D = np.array([
    [400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],
    [630,220],[660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],
    [850,1100],[900,1120],[950,1220],[1000,1450],[1040,1950],[1080,3250],
    [1105,2050],[1130,1850],[1150,1150],[1175,1180],[1200,1050],[1225,750],
    [1250,750],[1275,350],[1300,350],[1330,0],[1360,200],[1400,600],
    [1440,1050],[1480,1800],[1500,2600],[1520,3950],[1540,2900],[1560,1950],
    [1580,1450],[1600,1250],[1650,1050],[1700,950],[1750,850],[1800,750],[1850,700]
])
PAPER_PEAKS = {540: 1260, 760: 2450, 1080: 3250, 1520: 3950}


# ======================================================================================
# INPUT DECK
# ======================================================================================

def well_edges():
    """Edges of the two GaAs wells, ordered 2.9 nm then 7.1 nm as in paper Fig. 1a."""
    qw1_min = STRUCTURE_MIDDLE_NM - TUNNEL_BARRIER_NM / 2.0 - WELL1_NM
    qw1_max = STRUCTURE_MIDDLE_NM - TUNNEL_BARRIER_NM / 2.0
    qw2_min = STRUCTURE_MIDDLE_NM + TUNNEL_BARRIER_NM / 2.0
    qw2_max = STRUCTURE_MIDDLE_NM + TUNNEL_BARRIER_NM / 2.0 + WELL2_NM
    return qw1_min, qw1_max, qw2_min, qw2_max


def common_header():
    return (
        'run{quantum{}} '
        'global{simulate1D{} crystal_zb{x_hkl=[1,0,0] y_hkl=[0,1,0]} substrate{name="GaAs"} temperature=300.0} '
        'contacts{fermi{name=fermi_zero bias=0}} '
        'classical{Gamma{output_bandedge{averaged=no}} HH{} LH{} SO{} output_bandedges{averaged=no}} '
        'poisson{between_fermi_levels{}} '
        'currents{recombination_model{SRH=no Auger=no radiative=no}}'
    )


def common_structure_and_grid():
    QW1_min, QW1_max, QW2_min, QW2_max = well_edges()

    margin = max(GRADE_WIDTH_NM, GRID_REFINE_MARGIN_NM)
    refine_min, refine_max = QW1_min - margin, QW2_max + margin

    grid = (
        f"line{{pos=0.0 spacing={GRID_COARSE_SPACING_NM}}} "
        f"line{{pos={refine_min:.6f} spacing={GRID_FINE_SPACING_NM}}} "
        f"line{{pos={refine_max:.6f} spacing={GRID_FINE_SPACING_NM}}} "
        f"line{{pos=56.0 spacing={GRID_COARSE_SPACING_NM}}}"
    )

    return f"""
structure{{
    output_region_index{{boxes=no}}
    output_material_index{{boxes=no}}
    output_alloy_composition{{boxes=no}}

    region{{everywhere{{}} contact{{name=fermi_zero}}
        ternary_constant{{name="Al(x)Ga(1-x)As" alloy_x={AL_X}}}}}

    region{{line{{x=[0.0,56.0]}}
        ternary_constant{{name="Al(x)Ga(1-x)As" alloy_x={AL_X}}}}}

    region{{line{{x=[{QW1_min:.6f},{QW1_max:.6f}]}} binary{{name="GaAs"}}}}
    region{{line{{x=[{QW2_min:.6f},{QW2_max:.6f}]}} binary{{name="GaAs"}}}}
}}

grid{{xgrid{{{grid}}}}}
"""


def build_single_band_deck() -> str:
    """Single-band Gamma and HH solvers, the paper's stated Schrodinger-Poisson model.

    There is no k_integration{} here. Single-band regions solve at k_par = 0 only and
    the in-plane dispersion is parabolic by construction, so it is supplied
    analytically in parabolic_dispersion() rather than sampled by the solver.

    energy_shift = both is deliberate: the default wf_amplitudes_shift_* files have
    each psi offset by its own eigenvalue for plotting, and reading those without
    undoing the offset corrupts every overlap and dipole. Requesting both writes an
    unshifted file alongside, which is what load_single_band_states() prefers.
    """
    return (
        common_header()
        + common_structure_and_grid()
        + """
quantum{
    region{
        name=quantum_region
        x=[0.0,36.0]
        no_density=yes
        boundary{x=dirichlet}

        Gamma{ num_ev=4  lapack{} }
        HH{    num_ev=4  lapack{} }

        output_wavefunctions{
            max_num=4
            amplitudes=yes
            probabilities=yes
            energy_shift=both
            include_energies_in_shifted_files=no
            in_one_file=yes
        }
    }
}
"""
    ).strip()


# ======================================================================================
# SOLVER
# ======================================================================================

def run_nextnano(input_text: str, input_filename: str, output_dir: Path):
    if not EXE_PATH.exists():
        raise FileNotFoundError(f"nextnano++ executable not found: {EXE_PATH}")
    input_path = Path.cwd() / input_filename
    input_path.write_text(input_text, encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Solver] Running {input_filename} ...")
    cmd = [
        str(EXE_PATH),
        "--database", str(DATABASE_PATH),
        "--license", str(LICENSE_PATH),
        "--outputdirectory", str(output_dir),
        "--noautooutdir",
        str(input_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"\n--- STDOUT ---\n{res.stdout}\n\n--- STDERR ---\n{res.stderr}")
        raise RuntimeError(f"Simulation failed with exit code {res.returncode}")
    print(f"[Solver] {input_filename} finished successfully!")


# ======================================================================================
# DATA LOADING
# ======================================================================================

def read_numeric_dat(file_path: Path) -> np.ndarray:
    rows = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("%"):
                continue
            try:
                rows.append([float(p) for p in line.split()])
            except ValueError:
                continue
    if not rows:
        raise RuntimeError(f"No numeric rows parsed from file: {file_path}")
    return np.array(rows)


def _find_one(root: Path, patterns, what: str) -> Path:
    """Locate a single output file, tolerating nextnano's index-width differences.

    The single-band filenames carry a zero-padded index whose width has varied between
    releases (wf_..._0000.dat vs _00000.dat) and move into per-band subdirectories when
    structured = yes, so globbing recursively is more robust than hardcoding a path.
    """
    for pattern in patterns:
        hits = sorted(root.rglob(pattern))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise RuntimeError(
                f"Ambiguous {what}: {pattern} matched {[h.name for h in hits]} under "
                f"{root}. Clear the output directory and re-run.")
    available = sorted(p.name for p in root.rglob("*.dat"))[:40]
    raise FileNotFoundError(
        f"Could not locate {what} under {root}. Tried {list(patterns)}. "
        f"Files present (first 40): {available}")


def load_single_band_states(output_root: Path):
    """Read Gamma and HH eigenvalues and envelopes, and assign the four state roles.

    Single-band output carries no spinor composition, so unlike the 8-band pipeline
    there is nothing to identify: the solver already separates the bands. e1 and e2 are
    simply Gamma states 1 and 2, and h1 and h2 are HH states 1 and 2. Hole eigenvalues
    are returned as confinement energies measured downward from the GaAs valence edge,
    which is how nextnano reports them for the HH solver.
    """
    root = output_root / "bias_00000"
    if not root.exists():
        root = output_root

    out = {}
    for band in ("Gamma", "HH"):
        e_file = _find_one(
            root,
            [f"*energy_spectrum*{band}*.dat", f"*energy_spectrum*{band.lower()}*.dat"],
            f"{band} energy spectrum")
        energies = read_numeric_dat(e_file)
        energies = energies[:, -1] if energies.ndim == 2 else energies

        # Prefer the unshifted amplitudes; fall back to de-shifting if only the
        # plotting-oriented file exists.
        try:
            a_file = _find_one(root, [f"wf_amplitudes_quantum_region_{band}_*.dat"],
                               f"{band} amplitudes")
            shifted = False
        except FileNotFoundError:
            a_file = _find_one(root, [f"wf_amplitudes_shift_quantum_region_{band}_*.dat"],
                               f"{band} shifted amplitudes")
            shifted = True

        raw = read_numeric_dat(a_file)
        x_nm, psi = raw[:, 0], raw[:, 1:]
        if shifted:
            print(f"  [load] de-shifting {a_file.name} by its eigenvalues")
            psi = psi - energies[None, :psi.shape[1]]

        out[band] = {"x_nm": x_nm, "energies": energies, "psi": psi, "file": e_file}
        print(f"  [load] {band}: {len(energies)} states from {e_file.name}")

    x_nm = out["Gamma"]["x_nm"]
    if not np.allclose(x_nm, out["HH"]["x_nm"]):
        raise RuntimeError("Gamma and HH envelopes are on different grids.")

    def norm(v):
        # The overall sign is arbitrary and cancels: every chi(2) term contains each
        # state exactly twice. Fixing it anyway keeps the printed matrices comparable
        # between runs.
        v = np.asarray(v, dtype=float)
        if np.trapezoid(v, x_nm) < 0:
            v = -v
        return v / np.sqrt(np.trapezoid(v ** 2, x_nm))

    e_energies = np.asarray(out["Gamma"]["energies"], dtype=float)
    e_perm = np.argsort(e_energies)[:2]        # electron ground state = lowest
    h_abs, h_perm = resolve_hole_scale(e_energies, out["HH"]["energies"])

    envelopes = {
        "e1": norm(out["Gamma"]["psi"][:, e_perm[0]]),
        "e2": norm(out["Gamma"]["psi"][:, e_perm[1]]),
        "h1": norm(out["HH"]["psi"][:, h_perm[0]]),
        "h2": norm(out["HH"]["psi"][:, h_perm[1]]),
    }
    conf = {
        "e1": float(e_energies[e_perm[0]]),
        "e2": float(e_energies[e_perm[1]]),
        "h1": float(h_abs[0]),
        "h2": float(h_abs[1]),
    }
    return {"x_nm": x_nm, "envelopes": envelopes, "confinement": conf}


# The two quoted transition energies, used only to resolve the HH sign convention.
TARGET_TRANSITIONS = (1.49, 1.62)


def resolve_hole_scale(e_energies, h_energies):
    """Put HH eigenvalues on the same electron-energy scale as Gamma, and order them.

    nextnano++ may report HH eigenvalues either on a common absolute scale with Gamma,
    or as positive confinement depths measured downward from the valence edge. The two
    differ by a sign, and the sign also flips which eigenvalue is the hole ground state,
    so the scale and the h1/h2 assignment have to be settled together.

    A single transition cannot separate them here: the hole confinement is only ~14 meV,
    so both readings of e1-h1 land within 30 meV of 1.49 eV. The *pair* of transitions
    can, because the e1-h1 to e2-h2 splitting is 0.13 eV and comes out with the wrong
    sign under the wrong hypothesis. Both candidates are printed so the choice is
    auditable rather than silent.

    Returns (hole energies on the electron scale, ordered ground state first, and the
    permutation to apply to the envelopes).
    """
    e_sorted = np.sort(np.asarray(e_energies, dtype=float))[:2]
    h = np.asarray(h_energies, dtype=float)[:2]

    results = []
    for sign, name in ((-1.0, "confinement depths below the valence edge"),
                       (+1.0, "a common absolute scale with Gamma")):
        eh = sign * h
        perm = np.argsort(-eh)          # ground state = highest electron energy
        eh = eh[perm]
        trans = (e_sorted[0] - eh[0], e_sorted[1] - eh[1])
        err = sum(abs(t - g) for t, g in zip(trans, TARGET_TRANSITIONS))
        results.append({"sign": sign, "name": name, "eh": eh,
                        "perm": perm, "trans": trans, "err": err})

    results.sort(key=lambda r: r["err"])
    best, runner = results

    print("  [load] resolving the HH energy convention")
    for r in results:
        print("     %-45s e1-h1 = %.4f  e2-h2 = %.4f  (off by %.0f meV)"
              % (r["name"], r["trans"][0], r["trans"][1], 1000 * r["err"]))

    if best["err"] > 0.10:
        raise RuntimeError(
            f"Neither hole convention reproduces the expected transitions "
            f"{TARGET_TRANSITIONS}; best was {best['trans']}. Check the structure "
            "definition and the HH energy spectrum file.")
    if runner["err"] - best["err"] < 0.02:
        raise RuntimeError(
            "The two hole conventions are within 20 meV of each other, so the "
            "automatic choice is not trustworthy. Inspect the HH spectrum by hand.")

    print("  [load] chose: %s" % best["name"])
    return best["eh"], best["perm"]


def report_states(states):
    conf = states["confinement"]
    print("\n[States] eigenvalues on a common electron-energy scale (eV)")
    for key in ("e1", "e2", "h1", "h2"):
        print("  %-3s = %+9.5f" % (key, conf[key]))

    print("\n[States] interband transitions")
    ok = True
    for e, h, target in (("e1", "h1", 1.49), ("e2", "h2", 1.62)):
        delta = conf[e] - conf[h]
        print("  %s-%s = %.4f eV -> %4.0f nm (1w), %4.0f nm (2w)   [paper %.2f]"
              % (e, h, delta, 1e9 * H_PLANCK * C_LIGHT / (delta * E_CHARGE),
                 2e9 * H_PLANCK * C_LIGHT / (delta * E_CHARGE), target))
        if abs(delta - target) > 0.05:
            ok = False
            print("    WARNING: %.0f meV from the paper value; check the structure."
                  % (1000 * abs(delta - target)))
    return ok


# ======================================================================================
# MATRIX ELEMENTS AND DISPERSION
# ======================================================================================

def build_numerator_matrices(states):
    """Envelope overlaps and dipoles in the [e1, e2, h1, h2] ordering used by Eq. 2.

    The dipole origin sits at the centroid of the coupled-QW block. chi(2) is formally
    origin independent, but the four-state truncation does not fully cancel a shift, so
    main() reports the residual sensitivity as a sanity check.
    """
    x_nm = states["x_nm"]
    env = states["envelopes"]
    qw1_min, _, _, qw2_max = well_edges()
    z_nm = x_nm - 0.5 * (qw1_min + qw2_max)

    order = ["e1", "e2", "h1", "h2"]
    overlap = np.zeros((4, 4))
    dipole = np.zeros((4, 4))
    for a, ka in enumerate(order):
        for b, kb in enumerate(order):
            overlap[a, b] = np.trapezoid(env[ka] * env[kb], x_nm)
            dipole[a, b] = np.trapezoid(env[ka] * z_nm * env[kb], x_nm)
    return {"overlap": overlap, "dipole": dipole}


def parabolic_dispersion(conf):
    """In-plane dispersion for a single-band model: parabolic, no coupling.

    conf is already on a common electron-energy scale, so electrons disperse upward and
    holes downward and E[e] - E[h] is the transition at every k, which is what
    perform_integration expects. The reduced mass 1/mu = 1/m_e + 1/m_hh sets both the
    resonance width and, together with the cutoff, where the truncation artefacts land.
    """
    def band(edge, mass, sign):
        return lambda k: edge + sign * HB * np.asarray(k, dtype=float) ** 2 / mass

    return {
        "e1": band(conf["e1"], M_E_INPLANE, +1.0),
        "e2": band(conf["e2"], M_E_INPLANE, +1.0),
        "h1": band(conf["h1"], M_HH_INPLANE, -1.0),
        "h2": band(conf["h2"], M_HH_INPLANE, -1.0),
    }


# ======================================================================================
# CHI(2) INTEGRATION
# ======================================================================================

def k_measure():
    """(1/A) sum_k|| folded with d2k = 2 pi k dk, so the integrand is a function of k.

    Correct: g_s/(2 pi)^2 * 2 pi = g_s/(2 pi) = 1/pi.
    Paper:   g_s * 2 pi = 4 pi, larger by (2 pi)^2 = 39.478. See convention (2).
    """
    correct = SPIN_DEGENERACY / (2.0 * np.pi)
    return correct if APPLY_BZ_NORMALIZATION else correct * (2.0 * np.pi) ** 2


def xi2_integrate_complex(integrand, krng, num_points=5000):
    k_arr = np.linspace(0.0, krng, num_points)
    return np.trapezoid(integrand(k_arr), k_arr)


def perform_integration(hw_ev, overlap, dipole, E_interp, apre, krng):
    chi_total = np.zeros_like(hw_ev, dtype=np.complex128)
    idx_to_key = {0: "e1", 1: "e2", 2: "h1", 3: "h2"}
    measure = k_measure()

    for iw, w1 in enumerate(hw_ev):
        w2 = w1
        electron_sum = 0.0 + 0.0j
        hole_sum = 0.0 + 0.0j

        for e_a, e_b, h_c in XI2_BPE:
            key_ea, key_eb, key_hc = idx_to_key[e_a], idx_to_key[e_b], idx_to_key[h_c]
            Ae = apre * overlap[h_c, e_a] * (dipole[e_a, e_b] * 1e-9) * overlap[e_b, h_c]

            def electron_integrand(kval, Ae=Ae, ka=key_ea, kb=key_eb, kc=key_hc):
                E13 = E_interp[ka](kval) - E_interp[kc](kval)
                E23 = E_interp[kb](kval) - E_interp[kc](kval)
                denom = ((E13 - w1 - w2 + 1j * XI2_GAMMA_EV)
                         * (E23 - w1 + 1j * XI2_GAMMA_EV))
                return Ae * measure * kval / denom

            electron_sum += xi2_integrate_complex(electron_integrand, krng)

        for h_a, h_b, e_c in XI2_BPH:
            key_ha, key_hb, key_ec = idx_to_key[h_a], idx_to_key[h_b], idx_to_key[e_c]
            Ah = apre * overlap[e_c, h_a] * (dipole[h_a, h_b] * 1e-9) * overlap[h_b, e_c]

            def hole_integrand(kval, Ah=Ah, ka=key_ha, kb=key_hb, kc=key_ec):
                H13 = E_interp[kc](kval) - E_interp[ka](kval)
                H23 = E_interp[kc](kval) - E_interp[kb](kval)
                denom = ((H13 - w1 - w2 + 1j * XI2_GAMMA_EV)
                         * (H23 - w1 + 1j * XI2_GAMMA_EV))
                return -Ah * measure * kval / denom

            hole_sum += xi2_integrate_complex(hole_integrand, krng)

        # k integral was in nm^-2 -> m^-2 (1e18), then m/V -> pm/V (1e12).
        chi_total[iw] = (electron_sum + hole_sum) * 1e18 * 1e12

    return chi_total


def chi2_prefactor():
    """N_z e^3 r^2 / (divisor * eps0 * hbar^2).

    The denominators are in eV^2, so hbar^2 cancels against the angular frequencies and
    two powers of e cancel from e^3, leaving a single elementary charge on top.
    """
    return (NZ_M_INV * E_CHARGE * REHH_M ** 2) / (PREFACTOR_DIVISOR * EPS0)


# ======================================================================================
# PLOTTING
# ======================================================================================

def plot_vs_paper(wl_nm, chi, save_dir: Path):
    plotted = np.abs(chi.real) if PLOT_REAL_PART else np.abs(chi)
    label = r"$|\mathrm{Re}\,\chi^{(2)}|$" if PLOT_REAL_PART else r"$|\chi^{(2)}|$"

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(14, 5.0), dpi=200)
    for ax in (ax_lin, ax_log):
        ax.plot(PAPER_FIG2D[:, 0], PAPER_FIG2D[:, 1], "k--", lw=2.0, label="Paper Fig. 2d")
        ax.plot(wl_nm, plotted, color="crimson", lw=1.8,
                label=label + ", this work")
        # The magnitude is carried alongside because the gap between them is the whole
        # basis for convention (3): it is what fills in the troughs.
        ax.plot(wl_nm, np.abs(chi), color="lightcoral", lw=1.0, alpha=0.8,
                label=r"$|\chi^{(2)}|$ (troughs filled by Im)")
        ax.set_xlabel("Fundamental wavelength (nm)")
        ax.set_ylabel(r"$\chi^{(2)}$ (pm/V)")
        ax.grid(True, ls=":", alpha=0.6)
        ax.legend(fontsize=8)
    ax_lin.set_title("Linear scale")
    ax_log.set_yscale("log")
    ax_log.set_ylim(1.0, 2e4)
    ax_log.set_title("Log scale")

    fig.suptitle("Single-band reproduction of the published Fig. 2d")
    plt.tight_layout()
    save_dir.mkdir(parents=True, exist_ok=True)
    out = save_dir / "chi2_paper_replication.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[Plot] wrote {out}")


# ======================================================================================
# MAIN
# ======================================================================================

def main():
    print("=" * 78)
    print("Single-band reproduction of Fig. 2d")
    print("  prefactor divisor : %.1f %s" % (
        PREFACTOR_DIVISOR, "(Eq. 2 as printed)" if PREFACTOR_DIVISOR == 6 else "(1/6 removed)"))
    print("  k measure         : %s" % (
        "correct 1/(2pi)^2" if APPLY_BZ_NORMALIZATION else "unnormalized, (2pi)^2 larger"))
    print("  plotted quantity  : %s" % ("Re chi(2)" if PLOT_REAL_PART else "|chi(2)|"))
    print("  k cutoff          : %.3f 1/nm" % K_MAX_NM_INV)
    print("=" * 78)

    if RUN_SOLVER:
        run_nextnano(build_single_band_deck(), "simulation_1band.nnp", OUTPUT_DIR_1B)

    print("\n[Load] reading single-band output")
    states = load_single_band_states(OUTPUT_DIR_1B)
    report_states(states)

    num = build_numerator_matrices(states)
    order = ["e1", "e2", "h1", "h2"]
    print("\n[Matrices]")
    print("  overlaps:  " + "  ".join(
        "<%s|%s> = %+.3f" % (h, e, num["overlap"][order.index(h), order.index(e)])
        for h in ("h1", "h2") for e in ("e1", "e2")))
    print("  dipoles:   " + "  ".join(
        "<%s|z|%s> = %+.3f nm" % (a, b, num["dipole"][order.index(a), order.index(b)])
        for a, b in (("e1", "e2"), ("h1", "h2"), ("e1", "e1"), ("h1", "h1"))))

    E = parabolic_dispersion(states["confinement"])
    mu = 1.0 / (1.0 / M_E_INPLANE + 1.0 / M_HH_INPLANE)
    e0 = E["e1"](0.0) - E["h1"](0.0)
    ek = E["e1"](K_MAX_NM_INV) - E["h1"](K_MAX_NM_INV)
    print("\n[Dispersion] parabolic, reduced mass %.4f m0" % mu)
    print("  e1-h1 sweeps %.3f -> %.3f eV over |k| <= %.3f 1/nm" % (e0, ek, K_MAX_NM_INV))
    print("  cutoff artefacts therefore land near %.0f nm (2w) and %.0f nm (1w)"
          % (2e9 * H_PLANCK * C_LIGHT / (ek * E_CHARGE),
             1e9 * H_PLANCK * C_LIGHT / (ek * E_CHARGE)))

    wl_nm = np.linspace(WL_MIN_NM, WL_MAX_NM, WL_POINTS)
    hw_ev = (H_PLANCK * C_LIGHT) / (wl_nm * 1e-9 * E_CHARGE)
    apre = chi2_prefactor()

    print("\n[Integrating] ...")
    chi = perform_integration(hw_ev, num["overlap"], num["dipole"], E, apre, K_MAX_NM_INV)
    plotted = np.abs(chi.real) if PLOT_REAL_PART else np.abs(chi)

    print("\n[Result] peaks against Fig. 2d")
    print("   nm    paper    this work    ratio")
    for pk, pv in PAPER_PEAKS.items():
        j = int(np.argmin(np.abs(wl_nm - pk)))
        print("  %4d   %6d     %7.0f     %.2fx" % (pk, pv, plotted[j], plotted[j] / pv))

    idx, _ = find_peaks(plotted, prominence=0.05 * plotted.max())
    print("\n  peak positions found: %s"
          % "  ".join("%.0f nm" % wl_nm[i] for i in idx))

    j1550 = int(np.argmin(np.abs(wl_nm - 1550)))
    print("\n  at 1550 nm: %.0f pm/V   [paper quotes 2340 pm/V simulated, 1345 measured]"
          % plotted[j1550])
    print("  NOTE: applying the correct 1/(2pi)^2 would divide this by %.1f."
          % ((2.0 * np.pi) ** 2))

    plot_vs_paper(wl_nm, chi, FIG_DIR)


if __name__ == "__main__":
    main()

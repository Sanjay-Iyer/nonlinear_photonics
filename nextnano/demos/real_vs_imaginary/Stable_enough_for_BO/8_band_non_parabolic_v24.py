from pathlib import Path
import subprocess
import re
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from scipy.optimize import linear_sum_assignment
from scipy.signal import find_peaks

# ======================================================================================
# 8_band_non_parabolic_v24.py
#
# chi(2) OF THE COUPLED QW FROM 8-BAND k.p, WITH THE NORMALIZATION CORRECTED
#
# This is the physics answer for this structure. It is NOT an attempt to reproduce the
# published Fig. 2d; for that see 1_band_paper_replication_v1.py, which uses the
# paper's single-band model and its four undocumented conventions.
#
# The two differ in three ways that all push the same direction:
#   - single band -> 8-band k.p, so the in-plane dispersion is non-parabolic and the
#     valence states carry real HH/LH mixing
#   - the 2D k sum carries its Brillouin-zone density of states, g_s/(2 pi)^2, which
#     the paper's magnitude appears to omit; this alone is a factor of (2 pi)^2 = 39.5
#   - |chi(2)| is plotted, not |Re chi(2)|
# Net result at 1550 nm: 262 pm/V here against 2340 pm/V published, a factor of 8.9.
#
# The measured value in the paper is 1345 pm/V, 5.1x above this calculation. That is a
# real and unresolved tension, but a much smaller one than the 39.5x the normalization
# argument would otherwise imply. See chi2_replication_findings.md.
#
# TWO OF THE FOUR PEAKS ARE ARTEFACTS. Truncating the k integral at a hard edge leaves
# a step in the joint density of states, which rings as a spurious resonance at the
# transition energy reached at that edge. Only the peaks near 749 and 1494 nm are
# resonances of the structure, both from e2-h2; those near 567 and 1134 nm follow
# K_MAX_NM_INV when it moves and are labelled as such in the output and the figure.
# The same artefacts account for the published 540 and 1080 nm peaks, which the paper's
# own text never claims. classify_peaks() re-runs the integral at a reduced cutoff and
# reports the shift, so this is demonstrated on every run rather than asserted here.
#
# Changes from v23:
# - Removed the DISPERSION_MODE switch and its "subband_edge" branch. It was a
#   diagnostic for separating the genuine resonances from the cutoff artefacts, which
#   report_peak_character() now does directly, and holding the transition energies at
#   their zone-centre values is not a physical model of this structure.
# - Cutoff artefacts are identified and labelled rather than left for the reader.
# - Figure re-cut around the corrected magnitude instead of the paper's axis range.
#
# Changes from v22 (all in the k grid; the structure itself was already right):
# - K_RELATIVE_SIZE 0.15 -> 0.078. v22 solved out to 2.32 1/nm while chi(2) integrates
#   only to K_MAX_NM_INV = 1.11, so 10 of the 15 shells were computed and then thrown
#   away, and they still skewed the polynomial dispersion fit over the range that is
#   actually used. The axis maximum now lands at 1.21, just past the cutoff.
# - K_NUM_POINTS 5 -> 9. In v22 the first shell sat at 0.41 1/nm, across which e1-h1
#   climbs 78 meV, or 16 linewidths at Gamma = 5 meV. Every resonance was therefore
#   crossed inside the first, unsampled interval, and the peak heights came from the
#   interpolant rather than from data: holding those 5 shells fixed and changing only
#   the fit degree moved the cutoff artefact from 1115 nm / 585 pm/V to 1182 nm /
#   1869 pm/V. The first interval is now 0.0755 1/nm, about half a linewidth.
#   check_k_convergence.py reproduces that test.
# - Confirmed rather than changed: GRADE_WIDTH_NM stays 0.0. The paper states its
#   2340 pm/V curve is "the simulation prediction based on abrupt composition changes
#   at the interfaces"; the STEM-measured graded profile is only used later, for the
#   red points in its Fig. 4. Layer stack, Al fraction, period and temperature already
#   match the paper, so nothing else in the deck was touched.
#
# Expect peak heights to shift once this is re-run. Treat the residual magnitude gap
# against Fig. 2d as unmeasured until then. Runtime and envelope output grow about
# 3.7x with the denser grid, but only envelopes_k00000_SXYZ.dat is ever read back.
#
# Changes from v19 (carried over from v22):
# - States are identified from band character instead of the hardcoded map
#   {h1:3, h2:1, e1:5, e2:7}, which selected four hole states (one of them light hole)
#   and gave transition energies of 0.011 and 0.040 eV instead of 1.49 and 1.61 eV
# - Each Kramers doublet is reduced to one real envelope, so results no longer depend on
#   the arbitrary unitary mixture LAPACK returns within a degenerate pair
# - Envelope overlaps use the dominant band block (S for CB, HH block for holes) rather
#   than the unnormalized sum of all eight spinor components
# - Dipole origin placed at the coupled-QW centre instead of the quantum-region midpoint
# - In-plane k sum uses the correct 2D measure, d2k/(2 pi)^2 with spin degeneracy
# - Abrupt interfaces by default, and the mesh now resolves both wells rather than only
#   the 2.9 nm one
# - Dropped the ENERGY_OFFSET_EV fudge that was compensating for the wrong states
# ======================================================================================

# ======================================================================================
# GLOBAL CONFIGURATION
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

OUTPUT_DIR_KP = BASE_DIR / "Output" / "simulation_kp8band"
FIG_DIR = Path(
    r"C:\Users\mccoysa\Projects\Quantum_Wells\mqw-optimization\figures_kp8band_corrected_v24"
)

RUN_SOLVER = True

# ======================================================================================
# TEST SWITCHES
# ======================================================================================

ORIGIN_MODE = "structure_center"

# The in-plane transition energies come from the 8-band dispersion, tracked branch by
# branch across k_||. Magnitudes remain indicative rather than converged: the
# zone-centre envelope overlaps are reused at every k, and check_k_dependence.py shows
# the topmost valence state picks up ~40% light-hole character by k = 0.4 1/nm, so the
# scalar-envelope factorization Eq. 2 assumes is only strictly valid at zone centre.
# Fixing that needs k-resolved envelopes and a spinor-resolved dipole, which is the
# main outstanding item on this calculation.

# One tenth of the Brillouin zone, 2 pi / (10 a) for GaAs, matching the paper's stated
# cutoff. This sets where the two truncation artefacts land, so it is reported
# alongside them rather than buried. None means "use the full solved range".
K_MAX_NM_INV = 2.0 * np.pi / (10.0 * 0.565325)

# Fraction by which the cutoff is nudged to test which peaks follow it. Artefacts track
# E(k_max) and move; genuine resonances sit at zone-centre transitions and do not.
ARTEFACT_PROBE_FRACTION = 0.92

# ======================================================================================
# CONSTANTS
# ======================================================================================

H_PLANCK = 6.62607015e-34
C_LIGHT = 299792458.0
E_CHARGE = 1.602176634e-19

# Flipped to match Fig 1a: 2.9 nm well, 1.8 nm barrier, 7.1 nm well
WELL1_NM = 2.9
TUNNEL_BARRIER_NM = 1.8
WELL2_NM = 7.1
AL_X = 0.55

# 0.0 reproduces the ideal abrupt-interface structure behind the paper's Fig. 2d
# simulated curve. Anything above ~0.45 eats into the 1.8 nm tunnelling barrier.
GRADE_WIDTH_NM = 0.0

# The old deck refined only around well 1, leaving the 7.1 nm well (where e1 and hh1
# are 91-98% localized) on a mesh that coarsened to ~0.22 nm. Refine the whole coupled
# QW block instead. 0.02 nm keeps the total node count close to the previous run.
GRID_FINE_SPACING_NM = 0.02
GRID_COARSE_SPACING_NM = 1.0
GRID_REFINE_MARGIN_NM = 0.7

# Empirically nextnano++ puts the axis maximum at 15.478 * K_RELATIVE_SIZE 1/nm, so
# 0.078 reaches 1.21, just past the one-tenth-Brillouin-zone cutoff chi(2) uses. The
# old 0.15 ran to 2.32 and left only 5 of 15 shells inside the cutoff, while still
# letting the discarded shells bend the polynomial dispersion fit.
#
# num_points = n gives 2(n-1) intervals per positive axis, so n = 9 puts the first
# shell near 0.075 1/nm. e1-h1 rises about 2.6 meV over that first interval, half a
# linewidth, where the old grid jumped 78 meV, or 16 linewidths, in one step and left
# the whole resonance to be guessed by interpolation. Costs roughly 300 k points
# instead of 81; n = 7 is the cheaper compromise at about one linewidth per interval.
K_RELATIVE_SIZE = 0.078
K_NUM_POINTS = 9

WL_MIN_NM = 400.0
WL_MAX_NM = 1850.0
WL_POINTS = 400

# 8-band spinor basis as written by nextnano++ into envelopes_k00000_SXYZ.dat.
BASIS_LABELS = ["s1", "s2", "x1", "y1", "z1", "x2", "y2", "z2"]
CB_COMPONENTS = ("s1", "s2")
VB_COMPONENTS = ("x1", "y1", "z1", "x2", "y2", "z2")

# The deck declares crystal_zb{x_hkl=[1,0,0]} with simulate1D{}, so the growth axis is
# the crystallographic X. Heavy holes are |3/2,+-3/2> about the growth axis and
# therefore carry no X weight; light and split-off holes do.
GROWTH_AXIS_COMPONENTS = ("x1", "x2")

DOUBLET_ENERGY_TOL_EV = 1e-6
CB_MIN_S_FRACTION = 0.5
HH_MAX_GROWTH_AXIS_FRACTION = 0.05

# Each level is a Kramers doublet represented by a single envelope, so the spin
# degeneracy has to be applied explicitly in the k_|| sum.
SPIN_DEGENERACY = 2

# ======================================================================================
# Xi2.m BASELINE CONSTANTS
# ======================================================================================

# Fathi et al., which reuses this same chi(2) expression, states Gamma = 5 meV. Do not
# raise this to widen the peaks: the ~60 nm width of the Fig. 2d resonances comes from
# in-plane dispersion smearing them, not from the broadening.
XI2_GAMMA_EV = 0.005
# Eq. 2 of the paper carries Nz e^3 re,hh^2 / (6 eps0 hbar^2). Writing its numerator in
# dipole form gives e^3 re,hh^2 <h|e><e|z|e><e|h> and the hbar^2 cancels against the
# angular-frequency denominators, so the prefactor is Nz/(6 eps0). The standard three
# level result is Nz/eps0 with no 6 (Rosencher & Bois, PRB 44, 11315; Ikonic et al.,
# Physica E 4, 54), so Eq. 2 as written sits a factor of 6 below the usual convention.
# Set to 6.0 to reproduce the paper's equation verbatim, 1.0 for the standard form.
PREFACTOR_DIVISOR = 1.0

XI2_HBAR_EV_S = 6.582119569e-16
XI2_REHH_ANGSTROM = 7.51
XI2_EPS0 = 8.8541878188e-12
XI2_E_CHARGE = -1.60217663e-19
XI2_EE0 = 1.0
XI2_NZ = 1.0 / 500.0
XI2_OUTPUT_SCALE = -1.0e9

XI2_BPE = np.array([
    [0, 0, 2], [0, 0, 3], [0, 1, 2], [0, 1, 3],
    [1, 0, 2], [1, 0, 3], [1, 1, 2], [1, 1, 3]
], dtype=int)

XI2_BPH = np.array([
    [2, 2, 0], [3, 3, 0], [2, 3, 0], [2, 3, 1],
    [3, 2, 0], [3, 2, 1], [2, 2, 1], [3, 3, 1]
], dtype=int)

# ======================================================================================
# HELPERS & INPUT DECK
# ======================================================================================

def read_numeric_dat(file_path: Path) -> np.ndarray:
    if not file_path.exists():
        raise FileNotFoundError(f"Missing required file: {file_path}")
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

def print_file_head(path: Path, n: int = 8):
    print(f"\n--- HEAD: {path} ---")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            print(line.rstrip())
    print("--- END HEAD ---")

STRUCTURE_MIDDLE_NM = 18.0


def well_edges():
    """Edges of the two GaAs wells, ordered 2.9 nm then 7.1 nm as in paper Fig. 1a."""
    qw1_min = STRUCTURE_MIDDLE_NM - TUNNEL_BARRIER_NM / 2.0 - WELL1_NM
    qw1_max = STRUCTURE_MIDDLE_NM - TUNNEL_BARRIER_NM / 2.0
    qw2_min = STRUCTURE_MIDDLE_NM + TUNNEL_BARRIER_NM / 2.0
    qw2_max = STRUCTURE_MIDDLE_NM + TUNNEL_BARRIER_NM / 2.0 + WELL2_NM
    return qw1_min, qw1_max, qw2_min, qw2_max


def common_structure_and_grid():
    QW1_min, QW1_max, QW2_min, QW2_max = well_edges()

    QW1grade_min, QW1grade_max = QW1_min - GRADE_WIDTH_NM, QW1_max + GRADE_WIDTH_NM
    QW2grade_min, QW2grade_max = QW2_min - GRADE_WIDTH_NM, QW2_max + GRADE_WIDTH_NM

    # Refine across both wells and the tunnelling barrier, not just well 1.
    margin = max(GRADE_WIDTH_NM, GRID_REFINE_MARGIN_NM)
    refine_min, refine_max = QW1_min - margin, QW2_max + margin

    grid = (
        f"line{{pos=0.0 spacing={GRID_COARSE_SPACING_NM}}} "
        f"line{{pos={refine_min:.6f} spacing={GRID_FINE_SPACING_NM}}} "
        f"line{{pos={refine_max:.6f} spacing={GRID_FINE_SPACING_NM}}} "
        f"line{{pos=56.0 spacing={GRID_COARSE_SPACING_NM}}}"
    )

    if GRADE_WIDTH_NM > 0.0:
        grading = f"""
    region{{line{{x=[{QW1grade_min:.6f},{QW1_min:.6f}]}}
        ternary_linear{{name="Al(x)Ga(1-x)As" alloy_x=[{AL_X},0.0] x=[{QW1grade_min:.6f},{QW1_min:.6f}]}}}}
    region{{line{{x=[{QW1_max:.6f},{QW1grade_max:.6f}]}}
        ternary_linear{{name="Al(x)Ga(1-x)As" alloy_x=[0.0,{AL_X}] x=[{QW1_max:.6f},{QW1grade_max:.6f}]}}}}
    region{{line{{x=[{QW2grade_min:.6f},{QW2_min:.6f}]}}
        ternary_linear{{name="Al(x)Ga(1-x)As" alloy_x=[{AL_X},0.0] x=[{QW2grade_min:.6f},{QW2_min:.6f}]}}}}
    region{{line{{x=[{QW2_max:.6f},{QW2grade_max:.6f}]}}
        ternary_linear{{name="Al(x)Ga(1-x)As" alloy_x=[0.0,{AL_X}] x=[{QW2_max:.6f},{QW2grade_max:.6f}]}}}}
"""
    else:
        grading = ""

    structure = f"""
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
{grading}}}

grid{{xgrid{{{grid}}}}}
"""
    return structure

def common_header():
    return (
        'run{quantum{}} '
        'global{simulate1D{} crystal_zb{x_hkl=[1,0,0] y_hkl=[0,1,0]} substrate{name="GaAs"} temperature=300.0} '
        'contacts{fermi{name=fermi_zero bias=0}} '
        'classical{Gamma{output_bandedge{averaged=no}} HH{} LH{} SO{} output_bandedges{averaged=no}} '
        'poisson{between_fermi_levels{}} '
        'currents{recombination_model{SRH=no Auger=no radiative=no}}'
    )

def build_kp8band_deck() -> str:
    return (
        common_header()
        + common_structure_and_grid()
        + f"""
quantum{{
    region{{
        name=quantum_region
        x=[0.0,36.0]
        no_density=yes
        boundary{{x=dirichlet}}
        kp_8band{{
            num_electrons=6
            num_holes=8
            k_integration{{
                relative_size={K_RELATIVE_SIZE}
                num_points={K_NUM_POINTS}
                num_subpoints=1
                force_k0_subspace=yes
            }}
            lapack{{}}
            kp_parameters{{
                from_6band_parameters=yes
                evaluate_S=yes
                approximate_kappa=yes
                rescale_S_to=1.0
            }}
        }}
        output_states{{
            max_num=14
            all_k_points=yes
            envelopes=yes
            probabilities=yes
            spinor_composition=yes
        }}
    }}
}}
"""
    ).strip()

# ======================================================================================
# RUNNER, DISCOVERY, AND STATE DETECTION
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

def find_kp_output_dir(output_root: Path) -> Path:
    quantum_region_root = output_root / "bias_00000" / "Quantum" / "quantum_region"
    if not quantum_region_root.exists():
        raise FileNotFoundError(f"Quantum region root not found: {quantum_region_root}")
    candidates = sorted(
        sub for sub in quantum_region_root.iterdir()
        if sub.is_dir() and (sub / "energy_spectrum_k00000.dat").exists()
    )
    if not candidates:
        raise FileNotFoundError(f"No kp output directory found under {quantum_region_root}")
    if len(candidates) > 1:
        names = ", ".join(sub.name for sub in candidates)
        raise RuntimeError(
            f"Ambiguous kp output under {quantum_region_root}: found {names}. "
            "Clear the output directory and re-run so exactly one solver result is present."
        )
    return candidates[0]

# ======================================================================================
# DATA LOADING, TRACKING, and MATRICES
# ======================================================================================

def load_kp_dataset(output_root: Path):
    kp_dir = find_kp_output_dir(output_root)
    k_data = read_numeric_dat(kp_dir / "k_points.txt")
    k_par = np.sqrt(k_data[:, 2]**2 + k_data[:, 3]**2)
    energy_files = sorted(
        kp_dir.glob("energy_spectrum_k*.dat"),
        key=lambda p: int(re.search(r"k(\d+)", p.name).group(1))
    )
    spectra = np.array([read_numeric_dat(ef)[:, 1] for ef in energy_files])
    return {"kp_dir": kp_dir, "k_par": k_par, "spectra": spectra}

def load_zone_center_spinors(kp_dir: Path):
    efile = kp_dir / "envelopes_k00000_SXYZ.dat"
    with open(efile, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip().split()

    raw = np.loadtxt(efile, skiprows=1)
    x_nm = raw[:, 0]
    colmap = {name: i for i, name in enumerate(header)}

    nstates = len(read_numeric_dat(kp_dir / "energy_spectrum_k00000.dat"))
    spinors = {}
    for n in range(1, nstates + 1):
        spinors[n] = {
            b: raw[:, colmap[f"Psi_{n}_{b}_real[nm^-1/2]"]]
            + 1j * raw[:, colmap[f"Psi_{n}_{b}_imag[nm^-1/2]"]]
            for b in BASIS_LABELS
        }
    return x_nm, spinors

def spinor_fractions(x_nm, psi):
    """Fraction of the norm carried by each basis component."""
    weights = {b: np.trapezoid(np.abs(psi[b])**2, x_nm) for b in BASIS_LABELS}
    total = sum(weights.values())
    return {b: w / total for b, w in weights.items()}

def group_kramers_doublets(energies):
    """Group the sorted spectrum into degenerate multiplets of 1-based state numbers."""
    doublets, start = [], 0
    for i in range(1, len(energies) + 1):
        if i == len(energies) or energies[i] - energies[start] > DOUBLET_ENERGY_TOL_EV:
            doublets.append(tuple(range(start + 1, i + 1)))
            start = i
    return doublets

def identify_states(kp_dir: Path):
    """Locate e1, e2, hh1 and hh2 from band character rather than hardcoded indices.

    nextnano++ sorts the spectrum in ascending energy and treats the lowest num_holes
    bands as valence and the rest as conduction, so conduction and valence are split at
    the largest gap. Within the valence block, heavy holes are separated from light and
    split-off holes by their vanishing weight along the growth axis.
    """
    energies = read_numeric_dat(kp_dir / "energy_spectrum_k00000.dat")[:, 1]
    x_nm, spinors = load_zone_center_spinors(kp_dir)

    doublets = group_kramers_doublets(energies)
    split = int(np.argmax(np.diff(energies))) + 1  # first conduction state, 0-based

    print("\n[States] Zone-centre spectrum")
    print("  states        E[eV]     P_S    P_growth    character")

    levels = []
    for members in doublets:
        fracs = [spinor_fractions(x_nm, spinors[n]) for n in members]
        p_s = float(np.mean([sum(f[b] for b in CB_COMPONENTS) for f in fracs]))
        p_axis = float(np.mean([sum(f[b] for b in GROWTH_AXIS_COMPONENTS) for f in fracs]))
        energy = float(energies[members[0] - 1])

        if members[0] - 1 >= split and p_s >= CB_MIN_S_FRACTION:
            character = "CB"
        elif members[0] - 1 < split and p_axis < HH_MAX_GROWTH_AXIS_FRACTION:
            character = "HH"
        elif members[0] - 1 < split:
            character = "LH/SO"
        else:
            character = "other"

        levels.append({"members": members, "energy": energy, "character": character})
        print("  %-12s %9.5f  %6.3f    %6.3f     %s"
              % (",".join(str(n) for n in members), energy, p_s, p_axis, character))

    cb = sorted([lv for lv in levels if lv["character"] == "CB"], key=lambda lv: lv["energy"])
    hh = sorted([lv for lv in levels if lv["character"] == "HH"],
                key=lambda lv: lv["energy"], reverse=True)

    if len(cb) < 2:
        raise RuntimeError(f"Need two conduction doublets, found {len(cb)}. Raise num_electrons.")
    if len(hh) < 2:
        raise RuntimeError(f"Need two heavy-hole doublets, found {len(hh)}. Raise num_holes.")

    roles = {"e1": cb[0], "e2": cb[1], "h1": hh[0], "h2": hh[1]}

    print("\n[States] Selected roles")
    for key in ("e1", "e2", "h1", "h2"):
        lv = roles[key]
        print("  %-3s = states %-8s E = %.5f eV"
              % (key, ",".join(str(n) for n in lv["members"]), lv["energy"]))

    for electron, hole, target in (("e1", "h1", 1.49), ("e2", "h2", 1.62)):
        delta = roles[electron]["energy"] - roles[hole]["energy"]
        print("  %s-%s = %.4f eV -> %.0f nm (1w), %.0f nm (2w)   [paper %.2f eV]"
              % (electron, hole, delta, 1e9 * H_PLANCK * C_LIGHT / (delta * E_CHARGE),
                 2e9 * H_PLANCK * C_LIGHT / (delta * E_CHARGE), target))
        if abs(delta - target) > 0.05:
            print("    WARNING: %.0f meV from the paper value; check the structure definition."
                  % (1000 * abs(delta - target)))

    return {"roles": roles, "x_nm": x_nm, "spinors": spinors}

def extract_envelope(x_nm, spinors, members, components):
    """Reduce a Kramers doublet to the single real envelope of its dominant band block.

    LAPACK returns an arbitrary unitary mixture within a degenerate doublet, so picking
    one member is basis dependent. Every non-negligible component of both members is
    however the same real function up to a complex constant, so taking the largest one
    and dividing out its global phase gives a basis-independent envelope. The overall
    sign is arbitrary but cancels: each state appears exactly twice in every chi(2) term.
    """
    best, best_norm = None, 0.0
    for n in members:
        for b in components:
            f = spinors[n][b]
            norm = np.trapezoid(np.abs(f)**2, x_nm)
            if norm > best_norm:
                best, best_norm = f, norm

    if best is None or best_norm <= 0.0:
        raise RuntimeError(f"States {members} carry no weight in components {components}")

    phase = np.angle(best[np.argmax(np.abs(best))])
    f = best * np.exp(-1j * phase)

    residual = np.trapezoid(f.imag**2, x_nm) / best_norm
    if residual > 1e-6:
        raise RuntimeError(
            f"States {members} are not real after removing a global phase "
            f"(residual {residual:.2e}); the envelope reduction does not apply."
        )

    f = f.real
    return f / np.sqrt(np.trapezoid(f**2, x_nm))

def dipole_origin_nm(mode: str, x_nm):
    if mode == "structure_center":
        qw1_min, _, _, qw2_max = well_edges()
        return 0.5 * (qw1_min + qw2_max)
    elif mode == "midpoint_box":
        return 0.5 * (np.min(x_nm) + np.max(x_nm))
    elif mode == "mean_center":
        return float(np.mean(x_nm))
    else:
        raise ValueError(f"Unknown ORIGIN_MODE={mode!r}")

def build_numerator_matrices(states, origin_mode: str = ORIGIN_MODE):
    """Envelope overlaps and dipoles in the [e1, e2, h1, h2] ordering used by Eq. 2."""
    x_nm, spinors, roles = states["x_nm"], states["spinors"], states["roles"]

    envelopes = {
        key: extract_envelope(
            x_nm, spinors, roles[key]["members"],
            CB_COMPONENTS if key.startswith("e") else VB_COMPONENTS,
        )
        for key in ("e1", "e2", "h1", "h2")
    }

    z_nm = x_nm - dipole_origin_nm(origin_mode, x_nm)

    state_order = ["e1", "e2", "h1", "h2"]
    overlap = np.zeros((4, 4))
    dipole = np.zeros((4, 4))
    for a, ka in enumerate(state_order):
        for b, kb in enumerate(state_order):
            overlap[a, b] = np.trapezoid(envelopes[ka] * envelopes[kb], x_nm)
            dipole[a, b] = np.trapezoid(envelopes[ka] * z_nm * envelopes[kb], x_nm)

    return {"overlap": overlap, "dipole": dipole, "envelopes": envelopes}

def track_selected_branches(dataset, states):
    """Follow each tracked level across k_|| by nearest-energy continuity.

    Heavy- and light-hole branches cross away from zone centre, so states cannot be
    followed by index. Both members of each doublet are tracked and averaged, which
    gives the spin-averaged subband dispersion the single-band formalism expects.

    nextnano++ writes k_points.txt as a 2D grid scan rather than in order of |k|: the
    first non-zero entry is at the *largest* |k|. Continuity tracking therefore has to
    walk the points in order of increasing |k|, not in file order, or the very first
    step jumps the whole way across the Brillouin zone and the assignment is arbitrary.
    """
    spectra = dataset["spectra"]
    k_par = dataset["k_par"]
    roles = states["roles"]
    Nk, Nstates = spectra.shape

    if len(k_par) != Nk:
        raise RuntimeError(f"{Nk} spectra but {len(k_par)} k points")

    order = np.argsort(k_par, kind="stable")
    if k_par[order[0]] > 1e-9:
        raise RuntimeError("No zone-centre k point; state roles are seeded at k=0.")

    keys = ["e1", "e2", "h1", "h2"]
    members = {key: [n - 1 for n in roles[key]["members"]] for key in keys}
    is_electron = {key: key.startswith("e") for key in keys}

    # Flat list of tracked member states, so each doublet contributes both branches.
    tracked = [(key, idx) for key in keys for idx in members[key]]
    rows_of = {
        electron: [i for i, (key, _) in enumerate(tracked) if is_electron[key] == electron]
        for electron in (True, False)
    }

    k0 = order[0]
    per_member = np.zeros((len(tracked), Nk))
    prev = np.array([spectra[k0][idx] for _, idx in tracked])
    per_member[:, k0] = prev

    for ik in order[1:]:
        Ek = spectra[ik]
        split = int(np.argmax(np.diff(Ek))) + 1
        pools = {True: list(range(split, Nstates)), False: list(range(0, split))}

        for electron in (True, False):
            rows, pool = rows_of[electron], pools[electron]
            if len(pool) < len(rows):
                raise RuntimeError(
                    f"k-point {ik}: {len(pool)} states available for "
                    f"{'electrons' if electron else 'holes'}, need {len(rows)}."
                )
            cost = np.abs(prev[rows][:, None] - Ek[pool][None, :])
            r, c = linear_sum_assignment(cost)
            for ri, ci in zip(r, c):
                row = rows[ri]
                per_member[row, ik] = Ek[pool[ci]]
                prev[row] = Ek[pool[ci]]

    branches = {}
    for key in keys:
        rows = [i for i, (k, _) in enumerate(tracked) if k == key]
        branches[key] = per_member[rows].mean(axis=0)
    return branches

def shell_average_dispersion(dataset, branches, decimals=6):
    k_par = dataset["k_par"]
    shell_key = np.round(k_par, decimals)
    uniq = np.unique(shell_key)
    shell_k, shell_E = [], {key: [] for key in branches}

    for uk in uniq:
        idx = np.where(shell_key == uk)[0]
        shell_k.append(np.mean(k_par[idx]))
        for b in branches:
            shell_E[b].append(np.mean(branches[b][idx]))

    shell_k = np.array(shell_k)
    order = np.argsort(shell_k)
    return shell_k[order], {b: np.array(v)[order] for b, v in shell_E.items()}

def build_dispersion_interpolators(shell_k, shell_E, degree):
    """Fit each branch as a polynomial in k^2, so E(k_par) comes out even in k.

    Fitting in k instead lets np.polyfit use odd powers, which puts a linear term at
    zone centre and gives E a cusp there, when the in-plane dispersion must satisfy
    dE/dk = 0 at k = 0. It is not a cosmetic point: only |k| < 0.086 1/nm is within
    Gamma of resonance, and the linear coefficient the free fit chose, about
    0.07 eV nm at degree 6, detunes the transition by ~6 meV across exactly that disc.
    A resonance was therefore being damped by the choice of fit basis. See
    check_even_fit.py; removing it lifts the peaks by 10-20%.
    """
    out = {}
    for key, vals in shell_E.items():
        coeffs = np.polyfit(shell_k**2, vals, deg=degree)
        out[key] = (lambda c: lambda k: np.polyval(c, np.asarray(k, dtype=float) ** 2))(coeffs)
    return out

# ======================================================================================
# INTEGRATION ENGINE - DENOMINATOR FIX
# ======================================================================================

def xi2_integrate_complex(integrand, krng, num_points=5000):
    k_arr = np.linspace(0.0, krng, num_points)
    y_arr = integrand(k_arr)
    return np.trapezoid(y_arr, k_arr)

# chi(2) needs a volume density: Nz [m^-1] times the in-plane state density
# (1/A) sum_k|| = SPIN_DEGENERACY / (2 pi)^2 * integral d2k, and d2k = 2 pi k dk.
K_MEASURE = SPIN_DEGENERACY / (2.0 * np.pi)


# ======================================================================================
# UPDATED INTEGRATION ENGINE & MODEL CALCULATIONS
# ======================================================================================

def perform_integration(hw_ev, overlap, dipole, E_interp, apre, krng):
    chi_total = np.zeros_like(hw_ev, dtype=np.complex128)
    idx_to_key = {0: "e1", 1: "e2", 2: "h1", 3: "h2"}

    for iw, w1 in enumerate(hw_ev):
        w2 = w1
        electron_sum = 0.0 + 0.0j
        hole_sum = 0.0 + 0.0j

        for e_a, e_b, h_c in XI2_BPE:
            key_ea = idx_to_key[e_a]
            key_eb = idx_to_key[e_b]
            key_hc = idx_to_key[h_c]

            # Dipole is in nm, so we multiply by 1e-9 to convert to meters
            Ae = apre * overlap[h_c, e_a] * (dipole[e_a, e_b] * 1e-9) * overlap[e_b, h_c]

            def electron_integrand(kval, Ae=Ae, key_ea=key_ea, key_eb=key_eb, key_hc=key_hc):
                E13 = E_interp[key_ea](kval) - E_interp[key_hc](kval)
                E23 = E_interp[key_eb](kval) - E_interp[key_hc](kval)
                denom = (
                    (E13 - w1 - w2 + 1j * XI2_GAMMA_EV)
                    * (E23 - w1 + 1j * XI2_GAMMA_EV)
                )
                return Ae * K_MEASURE * kval / denom

            electron_sum += xi2_integrate_complex(electron_integrand, krng)

        for h_a, h_b, e_c in XI2_BPH:
            key_ha = idx_to_key[h_a]
            key_hb = idx_to_key[h_b]
            key_ec = idx_to_key[e_c]

            # Dipole is in nm, multiply by 1e-9 to convert to meters
            Ah = apre * overlap[e_c, h_a] * (dipole[h_a, h_b] * 1e-9) * overlap[h_b, e_c]

            def hole_integrand(kval, Ah=Ah, key_ha=key_ha, key_hb=key_hb, key_ec=key_ec):
                H13 = E_interp[key_ec](kval) - E_interp[key_ha](kval)
                H23 = E_interp[key_ec](kval) - E_interp[key_hb](kval)
                denom = (
                    (H13 - w1 - w2 + 1j * XI2_GAMMA_EV)
                    * (H23 - w1 + 1j * XI2_GAMMA_EV)
                )
                return -Ah * K_MEASURE * kval / denom

            hole_sum += xi2_integrate_complex(hole_integrand, krng)

        # k-space integration was in nm^-2, so multiply by 1e18 to convert to m^-2.
        # Then multiply by 1e12 to convert output from m/V to pm/V.
        chi_total[iw] = (electron_sum + hole_sum) * 1e18 * 1e12

    return chi_total

def report_matrices(num, label):
    state_order = ["e1", "e2", "h1", "h2"]
    print(f"\n[Matrices] origin = {label}")
    print("  diagonal dipoles [nm]: " + "  ".join(
        "<%s|z|%s> = %+.3f" % (k, k, num["dipole"][i, i]) for i, k in enumerate(state_order)))
    print("  envelope overlaps:     " + "  ".join(
        "<%s|%s> = %.3f" % (h, e, num["overlap"][state_order.index(h), state_order.index(e)])
        for h in ("h1", "h2") for e in ("e1", "e2")))

def calculate_chi2_models(dataset, states, branches, report=True, k_max=None):
    num = build_numerator_matrices(states, ORIGIN_MODE)
    overlap, dipole = num["overlap"], num["dipole"]
    if report:
        report_matrices(num, ORIGIN_MODE)

    shell_k, shell_E = shell_average_dispersion(dataset, branches)

    print("\n[Dispersion] e1-h1 sweeps %.4f -> %.4f eV over |k| <= %.3f 1/nm"
          % (shell_E["e1"][0] - shell_E["h1"][0],
             shell_E["e1"][-1] - shell_E["h1"][-1], shell_k.max()))

    E_interp_poly6 = build_dispersion_interpolators(shell_k, shell_E, degree=6)
    E_interp_poly2 = build_dispersion_interpolators(shell_k, shell_E, degree=2)
    E_interp_raw = {key: PchipInterpolator(shell_k, shell_E[key]) for key in shell_E}

    # Strict SI Conversions
    E_CHARGE_C = 1.602176634e-19
    EPS0 = 8.8541878188e-12
    REHH_M = 7.51e-10  # 7.51 Angstroms to meters
    
    # Nz = 1 / L_period. The paper's text says "each period is 20 nm" but then lists
    # 10 nm of QW, a 1.8 nm tunnelling barrier and an 18.2 nm period barrier, and the
    # Fig. 1a caption says 30 nm, so 30 is the self-consistent value.
    NZ_M_INV = 1.0 / (30.0 * 1e-9)

    # Because our denominator uses eV^2, (E_CHARGE_C)^2 cancels from the e^3 in the numerator,
    # leaving us with a single E_CHARGE_C on top.
    apre = (NZ_M_INV * E_CHARGE_C * (REHH_M**2)) / (PREFACTOR_DIVISOR * EPS0)

    requested = K_MAX_NM_INV if k_max is None else k_max
    krng = float(np.max(shell_k))
    if requested is not None:
        if requested > krng:
            raise ValueError(
                f"k cutoff {requested:.3f} exceeds the solved range {krng:.3f} 1/nm; "
                "raise K_RELATIVE_SIZE and re-run the solver.")
        krng = float(requested)
    e_cut = float(E_interp_poly6["e1"](krng) - E_interp_poly6["h1"](krng))
    print("[Dispersion] integrating to |k| <= %.3f 1/nm, where e1-h1 = %.3f eV "
          "-> cutoff artefacts near %.0f nm (2w) and %.0f nm (1w)"
          % (krng, e_cut,
             2e9 * H_PLANCK * C_LIGHT / (E_CHARGE * e_cut),
             1e9 * H_PLANCK * C_LIGHT / (E_CHARGE * e_cut)))
    wl_nm = np.linspace(WL_MIN_NM, WL_MAX_NM, WL_POINTS)
    hw_ev = (H_PLANCK * C_LIGHT) / (wl_nm * 1e-9 * E_CHARGE)

    # The diagonal intersubband elements dominate chi(2) and are origin dependent, so
    # the truncated four-state sum does not fully cancel a shift of the z origin.
    if report:
        hw_1550 = np.array([(H_PLANCK * C_LIGHT) / (1550.0e-9 * E_CHARGE)])
        print("\n[Origin check] |chi(2)| at 1550 nm fundamental, 6th-order dispersion")
        for origin in ("structure_center", "midpoint_box"):
            alt = build_numerator_matrices(states, origin)
            value = perform_integration(
                hw_1550, alt["overlap"], alt["dipole"], E_interp_poly6, apre, krng)
            print("  %-18s z0 = %6.2f nm -> %8.1f pm/V"
                  % (origin, dipole_origin_nm(origin, states["x_nm"]), abs(value[0])))

    print("\n[Integrating] Computing 6th-Order (Smooth Non-Parabolic)...")
    chi_poly6 = perform_integration(hw_ev, overlap, dipole, E_interp_poly6, apre, krng)

    print("[Integrating] Computing 2nd-Order (Quadratic)...")
    chi_poly2 = perform_integration(hw_ev, overlap, dipole, E_interp_poly2, apre, krng)

    print("[Integrating] Computing Raw Numerical (Full Physics)...")
    chi_raw = perform_integration(hw_ev, overlap, dipole, E_interp_raw, apre, krng)

    zone_centre = {
        "e1-h1": float(E_interp_poly6["e1"](0.0) - E_interp_poly6["h1"](0.0)),
        "e2-h2": float(E_interp_poly6["e2"](0.0) - E_interp_poly6["h2"](0.0)),
    }
    return {"wl_nm": wl_nm, "chi6": chi_poly6, "chi2nd": chi_poly2, "chiraw": chi_raw,
            "k_max": krng, "E_cut": e_cut, "zone_centre": zone_centre}


# ======================================================================================
# PLOTTING
# ======================================================================================

def classify_peaks(base, probe):
    """Separate genuine resonances from k-cutoff artefacts by moving the cutoff.

    A resonance sits where a zone-centre transition matches w or 2w and does not care
    where the k integral stops. An artefact sits at the transition energy reached at
    the cutoff, so shrinking the cutoff blue-shifts it by a predictable amount. Peaks
    are matched between the two runs by nearest wavelength and reported with how far
    they moved, so the classification is visible rather than asserted.
    """
    wl = base["wl_nm"]
    mag = np.abs(base["chi6"])
    mag_p = np.abs(probe["chi6"])

    idx, _ = find_peaks(mag, prominence=0.05 * mag.max())
    idx_p, _ = find_peaks(mag_p, prominence=0.05 * mag_p.max())
    wl_p = wl[idx_p]

    # A 2w resonance appears at twice the wavelength of the transition it comes from.
    expected = {}
    for name, energy in base["zone_centre"].items():
        lam = 1e9 * H_PLANCK * C_LIGHT / (E_CHARGE * energy)
        expected[name + " (1w)"] = lam
        expected[name + " (2w)"] = 2 * lam

    out = []
    for i in idx:
        lam = wl[i]
        shift = wl_p[np.argmin(np.abs(wl_p - lam))] - lam if len(wl_p) else np.nan
        label, best = "unassigned", 1e9
        for name, ref in expected.items():
            if abs(ref - lam) < best:
                label, best = name, abs(ref - lam)
        # Anything that follows the cutoff by more than a linewidth is an artefact.
        kind = "CUTOFF ARTEFACT" if abs(shift) > 8.0 else "resonance"
        out.append({"wl": lam, "value": mag[i], "shift": shift,
                    "kind": kind, "assign": label if best < 40 else "-"})
    return out


def report_peak_character(peaks, base):
    print("\n[Peaks] |chi(2)| maxima, and what happens when the k cutoff is cut to %.0f%%"
          % (100 * ARTEFACT_PROBE_FRACTION))
    print("    nm     pm/V     moves by    verdict            nearest transition")
    for p in peaks:
        print("  %5.0f   %7.0f   %+7.0f nm    %-17s  %s"
              % (p["wl"], p["value"], p["shift"], p["kind"], p["assign"]))
    print("\n  Zone-centre transitions: " + ",  ".join(
        "%s = %.4f eV (%.0f nm 1w, %.0f nm 2w)"
        % (n, e, 1e9 * H_PLANCK * C_LIGHT / (E_CHARGE * e),
           2e9 * H_PLANCK * C_LIGHT / (E_CHARGE * e))
        for n, e in base["zone_centre"].items()))


def plot_chi2_v24(base, peaks, save_dir: Path):
    wl = base["wl_nm"]
    mag = np.abs(base["chi6"])

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(14.5, 5.2), dpi=200)

    for ax in (ax_lin, ax_log):
        ax.plot(wl, mag, color="navy", lw=2.0, label=r"$|\chi^{(2)}|$, 8-band, corrected")
        ax.plot(wl, np.abs(base["chi2nd"]), color="navy", lw=1.0, ls=":", alpha=0.55,
                label="2nd-order (quadratic) dispersion fit")
        ax.plot(wl, np.abs(base["chiraw"]), color="navy", lw=1.0, ls="-.", alpha=0.55,
                label="raw numerical dispersion")
        ax.set_xlabel("Fundamental wavelength (nm)")
        ax.set_ylabel(r"$|\chi^{(2)}|$ (pm/V)")
        ax.grid(True, ls=":", alpha=0.6)

    # Headroom so the labels sit above the curve rather than over the title.
    ax_lin.set_ylim(0, mag.max() * 1.32)
    for p in peaks:
        colour = "grey" if p["kind"].startswith("CUTOFF") else "navy"
        text = "cutoff artefact" if p["kind"].startswith("CUTOFF") else "resonance"
        ax_lin.annotate(text, xy=(p["wl"], p["value"]),
                        xytext=(p["wl"], p["value"] + 0.10 * mag.max()),
                        fontsize=7, ha="center", color=colour,
                        arrowprops=dict(arrowstyle="-", color=colour, lw=0.7))

    ax_lin.set_title("Linear scale")
    ax_lin.legend(fontsize=8)
    ax_log.set_yscale("log")
    ax_log.set_title("Log scale")
    ax_log.legend(fontsize=8)

    fig.suptitle("Coupled QW $\\chi^{(2)}$ from 8-band k$\\cdot$p, corrected normalization")
    plt.tight_layout()
    save_dir.mkdir(parents=True, exist_ok=True)
    out = save_dir / "chi2_8band_corrected.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[Plot] wrote {out}")


# ======================================================================================
# MAIN
# ======================================================================================

def main():
    print("=" * 80)
    print("8-band k.p chi(2), corrected normalization")
    print("  k measure     : g_s/(2 pi)^2, the Brillouin-zone density of states")
    print("  prefactor     : standard form, no 1/6 (PREFACTOR_DIVISOR = %.1f)" % PREFACTOR_DIVISOR)
    print("  plotted       : |chi(2)|")
    print("  k cutoff      : %.4f 1/nm (one tenth of the Brillouin zone)" % K_MAX_NM_INV)
    print("=" * 80)

    if RUN_SOLVER:
        run_nextnano(build_kp8band_deck(), "simulation_kp8band.nnp", OUTPUT_DIR_KP)

    dataset = load_kp_dataset(OUTPUT_DIR_KP)
    states = identify_states(dataset["kp_dir"])
    branches = track_selected_branches(dataset, states)

    base = calculate_chi2_models(dataset, states, branches, report=True)

    print("\n[Artefact probe] re-integrating with the cutoff at %.0f%% to see which "
          "peaks follow it" % (100 * ARTEFACT_PROBE_FRACTION))
    probe = calculate_chi2_models(dataset, states, branches, report=False,
                                  k_max=ARTEFACT_PROBE_FRACTION * K_MAX_NM_INV)

    peaks = classify_peaks(base, probe)
    report_peak_character(peaks, base)

    wl, mag = base["wl_nm"], np.abs(base["chi6"])
    j = int(np.argmin(np.abs(wl - 1550)))
    print("\n[Result] |chi(2)| at 1550 nm = %.0f pm/V" % mag[j])
    print("  paper, simulated : 2340 pm/V   (%.1fx this value)" % (2340 / mag[j]))
    print("  paper, measured  : 1345 pm/V   (%.1fx this value)" % (1345 / mag[j]))
    print("  Most of the simulated gap is the (2 pi)^2 = 39.5 k-space normalization")
    print("  discussed in chi2_replication_findings.md; the gap to the measured value")
    print("  is the part that is genuinely unresolved.")

    plot_chi2_v24(base, peaks, FIG_DIR)

if __name__ == "__main__":
    main()

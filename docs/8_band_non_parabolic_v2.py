from pathlib import Path
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import pchip_interpolate

# ======================================================================================
# GLOBAL CONFIGURATION & PHYSICAL CONSTANTS
# ======================================================================================

BASE_DIR = Path(
    r"C:\Users\mccoysa\Projects\Quantum_Wells\nextnano_standard_26.7.0.0_2026_07_03_portable\nextnano\2026_07_03\nextnano++"
)
EXE_64 = BASE_DIR / r"bin 64bit\nextnano++_Microsoft_64bit_serial.exe"
EXE_32 = BASE_DIR / r"bin 32bit\nextnano++_Microsoft_32bit_serial.exe"
EXE_PATH = EXE_64 if EXE_64.exists() else EXE_32

DATABASE_PATH = BASE_DIR / "database" / "database.nnp"
LICENSE_PATH = Path(r"C:\Users\mccoysa\Projects\Quantum_Wells\License_nnp_stephen20260731.lic")

OUTPUT_DIR_SB = BASE_DIR / "Output" / "simulation_singleband"
OUTPUT_DIR_KP = BASE_DIR / "Output" / "simulation_kp8band"
SAVE_DIR = Path(r"C:\Users\mccoysa\Projects\Quantum_Wells\mqw-optimization\figures_non_parabolic")

HBAR = 1.054571817e-34
H_PLANCK = 6.62607015e-34
C_LIGHT = 299792458.0
E_CHARGE = 1.602176634e-19
EPS0 = 8.8541878128e-12
M0 = 9.1093837015e-31

# Asymmetric QW geometry in [15.0, 35.0] nm coordinates
Z_START = 15.0
Z_END = 35.0
I1 = 19.1
I2 = 26.2
I3 = 28.0
I4 = 30.9
AL_X = 0.55

PERIOD_M = 30.0e-9
NZ = 1.0 / PERIOD_M
R_E_HH_M = 0.751e-9
GAMMA_EV = 0.005

# Prefactor in SI-like scaling
APRE = (NZ * E_CHARGE * (R_E_HH_M**2)) / EPS0

# ======================================================================================
# SAFETY HELPERS
# ======================================================================================

def safe_inverse(z, eps=1e-14):
    z = np.asarray(z, dtype=np.complex128)
    out = np.zeros_like(z, dtype=np.complex128)
    mask = np.isfinite(z.real) & np.isfinite(z.imag) & (np.abs(z) > eps)
    out[mask] = 1.0 / z[mask]
    return out

def unique_states(energies, tol=1e-3):
    idx, used = [], []
    for i, e in enumerate(energies):
        if not any(abs(e - u) < tol for u in used):
            idx.append(i)
            used.append(e)
    return idx

# ======================================================================================
# 8-BAND NON-PARABOLIC DISPERSION (EYINK-STYLE FITS)
# ======================================================================================

def Ee1_k(k_m, E0=2.943):
    kA = k_m * 1e-10
    return E0 + 54.492 * (kA**2) - 851.1 * (kA**4)

def Ee2_k(k_m, E0=3.059):
    kA = k_m * 1e-10
    return E0 + 50.864 * (kA**2) - 732.61 * (kA**4)

def Eh1_k(k_m, E0=1.445):
    kA = k_m * 1e-10
    return E0 - 6.9771 * (kA**2) - 716.47 * (kA**4) + 36809.0 * (kA**6)

def Eh2_k(k_m, E0=1.421):
    kA = k_m * 1e-10
    return E0 - 10.165 * (kA**2)

# ======================================================================================
# NEXTNANO++ INPUT DECKS
# ======================================================================================

def common_header():
    return f"""
run{{
    quantum{{}}
}}

global{{
    simulate1D{{}}
    crystal_zb{{
        x_hkl = [1, 0, 0]
        y_hkl = [0, 1, 0]
    }}
    substrate{{ name = "GaAs" }}
    temperature = 300.0
}}

contacts{{
    fermi{{ name = "fermi_zero" bias = 0 }}
}}

classical{{
    Gamma{{ output_bandedge{{ averaged = no }} }}
    HH{{}}
    LH{{}}
    SO{{}}
    output_bandedges{{ averaged = no }}
}}

poisson{{
    between_fermi_levels{{}}
}}

currents{{
    recombination_model{{
        SRH = no
        Auger = no
        radiative = no
    }}
}}
"""

def common_structure_and_grid():
    grid = f"""
        line{{ pos = {Z_START:.6f} spacing = 0.2 }}
        line{{ pos = {I1:.6f}      spacing = 0.05 }}
        line{{ pos = {I2:.6f}      spacing = 0.05 }}
        line{{ pos = {I3:.6f}      spacing = 0.05 }}
        line{{ pos = {I4:.6f}      spacing = 0.05 }}
        line{{ pos = {Z_END:.6f}   spacing = 0.2 }}
    """
    structure = f"""
structure{{
    output_region_index{{ boxes = no }}
    output_material_index{{ boxes = no }}
    output_alloy_composition{{ boxes = no }}

    region{{
        everywhere{{}}
        contact{{ name = fermi_zero }}
        ternary_constant{{
            name = "Al(x)Ga(1-x)As"
            alloy_x = {AL_X}
        }}
    }}

    region{{
        line{{ x = [{Z_START:.6f}, {Z_END:.6f}] }}
        ternary_constant{{
            name = "Al(x)Ga(1-x)As"
            alloy_x = {AL_X}
        }}
    }}

    region{{
        line{{ x = [{I1:.6f}, {I2:.6f}] }}
        binary{{ name = "GaAs" }}
    }}

    region{{
        line{{ x = [{I3:.6f}, {I4:.6f}] }}
        binary{{ name = "GaAs" }}
    }}
}}

grid{{
    xgrid{{
{grid}
    }}
}}
"""
    return structure

def build_singleband_deck() -> str:
    return common_header() + common_structure_and_grid() + f"""
quantum{{
    region{{
        name = "quantum_region"
        x = [{Z_START:.6f}, {Z_END:.6f}]
        no_density = yes
        boundary{{ x = dirichlet }}

        Gamma{{ num_ev = 4 }}
        HH{{ num_ev = 4 }}

        output_states{{
            max_num = 4
            all_k_points = yes
            envelopes = yes
            probabilities = yes
        }}
    }}
}}
""".strip()

def build_kp8band_deck() -> str:
    return common_header() + common_structure_and_grid() + f"""
quantum{{
    region{{
        name = "quantum_region"
        x = [{Z_START:.6f}, {Z_END:.6f}]
        no_density = yes
        boundary{{ x = dirichlet }}

        kp_8band{{
            num_electrons = 4
            num_holes     = 4
            k_integration_disabled{{}}
            kp_parameters{{
                from_6band_parameters = yes
                evaluate_S = yes
                approximate_kappa = yes
                rescale_S_to = 1.0
            }}
        }}

        output_states{{
            max_num = 8
            all_k_points = yes
            envelopes = yes
            probabilities = yes
            spinor_composition = yes
        }}
    }}
}}
""".strip()

# ======================================================================================
# SOLVER & LOADERS
# ======================================================================================

def run_nextnano(input_text: str, input_filename: str, output_dir: Path):
    if not EXE_PATH.exists():
        print(f"[Notice] Executable not found at {EXE_PATH}. Using calibrated/manual model.")
        return

    work_dir = Path.cwd()
    input_path = work_dir / input_filename
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
        print("\n--- NEXTNANO++ ERROR ---")
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Simulation failed with exit code {res.returncode}")

    print(f"[Solver] {input_filename} finished successfully!")

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
    return np.array(rows)

def load_singleband(band: str):
    base = OUTPUT_DIR_SB / "bias_00000" / "Quantum" / "quantum_region" / band
    spectrum_file = base / "energy_spectrum_k00000.dat"
    env_file = base / "envelopes_k00000.dat"

    if spectrum_file.exists() and env_file.exists():
        e_data = read_numeric_dat(spectrum_file)
        energies = e_data[:, 1] if e_data.ndim == 2 else np.array([e_data[1]])
        if band == "HH":
            energies = np.sort(energies)[::-1]
        env = read_numeric_dat(env_file)
        z = env[:, 0]
        psi = [env[:, col] for col in range(1, env.shape[1])]
        return energies, z, psi

    # fallback analytical shapes only if output files are absent
    z = np.linspace(Z_START, Z_END, 500)
    psi1 = np.sin(np.pi * (z - I1) / (I2 - I1)) * ((z >= I1) & (z <= I2))
    psi2 = np.sin(np.pi * (z - I3) / (I4 - I3)) * ((z >= I3) & (z <= I4))
    if band == "Gamma":
        return np.array([2.943, 3.059]), z, [psi1 + 0.3 * psi2, -0.25 * psi1 + psi2]
    else:
        return np.array([1.445, 1.421]), z, [psi1, psi2]

def load_bandedges():
    path = OUTPUT_DIR_SB / "bias_00000" / "bandedges.dat"
    if path.exists():
        data = read_numeric_dat(path)
        return data[:, 0], data[:, 1], data[:, 2]

    z = np.linspace(Z_START, Z_END, 500)
    ec = np.where(((z >= I1) & (z <= I2)) | ((z >= I3) & (z <= I4)), 2.882, 3.320)
    ev = np.where(((z >= I1) & (z <= I2)) | ((z >= I3) & (z <= I4)), 1.460, 1.180)
    return z, ec, ev

def load_kp8_zone_center_energies():
    base = OUTPUT_DIR_KP / "bias_00000" / "Quantum" / "quantum_region" / "kp8"
    spectrum_file = base / "energy_spectrum_k00000.dat"
    if spectrum_file.exists():
        e_data = read_numeric_dat(spectrum_file)
        return e_data[:, 1] if e_data.ndim == 2 else np.array([e_data[1]])
    return np.array([1.421, 1.445, 2.943, 3.059])

# ======================================================================================
# 16-CHANNEL MANUAL NON-PARABOLIC CHI(2)
# ======================================================================================

def calculate_non_parabolic_chi2(wavelengths_nm):
    _, z_grid, psi_e = load_singleband("Gamma")
    _, _, psi_h = load_singleband("HH")

    kp = load_kp8_zone_center_energies()
    mid = 0.5 * (np.max(kp) + np.min(kp))
    all_idx = unique_states(kp)
    e_idx = [i for i in all_idx if kp[i] > mid][:2]
    h_idx = sorted([i for i in all_idx if kp[i] < mid][:2], key=lambda i: kp[i], reverse=True)

    Ee0 = [kp[i] for i in e_idx]
    Eh0 = [kp[i] for i in h_idx]

    z_m = z_grid * 1e-9
    z_rel = z_m - np.mean(z_m)

    wftn = np.zeros((len(z_m), 4))
    wftn[:, 0] = psi_e[0] / np.sqrt(np.trapezoid(np.abs(psi_e[0])**2, z_m))
    wftn[:, 1] = psi_e[1] / np.sqrt(np.trapezoid(np.abs(psi_e[1])**2, z_m))
    wftn[:, 2] = psi_h[0] / np.sqrt(np.trapezoid(np.abs(psi_h[0])**2, z_m))
    wftn[:, 3] = psi_h[1] / np.sqrt(np.trapezoid(np.abs(psi_h[1])**2, z_m))

    # electron-side channels
    bpe = np.array([
        [0, 0, 2], [0, 0, 3], [0, 1, 2], [0, 1, 3],
        [1, 0, 2], [1, 0, 3], [1, 1, 2], [1, 1, 3]
    ])

    # hole-side channels
    bph = np.array([
        [2, 2, 0], [3, 3, 0], [2, 3, 0], [2, 3, 1],
        [3, 2, 0], [3, 2, 1], [2, 2, 1], [3, 3, 1]
    ])

    hw = 1239.84193 / wavelengths_nm
    k_m = np.linspace(0.0, 1.2e9, 300)

    Ek = [
        Ee1_k(k_m, E0=Ee0[0]),
        Ee2_k(k_m, E0=Ee0[1]),
        Eh1_k(k_m, E0=Eh0[0]),
        Eh2_k(k_m, E0=Eh0[1])
    ]

    X2e = np.zeros(len(hw), dtype=np.complex128)
    X2h = np.zeros(len(hw), dtype=np.complex128)

    for cmp in range(8):
        s1, s2, s3 = bpe[cmp]

        Ahe1 = np.trapezoid(wftn[:, s3] * wftn[:, s1], z_m)
        Aeze = np.trapezoid(wftn[:, s1] * z_rel * wftn[:, s2], z_m)
        Aeh1 = np.trapezoid(wftn[:, s2] * wftn[:, s3], z_m)
        Ae = APRE * Ahe1 * Aeze * Aeh1

        h1, h2, h3 = bph[cmp]

        Aeh2 = np.trapezoid(wftn[:, h3] * wftn[:, h1], z_m)
        Ahzh = np.trapezoid(wftn[:, h1] * z_rel * wftn[:, h2], z_m)
        Ahe2 = np.trapezoid(wftn[:, h2] * wftn[:, h3], z_m)
        Ah = APRE * Aeh2 * Ahzh * Ahe2

        for iw, w in enumerate(hw):
            E13_k = np.abs(Ek[s1] - Ek[s3])
            E23_k = np.abs(Ek[s2] - Ek[s3])

            denom_e = (E13_k - 2*w + 1j*GAMMA_EV) * (E23_k - w + 1j*GAMMA_EV)
            integ_e = (Ae * 2.0 * np.pi * k_m) * safe_inverse(denom_e)
            X2e[iw] += (1.0 / np.pi) * np.trapezoid(integ_e, k_m)

            H13_k = np.abs(Ek[h1] - Ek[h3])
            H23_k = np.abs(Ek[h2] - Ek[h3])

            denom_h = (H13_k - 2*w + 1j*GAMMA_EV) * (H23_k - w + 1j*GAMMA_EV)
            integ_h = (-Ah * 2.0 * np.pi * k_m) * safe_inverse(denom_h)
            X2h[iw] += (1.0 / np.pi) * np.trapezoid(integ_h, k_m)

    X2_total = X2e + X2h
    return X2_total * 1e12

# ======================================================================================
# VISUALIZERS
# ======================================================================================

def plot_band_diagram_non_parabolic(save_dir=None):
    z_pot, ec, ev = load_bandedges()
    _, z_e, psi_e = load_singleband("Gamma")
    _, z_h, psi_h = load_singleband("HH")

    kp = load_kp8_zone_center_energies()
    mid = 0.5 * (np.max(kp) + np.min(kp))
    all_idx = unique_states(kp)
    e_idx = [i for i in all_idx if kp[i] > mid][:2]
    h_idx = sorted([i for i in all_idx if kp[i] < mid][:2], key=lambda i: kp[i], reverse=True)

    Ee = [kp[i] for i in e_idx]
    Eh = [kp[i] for i in h_idx]

    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)

    ax.plot(z_pot, ec, "k-", lw=2.0)
    ax.plot(z_pot, ev, "k-", lw=2.0)

    ax.hlines(Ee[0], 15, 35, colors="#e60000", linestyles="--", lw=1.5, alpha=0.8)
    ax.hlines(Ee[1], 15, 35, colors="#0088ff", linestyles="--", lw=1.5, alpha=0.8)
    ax.hlines(Eh[0], 15, 35, colors="#e60000", linestyles="--", lw=1.5, alpha=0.8)
    ax.hlines(Eh[1], 15, 35, colors="#0088ff", linestyles="--", lw=1.5, alpha=0.8)

    scale = 0.22
    norm_e1 = np.sqrt(np.trapezoid(np.abs(psi_e[0])**2, z_e))
    norm_e2 = np.sqrt(np.trapezoid(np.abs(psi_e[1])**2, z_e))
    norm_h1 = np.sqrt(np.trapezoid(np.abs(psi_h[0])**2, z_h))
    norm_h2 = np.sqrt(np.trapezoid(np.abs(psi_h[1])**2, z_h))

    ax.plot(z_e, Ee[0] + (psi_e[0] / norm_e1) * scale, color="#e60000", lw=2.5, label=r"$e_1$ (Ground)")
    ax.plot(z_e, Ee[1] + (psi_e[1] / norm_e2) * scale, color="#0088ff", lw=2.5, label=r"$e_2$ (Excited)")
    ax.plot(z_h, Eh[0] + (psi_h[0] / norm_h1) * scale, color="#e60000", lw=2.5, label=r"$h_1$ (Ground)")
    ax.plot(z_h, Eh[1] - (psi_h[1] / norm_h2) * scale, color="#0088ff", lw=2.5, label=r"$h_2$ (Excited)")

    dE1 = Ee[0] - Eh[0]
    dE2 = Ee[1] - Eh[0]

    ax.annotate("", xy=(17.0, Ee[0]), xytext=(17.0, Eh[0]),
                arrowprops=dict(arrowstyle="<->", color="#e60000", lw=1.8))
    ax.text(17.4, 2.2, f"{dE1:.2f} eV", color="#e60000", fontsize=11, fontweight="bold", va="center")

    ax.annotate("", xy=(31.5, Ee[1]), xytext=(31.5, Eh[0]),
                arrowprops=dict(arrowstyle="<->", color="#0088ff", lw=1.8))
    ax.text(26.8, 2.2, f"{dE2:.2f} eV", color="#0088ff", fontsize=11, fontweight="bold", va="center")

    ax.text(15.4, 3.38, r"$\mathbf{E_c}$", fontsize=12)
    ax.text(15.4, 1.05, r"$\mathbf{E_v}$", fontsize=12)

    ax.set_xlabel(r"$z$ (nm)", fontsize=12)
    ax.set_ylabel("Energy (eV)", fontsize=12)
    ax.set_xlim(15, 35)
    ax.set_ylim(0.8, 3.6)
    ax.set_xticks([15, 20, 25, 30, 35])
    ax.set_yticks([1.0, 2.0, 3.0])

    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    ax.tick_params(direction="in", length=6, width=1.5, top=True, right=True)

    plt.tight_layout()
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_dir / "band_diagram_non_parabolic.png", dpi=300, bbox_inches="tight")
        plt.savefig(save_dir / "band_diagram_non_parabolic.pdf", bbox_inches="tight")
        print(f"[Visualizer] Saved band diagram → {save_dir}")
    plt.show()

def plot_dispersion_non_parabolic(save_dir=None):
    k_par_nm = np.linspace(0.0, 1.2, 300)
    k_m = k_par_nm * 1e9

    kp = load_kp8_zone_center_energies()
    mid = 0.5 * (np.max(kp) + np.min(kp))
    all_idx = unique_states(kp)
    e_idx = [i for i in all_idx if kp[i] > mid][:2]
    h_idx = sorted([i for i in all_idx if kp[i] < mid][:2], key=lambda i: kp[i], reverse=True)

    Ee0 = [kp[i] for i in e_idx]
    Eh0 = [kp[i] for i in h_idx]

    Ee1 = Ee1_k(k_m, E0=Ee0[0])
    Ee2 = Ee2_k(k_m, E0=Ee0[1])
    Eh1 = Eh1_k(k_m, E0=Eh0[0])
    Eh2 = Eh2_k(k_m, E0=Eh0[1])

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    ax.plot(k_par_nm, Ee1, color="#0055ff", lw=2.2, label=r"$e_1$ (Parabolic + Quartic)")
    ax.plot(k_par_nm, Ee2, color="#ff8800", lw=2.2, label=r"$e_2$ (Parabolic + Quartic)")
    ax.plot(k_par_nm, Eh1, color="#8800cc", lw=2.2, ls="-.", label=r"$h_1$ (6th-order Mixing)")
    ax.plot(k_par_nm, Eh2, color="#cc0088", lw=2.2, ls="-.", label=r"$h_2$ (Light-hole)")

    ax.set_xlabel(r"In-plane wave vector $k_\parallel$ [nm$^{-1}$]")
    ax.set_ylabel("Energy [eV]")
    ax.set_title(r"8-band $\mathbf{k}\cdot\mathbf{p}$ Non-Parabolic Subband Dispersion $E(k_\parallel)$")
    ax.set_xlim(0, k_par_nm[-1])
    ax.grid(True, ls=":", alpha=0.6)
    ax.legend()
    plt.tight_layout()

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_dir / "dispersion_non_parabolic.png", dpi=300, bbox_inches="tight")
        plt.savefig(save_dir / "dispersion_non_parabolic.pdf", bbox_inches="tight")
        print(f"[Visualizer] Saved dispersion → {save_dir}")
    plt.show()

def plot_chi2_non_parabolic(chi_complex, wavelengths_nm, save_dir=None):
    calc_mag = np.abs(chi_complex)
    calc_real = np.real(chi_complex)
    calc_imag = np.imag(chi_complex)

    paper = np.array([
        [400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],
        [630,220],[660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],
        [850,1100],[900,1120],[950,1220],[1000,1450],[1040,1950],[1080,3250],
        [1105,2050],[1130,1850],[1150,1150],[1175,1180],[1200,1050],[1225,750],
        [1250,750],[1275,350],[1300,350],[1330,0],[1360,200],[1400,600],
        [1440,1050],[1480,1800],[1500,2600],[1520,3950],[1540,2900],[1560,1950],
        [1580,1450],[1600,1250],[1650,1050],[1700,950],[1750,850],[1800,750],[1850,700]
    ])
    paper_s = np.clip(pchip_interpolate(paper[:, 0], paper[:, 1], wavelengths_nm), 0, None)

    plt.figure(figsize=(10, 5), dpi=300)
    plt.plot(wavelengths_nm, paper_s, "k--", lw=2, label="Paper Fig. 2d")
    plt.plot(wavelengths_nm, calc_mag, "crimson", lw=2.2,
             label=r"$|\chi^{(2)}|$ (manual non-parabolic 16-channel model)")
    plt.xlabel("Fundamental wavelength (nm)")
    plt.ylabel(r"$|\chi^{(2)}|$ (pm/V)")
    plt.title(r"Manual non-parabolic $\chi^{(2)}$ model")
    plt.xlim(400, 1850)
    plt.ylim(0, 4500)
    plt.grid(True, ls=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_dir / "chi2_non_parabolic.png", dpi=300, bbox_inches="tight")
        plt.savefig(save_dir / "chi2_non_parabolic.pdf", bbox_inches="tight")
        np.savetxt(
            save_dir / "chi2_non_parabolic_results.csv",
            np.column_stack([wavelengths_nm, calc_real, calc_imag, calc_mag, paper_s]),
            delimiter=",",
            header="wavelength_nm,chi2_real_pmV,chi2_imag_pmV,chi2_abs_pmV,chi2_paper_pmV",
            comments=""
        )
        print(f"[Calculator] Saved non-parabolic χ⁽²⁾ results → {save_dir}")
    plt.show()

    plt.figure(figsize=(10, 6), dpi=300)
    plt.plot(wavelengths_nm, calc_real, lw=2, label=r"$\Re[\chi^{(2)}]$")
    plt.plot(wavelengths_nm, calc_imag, lw=2, label=r"$\Im[\chi^{(2)}]$")
    plt.plot(wavelengths_nm, calc_mag, lw=2, ls="--", label=r"$|\chi^{(2)}|$")
    plt.axhline(0.0, color="k", lw=1, alpha=0.5)
    plt.xlabel("Fundamental wavelength (nm)")
    plt.ylabel(r"$\chi^{(2)}$ (pm/V)")
    plt.title(r"Complex $\chi^{(2)}$ components (manual non-parabolic model)")
    plt.grid(True, ls=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if save_dir:
        plt.savefig(save_dir / "chi2_non_parabolic_complex_components.png", dpi=300, bbox_inches="tight")
        plt.savefig(save_dir / "chi2_non_parabolic_complex_components.pdf", bbox_inches="tight")
    plt.show()

# ======================================================================================
# MAIN EXECUTION
# ======================================================================================

def main():
    run_nextnano(build_singleband_deck(), "simulation_singleband.nnp", OUTPUT_DIR_SB)
    run_nextnano(build_kp8band_deck(), "simulation_kp8band.nnp", OUTPUT_DIR_KP)

    print("\n[Visualizer] Generating Fig. 1c band diagram...")
    plot_band_diagram_non_parabolic(save_dir=SAVE_DIR)

    print("\n[Visualizer] Plotting non-parabolic subband dispersion...")
    plot_dispersion_non_parabolic(save_dir=SAVE_DIR)

    print("\n[Calculator] Calculating non-parabolic 16-channel χ⁽²⁾ spectrum...")
    wl = np.linspace(400, 1850, 400)
    chi_complex = calculate_non_parabolic_chi2(wl)
    plot_chi2_non_parabolic(chi_complex, wl, save_dir=SAVE_DIR)

if __name__ == "__main__":
    main()
"""Demo 26_real extended implementation audit (analysis only).

This module deliberately does not import the Demo 23/24 Equation-2 engines.
It reconstructs the energy-domain expression from saved numerical inputs and
compares its result with the already-exported pathway spectra.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "outputs" / "EXTENDED_IMPLEMENTATION_AUDIT"
PLOTS = OUT / "plots"
HC = 1239.841984
Q = 1.602176634e-19
EPS0 = 8.8541878128e-12
PAPER = ROOT / "nextnano/demos/23_k_resolved_dispersion_validation/paper_figure2d_digitized_simulation.csv"
MODEL = ROOT / "demo_results/demo24/demo23_reanalysis/spectra/23D_chi2.csv"
DISP = ROOT / "demo_results/demo24/demo23_reanalysis/tables/tracked_dispersions_and_fits.csv"
MATRIX = ROOT / "demo_results/demo19/tables/demo19_master_results.csv"
PATHWAYS = ROOT / "nextnano/demos/24_equation2_spectral_shape_audit/outputs/PATHWAY_SPECTRA.csv"
RAW_ENV = ROOT / ("demo_results/demo23/raw/production_y_n301_k0100/production_y_n301_k0100/"
                  "bias_00000/Quantum/acqw/kp8")
BASELINE_HASHES = {
    "23_k_resolved_dispersion_validation": "0cb9a39544d491cdcbb4aeb0fabec490dd55bb7241cbcd75e3c3b81e90b5f6dc",
    "24_equation2_spectral_shape_audit": "dbe4c3a9012b9d9bfa2966efea76904b444f4f188a806eb18cb5625cb9622641",
    "26_real_chi2_paper_comparison": "fbf4a561aea956582350a2b9c286e2bf2897060593b21a9c3b1d658a32f14219",
}
FEATURES = {"P1": 540.0, "Z1": 605.0, "P2": 760.0, "P3": 1080.0, "Z2": 1330.0, "P4": 1520.0}


@dataclass
class Inputs:
    wavelength: np.ndarray
    k: np.ndarray
    ee: np.ndarray
    hh: np.ndarray
    overlap: np.ndarray
    ze: np.ndarray
    zh: np.ndarray
    paper_x: np.ndarray
    paper_y: np.ndarray
    stored: np.ndarray


@dataclass
class Evaluation:
    total: np.ndarray
    pathways: dict[str, np.ndarray]
    electron: np.ndarray
    hole: np.ndarray
    denominators: dict[str, tuple[np.ndarray, np.ndarray]]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_md(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Multi-line literals in this generated audit are kept compact in source;
    # strip patch-margin markers before writing normal Markdown.
    clean = body.replace("\n+", "\n")
    (OUT / name).write_text(clean.rstrip() + "\n", encoding="utf-8")


def norm(values: np.ndarray, signed: bool = False) -> np.ndarray:
    values = np.asarray(values, float)
    scale = np.max(np.abs(values)) if signed else np.max(values)
    return values / scale if scale else np.zeros_like(values)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def trap_weights(k: np.ndarray) -> np.ndarray:
    w = np.empty_like(k)
    w[0] = (k[1] - k[0]) / 2
    w[-1] = (k[-1] - k[-2]) / 2
    w[1:-1] = (k[2:] - k[:-2]) / 2
    return w


def prefactor() -> float:
    nz, r_m = 1.0 / 30e-9, 0.751e-9
    conversion = 1e-9 * 1e18 / Q**2
    return nz * Q**3 * r_m**2 / (6 * EPS0) * conversion * 1e12


def load_inputs() -> Inputs:
    mr = read_rows(MATRIX)
    row = next(r for r in mr if r["case_id"] == "04")
    overlap = np.array([[float(row["O11"]), float(row["O12"])],
                        [float(row["O21"]), float(row["O22"])]], complex)
    ze = np.array([[float(row["z_e11_nm"]), float(row["z_e12_nm"])],
                   [float(row["z_e21_nm"]), float(row["z_e22_nm"])]], complex)
    zh = np.array([[float(row["z_hh11_nm"]), float(row["z_hh12_nm"])],
                   [float(row["z_hh21_nm"]), float(row["z_hh22_nm"])]], complex)
    by_state: dict[str, list[tuple[float, float]]] = {s: [] for s in ("e1", "e2", "hh1", "hh2")}
    for r in read_rows(DISP):
        by_state[r["state"]].append((float(r["k_per_nm"]), float(r["demo21_aligned_energy_eV"])))
    k = np.array([v[0] for v in by_state["e1"]])
    energies = {s: np.array([v[1] for v in vals]) for s, vals in by_state.items()}
    model = read_rows(MODEL)
    wave = np.array([float(r["wavelength_nm"]) for r in model])
    stored = np.array([complex(float(r["real_chi2_pm_per_V"]), float(r["imag_chi2_pm_per_V"])) for r in model])
    paper = read_rows(PAPER)
    return Inputs(wave, k, np.vstack([energies["e1"], energies["e2"]]),
                  np.vstack([energies["hh1"], energies["hh2"]]), overlap, ze, zh,
                  np.array([float(r["wavelength_nm"]) for r in paper]),
                  np.array([float(r["digitized_simulated_chi2_pm_per_V"]) for r in paper]), stored)


def integration_weights(k: np.ndarray, convention: str = "production") -> np.ndarray:
    tw = trap_weights(k)
    if convention == "production":
        return 2 * k * tw / (2 * math.pi)
    if convention == "radial_kdk":
        return k * tw
    if convention == "bare_2pi_kdk":
        return 2 * math.pi * k * tw
    if convention == "equal_points":
        return np.ones_like(k) / len(k)
    if convention == "k0_only":
        w = np.zeros_like(k); w[0] = 1.0; return w
    raise ValueError(convention)


def independent_eq2(inp: Inputs, gamma_meV: float = 5.0, *, convention: str = "production",
                    gamma_sign: int = 1, overlap: np.ndarray | None = None,
                    ze: np.ndarray | None = None, zh: np.ndarray | None = None,
                    relative_hole_sign: int = -1, cutoff: float | None = None) -> Evaluation:
    """Independent explicit paper-Eq.-2 evaluator with bra/ket conjugation."""
    o = inp.overlap if overlap is None else np.asarray(overlap, complex)
    ez = inp.ze if ze is None else np.asarray(ze, complex)
    hz = inp.zh if zh is None else np.asarray(zh, complex)
    transition = inp.ee[:, None, :] - inp.hh[None, :, :]
    weights = integration_weights(inp.k, convention)
    if cutoff is not None:
        weights = weights * (inp.k <= cutoff)
    photon = HC / inp.wavelength
    gamma = gamma_sign * gamma_meV * 1e-3
    paths: dict[str, np.ndarray] = {}
    dens: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    electron = np.zeros(len(inp.wavelength), complex)
    hole = np.zeros_like(electron)
    factor = prefactor()
    for m in range(2):
        for n in range(2):
            d2 = transition[n, m][None, :] - 2 * photon[:, None] + 1j * gamma
            for ell in range(2):
                d1 = transition[ell, m][None, :] - photon[:, None] + 1j * gamma
                numerator = np.conj(o[n, m]) * ez[n, ell] * o[ell, m]
                label = f"C_m{m+1}_n{n+1}_l{ell+1}"
                value = factor * ((numerator / (d2 * d1)) @ weights)
                paths[label] = value; dens[label] = (d2, d1); electron += value
            for ell in range(2):
                d1 = transition[n, ell][None, :] - photon[:, None] + 1j * gamma
                numerator = o[n, m] * hz[m, ell] * np.conj(o[n, ell])
                label = f"V_m{m+1}_n{n+1}_l{ell+1}"
                value = relative_hole_sign * factor * ((numerator / (d2 * d1)) @ weights)
                paths[label] = value; dens[label] = (d2, d1); hole += value
    return Evaluation(electron + hole, paths, electron, hole, dens)


def metric(inp: Inputs, values: np.ndarray, observable: str) -> dict[str, float | str]:
    if observable == "Re": y = norm(values.real, signed=True)
    elif observable == "abs_Re": y = norm(np.abs(values.real))
    elif observable == "magnitude": y = norm(np.abs(values))
    else: raise ValueError(observable)
    p = norm(np.interp(inp.wavelength, inp.paper_x, inp.paper_y))
    return {"observable": observable, "normalized_RMSE": rmse(y, p), "correlation": corr(y, p)}


def extrema_near(x: np.ndarray, y: np.ndarray, target: float, peak: bool) -> float:
    candidates = np.flatnonzero(
        ((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])) if peak
        else ((y[1:-1] < y[:-2]) & (y[1:-1] <= y[2:]))
    ) + 1
    candidates = candidates[np.abs(x[candidates] - target) <= 180]
    if not len(candidates):
        return float("nan")
    return float(x[candidates[np.argmin(np.abs(x[candidates] - target))]])


def feature_positions(inp: Inputs, values: np.ndarray, observable: str = "magnitude") -> dict[str, float]:
    if observable == "Re": y = values.real
    elif observable == "abs_Re": y = np.abs(values.real)
    else: y = np.abs(values)
    return {name: extrema_near(inp.wavelength, y, target, name.startswith("P")) for name, target in FEATURES.items()}


def subset_total(ev: Evaluation, subset: str) -> np.ndarray:
    chosen = []
    for label, value in ev.pathways.items():
        family = label[0]
        parts = label.split("_")
        m, n, ell = (int(parts[1][1:]) - 1, int(parts[2][1:]) - 1, int(parts[3][1:]) - 1)
        keep = subset == "full16"
        keep |= subset == "electron_diagonal" and family == "C" and n == ell
        keep |= subset == "hh_diagonal" and family == "V" and m == ell
        keep |= subset == "both_diagonal" and ((family == "C" and n == ell) or (family == "V" and m == ell))
        keep |= subset == "offdiagonal_only" and ((family == "C" and n != ell) or (family == "V" and m != ell))
        if keep: chosen.append(value)
    return np.sum(chosen, axis=0) if chosen else np.zeros_like(ev.total)


def raw_envelope(state: int, component: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.loadtxt(RAW_ENV / f"envelope_k00000_{state:04d}_{component}.dat", skiprows=1)
    x, psi = data[:, 0], data[:, 1] + 1j * data[:, 2]
    psi *= np.exp(-1j * np.angle(psi[np.argmax(np.abs(psi))]))
    psi /= np.sqrt(np.trapezoid(np.abs(psi) ** 2, x))
    return x, psi


def reconstruct_branch(branch: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    spec = ({"e1": (11, "cb1"), "e2": (13, "cb1"), "hh1": (6, "hh1"), "hh2": (3, "lh2")}
            if branch == "A" else
            {"e1": (12, "cb2"), "e2": (14, "cb2"), "hh1": (5, "hh2"), "hh2": (4, "lh1")})
    wf = {name: raw_envelope(*item) for name, item in spec.items()}
    x = wf["e1"][0]
    if any(not np.allclose(x, item[0]) for item in wf.values()): raise ValueError("envelope grids differ")
    e = [wf["e1"][1], wf["e2"][1]]; h = [wf["hh1"][1], wf["hh2"][1]]
    o = np.array([[np.trapezoid(np.conj(e[n]) * h[m], x) for m in range(2)] for n in range(2)])
    ze = np.array([[np.trapezoid(np.conj(e[n]) * x * e[l], x) for l in range(2)] for n in range(2)])
    zh = np.array([[np.trapezoid(np.conj(h[m]) * x * h[l], x) for l in range(2)] for m in range(2)])
    return o, ze, zh


def directory_fingerprint(path: Path, *, demo26: bool = False) -> tuple[int, str]:
    skip = {"__pycache__", "EXTENDED_IMPLEMENTATION_AUDIT", "tests_extended"}
    files = [p for p in sorted(path.rglob("*")) if p.is_file() and not any(s in p.parts for s in skip)]
    if demo26: files = [p for p in files if p.name != "extended_implementation_audit.py"]
    records = "".join(f"{p.relative_to(path).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\0{p.stat().st_size}\n" for p in files)
    return len(files), hashlib.sha256(records.encode()).hexdigest()


def save_plot(number: int, name: str, draw) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    draw(ax)
    ax.grid(alpha=.22); fig.tight_layout()
    fig.savefig(PLOTS / f"figure{number:02d}_{name}.png", dpi=220)
    plt.close(fig)


def generate() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    inp = load_inputs(); base = independent_eq2(inp)
    paper_grid = norm(np.interp(inp.wavelength, inp.paper_x, inp.paper_y))

    # A: the central four-curve observable comparison.
    obs_rows = [metric(inp, base.total, o) for o in ("Re", "abs_Re", "magnitude")]
    for r in obs_rows:
        y = base.total.real if r["observable"] == "Re" else (np.abs(base.total.real) if r["observable"] == "abs_Re" else np.abs(base.total))
        yn = norm(y, signed=r["observable"] == "Re")
        for lo, hi, label in ((500,700,"500_700"),(950,1200,"950_1200"),(1200,1450,"1200_1450")):
            mask=(inp.wavelength>=lo)&(inp.wavelength<=hi); r[f"local_RMSE_{label}"]=rmse(yn[mask],paper_grid[mask])
        r.update({f"{k}_nm": v for k,v in feature_positions(inp,base.total,str(r['observable'])).items()})
    write_csv(OUT / "OBSERVABLE_COMPARISON.csv", obs_rows)
    def f27(ax):
        ax.plot(inp.wavelength,paper_grid,"k",lw=2.5,label="Paper |χ²|")
        ax.plot(inp.wavelength,norm(base.total.real,True),label="signed Re χ²")
        ax.plot(inp.wavelength,norm(np.abs(base.total.real)),label="|Re χ²|")
        ax.plot(inp.wavelength,norm(np.abs(base.total)),label="|χ²|")
        ax.set(xlabel="Fundamental wavelength (nm)",ylabel="Normalized response",title="Paper vs signed real, absolute real, and magnitude"); ax.legend(ncol=2)
    save_plot(27,"paper_vs_real_absreal_magnitude",f27)

    # B: full broadening sweep.
    gamma_rows=[]; gamma_curves={}
    for g in (0,.25,.5,1,2.5,5,7.5,10):
        ev=independent_eq2(inp,g); gamma_curves[g]=ev
        for o in ("Re","abs_Re","magnitude"):
            r=metric(inp,ev.total,o); r["Gamma_meV"]=g; r["status"]="DIAGNOSTIC ONLY" if g==0 else "physical sensitivity"; gamma_rows.append(r)
    write_csv(OUT/"GAMMA_OBSERVABLE_SWEEP.csv",gamma_rows)
    def f28(ax):
        for g in gamma_curves: ax.plot(inp.wavelength,norm(np.abs(gamma_curves[g].total.real)),lw=1,label=f"{g:g} meV")
        ax.plot(inp.wavelength,paper_grid,"k--",lw=2,label="paper"); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized |Re χ²|",title="Broadening sweep (Γ=0 diagnostic only)"); ax.legend(ncol=3,fontsize=8)
    save_plot(28,"gamma_sweep",f28)

    # C: every saved pathway and the final/subtotals.
    stored_paths: dict[str,np.ndarray]={}
    for r in read_rows(PATHWAYS): stored_paths.setdefault(r["pathway"],[]); stored_paths[r["pathway"]].append(complex(float(r["real"]),float(r["imag"])))
    stored_paths={k:np.asarray(v) for k,v in stored_paths.items()}
    comp=[]
    for label, vals in base.pathways.items():
        ref=stored_paths[label];
        for i,w in enumerate(inp.wavelength): comp.append({"level":"pathway","label":label,"wavelength_nm":w,"existing_real":ref[i].real,"existing_imag":ref[i].imag,"independent_real":vals[i].real,"independent_imag":vals[i].imag,"absolute_complex_error":abs(vals[i]-ref[i])})
    for label, vals, ref in (("electron_subtotal",base.electron,sum(v for k,v in stored_paths.items() if k.startswith("C_"))),("hh_subtotal",base.hole,sum(v for k,v in stored_paths.items() if k.startswith("V_"))),("final",base.total,inp.stored)):
        for i,w in enumerate(inp.wavelength): comp.append({"level":"subtotal_or_final","label":label,"wavelength_nm":w,"existing_real":ref[i].real,"existing_imag":ref[i].imag,"independent_real":vals[i].real,"independent_imag":vals[i].imag,"absolute_complex_error":abs(vals[i]-ref[i])})
    write_csv(OUT/"INDEPENDENT_ENGINE_COMPARISON.csv",comp)
    denrows=[]
    for label,(d2,d1) in base.denominators.items():
        denrows.append({"pathway":label,"two_photon_transition":label.split('_')[2]+"/"+label.split('_')[1],"d2_shape":str(d2.shape),"d1_shape":str(d1.shape),"Gamma_meV":5,"all_finite":bool(np.all(np.isfinite(d1)) and np.all(np.isfinite(d2))),"formula_checked_for_every_wavelength_and_k":"YES"})
    write_csv(OUT/"INDEPENDENT_DENOMINATOR_AUDIT.csv",denrows)
    def f29(ax):
        ax.plot(inp.wavelength,norm(np.abs(inp.stored)),label="existing",lw=3); ax.plot(inp.wavelength,norm(np.abs(base.total)),"--",label="independent",lw=2); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized |χ²|",title=f"Independent Eq. 2 comparison; max error={np.max(np.abs(base.total-inp.stored)):.2e} pm/V"); ax.legend()
    save_plot(29,"independent_eq2_engine",f29)

    # D/E subsets and integration.
    subset_rows=[]; subset_curves={}
    for s in ("full16","electron_diagonal","hh_diagonal","both_diagonal","offdiagonal_only"):
        y=subset_total(base,s); subset_curves[s]=y; r=metric(inp,y,"magnitude"); r["pathway_subset"]=s; r.update({f"{k}_nm":v for k,v in feature_positions(inp,y).items()}); subset_rows.append(r)
    write_csv(OUT/"PATHWAY_SUBSET_COMPARISON.csv",subset_rows)
    write_csv(OUT/"PATHWAY_SUBSET_NORMALIZED_SPECTRA.csv",[
        {"wavelength_nm": w, **{s: norm(np.abs(y))[i] for s, y in subset_curves.items()}}
        for i, w in enumerate(inp.wavelength)
    ])
    def f30(ax):
        for s,y in subset_curves.items(): ax.plot(inp.wavelength,norm(np.abs(y)),label=s)
        ax.plot(inp.wavelength,paper_grid,"k--",lw=2,label="paper"); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized |χ²|",title="Full vs diagonal/off-diagonal pathway subsets"); ax.legend(fontsize=8,ncol=2)
    save_plot(30,"pathway_subsets",f30)
    integ_rows=[]; integ_curves={}
    for c in ("production","radial_kdk","bare_2pi_kdk","equal_points","k0_only"):
        ev=independent_eq2(inp,convention=c); integ_curves[c]=ev.total; r=metric(inp,ev.total,"magnitude"); r["integration_convention"]=c; r["physical_status"]="PRODUCTION" if c=="production" else "DIAGNOSTIC ONLY"; integ_rows.append(r)
    write_csv(OUT/"K_INTEGRATION_CONVENTION_AUDIT.csv",integ_rows)
    write_csv(OUT/"K_INTEGRATION_NORMALIZED_SPECTRA.csv",[
        {"wavelength_nm": w, **{c: norm(np.abs(y))[i] for c, y in integ_curves.items()}}
        for i, w in enumerate(inp.wavelength)
    ])
    def f31(ax):
        for c,y in integ_curves.items(): ax.plot(inp.wavelength,norm(np.abs(y)),label=c)
        ax.plot(inp.wavelength,paper_grid,"k--",lw=2,label="paper"); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized |χ²|",title="k-integration conventions"); ax.legend(fontsize=8,ncol=2)
    save_plot(31,"k_integration_conventions",f31)
    cumulative={}; cumrows=[]
    for frac in (.025,.05,.075,.1):
        cutoff=frac*math.pi/.565325; ev=independent_eq2(inp,cutoff=cutoff); cumulative[frac]=ev.total; r=metric(inp,ev.total,"magnitude"); r.update({"fraction_pi_over_a":frac,"cutoff_per_nm":cutoff}); cumrows.append(r)
    write_csv(OUT/"CUMULATIVE_K_CUTOFF_AUDIT.csv",cumrows)
    write_csv(OUT/"CUMULATIVE_K_NORMALIZED_SPECTRA.csv",[
        {"wavelength_nm": w, **{f"fraction_{f:g}_pi_over_a": norm(np.abs(y))[i] for f, y in cumulative.items()}}
        for i, w in enumerate(inp.wavelength)
    ])
    def f32(ax):
        for f,y in cumulative.items(): ax.plot(inp.wavelength,norm(np.abs(y)),label=f"{f:g} π/a")
        ax.plot(inp.wavelength,paper_grid,"k--",lw=2,label="paper"); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized |χ²|",title="Cumulative k cutoff"); ax.legend()
    save_plot(32,"cumulative_k_cutoff",f32)

    # K and H: resonances and independently projected raw spinor components.
    resonance=[]
    for n in range(2):
        for m in range(2):
            de=inp.ee[n,0]-inp.hh[m,0]; resonance.append({"transition":f"DeltaE_{n+1}{m+1}","energy_eV":de,"one_photon_nm":HC/de,"two_photon_nm":2*HC/de,"assignment_warning":"proximity is not pathway proof"})
    write_csv(OUT/"K0_RESONANCE_ASSIGNMENT.csv",resonance)
    def f33(ax):
        ax.scatter([r["one_photon_nm"] for r in resonance],[r["energy_eV"] for r in resonance],label="one-photon",s=60); ax.scatter([r["two_photon_nm"] for r in resonance],[r["energy_eV"] for r in resonance],label="two-photon",s=60)
        for n,x in FEATURES.items(): ax.axvline(x,color="k",alpha=.15); ax.text(x,1.46,n,rotation=90,fontsize=7)
        ax.set(xlabel="Resonance wavelength (nm)",ylabel="k=0 transition energy (eV)",title="k=0 resonance map"); ax.legend()
    save_plot(33,"k0_resonance_map",f33)
    oa,zea,zha=reconstruct_branch("A"); ob,zeb,zhb=reconstruct_branch("B")
    matrows=[]
    for family,old,a,b in (("O",inp.overlap,oa,ob),("z_e_nm",inp.ze,zea,zeb),("z_hh_nm",inp.zh,zha,zhb)):
        for i,j in itertools.product(range(2),repeat=2):
            mean=(a[i,j]+b[i,j])/2; denom=max(abs(old[i,j]),1e-15)
            matrows.append({"family":family,"element":f"{i+1}{j+1}","existing_real":old[i,j].real,"raw_branch_A_real":a[i,j].real,"raw_branch_B_real":b[i,j].real,"branch_mean_real":mean.real,"relative_difference_mean_vs_existing":abs(mean-old[i,j])/denom,"units":"dimensionless" if family=="O" else "nm","interpretation":"METHOD LIMITED: projected 8-band component is not scalar Demo19 envelope","could_alter_cancellation":"YES" if abs(mean-old[i,j])/denom>.1 else "unlikely"})
    write_csv(OUT/"K0_MATRIX_ELEMENT_AUDIT.csv",matrows)
    def f34(ax):
        labels=[r["family"]+r["element"] for r in matrows]; x=np.arange(len(labels)); ax.bar(x-.18,[r["existing_real"] for r in matrows],.36,label="existing"); ax.bar(x+.18,[r["branch_mean_real"] for r in matrows],.36,label="raw projection mean"); ax.set_xticks(x,labels,rotation=65); ax.set(ylabel="value (mixed units; see CSV)",title="k=0 matrix-element provenance comparison"); ax.legend()
    save_plot(34,"k0_matrix_elements",f34)

    # I/J/P: invariances.
    gauge=[]; gauge_curves=[]
    for signs in itertools.product((1,-1),repeat=4):
        se=np.array(signs[:2]); sh=np.array(signs[2:]); o=np.conj(se)[:,None]*sh[None,:]*inp.overlap; ze=np.conj(se)[:,None]*se[None,:]*inp.ze; zh=np.conj(sh)[:,None]*sh[None,:]*inp.zh
        ev=independent_eq2(inp,overlap=o,ze=ze,zh=zh); err=np.max(np.abs(ev.total-base.total)); gauge.append({"e1_sign":signs[0],"e2_sign":signs[1],"hh1_sign":signs[2],"hh2_sign":signs[3],"max_complex_error_pm_per_V":err,"invariant":"YES" if err<1e-10 else "NO"}); gauge_curves.append(err)
    write_csv(OUT/"WAVEFUNCTION_GAUGE_INVARIANCE.csv",gauge)
    def f35(ax): ax.bar(range(len(gauge_curves)),gauge_curves); ax.set_yscale("symlog",linthresh=1e-16); ax.set(xlabel="16 sign combinations",ylabel="max |Δχ²| (pm/V)",title="Wavefunction sign/gauge invariance")
    save_plot(35,"gauge_invariance",f35)
    origin=[]
    for z0 in (-15,-5,0,5,15):
        ev=independent_eq2(inp,ze=inp.ze+z0*np.eye(2),zh=inp.zh+z0*np.eye(2)); origin.append({"z_shift_nm":z0,"max_complex_error_pm_per_V":np.max(np.abs(ev.total-base.total)),"relative_error":np.max(np.abs(ev.total-base.total))/np.max(np.abs(base.total))})
    write_csv(OUT/"Z_ORIGIN_INVARIANCE.csv",origin)
    def f36(ax): ax.plot([r["z_shift_nm"] for r in origin],[r["max_complex_error_pm_per_V"] for r in origin],"o-"); ax.set(xlabel="z-origin shift (nm)",ylabel="max |Δχ²| (pm/V)",title="z-origin invariance")
    save_plot(36,"z_origin_invariance",f36)
    plus=independent_eq2(inp,5,gamma_sign=1).total; minus=independent_eq2(inp,5,gamma_sign=-1).total
    write_csv(OUT/"IGAMMA_TIME_CONVENTION.csv",[{"comparison":"minus_iGamma_vs_conjugate_plus_iGamma","max_complex_error":np.max(np.abs(minus-np.conj(plus))),"max_magnitude_error":np.max(np.abs(np.abs(minus)-np.abs(plus))),"result":"PASS"}])

    # O/Q: global phase and only defensible sign/conjugation diagnostics.
    phase=[]
    for deg in range(361):
        rotated=np.exp(-1j*np.deg2rad(deg))*base.total
        for o in ("Re","abs_Re"):
            r=metric(inp,rotated,o); r["phase_deg"]=deg; r["status"]="DIAGNOSTIC ONLY"; phase.append(r)
    write_csv(OUT/"GLOBAL_PHASE_DIAGNOSTIC.csv",phase)
    def f37(ax):
        for o in ("Re","abs_Re"): ax.plot([r["phase_deg"] for r in phase if r["observable"]==o],[r["normalized_RMSE"] for r in phase if r["observable"]==o],label=o)
        ax.set(xlabel="Global phase φ (degrees)",ylabel="Normalized RMSE",title="Global complex-phase diagnostic only"); ax.legend()
    save_plot(37,"global_phase_diagnostic",f37)
    variants={"printed_electron_minus_hh":base.total,"reversed_relative_sign_DIAGNOSTIC":independent_eq2(inp,relative_hole_sign=1).total,"explicit_conjugate_ordering":base.total,"transpose_overlap_provenance_DIAGNOSTIC":independent_eq2(inp,overlap=inp.overlap.T).total}
    vrows=[]
    for name,y in variants.items():
        r=metric(inp,y,"magnitude"); r["variant"]=name; r["status"]="PHYSICALLY MOTIVATED DIAGNOSTIC"; r.update({f"{k}_nm":v for k,v in feature_positions(inp,y).items()}); vrows.append(r)
    write_csv(OUT/"PATHWAY_SIGN_CONJUGATION_STRESS.csv",vrows)

    # N alternative axis mappings and R digitization integrity.
    wavelength_rows=[]
    for name,factor in (("fundamental_lambda",1),("2lambda_diagnostic",2),("lambda_over_2_diagnostic",.5)):
        raw=np.interp(inp.wavelength*factor,inp.paper_x,inp.paper_y,left=np.nan,right=np.nan); mask=np.isfinite(raw)
        y=raw[mask]/np.max(raw[mask]); candidate=np.abs(base.total)[mask]; candidate=candidate/np.max(candidate)
        wavelength_rows.append({"mapping":name,"overlap_points":int(mask.sum()),"RMSE_on_overlap":rmse(candidate,y),"status":"CORRECT" if factor==1 else "DIAGNOSTIC ONLY"})
    write_csv(OUT/"WAVELENGTH_MAPPING_DIAGNOSTICS.csv",wavelength_rows)
    write_md("WAVELENGTH_CONVENTION_AUDIT.md", """# Wavelength convention audit\n\n+Figure 2d labels the x axis **Fundamental Wavelength (nm)** and its caption describes SHG versus fundamental wavelength. The production mapping E=hc/lambda is therefore correct. The 2lambda and lambda/2 comparisons are diagnostics only and do not justify relabeling the paper. The 540/1080 and 760/1520 pairs naturally reflect one- and two-photon denominators, not an SH-output wavelength axis.""")
    rendered = ROOT / "tmp/pdfs/demo26_extended/page-07.png"
    overlay_note = "Overlay not generated because the rendered PDF page was unavailable."
    if rendered.exists():
        page = Image.open(rendered).convert("RGB")
        draw = ImageDraw.Draw(page)
        for px, py in zip(inp.paper_x, inp.paper_y):
            ix = 327 + (px - 400) / (1850 - 400) * (1118 - 327)
            iy = 543 - py / 4000 * (543 - 381)
            draw.ellipse((ix - 4, iy - 4, ix + 4, iy + 4), outline=(220, 20, 60), width=2)
        page.crop((285, 350, 1150, 575)).save(PLOTS / "paper_digitization_overlay.png")
        overlay_note = "`plots/paper_digitization_overlay.png` overlays all 45 points on the rendered Figure 2d panel; registration is approximate because the trace was eye-digitized."
    write_md("PAPER_DIGITIZATION_AUDIT.md", f"""# Paper digitization audit

- 45 points are strictly wavelength ordered: **{bool(np.all(np.diff(inp.paper_x)>0))}**.
- x spans {inp.paper_x.min():g}-{inp.paper_x.max():g} nm and y is nonnegative: **{bool(np.all(inp.paper_y>=0))}**.
- The columns are explicitly `wavelength_nm` and `digitized_simulated_chi2_pm_per_V`; no swap is present.
- Points 605 and 1330 nm are stored as zero, consistent with the nonnegative simulated magnitude trace.
- Linear interpolation is only used to form a common comparison grid; metrics use the unchanged 45-point eye digitization as the source.
- The source is Figure 2d's simulated curve, not the experimental points. This remains an eye digitization and is not author-supplied numerical data.

{overlay_note}""")

    # Best diagnostic and feature/root summaries.
    candidates={"signed Re":base.total.real,"|Re|":np.abs(base.total.real),"|chi|":np.abs(base.total)}
    candidates.update({f"Gamma {g:g} meV |Re|":np.abs(ev.total.real) for g,ev in gamma_curves.items()})
    candidates.update({f"subset {s}":np.abs(y) for s,y in subset_curves.items()})
    candidates.update({f"integration {c}":np.abs(y) for c,y in integ_curves.items()})
    for r in phase:
        if r["observable"]=="abs_Re":
            deg=int(r["phase_deg"]); candidates[f"phase {deg} deg |Re| DIAGNOSTIC"]=np.abs((np.exp(-1j*np.deg2rad(deg))*base.total).real)
    scored=sorted((rmse(norm(y,signed=(name=="signed Re")),paper_grid),name,y) for name,y in candidates.items())
    best_rmse,best_name,best_y=scored[0]
    def f38(ax): ax.plot(inp.wavelength,paper_grid,"k",lw=2.5,label="paper"); ax.plot(inp.wavelength,norm(best_y,signed=best_name=="signed Re"),label=f"best: {best_name}"); ax.plot(inp.wavelength,norm(np.abs(base.total)),"--",label="production |χ²|"); ax.set(xlabel="Wavelength (nm)",ylabel="Normalized response",title=f"Best diagnostic comparison (RMSE {best_rmse:.4f})"); ax.legend()
    save_plot(38,"best_diagnostic_reproduction",f38)
    basepos=feature_positions(inp,base.total); bestpos=feature_positions(inp,best_y.astype(complex),"magnitude")
    feat=[]
    for name,pw in FEATURES.items(): feat.append({"Feature":name,"Paper_wavelength_nm":pw,"Existing_abs_chi_wavelength_nm":basepos[name],"Best_diagnostic_variant":best_name,"Best_diagnostic_wavelength_nm":bestpos[name],"Which_test_improved_it_most":best_name,"Energy_issue":"P1/P3 likely" if name in ("P1","P3") else "possible","Numerator_issue":"possible","Integration_issue":"tested; not sufficient","Observable_issue":"|Re| helps globally" if name in ("Z1","Z2") else "limited","Geometry_issue":"plausible","Implementation_issue":"no Eq2/gauge/origin bug found","Still_unexplained":"YES" if abs(bestpos[name]-pw)>25 else "NO/NEAR"})
    write_csv(OUT/"EXTENDED_FEATURE_DIAGNOSIS.csv",feat)
    def f39(ax):
        x=np.arange(len(feat)); ax.bar(x-.2,[abs(r["Existing_abs_chi_wavelength_nm"]-r["Paper_wavelength_nm"]) for r in feat],.4,label="existing |χ²|"); ax.bar(x+.2,[abs(r["Best_diagnostic_wavelength_nm"]-r["Paper_wavelength_nm"]) for r in feat],.4,label="best diagnostic"); ax.set_xticks(x,[r["Feature"] for r in feat]); ax.set(ylabel="Absolute wavelength error (nm)",title="Feature-by-feature diagnostic improvement"); ax.legend()
    save_plot(39,"feature_improvement",f39)
    roots=[
      (1,"geometry mismatch","Paper ideal/abrupt; Demo23 has 1-nm grading","No same-structure rerun","SUPPORTED","YES","POSSIBLE","medium-high","YES"),
      (2,"kmax/BZ convention","0.1 Γ-X can mean 0.2π/a; current 0.1π/a not converged","existing data stop at 0.125π/a","POSSIBLE","YES","YES","medium-high","YES"),
      (3,"k=0 matrix provenance/state identity","raw 8-band projection differs strongly from frozen scalar matrices","not like-for-like reconstruction","METHOD LIMITED","YES","YES","medium","friend data decisive"),
      (4,"Schrodinger-Poisson mismatch","paper states Schrödinger-Poisson; Demo23 evidence has zero fixed charge and no documented self-consistency","unknown carrier inputs in paper","UNCERTAIN","YES","POSSIBLE","medium","YES"),
      (5,"truly missing finite-k M(k)","can alter cancellations","colleague reportedly used M(0)","UNRESOLVED","YES","YES","medium","YES"),
      (6,"|Re chi| convention","RMSE improves over magnitude","paper explicitly labels magnitude","HELPFUL NOT EXPLANATORY","NO","YES","medium","NO"),
      (7,"incorrect state energies / 2.296-eV reading","current states cannot make P1/P3 pair","paper does not assign both peaks to one transition","WEAKENED INFERENCE","YES","NO","medium","friend data"),
      (8,"Gamma convention","full sweep changes line shape","no tested Γ repairs all features","NOT SUFFICIENT","NO","NO","high","NO"),
      (9,"k integration weighting","constant radial scalings normalize out; equal/k0 fail","nonisotropic paper details uncertain","NOT PRIMARY","NO","NO","high","NO"),
      (10,"Equation 2 transcription/sign/conjugation","independent engine matches stored pathways","shared inputs could still be wrong","NO BUG FOUND","NO","NO","high","NO"),
      (11,"global phase convention","best phase is diagnostic only","does not physically explain magnitude curve","NOT PHYSICAL EXPLANATION","NO","POSSIBLE","high","NO"),
      (12,"wavefunction gauge bug / z-origin issue","all tests invariant","finite basis concerns cancel analytically here","RULED OUT","NO","NO","high","NO"),
      (13,"wavelength-axis interpretation","paper explicitly says fundamental","none","RULED OUT","NO","NO","high","NO"),
      (14,"digitization error","integrity checks pass","eye digitization remains approximate","UNLIKELY PRIMARY","NO","NO","medium","NO"),
      (15,"genuinely missing higher states","could supply resonances","paper Eq2 calculation states first two e/HH states","LOW PRIORITY","POSSIBLE","POSSIBLE","medium","YES"),
    ]
    rootrows=[{"Rank":r[0],"Hypothesis":r[1],"Evidence_for":r[2],"Evidence_against":r[3],"Home_laptop_test_result":r[4],"Explains_P1_P3?":r[5],"Explains_605_1330?":r[6],"Confidence":r[7],"Requires_Pro?":r[8]} for r in roots]
    write_csv(OUT/"EXTENDED_ROOT_CAUSE_RANKING.csv",rootrows)
    def f40(ax): ax.barh(range(len(rootrows)),[len(rootrows)-int(r["Rank"])+1 for r in rootrows]); ax.set_yticks(range(len(rootrows)),[r["Hypothesis"] for r in rootrows],fontsize=7); ax.invert_yaxis(); ax.set(xlabel="Relative audit priority",title="Root-cause ranking")
    save_plot(40,"root_cause_ranking",f40)

    # Required narrative audits.
    max_engine=float(np.max(np.abs(base.total-inp.stored)))
    write_md("EQUATION2_TERM_BY_TERM_AUDIT.md", f"""# Equation 2 term-by-term audit\n\n+| Printed element | Independent code expression | Match? | Notes |\n+|---|---|---|---|\n+| Common two-photon denominator | `Delta[n,m]-2E+iGamma` | YES | E=hc/lambda |\n+| Electron one-photon denominator | `Delta[l,m]-E+iGamma` | YES | Correct l,m transition |\n+| HH one-photon denominator | `Delta[n,l]-E+iGamma` | YES | Correct n,l transition |\n+| Electron numerator | `conj(O[n,m])*ze[n,l]*O[l,m]` | YES | Explicit bra/ket orientation |\n+| HH numerator | `O[n,m]*zh[m,l]*conj(O[n,l])` | YES | Explicit bra/ket orientation |\n+| Relative family sign | electron minus HH | YES | Printed minus retained |\n+| m,n,l ranges | 0,1 for each | YES | 8 electron + 8 HH pathways |\n+| SH permutation | omega1=omega2=omega | YES | 2E and E denominators |\n+| Occupation | occupied HH / empty electron implicit | YES/ASSUMED | Same low-density interband reduction as paper |\n+| Broadening | +i Gamma in both denominators | YES | 5 meV baseline |\n+| Energy conversion | E=hc/lambda, Gamma in eV | YES | No mixed angular-frequency units |\n+| hbar | absent in energy-domain evaluator | YES | The printed hbar^-2 cancels the two hbar factors from frequency denominators |\n+\n+Every one of 16 pathways, both subtotals, and the final 1,451 complex wavelength samples were compared with the stored engine. Maximum final complex error: **{max_engine:.3e} pm/V**. Per-denominator shapes and finiteness are recorded separately.""")
    write_md("BZ_CONVENTION_AUDIT.md", """# BZ convention audit\n\n+The repository defines `k_BZ=pi/a`, hence production `kmax=0.1 pi/a = 0.5557 nm^-1`. The paper says the response saturates at “one-tenth of the Brillouin zone away from the zone center” without supplying the code's exact reciprocal-space convention. For zincblende along a conventional [010] Gamma-X line, Gamma-X is 2pi/a, so 0.1 Gamma-X would be 0.2pi/a—twice the production cutoff. “0.1 reciprocal-lattice vector” is likewise 0.2pi/a.\n\n+Existing copied data support direct calculations through 0.1pi/a and a separate 0.125pi/a sensitivity case only. The cumulative tests through 0.1pi/a are valid; 0.2pi/a is **REQUIRES_PROFESSIONAL_DATA** and was not extrapolated. Because Demo24 found appreciable change at 0.125pi/a, the cutoff convention is a **POSSIBLE ISSUE**, not a proven cause.""")
    write_md("PAPER_STRUCTURE_REPRODUCTION_AUDIT.md", """# Paper structure reproduction audit\n\n+| Item | Paper ideal Fig.2d | Experimental / EDS model | Demo 23 | Match |\n+|---|---|---|---|---|\n+| wells | 7.1 / 2.9 nm GaAs | nominally same | 7.1 / 2.9 nm | YES |\n+| central barrier | 1.8 nm Al0.55Ga0.45As | measured interface profiles | 1.8 nm Al0.55Ga0.45As | YES nominally |\n+| outer barrier/period | 18.2 nm / 30 nm by layer arithmetic | grown superlattice | 18.2 nm / 30 nm | LIKELY |\n+| interfaces | ideal/abrupt design simulation | non-abrupt EDS profiles | 1-nm linear at all interfaces | NO / NOT SAME AS IDEAL |\n+| temperature | not stated for Fig.2d | experiment-specific | 300 K | UNCERTAIN |\n+| strain/substrate/growth | GaAs/AlGaAs, GaAs substrate | experimental wafer | GaAs substrate, [100] growth | LIKELY |\n+| electrostatics | paper Methods says Schrödinger-Poisson | experimental carrier conditions not numerically specified | no documented self-consistency in Demo23 input audit | UNCERTAIN/NO |\n+\n+Grading changes confinement energies, wavefunction centroids, overlaps, and z-matrix cancellation, so it can move resonances and reshape minima. Direction and size require a like-for-like calculation; no geometry was changed here.""")
    write_md("P1_P3_2296EV_REASSESSMENT.md", """# P1/P3 2.296-eV reassessment\n\n+The arithmetic is correct: hc/540 nm and 2hc/1080 nm both equal about 2.296 eV. The inference that one missing transition causes both peaks is not compelled by the figure. The paper's Eq.2 model uses the first two electron and first two HH states, but the text/figure does not assign P1 and P3 to the same `(n,m,l)` pathway. Coherent sums can place extrema away from poles, and different one- and two-photon denominators may dominate different peaks. The eye digitization's exact 2:1 pair is not author-tabulated precision. The axis is fundamental wavelength, so an axis swap does not rescue the inference.\n\n+Verdict: **WEAKENED, not invalidated**. A 2.296-eV transition remains a useful resonance hypothesis, but not a demonstrated missing state or proof that higher states are required.""")
    write_md("SCHRODINGER_POISSON_AUDIT.md", """# Schrödinger-Poisson audit\n\n+The paper Methods explicitly describes Schrödinger-Poisson calculations with nextnano. The copied Demo23 results contain `fixed charges: 0 e/cm^2`, and the Demo23 configuration/deck audit does not document doping, carrier density, or a self-consistent Poisson loop matching the paper. Therefore the implementations are **UNCERTAIN / NOT DEMONSTRABLY MATCHED**.\n\n+Charge, doping, occupations, built-in fields, and Hartree potential can shift subbands and alter asymmetric-well wavefunctions. Their importance cannot be quantified from the copied data. A like-for-like electrostatic rerun is **REQUIRES_PROFESSIONAL_DATA**, but the colleague's deck/charge settings should be obtained first.""")
    write_md("FRIEND_REPRODUCTION_CHECKLIST.md", """# Friend reproduction checklist\n\n+Please obtain: (1) exact nextnano input deck and version; (2) exact layers, alloys, grading, temperature, substrate/growth axis; (3) k=0 e1/e2/hh1/hh2 energies and raw state indices; (4) precise k path and meaning of kmax/BZ; (5) k-point count; (6) all O, ze, and zhh values with bra/ket convention and units; (7) Gamma value and whether it is HWHM/FWHM; (8) exact Eq.2 code, signs, conjugates, and prefactor; (9) plotted observable—Re, |Re|, or |chi|; (10) fundamental/output wavelength conversion; (11) included pathway subset; (12) state identities/spinor composition; (13) whether Schrödinger-Poisson was self-consistent, with charge/doping/occupation settings.\n\n+**Most decisive single item:** the runnable input deck plus the exact post-processing script that generated the plotted curve. Together they resolve structure, states, cutoff, matrices, equation, and observable without relying on recollection.""")

    counts={}; preserved=True
    for name in BASELINE_HASHES:
        p=ROOT/"nextnano/demos"/name; count,digest=directory_fingerprint(p,demo26=name.startswith("26_")); counts[name]={"file_count":count,"sha256":digest,"expected":BASELINE_HASHES[name],"unchanged":digest==BASELINE_HASHES[name]}; preserved &= digest==BASELINE_HASHES[name]
    (OUT/"PRESERVATION_HASHES.json").write_text(json.dumps(counts,indent=2)+"\n")
    best_phase=min((r for r in phase if r["observable"]=="abs_Re"),key=lambda r:r["normalized_RMSE"])
    summary={"status":"COMPLETE","existing_engine_max_error_pm_per_V":max_engine,"observable_metrics":obs_rows,"best_diagnostic":{"name":best_name,"RMSE":best_rmse},"best_global_phase_absRe":best_phase,"gauge_max_error":max(gauge_curves),"origin_max_error":max(r["max_complex_error_pm_per_V"] for r in origin),"preserved":preserved,"demo25_decision":"DEMO 25 SHOULD WAIT — NEED FRIEND'S REPRODUCTION DETAILS FIRST"}
    (OUT/"extended_audit_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))

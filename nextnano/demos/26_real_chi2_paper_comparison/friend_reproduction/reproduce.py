"""Portable Demo 26 reproduction. Run: python reproduce.py [--mode baseline]."""
from pathlib import Path
import argparse
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
HC = 1239.841984  # photon energy (eV) = HC / wavelength (nm)


def baseline(wavelength, data):
    """Historical Demo 22 algebra on the real inputs consumed by Demo 26."""
    k = np.array(data["k_per_nm"])
    ee, hh = np.array(data["electron_eV"]), np.array(data["valence_eV"])
    o, ze, zh = (np.array(data[key]) for key in ("overlap", "ze_nm", "zh_nm"))
    transition = ee[:, None, :] - hh[None, :, :]
    dk = np.empty_like(k)
    dk[0], dk[-1] = (k[1]-k[0])/2, (k[-1]-k[-2])/2
    dk[1:-1] = (k[2:]-k[:-2])/2
    weights = 2 * k * dk / (2 * np.pi)  # spin degeneracy 2
    q, eps0 = 1.602176634e-19, 8.8541878128e-12
    factor = (1/30e-9) * q**3 * (0.751e-9)**2 / (6*eps0)
    factor *= 1e-9 * 1e18 / q**2 * 1e12  # nm, eV, k units -> pm/V
    photon = HC / wavelength[:, None]
    total = np.zeros((len(wavelength), len(k)), complex)
    for m in range(2):
        for n in range(2):
            d2 = transition[n,m] - 2*photon + 1j*0.005
            for ell in range(2):
                d1 = transition[ell,m] - photon + 1j*0.005
                total += o[n,m]*ze[n,ell]*o[ell,m] / (d2*d1)
                d1 = transition[n,ell] - photon + 1j*0.005
                total -= o[n,m]*zh[m,ell]*o[n,ell] / (d2*d1)
    return factor * (total @ weights)


def log_integral(m1, a, m2, b, cutoff_squared):
    """Integral of 2*pi*k/((m1*k^2+a)*(m2*k^2+b)) from 0 to K."""
    c = m2*a - m1*b
    c = np.where(np.abs(c) < 1e-14, 1e-14+0j, c)
    return np.pi * (np.log((m2*cutoff_squared+b)/b)
                    - np.log((m1*cutoff_squared+a)/a)) / c


def diagnostic(wavelength, data, gamma_sign=-1):
    """Exact historical cutoff diagnostic; NOT the original baseline model."""
    energy, curvature = np.array(data["energy_eV"]), np.array(data["curvature_eV_nm2"])
    o, ze, zh = (np.array(data[key]) for key in ("overlap", "ze_nm", "zh_nm"))
    photon, g = HC/wavelength, gamma_sign*1j*0.005
    k2 = (0.1*2*np.pi/0.56533)**2
    total = np.zeros(len(wavelength), complex)
    for m in range(2):
        for n in range(2):
            a = energy[n]-energy[m+2]-2*photon+g
            m1 = abs(curvature[n]-curvature[m+2])
            for ell in range(2):
                b = energy[ell]-energy[m+2]-photon+g
                m2 = abs(curvature[ell]-curvature[m+2])
                total -= o[n,m]*ze[n,ell]*o[ell,m]*log_integral(m1,a,m2,b,k2)
                b = energy[n]-energy[ell+2]-photon+g
                m2 = abs(curvature[n]-curvature[ell+2])
                total += o[n,m]*zh[m,ell]*o[n,ell]*log_integral(m1,a,m2,b,k2)
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["diagnostic", "baseline"], default="diagnostic")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    data = json.loads((HERE/"inputs.json").read_text())
    wavelength = np.arange(400., 1851.)
    chi = (diagnostic if args.mode == "diagnostic" else baseline)(wavelength, data[args.mode])
    reference = np.loadtxt(HERE/"data"/(args.mode+"_reference.csv"), delimiter=",", skiprows=1)
    error = float(np.max(np.abs(chi-(reference[:,1]+1j*reference[:,2]))))
    tolerance = 1e-4 if args.mode == "diagnostic" else 1e-8
    if not np.all(np.isfinite(chi)) or error > tolerance:
        raise RuntimeError(f"Reference comparison failed: {error}, tolerance {tolerance}")
    out = args.output or HERE/"results"/args.mode
    out.mkdir(parents=True, exist_ok=True)
    paper = np.loadtxt(HERE/"data/paper.csv", delimiter=",", skiprows=1)
    paper_norm = paper[:,1]/paper[:,1].max()
    scale = np.max(np.abs(chi.real))
    np.savetxt(out/"spectrum.csv", np.column_stack([wavelength, chi.real, chi.imag,
               np.abs(chi.real), np.abs(chi), chi.real/scale, chi.imag/scale]),
               delimiter=",", header="wavelength_nm,real,imag,abs_real,magnitude,real_normalized,imag_normalized", comments="")
    for components in [False, True]:
        fig, ax = plt.subplots(figsize=(10,4.8))
        ax.plot(paper[:,0], paper_norm, "ko--", ms=4, lw=1.3, label="paper Fig. 2d")
        if components:
            ax.axhline(0, color="0.6", lw=0.9, zorder=0)
            ax.plot(wavelength, chi.real/scale, color="crimson", lw=2, label=r"Re $\chi^{(2)}$")
            ax.plot(wavelength, chi.imag/scale, color="steelblue", lw=1.8, label=r"Im $\chi^{(2)}$")
        else:
            ax.plot(wavelength, np.abs(chi.real)/scale, color="crimson", lw=2, label=r"$|\mathrm{Re}\,\chi^{(2)}|$")
            ax.plot(wavelength, np.abs(chi)/np.abs(chi).max(), color="darkgreen", ls=":", lw=1.8, label=r"$|\chi^{(2)}|$")
            ax.set_ylim(0,1.1)
        ax.set(xlabel="fundamental wavelength (nm)", ylabel=r"normalized $\chi^{(2)}$", xlim=(400,1850))
        ax.spines[["top","right"]].set_visible(False)
        ax.legend(loc="upper left", frameon=False)
        fig.tight_layout()
        fig.savefig(out/("paper_re_im.png" if components else "paper_magnitudes.png"), dpi=200)
        plt.close(fig)
    crossings = []
    for i in np.where(chi.real[:-1]*chi.real[1:] < 0)[0]:
        fraction = -chi.real[i]/(chi.real[i+1]-chi.real[i])
        crossings.append({"wavelength_nm":float(wavelength[i]+fraction),
                          "imag_normalized":float((chi.imag[i]+fraction*(chi.imag[i+1]-chi.imag[i]))/scale)})
    info = {"mode":args.mode,"reference_max_complex_error":error,"tolerance":tolerance,
            "component_normalization":float(scale),"zero_crossings_linear_interpolation":crossings,
            "units":"unscaled diagnostic response" if args.mode=="diagnostic" else "historical pm/V convention",
            "gamma_sign":-1 if args.mode=="diagnostic" else 1,
            "python_numpy":np.__version__,"matplotlib":matplotlib.__version__}
    (out/"verification.json").write_text(json.dumps(info,indent=2))
    print(json.dumps(info,indent=2))
    print(f"Plots and spectrum written to {out}")


if __name__ == "__main__":
    main()

"""29C: same-temperature mixed-model Equation 2 control."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .acquisition import ROOT, config
from .artifacts import save_inputs, save_spectrum, write_json
from .diagnostics import features
from .equation2 import Settings, calculate_chi2
from .input_builder import build_inputs
from .transfer import validate


def calculate(bundle: Path, output: Path) -> dict:
    status = validate(bundle)
    c = config()
    t = status["temperature_K"]
    if output.exists():
        raise ValueError("Refusing to overwrite mixed-control output")
    inputs, parsed = build_inputs(bundle / "mixed")
    if len(inputs["k_per_nm"]) != 301 or abs(float(inputs["k_per_nm"][-1]) - c["k_max_per_nm"]) > 5e-10:
        raise ValueError("Mixed-control k grid differs from full-8-band acquisition")
    settings = Settings(**c["settings"])
    wave = c["wavelength_nm"]
    wavelength = np.arange(wave["min"], wave["max"] + wave["step"]/2, wave["step"])
    spectrum = calculate_chi2(wavelength, inputs, settings)
    if not np.isfinite(spectrum.chi2_complex).all():
        raise ValueError("Nonfinite mixed-control susceptibility")
    output.mkdir(parents=True)
    save_inputs(output / "chi2_inputs", inputs, settings, wavelength)
    save_spectrum(output / "chi2_results", spectrum)
    f = features(wavelength, spectrum.chi2_complex,
                 lambda x: calculate_chi2(x, inputs, settings).chi2_complex)
    result = {"temperature_K": t, "model": "same-temperature mixed 8-band/single-band control",
              "full8_primary": False, "kp8_pair_ids": inputs["kp8_pair_ids"],
              "features": f, "finite": True, "gamma_meV": settings.gamma_meV,
              "source_bundle": str(bundle.resolve()),
              "limitations": inputs["limitations"]}
    write_json(output / "metadata.json", result)
    for component, values in (("real", spectrum.chi2_complex.real),
                              ("imag", spectrum.chi2_complex.imag),
                              ("abs_real", abs(spectrum.chi2_complex.real))):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(wavelength, values, label=f"{t} K")
        ax.set(xlabel="fundamental wavelength (nm)", ylabel=r"$\chi^{(2)}$ (pm/V)")
        ax.legend(frameon=False)
        fig.tight_layout()
        folder = output / "plots"
        folder.mkdir(exist_ok=True)
        fig.savefig(folder / f"mixed_{component}.png", dpi=180)
        plt.close(fig)
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    try:
        result = calculate(a.input, a.output or ROOT / "outputs/29C_mixed_control" / a.input.name)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

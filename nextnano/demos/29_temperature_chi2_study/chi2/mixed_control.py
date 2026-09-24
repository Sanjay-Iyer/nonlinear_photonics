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

from .acquisition import ROOT, config, job_decks
from .artifacts import save_inputs, save_spectrum, write_json
from .diagnostics import features
from .equation2 import Settings, calculate_chi2
from .input_builder import build_inputs
from .transfer import validate
from . import decks, parse_nextnano as io


def validate_control_run(run_root: Path) -> dict:
    """Validate the original matched solver pair when full-k spinors are absent."""
    c = config()
    report = json.loads((run_root / "run_metadata.json").read_text(encoding="utf-8"))
    t = int(report["temperature_K"])
    if (t not in c["temperatures_K"] or report.get("pilot") or
            not report.get("professional_execution_performed") or
            report.get("source_config") != c):
        raise ValueError("Control run is not a matching Demo 29 production pair")
    if set(report.get("jobs", {})) != {"kp8", "singleband_case04_graded"} or any(
            job.get("status") != "PASS" for job in report["jobs"].values()):
        raise ValueError("Both same-temperature solver jobs must have passed")
    for name, expected in job_decks(t, c).items():
        actual = (run_root / "decks" / f"{name}.in").read_text(encoding="utf-8")
        if not decks.same_deck(actual, expected):
            raise ValueError(f"Executed {name} deck differs from Demo 29 configuration")
    k, energy, direction = io.read_dispersion(run_root / "kp8")
    expected_k = np.linspace(0, c["k_max_per_nm"], c["k_points"])
    if (energy.shape != (c["k_points"], c["num_electrons"] + c["num_holes"]) or
            not np.allclose(k, expected_k, atol=5e-10, rtol=0) or
            not np.allclose(direction["direction"], [0, 1, 0], atol=1e-7)):
        raise ValueError("Control run has wrong 301-point 0.10 pi/a dispersion")
    io.read_single_band(run_root / "singleband_case04_graded")
    composition = (io.find_optional(run_root / "kp8", "k00000/spinor_composition_CbHhLhSo.dat") or
                   io.find_one(run_root / "kp8", "spinor_composition_k00000_CbHhLhSo.dat"))
    fractions = io.read_composition(composition)
    if any(len(fractions[name]) != energy.shape[1] for name in io.KP8_COMPONENTS):
        raise ValueError("k=0 composition does not cover all candidate states")
    return {"status": "PASS", "temperature_K": t, "k_points": len(k),
            "source_format": "original_solver_run", "full8_frames_present": False}


def calculate(bundle: Path, output: Path) -> dict:
    if (bundle / "bundle.json").is_file():
        status = validate(bundle)
        mixed_source = bundle / "mixed"
    else:
        status = validate_control_run(bundle)
        mixed_source = bundle
    c = config()
    t = status["temperature_K"]
    if output.exists():
        raise ValueError("Refusing to overwrite mixed-control output")
    inputs, parsed = build_inputs(mixed_source)
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
              "source_format": status.get("source_format", "full8_numeric_bundle"),
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

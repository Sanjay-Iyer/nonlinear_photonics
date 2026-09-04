"""Validated Equation 2 adapter and frozen k=0 inputs for Demo 23."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from config23 import DEMO_DIR, REPO_ROOT, Demo23Error
from dispersion_models import SubbandDispersion
import k_integration
from transition_energies import TransitionEnergies, assert_k0_matches, build_transition_energies


DEMO20 = DEMO_DIR.parent / "20_quantum_well_interface_grading_scaled"
DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
for module_dir in (DEMO20, DEMO22):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
import s06_chi2 as validated  # noqa: E402
import chi2_22  # noqa: E402


@dataclass(frozen=True)
class FrozenK0Inputs:
    states: validated.CaseStates
    overlap_eh: np.ndarray
    z_e_nm: np.ndarray
    z_hh_nm: np.ndarray
    source: Path


@dataclass(frozen=True)
class ModeResult:
    mode: str
    subbands_eV: Mapping[str, np.ndarray]
    transitions: TransitionEnergies
    spectrum: chi2_22.KResolvedSpectrum

    @property
    def magnitude(self) -> np.ndarray:
        return np.abs(self.spectrum.chi2)


def _matrix(prefix: str, row: Mapping[str, str]) -> np.ndarray:
    return np.asarray([
        [float(row[f"{prefix}11"]), float(row[f"{prefix}12"])],
        [float(row[f"{prefix}21"]), float(row[f"{prefix}22"])],
    ])


def load_frozen_k0_inputs(cfg: Mapping[str, Any]) -> FrozenK0Inputs:
    source = Path(str(cfg["chi2"]["frozen_matrix_source"]))
    if not source.is_absolute():
        source = REPO_ROOT / source
    if not source.is_file():
        raise Demo23Error(f"validated Demo 20/21 input table is missing: {source}")
    wanted = str(cfg["chi2"]["frozen_matrix_case_id"])
    with source.open(newline="", encoding="utf-8") as handle:
        row = next((item for item in csv.DictReader(handle) if item["case_id"] == wanted), None)
    if row is None:
        raise Demo23Error(f"case {wanted} is missing from {source}")
    electron = np.asarray([float(row["E1_eV"]), float(row["E2_eV"])])
    holes = np.asarray([float(row["HH1_eV"]), float(row["HH2_eV"])])
    overlap = _matrix("O", row)
    z_e = np.asarray([
        [float(row["z_e11_nm"]), float(row["z_e12_nm"])],
        [float(row["z_e21_nm"]), float(row["z_e22_nm"])],
    ])
    z_hh = np.asarray([
        [float(row["z_hh11_nm"]), float(row["z_hh12_nm"])],
        [float(row["z_hh21_nm"]), float(row["z_hh22_nm"])],
    ])
    states = validated.CaseStates(
        wanted, electron, holes, overlap, z_e, z_hh,
        f"licensed Demo 19 table used by Demo 20/21: {source}",
    )
    return FrozenK0Inputs(states, overlap, z_e, z_hh, source)


def settings_from_config(cfg: Mapping[str, Any]) -> validated.Chi2Settings:
    return validated.Chi2Settings(
        broadening_meV=float(cfg["chi2"]["broadening_meV"]),
        r_e_hh_nm=float(cfg["chi2"]["r_e_hh_nm"]),
        n_wells_per_metre=float(cfg["chi2"]["n_periods_per_metre"]),
        nz_mode="period_density",
        reference_period_nm=float(cfg["geometry"]["total_period_nm"]),
        max_states_per_band=int(cfg["chi2"]["max_states_per_band"]),
        k_parallel_fraction_of_bz=float(cfg["integration"]["fraction_of_bz"]),
        lattice_constant_nm=float(cfg["integration"]["lattice_constant_nm"]),
        bz_edge_convention=str(cfg["integration"]["bz_edge_convention"]),
        k_parallel_points=int(cfg["integration"]["production_points"]),
        electron_mass_m0=float(cfg["dispersion"]["baseline_electron_mass_m0"]),
        heavy_hole_inplane_mass_m0=float(cfg["dispersion"]["baseline_heavy_hole_mass_m0"]),
        spin_degeneracy=int(cfg["integration"]["spin_degeneracy"]),
        kspace_convention=validated.CONVENTION_DEMO19,
    )


def wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    block = cfg["chi2"]
    start, stop, step = (
        float(block["wavelength_min_nm"]),
        float(block["wavelength_max_nm"]),
        float(block["wavelength_step_nm"]),
    )
    return np.arange(start, stop + 0.5 * step, step)


def evaluate_mode(
    mode: str,
    model: SubbandDispersion,
    k_per_nm: np.ndarray,
    wavelengths_nm: np.ndarray,
    frozen: FrozenK0Inputs,
    settings: validated.Chi2Settings,
    *,
    k0_tolerance_eV: float,
) -> ModeResult:
    subbands = model.evaluate(k_per_nm)
    transitions = build_transition_energies(k_per_nm, subbands)
    assert_k0_matches(
        transitions, frozen.states.electron_energies_eV, frozen.states.hole_energies_eV,
        tolerance_eV=k0_tolerance_eV,
    )
    # chi2_22 is the existing generalized 16-pathway adapter. It constructs
    # this same transition tensor once and shares it across every pathway.
    spectrum = chi2_22.chi2_from_k_inputs(
        wavelengths_nm,
        k_per_nm,
        np.vstack([subbands["e1"], subbands["e2"]]),
        np.vstack([subbands["hh1"], subbands["hh2"]]),
        frozen.overlap_eh,
        frozen.z_e_nm,
        frozen.z_hh_nm,
        broadening_meV=settings.broadening_meV,
        settings=settings,
    )
    central_weights = k_integration.radial_weights(
        k_per_nm,
        spin_degeneracy=settings.spin_degeneracy,
        convention="d2k_over_2pi_squared",
    )
    if not np.allclose(spectrum.k_weights, central_weights, rtol=0.0, atol=1e-15):
        raise Demo23Error("Equation 2 adapter and central integration weights disagree")
    return ModeResult(mode, subbands, transitions, spectrum)


def baseline_regression_error(
    result_23a: ModeResult,
    frozen: FrozenK0Inputs,
    wavelengths_nm: np.ndarray,
    settings: validated.Chi2Settings,
) -> float:
    reference = validated.chi2_spectrum(frozen.states, wavelengths_nm, settings).chi2
    return float(np.max(np.abs(result_23a.spectrum.chi2 - reference)))


def pathway_summary(result: ModeResult, target_nm: float) -> dict[str, Any]:
    index = int(np.argmin(np.abs(result.spectrum.wavelength_nm - float(target_nm))))
    values = result.spectrum.terms[:, index]
    conduction = np.asarray([
        value for label, value in zip(result.spectrum.term_labels, values) if label.startswith("C_")
    ])
    valence = np.asarray([
        value for label, value in zip(result.spectrum.term_labels, values) if label.startswith("V_")
    ])
    order = np.argsort(np.abs(values))[::-1]
    return {
        "mode": result.mode,
        "wavelength_nm": float(result.spectrum.wavelength_nm[index]),
        "electron_side_real_pm_per_V": float(np.sum(conduction).real),
        "electron_side_imag_pm_per_V": float(np.sum(conduction).imag),
        "heavy_hole_side_real_pm_per_V": float(np.sum(valence).real),
        "heavy_hole_side_imag_pm_per_V": float(np.sum(valence).imag),
        "final_real_pm_per_V": float(result.spectrum.chi2[index].real),
        "final_imag_pm_per_V": float(result.spectrum.chi2[index].imag),
        "final_abs_pm_per_V": float(abs(result.spectrum.chi2[index])),
        "largest_pathways": "; ".join(
            f"{result.spectrum.term_labels[i]}={abs(values[i]):.8g}" for i in order[:5]
        ),
    }


def spectrum_metrics(result: ModeResult, reference: ModeResult | None = None) -> dict[str, Any]:
    wavelength = result.spectrum.wavelength_nm
    magnitude = result.magnitude
    target = float(np.interp(1550.0, wavelength, magnitude))
    peak_index = int(np.argmax(magnitude))
    if reference is None:
        relative = 0.0
    else:
        relative = float(
            np.sqrt(np.mean((magnitude - reference.magnitude) ** 2))
            / max(float(np.max(reference.magnitude)), 1e-300)
        )
    return {
        "mode": result.mode,
        "chi2_1550_pm_per_V": target,
        "peak_chi2_pm_per_V": float(magnitude[peak_index]),
        "peak_wavelength_nm": float(wavelength[peak_index]),
        "relative_spectrum_RMSE_vs_23D": relative,
    }

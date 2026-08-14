"""Demo 17d engine: ten declared prefactor combinations, scored against the paper.

WHERE THIS SITS
===============
Demo 17 closed the envelope side of the reproduction. Wavefunctions, energies,
the 1520 nm resonance position and the whole lineshape are converged, two
independently written Eq. 2 evaluators agree to 0.8 %, origin independence holds
at 1e-13, and the graded/abrupt ratio is right. One thing is left: a single
global scalar. ``case_02`` computes 84.70 pm/V where the paper reports 2340, a
factor of 27.63, and the same factor on every structure.

Demo 17b decomposed that scalar into candidate factors and recorded which ones a
cited source actually requires -- almost none of them. Demo 17c removed the
offset with one fitted K and reported everything else as a prediction.

Demo 17d asks the one question neither answered: if the candidates are
COMPOUNDED rather than swept one at a time or absorbed into a single fit, how do
they stack up across the spectrum, and does any combination land close to more
than one published number at once?

WHAT IS FITTED
==============
Nothing that reaches a reported number. Every multiplier is declared in
``demo17d.yaml``, checked against its stated total at load time, and applied as
written. The residual against each published value is measured and printed
whatever it turns out to be.

There is exactly one fit anywhere in this module, and it is quarantined:
:func:`_fit_cross_overlaps` recovers two matrix elements that Demo 17 did not
write into its hand-off, by matching **Demo 17's own stored outputs** -- never a
published number. It exists so the ten curves can be DRAWN. It moves no reported
value, because the two numbers this demo reports per case (chi2 at 1550 nm, and
the spectral peak) are read straight out of Demo 17's stored scalars and
multiplied. Setting ``spectrum.cross_overlap_model: zero`` turns even that off
and costs about 3 % on the drawn curve.

WHAT THE SWEEP CAN AND CANNOT RESOLVE
=====================================
It resolves the PRODUCT and nothing finer. Combos 07 and 08 both total 8.40x by
different routes and produce identical spectra, which is in the ensemble on
purpose: no ranking here can attribute the scale gap to a particular factor, and
a combination that hits a target is not thereby shown to be the right physics.
Combo 10 makes that sharpest -- its four factors multiply to 27.72 against a
measured residual of 27.63, so it was constructed to close the gap and
reproducing the anchor is arithmetic, exactly as Demo 17c's K is arithmetic.

THE FINDING THE ARITHMETIC FORCES
=================================
Demo 17's abrupt spectrum peaks at 145.78 pm/V and passes 84.70 at 1550 nm, a
peak/1550 contrast of 1.72. The paper's 2340 pm/V peak against ~1150 pm/V at
1550 nm implies 2.03. A scalar multiplier cannot change a ratio, so no
combination in this ensemble -- or any other ensemble of pure scalars -- can
match both. :func:`shape_versus_scale` measures that gap and reports it as the
structural limit on the whole exercise.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
for _path in (DEMOS / "_shared", DEMOS / "17b_prefactor_scale_audit"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prefactor_audit17b as audit17b  # noqa: E402

#: Stamped on every artifact. These are estimates under declared multipliers,
#: not predictions and not a calibrated reproduction.
ENSEMBLE_UNITS = "pm/V (Demo 17 raw value x a declared multiplier)"

ENSEMBLE_WARNING = (
    "Every multiplier here is DECLARED, not derived. A combination that lands "
    "near a published number has not thereby been shown to be the right "
    "physics: the sweep resolves the product of four factors and can never "
    "attribute it, two of the ten combinations are numerically identical by "
    "different routes, and one was constructed from the known residual. Read "
    "the ranking as a map of what each hypothesis would imply, not as evidence "
    "for any of them."
)

#: The four factors, in the order they compound and are reported.
FACTOR_ORDER: tuple[str, ...] = ("n_z", "permutation", "tensor", "dipole")

#: Demo 17b's verdict vocabulary, weakest last. A combination inherits the
#: weakest status among the factors it actually raises above 1.0.
STATUS_ORDER: tuple[str, ...] = (
    "established", "reported", "speculative", "contradicted",
)

STATUS_MARK = {
    "established": " ",
    "reported": "~",
    "speculative": "?",
    "contradicted": "!",
}


class Ensemble17dError(RuntimeError):
    """A sweep that would report a number it cannot stand behind."""


# ---------------------------------------------------------------------------
# The ensemble matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactorChoice:
    """One factor of one combination: how big, and what backs it."""

    key: str
    label: str
    multiplier: float
    status: str
    rationale: str

    @property
    def is_active(self) -> bool:
        """Whether this choice actually changes the result."""

        return self.multiplier != 1.0

    def as_record(self) -> dict[str, Any]:
        return {
            "factor": self.key,
            "label": self.label,
            "multiplier": self.multiplier,
            "status": self.status,
            "active": self.is_active,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class EstimationCombo:
    """One of the ten combinations, with its factors and its provenance."""

    combo_id: str
    name: str
    description: str
    choices: tuple[FactorChoice, ...]
    declared_total: float
    is_reconciliation_budget: bool = False

    @property
    def multiplier(self) -> float:
        product = 1.0
        for choice in self.choices:
            product *= float(choice.multiplier)
        return product

    @property
    def by_key(self) -> dict[str, FactorChoice]:
        return {choice.key: choice for choice in self.choices}

    @property
    def active_choices(self) -> tuple[FactorChoice, ...]:
        return tuple(choice for choice in self.choices if choice.is_active)

    @property
    def weakest_status(self) -> str:
        """The weakest evidence any RAISED factor rests on.

        A factor left at 1.0 contributes nothing, so it cannot weaken the
        combination -- Combo 01 is 'established' because it raises nothing.
        """

        active = self.active_choices
        if not active:
            return "established"
        return max((c.status for c in active), key=STATUS_ORDER.index)

    @property
    def status_mark(self) -> str:
        return STATUS_MARK.get(self.weakest_status, "?")

    @property
    def factor_signature(self) -> str:
        """``3.0 x 3.0 x 2.8 x 1.1`` -- what compounded to the total."""

        return " x ".join(f"{c.multiplier:g}" for c in self.choices)

    def as_record(self) -> dict[str, Any]:
        return {
            "combo_id": self.combo_id,
            "name": self.name,
            "description": self.description,
            "multiplier": self.multiplier,
            "declared_total": self.declared_total,
            "factor_signature": self.factor_signature,
            "weakest_active_status": self.weakest_status,
            "is_reconciliation_budget": self.is_reconciliation_budget,
            "factors": [choice.as_record() for choice in self.choices],
        }


def _variant_table(block: Mapping[str, Any], factor_key: str) -> dict[float, Any]:
    """``{multiplier: variant}`` with float keys, however YAML spelled them."""

    variants = block.get("variants")
    if not isinstance(variants, Mapping) or not variants:
        raise Ensemble17dError(
            f"factors.{factor_key}.variants is missing or empty in demo17d.yaml."
        )
    table: dict[float, Any] = {}
    for raw_key, entry in variants.items():
        try:
            value = float(raw_key)
        except (TypeError, ValueError) as exc:
            raise Ensemble17dError(
                f"factors.{factor_key}.variants has a non-numeric key {raw_key!r}."
            ) from exc
        table[value] = entry
    return table


def load_combos(cfg: Mapping[str, Any]) -> list[EstimationCombo]:
    """Build the ensemble, refusing any row whose arithmetic does not check out.

    Two things are verified rather than trusted:

    * the declared ``total`` equals the product of the four factors -- a typo in
      the ensemble matrix would otherwise print a multiplier the numbers were
      not computed with;
    * no combination raises a factor to a value the factor table does not
      define, so every multiplier that reaches a result carries a status and a
      rationale.
    """

    factors_cfg = cfg.get("factors")
    if not isinstance(factors_cfg, Mapping):
        raise Ensemble17dError("demo17d.yaml is missing the 'factors' block.")
    entries = cfg.get("combinations")
    if not entries:
        raise Ensemble17dError("demo17d.yaml defines no 'combinations'.")

    tables = {key: _variant_table(factors_cfg[key], key) for key in FACTOR_ORDER
              if key in factors_cfg}
    missing = [key for key in FACTOR_ORDER if key not in tables]
    if missing:
        raise Ensemble17dError(
            "demo17d.yaml's factors block is missing " + ", ".join(missing) + "."
        )

    combos: list[EstimationCombo] = []
    for entry in entries:
        combo_id = str(entry.get("id", "")).strip()
        if not combo_id:
            raise Ensemble17dError("a combination in demo17d.yaml has no 'id'.")
        choices: list[FactorChoice] = []
        for key in FACTOR_ORDER:
            if key not in entry:
                raise Ensemble17dError(
                    f"combination {combo_id} does not state its '{key}' factor."
                )
            value = float(entry[key])
            variant = _match_variant(tables[key], value, key, combo_id)
            choices.append(FactorChoice(
                key=key,
                label=str(factors_cfg[key].get("label", key)),
                multiplier=value,
                status=str(variant.get("status", "speculative")),
                rationale=str(variant.get("rationale", "")).strip(),
            ))
        combo = EstimationCombo(
            combo_id=combo_id,
            name=str(entry.get("name", f"combo {combo_id}")),
            description=str(entry.get("description", "")).strip(),
            choices=tuple(choices),
            declared_total=float(entry["total"]),
            is_reconciliation_budget=bool(entry.get("is_reconciliation_budget", False)),
        )
        if not math.isclose(combo.multiplier, combo.declared_total,
                            rel_tol=1.0e-9, abs_tol=1.0e-12):
            raise Ensemble17dError(
                f"combination {combo_id} ({combo.name}) declares total "
                f"{combo.declared_total:g} but its factors multiply to "
                f"{combo.multiplier:g} ({combo.factor_signature}). Fix the "
                "ensemble matrix; the demo will not report a multiplier the "
                "numbers were not computed with."
            )
        combos.append(combo)
    return combos


def _match_variant(
    table: Mapping[float, Any], value: float, key: str, combo_id: str
) -> Mapping[str, Any]:
    for candidate, variant in table.items():
        if math.isclose(candidate, value, rel_tol=1.0e-9, abs_tol=1.0e-12):
            return variant
    known = ", ".join(f"{v:g}" for v in sorted(table))
    raise Ensemble17dError(
        f"combination {combo_id} sets {key} = {value:g}, which the factors "
        f"table does not define (has: {known}). Add the variant with its status "
        "and rationale, or correct the combination -- an undocumented "
        "multiplier will not be applied."
    )


def exclusion_report(
    combos: Sequence[EstimationCombo], factors_cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """What the mutual-exclusion rule covers, and that the ensemble respects it.

    Demo 17b flagged the degenerate-SHG factor (2.0) and the Eq.1/Eq.2 ratio
    (3.0) as two readings of ONE piece of counting, so a combination that
    multiplied them would count it twice. Different ROWS may pick different
    readings -- that is the point of the sweep -- and one value per factor per
    row makes compounding them structurally impossible. This records which rows
    took which reading so that stays visible in the artifacts.
    """

    out: dict[str, Any] = {}
    for key, block in factors_cfg.items():
        if not isinstance(block, Mapping) or not block.get("mutually_exclusive_above_one"):
            continue
        usage: dict[str, list[str]] = {}
        for combo in combos:
            choice = combo.by_key.get(key)
            if choice is None or not choice.is_active:
                continue
            usage.setdefault(f"{choice.multiplier:g}x", []).append(combo.combo_id)
        out[key] = {
            "note": str(block.get("exclusion_note", "")).strip(),
            "readings_used": usage,
            "any_combination_multiplies_two_readings": False,
            "why_not": (
                "each combination states one value per factor, so two readings "
                "of the same counting cannot compound within a row"
            ),
        }
    return out


# ---------------------------------------------------------------------------
# The spectra
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseSpectrum:
    """One Demo 17 case: the two stored anchors, and a curve to draw them on.

    The distinction matters and is kept everywhere. ``stored_*`` came out of
    Demo 17 and are what this demo multiplies and reports. ``chi2_unit`` is the
    1400-1800 nm shape, which may have been rebuilt, and is only ever plotted.
    """

    case_id: str
    label: str
    role: str
    description: str
    stored_at_target: float
    stored_peak: float
    stored_peak_nm: float
    target_wavelength_nm: float
    provenance: str
    wavelength_nm: np.ndarray | None = None
    chi2_unit: np.ndarray | None = None
    fidelity: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @property
    def has_curve(self) -> bool:
        return self.wavelength_nm is not None and self.chi2_unit is not None

    @property
    def peak_over_target_contrast(self) -> float:
        """``peak / value at 1550 nm`` -- the one shape number a scalar cannot move."""

        return self.stored_peak / self.stored_at_target

    def scaled(self, multiplier: float):
        """The drawn curve for one combination. Reported numbers do not use this."""

        if not self.has_curve:
            return None, None
        return self.wavelength_nm, self.chi2_unit * float(multiplier)

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "label": self.label,
            "role": self.role,
            "description": self.description,
            "stored_chi2_at_1550_pm_per_V": self.stored_at_target,
            "stored_peak_pm_per_V": self.stored_peak,
            "stored_peak_wavelength_nm": self.stored_peak_nm,
            "peak_over_1550_contrast": self.peak_over_target_contrast,
            "curve_provenance": self.provenance,
            "curve_available": self.has_curve,
            "curve_points": int(self.wavelength_nm.size) if self.has_curve else 0,
            "rebuild_fidelity": dict(self.fidelity),
            "diagnostics": dict(self.diagnostics),
        }


def _wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    window = cfg["source"]["scan_window_nm"]
    step = float(cfg["source"].get("scan_step_nm", 1.0))
    start, stop = float(window[0]), float(window[1])
    if stop <= start or step <= 0:
        raise Ensemble17dError(
            f"source.scan_window_nm {window} with step {step} is not a usable grid."
        )
    return np.arange(start, stop + 0.5 * step, step)


def _stored_record(results_dir: Path, case_id: str) -> Mapping[str, Any]:
    summary = Path(results_dir) / "physics_summary.json"
    if not summary.is_file():
        raise Ensemble17dError(
            f"{summary} not found. Demo 17d reads Demo 17's hand-off; copy "
            "physics_summary.json (and demo17_master_summary.json) from the "
            "machine that ran the solver."
        )
    payload = json.loads(summary.read_text(encoding="utf-8"))
    for record in payload.get("cases", []):
        if str(record.get("case_id")) == case_id:
            optical = record.get("optical") or {}
            if optical.get("chi2_at_1550") is None:
                raise Ensemble17dError(
                    f"{case_id} has no recorded chi2 in {summary.name}; it did "
                    "not complete, so there is nothing to multiply."
                )
            return optical
    available = [str(r.get("case_id")) for r in payload.get("cases", [])]
    raise Ensemble17dError(f"{case_id} is not in {summary.name}; have {available}.")


def _spectrum_from_csv(
    optical: Mapping[str, Any], results_dir: Path, case_id: str, grid: np.ndarray
):
    """Demo 17's own chi2_focused.csv, if this hand-off happens to carry one.

    The columns follow Demo 17's writer: wavelength first, magnitude fourth.
    Values are interpolated onto the configured grid so every case is drawn on
    the same axis whichever tier supplied it.
    """

    candidates: list[Path] = []
    stored = optical.get("spectrum_path")
    if stored:
        candidates.append(Path(str(stored)))
    for name in (f"paper_target_{case_id}", case_id, "spectra"):
        candidates.append(Path(results_dir) / name / "chi2_focused.csv")
    candidates.append(Path(results_dir) / f"{case_id}_chi2_focused.csv")
    for candidate in candidates:
        try:
            if not candidate.is_file():
                continue
            data = np.loadtxt(candidate, delimiter=",", skiprows=1)
        except (OSError, ValueError):
            continue
        if data.ndim != 2 or data.shape[1] < 4:
            continue
        wavelength = np.asarray(data[:, 0], dtype=float)
        magnitude = np.abs(np.asarray(data[:, 3], dtype=float))
        order = np.argsort(wavelength)
        return np.interp(grid, wavelength[order], magnitude[order]), str(candidate)
    return None, None


def _k_weights(settings: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Demo 17's in-plane grid and ``(1/A) sum`` weights, in nm units.

    Mirrors ``_shared/chi2._k_grid``: ``(1/A) sum_k -> (1/2 pi) int k dk`` for an
    isotropic integrand, trapezoid weights, spin degeneracy folded in.
    """

    points = int(settings["k_parallel_points"])
    k = np.linspace(0.0, float(settings["k_max_per_nm"]), points)
    step = k[1] - k[0]
    weights = np.full(points, step)
    weights[0] = weights[-1] = 0.5 * step
    return k, weights * k / (2.0 * math.pi) * float(settings["spin_degeneracy"])


def _assemble_matrices(
    metrics: Mapping[str, Any], cross_e1_hh2: float, cross_e2_hh1: float,
    *, origin_shift_nm: float = 0.0,
):
    """The three Eq. 2 matrices, from the scalars Demo 17 wrote per case.

    Demo 17 recorded the two diagonal overlaps but not ``<e1|hh2>`` and
    ``<e2|hh1>``, which is why those two arrive as arguments rather than being
    read. ``origin_shift_nm`` moves the z origin, which shifts both bands'
    DIAGONAL position elements and leaves the off-diagonals alone -- Eq. 2's
    conduction and valence terms are built to cancel that exactly, so a
    nonzero shift is a correctness probe, not a transformation.
    """

    required = (
        "overlap_e1_hh1", "overlap_e2_hh2", "z_e1_e1_nm", "z_e1_e2_nm",
        "z_e2_e2_nm", "z_hh1_hh1_nm", "z_hh1_hh2_nm", "z_hh2_hh2_nm",
    )
    absent = [name for name in required if metrics.get(name) is None]
    if absent:
        raise Ensemble17dError(
            "this Demo 17 hand-off does not record " + ", ".join(absent)
            + ", so the 1400-1800 nm curve cannot be rebuilt from it."
        )
    overlap = np.array([
        [float(metrics["overlap_e1_hh1"]), float(cross_e1_hh2)],
        [float(cross_e2_hh1), float(metrics["overlap_e2_hh2"])],
    ], dtype=float)
    d = float(origin_shift_nm)
    z_e = np.array([
        [float(metrics["z_e1_e1_nm"]) + d, float(metrics["z_e1_e2_nm"])],
        [float(metrics["z_e1_e2_nm"]), float(metrics["z_e2_e2_nm"]) + d],
    ], dtype=float)
    z_h = np.array([
        [float(metrics["z_hh1_hh1_nm"]) + d, float(metrics["z_hh1_hh2_nm"])],
        [float(metrics["z_hh1_hh2_nm"]), float(metrics["z_hh2_hh2_nm"]) + d],
    ], dtype=float)
    return overlap, z_e, z_h


def _evaluate_curve(
    energies_e: np.ndarray, energies_h: np.ndarray,
    overlap: np.ndarray, z_e: np.ndarray, z_h: np.ndarray,
    wavelength_nm: np.ndarray, settings: Mapping[str, Any],
) -> np.ndarray:
    """Eq. 2 over the whole window at once, in Demo 17's production settings.

    This is the same sum ``_shared/chi2.chi2_spectrum`` performs -- energy-form
    denominators, the same k measure, the same prefactor -- vectorised over
    wavelength because the cross-overlap search evaluates it a few hundred
    times. :func:`verify_against_audit17b` checks it against Demo 17b's
    independently written angular-frequency kernel at every run, so the speedup
    never becomes an unchecked third implementation.
    """

    n_e, n_h = overlap.shape
    k, weights = _k_weights(settings)
    reduced_m0 = 1.0 / (
        1.0 / float(settings["electron_mass_m0"])
        + 1.0 / float(settings["heavy_hole_inplane_mass_m0"])
    )
    reduced_kg = reduced_m0 * audit17b.ELECTRON_MASS_KG
    k_per_m = k * 1.0e9
    kinetic_eV = (
        (audit17b.REDUCED_PLANCK_J_S ** 2) * k_per_m ** 2 / (2.0 * reduced_kg)
    ) / audit17b.ELEMENTARY_CHARGE_C

    transitions = (
        energies_e[:n_e, None] - energies_h[None, :n_h]
    )[:, :, None] + kinetic_eV[None, None, :]                       # (n, m, k)

    gamma = float(settings["broadening_meV"]) * 1.0e-3
    hw = (audit17b.HC_EV_NM / np.asarray(wavelength_nm, dtype=float))[:, None, None, None]
    two_photon = transitions[None] - 2.0 * hw + 1j * gamma          # (w, n, m, k)
    one_photon = transitions[None] - hw + 1j * gamma

    accumulated = np.zeros((hw.shape[0], k.size), dtype=complex)
    for m in range(n_h):
        for n in range(n_e):
            for l in range(n_e):
                numerator = overlap[n, m] * z_e[n, l] * overlap[l, m]
                if numerator:
                    accumulated += numerator / (
                        two_photon[:, n, m, :] * one_photon[:, l, m, :]
                    )
            for l in range(n_h):
                numerator = overlap[n, m] * z_h[m, l] * overlap[n, l]
                if numerator:
                    accumulated -= numerator / (
                        two_photon[:, n, m, :] * one_photon[:, n, l, :]
                    )

    prefactor = audit17b.production_prefactor_pm_per_V(
        n_wells_per_metre=float(settings["n_wells_per_metre"]),
        r_e_hh_nm=float(settings["r_e_hh_nm"]),
    )
    return np.abs(accumulated @ weights) * prefactor


def verify_against_audit17b(
    case: "audit17b.CaseArtifacts", overlap: np.ndarray, z_e: np.ndarray,
    z_h: np.ndarray, settings: Mapping[str, Any], wavelengths: Sequence[float],
) -> dict[str, Any]:
    """Check the vectorised sum against Demo 17b's kernel at a few wavelengths.

    Demo 17b writes Eq. 2 in ANGULAR FREQUENCY with hbar^2 left in the
    prefactor; the version above writes it in energy, where that hbar^2 cancels
    against the denominators. They are the same physics through a rewriting that
    is exactly the kind of step that can hide a factor, so they are made to
    agree on every run rather than once.
    """

    probe = replace(case, overlap_eh=overlap, z_e_nm=z_e, z_h_nm=z_h)
    reference = np.array([
        abs(audit17b.chi2_from_matrices(
            probe, float(w),
            n_wells_per_metre=float(settings["n_wells_per_metre"]),
            r_e_hh_nm=float(settings["r_e_hh_nm"]),
            k_max_per_nm=float(settings["k_max_per_nm"]),
            k_points=int(settings["k_parallel_points"]),
            spin_degeneracy=int(settings["spin_degeneracy"]),
            broadening_meV=float(settings["broadening_meV"]),
            electron_mass_m0=float(settings["electron_mass_m0"]),
            heavy_hole_inplane_mass_m0=float(settings["heavy_hole_inplane_mass_m0"]),
        )) for w in wavelengths
    ])
    ours = _evaluate_curve(
        case.electron_energies_eV, case.heavy_hole_energies_eV,
        overlap, z_e, z_h, np.asarray(wavelengths, dtype=float), settings,
    )
    scale = np.maximum(np.abs(reference), 1.0e-30)
    deviation = float(np.max(np.abs(ours - reference) / scale))
    return {
        "wavelengths_nm": [float(w) for w in wavelengths],
        "demo17b_angular_frequency_kernel_pm_per_V": reference.tolist(),
        "demo17d_vectorised_energy_form_pm_per_V": ours.tolist(),
        "max_relative_deviation": deviation,
        "agrees": deviation < 1.0e-9,
        "note": (
            "two independently written forms of Eq. 2 -- angular frequency with "
            "an explicit hbar^2, and energy denominators where it cancels"
        ),
    }


def _anchor_residuals(
    curve: np.ndarray, grid: np.ndarray, optical: Mapping[str, Any],
    target_nm: float,
) -> tuple[float, float, float, dict[str, Any]]:
    """How far a rebuilt curve sits from Demo 17's three stored anchors."""

    stored_1550 = float(optical["chi2_at_1550"])
    stored_peak = float(optical["spectral_peak_chi2"])
    stored_peak_nm = float(optical["spectral_peak_wavelength_nm"])
    index = int(np.argmax(curve))
    at_target = float(np.interp(target_nm, grid, curve))
    r_value = (at_target - stored_1550) / stored_1550
    r_peak = (float(curve[index]) - stored_peak) / stored_peak
    r_position = (float(grid[index]) - stored_peak_nm) / 10.0
    record = {
        "rebuilt_at_1550_pm_per_V": at_target,
        "stored_at_1550_pm_per_V": stored_1550,
        "at_1550_error_percent": r_value * 100.0,
        "rebuilt_peak_pm_per_V": float(curve[index]),
        "stored_peak_pm_per_V": stored_peak,
        "peak_error_percent": r_peak * 100.0,
        "rebuilt_peak_wavelength_nm": float(grid[index]),
        "stored_peak_wavelength_nm": stored_peak_nm,
        "peak_wavelength_error_nm": float(grid[index]) - stored_peak_nm,
    }
    return r_value, r_peak, r_position, record


def _fit_cross_overlaps(
    case: "audit17b.CaseArtifacts", metrics: Mapping[str, Any],
    optical: Mapping[str, Any], settings: Mapping[str, Any],
    cfg: Mapping[str, Any], target_nm: float,
) -> tuple[float, float, dict[str, Any]]:
    """Recover the two overlaps Demo 17 did not record, from Demo 17's own output.

    THE ONLY FIT IN THIS MODULE, and its target is never a published number --
    it is the trio of scalars Demo 17 itself stored (value at 1550 nm, peak
    height, peak position). Two unknowns against three constraints, so it is
    over-determined and the residual reported afterwards is a real check.

    It exists so the ten curves can be drawn through the points the table
    reports. No reported number depends on it; ``cross_overlap_model: zero``
    switches it off and lands within about 3 %.
    """

    block = cfg["spectrum"]
    limit = float(block.get("cross_overlap_search_limit", 0.3))
    points = int(block.get("cross_overlap_grid", 25))
    refinements = int(block.get("cross_overlap_refinements", 3))

    # Fit on a window around the stored resonance plus the target wavelength:
    # the three anchors all live there, and the full 1400-1800 grid would make
    # the search several times slower for no change in the answer.
    stored_peak_nm = float(optical["spectral_peak_wavelength_nm"])
    window = np.union1d(
        np.arange(stored_peak_nm - 60.0, stored_peak_nm + 60.0 + 0.5, 1.0),
        np.array([target_nm]),
    )

    def cost(a: float, b: float) -> tuple[float, dict[str, Any]]:
        overlap, z_e, z_h = _assemble_matrices(metrics, a, b)
        curve = _evaluate_curve(
            case.electron_energies_eV, case.heavy_hole_energies_eV,
            overlap, z_e, z_h, window, settings,
        )
        r_value, r_peak, r_position, record = _anchor_residuals(
            curve, window, optical, target_nm
        )
        return r_value ** 2 + r_peak ** 2 + r_position ** 2, record

    best_a = best_b = 0.0
    best_cost, best_record = cost(0.0, 0.0)
    zero_cost = best_cost
    span = limit
    centre_a = centre_b = 0.0
    for _ in range(max(1, refinements)):
        axis_a = np.linspace(centre_a - span, centre_a + span, points)
        axis_b = np.linspace(centre_b - span, centre_b + span, points)
        for a in axis_a:
            for b in axis_b:
                value, record = cost(float(a), float(b))
                if value < best_cost:
                    best_cost, best_a, best_b, best_record = value, float(a), float(b), record
        centre_a, centre_b = best_a, best_b
        span = 2.0 * span / (points - 1)

    return best_a, best_b, {
        "model": "fit_to_stored_anchors",
        "fitted_overlap_e1_hh2": best_a,
        "fitted_overlap_e2_hh1": best_b,
        "unknowns_fitted": 2,
        "constraints": 3,
        "fitted_to": "Demo 17's own stored chi2 at 1550 nm, peak height and peak "
                     "wavelength -- NOT to any published number",
        "cost_at_zero_cross_overlaps": zero_cost,
        "cost_at_fit": best_cost,
        "search_limit": limit,
        "grid_points_per_axis": points,
        "refinements": refinements,
        "affects_reported_numbers": False,
        **best_record,
    }


def _origin_independence(
    case: "audit17b.CaseArtifacts", metrics: Mapping[str, Any],
    cross: tuple[float, float], settings: Mapping[str, Any],
    cfg: Mapping[str, Any], target_nm: float,
) -> dict[str, Any]:
    """Move the z origin and confirm the assembled matrices do not care.

    Demo 17's diagonal position elements are ~38 nm because its z origin sits at
    the domain edge, while the susceptibility is a few tens of pm/V. Eq. 2's two
    terms are built to cancel that offset exactly, so re-evaluating with the
    origin moved is a free check that the 2x2 matrices were assembled
    consistently -- a transposed row or a mismatched band would break it.
    """

    shift = float(cfg["spectrum"].get("origin_independence_shift_nm", 100.0))
    tolerance = float(cfg["spectrum"].get("origin_independence_tolerance", 1.0e-9))
    probe = np.array([target_nm], dtype=float)
    values = []
    for offset in (0.0, shift):
        overlap, z_e, z_h = _assemble_matrices(
            metrics, cross[0], cross[1], origin_shift_nm=offset
        )
        values.append(float(_evaluate_curve(
            case.electron_energies_eV, case.heavy_hole_energies_eV,
            overlap, z_e, z_h, probe, settings,
        )[0]))
    base, shifted = values
    error = abs(shifted - base) / max(abs(base), 1.0e-30)
    return {
        "shift_nm": shift,
        "chi2_unshifted_pm_per_V": base,
        "chi2_shifted_pm_per_V": shifted,
        "relative_error": error,
        "tolerance": tolerance,
        "passed": error <= tolerance,
    }


def load_case_spectrum(
    results_dir: Path, case_cfg: Mapping[str, Any], cfg: Mapping[str, Any],
    *, cross_overlap_model: str | None = None,
) -> CaseSpectrum:
    """One case's stored anchors, plus the best curve this hand-off supports.

    Three tiers, and the artifact always says which one it got:

    1. ``demo17_spectrum_csv`` -- Demo 17's own sampled spectrum.
    2. ``eq2_rebuilt_from_recorded_matrix_elements`` -- Eq. 2 re-evaluated from
       the per-case matrix elements Demo 17 wrote into physics_summary.json.
    3. ``stored_anchors_only`` -- neither was available. The table is unchanged
       and complete; the figure falls back to markers and says so on the axes.
    """

    case_id = str(case_cfg["case_id"])
    target_nm = float(cfg["source"]["target_wavelength_nm"])
    grid = _wavelength_grid(cfg)
    optical = _stored_record(results_dir, case_id)
    base = CaseSpectrum(
        case_id=case_id,
        label=str(case_cfg.get("label", case_id)),
        role=str(case_cfg.get("role", "secondary")),
        description=str(case_cfg.get("description", "")).strip(),
        stored_at_target=float(optical["chi2_at_1550"]),
        stored_peak=float(optical["spectral_peak_chi2"]),
        stored_peak_nm=float(optical["spectral_peak_wavelength_nm"]),
        target_wavelength_nm=target_nm,
        provenance="stored_anchors_only",
    )

    if cfg["spectrum"].get("prefer_csv", True):
        curve, path = _spectrum_from_csv(optical, Path(results_dir), case_id, grid)
        if curve is not None:
            _, _, _, record = _anchor_residuals(curve, grid, optical, target_nm)
            return replace(
                base, wavelength_nm=grid, chi2_unit=curve,
                provenance="demo17_spectrum_csv",
                fidelity={"source_path": path, "nothing_was_rebuilt": True, **record},
            )

    metrics = optical.get("production_metrics") or {}
    try:
        case = audit17b.load_case(Path(results_dir), case_id)
    except audit17b.Audit17bError as exc:
        return replace(base, diagnostics={"rebuild_declined": str(exc)})

    settings = dict(case.settings)
    absent = [k for k in (
        "k_max_per_nm", "k_parallel_points", "spin_degeneracy", "broadening_meV",
        "electron_mass_m0", "heavy_hole_inplane_mass_m0", "n_wells_per_metre",
        "r_e_hh_nm",
    ) if settings.get(k) is None]
    if absent:
        return replace(base, diagnostics={
            "rebuild_declined": (
                "Demo 17's production settings are missing "
                + ", ".join(absent)
                + "; rebuilding on defaults would silently change the physics."
            )
        })

    model = str(cross_overlap_model or cfg["spectrum"].get(
        "cross_overlap_model", "fit_to_stored_anchors"))
    try:
        if model == "zero":
            cross = (0.0, 0.0)
            cross_record = {
                "model": "zero",
                "fitted_overlap_e1_hh2": 0.0,
                "fitted_overlap_e2_hh1": 0.0,
                "unknowns_fitted": 0,
                "note": ("Demo 17 recorded neither cross overlap; both are set to "
                         "zero and nothing is fitted anywhere in this run."),
                "affects_reported_numbers": False,
            }
        elif model == "fit_to_stored_anchors":
            a, b, cross_record = _fit_cross_overlaps(
                case, metrics, optical, settings, cfg, target_nm
            )
            cross = (a, b)
        else:
            raise Ensemble17dError(
                f"spectrum.cross_overlap_model is {model!r}; expected 'zero' or "
                "'fit_to_stored_anchors'."
            )
        overlap, z_e, z_h = _assemble_matrices(metrics, cross[0], cross[1])
        curve = _evaluate_curve(
            case.electron_energies_eV, case.heavy_hole_energies_eV,
            overlap, z_e, z_h, grid, settings,
        )
    except Ensemble17dError as exc:
        return replace(base, diagnostics={"rebuild_declined": str(exc)})

    _, _, _, residuals = _anchor_residuals(curve, grid, optical, target_nm)
    warn = float(cfg["spectrum"].get("fidelity_warn_percent", 5.0))
    worst = max(abs(residuals["at_1550_error_percent"]),
                abs(residuals["peak_error_percent"]))
    fidelity = {
        **cross_record,
        **residuals,
        "worst_anchor_error_percent": worst,
        "warn_threshold_percent": warn,
        "high_fidelity": worst <= warn,
        "reported_numbers_use_stored_anchors_not_this_curve": True,
    }
    diagnostics = {
        "loading_tier": case.tier,
        "source_paths": list(case.source_paths),
        "production_settings": settings,
        "origin_independence": _origin_independence(
            case, metrics, cross, settings, cfg, target_nm
        ),
        "kernel_agreement": verify_against_audit17b(
            case, overlap, z_e, z_h, settings,
            (float(grid[0]), target_nm, float(base.stored_peak_nm)),
        ),
    }
    return replace(
        base, wavelength_nm=grid, chi2_unit=curve,
        provenance="eq2_rebuilt_from_recorded_matrix_elements",
        fidelity=fidelity, diagnostics=diagnostics,
    )


# ---------------------------------------------------------------------------
# The published numbers, and the residuals against them
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperTarget:
    """One published absolute value, and which computed quantity it scores."""

    key: str
    label: str
    case_id: str
    quantity: str          # 'peak' | 'at_target_wavelength'
    value_pm_per_V: float
    source: str
    note: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "case_id": self.case_id,
            "quantity": self.quantity,
            "value_pm_per_V": self.value_pm_per_V,
            "source": self.source,
            "note": self.note,
        }


def load_targets(
    cfg: Mapping[str, Any], profile: str = "paper"
) -> tuple[list[PaperTarget], str]:
    """The scored published values, and which one heads the CSV's error column."""

    block = cfg["targets"] if profile == "paper" else cfg.get(f"targets_{profile}")
    if not block:
        raise Ensemble17dError(
            f"demo17d.yaml has no 'targets_{profile}' block; known profiles are "
            "'paper' and any targets_<name> section."
        )
    targets = [
        PaperTarget(
            key=str(entry["key"]),
            label=str(entry["label"]),
            case_id=str(entry["case_id"]),
            quantity=str(entry["quantity"]),
            value_pm_per_V=float(entry["value_pm_per_V"]),
            source=str(entry.get("source", "")).strip(),
            note=str(entry.get("note", "")).strip(),
        )
        for entry in block["entries"]
    ]
    headline = str(block.get("headline", targets[0].key))
    if headline not in {t.key for t in targets}:
        raise Ensemble17dError(
            f"targets.headline is {headline!r}, which is not one of "
            f"{sorted(t.key for t in targets)}."
        )
    return targets, headline


@dataclass(frozen=True)
class ComboOutcome:
    """One combination applied to every case, and scored against every target."""

    combo: EstimationCombo
    values: Mapping[str, Mapping[str, float]]     # case_id -> quantity -> pm/V
    residuals: Mapping[str, float]                # target key -> percent error
    aggregate_percent: float
    headline_key: str

    @property
    def headline_error_percent(self) -> float:
        return self.residuals[self.headline_key]

    def value(self, case_id: str, quantity: str) -> float:
        return self.values[case_id][quantity]

    def as_record(self) -> dict[str, Any]:
        return {
            **self.combo.as_record(),
            "values_pm_per_V": {
                case_id: dict(quantities)
                for case_id, quantities in self.values.items()
            },
            "target_errors_percent": dict(self.residuals),
            "aggregate_error_percent": self.aggregate_percent,
            "headline_target": self.headline_key,
            "headline_error_percent": self.headline_error_percent,
        }


def evaluate_ensemble(
    combos: Sequence[EstimationCombo], spectra: Sequence[CaseSpectrum],
    targets: Sequence[PaperTarget], headline: str,
    cfg: Mapping[str, Any],
) -> list[ComboOutcome]:
    """Apply each multiplier and measure every residual.

    The multiplied quantities come from Demo 17's STORED scalars, so they are
    exact whatever tier supplied the drawn curve -- a hand-off with no spectrum
    at all still produces the complete table.
    """

    by_case = {spectrum.case_id: spectrum for spectrum in spectra}
    unknown = sorted({t.case_id for t in targets} - set(by_case))
    if unknown:
        raise Ensemble17dError(
            "targets score " + ", ".join(unknown) + ", which source.cases does "
            "not load. Add the case or drop the target; scoring a case that was "
            "never evaluated would print an error against nothing."
        )
    aggregate_mode = str((cfg.get("scoring") or {}).get("aggregate", "rms_percent"))

    outcomes: list[ComboOutcome] = []
    for combo in combos:
        multiplier = combo.multiplier
        values = {
            spectrum.case_id: {
                "at_target_wavelength": spectrum.stored_at_target * multiplier,
                "peak": spectrum.stored_peak * multiplier,
                "peak_wavelength_nm": spectrum.stored_peak_nm,
            }
            for spectrum in spectra
        }
        residuals = {
            target.key: (
                values[target.case_id][target.quantity] - target.value_pm_per_V
            ) / target.value_pm_per_V * 100.0
            for target in targets
        }
        errors = np.array(list(residuals.values()), dtype=float)
        if aggregate_mode == "mean_abs_percent":
            aggregate = float(np.mean(np.abs(errors)))
        elif aggregate_mode == "max_abs_percent":
            aggregate = float(np.max(np.abs(errors)))
        else:
            aggregate = float(np.sqrt(np.mean(errors ** 2)))
        outcomes.append(ComboOutcome(
            combo=combo, values=values, residuals=residuals,
            aggregate_percent=aggregate, headline_key=headline,
        ))
    return outcomes


def rank_ensemble(
    outcomes: Sequence[ComboOutcome], targets: Sequence[PaperTarget],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Who is closest -- overall, and per target, because they disagree.

    The per-target winners are reported alongside the aggregate rather than
    collapsed into it. When one combination is closest to the abrupt numbers and
    a different one is closest to the graded number, that disagreement is the
    result; picking a single winner would hide it.
    """

    threshold = float((cfg.get("scoring") or {}).get("match_threshold_percent", 15.0))
    ordered = sorted(outcomes, key=lambda o: o.aggregate_percent)
    best = ordered[0]
    per_target = {}
    for target in targets:
        winner = min(outcomes, key=lambda o: abs(o.residuals[target.key]))
        per_target[target.key] = {
            "combo_id": winner.combo.combo_id,
            "combo_name": winner.combo.name,
            "multiplier": winner.combo.multiplier,
            "value_pm_per_V": winner.value(target.case_id, target.quantity),
            "target_pm_per_V": target.value_pm_per_V,
            "error_percent": winner.residuals[target.key],
        }
    winners = {entry["combo_id"] for entry in per_target.values()}
    return {
        "aggregate_metric": str((cfg.get("scoring") or {}).get("aggregate", "rms_percent")),
        "match_threshold_percent": threshold,
        "closest_overall": {
            "combo_id": best.combo.combo_id,
            "combo_name": best.combo.name,
            "multiplier": best.combo.multiplier,
            "aggregate_error_percent": best.aggregate_percent,
            "weakest_active_status": best.combo.weakest_status,
            "inside_threshold": best.aggregate_percent <= threshold,
        },
        "closest_per_target": per_target,
        "targets_agree_on_a_single_combination": len(winners) == 1,
        "combinations_winning_at_least_one_target": sorted(winners),
        "ranking": [
            {
                "rank": index + 1,
                "combo_id": outcome.combo.combo_id,
                "combo_name": outcome.combo.name,
                "multiplier": outcome.combo.multiplier,
                "aggregate_error_percent": outcome.aggregate_percent,
            }
            for index, outcome in enumerate(ordered)
        ],
        "caveat": ENSEMBLE_WARNING,
    }


def shape_versus_scale(
    spectra: Sequence[CaseSpectrum], targets: Sequence[PaperTarget]
) -> dict[str, Any]:
    """The part of the gap no multiplier in this ensemble can close.

    Every combination here is a scalar, and a scalar cannot change a ratio. So
    wherever the paper pins two quantities on the SAME case, their ratio is a
    fixed prediction of Demo 17's converged lineshape and the sweep is powerless
    over it. Measuring that first says how much of the residual is genuinely a
    scale question -- which is what Demo 17d is about -- and how much is not.
    """

    by_case = {spectrum.case_id: spectrum for spectrum in spectra}
    grouped: dict[str, dict[str, PaperTarget]] = {}
    for target in targets:
        grouped.setdefault(target.case_id, {})[target.quantity] = target

    comparisons = []
    for case_id, quantities in grouped.items():
        if "peak" not in quantities or "at_target_wavelength" not in quantities:
            continue
        spectrum = by_case[case_id]
        published = (quantities["peak"].value_pm_per_V
                     / quantities["at_target_wavelength"].value_pm_per_V)
        ours = spectrum.peak_over_target_contrast
        comparisons.append({
            "case_id": case_id,
            "label": spectrum.label,
            "our_peak_over_1550": ours,
            "published_peak_over_1550": published,
            "mismatch_percent": (ours - published) / published * 100.0,
            "best_possible_split_error_percent": _best_split_error(ours, published),
        })

    return {
        "definition": "spectral peak divided by the value at 1550 nm, same case",
        "why_it_matters": (
            "a scalar multiplier cannot change a ratio, so this mismatch "
            "survives every combination in the ensemble and sets a floor on how "
            "well any of them can do on both quantities at once"
        ),
        "comparisons": comparisons,
        "no_scalar_can_fix_these": [c["case_id"] for c in comparisons
                                    if abs(c["mismatch_percent"]) > 1.0],
    }


def _best_split_error(ours: float, published: float) -> float:
    """The error a perfectly chosen scalar still leaves on both quantities.

    Splitting the discrepancy evenly in log space is the best a single
    multiplier can do when it has to serve two targets whose ratio is wrong.
    """

    return abs(math.sqrt(ours / published) - 1.0) * 100.0


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


#: The seven columns the demo's schema requires, then the graded case and the
#: per-target residuals, which would otherwise have nowhere to live.
CSV_FIELDS: tuple[str, ...] = (
    "Combo_ID",
    "Combo_Name",
    "Multiplier",
    "Peak_chi2_pmV",
    "Peak_Wavelength_nm",
    "chi2_1550nm_pmV",
    "Target_Error_Percent",
    # --- beyond the required schema ---
    "Factor_Signature",
    "Weakest_Active_Status",
    "Graded_Peak_chi2_pmV",
    "Graded_Peak_Wavelength_nm",
    "Graded_chi2_1550nm_pmV",
    "Aggregate_Error_Percent",
)


def write_summary_csv(
    path: Path, outcomes: Sequence[ComboOutcome], spectra: Sequence[CaseSpectrum],
    targets: Sequence[PaperTarget], headline: str, decimals: int = 2,
) -> Path:
    """The master summary. Required columns first, in the schema's own names.

    ``Peak_chi2_pmV``, ``Peak_Wavelength_nm`` and ``chi2_1550nm_pmV`` are the
    PRIMARY case (the abrupt structure the paper quotes), and
    ``Target_Error_Percent`` is that case's residual against the headline
    target. The graded case gets its own prefixed columns rather than extra
    rows, so one row stays one combination.
    """

    primary = next((s for s in spectra if s.role == "primary"), spectra[0])
    secondary = next((s for s in spectra if s.case_id != primary.case_id), None)
    per_target_columns = [f"Error_vs_{t.key}_Percent" for t in targets]

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(list(CSV_FIELDS) + per_target_columns)
        for outcome in outcomes:
            row = [
                outcome.combo.combo_id,
                outcome.combo.name,
                round(outcome.combo.multiplier, 4),
                round(outcome.value(primary.case_id, "peak"), decimals),
                round(primary.stored_peak_nm, 1),
                round(outcome.value(primary.case_id, "at_target_wavelength"), decimals),
                round(outcome.residuals[headline], decimals),
                outcome.combo.factor_signature,
                outcome.combo.weakest_status,
                round(outcome.value(secondary.case_id, "peak"), decimals)
                if secondary else "",
                round(secondary.stored_peak_nm, 1) if secondary else "",
                round(outcome.value(secondary.case_id, "at_target_wavelength"), decimals)
                if secondary else "",
                round(outcome.aggregate_percent, decimals),
            ]
            row.extend(round(outcome.residuals[t.key], decimals) for t in targets)
            writer.writerow(row)
    return path


COMBO_COLOURS = (
    "#9aa7b1", "#4c72b0", "#dd8452", "#55a868", "#c44e52",
    "#8172b3", "#937860", "#da8bc3", "#0f7b8a", "#b5316a",
)


def _draw_styles(outcomes: Sequence[ComboOutcome]) -> list[dict[str, Any]]:
    """Per-combination line styling, made to expose numerically identical rows.

    Combos 07 and 08 both total 8.40x, so their curves coincide exactly and one
    would simply paint over the other -- hiding the very control they are in the
    ensemble to provide. Any multiplier used more than once is therefore drawn
    as a wide translucent band for the first row and a narrow dashed line for
    the rest, so a coincidence is visible AS a coincidence.
    """

    totals = [round(outcome.combo.multiplier, 9) for outcome in outcomes]
    seen: dict[float, int] = {}
    styles: list[dict[str, Any]] = []
    for multiplier in totals:
        rank = seen.get(multiplier, 0)
        seen[multiplier] = rank + 1
        if totals.count(multiplier) == 1:
            styles.append({"lw": 1.9, "linestyle": "-", "alpha": 0.95, "zorder": 3})
        elif rank == 0:
            styles.append({"lw": 5.0, "linestyle": "-", "alpha": 0.32, "zorder": 3})
        else:
            styles.append({"lw": 1.7, "linestyle": (0, (5, 3)), "alpha": 0.95,
                           "zorder": 4})
    return styles


def _plain_number_yaxis(axis: Any, log_scale: bool) -> None:
    """Label the susceptibility axis 100 / 200 / 500 / 1000, not 10^2 and 10^3.

    A log axis is the right choice here -- the ensemble spans 84 to 4041 pm/V,
    nearly two decades, and a linear axis would flatten the low combinations
    into the baseline. But matplotlib's default log labels are powers of ten,
    which puts the reader one mental step away from a number they can compare to
    "2340 pm/V". Decade ticks alone are also too sparse to read a value off: the
    whole spectrum lives between two of them.

    So the ticks go at 1, 2 and 5 per decade and are written out in full.
    """

    from matplotlib.ticker import (  # noqa: PLC0415
        FuncFormatter, LogLocator, NullFormatter, ScalarFormatter,
    )

    if not log_scale:
        formatter = ScalarFormatter(useOffset=False)
        formatter.set_scientific(False)
        axis.yaxis.set_major_formatter(formatter)
        return

    axis.yaxis.set_major_locator(
        LogLocator(base=10.0, subs=(1.0, 2.0, 5.0), numticks=32)
    )
    axis.yaxis.set_minor_locator(
        LogLocator(base=10.0, subs=tuple(x / 10.0 for x in range(1, 10)),
                   numticks=128)
    )
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    axis.yaxis.set_minor_formatter(NullFormatter())


def write_ensemble_figure(
    path: Path, outcomes: Sequence[ComboOutcome], spectra: Sequence[CaseSpectrum],
    targets: Sequence[PaperTarget], cfg: Mapping[str, Any],
) -> Path | None:
    """All ten combinations against the published bands, one panel per case.

    Degrades honestly. With no curve for a case the panel draws each
    combination's peak and 1550 nm values as markers instead of inventing a
    lineshape, and says so on the axes.
    """

    import plots  # noqa: PLC0415

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None
    import matplotlib.pyplot as plt  # noqa: PLC0415

    reporting = cfg.get("reporting") or {}
    band_percent = float(reporting.get("target_band_percent", 10.0))
    log_scale = bool(reporting.get("log_scale", True))
    target_nm = float(cfg["source"]["target_wavelength_nm"])
    by_case_targets: dict[str, list[PaperTarget]] = {}
    for target in targets:
        by_case_targets.setdefault(target.case_id, []).append(target)

    panels = len(spectra)
    styles = _draw_styles(outcomes)
    fig, axes = plt.subplots(
        panels, 1, figsize=(12.5, 5.2 * panels + 1.9), sharex=True,
    )
    axes = np.atleast_1d(axes)
    handles: list[Any] = []
    labels: list[str] = []

    for panel_index, (axis, spectrum) in enumerate(zip(axes, spectra)):
        for index, outcome in enumerate(outcomes):
            colour = COMBO_COLOURS[index % len(COMBO_COLOURS)]
            multiplier = outcome.combo.multiplier
            label = (f"{outcome.combo.combo_id} {outcome.combo.name} "
                     f"({multiplier:.2f}x){outcome.combo.status_mark}")
            wavelength, curve = spectrum.scaled(multiplier)
            if wavelength is not None:
                line, = axis.plot(wavelength, curve, color=colour, **styles[index])
            else:
                line = axis.scatter(
                    [spectrum.stored_peak_nm],
                    [outcome.value(spectrum.case_id, "peak")],
                    s=48, marker="^", color=colour, zorder=5,
                )
            axis.scatter([target_nm],
                         [outcome.value(spectrum.case_id, "at_target_wavelength")],
                         s=34, color=colour, edgecolor="white", linewidth=0.7,
                         zorder=6)
            if panel_index == 0:
                handles.append(line)
                labels.append(label)

        for offset, target in enumerate(by_case_targets.get(spectrum.case_id, [])):
            value = target.value_pm_per_V
            is_peak = target.quantity == "peak"
            if is_peak:
                axis.axhspan(value * (1 - band_percent / 100.0),
                             value * (1 + band_percent / 100.0),
                             color="#c0392b", alpha=0.12, zorder=1)
                axis.axhline(value, color="#c0392b", ls="--", lw=2.0, zorder=2)
            else:
                axis.axhline(value, color="#1f6f4a", ls=":", lw=1.8, zorder=2)
            axis.annotate(
                f"paper {target.label}: {value:.0f} pm/V"
                + (f"  (+-{band_percent:.0f}%)" if is_peak else ""),
                xy=(0.006 + 0.30 * offset, value), xycoords=("axes fraction", "data"),
                xytext=(0, 5), textcoords="offset points", fontsize=9,
                color="#c0392b" if is_peak else "#1f6f4a", fontweight="bold",
            )

        axis.axvline(target_nm, color="#222222", ls="--", lw=1.5, zorder=2)
        axis.annotate(f"{target_nm:.0f} nm", xy=(target_nm, 1.0),
                      xycoords=("data", "axes fraction"), xytext=(5, -14),
                      textcoords="offset points", fontsize=9.5, color="#222222")
        if log_scale:
            axis.set_yscale("log")
        _plain_number_yaxis(axis, log_scale)
        axis.set_ylabel(r"$|\chi^{(2)}_{xzx}|$ (pm/V)")
        axis.grid(alpha=0.2, which="both")
        title = (f"{spectrum.case_id} -- {spectrum.label} "
                 f"(peak {spectrum.stored_peak_nm:.0f} nm, "
                 f"peak/1550 = {spectrum.peak_over_target_contrast:.2f})")
        if not spectrum.has_curve:
            title += "  [markers only: no spectrum in this hand-off]"
        elif spectrum.provenance != "demo17_spectrum_csv":
            worst = spectrum.fidelity.get("worst_anchor_error_percent")
            title += ("  [lineshape rebuilt from recorded matrix elements"
                      + (f", within {worst:.2f} % of the stored anchors]"
                         if worst is not None else "]"))
        axis.set_title(title, fontsize=11)

    axes[-1].set_xlabel("fundamental wavelength (nm)")
    fig.legend(
        handles, labels, loc="lower center", ncol=4, fontsize=8.0, framealpha=0.95,
        title=("marks the weakest factor a row raises:   ~ reported (Demo 17b "
               "declined to promote)    ? speculative (no source here)    "
               "! contradicted (a measurement here points the other way)"),
        title_fontsize=8.0, bbox_to_anchor=(0.5, 0.005),
    )
    height = fig.get_figheight()
    fig.suptitle(
        "Demo 17d -- ten declared prefactor estimation combinations against the "
        "published absolute scale\n"
        "curves are Demo 17's converged lineshape times a declared multiplier; "
        "nothing here is fitted to a published number",
        fontsize=12.5, y=1.0 - 0.24 / height,
    )
    # Reserve the suptitle's two lines plus each panel's own title at the top,
    # and the four-column legend at the foot, in inches rather than fractions so
    # the margins hold however many panels there are.
    fig.subplots_adjust(top=1.0 - 1.32 / height, bottom=1.42 / height,
                        left=0.075, right=0.985, hspace=0.17)
    return plots.save_figure(fig, Path(path), tight=False)


def build_report(
    outcomes: Sequence[ComboOutcome], spectra: Sequence[CaseSpectrum],
    targets: Sequence[PaperTarget], headline: str, ranking: Mapping[str, Any],
    shape: Mapping[str, Any], exclusions: Mapping[str, Any],
    cfg: Mapping[str, Any], results_dir: Path, profile: str,
) -> dict[str, Any]:
    return {
        "demo_id": cfg["experiment"]["demo_id"],
        "source_results_dir": str(results_dir),
        "units": ENSEMBLE_UNITS,
        "targets_profile": profile,
        "no_scale_factor_was_fitted": True,
        "degrees_of_freedom_fitted_to_published_values": 0,
        "target_wavelength_nm": float(cfg["source"]["target_wavelength_nm"]),
        "scan_window_nm": list(cfg["source"]["scan_window_nm"]),
        "cases": [spectrum.as_record() for spectrum in spectra],
        "targets": [target.as_record() for target in targets],
        "headline_target": headline,
        "combinations": [outcome.as_record() for outcome in outcomes],
        "ranking": dict(ranking),
        "shape_versus_scale": dict(shape),
        "mutual_exclusions": dict(exclusions),
        "combinations_reported": len(outcomes),
        "warning": ENSEMBLE_WARNING,
    }

"""Demo 17c engine: one fitted scalar, then everything else is a prediction.

Demos 17 and 17b established where the reproduction stands. The lineshape, the
resonance position (3 nm from the paper's 1520), the graded/abrupt ratio (1.2 %),
the renderer equivalence (1e-13), the k-space normalisation, the dimensional
ledger, the unit-cell dipole and the spin weight are all settled. What is left is
a single global scalar: our evaluator sits 27.6x below the published scale on
every structure, by the same factor.

A constant offset on every case is exactly what a calibration removes, and this
module does that -- once, visibly, and with the result labelled a **calibrated
reproduction** rather than an absolute prediction, in the same way
``_shared/chi2.calibrate`` already labels its own.

WHY THE ANCHOR IS NOT BULK GaAs
===============================
The requested design was to anchor on bulk GaAs: evaluate chi(2) for bulk with
the same Eq. 2 evaluator, then set K = 377 / chi2_calc_bulk. That cannot be done,
and the reason is physical rather than practical.

Eq. 2 computes an ENVELOPE asymmetry:

    sum_mnl  <psi_hh,m|psi_e,n> <psi_e,n|z|psi_e,l> <psi_e,l|psi_hh,m> / (...)
           -  the matching valence term

Every factor is a confined-subband envelope integral. Bulk GaAs has no confined
envelopes, and -- decisively -- the two terms cancel EXACTLY for any symmetric
structure. The paper says so itself and this repository already carries it as a
target: ``chi2_zero_at_symmetric_limits: 0.0``. So the honest value of
``chi2_calc_bulk`` under Eq. 2 is **zero**, and ``K = 377 / 0`` is undefined.

Bulk GaAs's 377 pm/V is not an envelope effect at all. It comes from the
zincblende unit-cell bond asymmetry (d14) -- the same unit-cell physics that
``r_e_hh`` parameterises, and a different mechanism from the one Eq. 2 sums. That
is precisely why the paper reports the quantum well as an ENHANCEMENT OVER bulk
rather than as bulk plus a correction.

:func:`bulk_reference_evaluation` therefore refuses, explains, and offers the two
things that are defensible:

* 377 and 290 pm/V used as the **enhancement denominator and the plot's
  reference lines**, which is the role they actually play;
* an externally supplied ``chi2_calc_bulk_gaas_raw``, if a bulk number is ever
  produced by a theory that can produce one -- the plumbing is present and
  exercised the moment such a number exists.

WHAT IS FITTED, AND WHAT IS NOT
===============================
Exactly ONE real positive scalar K is fitted, to ONE published number. The anchor
is therefore not evidence -- reproducing it is arithmetic. The evidence is what
lands *without* further fitting:

    anchor      case_02 @ 1550 nm  ->  2340 pm/V   (Section 3.1, ideal abrupt)
    prediction  case_02 peak       ->  ~4000 pm/V  (Fig. 2d, digitised, +-15 %)
    prediction  case_09 @ 1550 nm  ->  1200 / 1363 pm/V (Section 3.1, EDS profiles)

Three published numbers, one fitted scalar. :func:`validate_predictions` reports
each one as a measured outcome and never adjusts anything to reach it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

import prefactor_audit17b as audit17b  # noqa: E402  (results-dir resolution reuse)

#: Stamped on every artifact. This is not an absolute prediction and must never
#: be reported as one.
CALIBRATED_UNITS = "pm/V (calibrated reproduction: one global scalar fitted to "
CALIBRATION_WARNING = (
    "One global scale factor was fitted to a single published value. The anchor "
    "case reproduces that value by construction and is NOT evidence. Every other "
    "number here is a prediction at the same scale, and the absolute magnitudes "
    "are a calibrated reproduction rather than an independent prediction."
)


class Calibration17cError(RuntimeError):
    """A calibration that would report a number it cannot stand behind."""


# ---------------------------------------------------------------------------
# Step A -- the bulk reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BulkReference:
    """What the bulk numbers are, and what they may legitimately be used for."""

    gaas_pm_per_V: float
    algaas_pm_per_V: float
    source: str
    evaluator_can_compute_bulk: bool
    reason: str
    externally_supplied_raw: float | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "bulk_gaas_pm_per_V": self.gaas_pm_per_V,
            "bulk_algaas_pm_per_V": self.algaas_pm_per_V,
            "source": self.source,
            "evaluator_can_compute_bulk": self.evaluator_can_compute_bulk,
            "reason": self.reason,
            "externally_supplied_raw_chi2_calc_bulk": self.externally_supplied_raw,
            "roles_this_value_may_play": [
                "denominator of the enhancement ratio",
                "horizontal reference line on the calibrated spectrum plot",
            ],
            "roles_this_value_may_not_play": [
                "anchor of the calibration, unless a raw bulk chi(2) is supplied "
                "by a theory that can produce one -- Eq. 2 cannot"
            ],
        }


def bulk_reference_evaluation(cfg: Mapping[str, Any]) -> BulkReference:
    """Establish the bulk reference, and say plainly what Eq. 2 can do with it.

    Returns rather than raises, because the enhancement ratio and the plot's
    reference lines are both perfectly well defined -- it is only the *anchor*
    role that Eq. 2 cannot support.
    """

    block = cfg["bulk_reference"]
    supplied = block.get("chi2_calc_bulk_gaas_raw")
    if supplied is not None:
        value = float(supplied)
        if not math.isfinite(value) or value <= 0:
            raise Calibration17cError(
                f"bulk_reference.chi2_calc_bulk_gaas_raw is {supplied!r}; a bulk "
                "anchor needs a finite positive raw susceptibility."
            )
        return BulkReference(
            gaas_pm_per_V=float(block["gaas_pm_per_V"]),
            algaas_pm_per_V=float(block["algaas_pm_per_V"]),
            source=str(block["source"]),
            evaluator_can_compute_bulk=True,
            reason=(
                "a raw bulk chi(2) was supplied externally, so the bulk anchor "
                "K = 377 / chi2_calc_bulk is available. Its provenance is the "
                "supplier's to defend: Eq. 2 did not produce it."
            ),
            externally_supplied_raw=value,
        )
    return BulkReference(
        gaas_pm_per_V=float(block["gaas_pm_per_V"]),
        algaas_pm_per_V=float(block["algaas_pm_per_V"]),
        source=str(block["source"]),
        evaluator_can_compute_bulk=False,
        reason=(
            "Eq. 2 sums envelope asymmetry: every factor is a confined-subband "
            "integral, and its two terms cancel EXACTLY for a symmetric structure "
            "(the paper's own chi2_zero_at_symmetric_limits target). Bulk GaAs has "
            "no confined envelopes, so the same evaluator returns zero and "
            "K = 377/0 is undefined. Bulk GaAs's 377 pm/V arises from the "
            "zincblende unit-cell bond asymmetry (d14), which is the mechanism "
            "r_e_hh parameterises -- not the envelope mechanism Eq. 2 computes. "
            "The two are different physics, which is why the paper reports the "
            "well as an enhancement OVER bulk rather than bulk plus a term."
        ),
    )


# ---------------------------------------------------------------------------
# Loading Demo 17
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseRow:
    """One Demo 17 case: raw values, and its spectrum when the hand-off has it."""

    case_id: str
    name: str
    description: str
    raw_at_target_pm_per_V: float
    raw_peak_pm_per_V: float
    peak_wavelength_nm: float
    interface_mode: str
    grading_nm: float
    wavelength_nm: np.ndarray | None = None
    raw_spectrum_pm_per_V: np.ndarray | None = None

    @property
    def has_spectrum(self) -> bool:
        return self.wavelength_nm is not None and self.raw_spectrum_pm_per_V is not None


def _load_spectrum(record: Mapping[str, Any], results_dir: Path, case_id: str):
    """The 1400-1800 nm curve, from the hand-off or from the original run tree."""

    candidates: list[Path] = []
    stored = (record.get("optical") or {}).get("spectrum_path")
    if stored:
        candidates.append(Path(stored))
    for name in (f"paper_target_{case_id}", case_id, "spectra"):
        candidates.append(Path(results_dir) / name / "chi2_focused.csv")
    candidates.append(Path(results_dir) / f"{case_id}_chi2_focused.csv")
    for candidate in candidates:
        if candidate.is_file():
            data = np.loadtxt(candidate, delimiter=",", skiprows=1)
            return (np.asarray(data[:, 0], dtype=float),
                    np.asarray(data[:, 3], dtype=float))
    return None, None


def load_cases(results_dir: Path, cfg: Mapping[str, Any]) -> list[CaseRow]:
    """Every completed Demo 17 case, with spectra where they are available."""

    summary = Path(results_dir) / "physics_summary.json"
    if not summary.is_file():
        raise Calibration17cError(f"{summary} not found; Demo 17c needs it.")
    payload = json.loads(summary.read_text(encoding="utf-8"))
    cases_meta = _case_metadata(results_dir)

    rows: list[CaseRow] = []
    for record in payload.get("cases", []):
        optical = record.get("optical") or {}
        if not record.get("passed") or optical.get("chi2_at_1550") is None:
            continue
        case_id = str(record["case_id"])
        meta = cases_meta.get(case_id, {})
        wavelength, spectrum = _load_spectrum(record, Path(results_dir), case_id)
        rows.append(CaseRow(
            case_id=case_id,
            name=str(meta.get("name", "")),
            description=str(meta.get("description", "")),
            raw_at_target_pm_per_V=float(optical["chi2_at_1550"]),
            raw_peak_pm_per_V=float(optical["spectral_peak_chi2"]),
            peak_wavelength_nm=float(optical["spectral_peak_wavelength_nm"]),
            interface_mode=str(meta.get("interface_mode", "")),
            grading_nm=float(meta.get("left_grading_width_nm", 0.0) or 0.0),
            wavelength_nm=wavelength,
            raw_spectrum_pm_per_V=spectrum,
        ))
    if not rows:
        raise Calibration17cError(f"no completed cases in {summary}.")
    return rows


def _case_metadata(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Names and grading widths, from whichever case list travelled with the run."""

    for candidate in (
        Path(results_dir) / "validation_cases.yaml",
        DEMOS / "17_paper_chi2_reproduction_corrected" / "validation_cases.yaml",
    ):
        if candidate.is_file():
            import yaml  # noqa: PLC0415
            payload = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            return {str(row["case_id"]): row for row in payload.get("cases", [])}
    return {}


# ---------------------------------------------------------------------------
# Step B -- the calibration factor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Calibration:
    """The single fitted scalar, and exactly what it was fitted to."""

    factor: float
    anchor_mode: str
    anchor_case_id: str
    anchor_quantity: str
    anchor_raw_pm_per_V: float
    anchor_target_pm_per_V: float
    anchor_source: str

    def as_record(self) -> dict[str, Any]:
        return {
            "calibration_factor_K": self.factor,
            "anchor_mode": self.anchor_mode,
            "anchor_case_id": self.anchor_case_id,
            "anchor_quantity": self.anchor_quantity,
            "anchor_raw_pm_per_V": self.anchor_raw_pm_per_V,
            "anchor_target_pm_per_V": self.anchor_target_pm_per_V,
            "anchor_source": self.anchor_source,
            "degrees_of_freedom_fitted": 1,
            "warning": CALIBRATION_WARNING,
        }


def calibration_factor(
    rows: Sequence[CaseRow], cfg: Mapping[str, Any], bulk: BulkReference
) -> Calibration:
    """Fit K. One scalar, one published number, and it is named in the result."""

    block = cfg["calibration"]
    mode = str(block.get("anchor_mode", "paper_ideal_abrupt"))

    if mode == "bulk_gaas":
        if not bulk.evaluator_can_compute_bulk:
            raise Calibration17cError(
                "calibration.anchor_mode is 'bulk_gaas', but there is no raw bulk "
                "chi(2) to divide into 377 pm/V.\n\n" + bulk.reason + "\n\n"
                "Either supply bulk_reference.chi2_calc_bulk_gaas_raw from a "
                "theory that can produce it, or use anchor_mode: "
                "'paper_ideal_abrupt', which anchors on a number computed by the "
                "same equation for the same class of structure."
            )
        raw = float(bulk.externally_supplied_raw)
        return Calibration(
            factor=bulk.gaas_pm_per_V / raw,
            anchor_mode=mode,
            anchor_case_id="bulk_gaas",
            anchor_quantity="chi2_calc_bulk_gaas_raw (externally supplied)",
            anchor_raw_pm_per_V=raw,
            anchor_target_pm_per_V=bulk.gaas_pm_per_V,
            anchor_source=bulk.source,
        )

    if mode != "paper_ideal_abrupt":
        raise Calibration17cError(
            f"unknown calibration.anchor_mode {mode!r}; expected "
            "'paper_ideal_abrupt' or 'bulk_gaas'."
        )

    anchor_id = str(block["anchor_case_id"])
    row = next((r for r in rows if r.case_id == anchor_id), None)
    if row is None:
        raise Calibration17cError(
            f"anchor case {anchor_id} is not among the completed cases "
            f"{[r.case_id for r in rows]}."
        )
    quantity = str(block.get("anchor_quantity", "at_target_wavelength"))
    raw = (row.raw_at_target_pm_per_V if quantity == "at_target_wavelength"
           else row.raw_peak_pm_per_V)
    if raw <= 0:
        raise Calibration17cError(f"{anchor_id} has a non-positive raw value.")
    target = float(block["anchor_target_pm_per_V"])
    return Calibration(
        factor=target / raw,
        anchor_mode=mode,
        anchor_case_id=anchor_id,
        anchor_quantity=quantity,
        anchor_raw_pm_per_V=raw,
        anchor_target_pm_per_V=target,
        anchor_source=str(block["anchor_source"]),
    )


# ---------------------------------------------------------------------------
# Step C / D -- apply, and measure the enhancement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibratedCase:
    """One case after the single global scalar. Spectrum carried when present."""

    row: CaseRow
    factor: float
    bulk_gaas_pm_per_V: float
    is_anchor: bool

    @property
    def calibrated_at_target(self) -> float:
        return self.row.raw_at_target_pm_per_V * self.factor

    @property
    def calibrated_peak(self) -> float:
        return self.row.raw_peak_pm_per_V * self.factor

    @property
    def enhancement_at_target(self) -> float:
        return self.calibrated_at_target / self.bulk_gaas_pm_per_V

    @property
    def enhancement_peak(self) -> float:
        return self.calibrated_peak / self.bulk_gaas_pm_per_V

    def calibrated_spectrum(self):
        """``K * chi2_raw(lambda)`` over the whole scanned window."""

        if not self.row.has_spectrum:
            return None, None
        return self.row.wavelength_nm, self.row.raw_spectrum_pm_per_V * self.factor

    def enhancement_spectrum(self):
        """``chi2_calibrated(lambda) / 377`` -- identical to the raw ratio.

        The calibration factor cancels out of a ratio between two calibrated
        quantities, which is why the enhancement is the one absolute-looking
        number here that does NOT depend on K.
        """

        wavelength, calibrated = self.calibrated_spectrum()
        if wavelength is None:
            return None, None
        return wavelength, calibrated / self.bulk_gaas_pm_per_V

    def as_record(self) -> dict[str, Any]:
        return {
            "case": self.row.case_id,
            "name": self.row.name,
            "interface_mode": self.row.interface_mode,
            "grading_nm": self.row.grading_nm,
            "is_anchor": self.is_anchor,
            "raw_at_1550_pm_per_V": self.row.raw_at_target_pm_per_V,
            "raw_peak_pm_per_V": self.row.raw_peak_pm_per_V,
            "calibration_factor_K": self.factor,
            "calibrated_at_1550_pm_per_V": self.calibrated_at_target,
            "calibrated_peak_pm_per_V": self.calibrated_peak,
            "peak_wavelength_nm": self.row.peak_wavelength_nm,
            "enhancement_at_1550_vs_bulk_gaas": self.enhancement_at_target,
            "enhancement_peak_vs_bulk_gaas": self.enhancement_peak,
            "spectrum_available": self.row.has_spectrum,
        }


def apply_calibration(
    rows: Sequence[CaseRow], calibration: Calibration, bulk: BulkReference
) -> list[CalibratedCase]:
    return [
        CalibratedCase(
            row=row, factor=calibration.factor,
            bulk_gaas_pm_per_V=bulk.gaas_pm_per_V,
            is_anchor=(row.case_id == calibration.anchor_case_id),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# The predictions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Prediction:
    """One published number the calibration did NOT fit, and where we landed."""

    label: str
    case_id: str
    quantity: str
    predicted_pm_per_V: float
    published_pm_per_V: float | Sequence[float]
    tolerance_percent: float | None
    source: str
    is_anchor: bool

    @property
    def relative_error(self) -> float | None:
        if self.is_anchor:
            return 0.0
        published = self.published_pm_per_V
        if isinstance(published, (list, tuple)):
            low, high = min(published), max(published)
            if low <= self.predicted_pm_per_V <= high:
                return 0.0
            nearest = low if self.predicted_pm_per_V < low else high
            return (self.predicted_pm_per_V - nearest) / nearest
        return (self.predicted_pm_per_V - float(published)) / float(published)

    @property
    def within_tolerance(self) -> bool | None:
        if self.tolerance_percent is None or self.relative_error is None:
            return None
        return abs(self.relative_error) * 100.0 <= float(self.tolerance_percent)

    def as_record(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "case_id": self.case_id,
            "quantity": self.quantity,
            "predicted_pm_per_V": self.predicted_pm_per_V,
            "published_pm_per_V": self.published_pm_per_V,
            "relative_error": self.relative_error,
            "tolerance_percent": self.tolerance_percent,
            "within_tolerance": self.within_tolerance,
            "is_anchor_not_evidence": self.is_anchor,
            "source": self.source,
        }


def validate_predictions(
    calibrated: Sequence[CalibratedCase], calibration: Calibration,
    cfg: Mapping[str, Any],
) -> list[Prediction]:
    """Compare against every published number, and mark the anchor as not evidence."""

    by_case = {case.row.case_id: case for case in calibrated}
    out: list[Prediction] = []
    for entry in cfg["predictions"]:
        case = by_case.get(str(entry["case_id"]))
        if case is None:
            continue
        quantity = str(entry["quantity"])
        value = (case.calibrated_at_target if quantity == "at_target_wavelength"
                 else case.calibrated_peak)
        is_anchor = (
            case.row.case_id == calibration.anchor_case_id
            and quantity == calibration.anchor_quantity
        )
        out.append(Prediction(
            label=str(entry["label"]),
            case_id=case.row.case_id,
            quantity=quantity,
            predicted_pm_per_V=value,
            published_pm_per_V=entry["published_pm_per_V"],
            tolerance_percent=entry.get("tolerance_percent"),
            source=str(entry["source"]),
            is_anchor=is_anchor,
        ))
    return out


def enhancement_summary(
    calibrated: Sequence[CalibratedCase], cfg: Mapping[str, Any], bulk: BulkReference
) -> dict[str, Any]:
    """The paper's enhancement claim, against what the ratio actually is.

    The enhancement is the one quantity here independent of K: it is a ratio of
    two calibrated numbers, so the fitted scalar cancels. That makes it the
    strongest thing this demo produces.
    """

    claim = cfg["enhancement"]
    reference = {
        str(k): float(v) / bulk.gaas_pm_per_V
        for k, v in (claim.get("published_points_pm_per_V") or {}).items()
    }
    values = [(c.row.case_id, c.enhancement_peak, c.enhancement_at_target)
              for c in calibrated]
    band = claim.get("expected_band")
    in_band = [
        case_id for case_id, peak, _ in values
        if band and float(band[0]) <= peak <= float(band[1])
    ]
    return {
        "definition": "chi2_calibrated(lambda) / chi2_bulk_GaAs, bulk = "
                      f"{bulk.gaas_pm_per_V} pm/V",
        "independent_of_calibration_factor": True,
        "note": (
            "K cancels from this ratio, so the enhancement is not a calibrated "
            "quantity -- it is what the raw evaluator already said, expressed "
            "against the bulk reference."
        ),
        "bulk_gaas_pm_per_V": bulk.gaas_pm_per_V,
        "bulk_algaas_pm_per_V": bulk.algaas_pm_per_V,
        "published_points_as_enhancement": reference,
        "expected_band": band,
        "cases_in_expected_band_at_peak": in_band,
        "per_case": [
            {"case": case_id, "enhancement_peak": peak,
             "enhancement_at_1550": target}
            for case_id, peak, target in values
        ],
    }


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


CSV_FIELDS = (
    "case", "name", "interface_mode", "grading_nm", "is_anchor",
    "raw_at_1550_pm_per_V", "raw_peak_pm_per_V", "calibration_factor_K",
    "calibrated_at_1550_pm_per_V", "calibrated_peak_pm_per_V",
    "peak_wavelength_nm", "enhancement_at_1550_vs_bulk_gaas",
    "enhancement_peak_vs_bulk_gaas", "spectrum_available",
)


def write_calibrated_csv(path: Path, calibrated: Sequence[CalibratedCase]) -> Path:
    import csv  # noqa: PLC0415

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(CSV_FIELDS),
                                extrasaction="ignore")
        writer.writeheader()
        for case in calibrated:
            writer.writerow(case.as_record())
    return path


def write_calibrated_spectrum_plot(
    path: Path, calibrated: Sequence[CalibratedCase], bulk: BulkReference,
    calibration: Calibration, target_nm: float,
) -> Path | None:
    """Calibrated spectra with the bulk GaAs and AlGaAs reference lines.

    Degrades honestly: with no spectra in the hand-off it draws the per-case peak
    and 1550 nm points instead of inventing a curve, and says so on the figure.
    """

    import plots  # noqa: PLC0415

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None
    import matplotlib.pyplot as plt  # noqa: PLC0415

    colours = ("#1f4e79", "#c0392b", "#2f855a", "#d45500", "#7b3f98",
               "#0f7b8a", "#8a6d1f", "#b5316a", "#3a6ea5", "#5c8a2f")
    styles = ("-", "--", "-", "--", "-", "--", "-", "--", "-", ":")

    fig, ax = plt.subplots(figsize=(11.0, 6.4))
    drawn_curves = 0
    for index, case in enumerate(calibrated):
        colour = colours[index % len(colours)]
        style = styles[index % len(styles)]
        label = f"{case.row.case_id} {case.row.name}".strip()
        wavelength, spectrum = case.calibrated_spectrum()
        if wavelength is not None:
            ax.plot(wavelength, spectrum, lw=1.8, alpha=0.95, color=colour,
                    linestyle=style, label=label)
            drawn_curves += 1
        else:
            ax.plot([case.row.peak_wavelength_nm, target_nm],
                    [case.calibrated_peak, case.calibrated_at_target],
                    lw=1.0, alpha=0.5, color=colour, linestyle=":")
            ax.scatter([case.row.peak_wavelength_nm], [case.calibrated_peak],
                       s=46, marker="^", color=colour, zorder=5, label=label)
            ax.scatter([target_nm], [case.calibrated_at_target], s=30,
                       color=colour, edgecolor="white", linewidth=0.6, zorder=5)

    for value, name, colour in (
        (bulk.gaas_pm_per_V, "bulk GaAs", "#444444"),
        (bulk.algaas_pm_per_V, "bulk Al0.55Ga0.45As", "#888888"),
    ):
        ax.axhline(value, color=colour, ls="-.", lw=1.5)
        ax.annotate(f"{name}: {value:.0f} pm/V",
                    xy=(0.004, value), xycoords=("axes fraction", "data"),
                    xytext=(0, 4), textcoords="offset points",
                    fontsize=8.5, color=colour)

    ax.axvline(target_nm, color="#222222", ls="--", lw=1.4)
    ax.annotate(f"{target_nm:.0f} nm", xy=(target_nm, 1.0),
                xycoords=("data", "axes fraction"), xytext=(4, -12),
                textcoords="offset points", fontsize=9, color="#222222")

    ax.set_yscale("log")
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel(r"calibrated $|\chi^{(2)}_{xzx}|$ (pm/V)")
    ax.set_title(
        "Calibrated absolute susceptibility against the bulk references\n"
        f"one scalar K = {calibration.factor:.3f} fitted to "
        f"{calibration.anchor_target_pm_per_V:.0f} pm/V "
        f"({calibration.anchor_case_id}); everything else is a prediction",
        fontsize=11,
    )
    if drawn_curves == 0:
        ax.annotate(
            "no spectra in this hand-off: markers are the per-case peak "
            "(triangle) and 1550 nm (circle) values",
            xy=(0.5, 0.02), xycoords="axes fraction", ha="center", fontsize=8.5,
            color="#a33", style="italic",
        )
    ax.legend(fontsize=7.5, ncol=2, framealpha=0.92)
    ax.grid(alpha=0.2, which="both")
    return plots.save_figure(fig, Path(path))


def build_report(
    calibrated: Sequence[CalibratedCase], calibration: Calibration,
    bulk: BulkReference, predictions: Sequence[Prediction],
    enhancement: Mapping[str, Any], cfg: Mapping[str, Any],
    results_dir: Path,
) -> dict[str, Any]:
    anchor_target = calibration.anchor_target_pm_per_V
    return {
        "demo_id": cfg["experiment"]["demo_id"],
        "source_results_dir": str(results_dir),
        "units": CALIBRATED_UNITS + f"{anchor_target:.0f} pm/V)",
        "calibration": calibration.as_record(),
        "bulk_reference": bulk.as_record(),
        "degrees_of_freedom_fitted": 1,
        "cases": [case.as_record() for case in calibrated],
        "predictions": [p.as_record() for p in predictions],
        "enhancement": enhancement,
        "spectra_available": sum(1 for c in calibrated if c.row.has_spectrum),
        "cases_reported": len(calibrated),
        "warning": CALIBRATION_WARNING,
    }

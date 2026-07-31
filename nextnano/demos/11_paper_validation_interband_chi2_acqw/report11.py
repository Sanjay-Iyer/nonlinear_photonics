"""Stage 8 — the formal paper-comparison report for Demo 11.

Every comparison is classified, and the classification is the point. A number
that merely *looks* close is not a reproduction if it came from a fitted scale
factor, and a number that disagrees is not a failure if the paper never
published what would be needed to compute it.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import chi2 as chi2mod
import plots as plotting
import sweeps
from demo_workflow import write_json_atomically, write_text_atomically

DIRECT = "directly_reproduced"
QUALITATIVE = "qualitatively_reproduced"
CALIBRATED = "calibrated_reproduction"
NOT_REPRODUCIBLE = "not_reproducible_from_available_information"
OUT_OF_SCOPE = "outside_nextnano_scope"
NEEDS_AUTHORS = "requires_author_data_or_code"


def _observable(result: sweeps.CaseResult | None, name: str) -> float | None:
    if result is None:
        return None
    value = result.observables.get(name)
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _entry(
    name: str,
    paper_value: float | None,
    ours: float | None,
    classification: str,
    units: str,
    note: str,
    *,
    tolerance: float | None = None,
) -> dict[str, Any]:
    difference = None
    relative = None
    within = None
    if paper_value is not None and ours is not None:
        difference = ours - paper_value
        if paper_value != 0:
            relative = difference / abs(paper_value)
        if tolerance is not None:
            within = abs(difference) <= tolerance
    # `classification` is the KIND of comparison this is. `outcome` is whether
    # it was actually evaluated. Without the split, a dry run would report
    # "directly_reproduced" for a quantity nothing has computed yet.
    if classification in (OUT_OF_SCOPE, NEEDS_AUTHORS, NOT_REPRODUCIBLE):
        outcome = "not_attempted"
    elif ours is None:
        outcome = "pending"
    elif within is None:
        outcome = "reported_without_tolerance"
    else:
        outcome = "within_tolerance" if within else "outside_tolerance"
    return {
        "quantity": name,
        "paper_value": paper_value,
        "our_value": ours,
        "units": units,
        "difference": difference,
        "relative_difference": relative,
        "within_tolerance": within,
        "classification": classification,
        "outcome": outcome,
        "evaluated": ours is not None,
        "note": note,
    }


def build(
    *,
    cfg: Mapping[str, Any],
    targets: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    reference: sweeps.CaseResult | None,
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    parent: Path,
) -> dict[str, Any]:
    """Assemble every paper-vs-simulation comparison with its classification."""

    published = targets["targets"]
    validation_cfg = cfg["validation"]
    metric_cfg = cfg.get("metric") or {}
    energy_tolerance_eV = (
        float(validation_cfg.get("transition_energy_tolerance_meV", 40.0)) / 1000.0
    )
    entries: list[dict[str, Any]] = []

    # --- structural: these are inputs, so agreement is a bookkeeping check ---
    scientific = cfg["scientific"]
    for key, ours in (
        ("thick_well_nm", float(scientific["thick_well_nm"])),
        ("thin_well_nm", float(scientific["thin_well_nm"])),
        ("tunnel_barrier_nm", float(scientific["tunnel_barrier_nm"])),
        ("period_barrier_nm", float(scientific["period_barrier_nm"])),
        ("aluminium_fraction", float(scientific["aluminum_fraction"])),
    ):
        entries.append(
            _entry(
                key,
                float(published[key]["value"]),
                ours,
                DIRECT,
                "nm" if key.endswith("_nm") else "",
                "Structural input, transcribed from the paper. Agreement here "
                "confirms transcription, not physics.",
                tolerance=1e-6,
            )
        )
    entries.append(
        _entry(
            "asymmetry_s",
            float(published["asymmetry_optimum"]["value"]),
            chi2mod.structural_asymmetry(
                float(scientific["thick_well_nm"]), float(scientific["thin_well_nm"])
            ),
            DIRECT,
            "",
            "s = (d1 - d2)/(d1 + d2), computed from the transcribed thicknesses.",
            tolerance=0.005,
        )
    )

    # --- electronic structure: the first real physics comparison ------------
    entries.append(
        _entry(
            "ground_interband_transition",
            float(published["ground_interband_transition_eV"]["value"]),
            _observable(reference, "transition_e1_hh1_eV"),
            DIRECT,
            "eV",
            "E_e1 - E_hh1 from a one-band Gamma + HH calculation of the designed "
            "layers. No material parameter was adjusted to improve agreement.",
            tolerance=energy_tolerance_eV,
        )
    )
    entries.append(
        _entry(
            "excited_interband_transition",
            float(published["excited_interband_transition_eV"]["value"]),
            _observable(reference, "transition_e2_hh2_eV"),
            DIRECT,
            "eV",
            "E_e2 - E_hh2. This transition sets the ~1520 nm two-photon resonance.",
            tolerance=energy_tolerance_eV,
        )
    )

    # --- spectral positions --------------------------------------------------
    two_photon = None
    if reference is not None:
        predicted = reference.observables.get("predicted_two_photon_resonances_nm") or []
        excited = [
            value
            for value in predicted
            if 1200.0 <= float(value) <= 1900.0
        ]
        two_photon = min(excited) if excited else None
    entries.append(
        _entry(
            "simulated_resonance_wavelength",
            float(published["simulated_resonance_nm"]["value"]),
            two_photon,
            DIRECT,
            "nm",
            "Two-photon resonance of the excited-state transition, 2hc/E. The "
            "paper's companion peak near 760 nm is the one-photon resonance of "
            "the same transition, so the two are one statement, not two.",
            tolerance=60.0,
        )
    )
    peak = (stage6 or {}).get("focused_peak") or {}
    entries.append(
        _entry(
            "focused_scan_peak_wavelength",
            float(published["simulated_resonance_nm"]["value"]),
            float(peak["wavelength_nm"]) if peak.get("wavelength_nm") else None,
            DIRECT,
            "nm",
            "Peak of |chi(2)| computed over 1400-1800 nm from Eq. 2. This is the "
            "end-to-end check that the resonance really lands where the transition "
            "energies say it should.",
            tolerance=60.0,
        )
    )
    entries.append(
        _entry(
            "measured_resonance_wavelength",
            float(published["measured_resonance_nm"]["value"]),
            None,
            OUT_OF_SCOPE,
            "nm",
            "Measured, not simulated. The paper attributes the ~40 nm offset from "
            "its own simulation to a lower transition energy in the grown sample. "
            "Reproducing it would require modelling the as-grown layers, not the "
            "designed ones.",
        )
    )

    # --- asymmetry and barrier trends ---------------------------------------
    stage3 = [r for r in results if r.spec.metadata.get("stage") == "stage3"]
    peak_asymmetry = _peak_of(stage3, "asymmetry", "chi2_relative_at_reference")
    entries.append(
        _entry(
            "asymmetry_of_maximum_chi2",
            float(published["asymmetry_optimum"]["value"]),
            peak_asymmetry,
            QUALITATIVE,
            "",
            "Position of the maximum of the relative chi(2) across the asymmetry "
            "sweep. The location is meaningful in relative mode; the height is not.",
            tolerance=0.08,
        )
    )
    zero_case = next(
        (r for r in stage3 if abs(float(r.spec.swept.get("thin_well_nm", -1)) -
                                 float(r.spec.swept.get("thick_well_nm", -2))) < 1e-9),
        None,
    )
    entries.append(
        _entry(
            "chi2_at_symmetric_limit",
            0.0,
            _observable(zero_case, "chi2_relative_at_reference"),
            QUALITATIVE,
            "relative",
            "s = 0 gives two identical wells. A symmetric structure has "
            "identically zero chi(2) by parity; this checks the calculation "
            "reproduces that rather than merely a small number.",
        )
    )
    stage4 = [r for r in results if r.spec.metadata.get("stage") == "stage4"]
    peak_barrier = _peak_of(stage4, "tunnel_barrier_nm", "chi2_relative_at_reference")
    entries.append(
        _entry(
            "barrier_of_maximum_chi2",
            float(published["barrier_optimum_nm"]["value"]),
            peak_barrier,
            QUALITATIVE,
            "nm",
            "The paper predicts an ideal optimum near 1 nm while the fabricated "
            "structure used 1.8 nm. Those are two different statements and both "
            "are reported; the difference is a design choice, not a discrepancy.",
            tolerance=0.6,
        )
    )

    # --- interface abruptness ------------------------------------------------
    stage7 = {
        str(r.spec.label): r
        for r in results
        if r.spec.metadata.get("stage") == "stage7"
    }
    abrupt = _observable(stage7.get("ideal_abrupt"), "chi2_relative_at_reference")
    graded = _observable(stage7.get("graded_1nm"), "chi2_relative_at_reference")
    ratio = (graded / abrupt) if (abrupt and graded and abrupt != 0) else None
    paper_ratio = (
        float(published["chi2_eds_al_profile_pm_per_V"]["value"])
        / float(published["chi2_ideal_abrupt_pm_per_V"]["value"])
    )
    entries.append(
        _entry(
            "graded_to_abrupt_chi2_ratio",
            paper_ratio,
            ratio,
            QUALITATIVE,
            "",
            "Ratio of graded to abrupt chi(2) at the reference wavelength. A "
            "ratio is comparable even in relative mode, because the unknown "
            "absolute scale cancels. The paper's ratio uses its 1200 pm/V EDS-Al "
            "result against its 2340 pm/V ideal result.",
            tolerance=0.25,
        )
    )

    # --- absolute magnitudes -------------------------------------------------
    absolute_mode = ((stage5 or {}).get("modes") or {}).get("absolute") or {}
    calibrated_mode = ((stage5 or {}).get("modes") or {}).get("calibrated") or {}
    entries.append(
        _entry(
            "chi2_ideal_abrupt_at_1550nm",
            float(published["chi2_ideal_abrupt_pm_per_V"]["value"]),
            float(absolute_mode["magnitude_at_reference"])
            if absolute_mode.get("magnitude_at_reference") is not None
            else None,
            NOT_REPRODUCIBLE if not absolute_mode.get("available") else DIRECT,
            "pm/V",
            absolute_mode.get(
                "reason",
                "Absolute prediction from the supplied r_e_hh and N_z.",
            )
            if not absolute_mode.get("available")
            else "Absolute prediction using externally supplied r_e_hh and N_z.",
        )
    )
    if calibrated_mode.get("magnitude_at_reference") is not None:
        entries.append(
            _entry(
                "chi2_ideal_abrupt_at_1550nm_calibrated",
                float(published["chi2_ideal_abrupt_pm_per_V"]["value"]),
                float(calibrated_mode["magnitude_at_reference"]),
                CALIBRATED,
                "pm/V",
                "This agrees BY CONSTRUCTION: one global factor was fitted to this "
                "very number. It is listed to make the circularity explicit, and "
                "carries no evidential weight on its own.",
            )
        )
    for key, note in (
        ("chi2_growth_interrupted_pm_per_V", "growth-interrupted sample"),
        ("chi2_12_and_16_period_pm_per_V", "12- and 16-period samples"),
        ("chi2_80_period_pm_per_V", "80-period sample"),
        ("chi2_4_period_pm_per_V", "4-period sample"),
    ):
        entries.append(
            _entry(
                key,
                float(published[key]["value"]),
                None,
                OUT_OF_SCOPE,
                "pm/V",
                f"Measured value for the {note}. Depends on surface band bending, "
                "standing waves, sample placement, and the Eq. 3 field-overlap "
                "extraction with its free parameter alpha. An electronic-structure "
                "calculation should not be expected to reproduce it, and this demo "
                "does not try.",
            )
        )
    entries.append(
        _entry(
            "r_e_hh_unit_cell_matrix_element",
            None,
            None,
            NEEDS_AUTHORS,
            "nm",
            "The HSE06 unit-cell interband matrix element sets the absolute scale "
            "and no numerical value appears in the paper. Without it, no "
            "independent pm/V figure is possible.",
        )
    )

    # Classifications are counted only among comparisons that were actually
    # evaluated; the rest are reported as pending so a dry run cannot look like
    # a successful reproduction.
    evaluated = [e for e in entries if e["evaluated"]]
    summary = {
        classification: sum(
            1 for e in evaluated if e["classification"] == classification
        )
        for classification in (
            DIRECT, QUALITATIVE, CALIBRATED, NOT_REPRODUCIBLE, OUT_OF_SCOPE, NEEDS_AUTHORS
        )
    }
    summary["evaluated"] = len(evaluated)
    summary["pending"] = sum(1 for e in entries if e["outcome"] == "pending")
    summary["not_attempted"] = sum(1 for e in entries if e["outcome"] == "not_attempted")
    checked = [e for e in entries if e["within_tolerance"] is not None]
    summary["comparisons_with_a_tolerance"] = len(checked)
    summary["within_tolerance"] = sum(1 for e in checked if e["within_tolerance"])

    criteria: list[tuple[str, bool | None, str]] = [
        (
            "structural parameters transcribed correctly",
            _all_within(entries, ("thick_well_nm", "thin_well_nm", "tunnel_barrier_nm",
                                  "period_barrier_nm", "aluminium_fraction", "asymmetry_s")),
            "bookkeeping check against paper_targets.yaml",
        ),
        (
            "ground interband transition within tolerance",
            _within(entries, "ground_interband_transition"),
            f"paper 1.49 eV, tolerance "
            f"{validation_cfg.get('transition_energy_tolerance_meV', 40.0)} meV",
        ),
        (
            "excited interband transition within tolerance",
            _within(entries, "excited_interband_transition"),
            "paper 1.62 eV",
        ),
        (
            "two-photon resonance lands near the published 1520 nm",
            _within(entries, "focused_scan_peak_wavelength"),
            "computed end-to-end from Eq. 2 over 1400-1800 nm",
        ),
        (
            "chi(2) maximum occurs near s = 0.42",
            _within(entries, "asymmetry_of_maximum_chi2"),
            "position of the maximum; height is not claimed in relative mode",
        ),
        (
            "chi(2) vanishes at the symmetric limit",
            _vanishes(entries, "chi2_at_symmetric_limit"),
            "parity forbids a second-order response in a symmetric structure",
        ),
        (
            "barrier optimum near the published 1 nm",
            _within(entries, "barrier_of_maximum_chi2"),
            "ideal optimum, distinct from the 1.8 nm fabricated design",
        ),
        (
            "grading reduces chi(2) in the published proportion",
            _within(entries, "graded_to_abrupt_chi2_ratio"),
            "a ratio, so the unknown absolute scale cancels",
        ),
        (
            "envelopes orthonormal and chi(2) origin independent",
            _all_true(results, "envelopes_orthonormal")
            and _all_true(results, "chi2_origin_independent"),
            "Eq. 2 contains diagonal dipoles; without orthonormality the result "
            "depends on where z = 0 is placed",
        ),
    ]
    return {"entries": entries, "summary": summary, "criteria": criteria}


def _peak_of(
    results: Sequence[sweeps.CaseResult], parameter: str, observable: str
) -> float | None:
    points = [
        (float(r.observables[parameter]), float(r.observables[observable]))
        for r in results
        if r.observables.get(parameter) is not None
        and r.observables.get(observable) is not None
    ]
    if not points:
        return None
    return max(points, key=lambda item: item[1])[0]


def _within(entries: Sequence[Mapping[str, Any]], name: str) -> bool | None:
    for entry in entries:
        if entry["quantity"] == name:
            return entry["within_tolerance"]
    return None


def _all_within(entries: Sequence[Mapping[str, Any]], names: Sequence[str]) -> bool | None:
    values = [_within(entries, name) for name in names]
    if any(value is None for value in values):
        return None
    return all(values)


def _vanishes(entries: Sequence[Mapping[str, Any]], name: str) -> bool | None:
    for entry in entries:
        if entry["quantity"] == name:
            ours = entry["our_value"]
            if ours is None:
                return None
            return bool(abs(float(ours)) < 1e-6)
    return None


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        r.validation.get(key) for r in results if r.solver_success and key in r.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)


def write_tables(
    parent: Path,
    targets: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    comparison: Mapping[str, Any],
) -> None:
    """paper_targets.csv, our_results.csv, comparison_metrics.csv."""

    published = targets["targets"]
    sweeps.write_table(
        parent,
        "paper_targets",
        [
            {
                "quantity": name,
                "value": entry.get("value"),
                "kind": entry.get("kind"),
                "source": " ".join(str(entry.get("source", "")).split()),
            }
            for name, entry in published.items()
        ],
    )
    sweeps.write_table(
        parent,
        "our_results",
        [
            {
                "case_id": r.spec.case_id,
                "stage": r.spec.metadata.get("stage"),
                "label": r.spec.label,
                "status": r.status,
                **{
                    key: value
                    for key, value in r.observables.items()
                    if isinstance(value, (int, float, str, bool)) or value is None
                },
            }
            for r in results
        ],
    )
    sweeps.write_table(parent, "comparison_metrics", list(comparison["entries"]))


def write_assumptions(parent: Path, targets: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    """assumptions_and_unknowns.yaml — everything the reproduction rests on."""

    write_text_atomically(
        parent / "assumptions_and_unknowns.yaml",
        yaml.safe_dump(
            {
                "paper": targets.get("paper", {}),
                "chi2_equation": "Eq. 2 of the paper, implemented in _shared/chi2.py",
                "assumptions": list(chi2mod.ASSUMPTIONS),
                "not_published_by_the_paper": targets.get(
                    "missing_for_absolute_scale", {}
                ),
                "our_settings": (cfg.get("metric") or {}),
                "consequences": {
                    "absolute_magnitude": (
                        "Not independently reproducible. Requires r_e_hh and N_z."
                    ),
                    "resonance_positions": (
                        "Reproducible: they follow from the transition energies alone."
                    ),
                    "trends": (
                        "Reproducible: asymmetry, barrier, and interface trends are "
                        "ratios in which the unknown absolute scale cancels."
                    ),
                    "measured_values": (
                        "Outside scope: they fold in band bending, standing waves, "
                        "sample placement, and a fitted extraction parameter."
                    ),
                },
            },
            sort_keys=False,
            default_flow_style=False,
        ),
    )


def write_report(
    parent: Path,
    cfg: Mapping[str, Any],
    targets: Mapping[str, Any],
    comparison: Mapping[str, Any],
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    """paper_comparison_report.md."""

    write_assumptions(parent, targets, cfg)
    paper = targets.get("paper", {})
    summary = comparison["summary"]
    lines = [
        "# Paper comparison report",
        "",
        f"- Target: **{paper.get('title')}** ({paper.get('arxiv')})",
        f"- Run status: `{manifest.get('status')}`",
        f"- Cases: {manifest.get('case_count')} "
        f"(completed {manifest.get('solver_success_count')}, "
        f"skipped {manifest.get('skipped_count')}, failed {manifest.get('failed_count')})",
        "",
        "## The headline, stated first",
        "",
        "The **absolute** chi(2) magnitude is not independently reproducible from ",
        "this paper. It does not publish the HSE06 unit-cell matrix element ",
        "`r_e_hh`, the wells-per-unit-length `N_z`, or the k-space quadrature ",
        "conventions, and those set the scale. What *is* reproducible, and what ",
        "this demo actually tests, is the electronic structure, the resonance ",
        "positions, and the asymmetry / barrier / interface trends.",
        "",
        "## Classification summary",
        "",
        "| classification | count |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        if key.startswith("comparisons") or key in {"within_tolerance", "evaluated",
                                                    "pending", "not_attempted"}:
            continue
        lines.append(f"| `{key}` | {value} |")
    lines += [
        "",
        f"Evaluated: {summary['evaluated']}. "
        f"Pending (nothing computed yet): {summary['pending']}. "
        f"Not attempted by design: {summary['not_attempted']}.",
    ]
    lines += [
        "",
        f"Comparisons carrying a numeric tolerance: {summary['comparisons_with_a_tolerance']}; "
        f"within tolerance: {summary['within_tolerance']}.",
        "",
        "## Comparisons",
        "",
        "| quantity | paper | ours | units | diff | within tol | classification / outcome |",
        "|---|---:|---:|---|---:|---|---|",
    ]
    for entry in comparison["entries"]:
        def fmt(value: Any) -> str:
            if value is None:
                return "—"
            if isinstance(value, float):
                return f"{value:.6g}"
            return str(value)

        within = entry["within_tolerance"]
        verdict = "—" if within is None else ("yes" if within else "**no**")
        lines.append(
            f"| {entry['quantity']} | {fmt(entry['paper_value'])} | "
            f"{fmt(entry['our_value'])} | {entry['units'] or '—'} | "
            f"{fmt(entry['difference'])} | {verdict} | "
            f"`{entry['classification']}` / `{entry['outcome']}` |"
        )
    lines += ["", "### Notes on each comparison", ""]
    for entry in comparison["entries"]:
        lines.append(f"- **{entry['quantity']}** — {entry['note']}")

    lines += ["", "## chi(2) modes (Stage 5)", ""]
    for name, record in ((stage5 or {}).get("modes") or {}).items():
        available = record.get("available")
        lines.append(f"### `{name}` — {'available' if available else 'not available'}")
        lines.append("")
        lines.append(f"- permitted by the configuration: {record.get('configured')}")
        if available:
            lines.append(f"- units: `{record.get('units')}`")
            lines.append(
                f"- |chi(2)| at the reference wavelength: "
                f"{record.get('magnitude_at_reference')}"
            )
            if record.get("scale_factor") is not None:
                lines.append(f"- fitted scale factor: {record['scale_factor']:.6g}")
        else:
            lines.append(f"- reason: {record.get('reason')}")
        lines.append(f"- what this may claim: {record.get('claim', '—')}")
        lines.append("")

    resonances = (stage6 or {}).get("predicted_resonances_nm") or {}
    if resonances:
        lines += ["## Resonance positions (Stage 6)", ""]
        lines.append(
            "- two-photon (2hbar.omega = E): "
            + ", ".join(f"{value:.1f} nm" for value in resonances.get("two_photon_resonance_nm", []))
        )
        lines.append(
            "- one-photon (hbar.omega = E): "
            + ", ".join(f"{value:.1f} nm" for value in resonances.get("one_photon_resonance_nm", []))
        )
        lines.append("")

    lines += [
        "## What would be needed for an independent absolute reproduction",
        "",
        "1. The numerical HSE06 value of `r_e_hh` used by the authors.",
        "2. An unambiguous `N_z` (the paper's own text says the period is 20 nm "
        "while its figure caption and layer arithmetic both give 30 nm).",
        "3. The k-parallel quadrature, zone-edge convention, in-plane masses, and "
        "whether spin degeneracy is folded into the sum.",
        "4. The nextnano input deck, material database version, and boundary "
        "conditions.",
        "",
        "Items 1-3 are recorded in `assumptions_and_unknowns.yaml`.",
        "",
    ]
    write_text_atomically(parent / "paper_comparison_report.md", "\n".join(lines) + "\n")
    write_json_atomically(parent / "comparison.json", dict(comparison))


def write_plots(
    parent: Path,
    cfg: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    reference: sweeps.CaseResult | None,
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> None:
    """The figure set required by the demo's README."""

    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def series(stage: str, parameter: str, observable: str) -> tuple[list[float], list[float]]:
        xs: list[float] = []
        ys: list[float] = []
        for r in results:
            if r.spec.metadata.get("stage") != stage:
                continue
            x = r.observables.get(parameter)
            y = r.observables.get(observable)
            if x is None or y is None:
                continue
            xs.append(float(x))
            ys.append(float(y))
        return xs, ys

    plotting.line_plot(
        plots_dir / "chi2_vs_asymmetry.png",
        title="Relative chi(2) versus structural asymmetry (paper optimum s = 0.42)",
        xlabel="Asymmetry s = (d1 - d2)/(d1 + d2)",
        ylabel="|chi(2)| (relative, arbitrary units)",
        series={"this work": series("stage3", "asymmetry", "chi2_relative_at_reference")},
        axhline=0.0,
    )
    plotting.line_plot(
        plots_dir / "localization_vs_asymmetry.png",
        title="Electron localisation versus asymmetry",
        xlabel="Asymmetry s",
        ylabel="Integrated probability",
        series={
            "e1 in thick well": series("stage3", "asymmetry", "electron1_thick_well_probability"),
            "e1 in thin well": series("stage3", "asymmetry", "electron1_thin_well_probability"),
            "e2 in thick well": series("stage3", "asymmetry", "electron2_thick_well_probability"),
            "e2 in thin well": series("stage3", "asymmetry", "electron2_thin_well_probability"),
        },
    )
    plotting.line_plot(
        plots_dir / "chi2_vs_barrier.png",
        title="Relative chi(2) versus tunnelling-barrier thickness (paper optimum ~1 nm)",
        xlabel="Tunnelling barrier (nm)",
        ylabel="|chi(2)| (relative, arbitrary units)",
        series={"this work": series("stage4", "tunnel_barrier_nm", "chi2_relative_at_reference")},
    )
    for name, filename, title in (
        ("broad", "chi2_broad_wavelength.png", "Relative chi(2) over 400-1800 nm"),
        ("focused", "chi2_focused_wavelength.png", "Relative chi(2) over 1400-1800 nm"),
    ):
        path = parent / "extracted" / f"chi2_{name}_wavelength.csv"
        if not path.is_file():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        plotting.line_plot(
            plots_dir / filename,
            title=title,
            xlabel="Fundamental wavelength (nm)",
            ylabel="chi(2) (relative, arbitrary units)",
            series={
                "Re": (data[:, 0], data[:, 1]),
                "Im": (data[:, 0], data[:, 2]),
                "|chi(2)|": (data[:, 0], data[:, 3]),
            },
            markers=False,
        )

    # Transition-energy comparison.
    published = {
        "E1-HH1": 1.49,
        "E2-HH2": 1.62,
    }
    ours = {
        "E1-HH1": reference.observables.get("transition_e1_hh1_eV") if reference else None,
        "E2-HH2": reference.observables.get("transition_e2_hh2_eV") if reference else None,
    }
    labels = [name for name in published if ours.get(name) is not None]
    if labels:
        plotting.line_plot(
            plots_dir / "transition_energy_comparison.png",
            title="Interband transition energies: paper versus this work",
            xlabel="Transition index",
            ylabel="Energy (eV)",
            series={
                "paper": (list(range(1, len(labels) + 1)), [published[n] for n in labels]),
                "this work": (
                    list(range(1, len(labels) + 1)),
                    [float(ours[n]) for n in labels],
                ),
            },
        )

    # Scorecard.
    entries = comparison["entries"]
    scored = [e for e in entries if e["within_tolerance"] is not None]
    plotting.bar_plot(
        plots_dir / "validation_scorecard.png",
        title="Validation scorecard (1 = within tolerance, 0 = outside)",
        xlabel="Comparison",
        ylabel="Within tolerance",
        labels=[e["quantity"] for e in scored],
        values=[1.0 if e["within_tolerance"] else 0.0 for e in scored],
        excluded=[not e["within_tolerance"] for e in scored],
    )
    plotting.bar_plot(
        plots_dir / "paper_vs_simulation_chi2.png",
        title="Published chi(2) values and what this demo can claim about each",
        xlabel="Published quantity",
        ylabel="chi(2) (pm/V)",
        labels=[
            e["quantity"] for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
        values=[
            float(e["paper_value"]) for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
        excluded=[
            e["classification"] in (OUT_OF_SCOPE, NOT_REPRODUCIBLE, NEEDS_AUTHORS)
            for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
    )

    # Convergence.
    plotting.line_plot(
        plots_dir / "convergence_summary.png",
        title="Numerical convergence of the interband transition energies",
        xlabel="Swept numerical parameter",
        ylabel="E1-HH1 (eV)",
        series={
            "grid spacing (nm)": series(
                "stage2", "active_region_grid_spacing_nm", "transition_e1_hh1_eV"
            ),
            "quantum padding (nm)": series(
                "stage2", "quantum_region_padding_nm", "transition_e1_hh1_eV"
            ),
        },
    )

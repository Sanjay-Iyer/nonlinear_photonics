"""Tables and final Markdown report for Demo 23."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    records = list(rows)
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in records:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _fmt(value: Any, spec: str = ".7g") -> str:
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def _pass(value: bool) -> str:
    return "PASS" if value else "FAIL"


def write_final_report(
    path: Path,
    *,
    baseline_error: float,
    tolerance: float,
    summary_rows: Sequence[Mapping[str, Any]],
    fit_rows: Sequence[Mapping[str, Any]],
    isotropy_rows: Sequence[Mapping[str, Any]],
    grid_rows: Sequence[Mapping[str, Any]],
    kmax_rows: Sequence[Mapping[str, Any]],
    resolved: Mapping[str, Any],
    unresolved: Sequence[str],
    validation_rows: Sequence[Mapping[str, Any]],
    pathway_rows: Sequence[Mapping[str, Any]],
    integrand_rows: Sequence[Mapping[str, Any]],
    paper_rows: Sequence[Mapping[str, Any]],
    paper_reference_rows: Sequence[Mapping[str, Any]],
) -> None:
    by_mode = {str(row["mode"]): row for row in summary_rows}
    fits = {str(row["state"]): row for row in fit_rows}
    pathways = {str(row["mode"]): row for row in pathway_rows}
    integrands = {str(row["mode"]): row for row in integrand_rows}
    paper = {str(row["mode"]): row for row in paper_rows}
    descriptions = {
        "23A": "shared reduced-mass parabola",
        "23B": "four independent anchored parabolas",
        "23C": "electron parabolas + nonparabolic kp8 holes",
        "23D": "raw/interpolated kp8 energies for all four states",
    }
    baseline_pass = baseline_error <= tolerance

    lines = [
        "# Demo 23 final scientific report",
        "",
        "## 1. Executive summary",
        "",
        "Demo 23 isolates the effect of in-plane energy dispersion on the already validated "
        "16-pathway Equation 2 calculation. No production matrix element, prefactor, broadening, "
        "geometry, wavelength grid, or k-space normalization changes between 23A–23D.",
        "",
        f"The 23A baseline regression is **{_pass(baseline_pass)}**: maximum complex error "
        f"`{baseline_error:.12g} pm/V` against tolerance `{tolerance:.12g} pm/V`. "
        f"The complete boss-hybrid validation is **{_pass(bool(resolved['boss_hybrid_validated']))}**.",
        "",
        "### Master mode table",
        "",
        "| Mode | Dispersion | χ²(1550) pm/V | Peak χ² pm/V | Peak λ nm | FWHM nm | RMSE vs 23D | Normalized RMSE vs digitized paper |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in ("23A", "23B", "23C", "23D"):
        if mode not in by_mode:
            continue
        row = by_mode[mode]
        lines.append(
            f"| {mode} | {descriptions[mode]} | {_fmt(row['chi2_1550_pm_per_V'])} | "
            f"{_fmt(row['peak_chi2_pm_per_V'])} | {_fmt(row['peak_wavelength_nm'])} | "
            f"{_fmt(row['FWHM_nm'])} | {_fmt(row['relative_spectrum_RMSE_vs_23D'])} | "
            f"{_fmt(row['normalized_RMSE_vs_digitized_paper'])} |"
        )
    lines += [
        "",
        "### Validation table",
        "",
        "| Check | Result | Threshold | PASS/FAIL |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['Check']} | {row['Result']} | {row['Threshold']} | **{row['PASS/FAIL']}** |"
        for row in validation_rows
    )

    lines += [
        "",
        "## 2. What changed relative to Demo 21",
        "",
        "Demo 21 uses one shared parabolic transition shift. Demo 23 adds separately fitted "
        "e1/e2/hh1/hh2 parabolas, a boss-requested electron-parabola/nonparabolic-hole hybrid, "
        "and a raw-kp8 energy-only reference. The four modes are evaluated on the same k and "
        "wavelength grids.",
        "",
        "## 3. What remained fixed",
        "",
        f"- `M(k)=M(0)` and all 16 Equation 2 pathways.",
        f"- Gamma `{_fmt(resolved['broadening_meV'])} meV`; r(e,hh) `{_fmt(resolved['r_e_hh_nm'])} nm`.",
        f"- Nz `{_fmt(resolved['n_periods_per_metre'])} m^-1` ({resolved['nz_semantics']}).",
        f"- Spin degeneracy `{resolved['spin_degeneracy']}` and measure `{resolved['kspace_convention']}`.",
        f"- Nominal kmax `{_fmt(resolved['kmax_per_nm'])} nm^-1` under `{resolved['bz_definition']}`.",
        "- No unexplained residual `1/hbar` was introduced.",
        "",
        "## 4. Professional nextnano runs completed",
        "",
        "The report is produced only after the required real Professional kp8 output directories "
        "are parsed successfully. Demo 23 has no synthetic production-result fallback. See "
        "`solver_manifest.json`, `raw/`, and the per-deck inventories in `tables/inventories/`.",
        "",
        "## 5. State-tracking validation",
        "",
        "Tracked identities are recorded at every k point in `tables/state_tracking.csv`, including "
        "raw solver index, overlap score, assignment margin, confidence, and dominant spinor "
        "character. Ambiguous target tracking stops analysis before fitting.",
        "",
        ("Finite-k spinors were available, so overlap tracking was evaluated."
         if bool(resolved.get("finite_k_overlap_available")) else
         "This Professional output contains only k=0 spinors. Target Kramers pairs are identified "
         "at k=0 and their fixed solver dispersion columns are averaged at finite k. Therefore "
         "finite-k overlap tracking is unavailable and the state-tracking validation is marked FAIL, "
         "even though the energy-only A–D diagnostics are still produced."),
        "",
        "## 6. Electron dispersion fits",
        "",
        "| State | m*/m0 | RMSE meV | Max error meV | k at max nm^-1 | Fit range nm^-1 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for state in ("e1", "e2"):
        row = fits[state]
        lines.append(f"| {state} | {_fmt(row['effective_mass_m0'])} | {_fmt(row['RMSE_meV'])} | {_fmt(row['max_abs_residual_meV'])} | {_fmt(row['k_at_max_residual_per_nm'])} | {_fmt(row['fit_kmin_per_nm'])}–{_fmt(row['fit_kmax_per_nm'])} |")
    lines += [
        "",
        "Figure 2 overlays tracked kp8 points and fits; Figure 3 shows signed residuals over the "
        "actual Equation 2 range. The validation table applies the configured electron-fit RMSE gate.",
        "",
        "## 7. Heavy-hole nonparabolicity",
        "",
        "| State | Diagnostic m*/m0 | RMSE meV | Max error meV | k at max nm^-1 | Pattern |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for state in ("hh1", "hh2"):
        row = fits[state]
        lines.append(f"| {state} | {_fmt(row['effective_mass_m0'])} | {_fmt(row['RMSE_meV'])} | {_fmt(row['max_abs_residual_meV'])} | {_fmt(row['k_at_max_residual_per_nm'])} | {row['residual_pattern']} |")
    lines += [
        "",
        "These heavy-hole masses are diagnostics only. 23C and 23D use shape-preserving "
        "interpolation of tracked kp8 hole energies. Figure 5b is a local-curvature diagnostic and "
        "does not feed production physics.",
        "",
        "## 8. Transition-energy comparison",
        "",
        "Figures 6 and 7 show ΔE11, ΔE12, ΔE21, and ΔE22 at the same k index. The horizontal "
        "line is twice the photon energy at 1550 nm, exposing which k regions approach the SHG "
        "resonance as the dispersion model changes.",
        "",
    ]
    for number, mode, heading in ((9, "23A", "23A results"), (10, "23B", "23B results"),
                                  (11, "23C", "23C boss-model results"), (12, "23D", "23D raw-kp8 reference")):
        lines += [f"## {number}. {heading}", ""]
        if mode in by_mode:
            row = by_mode[mode]
            lines.append(f"χ²(1550) = `{_fmt(row['chi2_1550_pm_per_V'])} pm/V`; peak = `{_fmt(row['peak_chi2_pm_per_V'])} pm/V` at `{_fmt(row['peak_wavelength_nm'])} nm`; FWHM = `{_fmt(row['FWHM_nm'])} nm`.")
        else:
            lines.append("Not evaluated in this mode-filtered analysis.")
        lines.append("")
    lines += [
        "## 13. A-D spectrum comparison",
        "",
        "Figure 8 shows the full wavelength range and Figure 9 shows absolute and relative "
        "differences to 23D. Pointwise relative deviations use an explicitly reported denominator "
        "floor near spectral nodes; the 1% acceptance gate uses whole-spectrum RMSE normalized by "
        "the 23D peak.",
        "",
        "## 14. Pathway-level interpretation",
        "",
    ]
    for mode in ("23A", "23B", "23C", "23D"):
        if mode in pathways:
            row = pathways[mode]
            lines.append(f"- {mode}: electron subtotal `({_fmt(row['electron_side_real_pm_per_V'])} + i {_fmt(row['electron_side_imag_pm_per_V'])}) pm/V`; signed HH subtotal `({_fmt(row['heavy_hole_side_real_pm_per_V'])} + i {_fmt(row['heavy_hole_side_imag_pm_per_V'])}) pm/V`; largest terms: {row['largest_pathways']}.")
    lines += [
        "",
        "All individual terms and subtotals at 1550 nm and each mode's peak are in "
        "`tables/pathway_contributions_1550_and_peaks.csv` and Figure 12. Figure 13 compares the "
        "eight largest 1550-nm pathways across modes.",
        "",
        "## 15. k-integrand interpretation",
        "",
    ]
    for mode in ("23A", "23B", "23C", "23D"):
        if mode in integrands:
            row = integrands[mode]
            lines.append(f"- {mode}: maximum absolute node at k=`{_fmt(row['k_at_max_absolute_node_per_nm'])} nm^-1`; 10–90% absolute-weight range `{_fmt(row['k_at_10pct_absolute_weight_per_nm'])}`–`{_fmt(row['k_at_90pct_absolute_weight_per_nm'])} nm^-1`; coherence ratio `{_fmt(row['coherence_ratio'])}`.")
    lines += [
        "",
        "Figure 10 shows real, imaginary, and magnitude per-node contributions. Figure 11 shows "
        "the cumulative complex integral; the absolute-weight quantiles above locate where the "
        "integrand is large without hiding cancellation.",
        "",
        "## 16. k-grid convergence",
        "",
        f"Grid convergence is **{_pass(bool(resolved['k_grid_converged']))}**. Figure 14 and "
        "`tables/k_grid_convergence.csv` report χ²(1550), peak χ², and peak wavelength for every "
        "configured N_k and mode.",
        "",
        "## 17. kmax convergence",
        "",
        f"Nominal kmax convergence is **{_pass(bool(resolved['kmax_converged']))}**. Figure 15 "
        "compares the configured cutoff ladder and marks the nominal 0.1 π/a cutoff.",
        "",
        "## 18. Isotropy validation",
        "",
        f"The two-direction isotropy check is **{_pass(bool(resolved['radial_assumption_validated']))}**. "
        "Figure 16 plots state-resolved energy differences. Passing supports the radial reduction "
        "over the sampled production range; failure means a direct 2D kp calculation is required.",
        "",
        "## 19. Comparison to Ramesh et al. Equation 2 spectrum",
        "",
        f"The full comparison uses **{resolved['paper_curve_label']}**, an "
        f"`{resolved['paper_curve_source_type']}` with `{resolved['paper_curve_points']}` points. "
        "It is not raw or tabulated author data and is not an acceptance gate.",
        "",
        "| Reference | Value | Category | Source type | Use |",
        "|---|---|---|---|---|",
    ]
    lines.extend(f"| {row['reference']} | {row['value']} | {row['category']} | {row['source_type']} | {row['use']} |" for row in paper_reference_rows)
    lines += [
        "",
        "P1 overlays absolute simulated susceptibility curves; the paper experiment is represented "
        "only by its separately labeled peak-location marker. P2 compares normalized shape, and "
        "P2b explicitly diagnoses the digitized paper zeros near 605 and 1330 nm. P3 "
        "compares peak locations, P4 compares 1550-nm values with an explicit abrupt-versus-graded "
        "caveat, and P5 reports digitization-dependent errors.",
        "",
        "| Mode | Normalized RMSE vs digitized paper | Peak λ error nm | χ²(1550) error pm/V |",
        "|---|---:|---:|---:|",
    ]
    for mode in ("23A", "23B", "23C", "23D"):
        if mode in paper:
            row = paper[mode]
            lines.append(f"| {mode} | {_fmt(row['normalized_RMSE_vs_digitized_paper'])} | {_fmt(row['peak_wavelength_error_nm'])} | {_fmt(row['chi2_1550_error_pm_per_V'])} |")
    lines += [
        "",
        "## 20. Remaining normalization/prefactor questions",
        "",
    ]
    lines.extend(f"- {item}" for item in unresolved)
    lines += [
        "",
        "The production calculation consistently uses the spin-degenerate `g_s k dk/(2π)` "
        "measure. Bare `2πk dk` and the two-individual-wells Nz interpretation remain labeled "
        "diagnostics and are not mixed into A–D results.",
        "",
        "## 21. Final scientific conclusion",
        "",
        f"- Did 23A reproduce the validated baseline? **{_pass(baseline_pass)}**, max complex error `{baseline_error:.8g} pm/V`.",
    ]
    for state in ("e1", "e2"):
        if state in fits:
            row = fits[state]
            lines.append(f"- Is {state} sufficiently parabolic? RMSE `{_fmt(row['RMSE_meV'])} meV`, evaluated against the explicit fit gate in the validation table.")
    for state in ("hh1", "hh2"):
        if state in fits:
            row = fits[state]
            lines.append(f"- {state} nonparabolicity: diagnostic RMSE `{_fmt(row['RMSE_meV'])} meV`, max error `{_fmt(row['max_abs_residual_meV'])} meV` at k=`{_fmt(row['k_at_max_residual_per_nm'])} nm^-1`.")
    if "23A" in by_mode and "23B" in by_mode:
        lines.append(f"- 23B change from 23A at 1550 nm: `{_fmt(float(by_mode['23B']['chi2_1550_pm_per_V']) - float(by_mode['23A']['chi2_1550_pm_per_V']))} pm/V`.")
    if "23B" in by_mode and "23C" in by_mode:
        lines.append(f"- Additional 23C hole-dispersion change from 23B at 1550 nm: `{_fmt(float(by_mode['23C']['chi2_1550_pm_per_V']) - float(by_mode['23B']['chi2_1550_pm_per_V']))} pm/V`.")
    if "23C" in by_mode and "23D" in by_mode:
        c = float(by_mode["23C"]["relative_spectrum_RMSE_vs_23D"])
        lines.append(f"- Does 23C reproduce 23D to ≤1% spectral RMSE? **{_pass(c <= float(resolved['boss_hybrid_relative_spectrum_tolerance']))}**; RMSE `{100*c:.6g}%`.")
    lines.append("- A–D χ²(1550) and peak wavelengths are reported in the master table above.")
    lines.append("- Dominant pathways and the dominant k range are reported in Sections 14–15 and their complete CSVs.")
    lines.append(f"- Is kmax converged? **{_pass(bool(resolved['kmax_converged']))}**. Is the radial approximation supported? **{_pass(bool(resolved['radial_assumption_validated']))}**.")
    if "23C" in paper and "23D" in paper:
        lines.append(f"- Full-spectrum comparison to the paper: normalized RMSE is `{_fmt(paper['23C']['normalized_RMSE_vs_digitized_paper'])}` for 23C and `{_fmt(paper['23D']['normalized_RMSE_vs_digitized_paper'])}` for 23D; their peak offsets from the digitized paper curve are `{_fmt(paper['23C']['peak_wavelength_error_nm'])} nm` and `{_fmt(paper['23D']['peak_wavelength_error_nm'])} nm`. These are diagnostic because the paper curve is eye-digitized.")
    lines += ["", "See `plots/`, `paper_comparison_plots/`, and `tables/` for the complete evidence set.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")

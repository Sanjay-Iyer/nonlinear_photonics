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
) -> None:
    by_mode = {str(row["mode"]): row for row in summary_rows}
    fits = {str(row["state"]): row for row in fit_rows}
    lines = [
        "# Demo 23 final scientific report",
        "",
        "Demo 23 changes only the four subband energy-dispersion models. All modes use the "
        "same validated k=0 matrix elements and Equation 2 pathway algebra.",
        "",
        "## Baseline gate",
        "",
        f"23A maximum complex spectral error versus Demo 20/21: `{baseline_error:.12g} pm/V` "
        f"(tolerance `{tolerance:.12g} pm/V`) — **{'PASS' if baseline_error <= tolerance else 'FAIL'}**.",
        "",
        "## A-D comparison",
        "",
        "| Mode | Dispersion | |chi2|(1550) pm/V | Peak pm/V | Peak wavelength nm | Relative spectrum RMSE vs 23D |",
        "|---|---|---:|---:|---:|---:|",
    ]
    descriptions = {
        "23A": "shared reduced-mass parabola",
        "23B": "four independent parabolas",
        "23C": "electron parabolas + nonparabolic kp8 holes",
        "23D": "nonparabolic kp8 energies for all four states",
    }
    for mode in ("23A", "23B", "23C", "23D"):
        if mode not in by_mode:
            continue
        row = by_mode[mode]
        lines.append(
            f"| {mode} | {descriptions[mode]} | {_fmt(row['chi2_1550_pm_per_V'])} | "
            f"{_fmt(row['peak_chi2_pm_per_V'])} | {_fmt(row['peak_wavelength_nm'])} | "
            f"{_fmt(row['relative_spectrum_RMSE_vs_23D'])} |"
        )
    lines += ["", "## Effective-mass fits", "",
              "| State | m*/m0 | RMSE meV | Max residual meV | Fit range nm^-1 | Pattern |",
              "|---|---:|---:|---:|---|---|"]
    for state in ("e1", "e2", "hh1", "hh2"):
        if state not in fits:
            continue
        row = fits[state]
        lines.append(
            f"| {state} | {_fmt(row['effective_mass_m0'])} | {_fmt(row['RMSE_meV'])} | "
            f"{_fmt(row['max_abs_residual_meV'])} | {_fmt(row['fit_kmin_per_nm'])}–"
            f"{_fmt(row['fit_kmax_per_nm'])} | {row['residual_pattern']} |"
        )
    lines += [
        "",
        "Heavy-hole fitted masses are diagnostics only; 23C uses shape-preserving interpolation of "
        "the tracked kp8 heavy-hole energies.",
        "",
        "## Integration and conventions",
        "",
        f"- Production measure: `{resolved['kspace_convention']}`.",
        f"- k_BZ definition: `{resolved['bz_definition']}`.",
        f"- kmax: `{_fmt(resolved['kmax_per_nm'])} nm^-1`.",
        f"- Spin degeneracy: `{resolved['spin_degeneracy']}`.",
        f"- Nz: `{_fmt(resolved['n_periods_per_metre'])} m^-1`, meaning "
        f"`{resolved['nz_semantics']}`.",
        f"- Gamma: `{_fmt(resolved['broadening_meV'])} meV` in energy-domain denominators.",
        "- Residual `1/hbar` from the boss slide was not introduced.",
        "- The bare radial normalization is reported only as a diagnostic and is never mixed with production values.",
        "",
        "## Convergence and isotropy",
        "",
        f"k-grid converged: **{resolved['k_grid_converged']}** (checking N_k="
        f"{resolved['grid_convergence_check_N_k']} against the production grid).",
        f"kmax converged at the nominal cutoff: **{resolved['kmax_converged']}**.",
        f"Radial/isotropy assumption validated: **{resolved['radial_assumption_validated']}**.",
        "See the CSV tables and plots beside this report for the quantitative values.",
        "",
        "## Unresolved physics questions",
        "",
    ]
    lines.extend(f"- {item}" for item in unresolved)
    lines += ["", "## Requested short conclusion", "",
              "```text", "BASELINE VALIDATION:"]
    lines.append(f"23A vs Demo 21 = max complex error {baseline_error:.8g} pm/V ({'PASS' if baseline_error <= tolerance else 'FAIL'})")
    lines.append("")
    lines.append("ELECTRON DISPERSION:")
    for state in ("e1", "e2"):
        if state in fits:
            lines.append(f"{state} = m*/m0 {_fmt(fits[state]['effective_mass_m0'])}, RMSE {_fmt(fits[state]['RMSE_meV'])} meV")
    lines.append("")
    lines.append("HEAVY-HOLE DISPERSION:")
    for state in ("hh1", "hh2"):
        if state in fits:
            lines.append(f"{state} = parabolic diagnostic RMSE {_fmt(fits[state]['RMSE_meV'])} meV; 23C uses kp8 interpolation")
    lines.append("")
    lines.append("BOSS HYBRID VALIDATION:")
    if "23C" in by_mode and "23D" in by_mode:
        lines.append(f"23C vs 23D = relative spectrum RMSE {_fmt(by_mode['23C']['relative_spectrum_RMSE_vs_23D'])}")
    else:
        lines.append("23C vs 23D = not computed in this selected-mode run")
    lines.append("")
    lines.append("CHI2 IMPACT:")
    lines.append("1550 nm:")
    for mode in ("23A", "23B", "23C", "23D"):
        if mode in by_mode:
            lines.append(f"{mode} = {_fmt(by_mode[mode]['chi2_1550_pm_per_V'])} pm/V")
    lines.append("")
    lines.append("Peak wavelength:")
    for mode in ("23A", "23B", "23C", "23D"):
        if mode in by_mode:
            lines.append(f"{mode} = {_fmt(by_mode[mode]['peak_wavelength_nm'])} nm")
    lines += ["", "INTEGRATION:",
              f"k grid converged? {resolved['k_grid_converged']}",
              f"kmax converged? {resolved['kmax_converged']}",
              f"radial assumption validated? {resolved['radial_assumption_validated']}",
              f"normalization convention used? {resolved['kspace_convention']}",
              "", "CONCLUSION:",
              f"Boss-requested reduced model validated? {resolved['boss_hybrid_validated']} "
              f"(relative spectrum tolerance {resolved['boss_hybrid_relative_spectrum_tolerance']:.6g}).",
              "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")

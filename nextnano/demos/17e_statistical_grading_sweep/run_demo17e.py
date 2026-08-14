"""CLI, orchestrator, summary reporter and plot generator for Demo 17E.

Only ``--physics`` can launch licensed full solves, and it launches
twenty-one of them: the ideal abrupt reference plus twenty seed-locked random
interface-grading realizations of the same structure. No optimizer runs at any
point and nothing in this file reads a result in order to choose a parameter --
the twenty realizations were drawn from a declared distribution before the first
deck was written, and are frozen in ``validation_cases.yaml``.

Everything structural is Demo 16E's and everything about the absolute scale is
Demo 17's, reused rather than copied: the same case ladder, the same parser and
realized-composition gates, the same solver invocation, the same Eq. 2
evaluator, the same three corrections. What this file supplies is the 21-case
loop, the two-scale summary tables, and the four diagnostic figures.

THE FIGURES ARE WRITTEN AT 300 DPI. The shared ``plots.save_figure`` helper is
fixed at 180 and is shared with every other demo in the repository, so this
module saves through :func:`_save` at the configured DPI while still recording
skips in the shared ledger -- a broken matplotlib degrades to a recorded skip
rather than destroying a multi-hour licensed run.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import uuid

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
SHARED = DEMOS / "_shared"
DEMO11 = DEMOS / "11_paper_validation_interband_chi2_acqw"
DEMO14 = DEMOS / "14_absolute_chi2_graded_acqw_bo"
DEMO16 = DEMOS / "16_acqw_renderer_stress_validation"
DEMO16B = DEMOS / "16B_simple_acqw_grading_validation"
DEMO16E = DEMOS / "16E_acqw_structure_physics_optical_comparison"
DEMO17 = DEMOS / "17_paper_chi2_reproduction_corrected"
for path in (SHARED, DEMO14, DEMO11, DEMO16, DEMO16B, DEMO16E, DEMO17, DEMO_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cases17e  # noqa: E402
import demo16e  # noqa: E402
import demo17  # noqa: E402
import demo17e  # noqa: E402
import plots16e  # noqa: E402
import preflight17e  # noqa: E402
import runlog14  # noqa: E402

RULE = "=" * 82
CASE_COUNT = cases17e.CASE_COUNT
STUDY_CSV = "study_summary.csv"
STUDY_JSON = "study_summary.json"
STRUCTURE_CSV = "structure_summary.csv"
SPECTRUM_CSV = "chi2_spectrum_all_cases.csv"

#: The bound-state verdict is tri-state on purpose: "could not tell" is a
#: different outcome from "passed", and printing them the same way is exactly how
#: a NOT CERTIFIED result gets read as a pass.
BOUND_LABEL = {True: "PASS", False: "FAIL", None: "NOT CERTIFIED"}

#: ``study_summary.csv`` column order. Written explicitly so the file is stable
#: across runs and so a Demo 17E table can be diffed against a Demo 17 one where
#: they overlap. The required study columns come first, in reading order:
#: identity, what was drawn, the energies, the dual optical scale, then QC.
STUDY_FIELDS = [
    "case", "case_name", "severity", "realization_index",
    "is_reference_case", "is_paper_target_case", "representation",
    # --- the variable -----------------------------------------------------
    "mean_grading_width_nm",
    "sigma_gaas_to_algaas_barrier_nm", "sigma_algaas_to_gaas_well_nm",
    "sigma_gaas_to_algaas_cladding_nm",
    "deck_rise_grading_nm", "deck_fall_grading_nm", "rise_tie_residual_nm",
    "narrowest_ramp_mesh_cells",
    # --- the fixed structure, repeated so a row stands alone --------------
    "well_1_nm", "central_barrier_nm", "well_2_nm", "asymmetry_s",
    "realized_peak_xAl", "max_composition_error", "rms_composition_error",
    # --- energies ---------------------------------------------------------
    "E1_eV", "E2_eV", "HH1_eV", "HH2_eV",
    "E2_minus_E1_meV", "HH1_minus_HH2_meV",
    "transition_e1_hh1_eV", "transition_e2_hh2_eV",
    "delta_E1_meV_vs_reference", "delta_E2_meV_vs_reference",
    "delta_HH1_meV_vs_reference", "delta_HH2_meV_vs_reference",
    # --- the dual optical scale -------------------------------------------
    "chi2_1550_raw_pm_per_V", "chi2_1550_calibrated_pm_per_V",
    "peak_chi2_raw_pm_per_V", "peak_chi2_calibrated_pm_per_V",
    "peak_wavelength_nm", "detuning_from_1550_nm", "peak_over_1550_contrast",
    "chi2_1550_over_reference", "peak_chi2_over_reference",
    "chi2_1550_change_percent_vs_reference",
    "peak_wavelength_shift_nm_vs_reference",
    "calibration_id", "calibration_multiplier", "calibration_status",
    "raw_units", "calibrated_units",
    # --- localization, for the states Eq. 2 used --------------------------
]
for _state in demo17e.STATE_LABELS:
    STUDY_FIELDS += [
        f"{_state}_left_probability", f"{_state}_barrier_probability",
        f"{_state}_right_probability", f"{_state}_outside_probability",
        f"{_state}_localization",
    ]
STUDY_FIELDS += [
    # --- quality control ---------------------------------------------------
    "bound_states_certified", "bound_states_failing", "max_boundary_probability",
    "quantum_region_width_nm", "dirichlet_clearance_nm",
    "paper_target_pm_per_V", "paper_remaining_factor_on_raw_peak",
    # --- provenance --------------------------------------------------------
    "reference_case", "spectrum_path", "envelopes_csv_path",
    "matrix_elements_path", "wavefunction_csv_path", "raw_output_dir",
]

#: One colour per severity band, used by every figure so a reader learns the
#: legend once. The abrupt reference is always black and always dashed.
SEVERITY_COLOURS = {
    "sharp": "#1f6f4a",
    "moderate": "#1f4e79",
    "severe": "#c0392b",
    cases17e.SEVERITY_ABRUPT: "#111111",
}
REFERENCE_STYLE = {"color": "#111111", "linestyle": "--", "lw": 2.2, "zorder": 6}


def resolve_machine():
    import demo_workflow as workflow
    return workflow.load_machine_config()


def _machine_or_none():
    try:
        return resolve_machine()
    except Exception:  # noqa: BLE001
        return None


def results_root() -> Path:
    machine = _machine_or_none()
    if machine is not None and getattr(machine, "results_root", None):
        return Path(machine.results_root)
    return DEMOS.parents[0] / "results" / "demo_runs"


def new_run_dir() -> tuple[Path, str]:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo17e_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo17e.DEMO_ID / run_id
    for sub in ("cases", "plots", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def _dpi(cfg) -> int:
    return int((cfg.get("plotting") or {}).get("dpi", 300))


def _save(fig, path: Path, dpi: int, *, tight: bool = True) -> Path | None:
    """Save at Demo 17E's DPI, with the shared demo's skip accounting.

    ``plots.save_figure`` is fixed at 180 and is shared with every other demo, so
    raising it there would silently re-render every figure in the repository.
    This writes at the configured DPI and still records a skip in the shared
    ledger, so ``plots.status()`` remains the one place a run reports what it
    could not draw.
    """

    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


def _skip(path: Path) -> None:
    import plots
    plots.SKIPPED_FIGURES.append(Path(path).name)


def _drawable(rows, key: str) -> list:
    return [row for row in rows if row.get(key) is not None]


def _case_colour(row) -> str:
    return SEVERITY_COLOURS.get(str(row.get("severity")), "#7b3f98")


def composition_all_cases(path: Path, entries, dpi: int) -> Path | None:
    """Question: how differently is aluminium distributed across the 21 profiles?

    Two panels sharing one x axis. The top is the whole active region, where the
    twenty realizations are almost indistinguishable -- which is itself the
    result, since interface roughness is a small perturbation on the layer stack.
    The bottom magnifies the 1.80 nm tunnelling barrier, where they are not, and
    that is the region the coupling and therefore chi(2) actually live in.
    """

    import plots

    if not plots.plotting_available() or not entries:
        _skip(path)
        return None

    import matplotlib.pyplot as plt

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10.4, 9.0), gridspec_kw={"height_ratios": [1.0, 1.0]}
    )
    seen_bands: set[str] = set()
    handles, labels = [], []
    for entry in entries:
        case = entry["case"]
        severity = case.severity
        style = (
            dict(REFERENCE_STYLE) if case.is_reference
            else {"color": SEVERITY_COLOURS.get(severity, "#7b3f98"),
                  "linestyle": "-", "lw": 1.2, "alpha": 0.75, "zorder": 3}
        )
        for ax in (top, bottom):
            line, = ax.plot(entry["x_nm"], entry["al_fraction"], **style)
        # One legend entry per band rather than 21 near-identical ones: a legend
        # with twenty entries for twenty overlapping curves is not a legend.
        if case.is_reference:
            handles.append(line)
            labels.append(f"{case.case_id} abrupt reference (0.00 nm)")
        elif severity not in seen_bands:
            seen_bands.add(severity)
            members = [e["case"] for e in entries
                       if not e["case"].is_reference and e["case"].severity == severity]
            widths = [c.mean_interface_width_nm() for c in members]
            handles.append(line)
            labels.append(
                f"{severity} -- {len(members)} realizations, "
                f"{min(widths):.2f}-{max(widths):.2f} nm"
            )

    reference = entries[0]["interfaces"]
    z1 = float(reference["outer_left_algaas_to_gaas"])
    z4 = float(reference["outer_right_gaas_to_algaas"])
    top.set_xlim(z1 - 2.5, z4 + 2.5)
    top.set_ylim(-0.01, 0.60)
    top.set_ylabel("aluminium fraction $x_{Al}$")
    top.set_title(
        f"Aluminium Composition of All {len(entries)} Structures", fontsize=12
    )
    top.grid(alpha=0.18)

    centre = float(reference["central_gaas_to_algaas"])
    other = float(reference["central_algaas_to_gaas"])
    bottom.set_xlim(centre - 2.2, other + 2.2)
    bottom.set_ylim(-0.01, 0.60)
    bottom.set_xlabel("position $z$ (nm)")
    bottom.set_ylabel("aluminium fraction $x_{Al}$")
    bottom.set_title(
        "Tunnelling Barrier, Magnified -- where the realizations differ",
        fontsize=10,
    )
    bottom.grid(alpha=0.18)

    fig.legend(handles, labels, fontsize=8.5, ncol=2, loc="lower center",
               framealpha=0.94)
    fig.subplots_adjust(bottom=0.15, hspace=0.26, top=0.94)
    return _save(fig, path, dpi, tight=False)


def chi2_wavelength_all_cases(path: Path, rows, cfg, dpi: int) -> Path | None:
    """Question: what does interface roughness do to the whole spectrum?

    All 21 curves on one panel, no normalisation: the actual computed magnitudes
    are drawn, because how far apart the responses are is the thing being
    measured. The abrupt reference is black and dashed and sits on top, so the
    statistical spread is read as a displacement from a solved anchor rather than
    as a cloud.
    """

    import plots

    rows = _drawable(rows, "chi2_1550_raw_pm_per_V")
    if not plots.plotting_available() or not rows:
        _skip(path)
        return None

    import matplotlib.pyplot as plt

    calibration = rows[0].get("calibration_multiplier") or 1.0
    fig, ax = plt.subplots(figsize=(11.4, 6.6))
    drawn = 0
    band_seen: set[str] = set()
    # Reference first, then bands in severity order, so the legend reads
    # sharp -> moderate -> severe however the cases happen to be ordered.
    band_order = [str(band["key"]) for band in
                  (cfg.get("severity_bands") or cases17e.DEFAULT_SEVERITY_BANDS)]
    rows = sorted(rows, key=lambda r: (
        0 if r.get("is_reference_case") else 1,
        band_order.index(str(r.get("severity")))
        if str(r.get("severity")) in band_order else len(band_order),
    ))
    for row in rows:
        spectrum = demo17e.read_spectrum(row.get("spectrum_path") or "")
        if spectrum is None:
            continue
        wavelength, magnitude = spectrum
        if row.get("is_reference_case"):
            ax.plot(wavelength, magnitude, label=f"{row['case']} abrupt reference",
                    **REFERENCE_STYLE)
        else:
            severity = str(row.get("severity"))
            label = None
            if severity not in band_seen:
                band_seen.add(severity)
                label = f"{severity} realizations"
            ax.plot(wavelength, magnitude, color=_case_colour(row), lw=1.1,
                    alpha=0.7, zorder=3, label=label)
        ax.scatter([demo17e.TARGET_WAVELENGTH_NM], [row["chi2_1550_raw_pm_per_V"]],
                   s=22, zorder=7, color=_case_colour(row), edgecolor="white",
                   linewidth=0.5)
        drawn += 1
    if not drawn:
        plt.close(fig)
        _skip(path)
        return None

    ax.axvline(demo17e.TARGET_WAVELENGTH_NM, color="#222222", ls="--", lw=1.4,
               zorder=2)
    ax.annotate("1550 nm", xy=(demo17e.TARGET_WAVELENGTH_NM, 1.0),
                xycoords=("data", "axes fraction"), xytext=(5, -14),
                textcoords="offset points", fontsize=9.5, color="#222222")
    ax.set_xlabel("fundamental wavelength (nm)")
    ax.set_ylabel(r"raw $|\chi^{(2)}_{xzx}|$ (pm/V)")
    ax.set_title(
        f"Nonlinear Response of {drawn} Interface Realizations, 1400-1800 nm",
        fontsize=12,
    )
    ax.legend(fontsize=8.5, framealpha=0.94)
    ax.grid(alpha=0.2)

    # A second axis rather than a second figure: the calibrated column is the
    # same curve read against a different tick set, and putting it anywhere else
    # would invite someone to plot it as if it were an independent result.
    if calibration and float(calibration) != 1.0:
        right = ax.secondary_yaxis(
            "right",
            functions=(lambda v: v * float(calibration),
                       lambda v: v / float(calibration)),
        )
        right.set_ylabel(
            f"calibrated (x{float(calibration):g}, "
            f"{rows[0].get('calibration_id')}, declared not derived) (pm/V)",
            fontsize=9,
        )
    return _save(fig, path, dpi)


def chi2_wavelength_grouped(path: Path, rows, cfg, dpi: int) -> Path | None:
    """The same spectra split by grading severity, each with a +-1 SD band.

    Question: does the spread grow with the roughness, or only the mean?

    The band is the pointwise mean +- one standard deviation across that band's
    realizations, on the shared 1 nm grid -- which is why the grid is checked to
    be exactly 1 nm before anything is solved. A band drawn from fewer than two
    curves is not drawn at all, because a standard deviation of one sample is
    zero and would paint a confident-looking line with no content.
    """

    import plots

    rows = _drawable(rows, "chi2_1550_raw_pm_per_V")
    if not plots.plotting_available() or not rows:
        _skip(path)
        return None

    import matplotlib.pyplot as plt
    import numpy as np

    bands = cfg.get("severity_bands") or cases17e.DEFAULT_SEVERITY_BANDS
    reference_row = next((r for r in rows if r.get("is_reference_case")), None)
    reference_spectrum = (
        None if reference_row is None
        else demo17e.read_spectrum(reference_row.get("spectrum_path") or "")
    )

    # sharey, deliberately: the question is how much amplitude each band loses
    # against the abrupt anchor, and three independently auto-scaled panels would
    # normalise that difference away -- each band would look equally tall.
    fig, axes = plt.subplots(len(bands), 1, figsize=(10.4, 3.8 * len(bands) + 1.0),
                             sharex=True, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, band in zip(axes, bands):
        key = str(band["key"])
        colour = SEVERITY_COLOURS.get(key, "#7b3f98")
        members = [r for r in rows
                   if not r.get("is_reference_case") and r.get("severity") == key]
        curves, grid = [], None
        for row in members:
            spectrum = demo17e.read_spectrum(row.get("spectrum_path") or "")
            if spectrum is None:
                continue
            grid = spectrum[0]
            curves.append(spectrum[1])
            ax.plot(spectrum[0], spectrum[1], color=colour, lw=0.9, alpha=0.45,
                    zorder=3)
        if curves and grid is not None:
            stack = np.vstack(curves)
            mean = stack.mean(axis=0)
            ax.plot(grid, mean, color=colour, lw=2.4, zorder=5,
                    label=f"{key} mean (n={len(curves)})")
            if len(curves) > 1:
                deviation = stack.std(axis=0, ddof=1)
                ax.fill_between(grid, mean - deviation, mean + deviation,
                                color=colour, alpha=0.18, zorder=1,
                                label=r"$\pm 1\sigma$ across realizations")
        if reference_spectrum is not None:
            ax.plot(reference_spectrum[0], reference_spectrum[1],
                    label=f"{reference_row['case']} abrupt reference",
                    **REFERENCE_STYLE)
        ax.axvline(demo17e.TARGET_WAVELENGTH_NM, color="#222222", ls="--", lw=1.2,
                   zorder=2)
        widths = [r.get("mean_grading_width_nm") for r in members
                  if r.get("mean_grading_width_nm") is not None]
        span = (f"{min(widths):.2f}-{max(widths):.2f} nm" if widths else "no members")
        ax.set_title(
            f"{band.get('label', key)} -- {len(members)} realizations, {span}",
            fontsize=10.5,
        )
        ax.set_ylabel(r"raw $|\chi^{(2)}|$ (pm/V)")
        ax.legend(fontsize=8, framealpha=0.94)
        ax.grid(alpha=0.2)
    axes[-1].set_xlabel("fundamental wavelength (nm)")
    fig.suptitle(
        "Nonlinear Response Grouped by Interface Grading Severity", fontsize=12.5
    )
    fig.subplots_adjust(top=0.94, hspace=0.24)
    return _save(fig, path, dpi, tight=False)


def chi2_vs_grading_width(path: Path, rows, summary, dpi: int) -> Path | None:
    """Question: how much chi(2) does a nanometre of interface roughness cost?

    Two panels, one per reported quantity, both against the mean rendered
    interface width. Each carries the least-squares line from
    ``demo17e.grading_trend`` with its r^2, and the abrupt reference is drawn as a
    horizontal line rather than as a point at x = 0: it is an anchor of a
    different kind (its deck has no ramps at all), and letting it sit inside the
    fit would let one point lever the whole slope.
    """

    import plots

    rows = _drawable(rows, "mean_grading_width_nm")
    graded = [r for r in rows if not r.get("is_reference_case")]
    if not plots.plotting_available() or len(graded) < 2:
        _skip(path)
        return None

    import matplotlib.pyplot as plt
    import numpy as np

    reference = next((r for r in rows if r.get("is_reference_case")), None)
    trends = (summary.get("trends") or {})
    fig, axes = plt.subplots(2, 1, figsize=(10.0, 9.2), sharex=True)
    panels = (
        (axes[0], "peak_chi2_raw_pm_per_V", "peak_chi2",
         r"peak raw $|\chi^{(2)}|$ (pm/V)", "Spectral Peak"),
        (axes[1], "chi2_1550_raw_pm_per_V", "chi2_at_1550",
         r"raw $|\chi^{(2)}|$ at 1550 nm (pm/V)", "At 1550 nm"),
    )
    for ax, key, trend_key, ylabel, title in panels:
        usable = [r for r in graded if r.get(key) is not None]
        if not usable:
            ax.annotate("no values available", xy=(0.5, 0.5),
                        xycoords="axes fraction", ha="center", fontsize=10)
            continue
        x = np.array([float(r["mean_grading_width_nm"]) for r in usable])
        y = np.array([float(r[key]) for r in usable])
        ax.scatter(x, y, s=64, zorder=4, edgecolor="white", linewidth=0.7,
                   c=[_case_colour(r) for r in usable])
        for row, xi, yi in zip(usable, x, y):
            ax.annotate(str(row["case"]).replace("case_", ""), xy=(xi, yi),
                        xytext=(0, 8), textcoords="offset points", ha="center",
                        fontsize=6.5, color="#555555")
        trend = trends.get(trend_key) or {}
        if trend.get("computable"):
            line_x = np.linspace(x.min(), x.max(), 64)
            line_y = float(trend["slope_per_nm"]) * line_x + float(trend["intercept"])
            r_squared = trend.get("r_squared")
            ax.plot(line_x, line_y, color="#555555", ls="-", lw=1.6, zorder=3,
                    label=(f"least squares: {trend['slope_per_nm']:+.1f} pm/V per nm"
                           + ("" if r_squared is None else f"  ($r^2$={r_squared:.2f})")))
        if reference is not None and reference.get(key) is not None:
            ax.axhline(float(reference[key]), zorder=2,
                       label=(f"{reference['case']} abrupt reference: "
                              f"{float(reference[key]):.1f} pm/V"),
                       **{k: v for k, v in REFERENCE_STYLE.items() if k != "zorder"})
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=10.5)
        ax.legend(fontsize=8.5, framealpha=0.94)
        ax.grid(alpha=0.2)
    axes[-1].set_xlabel("mean interface grading width $\\sigma$ (nm), as rendered")
    fig.suptitle(
        "Second-Order Susceptibility versus Interface Grading Width",
        fontsize=12.5, y=0.985,
    )
    # Both panels keep their own title, so the figure title needs room above the
    # first one rather than on top of it.
    fig.subplots_adjust(top=0.925, hspace=0.18)
    return _save(fig, path, dpi, tight=False)


# ---------------------------------------------------------------------------
# Structure levels
# ---------------------------------------------------------------------------


def _seed_run(root: Path, run_id: str, mode: str, machine, exe, database, licence,
              case_count: int, cfg, calibration) -> dict:
    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo17e.DEMO_ID,
        "demo17e_version": demo17e.DEMO_VERSION,
        "structural_engine": demo16e.DEMO_VERSION,
        "correction_engine": demo17.DEMO_VERSION,
        "mode": mode,
        "optimization_performed": False,
        "calibration_id": calibration.scale_id,
        "calibration_multiplier": calibration.multiplier,
        "nextnano_executable": str(exe) if exe else None,
        "nextnano_database": str(database) if database else None,
        "nextnano_license": str(licence) if licence else None,
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
        "run_solver_enabled": bool(getattr(machine, "run_solver", False)),
    }
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "running", "cases_total": case_count},
    )
    runlog14.write_text_atomic(
        root / cases17e.CASES_FILENAME,
        (DEMO_DIR / cases17e.CASES_FILENAME).read_text(encoding="utf-8"),
    )
    # Stamped before anything is solved, so what a run claims about its
    # corrections and its reporting scale cannot be edited into it afterwards.
    demo17e.write_manifests(root, cfg, calibration)
    return environment


def _print_header(cfg, plan, calibration) -> None:
    record = demo17.corrections_record(cfg)
    a, b, c = record["A_n_wells_per_metre"], record["B_k_max_per_nm"], record["C_domain"]
    print(f"  CORRECTION A : N_z {a['legacy']:.4e} -> {a['corrected']:.4e} m^-1 "
          f"({a['ratio']:.3f}x, exact)")
    print(f"  CORRECTION B : k_max {b['legacy']:.4f} -> {b['corrected']:.4f} nm^-1 "
          f"({b['zone_edge_convention']})")
    print(f"  CORRECTION C : cladding {c['domain_padding_nm']:.1f} nm, Dirichlet "
          f"wall {c['quantum_region_padding_nm']:.1f} nm clear of the wells")
    print(f"  SAMPLING     : seed {plan.seed}, {plan.distribution}, "
          f"mu={plan.mean_nm} nm sd={plan.standard_deviation_nm} nm, "
          f"clipped to [{plan.minimum_nm}, {plan.maximum_nm}] nm")
    print(f"  SCALES       : raw 1.00x (nothing fitted)  |  calibrated "
          f"{calibration.scale_id} {calibration.multiplier:g}x "
          f"({calibration.status}, declared not derived)")


def run_levels(*, do_parse: bool, do_structure: bool, mode: str,
               selected_cases=None, verbose: bool = False,
               calibration_id: str | None = None):
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo17e.load_config()
    plan = cases17e.sampling_plan_from_config(cfg)
    calibration = demo17e.active_calibration(cfg, calibration_id)
    cases = list(selected_cases if selected_cases is not None else
                 cases17e.load_cases(DEMO_DIR / cases17e.CASES_FILENAME, plan))
    machine = _machine_or_none()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    root, run_id = new_run_dir()
    environment = _seed_run(
        root, run_id, mode, machine, exe, database, licence, len(cases), cfg,
        calibration,
    )

    print(RULE)
    print(f"  DEMO 17E -- {mode.upper()}  (statistical interface roughness sweep)")
    print(RULE)
    print(f"  RUN DIR      : {root}")
    print(f"  EXECUTABLE   : {exe or '<none found>'}")
    print(f"  CASES        : {len(cases)} (1 abrupt reference + "
          f"{len(cases) - 1} frozen realizations, no optimization)")
    _print_header(cfg, plan, calibration)
    if mode == "physics":
        print("  NOTE         : parser + realized-composition gates precede every "
              "full solve.")
    elif do_structure:
        print("  NOTE         : composition construction only; no quantum solve.")
    else:
        print("  NOTE         : syntax parsing only; no quantum solve.")
    print(RULE)

    outcomes = []
    for case in cases:
        case_dir = root / "cases" / case.case_id
        outcome = demo17e.run_case(
            cfg, case, case_dir, exe=exe, database=database,
            license_path=licence, do_parse=do_parse, do_structure=do_structure,
        )
        outcomes.append(outcome)
        comparison = (outcome.structure or {}).get("comparison") or {}
        error = ""
        if comparison:
            error = (
                f" max|dx|={comparison['gated_max_absolute_al_fraction_difference']:.2e}"
                f" rms={comparison['gated_rms_al_fraction_difference']:.2e}"
            )
        print(
            f"  [{outcome.status:<22}] {case.case_id} "
            f"sigma={case.mean_interface_width_nm():.3f} nm "
            f"({case.left_grading_width_nm:.3f}/{case.right_grading_width_nm:.3f}) "
            f"{case.severity:<9} "
            f"{outcome.representation or case.expected_representation}"
            f"{' REFERENCE' if case.is_reference else ''}{error}"
        )
        if outcome.failure_reason and verbose:
            print(f"                           {outcome.failure_reason}")

    _write_structure_plots(root, cfg, cases, outcomes)
    passed_states = {"structure_passed"} if do_structure else {"parser_passed"}
    passed = sum(outcome.status in passed_states for outcome in outcomes)
    runlog14.write_json_atomic(root / "summary.json", {
        **environment, "cases_total": len(outcomes), "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
        "sampling": plan.as_record(),
        "corrections": demo17.corrections_record(cfg),
        "calibration": demo17e.calibration_record(cfg, calibration),
        "cases": [outcome.as_record() for outcome in outcomes],
    })
    _write_structure_summary(
        root / "summaries" / STRUCTURE_CSV, cfg, cases, outcomes
    )
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "completed", "cases_total": len(outcomes),
         "cases_passed": passed, "cases_failed": len(outcomes) - passed},
    )
    _write_run_readme(root, environment, cfg, plan, calibration, cases, outcomes)
    print(RULE)
    label = "PRE-PHYSICS GATE" if mode == "physics" else "RESULT"
    print(f"  {label}: {passed}/{len(outcomes)} passed")
    print(f"  FILES : {root}")
    print(RULE)
    return (0 if passed == len(outcomes) else 1), root, outcomes, cfg, plan, calibration


def _fmt(value, spec=".6f") -> str:
    return "" if value is None else format(value, spec)


def _write_structure_summary(path: Path, cfg, cases, outcomes) -> None:
    """The composition table: requested versus realized, per interface."""

    fields = [
        "case_id", "name", "severity", "status", "representation",
        "mean_grading_width_nm", "deck_rise_grading_nm", "deck_fall_grading_nm",
        "sigma_gaas_to_algaas_barrier_nm", "sigma_algaas_to_gaas_well_nm",
        "sigma_gaas_to_algaas_cladding_nm", "rise_tie_residual_nm",
        "requested_well_1_nm", "realized_well_1_nm",
        "requested_barrier_nm", "realized_barrier_nm",
        "requested_well_2_nm", "realized_well_2_nm", "realized_total_well_nm",
        "realized_left_grading_nm", "realized_right_grading_nm",
        "render_method", "expected_peak_al", "realized_peak_al",
        "max_abs_al_error", "rms_al_error", "gated_max_abs_al_error",
        "domain_width_nm", "quantum_region_width_nm",
        "dirichlet_clearance_left_nm", "dirichlet_clearance_right_nm",
    ]
    lines = [",".join(fields) + "\n"]
    for case, outcome in zip(cases, outcomes):
        metric = (outcome.structure or {}).get("comparison") or {}
        geometry = metric.get("geometry") or {}
        realized = {
            row["interface"]: row.get("realized_width_10_90_nm")
            for row in metric.get("realized_interface_metrics") or []
        }
        deck = demo17e.deck_geometry_record(cfg, case)
        sampled = dict(case.sampled_widths_nm)
        w1, w2 = case.well_widths_nm()
        lines.append(",".join([
            case.case_id, case.name, case.severity, outcome.status,
            outcome.representation or case.expected_representation,
            _fmt(case.mean_interface_width_nm(), ".4f"),
            _fmt(case.left_grading_width_nm, ".4f"),
            _fmt(case.right_grading_width_nm, ".4f"),
            _fmt(sampled.get("gaas_to_algaas_barrier"), ".4f"),
            _fmt(sampled.get("algaas_to_gaas_well"), ".4f"),
            _fmt(sampled.get("gaas_to_algaas_cladding"), ".4f"),
            _fmt(case.rise_tie_residual_nm(), ".4f"),
            _fmt(w1), _fmt(geometry.get("realized_well_1_nm")),
            _fmt(case.central_barrier_nm),
            _fmt(geometry.get("realized_central_barrier_nm")), _fmt(w2),
            _fmt(geometry.get("realized_well_2_nm")),
            _fmt(geometry.get("realized_total_gaas_well_nm")),
            _fmt(realized.get("central_gaas_to_algaas")),
            _fmt(realized.get("central_algaas_to_gaas")),
            outcome.render_method,
            _fmt(metric.get("expected_peak_al_fraction")),
            _fmt(metric.get("realized_peak_al_fraction")),
            _fmt(metric.get("max_absolute_al_fraction_difference"), ".3e"),
            _fmt(metric.get("rms_al_fraction_difference"), ".3e"),
            _fmt(metric.get("gated_max_absolute_al_fraction_difference"), ".3e"),
            _fmt(deck.get("domain_width_nm"), ".3f"),
            _fmt(deck.get("quantum_region_width_nm"), ".3f"),
            _fmt(deck.get("dirichlet_clearance_left_nm"), ".3f"),
            _fmt(deck.get("dirichlet_clearance_right_nm"), ".3f"),
        ]) + "\n")
    runlog14.write_text_atomic(path, "".join(lines))


def _read_two_column_csv(path: Path):
    import numpy as np
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def _profile_entries(cfg, cases, outcomes) -> list[dict]:
    entries = []
    for case, outcome in zip(cases, outcomes):
        if outcome.status == "render_failed":
            continue
        _geometry, profile, _blocks, _deck = demo17e.build_case(cfg, case)
        realized_x = realized_al = None
        realized_path = (outcome.structure or {}).get("realized_profile_path")
        if realized_path and Path(realized_path).is_file():
            realized_x, realized_al = _read_two_column_csv(Path(realized_path))
        entries.append({
            "case": case,
            "x_nm": profile.x_nm,
            "al_fraction": profile.al_fraction,
            "interfaces": profile.request["interfaces_nm"],
            "realized_x_nm": realized_x,
            "realized_al": realized_al,
        })
    return entries


def _write_structure_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    dpi = _dpi(cfg)
    entries = _profile_entries(cfg, cases, outcomes)
    for entry in entries:
        case = entry["case"]
        plots16e.composition_figure(
            root / "cases" / case.case_id / "plots" / "composition.png",
            title=plots16e.case_title(case, "Composition"),
            interfaces=entry["interfaces"],
            intended_x_nm=entry["x_nm"], intended_al=entry["al_fraction"],
            realized_x_nm=entry["realized_x_nm"], realized_al=entry["realized_al"],
            max_al_fraction=cases17e.AL_FRACTION,
            note=("realized profile unavailable" if entry["realized_x_nm"] is None
                  else f"nextnano++ realized composition ({case.expected_representation})"),
        )
    if entries:
        composition_all_cases(
            root / "plots" / "composition_all_cases.png", entries, dpi
        )


def _write_run_readme(root: Path, environment: dict, cfg, plan, calibration,
                      cases, outcomes) -> None:
    stats = cases17e.statistics_record(cases)
    width = stats["mean_interface_grading_width"]
    rows = [
        "| case | severity | mean sigma (nm) | barrier | well | cladding | status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for case, outcome in zip(cases, outcomes):
        sampled = dict(case.sampled_widths_nm)
        rows.append(
            f"| {case.case_id} | {case.severity} | "
            f"{case.mean_interface_width_nm():.4f} | "
            + " | ".join(
                "abrupt" if case.is_abrupt
                else f"{sampled.get(key, float('nan')):.4f}"
                for key in cases17e.SAMPLED_INTERFACES
            )
            + f" | {outcome.status} |"
        )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 17E run {environment['run_id']}", "",
        "One fixed paper-geometry GaAs/Al0.55Ga0.45As ACQW "
        f"({len(cases)} solves): the ideal abrupt reference plus "
        f"{len(cases) - 1} seed-locked random interface-grading realizations.",
        "Grading is the only thing that varies.", "",
        "## Sampling", "",
        f"- seed **{plan.seed}**, {plan.distribution}, mu = {plan.mean_nm} nm, "
        f"sd = {plan.standard_deviation_nm} nm, bounds "
        f"[{plan.minimum_nm}, {plan.maximum_nm}] nm",
        f"- realized mean width {width['min_nm']:.4f} - {width['max_nm']:.4f} nm "
        f"(mean {width['mean_nm']:.4f}, sd {width['stdev_nm']:.4f})",
        f"- severity split: "
        + ", ".join(f"{k}={v}" for k, v in stats["severity_counts"].items()),
        f"- narrowest ramp spans {stats['narrowest_ramp_mesh_cells']:.1f} mesh cells",
        "",
        "## Reporting scales", "",
        "- **raw** 1.00x -- nothing fitted; the only scale that follows from "
        "cited physics end to end.",
        f"- **calibrated** {calibration.scale_id} {calibration.multiplier:g}x "
        f"({calibration.status}) -- a DECLARED multiplier carried from Demo 17D. "
        "It puts the numbers on the paper's axis; it does not validate the scale, "
        "and no gate in this demo reads it.",
        "",
        *rows, "",
        "Only --physics launches full licensed calculations. Raw quantum output "
        "uses the short run-root paths p00 .. p20.", "",
    ]))


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------


def _write_study_summary(root: Path, cfg, plan, calibration, rows: list[dict]) -> None:
    summaries = root / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    payload = {
        "demo_id": demo17e.DEMO_ID,
        "demo17e_version": demo17e.DEMO_VERSION,
        "target_wavelength_nm": demo17e.TARGET_WAVELENGTH_NM,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "localization_convention": demo17e.LOCALIZATION_CONVENTION,
        "hole_energy_convention": demo17e.HOLE_ENERGY_CONVENTION,
        "reference_case": cases17e.REFERENCE_CASE_ID,
        "paper_target_case": cases17e.PAPER_TARGET_CASE_ID,
        "optimization_performed": False,
        "cases_reported": len(rows),
        "study_summary": demo17e.study_summary(cfg, rows, calibration, plan),
        "cases": rows,
    }
    runlog14.write_json_atomic(summaries / STUDY_JSON, payload)
    with (summaries / STUDY_CSV).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=STUDY_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    demo17e.write_spectrum_matrix(summaries / SPECTRUM_CSV, cfg, rows, calibration)


def _write_comparison_plots(root: Path, cfg, rows: list[dict], summary) -> None:
    import plots

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    dpi = _dpi(cfg)
    plots_dir = root / "plots"
    chi2_wavelength_all_cases(
        plots_dir / "chi2_wavelength_all_cases.png", rows, cfg, dpi
    )
    chi2_wavelength_grouped(
        plots_dir / "chi2_wavelength_grouped.png", rows, cfg, dpi
    )
    chi2_vs_grading_width(
        plots_dir / "chi2_vs_grading_width.png", rows,
        (summary.get("roughness") or {}), dpi,
    )
    # Demo 16E's cross-case figures still answer their own questions on this
    # ensemble, so they are drawn too rather than reimplemented.
    plots16e.energy_levels_all_cases(plots_dir / "energy_levels_all_cases.png", rows)
    plots16e.localization_all_cases(
        plots_dir / "wavefunction_localization_all_cases.png", rows
    )
    plots16e.peak_wavelength_and_detuning(
        plots_dir / "peak_wavelength_and_detuning.png", rows
    )


def _write_wavefunction_plots(root: Path, cfg, case, record) -> None:
    import plots

    waves = record.pop("_wavefunctions", None)
    if waves is None or not plots.plotting_available():
        return
    _geometry, profile, _blocks, _deck = demo17e.build_case(cfg, case)
    localization = (record.get("localization") or {}).get("by_state") or {}
    plots16e.wavefunction_figure(
        root / "cases" / case.case_id / "plots" / "wavefunctions.png",
        title=plots16e.case_title(case, "Band Edges and Wavefunctions"),
        interfaces=profile.request["interfaces_nm"],
        intended_x_nm=profile.x_nm, intended_al=profile.al_fraction,
        band_position_nm=waves.band_position_nm, band_edges=waves.band_edges,
        state_x_nm=waves.position_nm,
        electron_energies_eV=waves.electron_energies_eV,
        electron_densities=waves.electron_densities,
        hole_energies_eV=waves.hole_energies_eV,
        hole_densities=waves.hole_densities,
        localization=localization,
        max_al_fraction=cases17e.AL_FRACTION,
    )


def _post_solve_analysis(cfg, case, case_dir: Path, record: dict, calibration) -> dict:
    """Localization and optics for one completed solve; both or neither."""

    raw = Path(record["raw_output_dir"])
    try:
        localization, waves = demo17e.localization(
            cfg, raw, demo17e.build_case(cfg, case)[1]
        )
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "localization"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return record
    record["localization"] = localization
    record["_wavefunctions"] = waves
    record["wavefunction_csv_path"] = str(demo17e.write_wavefunction_csv(
        Path(case_dir) / "physics" / "wavefunctions.csv", waves
    ))
    if not localization["checks"]["passed"]:
        failed = [key for key, value in localization["checks"].items()
                  if key != "passed" and not value]
        record["passed"] = False
        record["failure_stage"] = "localization_checks"
        record["failure_reason"] = f"localization checks failed: {failed}"
        return record
    try:
        record["optical"] = demo17e.analyse_optics(
            cfg, case, case_dir, raw, calibration=calibration
        )
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "optical_analysis"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
    return record


def run_physics(verbose: bool = False, calibration_id: str | None = None,
                only: list[str] | None = None) -> int:
    cfg = demo17e.load_config()
    plan = cases17e.sampling_plan_from_config(cfg)
    cases = cases17e.load_cases(DEMO_DIR / cases17e.CASES_FILENAME, plan)
    if only:
        wanted = set(only)
        unknown = sorted(wanted - {case.case_id for case in cases})
        if unknown:
            print(f"Unknown case ids: {unknown}")
            return 2
        cases = [case for case in cases if case.case_id in wanted]
    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print(
            "Demo 17E physics was not run: this machine is not configured for "
            "licensed nextnano++ solves. Twenty-one full solves need the work "
            "laptop's licensed installation."
        )
        return 3
    gate_status, root, outcomes, cfg, plan, calibration = run_levels(
        do_parse=True, do_structure=True, mode="physics",
        selected_cases=cases, verbose=verbose, calibration_id=calibration_id,
    )

    records, rows = [], []
    for index, (case, outcome) in enumerate(zip(cases, outcomes), start=1):
        case_dir = root / "cases" / case.case_id
        if outcome.status != "structure_passed":
            record = {
                "case_id": case.case_id, "passed": False, "skipped": True,
                "failure_stage": "structure_gate",
                "failure_reason": outcome.failure_reason,
            }
        else:
            command = demo17e.full_physics_command(cfg, case, case_dir, machine=machine)
            print(f"  [FULL-SOLVE {index:>2}/{len(cases)}] {case.case_id} "
                  f"sigma={case.mean_interface_width_nm():.3f} nm ({case.severity})")
            if verbose:
                print(f"               command={subprocess.list2cmdline(command)}")
            record = demo17e.solve_case(cfg, case, case_dir, machine=machine)
            record["reported_full_physics_command"] = command
            if record.get("passed"):
                record = _post_solve_analysis(
                    cfg, case, case_dir, record, calibration
                )
                _write_wavefunction_plots(root, cfg, case, record)
            outcome.physics = {k: v for k, v in record.items()
                               if not k.startswith("_")}
            runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
            runlog14.write_json_atomic(
                case_dir / "physics" / "physics_result.json", outcome.physics
            )
        record.pop("_wavefunctions", None)
        records.append(record)
        if record.get("passed"):
            comparison = (outcome.structure or {}).get("comparison") or {}
            rows.append(demo17e.master_row(
                case, record, comparison,
                outcome.representation or case.expected_representation,
                calibration,
            ))
        analysis = record.get("analysis") or {}
        optical = record.get("optical") or {}
        scales = optical.get("scales") or {}
        return_code = (record.get("solver") or {}).get("solver_return_code")
        state = "PHYS-OK" if record.get("passed") else "PHYS-FAIL"
        print(
            f"  [{state:<9}] {case.case_id} rc={return_code} "
            f"E1={analysis.get('E_e1_eV')} E2={analysis.get('E_e2_eV')} "
            f"HH1={analysis.get('E_hh1_eV')} HH2={analysis.get('E_hh2_eV')}"
        )
        if record.get("passed"):
            verdict = (optical.get("bound_state_verdict") or {}).get("certified")
            raw = scales.get("chi2_1550_raw_pm_per_V")
            cal = scales.get("chi2_1550_calibrated_pm_per_V")
            peak = scales.get("peak_wavelength_nm")
            print(f"               chi2(1550) raw={_num(raw)} pm/V  "
                  f"calibrated={_num(cal)} pm/V  peak={_num(peak, '.1f')} nm  "
                  f"bound-states={BOUND_LABEL[verdict]}")
        else:
            print(f"               stage={record.get('failure_stage', 'unknown')}")
            print(f"               reason={record.get('failure_reason', 'not recorded')}")

    solved = sum(bool(record.get("passed")) for record in records)
    runlog14.write_json_atomic(root / "physics_summary.json", {
        "selected_cases": [case.case_id for case in cases],
        "sampling": plan.as_record(),
        "corrections": demo17.corrections_record(cfg),
        "calibration": demo17e.calibration_record(cfg, calibration),
        "cases": records, "passed": solved,
    })
    rows = demo17e.add_reference_comparison(rows)
    summary = demo17e.study_summary(cfg, rows, calibration, plan)
    _write_study_summary(root, cfg, plan, calibration, rows)
    _write_comparison_plots(root, cfg, rows, summary)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        "run_id": root.name, "demo_id": demo17e.DEMO_ID, "mode": "physics",
        "status": "completed", "cases_total": len(cases), "cases_passed": solved,
        "cases_failed": len(cases) - solved,
    })
    _print_physics_epilogue(root, summary, calibration, solved, len(cases))
    return 0 if gate_status == 0 and solved == len(cases) else 1


def _num(value, spec: str = ".3f") -> str:
    return "n/a" if value is None else format(float(value), spec)


def _print_physics_epilogue(root: Path, summary, calibration, solved: int,
                            total: int) -> None:
    roughness = summary.get("roughness") or {}
    reference = roughness.get("reference") or {}
    ensemble = roughness.get("ensemble") or {}
    print(RULE)
    print(f"  PHYSICS + OPTICAL RESULT: {solved}/{total} solved, gated and analysed")
    if reference.get("chi2_1550_raw_pm_per_V") is not None:
        print(f"  ABRUPT REFERENCE : "
              f"{_num(reference['chi2_1550_raw_pm_per_V'])} pm/V at 1550 nm, peak "
              f"{_num(reference.get('peak_chi2_raw_pm_per_V'))} pm/V at "
              f"{_num(reference.get('peak_wavelength_nm'), '.1f')} nm (raw)")
    block = ensemble.get("chi2_1550_raw_pm_per_V") or {}
    if block.get("count"):
        relative = block.get("relative_stdev")
        print(f"  {block['count']} REALIZATIONS  : chi2(1550) "
              f"{_num(block['min'])} - {_num(block['max'])} pm/V, mean "
              f"{_num(block['mean'])} +- {_num(block['stdev'])}"
              + ("" if relative is None else f" ({relative * 100.0:.1f} %)"))
    ratio = ensemble.get("chi2_1550_over_reference") or {}
    if ratio.get("count"):
        print(f"  VERSUS ABRUPT    : {_num(ratio['min'])}x - {_num(ratio['max'])}x, "
              f"median {_num(ratio['median'])}x")
    for label, key in (
        ("chi2 at 1550 nm", "chi2_at_1550"),
        ("spectral peak  ", "peak_chi2"),
        ("peak wavelength", "peak_wavelength"),
    ):
        trend = (roughness.get("trends") or {}).get(key) or {}
        if trend.get("computable"):
            r_squared = trend.get("r_squared")
            print(f"  TREND {label}: {trend['slope_per_nm']:+.2f} per nm of grading"
                  + ("" if r_squared is None else f"  (r^2 = {r_squared:.3f})"))
        else:
            print(f"  TREND {label}: not computable ({trend.get('reason', 'no data')})")
    bound = roughness.get("bound_states_certified") or {}
    print(f"  BOUND STATES     : {bound.get('true', 0)} certified, "
          f"{bound.get('false', 0)} failing, "
          f"{bound.get('not_certified', 0)} not certified")
    target = summary.get("paper_target") or {}
    if target.get("computed_raw_peak_pm_per_V") is not None:
        print(f"  PAPER TARGET ({target['case_id']}, abrupt peak): "
              f"raw {_num(target['computed_raw_peak_pm_per_V'], '.1f')} pm/V, "
              f"calibrated {_num(target.get('computed_calibrated_peak_pm_per_V'), '.1f')}"
              f" pm/V against {target['target_pm_per_V']:.0f} pm/V stated "
              f"(remaining factor on raw: "
              f"{_num(target.get('remaining_factor_on_raw_peak'), '.1f')}x)")
    print(f"  SCALES : raw 1.00x  |  calibrated {calibration.scale_id} "
          f"{calibration.multiplier:g}x ({calibration.status}, declared not derived)")
    print(f"  SUMMARY: {root / 'summaries' / STUDY_CSV}")
    print(f"  SPECTRA: {root / 'summaries' / SPECTRUM_CSV}")
    print(f"  PLOTS  : {root / 'plots'}")
    print(RULE)


# ---------------------------------------------------------------------------
# Reanalysis
# ---------------------------------------------------------------------------


def analyze_existing(path: Path, calibration_id: str | None = None) -> int:
    """Rebuild every table and figure from an existing run; never runs a solver.

    Also the way to re-report a completed study under a different calibration:
    the raw column is read back from the solved artifacts and multiplied, so
    ``--calibration combo_10 --analyze-existing`` costs no licensed time.
    """

    root = Path(path).resolve()
    physics_path = root / "physics_summary.json"
    if not physics_path.is_file():
        summary_path = root / "summary.json"
        if not summary_path.is_file():
            print(f"No Demo 17E summary at {root}")
            return 1
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"Demo 17E {payload['run_id']}: "
              f"{payload['cases_passed']}/{payload['cases_total']} validation "
              "cases passed")
        return 0
    cfg = demo17e.load_config()
    plan = cases17e.sampling_plan_from_config(cfg)
    calibration = demo17e.active_calibration(cfg, calibration_id)
    cases = {case.case_id: case for case in
             cases17e.load_cases(DEMO_DIR / cases17e.CASES_FILENAME, plan)}
    payload = json.loads(physics_path.read_text(encoding="utf-8"))
    rows, changed = [], False
    for record in payload.get("cases", []):
        case = cases.get(record.get("case_id"))
        if case is None or not record.get("passed"):
            continue
        case_dir = root / "cases" / case.case_id
        if not record.get("localization") or not record.get("optical"):
            record = _post_solve_analysis(cfg, case, case_dir, record, calibration)
            _write_wavefunction_plots(root, cfg, case, record)
            record.pop("_wavefunctions", None)
            changed = True
        else:
            # Re-scale a stored raw result without re-reading the solver tree.
            record["optical"]["scales"] = demo17e.scaled_optics(
                record["optical"], calibration
            )
        rows.append(demo17e.master_row(
            case, record, _stored_comparison(case_dir),
            _stored_representation(case_dir, case), calibration,
        ))
    if changed:
        runlog14.write_json_atomic(physics_path, payload)
    rows = demo17e.add_reference_comparison(rows)
    summary = demo17e.study_summary(cfg, rows, calibration, plan)
    _write_study_summary(root, cfg, plan, calibration, rows)
    _write_comparison_plots(root, cfg, rows, summary)
    print(f"Demo 17E existing run: {len(rows)}/{CASE_COUNT} physics cases "
          f"available, reported at calibration {calibration.scale_id} "
          f"({calibration.multiplier:g}x)")
    print(f"Summary: {root / 'summaries' / STUDY_CSV}")
    return 0 if len(rows) == CASE_COUNT else 1


def _stored_comparison(case_dir: Path) -> dict:
    path = Path(case_dir) / "comparison_metrics.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _stored_representation(case_dir: Path, case) -> str:
    path = Path(case_dir) / "case_result.json"
    if path.is_file():
        stored = json.loads(path.read_text(encoding="utf-8")).get("representation")
        if stored:
            return str(stored)
    return case.expected_representation


def show_scales(calibration_id: str | None = None) -> int:
    """Print the corrections and the reporting scales, then exit."""

    import yaml

    cfg = demo17e.load_config()
    calibration = demo17e.active_calibration(cfg, calibration_id)
    print(yaml.safe_dump({
        "corrections": demo17.corrections_record(cfg),
        "reporting_scales": demo17e.calibration_record(cfg, calibration),
        "sampling": cases17e.sampling_plan_from_config(cfg).as_record(),
    }, sort_keys=False, default_flow_style=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 17E: one fixed paper-geometry ACQW solved 21 times with the "
            "production nextnano++ binary -- the ideal abrupt reference plus 20 "
            "seed-locked random interface-grading realizations -- reported on a "
            "raw and a calibrated pm/V scale"
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true",
                       help="offline structural and syntax checks (the default)")
    group.add_argument("--physics", action="store_true",
                       help="the full licensed 21-case solve, analysis and plots")
    group.add_argument("--scales", action="store_true",
                       help="print the corrections and reporting scales and exit")
    group.add_argument("--syntax", action="store_true",
                       help="render and --parse every deck; no quantum solve")
    group.add_argument("--structure", action="store_true",
                       help="build every composition and gate it; no quantum solve")
    group.add_argument("--validate", action="store_true",
                       help="parse and structure-gate every deck; no quantum solve")
    group.add_argument("--write-cases", action="store_true",
                       help="freeze the 21 definitions into validation_cases.yaml")
    group.add_argument("--analyze-existing", metavar="RUN_DIR",
                       help="rebuild tables and figures from a completed run")
    parser.add_argument("--calibration", metavar="SCALE",
                        help="which declared multiplier the calibrated column "
                             "uses (raw, combo_09, combo_10); defaults to "
                             "prefactor.active in demo17e.yaml")
    parser.add_argument("--cases", metavar="ID[,ID...]",
                        help="solve only these case ids; the 21-case study is "
                             "several hours, and this is how one is re-run")
    parser.add_argument("--verbose", action="store_true",
                        help="solver commands, per-case failure detail and the "
                             "full check output")
    args = parser.parse_args(argv)
    only = [part.strip() for part in args.cases.split(",")] if args.cases else None

    if args.write_cases:
        path = cases17e.write_cases_file(DEMO_DIR / cases17e.CASES_FILENAME)
        cases = cases17e.load_cases(path)
        stats = cases17e.statistics_record(cases)
        width = stats["mean_interface_grading_width"]
        print(path)
        print(f"  {len(cases)} cases frozen (1 abrupt reference + "
              f"{len(cases) - 1} realizations)")
        print(f"  mean grading width {width['min_nm']:.4f} - {width['max_nm']:.4f} nm "
              f"(mean {width['mean_nm']:.4f}, sd {width['stdev_nm']:.4f})")
        print("  severity split: "
              + ", ".join(f"{k}={v}" for k, v in stats["severity_counts"].items()))
        return 0
    if args.scales:
        return show_scales(args.calibration)
    if args.syntax:
        return run_levels(do_parse=True, do_structure=False, mode="syntax",
                          verbose=args.verbose,
                          calibration_id=args.calibration)[0]
    if args.structure:
        return run_levels(do_parse=False, do_structure=True, mode="structure",
                          verbose=args.verbose,
                          calibration_id=args.calibration)[0]
    if args.validate:
        return run_levels(do_parse=True, do_structure=True, mode="validate",
                          verbose=args.verbose,
                          calibration_id=args.calibration)[0]
    if args.physics:
        return run_physics(verbose=args.verbose, calibration_id=args.calibration,
                           only=only)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing), args.calibration)
    return preflight17e.run_preflight(verbose=args.verbose,
                                      calibration=args.calibration)


if __name__ == "__main__":
    raise SystemExit(main())

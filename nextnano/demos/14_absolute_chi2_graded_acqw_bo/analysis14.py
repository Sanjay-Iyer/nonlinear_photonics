"""Demo 14 post-run analysis and plots.

Runs entirely from the artifacts a completed campaign left behind, so plots can
be regenerated without touching the solver. Plot failures are contained: a
cosmetic error must never invalidate a licensed campaign that already produced
its data, so each figure is attempted independently and its exception recorded.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

import runlog14

TARGET_NM = 1550.0
DETUNING_NM = 40.0

FAMILY_COLOURS = {
    "linear": "#4C72B0", "fermi": "#DD8452", "erf": "#55A868", "cosine": "#C44E52",
}


def load_run(run_root: Path) -> dict[str, Any]:
    run_root = Path(run_root)
    manifest_path = run_root / "manifest.json"
    ledger_path = run_root / "optimization" / "trial_ledger.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    records = []
    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return {"root": run_root, "manifest": manifest, "records": records}


def per_family_statistics(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Exploration and performance side by side.

    Reporting the counts next to the values is what separates "this family is
    better" from "this family was sampled more" -- the two look identical if you
    only plot the best value.
    """

    families = sorted({
        r.get("parameters", {}).get("grading_profile") for r in records
        if r.get("parameters", {}).get("grading_profile")
    })
    rows = []
    for family in families:
        subset = [r for r in records
                  if r.get("parameters", {}).get("grading_profile") == family]
        completed = [r for r in subset if r.get("status") in ("completed", "infeasible")]
        feasible = [r for r in completed if r.get("feasible")]
        values = [float(r["objective_pm_per_V"]) for r in completed
                  if r.get("objective_pm_per_V") is not None]
        feasible_values = [float(r["objective_pm_per_V"]) for r in feasible
                           if r.get("objective_pm_per_V") is not None]
        detunings = [abs(float(r["metrics"]["absolute_detuning_nm"])) for r in completed
                     if (r.get("metrics") or {}).get("absolute_detuning_nm") is not None]
        rows.append({
            "grading_profile": family,
            "number_initialized": sum(1 for r in subset
                                      if r.get("generation_phase") == "initialization"),
            "number_bo_selected": sum(1 for r in subset
                                      if r.get("generation_phase") == "bayesian_optimization"),
            "number_completed": len(completed),
            "number_feasible": len(feasible),
            "best_chi2_at_1550_pm_per_V": max(feasible_values) if feasible_values else None,
            "median_chi2_at_1550_pm_per_V": float(np.median(values)) if values else None,
            "median_absolute_detuning_nm": float(np.median(detunings)) if detunings else None,
        })
    return rows


def _safe_plot(name: str, failures: list[dict[str, str]], fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - a figure must not sink a campaign
        failures.append({
            "plot": name, "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        })


def generate_plots(run: Mapping[str, Any]) -> dict[str, Any]:
    """Every required figure, each attempted independently."""

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(run["root"])
    records = run["records"]
    plots_dir = root / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    written: list[str] = []
    mock = run["manifest"].get("scientific_valid") is False

    completed = [r for r in records if r.get("status") in ("completed", "infeasible")]

    def annotate_mock(ax) -> None:
        if mock:
            ax.text(0.5, 0.5, "MOCK — NOT SCIENTIFIC", transform=ax.transAxes,
                    ha="center", va="center", fontsize=26, color="red",
                    alpha=0.18, rotation=25, zorder=10)

    def convergence() -> None:
        fig, ax = plt.subplots(figsize=(9, 5))
        xs, ys, colours = [], [], []
        best, best_curve = -math.inf, []
        for i, r in enumerate(completed, start=1):
            value = r.get("objective_pm_per_V")
            xs.append(i)
            ys.append(float(value) if value is not None else np.nan)
            colours.append("#2E7D32" if r.get("feasible") else "#B0BEC5")
            if r.get("feasible") and value is not None:
                best = max(best, float(value))
            best_curve.append(best if best > -math.inf else np.nan)
        ax.scatter(xs, ys, c=colours, s=55, zorder=3, edgecolor="k", linewidth=0.4)
        ax.plot(xs, best_curve, color="#1A237E", lw=2, label="best feasible so far")
        n_init = int(run["manifest"].get("planned_initialization_trials", 0))
        if n_init and len(xs) > n_init:
            ax.axvline(n_init + 0.5, color="k", ls="--", lw=1)
            ax.text(n_init + 0.7, ax.get_ylim()[1] * 0.95, "BO begins", fontsize=9)
        ax.set_xlabel("completed solver trial")
        ax.set_ylabel(r"$|\chi^{(2)}_{xzx}|$ at 1550 nm  (pm/V)")
        ax.set_title("Demo 14 Bayesian optimization convergence")
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(alpha=0.25)
        annotate_mock(ax)
        fig.tight_layout()
        fig.savefig(plots_dir / "bo_convergence.png", dpi=150)
        plt.close(fig)
        written.append("bo_convergence.png")

    def design_space() -> None:
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
        pairs = [
            ("nominal_central_barrier_thickness_nm", "gaas_to_algaas_grading_width_10_90_nm",
             "barrier (nm)", "left 10-90 width (nm)"),
            ("asymmetry_s", "gaas_to_algaas_grading_width_10_90_nm",
             "asymmetry s", "left 10-90 width (nm)"),
            ("gaas_to_algaas_grading_width_10_90_nm", "algaas_to_gaas_grading_width_10_90_nm",
             "left 10-90 width (nm)", "right 10-90 width (nm)"),
        ]
        values = [float(r["objective_pm_per_V"]) for r in completed
                  if r.get("objective_pm_per_V") is not None]
        vmin, vmax = (min(values), max(values)) if values else (0.0, 1.0)
        for ax, (xk, yk, xl, yl) in zip(axes, pairs):
            xs = [r["parameters"][xk] for r in completed]
            ys = [r["parameters"][yk] for r in completed]
            cs = [r.get("objective_pm_per_V") or vmin for r in completed]
            markers = {"linear": "o", "fermi": "s", "erf": "^", "cosine": "D"}
            for family, marker in markers.items():
                idx = [i for i, r in enumerate(completed)
                       if r["parameters"].get("grading_profile") == family]
                if not idx:
                    continue
                sc = ax.scatter([xs[i] for i in idx], [ys[i] for i in idx],
                                c=[cs[i] for i in idx], marker=marker, s=70,
                                cmap="viridis", vmin=vmin, vmax=vmax,
                                edgecolor="k", linewidth=0.4, label=family)
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.grid(alpha=0.25)
        axes[0].legend(fontsize=8, title="profile")
        fig.colorbar(sc, ax=axes, label=r"$|\chi^{(2)}|$ at 1550 nm (pm/V)")
        annotate_mock(axes[1])
        fig.savefig(plots_dir / "grading_design_space.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append("grading_design_space.png")

    def per_family() -> None:
        stats = per_family_statistics(records)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
        families = [s["grading_profile"] for s in stats]
        best = [s["best_chi2_at_1550_pm_per_V"] or 0.0 for s in stats]
        axes[0].bar(families, best,
                    color=[FAMILY_COLOURS.get(f, "#888") for f in families])
        axes[0].set_ylabel(r"best feasible $|\chi^{(2)}|$ (pm/V)")
        axes[0].set_title("Performance by grading family")
        width = 0.38
        idx = np.arange(len(families))
        axes[1].bar(idx - width / 2, [s["number_completed"] for s in stats], width,
                    label="completed")
        axes[1].bar(idx + width / 2, [s["number_feasible"] for s in stats], width,
                    label="feasible")
        axes[1].set_xticks(idx)
        axes[1].set_xticklabels(families)
        axes[1].set_ylabel("trials")
        axes[1].set_title("Exploration by grading family")
        axes[1].legend(fontsize=9)
        for ax in axes:
            ax.grid(alpha=0.25, axis="y")
        annotate_mock(axes[0])
        fig.tight_layout()
        fig.savefig(plots_dir / "grading_family_performance.png", dpi=150)
        plt.close(fig)
        written.append("grading_family_performance.png")

    def realized_profiles() -> None:
        feasible = [r for r in completed if r.get("feasible")
                    and r.get("objective_pm_per_V") is not None]
        if not feasible:
            raise RuntimeError("no feasible trial to plot a profile for")
        best_per_family: dict[str, Any] = {}
        for r in feasible:
            fam = r["parameters"].get("grading_profile")
            if fam not in best_per_family or (
                float(r["objective_pm_per_V"])
                > float(best_per_family[fam]["objective_pm_per_V"])
            ):
                best_per_family[fam] = r
        fig, ax = plt.subplots(figsize=(9, 5))
        for fam, r in sorted(best_per_family.items()):
            csv = root / "trials" / r["trial_id"] / "grading_profile.csv"
            if not csv.is_file():
                continue
            rows = [line.split(",") for line in
                    csv.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
            xs = [float(c[0]) for c in rows]
            ys = [float(c[2]) for c in rows]
            ax.plot(xs, ys, label=f"{fam} ({r['trial_id']})",
                    color=FAMILY_COLOURS.get(fam), lw=2)
        ax.set_xlabel("growth coordinate x (nm)")
        ax.set_ylabel(r"$x_{\mathrm{Al}}$")
        ax.set_title("Realized Al composition profiles of the best design per family")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.25)
        annotate_mock(ax)
        fig.tight_layout()
        fig.savefig(plots_dir / "realized_composition_profiles.png", dpi=150)
        plt.close(fig)
        written.append("realized_composition_profiles.png")

    def paper_comparison() -> None:
        feasible = [r for r in completed if r.get("feasible")
                    and r.get("objective_pm_per_V") is not None]
        ours = max((float(r["objective_pm_per_V"]) for r in feasible), default=None)
        labels = ["bulk GaAs", "paper EDS (Al)", "paper EDS (Ga)",
                  "paper ideal abrupt", "paper best measured", "Demo 14 best"]
        values = [377.0, 1200.0, 1363.0, 2340.0, 2750.0, ours or 0.0]
        kinds = ["reference", "simulated", "simulated", "simulated", "measured", "ours"]
        colour = {"reference": "#9E9E9E", "simulated": "#4C72B0",
                  "measured": "#DD8452", "ours": "#2E7D32"}
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(labels, values, color=[colour[k] for k in kinds])
        ax.set_ylabel(r"$|\chi^{(2)}|$ at 1550 nm (pm/V)")
        ax.set_title("Demo 14 against published values (comparison types differ)")
        ax.tick_params(axis="x", rotation=20)
        ax.grid(alpha=0.25, axis="y")
        ax.text(0.01, 0.97,
                "measured values fold in optical-field effects and are NOT the\n"
                "same quantity as a material susceptibility",
                transform=ax.transAxes, va="top", fontsize=8, color="#555")
        annotate_mock(ax)
        fig.tight_layout()
        fig.savefig(plots_dir / "paper_comparison.png", dpi=150)
        plt.close(fig)
        written.append("paper_comparison.png")

    _safe_plot("bo_convergence", failures, convergence)
    _safe_plot("grading_design_space", failures, design_space)
    _safe_plot("grading_family_performance", failures, per_family)
    _safe_plot("realized_composition_profiles", failures, realized_profiles)
    _safe_plot("paper_comparison", failures, paper_comparison)

    inventory = {
        "written": written,
        "failed": failures,
        "scientific_valid": not mock,
        "generated_utc": runlog14.utc_now(),
    }
    runlog14.write_json_atomic(plots_dir / "plot_inventory.json", inventory)
    return inventory


def analyze_run(run_root: Path, *, plots_only: bool = False) -> int:
    run = load_run(run_root)
    root = Path(run["root"])
    if not run["records"]:
        print(f"No trial ledger found under {root}")
        return 1

    stats = per_family_statistics(run["records"])
    runlog14.write_json_atomic(
        root / "summaries" / "per_family_statistics.json", {"families": stats}
    )
    header = ("grading_profile,number_initialized,number_bo_selected,number_completed,"
              "number_feasible,best_chi2_at_1550_pm_per_V,median_chi2_at_1550_pm_per_V,"
              "median_absolute_detuning_nm\n")
    body = "".join(
        f"{s['grading_profile']},{s['number_initialized']},{s['number_bo_selected']},"
        f"{s['number_completed']},{s['number_feasible']},"
        f"{s['best_chi2_at_1550_pm_per_V'] or ''},"
        f"{s['median_chi2_at_1550_pm_per_V'] or ''},"
        f"{s['median_absolute_detuning_nm'] or ''}\n" for s in stats
    )
    runlog14.write_text_atomic(root / "summaries" / "per_family_statistics.csv", header + body)

    inventory = generate_plots(run)

    print(f"Run          : {run['manifest'].get('run_id')}")
    print(f"Status       : {run['manifest'].get('final_status')}")
    print(f"Scientific   : {run['manifest'].get('scientific_valid')}")
    print(f"Plots written: {len(inventory['written'])} -> {root / 'plots'}")
    if inventory["failed"]:
        print(f"Plot failures: {len(inventory['failed'])} (recorded, campaign data intact)")
        for failure in inventory["failed"]:
            print(f"  - {failure['plot']}: {failure['error']}")
    for row in stats:
        print(f"  {row['grading_profile']:<8} completed={row['number_completed']:<3} "
              f"feasible={row['number_feasible']:<3} "
              f"best={row['best_chi2_at_1550_pm_per_V']}")
    return 0

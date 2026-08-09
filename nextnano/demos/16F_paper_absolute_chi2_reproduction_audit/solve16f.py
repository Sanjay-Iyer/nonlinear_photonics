"""Licensed nextnano++ solves for the reproduction audit, run by 16F itself.

One structure -- the paper's ideal-abrupt 7.1 / 1.8 / 2.9 nm coupled pair -- at
three outer AlGaAs widths, so the domain-convergence question is answered by
this demo rather than delegated to three manual runs whose settings nobody can
later reconstruct.

Everything physical is Demo 16E's, unchanged: its renderer, its parser gate, its
realized-composition gate, its required-quantum-output gate, its solve, and
Demo 11's optical analysis through Demo 14's adapter. 16F adds only the domain
sweep, the strict bound-state verdict, and the convention ladder afterwards.

Nothing here fits anything. There is no scale factor, and the ladder is the same
one the solver-free audit already validated.

**On the bound-state policy.** The analysis runs under ``warn`` and 16F applies
the strict verdict itself, which is not a softening: ``fail_case`` makes Demo 11
raise at the point the diagnosis is written, *before* ``envelopes.csv`` exists,
which would deny the audit the wavefunctions it needs to explain the failure. The
verdict is identical; only the moment of the abort differs, and every artifact
survives to be inspected. ``--strict-abort`` restores the hard abort for anyone
who wants the run to stop instead.
"""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
import uuid

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
for _relative in (
    "_shared",
    "11_paper_validation_interband_chi2_acqw",
    "14_absolute_chi2_graded_acqw_bo",
    "16_acqw_renderer_stress_validation",
    "16B_simple_acqw_grading_validation",
    "16E_acqw_structure_physics_optical_comparison",
):
    _path = str(DEMOS / _relative)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import numpy as np

import cases16e  # noqa: E402
import demo14  # noqa: E402
import demo16e  # noqa: E402
import runlog14  # noqa: E402

import conventions16f as conv  # noqa: E402
import demo16f  # noqa: E402
import eq16f  # noqa: E402
import variants16f as variants  # noqa: E402


class Solve16FError(RuntimeError):
    """A licensed-solve precondition that is violated rather than merely unusual."""


# ---------------------------------------------------------------------------
# The case
# ---------------------------------------------------------------------------


#: The paper's asymmetry, derived from its own well widths rather than typed in,
#: so 7.1/2.9 and s = 0.42 cannot drift apart.
PAPER_ASYMMETRY = cases16e.PAPER_ASYMMETRY


def paper_case(index: int, outer_barrier_nm: float) -> cases16e.GeometryCase:
    """The ideal-abrupt paper structure, tagged with its outer-domain width.

    A ``cases16e.GeometryCase`` so Demo 16E's renderer, gates and solver accept
    it unchanged -- this is byte-for-byte the structure 16E calls ``case_02``.
    ``cases16e.validate_cases`` is deliberately not called: it enforces the
    ten-case Demo 16E list, which 16F is not.
    """

    return cases16e.GeometryCase(
        case_id=f"domain_{index:02d}",
        name=f"paper_abrupt_outer_{outer_barrier_nm:g}nm".replace(".", "p"),
        description=(
            "Paper ideal-abrupt ACQW: 7.10 nm GaAs / 1.80 nm Al0.55Ga0.45As / "
            f"2.90 nm GaAs, s = 0.42, abrupt interfaces, {outer_barrier_nm:g} nm "
            "outer AlGaAs each side. The structure whose chi2 the paper states "
            "as 2340 pm/V at 1550 nm."
        ),
        asymmetry_s=PAPER_ASYMMETRY,
        central_barrier_nm=conv.PAPER_TUNNEL_BARRIER_NM,
        left_grading_width_nm=0.0,
        right_grading_width_nm=0.0,
        interface_mode="abrupt",
    )


def config_for_domain(
    cfg: Mapping[str, Any], outer_barrier_nm: float, *, strict_abort: bool = False
) -> dict[str, Any]:
    """A deep copy of the production config with only the outer domain changed.

    ``geometry.domain_padding_nm`` is the flat AlGaAs Demo 14's renderer puts on
    each side of the active region, so it *is* the outer-barrier width this
    sweep varies. Deep-copied because the three domains must not share mutable
    sub-dictionaries -- a sweep that silently solved the same geometry three
    times would look beautifully converged.
    """

    updated = copy.deepcopy(dict(cfg))
    updated["geometry"] = dict(updated["geometry"])
    updated["geometry"]["domain_padding_nm"] = float(outer_barrier_nm)
    if strict_abort:
        validation = dict(updated.get("validation") or {})
        validation["quasi_bound_state_policy"] = "fail_case"
        updated["validation"] = validation
    return updated


def _machine():
    import demo_workflow as workflow

    machine = workflow.load_machine_config()
    if machine is None or not getattr(machine, "run_solver", False):
        raise Solve16FError(
            "this machine is not configured for licensed nextnano++ solves; "
            "set NEXTNANO_MACHINE_CONFIG to the licensed machine configuration"
        )
    return machine


def results_root() -> Path:
    machine = _machine()
    root = getattr(machine, "results_root", None)
    if not root:
        raise Solve16FError(
            "the machine configuration has no results_root; Demo 16F needs the "
            "short raw-output root that preserved the 16C/16D Windows path fix"
        )
    return Path(root)


def new_run_dir() -> tuple[Path, str]:
    facts = runlog14.git_facts(DEMOS.parents[1])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo16f_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / conv.DEMO_ID / run_id
    for sub in ("cases", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


# ---------------------------------------------------------------------------
# One domain
# ---------------------------------------------------------------------------


def _matrix_element_report(states: eq16f.StateSet) -> dict[str, Any]:
    """Every quantity Eq. 2 consumes, named the way Eq. 2 names it."""

    overlap = np.asarray(states.overlap_eh, dtype=float)
    z_e = np.asarray(states.z_e_nm, dtype=float)
    z_h = np.asarray(states.z_h_nm, dtype=float)
    energies = {
        "E1_eV": float(states.electron_energies_eV[0]),
        "E2_eV": float(states.electron_energies_eV[1]),
        "HH1_eV": float(states.hole_energies_eV[0]),
        "HH2_eV": float(states.hole_energies_eV[1]),
    }
    return {
        **energies,
        "E2_minus_E1_meV": (energies["E2_eV"] - energies["E1_eV"]) * 1000.0,
        "HH1_minus_HH2_meV": (energies["HH1_eV"] - energies["HH2_eV"]) * 1000.0,
        "transition_E1_HH1_eV": energies["E1_eV"] - energies["HH1_eV"],
        "transition_E2_HH2_eV": energies["E2_eV"] - energies["HH2_eV"],
        "overlap_e1_hh1": float(overlap[0, 0]),
        "overlap_e1_hh2": float(overlap[0, 1]),
        "overlap_e2_hh1": float(overlap[1, 0]),
        "overlap_e2_hh2": float(overlap[1, 1]),
        "z_e1_e1_nm": float(z_e[0, 0]),
        "z_e1_e2_nm": float(z_e[0, 1]),
        "z_e2_e2_nm": float(z_e[1, 1]),
        "z_hh1_hh1_nm": float(z_h[0, 0]),
        "z_hh1_hh2_nm": float(z_h[0, 1]),
        "z_hh2_hh2_nm": float(z_h[1, 1]),
        # The two combinations Eq. 2 is actually sensitive to: the intersubband
        # dipole, and the diagonal difference that survives the origin cancellation.
        "electron_diagonal_difference_nm": float(z_e[1, 1] - z_e[0, 0]),
        "hole_diagonal_difference_nm": float(z_h[1, 1] - z_h[0, 0]),
    }


def solve_domain(
    cfg: Mapping[str, Any],
    root: Path,
    index: int,
    outer_barrier_nm: float,
    *,
    machine: Any,
    exe: Any,
    database: Any,
    license_path: Any,
    strict_abort: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Gate, solve and analyse one outer-domain width. Never fits anything."""

    case = paper_case(index, outer_barrier_nm)
    domain_cfg = config_for_domain(cfg, outer_barrier_nm, strict_abort=strict_abort)
    case_dir = Path(root) / "cases" / case.case_id
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "outer_barrier_nm": float(outer_barrier_nm),
        "structure": demo16f.PAPER_STRUCTURE.as_record(),
        "is_paper_domain": abs(outer_barrier_nm - conv.PAPER_PERIOD_BARRIER_NM) < 1e-9,
        "passed": False,
    }

    outcome = demo16e.run_case(
        domain_cfg, case, case_dir, exe=exe, database=database,
        license_path=license_path, do_parse=True, do_structure=True,
    )
    record["structure_gate"] = {
        "status": outcome.status,
        "representation": outcome.representation,
        "render_method": outcome.render_method,
        "failure_reason": outcome.failure_reason,
    }
    if outcome.status != "structure_passed":
        record["failure_stage"] = "structure_gate"
        record["failure_reason"] = outcome.failure_reason
        return record

    solved = demo16e.solve_case(domain_cfg, case, case_dir, machine=machine)
    record["solver"] = {
        key: solved.get(key) for key in ("passed", "raw_output_dir")
    }
    if not solved.get("passed"):
        record["failure_stage"] = solved.get("failure_stage", "solve")
        record["failure_reason"] = solved.get("failure_reason")
        return record

    raw = Path(solved["raw_output_dir"])
    try:
        optical = demo16e.analyse_optics(domain_cfg, case, case_dir, raw)
    except Exception as exc:  # noqa: BLE001
        # Under --strict-abort this is where Demo 11's fail_case policy lands.
        # The per-state diagnosis has already been written, so it is still read
        # and reported: an abort must explain itself.
        parsed = case_dir / "physics" / "optical" / "parsed"
        record["failure_stage"] = "optical_analysis"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        record["bound_state_gate"] = demo16f.bound_state_gate(parsed)
        return record

    parsed = case_dir / "physics" / "optical" / "parsed"
    production = optical.get("production_metrics") or {}
    states, diagnostics = demo16f.state_set_from_run(
        parsed,
        electron_energies_eV=production["electron_energies_eV"],
        hole_energies_eV=production["heavy_hole_energies_eV"],
    )
    record.update({
        "passed": True,
        "raw_output_dir": str(raw),
        "parsed_dir": str(parsed),
        "matrix_elements": _matrix_element_report(states),
        "state_diagnostics": diagnostics,
        "matrix_element_cross_check": demo16f.cross_check_recorded(
            diagnostics, production
        ),
        "bound_state_gate": demo16f.bound_state_gate(parsed),
        "production_chi2_at_1550_pm_per_V": optical.get("chi2_at_1550"),
        "production_peak_wavelength_nm": optical.get("spectral_peak_wavelength_nm"),
        "production_physical_qc_valid": production.get("physical_qc_valid"),
        "variant_ladder": variants.evaluate_ladder(states),
        "_states": states,
    })
    return record


# ---------------------------------------------------------------------------
# The experiment
# ---------------------------------------------------------------------------


def run_solves(
    *, domains: Sequence[float] | None = None, strict_abort: bool = False,
    verbose: bool = False,
) -> tuple[Path, dict[str, Any]]:
    """The three licensed solves, the convergence verdict and the ladder.

    Returns the run directory and the full report. Writes everything as it goes,
    so a run that dies on the third domain still leaves the first two analysed.
    """

    machine = _machine()
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo14.load_config()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    widths = list(domains if domains is not None else demo16f.DOMAIN_SWEEP_NM)
    root, run_id = new_run_dir()

    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": conv.DEMO_ID,
        "demo16f_version": conv.DEMO_VERSION,
        "paper": conv.PAPER,
        "mode": "licensed_solve",
        "optimization_performed": False,
        "scale_factor_applied": None,
        "outer_barrier_widths_nm": widths,
        "quasi_bound_state_policy_requested": "fail_case",
        "quasi_bound_state_policy_mechanism": (
            "strict verdict applied by Demo 16F from Demo 11's per-state table; "
            "Demo 11 itself runs under warn so envelopes.csv is written before "
            "any abort. --strict-abort switches Demo 11 to fail_case."
            if not strict_abort else
            "Demo 11 runs under fail_case and aborts the case; the per-state "
            "table is still read and reported"
        ),
        "nextnano_executable": str(exe) if exe else None,
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
    }
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json", {**environment, "status": "running"}
    )

    records: list[dict[str, Any]] = []
    for index, width in enumerate(widths, start=1):
        record = solve_domain(
            cfg, root, index, width, machine=machine, exe=exe, database=database,
            license_path=licence, strict_abort=strict_abort, verbose=verbose,
        )
        records.append(record)
        persisted = {k: v for k, v in record.items() if not k.startswith("_")}
        runlog14.write_json_atomic(
            root / "cases" / record["case_id"] / "domain_result.json", persisted
        )

    report = build_report(environment, records)
    runlog14.write_json_atomic(root / "summaries" / "demo16f_report.json", report)
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "completed",
         "domains_total": len(widths),
         "domains_solved": sum(bool(r.get("passed")) for r in records)},
    )
    return root, report


def build_report(
    environment: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The single final report: converged, bound, best justified value, shortfall."""

    solved = [record for record in records if record.get("passed")]
    # Only domains that actually produced wavefunctions can be compared. A
    # domain that solved but whose states could not be rebuilt must not silently
    # drop out of the convergence verdict, so the count is reported alongside it.
    comparable = [record for record in solved if record.get("_states") is not None]
    convergence = (
        demo16f.domain_convergence([
            {"outer_barrier_nm": record["outer_barrier_nm"],
             "states": record["_states"]}
            for record in comparable
        ])
        if len(comparable) >= 2
        else {"converged": None,
              "reason": f"only {len(comparable)} domain(s) produced states; "
                        "two are needed"}
    )
    convergence["domains_solved"] = len(solved)
    convergence["domains_comparable"] = len(comparable)

    paper_domain = next(
        (record for record in comparable if record.get("is_paper_domain")), None
    )

    # The value the audit is willing to stand behind: the paper's own domain,
    # under the conventions every one of whose choices a cited source requires.
    best: float | None = None
    best_variant: str | None = None
    ladder_regression: dict[str, Any] | None = None
    if paper_domain is not None and paper_domain.get("variant_ladder"):
        rows = paper_domain["variant_ladder"]["rows"]
        ladder_regression = conv.check_ladder_regression(rows)
        promotable = [row for row in rows if row["promotable"]]
        if promotable:
            chosen = max(promotable, key=lambda row: row["chi2_at_1550_pm_per_V"])
            best = float(chosen["chi2_at_1550_pm_per_V"])
            best_variant = str(chosen["variant"])

    target = conv.PRIMARY_TARGET
    bound_verdicts = {
        record["case_id"]: (record.get("bound_state_gate") or {}).get("passed")
        for record in records
    }
    non_bound = {
        record["case_id"]: (record.get("bound_state_gate") or {}).get("failing_states")
        for record in records
        if (record.get("bound_state_gate") or {}).get("failing_states")
    }
    uncertified = [
        case_id for case_id, verdict in bound_verdicts.items() if verdict is not True
    ]

    return {
        **dict(environment),
        "domains": [
            {k: v for k, v in record.items() if not k.startswith("_")}
            for record in records
        ],
        "domain_convergence": convergence,
        "ladder_regression": ladder_regression,
        "bound_state_verdicts": bound_verdicts,
        "non_bound_states": non_bound,
        "domains_without_a_certified_bound_gate": uncertified,
        "best_physically_justified": {
            "variant": best_variant,
            "chi2_at_1550_pm_per_V": best,
            "outer_barrier_nm": (
                paper_domain["outer_barrier_nm"] if paper_domain else None
            ),
            "conventions": (
                "well_density N_z and the zincblende gamma_to_x_2pi_over_a zone "
                "edge; every choice required by a cited source"
            ),
            "certified_by_bound_gate": (
                None if paper_domain is None
                else (paper_domain.get("bound_state_gate") or {}).get("passed")
            ),
        },
        "target": {
            "name": target.name,
            "value_pm_per_V": target.value_pm_per_V,
            "source": target.source,
        },
        "remaining_factor_vs_target": (
            None if not best else target.value_pm_per_V / best
        ),
        "unresolved_published_ambiguities": [
            {
                "name": "eq1_eq2_prefactor",
                "size": 3.0,
                "applied": False,
                "detail": (
                    "Eq. 1 (1/(2 eps0 hbar^2), with a permutation sum) and Eq. 2 "
                    "(1/(6 eps0 hbar^2), without one) differ by exactly 3 for the "
                    "identity index assignment, and no integer permutation count "
                    "closes it. Reported, never applied."
                ),
            },
            {
                "name": "heavy_hole_mj_multiplicity",
                "size": 2.0,
                "applied": False,
                "detail": (
                    "the hh band is doubly degenerate at k = 0; the paper does "
                    "not state whether its Nz-normalised sum runs over both m_j "
                    "branches. Reported as the open ladder rung, never promoted."
                ),
            },
        ],
        "scale_factor_applied": None,
        "no_empirical_scaling_note": (
            "Demo 16F contains no absolute_scale_factor and fits nothing. Every "
            "convention on the promotable path is required by a cited source, "
            "and no convention was chosen because it improved agreement."
        ),
    }

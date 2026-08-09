"""One runner per group. Each case is independent; a failure never stops the run.

The three runners differ only in how the deck arrives:

* Group 1 stages the supplied ``.nnp`` file verbatim;
* Groups 2 and 3 render one with :mod:`deck16g`.

From the solver call onwards every group takes exactly the same path -- same
invocation helper, same output discovery, same Demo 11 parse, same Demo 16F chi2
evaluator, same strict bound gate -- which is the only way the comparison
measures structures rather than pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import cases16g
import deck16g
import demo16g
import grading16g
import nnp16g


#: Demo 11's analysis config is built through Demo 14's adapter, which derives
#: the localization region edges from ``domain_padding_nm``. Demo 16G places its
#: grades OUTSIDE the wells, so the thick well starts one full left ramp further
#: in than Demo 14 would assume. Passing an effective padding makes the adapter's
#: ``active_start`` land exactly on this demo's ``well1_start``:
#:
#:     active_start = padding                       (demo14.build_geometry)
#:     well1_start  = outer + left_full_ramp        (deck16g.layout_for)
#:
#: This is the single integration point between 16G's layout and Demo 11's
#: analysis, and it is the first thing to check if localization numbers look
#: shifted on the work laptop.
def effective_padding_nm(case: cases16g.StructureCase, cfg: Mapping[str, Any]) -> float:
    layout = deck16g.layout_for(case, cfg)
    return float(layout.well1_start - layout.domain_start)


def _demo14_geometry_and_profile(
    case: cases16g.StructureCase, cfg: Mapping[str, Any], log: demo16g.CaseLog
):
    """A Demo 14 geometry/profile pair describing this case, for analysis only.

    The deck Demo 16G actually solves is :func:`deck16g.render`'s. This pair
    exists so Demo 11's analysis knows where the layers are; it never becomes a
    deck. The grading width handed to the profile builder is converted into Demo
    14's 10-90 convention on the way in, because that is the only language its
    builder speaks -- see :mod:`grading16g` for why the two differ.
    """

    import demo14
    import grading14

    demo14_cfg = demo14.load_config()
    demo14_cfg["geometry"] = dict(demo14_cfg["geometry"])
    demo14_cfg["geometry"]["domain_padding_nm"] = effective_padding_nm(case, cfg)
    demo14_cfg["geometry"]["total_well_thickness_nm"] = case.total_well_nm

    ten_ninety_left = max(case.left_grade.ten_ninety_width_nm, 1.0e-3)
    ten_ninety_right = max(case.right_grade.ten_ninety_width_nm, 1.0e-3)
    parameters = {
        "asymmetry_s": case.asymmetry_s,
        "nominal_central_barrier_thickness_nm": case.tunnel_barrier_nm,
        "gaas_to_algaas_grading_width_10_90_nm": ten_ninety_left,
        "algaas_to_gaas_grading_width_10_90_nm": ten_ninety_right,
        "grading_profile": "linear",
    }
    log.field("analysis padding nm", demo14_cfg["geometry"]["domain_padding_nm"])
    log.field("analysis 10-90 L/R nm", f"{ten_ninety_left:.4f}/{ten_ninety_right:.4f}")
    geometry = demo14.build_geometry(demo14_cfg, parameters)
    profile = grading14.build_structure_profile(
        geometry=geometry,
        max_al_fraction=float(cfg["materials"]["al_fraction"]),
        mesh_nm=float(cfg["numerics"]["mesh_nm"]),
    ) if hasattr(grading14, "build_structure_profile") else None
    return demo14_cfg, geometry, profile


# ---------------------------------------------------------------------------
# Group 1
# ---------------------------------------------------------------------------


def run_nnp_case(
    case: cases16g.NnpCase, cfg: Mapping[str, Any], run_root: Path, machine: Any,
    *, verbose: bool = False,
) -> dict[str, Any]:
    workspace = demo16g.Workspace.create(run_root, case.group, case.case_id)
    log = demo16g.CaseLog(workspace.logs / "case.log", verbose=verbose)
    record: dict[str, Any] = {
        **case.as_record(),
        "workspace": workspace.as_record(),
        **demo16g.machine_record(machine),
        "passed": False,
    }
    log(f"case {case.case_id} ({case.group})", always=True)
    log.field("source path", case.source_path)
    try:
        inspection = nnp16g.inspect(case.source_path)
        staged = nnp16g.stage_copy(inspection, workspace.input)
        record["nnp_inspection"] = inspection.as_record()
        record["nnp_staging"] = staged
        record.update(nnp16g.structure_summary(inspection))
        log.field("sha256 source", inspection.sha256_source)
        log.field("staged input", staged["staged_path"])
        log.field("hole model", inspection.hole_model)
        log.field("computes chi2 itself", inspection.computes_chi2)
        for warning in inspection.warnings:
            log(f"WARNING {warning}", always=True)

        command = demo16g.solver_command(
            machine, Path(staged["staged_path"]), workspace.raw,
            threads=int(cfg["execution"]["threads"]),
        )
        record["solver"] = demo16g.run_solver(
            command, workspace, log,
            timeout_seconds=int(cfg["execution"]["solver_timeout_seconds"]),
        )
        record["outputs"] = demo16g.discover_outputs(workspace.raw, log)
        if not record["solver"]["succeeded"]:
            record.update({"failure_stage": "solve",
                           "failure_reason": "solver did not return 0"})
            return record

        # The supplied files solve states only, so their envelopes go into the
        # same evaluator every other group uses. No second chi2 formula exists.
        analysis = demo16g.analyse_states(
            cfg, workspace, log,
            geometry=record.get("_analysis_geometry"),
        )
        record["analysis"] = analysis
        record.update(demo16g.optical_from_parsed(
            cfg, workspace, analysis["observables"], log
        ))
        record["physical_qc_valid"] = analysis["physical_qc_valid"]
        record["passed"] = True
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
        stage = record.get("failure_stage", "nnp_case")
        record.update(demo16g.failure_record(exc, stage))
        log(f"FAILED at {stage}: {type(exc).__name__}: {exc}", always=True)
        log(record["traceback"])
    finally:
        log.flush()
        demo16g.write_case_provenance(workspace, cfg, record)
    return record


# ---------------------------------------------------------------------------
# Groups 2 and 3
# ---------------------------------------------------------------------------


def run_structure_case(
    case: cases16g.StructureCase, cfg: Mapping[str, Any], run_root: Path,
    machine: Any, *, verbose: bool = False,
) -> dict[str, Any]:
    workspace = demo16g.Workspace.create(run_root, case.group, case.case_id)
    log = demo16g.CaseLog(workspace.logs / "case.log", verbose=verbose)
    record: dict[str, Any] = {
        **case.as_record(),
        "workspace": workspace.as_record(),
        **demo16g.machine_record(machine),
        "passed": False,
    }
    log(f"case {case.case_id} ({case.group})", always=True)
    log.field("thick/barrier/thin nm",
              f"{case.thick_well_nm:.3f} / {case.tunnel_barrier_nm:.3f} / "
              f"{case.thin_well_nm:.3f}")
    log.field("grades L/R nm (requested)",
              f"{case.left_grade_nm:.3f} / {case.right_grade_nm:.3f}")
    log.field("grading definition", case.grading_definition)
    log.field("full ramp L/R nm",
              f"{case.left_grade.full_linear_ramp_width_nm:.4f} / "
              f"{case.right_grade.full_linear_ramp_width_nm:.4f}")
    log.field("10-90 L/R nm",
              f"{case.left_grade.ten_ninety_width_nm:.4f} / "
              f"{case.right_grade.ten_ninety_width_nm:.4f}")
    log.field("asymmetry s", f"{case.asymmetry_s:.4f}")
    try:
        deck_text, deck_provenance = deck16g.render(case, cfg)
        deck_path = workspace.input / f"{case.case_id}.in"
        deck_path.write_text(deck_text, encoding="utf-8")
        record["deck"] = deck_provenance
        record["representation"] = deck_provenance["representation"]
        record["generated_input_path"] = str(deck_path)
        record["sha256_generated_input"] = nnp16g.sha256(deck_path)
        log.field("generated input", deck_path)
        log.field("representation", deck_provenance["representation"])
        log.field("mesh nm", deck_provenance["mesh_nm"])
        log.field("quantum model", deck_provenance["quantum_model"])
        for name, span in deck_provenance["full_ramp_coordinates_nm"].items():
            log.field(f"ramp {name}", f"[{span[0]:.4f}, {span[1]:.4f}] nm")

        command = demo16g.solver_command(
            machine, deck_path, workspace.raw,
            threads=int(cfg["execution"]["threads"]),
        )
        record["solver"] = demo16g.run_solver(
            command, workspace, log,
            timeout_seconds=int(cfg["execution"]["solver_timeout_seconds"]),
        )
        record["outputs"] = demo16g.discover_outputs(workspace.raw, log)
        if not record["solver"]["succeeded"]:
            record.update({"failure_stage": "solve",
                           "failure_reason": "solver did not return 0"})
            return record

        demo14_cfg, geometry, profile = _demo14_geometry_and_profile(case, cfg, log)
        analysis = demo16g.analyse_states(
            cfg, workspace, log,
            geometry={"geometry": geometry, "profile": profile},
        )
        record["analysis"] = analysis
        record.update(demo16g.optical_from_parsed(
            cfg, workspace, analysis["observables"], log
        ))
        record["physical_qc_valid"] = analysis["physical_qc_valid"]
        record["passed"] = True
    except deck16g.Deck16GError as exc:
        record.update(demo16g.failure_record(exc, "render"))
        log(f"REFUSED to render: {exc}", always=True)
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
        stage = record.get("failure_stage", "structure_case")
        record.update(demo16g.failure_record(exc, stage))
        log(f"FAILED at {stage}: {type(exc).__name__}: {exc}", always=True)
        log(record["traceback"])
    finally:
        log.flush()
        demo16g.write_case_provenance(workspace, cfg, record)
    return record


def run_group(
    group: str, cases: Sequence[Any], cfg: Mapping[str, Any], run_root: Path,
    machine: Any, *, verbose: bool = False,
) -> list[dict[str, Any]]:
    """Every case in one group. Continues past a failure by design."""

    runner = run_nnp_case if group == cases16g.GROUP_NNP else run_structure_case
    records = []
    for case in cases:
        record = runner(case, cfg, run_root, machine, verbose=verbose)
        records.append(record)
        status = "OK" if record.get("passed") else "FAIL"
        print(f"  [{status:<4}] {record['group']}/{record['case_id']}"
              + ("" if record.get("passed")
                 else f"  ({record.get('failure_stage')}: "
                      f"{record.get('failure_reason')})"))
        if not record.get("passed") and not cfg["execution"]["continue_on_case_failure"]:
            print("  execution.continue_on_case_failure is false; stopping.")
            break
    return records

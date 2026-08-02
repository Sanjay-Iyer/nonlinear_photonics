"""Stage 5 settings, the two-case entry gate, and directory isolation.

One authoritative source
========================

Stage 5 settings previously existed in three places that could disagree: the
``validation_study`` block of ``demo.yaml``, the case builders in
:mod:`demo13`, and the prose of ``V3_STAGE5_EXECUTION_PLAN.md``.  Everything
Stage 5 needs is resolved here instead, so a guide that quotes a mesh value and
a run that uses one are reading the same object.

The gate
========

Stage 5's full campaign is roughly forty licensed solver cases: nominal, local
refinement, mesh, state-count and padding checks for each of the top designs,
plus fabrication perturbations.  Spending that before knowing whether the
*first* question even resolves is the expensive mistake.

So the first paid Stage 5 action is a **gate**: exactly two new mesh cases for
one anchor design, at meshes the campaign has never run.  The v3 campaign was
computed at 0.05 nm; the gate adds 0.025 nm and 0.10 nm and asks whether the
state assignment, the confidence, the hole gap and the chi(2) survive a factor
of two in either direction.  Nothing else is generated until that passes.

Isolation
=========

Stage 5 writes.  The optimization experiment holds the immutable ledger of a
licensed campaign.  :func:`assert_isolated` refuses any Stage 5 destination that
*is*, contains, or is contained by a directory holding a BO checkpoint or
ledger -- after resolving symlinks, so an alias cannot get around it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

import design13  # noqa: E402

#: Files whose presence marks a directory as a protected optimization
#: experiment. Content-based, so a campaign directory is refused whatever it is
#: called -- which is the rule that survives someone renaming one.
PROTECTED_ARTIFACTS: tuple[str, ...] = (
    "ax_experiment_snapshot.json",
    "trial_ledger.jsonl",
    "experiment_schema.json",
)

#: Directory names always refused regardless of content, so the protection
#: holds before a campaign directory exists as well as after.
PROTECTED_EXPERIMENT_NAMES: frozenset[str] = frozenset(
    {
        "demo13_ax_experiment",
        "demo13_ax_experiment_v2",
        "demo13_ax_experiment_v3",
    }
)

_PROTECTED_NAMES_FOLDED: frozenset[str] = frozenset(
    name.casefold() for name in PROTECTED_EXPERIMENT_NAMES
)

#: What the gate compares between the reference mesh and each new mesh. Named
#: here so the guides, the report and the acceptance test quote one list.
GATE_COMPARISON_FIELDS: tuple[str, ...] = (
    "tracked_state_labels",
    "state_tracking_confidence",
    "state_tracking_ambiguous",
    "heavy_hole_anticrossing_gap_meV",
    "relative_chi2_at_target_wavelength_abs",
    "peak_wavelength_nm",
    "signed_detuning_nm",
    "absolute_detuning_nm",
    "maximum_boundary_probability",
    "physical_qc_valid",
    "feasible_under_ax_constraints",
)


#: Relative change a compared field may show between the reference mesh and a
#: new one before the gate fails. Without these the gate computed
#: ``relative_change`` and threw it away: a 60 % shift in chi(2) passed.
#: Generous, because the gate asks "did the answer survive?", not "is it
#: converged to three digits" -- that is what the full campaign is for.
DEFAULT_GATE_TOLERANCES: Mapping[str, float] = {
    "relative_chi2_at_target_wavelength_abs": 0.10,
    "peak_wavelength_nm": 0.01,
    "heavy_hole_anticrossing_gap_meV": 0.25,
    "absolute_detuning_nm": 0.50,
    "maximum_boundary_probability": 10.0,
}


class Stage5Error(DemoError):
    """A Stage 5 configuration or destination that must not be used."""


@dataclass(frozen=True)
class GateSettings:
    """The two-case entry gate, resolved from one place."""

    enabled: bool
    anchor_case: str
    design: str
    reference_mesh_nm: float
    mesh_convergence_nm: tuple[float, ...]
    required_before_full_campaign: bool

    @property
    def case_count(self) -> int:
        return len(self.mesh_convergence_nm)

    def as_record(self) -> dict[str, Any]:
        return {
            "gate_enabled": self.enabled,
            "gate_anchor_case": self.anchor_case,
            "gate_design": self.design,
            "gate_reference_mesh_nm": self.reference_mesh_nm,
            "gate_mesh_convergence_nm": list(self.mesh_convergence_nm),
            "gate_case_count": self.case_count,
            "gate_required_before_full_campaign": self.required_before_full_campaign,
            "gate_comparison_fields": list(GATE_COMPARISON_FIELDS),
        }


@dataclass(frozen=True)
class Stage5Settings:
    """Every Stage 5 setting, resolved once.

    Anything that reads a Stage 5 number -- the case builders, the report, the
    guides generator, the handoff -- takes it from here, so there is exactly one
    definition of "the gate meshes" or "the anchor design".
    """

    enabled: bool
    output_state_dir: str | None
    top_designs: int
    local_refinement: Mapping[str, Sequence[float]]
    mesh_convergence_nm: tuple[float, ...]
    state_count_convergence: tuple[int, ...]
    domain_padding_nm: tuple[float, ...]
    fabrication_perturbations: Mapping[str, Sequence[float]]
    gate: GateSettings
    reserved_unsupported: tuple[str, ...] = field(default=())

    def as_record(self) -> dict[str, Any]:
        return {
            "stage5_enabled": self.enabled,
            "stage5_output_state_dir": self.output_state_dir,
            "stage5_top_designs": self.top_designs,
            "stage5_mesh_convergence_nm": list(self.mesh_convergence_nm),
            "stage5_state_count_convergence": list(self.state_count_convergence),
            "stage5_domain_padding_nm": list(self.domain_padding_nm),
            "stage5_reserved_unsupported": list(self.reserved_unsupported),
            **self.gate.as_record(),
        }


#: ``validation_study`` keys that are accepted but do nothing. Kept named rather
#: than silently ignored: a setting that looks live and is not is how a slice
#: quietly reverted to its default in v2.
RESERVED_UNSUPPORTED_KEYS: tuple[str, ...] = (
    "stopping_criteria",
    "max_parallel_cases",
)


def settings(cfg: Mapping[str, Any]) -> Stage5Settings:
    """Resolve ``validation_study`` into the one object Stage 5 reads."""

    study = dict(cfg.get("validation_study") or {})
    gate_cfg = dict(study.get("gate") or {})

    reference_mesh = float(
        gate_cfg.get(
            "reference_mesh_nm",
            (cfg.get("numerical") or {}).get("active_region_grid_spacing_nm", 0.05),
        )
    )
    gate_meshes = tuple(
        float(value) for value in (gate_cfg.get("mesh_convergence_nm") or ())
    )
    gate = GateSettings(
        enabled=bool(gate_cfg.get("enabled", False)),
        anchor_case=str(gate_cfg.get("anchor_case", "")),
        design=str(gate_cfg.get("design", "")),
        reference_mesh_nm=reference_mesh,
        mesh_convergence_nm=gate_meshes,
        required_before_full_campaign=bool(
            gate_cfg.get("require_gate_before_full_campaign", True)
        ),
    )
    resolved = Stage5Settings(
        enabled=bool(study.get("enabled", False)),
        output_state_dir=(
            str(study["output_state_dir"]) if study.get("output_state_dir") else None
        ),
        top_designs=int(study.get("top_designs", 3)),
        local_refinement=dict(study.get("local_refinement") or {}),
        mesh_convergence_nm=tuple(
            float(value) for value in (study.get("mesh_convergence_nm") or ())
        ),
        state_count_convergence=tuple(
            int(value) for value in (study.get("state_count_convergence") or ())
        ),
        domain_padding_nm=tuple(
            float(value) for value in (study.get("domain_padding_nm") or ())
        ),
        fabrication_perturbations=dict(study.get("fabrication_perturbations") or {}),
        gate=gate,
        reserved_unsupported=tuple(
            key for key in RESERVED_UNSUPPORTED_KEYS if key in study
        ),
    )
    _validate(resolved, cfg)
    return resolved


def _validate(resolved: Stage5Settings, cfg: Mapping[str, Any]) -> None:
    if not resolved.enabled:
        return
    gate = resolved.gate
    if not gate.enabled:
        return
    if gate.case_count != 2:
        raise Stage5Error(
            "validation_study.gate.mesh_convergence_nm must name exactly two new "
            f"meshes; got {list(gate.mesh_convergence_nm)}. The first paid Stage 5 "
            "action is a two-case gate by design."
        )
    if any(
        math.isclose(gate.reference_mesh_nm, value, rel_tol=1e-9, abs_tol=1e-12)
        for value in gate.mesh_convergence_nm
    ):
        raise Stage5Error(
            f"validation_study.gate.mesh_convergence_nm repeats the reference mesh "
            f"({gate.reference_mesh_nm} nm), which the campaign has already computed. "
            "The gate must spend licensed time only on meshes that are new."
        )
    # The reference mesh must be the mesh the campaign actually ran, or the
    # comparison is against a number that was never computed.
    campaign_mesh = float(
        (cfg.get("numerical") or {}).get("active_region_grid_spacing_nm", 0.0)
    )
    if campaign_mesh and not math.isclose(
        gate.reference_mesh_nm, campaign_mesh, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise Stage5Error(
            f"validation_study.gate.reference_mesh_nm ({gate.reference_mesh_nm} nm) "
            f"is not numerical.active_region_grid_spacing_nm ({campaign_mesh} nm). "
            "The gate compares each new mesh against the campaign's own result, so "
            "the reference must be the mesh the campaign ran."
        )
    if not gate.design:
        raise Stage5Error("validation_study.gate.design must name the anchor design")
    if not gate.anchor_case:
        raise Stage5Error(
            "validation_study.gate.anchor_case must name the design every gate case "
            "is assigned against"
        )
    if gate.anchor_case != gate.design:
        # The gate loads the anchor's wavefunctions from the *design's* completed
        # trial directory, because that is the trial it is recomputing. Letting
        # the two names differ would label one trial's states with another
        # trial's identity and report the mismatch as a confident assignment --
        # the exact class of error fixed-anchor tracking exists to prevent.
        raise Stage5Error(
            f"validation_study.gate.anchor_case ({gate.anchor_case!r}) must equal "
            f"validation_study.gate.design ({gate.design!r}). The gate asks whether "
            "a design's own state identities survive a mesh change, so it anchors "
            "on that design and reads its completed output. Anchoring on a "
            "different trial needs a separate lookup that is deliberately not "
            "implemented."
        )


# ---------------------------------------------------------------------------
# directory isolation
# ---------------------------------------------------------------------------


def gate_tolerances(cfg: Mapping[str, Any]) -> dict[str, float]:
    """Per-field relative tolerances the gate verdict enforces."""

    configured = ((cfg.get("validation_study") or {}).get("gate") or {}).get(
        "tolerances"
    ) or {}
    merged = dict(DEFAULT_GATE_TOLERANCES)
    merged.update({str(k): float(v) for k, v in configured.items()})
    return merged


def is_protected_experiment_dir(path: Path) -> bool:
    """Whether this directory is a protected optimization experiment.

    True on name **or** content: the name check protects a campaign directory
    that does not exist yet, the content check protects one that was renamed.
    """

    path = Path(path)
    # Case-insensitive: on Windows `DEMO13_AX_EXPERIMENT_V3` and
    # `demo13_ax_experiment_v3` are the same directory, so a case-sensitive
    # comparison would let a differently-cased alias through the name check.
    # The content check below would still catch it once the campaign directory
    # exists, but protection must not depend on that.
    if path.name.casefold() in _PROTECTED_NAMES_FOLDED:
        return True
    return any((path / name).is_file() for name in PROTECTED_ARTIFACTS)


def _resolved(path: Path) -> Path:
    """Absolute, symlink-free path.

    ``strict=False`` so a destination that does not exist yet still resolves --
    the check has to work *before* Stage 5 creates its directory, which is
    exactly when it matters.
    """

    return Path(path).expanduser().resolve()


def assert_isolated(
    state_dir: Path,
    cfg: Mapping[str, Any],
    results_root: Path | None = None,
    *,
    experiment_dir: Path | None = None,
) -> Path:
    """Refuse any Stage 5 destination that could reach a licensed campaign.

    Four ways a destination can fail, all checked on the resolved path so a
    symlink or a ``..`` alias cannot slip past:

    * it *is* the configured optimization experiment;
    * it *is* a protected experiment, by name or because it holds a checkpoint
      or ledger;
    * it *contains* a protected experiment, so writing under it could reach one;
    * it is *inside* a protected experiment.
    """

    target = _resolved(state_dir)
    workflow = cfg.get("workflow") or {}
    experiment_name = str(workflow.get("experiment_state_dir", "") or "")

    # Prefer the caller's already-resolved experiment directory. Re-deriving it
    # from the results root is what made this comparison vacuous: the caller
    # built `<root>/<demo_id>/<name>` and this built `<root>/<name>`, so the two
    # were never equal whatever the configuration said.
    if experiment_dir is None and results_root is not None and experiment_name:
        experiment_dir = Path(results_root) / str(cfg.get("demo_id", "")) / experiment_name
    if experiment_dir is not None:
        experiment = _resolved(experiment_dir)
        if target == experiment:
            raise Stage5Error(
                f"Stage 5 destination {target} is the optimization experiment "
                f"directory ({experiment_name!r}). Stage 5 writes; that directory "
                "holds the immutable ledger of a licensed campaign. Set "
                "validation_study.output_state_dir to a separate directory such as "
                "demo13_stage5_v3_validation."
            )

    if is_protected_experiment_dir(target):
        raise Stage5Error(
            f"Stage 5 destination {target} is a protected optimization experiment "
            "(it is a known campaign directory or holds a BO checkpoint or ledger). "
            "Refusing to let Stage 5 write into it."
        )

    for parent in target.parents:
        if is_protected_experiment_dir(parent):
            raise Stage5Error(
                f"Stage 5 destination {target} lies inside the protected experiment "
                f"{parent}. Stage 5 must not write anywhere under a licensed campaign."
            )

    if target.is_dir():
        # Bounded descendant scan, not one level. A destination two levels above
        # a campaign -- `results/demo_runs`, with the campaign at
        # `results/demo_runs/13_.../demo13_ax_experiment_v3` -- was accepted,
        # while the docstring promised "any destination containing one".
        found = _protected_descendant(target, max_depth=CONTAINMENT_SCAN_DEPTH)
        if found is not None:
            raise Stage5Error(
                f"Stage 5 destination {target} contains the protected experiment "
                f"{found}. Choose a destination that holds no campaign data."
            )
    return target


#: How far below a destination to look for a campaign. Three levels covers
#: `<results root>/<demo id>/<experiment>`, which is the deepest a campaign sits
#: under any directory a person would plausibly point Stage 5 at.
CONTAINMENT_SCAN_DEPTH = 3


def _protected_descendant(root: Path, *, max_depth: int) -> Path | None:
    """First protected experiment at or below ``root``, within ``max_depth``."""

    frontier = [(root, 0)]
    while frontier:
        directory, depth = frontier.pop()
        if depth >= max_depth:
            continue
        try:
            children = sorted(
                child for child in directory.iterdir() if child.is_dir()
            )
        except (OSError, PermissionError):
            continue
        for child in children:
            if is_protected_experiment_dir(child):
                return child
            frontier.append((child, depth + 1))
    return None


def assert_resume_schema_matches(state_dir: Path, cfg: Mapping[str, Any]) -> None:
    """An existing Stage 5 directory may be resumed only under its own schema.

    Resuming a Stage 5 directory written under different physics -- a different
    active mesh, a different grading parameterization -- would mix two
    calculations of different functions into one convergence claim.
    """

    import json

    path = Path(state_dir) / "stage5_schema.json"
    if not path.is_file():
        return
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Stage5Error(f"unreadable Stage 5 schema at {path}: {exc}") from exc
    current = stage5_schema(cfg)
    differences = sorted(
        key for key in set(stored) | set(current) if stored.get(key) != current.get(key)
    )
    if differences:
        raise Stage5Error(
            f"the Stage 5 directory {state_dir} was written under a different "
            f"configuration ({', '.join(differences)} differ). Resuming would mix "
            "two different calculations into one convergence claim. Use a new "
            "directory."
        )


def stage5_schema(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The Stage 5 identity a resumed directory has to agree with."""

    resolved = settings(cfg)
    numerical = cfg.get("numerical") or {}
    return {
        "gate_anchor_case": resolved.gate.anchor_case,
        "gate_design": resolved.gate.design,
        "gate_mesh_convergence_nm": list(resolved.gate.mesh_convergence_nm),
        "gate_reference_mesh_nm": resolved.gate.reference_mesh_nm,
        "reference_active_mesh_nm": float(
            numerical.get("active_region_grid_spacing_nm", 0.05)
        ),
        "parameterization": str(
            ((cfg.get("bo") or {}).get("search_space") or {}).get(
                "parameterization", "thickness"
            )
        ),
        "number_of_electron_states": int(numerical.get("number_of_electron_states", 0)),
        "number_of_hole_states": int(numerical.get("number_of_hole_states", 0)),
    }


# ---------------------------------------------------------------------------
# the gate's cases
# ---------------------------------------------------------------------------


def gate_design_record(
    cfg: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    """The completed trial the gate anchors on, found by candidate id.

    Looked up by the id the gate names rather than by rank, because "the best
    design" changes when the ranking changes and the gate must be reproducible.
    """

    resolved = settings(cfg)
    wanted = resolved.gate.design
    for record in records:
        if str(record.get("candidate_id")) == wanted and str(
            record.get("status")
        ) == "completed":
            return record
    raise Stage5Error(
        f"validation_study.gate.design names {wanted!r}, which is not a completed "
        "trial in this experiment's ledger. The gate cannot run against a design "
        "that was never evaluated."
    )


def gate_cases(
    cfg: Mapping[str, Any], design: Mapping[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    """Exactly the new-mesh cases the gate spends licensed time on.

    Deliberately *only* mesh cases. No local refinement, no state-count sweep,
    no padding sweep, no perturbations: those are the full campaign, and the
    campaign is what the gate exists to decide about.
    """

    resolved = settings(cfg)
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    if not base_parameters:
        raise Stage5Error(
            "the gate design record carries no parameter_* fields; it is not a "
            "Demo 13 trial record."
        )
    cases: list[tuple[str, str, dict[str, Any]]] = []
    for spacing in resolved.gate.mesh_convergence_nm:
        config = design13.resolve_config(base_parameters, cfg)
        _set(config, "numerical.active_region_grid_spacing_nm", float(spacing))
        cases.append((f"gate_mesh_{float(spacing):g}nm", "gate_mesh_convergence", config))
    return cases


def _set(config: dict[str, Any], dotted: str, value: Any) -> None:
    cursor: Any = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def gate_is_satisfied(state_dir: Path) -> bool:
    """Whether a completed, passing gate result already exists on disk."""

    import json

    path = Path(state_dir) / "stage5_gate_result.json"
    if not path.is_file():
        return False
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    # Exactly `true`, not merely truthy. `bool(...)` would unblock roughly
    # seventy licensed cases on any non-empty value -- a hand-edited "yes", a
    # timestamp, the string "false". The gate writes a real boolean; anything
    # else is a malformed result and must not spend solver time.
    return record.get("gate_passed") is True


def full_campaign_allowed(cfg: Mapping[str, Any], state_dir: Path) -> tuple[bool, str]:
    """Whether the full Stage 5 campaign may generate cases yet, and why not."""

    resolved = settings(cfg)
    if not resolved.gate.enabled:
        return True, "no gate is configured"
    if not resolved.gate.required_before_full_campaign:
        return True, "validation_study.gate.require_gate_before_full_campaign is false"
    if gate_is_satisfied(state_dir):
        return True, "the two-case mesh gate has passed"
    return False, (
        "the two-case mesh gate has not passed. The full Stage 5 campaign is "
        f"roughly {_full_campaign_case_estimate(resolved)} licensed cases and is "
        "not generated until the gate result exists and records gate_passed: true."
    )


def _full_campaign_case_estimate(resolved: Stage5Settings) -> int:
    per_design = (
        1
        + sum(len(tuple(values)) for values in resolved.local_refinement.values())
        + len(resolved.mesh_convergence_nm)
        + len(resolved.state_count_convergence)
        + len(resolved.domain_padding_nm)
        + sum(
            len(tuple(values)) for values in resolved.fabrication_perturbations.values()
        )
    )
    return per_design * max(resolved.top_designs, 1)

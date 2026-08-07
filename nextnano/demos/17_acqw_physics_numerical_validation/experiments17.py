"""Demo 17's twelve controlled experiments.

Every experiment answers the same five questions and records the answers beside
its numbers: what changed, what was held constant, what should have stayed the
same, what should have moved, and whether nextnano++ agreed.

They split into two classes, and the split is a property of the machine rather
than of the science:

* **Structural** experiments need no solver. They compare the authoritative
  ``x_Al(z)`` against itself under controlled changes, and against the geometry
  the mesh can represent. These run anywhere.
* **Physics** experiments need the licensed build. They compare band edges,
  eigenvalues, wavefunctions and transition energies. Attempting one without a
  licence produces a ``not_run`` result and no numbers -- never a fabricated
  pass.

The one rule that keeps the two honest: an experiment reports ``passed`` only
when it actually made the measurement. "Nothing failed" is not a pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

import chi2 as chi2mod
import demo14
import grading14
import measure17
import refs17
import runlog14
import solve17

TOL = measure17.TOLERANCES


class Experiment17Error(RuntimeError):
    """The experiment could not be set up, as distinct from failing."""


@dataclass
class ExperimentResult:
    """One experiment's verdict and every number behind it."""

    name: str
    question: str
    status: str = "pending"          # passed | failed | not_run | error
    what_changed: list[str] = field(default_factory=list)
    what_was_held_constant: list[str] = field(default_factory=list)
    expected_invariant: list[str] = field(default_factory=list)
    expected_to_change: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    tolerances: dict[str, Any] = field(default_factory=dict)
    licensed_solves: int = 0
    notes: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    def fail(self, reason: str) -> "ExperimentResult":
        self.status = "failed"
        self.failure_reason = reason
        return self

    def finish(self) -> "ExperimentResult":
        """Pass only if every boolean check passed and at least one exists."""

        booleans = {k: v for k, v in self.checks.items() if isinstance(v, bool)}
        if self.status in ("not_run", "error", "failed"):
            return self
        if not booleans:
            self.status = "not_run"
            self.failure_reason = (
                "no check was evaluated; an experiment that measured nothing has "
                "not passed"
            )
            return self
        failed = sorted(k for k, v in booleans.items() if not v)
        self.status = "passed" if not failed else "failed"
        if failed:
            self.failure_reason = f"checks failed: {failed}"
        return self

    def as_record(self) -> dict[str, Any]:
        return {
            "experiment": self.name,
            "question": self.question,
            "status": self.status,
            "what_changed": self.what_changed,
            "what_was_held_constant": self.what_was_held_constant,
            "expected_invariant": self.expected_invariant,
            "expected_to_change": self.expected_to_change,
            "checks": self.checks,
            "metrics": self.metrics,
            "tolerances": self.tolerances,
            "licensed_solver_calls": self.licensed_solves,
            "notes": self.notes,
            "failure_reason": self.failure_reason,
        }


def _write(directory: Path, name: str, payload: Any) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return runlog14.write_json_atomic(directory / name, payload)


# ---------------------------------------------------------------------------
# Experiment 1 -- native linear vs imported linear
# ---------------------------------------------------------------------------


def native_vs_imported_structural(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure], out_dir: Path,
) -> ExperimentResult:
    """The solver-free half of the equivalence experiment.

    Before asking whether nextnano++ solves the same physics from two encodings,
    establish that the two encodings really do describe one function. Both
    renderings are generated from a *single* ``CompositionProfile`` object, so
    the mathematical ``x_Al(z)`` is identical by construction and the only thing
    that can differ is how it was written into the deck.

    Overlapping structures are excluded on purpose. The native linear grammar
    cannot represent an overlapped profile at all -- it would let one ramp
    overwrite the other -- so comparing the two encodings there would compare
    the imported profile against a structure nobody requested.
    """

    result = ExperimentResult(
        name="native_import_equivalence_structural",
        question=(
            "Do the native-linear and imported renderings of one authoritative "
            "profile describe the same heterostructure?"
        ),
        what_changed=["deck encoding of x_Al(z) (ternary_linear vs ternary_import)"],
        what_was_held_constant=[
            "authoritative x_Al(z)", "geometry", "mesh", "temperature",
            "quantum region", "state counts",
        ],
        expected_invariant=[
            "intended composition", "interface centres", "10-90 widths",
            "integrated Al dose", "peak Al fraction",
        ],
        expected_to_change=["structure{} region syntax", "presence of import{}"],
        tolerances={"composition_max": TOL.equivalence_composition_max},
    )

    eligible = []
    for ref in refs:
        if ref.case.grading_profile != "linear":
            continue
        geometry = demo14.geometry_for(cfg, ref.parameters())
        profile = demo14.build_grading(cfg, ref.parameters(), geometry)
        if profile.diagnostics["grading_interfaces_overlap"]:
            result.notes.append(
                f"{ref.ref_id} excluded: its grades overlap, and the native "
                "linear grammar cannot represent that profile"
            )
            continue
        eligible.append((ref, geometry, profile))

    if not eligible:
        return result.fail("no non-overlapping linear reference structure found")

    rows = []
    for ref, geometry, profile in eligible:
        native = grading14.render_structure_blocks(profile)
        imported = grading14.render_imported_blocks(profile)
        native_deck = demo14.render_deck(cfg, geometry, profile, native)
        imported_deck = demo14.render_deck(cfg, geometry, profile, imported)

        # The imported table IS the profile, so any difference here is a
        # serialization defect rather than a physics one.
        table = np.array(
            [[float(v) for v in line.split()]
             for line in imported["datafile"].strip().splitlines()],
            dtype=float,
        )
        table_error = float(np.max(np.abs(table[:, 1] - profile.al_fraction)))
        position_error = float(np.max(np.abs(table[:, 0] - profile.x_nm)))

        widths = _requested_widths(ref)
        rows.append({
            "ref_id": ref.ref_id,
            "grading_profile": ref.case.grading_profile,
            "native_render_method": (
                "ternary_import" if "ternary_import" in native["structure_block"]
                else "ternary_linear"),
            "imported_render_method": "ternary_import",
            "native_region_count": len(native["regions"]),
            "imported_region_count": len(imported["regions"]),
            "imported_table_rows": int(table.shape[0]),
            "imported_table_max_composition_error": table_error,
            "imported_table_max_position_error_nm": position_error,
            "decks_differ": bool(native_deck != imported_deck),
            "native_deck_sha256": _sha_text(native_deck),
            "imported_deck_sha256": _sha_text(imported_deck),
            "grading_width_report": measure17.grading_width_report(
                profile, widths, float(cfg["materials"]["barrier_al_fraction"])),
            "interfaces_nm": dict(profile.request["interfaces_nm"]),
            "integrated_al_dose_nm": float(
                np.trapezoid(profile.al_fraction_continuous,
                             profile.x_nm_continuous)),
            "peak_al_fraction_central": profile.diagnostics[
                "realized_peak_al_fraction"],
        })

    result.metrics = {
        "structures_compared": len(rows),
        "structures": rows,
        "why_overlap_is_excluded": (
            "a native linear region template cannot express two overlapping "
            "ramps; the later region overwrites the earlier one"
        ),
    }
    result.checks = {
        "at_least_one_eligible_structure": bool(rows),
        "imported_table_reproduces_profile_exactly": all(
            r["imported_table_max_composition_error"] <= 1e-8 for r in rows),
        "imported_table_positions_exact": all(
            r["imported_table_max_position_error_nm"] <= 1e-6 for r in rows),
        "native_path_really_is_native": all(
            r["native_render_method"] == "ternary_linear" for r in rows),
        "two_encodings_produce_different_decks": all(r["decks_differ"] for r in rows),
    }
    _write(out_dir, "native_vs_imported_structural.json", result.as_record())
    return result.finish()


def _sha_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _requested_widths(ref: refs17.ReferenceStructure) -> dict[str, float]:
    params = ref.parameters()
    return {
        "outer_left_algaas_to_gaas": params["algaas_to_gaas_grading_width_10_90_nm"],
        "central_gaas_to_algaas": params["gaas_to_algaas_grading_width_10_90_nm"],
        "central_algaas_to_gaas": params["algaas_to_gaas_grading_width_10_90_nm"],
        "outer_right_gaas_to_algaas": params["gaas_to_algaas_grading_width_10_90_nm"],
    }


def native_vs_imported_physics(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure],
    out_dir: Path, environment: solve17.SolverEnvironment, cache: solve17.SolveCache,
) -> ExperimentResult:
    """The licensed half: does nextnano++ solve the same physics both ways?

    Phases and signs of eigenvectors are arbitrary, so wavefunctions are compared
    through ``|psi|^2`` and through ``|<psi_native|psi_imported>|``, never by
    subtracting envelopes.
    """

    result = ExperimentResult(
        name="native_import_equivalence_physics",
        question=(
            "Given two valid nextnano++ encodings of one heterostructure, does "
            "the solver produce the same band edges, states and transitions?"
        ),
        what_changed=["deck encoding of x_Al(z)"],
        what_was_held_constant=[
            "authoritative x_Al(z)", "geometry", "mesh", "temperature",
            "quantum region", "state counts", "electric field (none)",
        ],
        expected_invariant=[
            "realized composition", "band edges", "E1/E2", "HH1/HH2",
            "transition energies", "|psi|^2",
        ],
        expected_to_change=["nothing physical"],
        tolerances={
            "energy_eV": TOL.equivalence_energy_eV,
            "transition_eV": TOL.equivalence_transition_eV,
            "composition_max": TOL.equivalence_composition_max,
        },
    )

    eligible = [
        ref for ref in refs
        if ref.case.grading_profile == "linear"
        and not demo14.build_grading(
            cfg, ref.parameters(), demo14.geometry_for(cfg, ref.parameters())
        ).diagnostics["grading_interfaces_overlap"]
    ]
    if not eligible:
        return result.fail("no non-overlapping linear reference structure")

    comparisons = []
    for ref in eligible:
        pair: dict[str, Any] = {"ref_id": ref.ref_id}
        solved: dict[str, Any] = {}
        for encoding in ("auto", "imported"):
            variant = refs17.Variant(
                variant_id=f"{ref.ref_id}_equiv_{encoding}",
                ref_id=ref.ref_id,
                experiment="native_import_equivalence",
                hypothesis=f"{encoding} encoding of the same authoritative profile",
                render_options={"render_method": encoding},
            )
            resolved = refs17.resolve_variant(cfg, variant, references=refs)
            request, transform = solve17.build_request(
                variant.variant_id, resolved, field_kV_cm=0.0)
            work = out_dir / "solves" / variant.variant_id
            outcome = solve17.execute(request, environment, work, cache)
            solved[encoding] = (resolved, outcome, transform)
            if not outcome.usable:
                result.status = "not_run" if outcome.status == "not_run" else "failed"
                result.failure_reason = outcome.failure_reason
                pair[encoding] = outcome.as_record()

        if result.status in ("not_run", "failed"):
            comparisons.append(pair)
            break

        pair.update(_compare_two_solves(
            solved["auto"], solved["imported"], cfg,
            labels=("native_linear", "imported_table"),
        ))
        comparisons.append(pair)

    result.licensed_solves = cache.solver_calls
    result.metrics = {"comparisons": comparisons}
    if result.status not in ("not_run", "failed"):
        result.checks = {
            "composition_agrees": all(
                c["composition"]["max_abs_difference"]
                <= TOL.equivalence_composition_max for c in comparisons),
            "electron_energies_agree": all(
                c["electron"]["max_abs_energy_difference_eV"]
                <= TOL.equivalence_energy_eV for c in comparisons),
            "hole_energies_agree": all(
                c["heavy_hole"]["max_abs_energy_difference_eV"]
                <= TOL.equivalence_energy_eV for c in comparisons),
            "transitions_agree": all(
                c["transition"]["absolute_difference_eV"]
                <= TOL.equivalence_transition_eV for c in comparisons),
            "probability_densities_agree": all(
                c["electron"]["max_probability_density_difference"]
                <= TOL.mirror_probability for c in comparisons),
        }
    _write(out_dir, "native_vs_imported_linear_equivalence.json", result.as_record())
    return result.finish()


def _compare_two_solves(
    a: tuple[Any, Any, Any], b: tuple[Any, Any, Any], cfg: Mapping[str, Any],
    *, labels: tuple[str, str],
) -> dict[str, Any]:
    """Composition, states and transitions of two completed solves."""

    (resolved_a, out_a, _), (resolved_b, out_b, _) = a, b
    region = str(cfg["nextnano"]["quantum_region_name"])
    comp_a = measure17.load_realized_composition(out_a.raw_dir)
    comp_b = measure17.load_realized_composition(out_b.raw_dir)
    grid = comp_a.x_nm
    b_on_a = np.interp(grid, comp_b.x_nm, comp_b.al_fraction)
    composition = {
        "grids_identical": bool(
            comp_a.x_nm.shape == comp_b.x_nm.shape
            and np.allclose(comp_a.x_nm, comp_b.x_nm)),
        "max_abs_difference": float(np.max(np.abs(comp_a.al_fraction - b_on_a))),
        "rms_difference": float(np.sqrt(np.mean((comp_a.al_fraction - b_on_a) ** 2))),
        labels[0]: comp_a.as_record(),
        labels[1]: comp_b.as_record(),
    }

    states_a = measure17.load_states(out_a.raw_dir, region)
    states_b = measure17.load_states(out_b.raw_dir, region)
    bands: dict[str, Any] = {}
    for key, band_a, band_b in (
        ("electron", states_a.electron, states_b.electron),
        ("heavy_hole", states_a.heavy_hole, states_b.heavy_hole),
    ):
        n = min(band_a.count, band_b.count)
        diffs = [
            abs(float(band_a.energies_eV[i] - band_b.energies_eV[i]))
            for i in range(n)
        ]
        # Sign and phase of an eigenvector are arbitrary: compare |psi|^2 and the
        # magnitude of the overlap, never the envelopes themselves.
        density_diff, overlaps = [], []
        for i in range(n):
            pa = band_a.envelopes[:, i] ** 2
            pb = np.interp(band_a.z_nm, band_b.z_nm, band_b.envelopes[:, i] ** 2)
            density_diff.append(float(np.max(np.abs(pa - pb))))
            psi_b = np.interp(band_a.z_nm, band_b.z_nm, band_b.envelopes[:, i])
            overlaps.append(abs(float(
                np.trapezoid(band_a.envelopes[:, i] * psi_b, band_a.z_nm))))
        bands[key] = {
            "states_compared": n,
            f"{labels[0]}_energies_eV": [float(e) for e in band_a.energies_eV[:n]],
            f"{labels[1]}_energies_eV": [float(e) for e in band_b.energies_eV[:n]],
            "abs_energy_differences_eV": diffs,
            "max_abs_energy_difference_eV": max(diffs) if diffs else 0.0,
            "max_probability_density_difference": max(density_diff) if density_diff else 0.0,
            "state_overlap_magnitudes": overlaps,
            "min_state_overlap_magnitude": min(overlaps) if overlaps else None,
        }

    t_a, t_b = states_a.transition_eV(), states_b.transition_eV()
    return {
        "composition": composition,
        "electron": bands["electron"],
        "heavy_hole": bands["heavy_hole"],
        "transition": {
            f"{labels[0]}_e1_hh1_eV": t_a,
            f"{labels[1]}_e1_hh1_eV": t_b,
            "absolute_difference_eV": abs(t_a - t_b),
            f"{labels[0]}_wavelength_nm": measure17.HC_EV_NM / t_a if t_a > 0 else None,
            f"{labels[1]}_wavelength_nm": measure17.HC_EV_NM / t_b if t_b > 0 else None,
        },
        "quality": {
            labels[0]: measure17.state_quality_report(states_a),
            labels[1]: measure17.state_quality_report(states_b),
        },
    }


# ---------------------------------------------------------------------------
# Experiment 2 -- authoritative overlap physics
# ---------------------------------------------------------------------------


def overlap_physics(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure], out_dir: Path,
) -> ExperimentResult:
    """Prove the renderer does not fabricate a nominal plateau across a thin barrier."""

    result = ExperimentResult(
        name="overlap_physics",
        question=(
            "When two grading ramps overlap, is the resulting composition an "
            "explicit, reproducible consequence of a stated rule?"
        ),
        what_changed=["central barrier thickness relative to the grading widths"],
        what_was_held_constant=[
            "grading family", "nominal Al fraction", "total well thickness", "mesh",
        ],
        expected_invariant=["the combination rule itself", "composition bounds"],
        expected_to_change=[
            "peak Al fraction in the barrier", "existence of a plateau",
            "render method",
        ],
    )

    x_max = float(cfg["materials"]["barrier_al_fraction"])
    rows = []
    for ref in refs:
        geometry = demo14.geometry_for(cfg, ref.parameters())
        profile = demo14.build_grading(cfg, ref.parameters(), geometry)
        report = measure17.overlap_physics_report(profile, x_max)
        blocks = grading14.render_structure_blocks(profile)
        report.update({
            "ref_id": ref.ref_id,
            "grading_profile": ref.case.grading_profile,
            "render_method": (
                "ternary_import" if "ternary_import" in blocks["structure_block"]
                else "ternary_linear"),
            "render_fallback_reason": blocks.get("render_fallback_reason", ""),
            "requested_left_width_nm": ref.parameters()[
                "gaas_to_algaas_grading_width_10_90_nm"],
            "requested_right_width_nm": ref.parameters()[
                "algaas_to_gaas_grading_width_10_90_nm"],
        })
        rows.append(report)

    # Determinism: the rule must give the same answer twice.
    repeat = [
        measure17.overlap_physics_report(
            demo14.build_grading(
                cfg, ref.parameters(), demo14.geometry_for(cfg, ref.parameters())),
            x_max,
        )["realized_peak_al_fraction"]
        for ref in refs
    ]
    deterministic = all(
        abs(r["realized_peak_al_fraction"] - v) < 1e-15
        for r, v in zip(rows, repeat)
    )

    overlapping = [r for r in rows if r["grades_overlap"]]
    result.metrics = {
        "structures": rows,
        "overlapping_structures": len(overlapping),
        "authoritative_rule": rows[0]["combination_rule"] if rows else None,
    }
    result.checks = {
        "combination_rule_verified_on_every_structure": all(
            r["combination_rule_verified"] for r in rows),
        "rule_is_deterministic": deterministic,
        "no_fabricated_plateau_where_grades_overlap": all(
            not r["nominal_plateau_exists"] for r in overlapping),
        "overlapped_peak_is_below_nominal": all(
            r["realized_peak_al_fraction"] < x_max for r in overlapping),
        "linear_overlap_switches_to_imported": all(
            r["render_method"] == "ternary_import"
            for r in overlapping if r["grading_profile"] == "linear"),
        "composition_never_exceeds_nominal": all(
            r["realized_peak_al_fraction"] <= x_max + 1e-12 for r in rows),
        "at_least_one_overlapping_structure_present": bool(overlapping),
    }
    _write(out_dir, "overlap_physics.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment 3 -- grading-width definition
# ---------------------------------------------------------------------------


def grading_width_definition(
    cfg: Mapping[str, Any], out_dir: Path,
) -> ExperimentResult:
    """Standardize what ``grading_width_nm`` means across all four families.

    The production convention already is the physical 10%-90% width: each family
    carries its 10-90 width in its own natural unit and
    ``ProfileFamily.scale_for`` divides the requested nanometres by it. This
    experiment verifies that the convention is *realized*, by measuring an
    isolated interface of every family at a common requested width.
    """

    result = ExperimentResult(
        name="grading_width_definition",
        question=(
            "Does one number, grading_width_nm, mean the same physical interface "
            "for linear, Fermi, erf and cosine?"
        ),
        what_changed=["grading profile family"],
        what_was_held_constant=[
            "requested 10-90 width", "geometry", "barrier thickness", "mesh",
            "Al fraction",
        ],
        expected_invariant=["realized 10-90 width at an isolated interface"],
        expected_to_change=[
            "raw mathematical scale parameter", "shape of the transition",
            "composition at the barrier centre",
        ],
        tolerances={"isolated_width_nm": TOL.grading_width_isolated_nm},
    )

    x_max = float(cfg["materials"]["barrier_al_fraction"])
    # A common comparison point: the paper geometry with a thick enough barrier
    # that both central interfaces are isolated at every width tested.
    common = {
        "asymmetry_s": 0.42,
        "nominal_central_barrier_thickness_nm": 2.50,
        "grading_profile": "linear",
    }
    families = list(grading14.PROFILE_FAMILIES)
    widths = [0.40, 0.90, 1.40]

    rows = []
    for width in widths:
        for family_name in families:
            params = dict(common)
            params.update({
                "grading_profile": family_name,
                "gaas_to_algaas_grading_width_10_90_nm": width,
                "algaas_to_gaas_grading_width_10_90_nm": width,
            })
            geometry = demo14.geometry_for(cfg, params)
            profile = demo14.build_grading(cfg, params, geometry)
            requested = {
                "outer_left_algaas_to_gaas": width,
                "central_gaas_to_algaas": width,
                "central_algaas_to_gaas": width,
                "outer_right_gaas_to_algaas": width,
            }
            report = measure17.grading_width_report(profile, requested, x_max)
            fam = grading14.family(family_name)
            for entry in report["interfaces"]:
                rows.append({
                    "requested_width_nm": width,
                    "profile_family": family_name,
                    "family_10_90_in_natural_units": fam.width_10_90_natural,
                    "compact_support": fam.compact_support,
                    **entry,
                })

    isolated = [r for r in rows if r["interface_is_isolated"]
                and r["width_error_nm"] is not None]
    worst = max((r["width_error_nm"] for r in isolated), default=0.0)
    by_family: dict[str, float] = {}
    for row in isolated:
        by_family[row["profile_family"]] = max(
            by_family.get(row["profile_family"], 0.0), row["width_error_nm"])

    result.metrics = {
        "definition": (
            "grading_width_nm is the 10%-to-90% Al-composition transition width "
            "of that interface's grading function taken in isolation"
        ),
        "production_convention_source": (
            "demo.yaml grading.width_definition = 10_90_percent_of_transition; "
            "grading14.ProfileFamily.scale_for divides the requested width by "
            "the family's own 10-90 width in natural units"
        ),
        "family_natural_widths": {
            name: grading14.family(name).width_10_90_natural for name in families
        },
        "rows": rows,
        "isolated_interfaces_measured": len(isolated),
        "max_isolated_width_error_nm": worst,
        "max_isolated_width_error_by_family": by_family,
        "composite_interface_note": (
            "at a barrier thin enough for the two interfaces to superpose, the "
            "realized 10-90 width of the composite is smaller than either "
            "request and the nominal-referenced width is undefined; both are "
            "reported rather than treated as failures"
        ),
    }
    result.checks = {
        "every_family_measured": set(by_family) == set(families),
        "isolated_width_matches_request_for_every_family": worst
        <= TOL.grading_width_isolated_nm,
        "linear_is_exact": by_family.get("linear", 1.0) <= 1e-9,
        "nominal_reference_null_is_reported_not_failed": all(
            (r["realized_peak_referenced_10_90_width_nm"] is not None)
            or (not r["interface_is_isolated"])
            for r in rows
        ),
    }
    _write(out_dir, "grading_width_definition.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment 4 -- interface centre and local profile accuracy
# ---------------------------------------------------------------------------


def interface_accuracy(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure],
    out_dir: Path, realized: Mapping[str, Any] | None = None,
) -> ExperimentResult:
    """Where each interface actually is, measured in a local window.

    ``realized`` maps ref_id to a :class:`measure17.RealizedComposition` when
    licensed output is available; without it the experiment still validates the
    authoritative Python profile, which is where the 7.1 / 2.9 nm regression
    lived.
    """

    result = ExperimentResult(
        name="interface_accuracy",
        question=(
            "Does every interface sit where it was requested, to within "
            "discretization error, when measured locally?"
        ),
        what_changed=["nothing; this is a positional accuracy audit"],
        what_was_held_constant=["all structure parameters"],
        expected_invariant=[
            "50% crossing at the requested interface centre",
            "10-90 width at isolated interfaces",
        ],
        expected_to_change=[],
        tolerances={
            "interface_centre_nm": TOL.interface_centre_nm,
            "grading_width_isolated_nm": TOL.grading_width_isolated_nm,
        },
    )

    x_max = float(cfg["materials"]["barrier_al_fraction"])
    rows: list[dict[str, Any]] = []
    forbidden_hits: list[str] = []
    for ref in refs:
        geometry = demo14.geometry_for(cfg, ref.parameters())
        profile = demo14.build_grading(cfg, ref.parameters(), geometry)
        widths = _requested_widths(ref)
        report = measure17.grading_width_report(profile, widths, x_max)

        realized_entry = (realized or {}).get(ref.ref_id)
        for entry in report["interfaces"]:
            record = {"ref_id": ref.ref_id, "source": "authoritative_python", **entry}
            # Local integrated dose in this interface's own window.
            lo, hi = entry["measurement_window_nm"]
            mask = (profile.x_nm_continuous >= lo) & (profile.x_nm_continuous <= hi)
            record["local_integrated_al_dose_nm"] = float(np.trapezoid(
                profile.al_fraction_continuous[mask], profile.x_nm_continuous[mask]
            )) if np.count_nonzero(mask) > 1 else None
            rows.append(record)

            width = entry["realized_peak_referenced_10_90_width_nm"]
            # The exact regression: a grading-width search that wandered across a
            # well and returned the WELL width. 7.1 and 2.9 nm are the paper's
            # well thicknesses and must never appear as an interface width.
            if width is not None and ref.ref_id == "REF01":
                for forbidden in (7.1, 2.9):
                    if abs(width - forbidden) < 0.5:
                        forbidden_hits.append(
                            f"{ref.ref_id}/{entry['interface']} reported "
                            f"{width:.3f} nm, which is the {forbidden} nm well width"
                        )

        if realized_entry is not None:
            comparison = measure17.compare_composition(profile, realized_entry)
            rows.append({
                "ref_id": ref.ref_id, "source": "nextnano_realized",
                **comparison,
            })

    isolated = [
        r for r in rows
        if r.get("interface_is_isolated") and r.get("centre_error_nm") is not None
    ]
    worst_centre = max((r["centre_error_nm"] for r in isolated), default=0.0)
    worst_width = max(
        (r["width_error_nm"] for r in isolated if r.get("width_error_nm") is not None),
        default=0.0,
    )

    result.metrics = {
        "rows": rows,
        "isolated_interfaces": len(isolated),
        "max_centre_error_nm": worst_centre,
        "max_isolated_width_error_nm": worst_width,
        "realized_composition_available": bool(realized),
        "regression_guard": (
            "7.1 nm and 2.9 nm are the paper reference's WELL widths. A local "
            "interface search must never return either as a grading width."
        ),
    }
    result.checks = {
        "all_windows_isolated": all(
            r.get("window_isolated_from_other_interfaces", True) for r in rows),
        "interface_centres_within_one_mesh_cell": worst_centre <= TOL.interface_centre_nm,
        "isolated_widths_within_tolerance": worst_width <= TOL.grading_width_isolated_nm,
        "no_well_width_reported_as_grading_width": not forbidden_hits,
    }
    if forbidden_hits:
        result.metrics["forbidden_width_hits"] = forbidden_hits
    _write(out_dir, "interface_accuracy.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment 5 -- mesh snapping
# ---------------------------------------------------------------------------


def mesh_snapping(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure], out_dir: Path,
) -> ExperimentResult:
    """Requested continuous geometry against mesh-represented geometry."""

    result = ExperimentResult(
        name="mesh_snapping",
        question=(
            "How much of the difference between requested and realized geometry "
            "is discretization, and how much would be a renderer error?"
        ),
        what_changed=["nothing; this separates two sources of error"],
        what_was_held_constant=["all structure parameters", "mesh"],
        expected_invariant=["layer ordering"],
        expected_to_change=["nothing"],
    )

    mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    rows = []
    for ref in refs:
        geometry = demo14.geometry_for(cfg, ref.parameters())
        profile = demo14.build_grading(cfg, ref.parameters(), geometry)
        report = measure17.mesh_snapping_report(geometry, profile, mesh)
        report["ref_id"] = ref.ref_id
        report["requested_thick_well_nm"] = geometry.thick_well_nm
        report["requested_thin_well_nm"] = geometry.thin_well_nm
        report["requested_barrier_nm"] = geometry.barrier_nm
        report["requested_grading_widths_nm"] = {
            "gaas_to_algaas": ref.parameters()["gaas_to_algaas_grading_width_10_90_nm"],
            "algaas_to_gaas": ref.parameters()["algaas_to_gaas_grading_width_10_90_nm"],
        }
        rows.append(report)

    worst = max(r["max_interface_snapping_error_nm"] for r in rows)
    result.metrics = {
        "mesh_nm": mesh,
        "structures": rows,
        "max_snapping_error_nm": worst,
        "half_cell_nm": 0.5 * mesh,
        "interpretation": (
            "an interface can never land further than half a mesh cell from its "
            "request; a larger error is a renderer or geometry defect, not "
            "discretization"
        ),
    }
    result.checks = {
        "every_snap_within_half_a_cell": all(r["within_half_a_mesh_cell"] for r in rows),
        "layer_ordering_preserved": all(
            r["layers"]["thick_well_nm"]["mesh_represented_nm"] > 0
            and r["layers"]["central_barrier_nm"]["mesh_represented_nm"] > 0
            and r["layers"]["thin_well_nm"]["mesh_represented_nm"] > 0
            for r in rows),
        "snapping_is_measured_not_assumed_exact": all(
            "snapping_error_nm" in next(iter(r["interfaces"].values())) for r in rows),
    }
    _write(out_dir, "mesh_snapping.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment 10 -- parameter-consumer matrix
# ---------------------------------------------------------------------------

#: Which pipeline stage each parameter is *allowed* to affect. This is the
#: intended ownership; :func:`parameter_effect_matrix` checks the code against it.
PARAMETER_OWNERSHIP: Mapping[str, dict[str, str]] = {
    "asymmetry_s": {
        "geometry": "YES", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "demo14.geometry_for -> chi2.well_widths_from_asymmetry",
    },
    "nominal_central_barrier_thickness_nm": {
        "geometry": "YES", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "demo14.geometry_for",
    },
    "gaas_to_algaas_grading_width_10_90_nm": {
        "geometry": "NO", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "grading14.build_structure_profile (scale_rise)",
    },
    "algaas_to_gaas_grading_width_10_90_nm": {
        "geometry": "NO", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "grading14.build_structure_profile (scale_fall)",
    },
    "grading_profile": {
        "geometry": "NO", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "grading14.family + RENDER_METHOD",
    },
    "barrier_al_fraction": {
        "geometry": "NO", "composition": "YES", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "grading14.build_structure_profile (max_al_fraction)",
    },
    "mesh.active_region_grid_spacing_nm": {
        "geometry": "NUMERICAL", "composition": "NUMERICAL",
        "band_edges": "NUMERICAL", "quantum_states": "NUMERICAL",
        "optical_analysis": "NUMERICAL",
        "consumer": "demo14.build_grading + demo14.render_deck grid lines",
    },
    "materials.temperature_K": {
        "geometry": "NO", "composition": "NO", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "demo14.render_deck -> global{ temperature }",
    },
    "electric_field_kV_cm": {
        "geometry": "NO", "composition": "NO", "band_edges": "YES",
        "quantum_states": "YES", "optical_analysis": "YES",
        "consumer": "solve17.with_electric_field (Demo 17 only; not in the "
                    "Demo 14 production model)",
    },
    "chi2.broadening_meV": {
        "geometry": "NO", "composition": "NO", "band_edges": "NO",
        "quantum_states": "NO", "optical_analysis": "YES",
        "consumer": "chi2.Chi2Settings.broadening_meV",
    },
    "chi2.target_wavelength_nm": {
        "geometry": "NO", "composition": "NO", "band_edges": "NO",
        "quantum_states": "NO", "optical_analysis": "ANALYSIS_ONLY",
        "consumer": "demo14.analyse_real_trial detuning; never the deck",
    },
}


def parameter_effect_matrix(
    cfg: Mapping[str, Any], out_dir: Path, demo_dir: Path,
) -> ExperimentResult:
    """Check the production code actually honours the declared ownership.

    Two things go wrong without this: a configuration setting becomes decorative
    because nothing reads it, or an analysis-only setting reaches the deck and
    silently changes the solver model. Both are checked by rendering decks with
    the parameter varied and seeing whether the deck text moved.
    """

    result = ExperimentResult(
        name="parameter_effect_matrix",
        question=(
            "Does every parameter affect exactly the pipeline stages it is "
            "supposed to, and no others?"
        ),
        what_changed=["one parameter at a time"],
        what_was_held_constant=["everything else"],
        expected_invariant=["stages marked NO"],
        expected_to_change=["stages marked YES"],
    )

    ref = refs17.reference("REF01")
    base_params = ref.parameters()
    base_geometry = demo14.geometry_for(cfg, base_params)
    base_profile = demo14.build_grading(cfg, base_params, base_geometry)
    base_blocks = grading14.render_structure_blocks(base_profile)
    base_deck = demo14.render_deck(cfg, base_geometry, base_profile, base_blocks)

    def render_with(params: Mapping[str, Any], config: Mapping[str, Any]
                    ) -> tuple[str, Any, Any]:
        geometry = demo14.geometry_for(config, params)
        profile = demo14.build_grading(config, params, geometry)
        blocks = grading14.render_structure_blocks(profile)
        return demo14.render_deck(config, geometry, profile, blocks), geometry, profile

    import copy

    observations: list[dict[str, Any]] = []

    def observe(label: str, params: Mapping[str, Any], config: Mapping[str, Any],
                declared: Mapping[str, str]) -> None:
        deck, geometry, profile = render_with(params, config)
        geometry_changed = geometry.as_record() != base_geometry.as_record()
        composition_changed = not (
            profile.al_fraction.shape == base_profile.al_fraction.shape
            and np.allclose(profile.al_fraction, base_profile.al_fraction)
        )
        observations.append({
            "parameter": label,
            "declared": dict(declared),
            "observed_geometry_changed": bool(geometry_changed),
            "observed_composition_changed": bool(composition_changed),
            "observed_deck_changed": bool(deck != base_deck),
            "consumer": declared.get("consumer", ""),
        })

    # Structure parameters.
    for name, delta in (
        ("asymmetry_s", 0.05),
        ("nominal_central_barrier_thickness_nm", 0.20),
        ("gaas_to_algaas_grading_width_10_90_nm", 0.20),
        ("algaas_to_gaas_grading_width_10_90_nm", 0.20),
    ):
        params = dict(base_params)
        params[name] = float(params[name]) + delta
        observe(name, params, cfg, PARAMETER_OWNERSHIP[name])

    params = dict(base_params)
    params["grading_profile"] = "fermi"
    observe("grading_profile", params, cfg, PARAMETER_OWNERSHIP["grading_profile"])

    # Configuration settings.
    for dotted, value in (
        ("mesh.active_region_grid_spacing_nm", 0.025),
        ("materials.temperature_K", 77.0),
        ("materials.barrier_al_fraction", 0.45),
    ):
        config = copy.deepcopy(dict(cfg))
        node = config
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
        key = "barrier_al_fraction" if dotted.endswith("barrier_al_fraction") else dotted
        observe(dotted, base_params, config, PARAMETER_OWNERSHIP[key])

    # Analysis-only settings must not reach the deck at all.
    analysis_only = []
    for dotted, value in (
        ("chi2.broadening_meV", 10.0),
        ("chi2.target_wavelength_nm", 1310.0),
    ):
        config = copy.deepcopy(dict(cfg))
        node = config
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
        deck, geometry, profile = render_with(base_params, config)
        analysis_only.append({
            "parameter": dotted,
            "declared": dict(PARAMETER_OWNERSHIP[dotted]),
            "observed_deck_changed": bool(deck != base_deck),
            "observed_geometry_changed": geometry.as_record() != base_geometry.as_record(),
            "observed_composition_changed": not np.allclose(
                profile.al_fraction, base_profile.al_fraction),
        })

    # The electric field is a Demo 17 deck transform, so it is checked there.
    field_deck, field_transform = solve17.with_electric_field(base_deck, 50.0)
    field_audit = solve17.verify_transform_is_additive(
        base_deck, field_deck, field_transform["inserted_block"])

    mismatches = []
    for row in observations:
        declared = row["declared"]
        if declared["geometry"] == "NO" and row["observed_geometry_changed"]:
            mismatches.append(f"{row['parameter']} changed geometry but declares NO")
        if declared["geometry"] == "YES" and not row["observed_geometry_changed"]:
            mismatches.append(f"{row['parameter']} declares geometry YES but did not")
        if declared["composition"] == "YES" and not row["observed_composition_changed"]:
            mismatches.append(
                f"{row['parameter']} declares composition YES but did not change it")
        if declared["composition"] == "NO" and row["observed_composition_changed"]:
            mismatches.append(
                f"{row['parameter']} changed composition but declares NO")
        if not row["observed_deck_changed"]:
            mismatches.append(
                f"{row['parameter']} is decorative: it changed no deck content")

    result.metrics = {
        "matrix": {k: dict(v) for k, v in PARAMETER_OWNERSHIP.items()},
        "observations": observations,
        "analysis_only_observations": analysis_only,
        "electric_field": {
            "is_a_demo17_deck_transform": True,
            "transform_is_purely_additive": field_audit["additive"],
            "sign_convention": solve17.FIELD_SIGN_CONVENTION,
        },
        "mismatches": mismatches,
    }
    result.checks = {
        "no_ownership_mismatch": not mismatches,
        "broadening_does_not_reach_the_deck": not analysis_only[0]["observed_deck_changed"],
        "target_wavelength_does_not_reach_the_deck": not analysis_only[1][
            "observed_deck_changed"],
        "analysis_only_settings_leave_composition_alone": all(
            not row["observed_composition_changed"] for row in analysis_only),
        "electric_field_transform_is_additive": field_audit["additive"],
    }
    _write(out_dir, "parameter_effect_matrix.json", result.as_record())
    _write_matrix_csv(out_dir.parent / "summaries" / "parameter_effect_matrix.csv")
    return result.finish()


def _write_matrix_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ("parameter,geometry,composition,band_edges,quantum_states,"
              "optical_analysis,authoritative_consumer\n")
    lines = [
        f"{name},{row['geometry']},{row['composition']},{row['band_edges']},"
        f"{row['quantum_states']},{row['optical_analysis']},\"{row['consumer']}\"\n"
        for name, row in PARAMETER_OWNERSHIP.items()
    ]
    return runlog14.write_text_atomic(path, header + "".join(lines))


# ---------------------------------------------------------------------------
# Experiment Q -- independent energy-to-wavelength validation
# ---------------------------------------------------------------------------


def energy_wavelength(
    cfg: Mapping[str, Any], out_dir: Path,
    states: measure17.SolvedStates | None = None,
) -> ExperimentResult:
    """Recompute every wavelength independently of the production path."""

    result = ExperimentResult(
        name="energy_wavelength",
        question=(
            "Are transition energies converted to wavelengths correctly, and "
            "would an eV/meV slip be visible?"
        ),
        what_changed=["nothing; this is an arithmetic cross-check"],
        what_was_held_constant=["all physics"],
        expected_invariant=["independent and production wavelengths agree"],
        expected_to_change=[],
        tolerances={"relative": TOL.wavelength_relative},
    )

    target_nm = float(cfg["chi2"]["target_wavelength_nm"])
    target = measure17.target_energy_check(target_nm)

    # Reference conversions that do not need a solver.
    probes = []
    for energy_eV in (0.7999, 0.80, 1.00, 1.4237, 1.55):
        probes.append(measure17.wavelength_check(energy_eV, 0.0))

    from_states = None
    if states is not None:
        from_states = [
            measure17.wavelength_check(
                float(states.electron.energies_eV[i]),
                float(states.heavy_hole.energies_eV[j]),
            )
            for i in range(min(2, states.electron.count))
            for j in range(min(2, states.heavy_hole.count))
        ]

    # A deliberate unit slip must be detectable, not merely unlikely.
    slip = measure17.wavelength_check(0.80, 0.0)
    slip_ratio = (
        slip["wavelength_if_energy_mistaken_for_meV_nm"]
        / slip["independent_wavelength_nm"]
    )

    result.metrics = {
        "constant_eV_nm": measure17.HC_EV_NM,
        "target": target,
        "probe_conversions": probes,
        "from_solved_states": from_states,
        "unit_slip_detection": {
            "energy_eV": 0.80,
            "correct_wavelength_nm": slip["independent_wavelength_nm"],
            "wavelength_if_eV_read_as_meV_nm": slip[
                "wavelength_if_energy_mistaken_for_meV_nm"],
            "ratio": slip_ratio,
        },
    }
    result.checks = {
        "target_energy_agrees_with_production": (
            target["relative_difference"] <= TOL.wavelength_relative),
        "target_round_trips": target["round_trip_error_nm"] <= 1e-9,
        "probe_conversions_agree_with_production": all(
            p["within_tolerance"] for p in probes),
        "ev_mev_slip_is_a_factor_of_1000": abs(slip_ratio - 1000.0) < 1e-6,
        "solved_state_conversions_agree": (
            all(p["within_tolerance"] for p in from_states)
            if from_states else True),
    }
    _write(out_dir, "energy_wavelength.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment R -- broadening isolation
# ---------------------------------------------------------------------------


def synthetic_reference_states(
    n_points: int = 401, domain_nm: tuple[float, float] = (0.0, 20.0),
) -> measure17.SolvedStates:
    """Deterministic analytic states for testing the analysis layer alone.

    Particle-in-a-box envelopes on a fixed grid. These are *not* nextnano++
    output and are never used to make a claim about nextnano++; they exist so
    the broadening-isolation property -- which is a property of the analysis
    code, not of the solver -- can be demonstrated without a licence.
    """

    z = np.linspace(domain_nm[0], domain_nm[1], n_points)
    width = domain_nm[1] - domain_nm[0]

    def box(n: int) -> np.ndarray:
        return np.sin(n * math.pi * (z - domain_nm[0]) / width)

    # The excited states are placed far away on purpose. With closely spaced
    # levels the four E_i -> HH_j transitions put four two-photon resonances
    # within a few tens of meV of each other, and any "linewidth" measured
    # across them is the width of the multiplet rather than of a line -- which
    # barely moves when the broadening does.
    electron = chi2mod.BandStates(
        z, np.array([0.100, 0.400]), np.column_stack([box(1), box(2)]), "Gamma")
    heavy_hole = chi2mod.BandStates(
        z, np.array([-1.500, -1.800]), np.column_stack([box(1), box(2)]), "HH")
    return measure17.SolvedStates(
        electron=electron, heavy_hole=heavy_hole,
        raw_dir="<synthetic>", region="<synthetic>", z_nm=z,
    )


def _line_width_at_half_prominence_eV(
    energies: np.ndarray, magnitude: np.ndarray, peak_index: int
) -> tuple[float | None, float]:
    """Width of the resonance measured above its own baseline.

    ``|chi2|`` does not fall to half its peak on either side: the resonance sits
    on a large non-resonant pedestal, which for these structures is 25-85% of the
    peak. A full-width-at-half-*maximum* therefore does not exist, and asking for
    one returns either nothing or the width of the whole scan window.

    The prominence is measured against the higher of the two side minima -- the
    conservative choice, since it yields the narrower width -- and the returned
    width is taken at half of that prominence.
    """

    peak = float(magnitude[peak_index])
    if not math.isfinite(peak) or peak <= 0 or peak_index <= 0 or peak_index >= magnitude.size - 1:
        return None, 0.0
    left_floor = float(np.min(magnitude[: peak_index + 1]))
    right_floor = float(np.min(magnitude[peak_index:]))
    baseline = max(left_floor, right_floor)
    prominence = peak - baseline
    if prominence <= 0:
        return None, 0.0
    level = baseline + 0.5 * prominence

    def crossing(step: int) -> float | None:
        index = peak_index
        while 0 <= index + step < magnitude.size:
            nxt = index + step
            if magnitude[nxt] <= level:
                a, b = magnitude[index], magnitude[nxt]
                t = 0.0 if a == b else (a - level) / (a - b)
                return float(energies[index] + t * (energies[nxt] - energies[index]))
            index = nxt
        return None

    left, right = crossing(-1), crossing(+1)
    if left is None or right is None:
        return None, prominence / peak
    return abs(right - left), prominence / peak


def broadening_isolation(
    cfg: Mapping[str, Any], out_dir: Path,
    states: measure17.SolvedStates | None = None,
) -> ExperimentResult:
    """Broadening must move spectra and nothing else.

    Only the optical post-processing is re-run. No deck is rendered and no
    solver is invoked, which is the point: if changing broadening required a
    solve, it would not be an analysis parameter.
    """

    result = ExperimentResult(
        name="broadening_isolation",
        question="Is broadening consumed only in the optical analysis layer?",
        what_changed=["chi2 broadening, 2 / 5 / 10 meV"],
        what_was_held_constant=[
            "solver result", "composition", "band edges", "state energies",
            "wavefunctions",
        ],
        expected_invariant=[
            "state energies", "wavefunctions", "transition energies",
        ],
        expected_to_change=["spectral linewidth", "peak susceptibility"],
    )

    source = "nextnano_solve" if states is not None else "synthetic_reference_states"
    states = states or synthetic_reference_states()

    energies_before = [float(e) for e in states.electron.energies_eV]
    holes_before = [float(e) for e in states.heavy_hole.energies_eV]
    envelopes_before = states.electron.envelopes.copy()

    # Scan around the TWO-PHOTON resonance of E1 -> HH1. SHG resonates when
    # 2*hbar*omega equals the transition energy, so a window centred on
    # (E1 - HH1)/2 is where a linewidth can be measured at all. The production
    # focused window is fixed at 1400-1800 nm and need not contain this
    # structure's resonance; measuring a width outside the line would compare
    # three numbers that are all tail.
    resonance_eV = 0.5 * states.transition_eV()
    span = 0.04
    photon_eV = np.linspace(resonance_eV - span, resonance_eV + span, 801)
    spectra = []
    for broadening in refs17.BROADENING_LADDER_MEV:
        settings = chi2mod.Chi2Settings(
            mode="relative", broadening_meV=float(broadening),
            max_states_per_band=2,
        )
        spectrum = chi2mod.chi2_spectrum(
            states.electron, states.heavy_hole, photon_eV, settings)
        magnitude = np.abs(np.asarray(spectrum.chi2, dtype=complex))
        peak_index = int(np.argmax(magnitude))
        fwhm_eV = _line_fwhm_eV(photon_eV, magnitude, peak_index)
        spectra.append({
            "broadening_meV": float(broadening),
            "peak_magnitude": float(magnitude[peak_index]),
            "peak_photon_energy_eV": float(photon_eV[peak_index]),
            "peak_wavelength_nm": measure17.HC_EV_NM / float(photon_eV[peak_index]),
            "fwhm_eV": fwhm_eV,
            "fwhm_meV": None if fwhm_eV is None else fwhm_eV * 1000.0,
            "peak_is_interior_to_window": bool(0 < peak_index < magnitude.size - 1),
            "spectrum_points": int(magnitude.size),
        })

    unchanged_e = [float(e) for e in states.electron.energies_eV] == energies_before
    unchanged_h = [float(e) for e in states.heavy_hole.energies_eV] == holes_before
    unchanged_env = bool(np.array_equal(states.electron.envelopes, envelopes_before))
    widths = [s["fwhm_eV"] for s in spectra if s["fwhm_eV"] is not None]
    peaks = [s["peak_magnitude"] for s in spectra]

    # chi2 magnitudes are ~1e-16 in SI, so an absolute comparison would call
    # every spectrum identical. Differences are judged relative to the peak.
    reference_peak = max(peaks) if peaks else 0.0
    distinct = all(
        abs(a - b) / reference_peak > 1e-6
        for a, b in zip(peaks, peaks[1:])
    ) if reference_peak > 0 else False

    result.metrics = {
        "state_source": source,
        "electron_energies_eV": energies_before,
        "hole_energies_eV": holes_before,
        "two_photon_resonance_eV": float(0.5 * states.transition_eV()),
        "scan_window_eV": [float(photon_eV[0]), float(photon_eV[-1])],
        "spectra": spectra,
        "licensed_solver_calls": 0,
        "relative_peak_spread": (
            (max(peaks) - min(peaks)) / reference_peak if reference_peak > 0 else None),
        "note": (
            "synthetic reference states exercise the analysis layer only; they "
            "are never used to make a claim about nextnano++"
        ) if source == "synthetic_reference_states" else "",
    }
    result.checks = {
        "state_energies_unchanged": unchanged_e and unchanged_h,
        "wavefunctions_unchanged": unchanged_env,
        "no_solver_call_required": True,
        "every_peak_interior_to_window": all(
            s["peak_is_interior_to_window"] for s in spectra),
        "linewidth_measurable_at_every_broadening": len(widths) == len(spectra),
        "linewidth_increases_with_broadening": (
            all(a < b for a, b in zip(widths, widths[1:]))
            if len(widths) == len(spectra) else False),
        "spectra_actually_differ": distinct,
    }
    _write(out_dir, "broadening_isolation.json", result.as_record())
    return result.finish()


# ---------------------------------------------------------------------------
# Experiment 8 -- mirror invariance (structural half)
# ---------------------------------------------------------------------------


def mirror_structural(
    cfg: Mapping[str, Any], refs: Sequence[refs17.ReferenceStructure], out_dir: Path,
) -> ExperimentResult:
    """Is the mirrored structure really the mirror image of the original?

    Before comparing physics, establish that the transformation is what it
    claims. This is the check that catches a left/right indexing error at the
    point where it is cheap to find.
    """

    result = ExperimentResult(
        name="mirror_structural",
        question="Does the mirror transformation reverse the structure exactly?",
        what_changed=["spatial ordering of the layers"],
        what_was_held_constant=[
            "layer thicknesses", "grading widths", "Al fraction", "mesh", "domain",
        ],
        expected_invariant=[
            "composition after mirroring coordinates", "integrated Al dose",
            "set of layer thicknesses",
        ],
        expected_to_change=["which well comes first", "which grade is where"],
    )

    rows = []
    for ref in refs:
        geometry = demo14.geometry_for(cfg, ref.parameters())
        original = demo14.build_grading(cfg, ref.parameters(), geometry)
        mirrored, _ = refs17.build_mirrored_profile(cfg, ref)

        # Compare original(z) against mirrored(L - z) on the continuous grid.
        xc = original.x_nm_continuous
        reflected = refs17.mirror_coordinate(xc, geometry.domain_nm)
        mirrored_at_reflected = np.interp(
            reflected[::-1], mirrored.x_nm_continuous,
            mirrored.al_fraction_continuous,
        )[::-1]
        residual = np.abs(original.al_fraction_continuous - mirrored_at_reflected)

        thick, thin = ref.well_widths_nm()
        # The peak of the CONTINUOUS profile is the physical quantity. The
        # mesh-sampled peak differs slightly between a structure and its mirror
        # because the grid is anchored at z = 0 and is not symmetric about the
        # barrier, so the peak falls at a different offset within its cell. That
        # is sampling, not asymmetry, and conflating the two would either hide a
        # real error or invent one.
        original_peak = _continuous_central_peak(original)
        mirrored_peak = _continuous_central_peak(mirrored)
        rows.append({
            "ref_id": ref.ref_id,
            "original_thick_well_nm": thick,
            "original_thin_well_nm": thin,
            "mirror_parameters": refs17.mirror_parameters(ref),
            "max_composition_difference_after_mirroring": float(np.max(residual)),
            "rms_composition_difference_after_mirroring": float(
                np.sqrt(np.mean(residual**2))),
            "original_dose_nm": float(np.trapezoid(
                original.al_fraction_continuous, xc)),
            "mirrored_dose_nm": float(np.trapezoid(
                mirrored.al_fraction_continuous, mirrored.x_nm_continuous)),
            "original_interfaces_nm": dict(original.request["interfaces_nm"]),
            "mirrored_interfaces_nm": dict(mirrored.request["interfaces_nm"]),
            "original_central_peak_continuous": original_peak,
            "mirrored_central_peak_continuous": mirrored_peak,
            "central_peak_difference_continuous": abs(original_peak - mirrored_peak),
            "original_central_peak_on_mesh": original.diagnostics[
                "realized_peak_al_fraction"],
            "mirrored_central_peak_on_mesh": mirrored.diagnostics[
                "realized_peak_al_fraction"],
            "central_peak_difference_on_mesh": abs(
                original.diagnostics["realized_peak_al_fraction"]
                - mirrored.diagnostics["realized_peak_al_fraction"]),
            "structure_is_actually_reversed": bool(abs(thick - thin) > 1e-9),
        })

    worst = max(r["max_composition_difference_after_mirroring"] for r in rows)
    worst_mesh_peak = max(r["central_peak_difference_on_mesh"] for r in rows)
    result.metrics = {
        "structures": rows,
        "mirror_definition": "z -> (domain_lo + domain_hi) - z",
        "mirror_construction": (
            "swap the thick and thin wells and swap the rise/fall grading widths; "
            "asymmetry_s cannot express this because Demo 14 bounds it to "
            "[0.30, 0.55] and the reversal needs -s"
        ),
        "max_composition_difference": worst,
        "max_mesh_sampled_central_peak_difference": worst_mesh_peak,
        "mesh_sampling_note": (
            "the mesh is anchored at z = 0 and is not symmetric about the "
            "barrier, so a structure and its mirror sample the composition peak "
            "at different offsets within a cell. The continuous profiles are "
            "exact mirrors; the mesh-sampled peaks differ by that sampling only."
        ),
    }
    result.checks = {
        "mirrored_composition_matches_reflected_original": worst <= 1e-9,
        "doses_agree": all(
            abs(r["original_dose_nm"] - r["mirrored_dose_nm"]) < 1e-6 for r in rows),
        "continuous_central_peaks_agree": all(
            r["central_peak_difference_continuous"] < 1e-12 for r in rows),
        "mesh_sampled_peaks_agree_to_sampling_error": worst_mesh_peak < 1e-3,
        "at_least_one_genuinely_asymmetric_structure": any(
            r["structure_is_actually_reversed"] for r in rows),
    }
    _write(out_dir, "mirror_structural.json", result.as_record())
    return result.finish()


def _continuous_central_peak(profile: grading14.CompositionProfile) -> float:
    """Peak Al fraction between the two wells, on the continuous grid."""

    interfaces = profile.request["interfaces_nm"]
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    xc = profile.x_nm_continuous
    inner = (xc >= z2) & (xc <= z3)
    if not np.any(inner):
        inner = (xc >= z2 - 0.5) & (xc <= z3 + 0.5)
    return float(np.max(profile.al_fraction_continuous[inner]))

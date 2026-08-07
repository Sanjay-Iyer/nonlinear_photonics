"""Demo 17 solve orchestration: decks in, audited nextnano++ output out.

Two responsibilities beyond calling the solver.

**Deck transforms.** Demo 14's production template has no electric field, and
adding one to it would change what the production campaign computes. Demo 17
therefore renders through ``demo14.render_deck`` exactly like the campaign does
and then applies a narrow, auditable transform to the resulting text. The
transform returns the inserted block alongside the deck, and
:func:`verify_transform_is_additive` proves the rest of the deck is byte-identical
-- so "geometry and composition are unchanged" is demonstrated rather than
asserted. Field decks are an *independent capability demonstration*, not part of
the Demo 14 production model.

**Not solving the same thing twice.** Licensed solver time is the scarce
resource, and several experiments share structures: REF01 at 0.05 nm is both the
mesh-convergence midpoint and the core-physics baseline. :class:`SolveCache` keys
completed runs by the SHA-256 of the deck plus its imported profile, so a deck
that has already been solved in this run is reused. The cache is keyed by content,
not by name, so two experiments asking for the same physics get one solve and a
deck that differs by one character gets its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
import shutil
from typing import Any, Mapping

import quantum1d
import runlog14
import solver14

#: Measured on nextnano++ 3.0.0 (Demo 5, home laptop, 2026-07-30), not assumed.
FIELD_SIGN_CONVENTION = (
    "poisson{ electric_field{ direction = [1,0,0] strength = S } } with S in V/m. "
    "For S > 0 the electrostatic potential DECREASES with increasing x and the "
    "conduction band edge RISES with increasing x, so electrons are pushed "
    "towards small x. Consistent with Ec = -e*phi + const. The imposed tilt "
    "survives only because run{} contains no poisson step; with run{ poisson{} } "
    "the solver replaces it with the contact-pinned solution."
)

#: Anchor the field block is inserted before. Present in the Demo 14 template.
_QUANTUM_ANCHOR = re.compile(r"^quantum\{", re.MULTILINE)


class Solve17Error(RuntimeError):
    """A solve could not be set up or its result could not be trusted."""


# ---------------------------------------------------------------------------
# Deck transforms
# ---------------------------------------------------------------------------


def electric_field_block(field_kV_cm: float) -> str:
    """The ``poisson{}`` block imposing a uniform field, in Demo 5's grammar."""

    volts_per_metre = quantum1d.kv_per_cm_to_volts_per_metre(float(field_kV_cm))
    return (
        "poisson{\n"
        "    electric_field{\n"
        "        direction = [1, 0, 0]\n"
        f"        strength  = {volts_per_metre:.6e}   # V/m; {field_kV_cm:+g} kV/cm\n"
        "    }\n"
        "    output_potential{}\n"
        "    output_electric_field{}\n"
        "}\n\n"
    )


def with_electric_field(deck_text: str, field_kV_cm: float) -> tuple[str, dict[str, Any]]:
    """Insert a uniform-field block ahead of ``quantum{``.

    A zero field is a genuine no-op: the deck is returned unchanged rather than
    carrying a ``strength = 0`` block, so the zero-field arm of the experiment is
    literally the production deck and the comparison has a real control.
    """

    if float(field_kV_cm) == 0.0:
        return deck_text, {
            "transform": "none",
            "electric_field_kV_cm": 0.0,
            "deck_unchanged": True,
            "note": "zero field is the unmodified production deck",
        }
    match = _QUANTUM_ANCHOR.search(deck_text)
    if match is None:
        raise Solve17Error(
            "no 'quantum{' anchor in the rendered deck; the field transform "
            "cannot place its block without one"
        )
    block = electric_field_block(field_kV_cm)
    transformed = deck_text[: match.start()] + block + deck_text[match.start():]
    return transformed, {
        "transform": "insert_poisson_electric_field",
        "electric_field_kV_cm": float(field_kV_cm),
        "electric_field_V_per_m": quantum1d.kv_per_cm_to_volts_per_metre(
            float(field_kV_cm)),
        "inserted_block": block,
        "insertion_offset": int(match.start()),
        "sign_convention": FIELD_SIGN_CONVENTION,
        "deck_unchanged": False,
        "classification": (
            "independent capability demonstration; the Demo 14 production model "
            "is unstrained and field-free"
        ),
    }


def verify_transform_is_additive(
    original: str, transformed: str, inserted: str
) -> dict[str, Any]:
    """Prove the transform only inserted text.

    Removing the inserted block from the transformed deck must give back the
    original byte for byte. If it does not, the transform changed something it
    did not declare and every "composition is unchanged" claim downstream is
    unsupported.
    """

    if not inserted:
        identical = original == transformed
        return {
            "additive": identical,
            "recovered_original": identical,
            "removed_block_length": 0,
        }
    index = transformed.find(inserted)
    recovered = (
        transformed[:index] + transformed[index + len(inserted):]
        if index >= 0 else None
    )
    return {
        "additive": bool(recovered == original),
        "recovered_original": bool(recovered == original),
        "removed_block_length": len(inserted),
        "block_found_at": index,
        "original_length": len(original),
        "transformed_length": len(transformed),
    }


# ---------------------------------------------------------------------------
# Solve requests and results
# ---------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SolveRequest:
    """One deck to run, with everything needed to identify it."""

    solve_id: str
    deck_text: str
    datafile: str
    region: str
    import_name: str = "al_profile"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Content hash of the deck and its imported profile together.

        The datafile has to be part of the key: two decks can be textually
        identical and describe different structures when the imported table
        differs, which is exactly the case for every non-linear family.
        """

        return _sha256_text(self.deck_text + "\x00" + self.datafile)


@dataclass
class SolveResult:
    """A completed (or failed) solver invocation and where its output lives."""

    solve_id: str
    fingerprint: str
    raw_dir: Path
    work_dir: Path
    invocation: dict[str, Any]
    integrity: dict[str, Any]
    status: str
    reused: bool = False
    failure_reason: str | None = None

    @property
    def usable(self) -> bool:
        return self.status == "completed" and bool(
            self.integrity.get("may_be_used_for_physics"))

    def as_record(self) -> dict[str, Any]:
        return {
            "solve_id": self.solve_id,
            "fingerprint": self.fingerprint,
            "raw_output_dir": str(self.raw_dir),
            "work_dir": str(self.work_dir),
            "status": self.status,
            "reused_existing_solve": self.reused,
            "usable_for_physics": self.usable,
            "invocation": self.invocation,
            "integrity": self.integrity,
            "failure_reason": self.failure_reason,
        }


class SolveCache:
    """Content-keyed store of completed solves for one Demo 17 run."""

    def __init__(self) -> None:
        self._by_fingerprint: dict[str, SolveResult] = {}
        self.solver_calls = 0
        self.cache_hits = 0

    def get(self, fingerprint: str) -> SolveResult | None:
        return self._by_fingerprint.get(fingerprint)

    def put(self, result: SolveResult) -> None:
        self._by_fingerprint[result.fingerprint] = result

    def as_record(self) -> dict[str, Any]:
        return {
            "licensed_solver_calls": self.solver_calls,
            "cache_hits_avoiding_a_solve": self.cache_hits,
            "distinct_decks": len(self._by_fingerprint),
            "solves": {k: v.solve_id for k, v in self._by_fingerprint.items()},
        }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverEnvironment:
    """Where nextnano++ lives on this machine."""

    executable: Path | None
    database: Path | None
    license_path: Path | None
    threads: int = 1
    timeout_seconds: float = 3600.0
    run_solver: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "executable": str(self.executable) if self.executable else None,
            "executable_sha256": (
                runlog14.sha256_file(self.executable) if self.executable else None),
            "database": str(self.database) if self.database else None,
            "database_sha256": (
                runlog14.sha256_file(self.database) if self.database else None),
            "license_configured": self.license_path is not None,
            "threads": self.threads,
            "timeout_seconds": self.timeout_seconds,
            "run_solver": self.run_solver,
        }


def environment_from_machine(
    machine: Any | None, cfg: Mapping[str, Any] | None = None
) -> SolverEnvironment:
    """Resolve the solver environment from the shared machine config.

    The timeout is a scientific-configuration setting and comes from Demo 14's
    ``demo.yaml``; the paths and the run_solver decision are machine-local.
    """

    timeout = 3600.0
    threads = 1
    if cfg is not None:
        timeout = float(cfg["nextnano"].get("solver_timeout_seconds", timeout))
        threads = int(cfg["nextnano"].get("threads", threads))
    if machine is None:
        return SolverEnvironment(
            None, None, None, threads=threads, timeout_seconds=timeout,
            run_solver=False,
        )
    executable = getattr(machine, "executable", None)
    database = getattr(machine, "database", None)
    license_path = getattr(machine, "license", None)
    return SolverEnvironment(
        executable=Path(executable) if executable else None,
        database=Path(database) if database else None,
        license_path=Path(license_path) if license_path else None,
        threads=int(getattr(machine, "threads", threads) or threads),
        timeout_seconds=timeout,
        run_solver=bool(getattr(machine, "run_solver", False)),
    )


def execute(
    request: SolveRequest,
    environment: SolverEnvironment,
    work_dir: Path,
    cache: SolveCache,
    *,
    expected_files: tuple[str, ...] = ("bandedges.dat", "alloy_composition.dat"),
) -> SolveResult:
    """Run one deck, or return the cached result of an identical one.

    Output is written into a directory this function creates and clears first. A
    stale directory is the mechanism by which a failed solve returns the previous
    run's physics, so the cleanup is not housekeeping -- it is what makes the
    staleness check in ``measure17.run_integrity`` meaningful.
    """

    import measure17

    cached = cache.get(request.fingerprint)
    if cached is not None and cached.usable:
        cache.cache_hits += 1
        reused = SolveResult(
            solve_id=request.solve_id, fingerprint=cached.fingerprint,
            raw_dir=cached.raw_dir, work_dir=cached.work_dir,
            invocation=cached.invocation, integrity=cached.integrity,
            status=cached.status, reused=True,
        )
        return reused

    if environment.executable is None or not environment.run_solver:
        return SolveResult(
            solve_id=request.solve_id, fingerprint=request.fingerprint,
            raw_dir=work_dir / "output", work_dir=work_dir,
            invocation={}, integrity={"may_be_used_for_physics": False},
            status="not_run",
            failure_reason=(
                "no licensed nextnano++ available on this machine; Demo 17 does "
                "not fabricate solver output"
            ),
        )

    work_dir = Path(work_dir)
    deck_dir = work_dir / "nextnano_input"
    output_dir = work_dir / "output"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    deck_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    deck_path = deck_dir / "case.in"
    runlog14.write_text_atomic(deck_path, request.deck_text)
    imported: dict[str, Path] = {}
    if request.datafile:
        profile_path = deck_dir / f"{request.import_name}.dat"
        runlog14.write_text_atomic(profile_path, request.datafile)
        imported[request.import_name] = profile_path

    started = runlog14.utc_now()
    cache.solver_calls += 1
    try:
        invocation = solver14.execute_real(
            executable=environment.executable,
            database=environment.database,
            license_path=environment.license_path,
            deck=deck_path,
            output_dir=output_dir,
            threads=environment.threads,
            timeout_seconds=environment.timeout_seconds,
            imported_files=imported,
            logs_dir=work_dir / "logs",
        )
        record = invocation.as_record()
        return_code = invocation.return_code
    except (solver14.SolverTimeout, solver14.SolverTechnicalFailure) as exc:
        result = SolveResult(
            solve_id=request.solve_id, fingerprint=request.fingerprint,
            raw_dir=output_dir, work_dir=work_dir, invocation={},
            integrity={"may_be_used_for_physics": False},
            status="solver_failed", failure_reason=f"{type(exc).__name__}: {exc}",
        )
        # Artifacts are deliberately left in place: a failed licensed solve is
        # the most expensive thing in this demo to reproduce.
        runlog14.write_json_atomic(work_dir / "solve_result.json", result.as_record())
        return result

    integrity = measure17.run_integrity(
        output_dir, return_code=return_code, started_utc=started,
        expected_files=expected_files,
    )
    status = "completed" if integrity["may_be_used_for_physics"] else "unusable"
    result = SolveResult(
        solve_id=request.solve_id, fingerprint=request.fingerprint,
        raw_dir=output_dir, work_dir=work_dir, invocation=record,
        integrity=integrity, status=status,
        failure_reason=(
            None if status == "completed"
            else f"run integrity failed: {integrity}"
        ),
    )
    runlog14.write_json_atomic(work_dir / "solve_result.json", result.as_record())
    if result.usable:
        cache.put(result)
    return result


def build_request(
    solve_id: str, resolved: Any, *, field_kV_cm: float = 0.0,
    region: str | None = None,
) -> tuple[SolveRequest, dict[str, Any]]:
    """A solve request from a resolved variant, with any deck transform applied."""

    deck, transform = with_electric_field(resolved.deck, field_kV_cm)
    audit = verify_transform_is_additive(
        resolved.deck, deck, transform.get("inserted_block", "")
    )
    if not audit["additive"]:
        raise Solve17Error(
            f"{solve_id}: the field transform did not merely insert text; "
            "composition-unchanged claims would be unsupported"
        )
    request = SolveRequest(
        solve_id=solve_id,
        deck_text=deck,
        datafile=str(resolved.blocks.get("datafile", "")),
        region=region or str(resolved.cfg["nextnano"]["quantum_region_name"]),
        import_name=str(resolved.cfg["grading"].get("import_name", "al_profile")),
        metadata={"variant_id": resolved.variant.variant_id},
    )
    return request, {"deck_transform": transform, "transform_audit": audit}

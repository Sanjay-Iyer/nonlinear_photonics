"""Frozen 300 K pilot reference and temperature-only 8-band acquisition checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np

from . import decks, parse_nextnano as io, run_debug

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "config/29b_reference.json"


def reference() -> tuple[dict, str]:
    record = json.loads(REFERENCE.read_text(encoding="utf-8"))
    deck_path = ROOT / record["reference_deck"]
    raw = deck_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record["reference_deck_sha256"]:
        raise ValueError("Frozen 300 K pilot deck differs from its recorded SHA-256")
    return record, raw.decode("utf-8")


def _temperature_line(deck: str, temperature: int) -> str:
    matches = list(re.finditer(r"(?m)^(\s*temperature\s*=\s*)300(\s*)$", deck))
    if len(matches) != 1:
        raise ValueError("Frozen reference must have exactly one 300 K temperature line")
    return deck[:matches[0].start()] + matches[0].group(1) + str(temperature) + matches[0].group(2) + deck[matches[0].end():]


def check_decks(reference_run: Path | None = None) -> dict:
    """Prove exact text equality after changing only the temperature assignment."""
    from .acquisition import config, job_decks
    record, frozen = reference()
    rendered = {}
    for temperature in (100, 300, 500):
        deck = job_decks(temperature, config(), temperature_full8=True)["kp8"]
        if deck != _temperature_line(frozen, temperature):
            raise ValueError(f"{temperature} K 29B deck differs from executed 300 K pilot beyond temperature")
        if decks.without_temperature(deck) != decks.without_temperature(frozen):
            raise ValueError(f"{temperature} K 29B deck token comparison failed")
        rendered[str(temperature)] = {
            "temperature_K": temperature, "deck_sha256": hashlib.sha256(deck.encode("utf-8")).hexdigest(),
            "single_changed_assignment": f"temperature = {temperature}",
            "otherwise_byte_identical_to_frozen_300K_deck": True,
        }
    raw_verified = False
    if reference_run is not None:
        root = Path(reference_run)
        metadata = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
        actual = (root / "decks/kp8.in").read_bytes()
        grids = sorted((root / "kp8").rglob("k_points.txt"))
        grid_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in grids}
        if (metadata.get("temperature_K") != 300 or metadata.get("run_id") != record["reference_run_id"] or
                metadata.get("jobs", {}).get("kp8", {}).get("status") != "PASS" or
                metadata["jobs"]["kp8"].get("deck_sha256") != record["reference_deck_sha256"] or
                hashlib.sha256(actual).hexdigest() != record["reference_deck_sha256"] or
                not grids or grid_hashes != {record["reference_k_points_sha256"]} or
                metadata.get("executable_sha256") != record["reference_executable_sha256"] or
                metadata.get("database_sha256") != record["reference_database_sha256"]):
            raise ValueError("Provided 300 K solver directory is not the frozen successful pilot")
        raw_verified = True
    return {"status": "PASS", "model": "29B electronic structure only; no full-8-band chi2",
            "reference_run_id": record["reference_run_id"],
            "reference_deck_sha256": record["reference_deck_sha256"],
            "reference_raw_verified_here": raw_verified,
            "only_intended_deck_difference": "global solver temperature",
            "kmax_pi_over_a": record["kmax_pi_over_a"],
            "dispersion_points": record["dispersion_points"],
            "finite_k_integration": record["finite_k_integration"], "decks": rendered}


def check_solver(executable: Path, database: Path) -> None:
    record, _ = reference()
    for name, path in (("executable", executable), ("database", database)):
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if actual != record[f"reference_{name}_sha256"]:
            raise ValueError(f"29B {name} differs from the successful 300 K reference; stop for review")


def validate_run(root: Path, temperature: int) -> dict:
    """Read all exported states and native tables before accepting a 29B raw package."""
    if temperature not in (100, 300, 500):
        raise ValueError("Expected the 100/500 K acquisition or frozen 300 K reference")
    record, _ = reference()
    metadata = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
    deck_bytes = (root / "decks/kp8.in").read_bytes()
    expected_hash = check_decks()["decks"][str(temperature)]["deck_sha256"]
    expected_kind = "finite_k" if temperature == 300 else "temperature_full8_finite_k"
    if (metadata.get("temperature_K") != temperature or
            metadata.get("pilot_kind") != expected_kind or
            metadata.get("jobs", {}).get("kp8", {}).get("status") != "PASS" or
            hashlib.sha256(deck_bytes).hexdigest() != expected_hash or
            metadata["jobs"]["kp8"].get("deck_sha256") != expected_hash or
            metadata.get("executable_sha256") != record["reference_executable_sha256"] or
            metadata.get("database_sha256") != record["reference_database_sha256"]):
        raise ValueError("29B run metadata/deck/solver differs from frozen acquisition")
    report = run_debug.scan_output(root)
    grid = report["integration_grid"]
    grid_path = Path(grid.get("file") or "")
    if (report["dispersion"]["points"] != 301 or
            abs(report["dispersion"]["k_max_per_nm"] - record["k_max_per_nm"]) > 5e-10 or
            not grid_path.is_file() or
            hashlib.sha256(grid_path.read_bytes()).hexdigest() != record["reference_k_points_sha256"] or
            grid.get("points") != report["complete_state_frames"] or
            grid.get("complete_target_path_frames", 0) < 3 or
            not report["k0_exists"] or report["duplicate_frames"] or
            report["relevant_files_ignored_total"]):
        raise ValueError("29B dispersion, k-grid or complete state frames failed reference checks")
    frames = [row for row in report["frames"] if row["composition_files"]]
    if len(frames) != grid["points"]:
        raise ValueError("29B frame inventory differs from integration grid")
    folders = {row["id"]: row["state_folder"] for row in grid["rows"]}
    native_root = root / "kp8/kp8/bias_00000/Quantum/acqw/kp8_kp8"
    checked_envelopes = checked_tables = 0
    for frame in frames:
        folder = Path(folders[frame["id"]])
        if not frame["state_component_complete"]:
            raise ValueError(f"Incomplete 8-component spinor frame: {frame['id']}")
        energies = io.read_energy_spectrum(folder / "energy_spectrum.dat")
        composition = io.read_composition(folder / "spinor_composition_CbHhLhSo.dat")
        if len(energies) != 14 or any(len(composition[c]) != 14 for c in io.KP8_COMPONENTS):
            raise ValueError(f"Wrong state/composition count: {frame['id']}")
        for state in range(1, 15):
            for component in io.KP8_COMPONENTS:
                _, table = io.read_table(folder / f"envelope_{state:04d}_{component}.dat")
                if table.shape[1] != 3:
                    raise ValueError(f"Noncomplex spinor table: {frame['id']} state {state} {component}")
                checked_envelopes += 1
        for name in ("dipole_moment_matrix_elements_growth_z.txt",
                     "momentum_matrix_elements_growth_z.txt",
                     "momentum_matrix_elements_inplane_y.txt"):
            _, table = io.read_table(native_root / frame["id"] / name)
            if table.shape != (196, 6):
                raise ValueError(f"Wrong native matrix shape: {frame['id']} {name}")
            checked_tables += 1
    return {"status": "PASS", "temperature_K": temperature, "dispersion_points": 301,
            "integration_frames": grid["points"],
            "complete_target_path_frames": grid["complete_target_path_frames"],
            "complex_component_files_checked": checked_envelopes,
            "native_matrix_tables_checked": checked_tables,
            "k_points_sha256": record["reference_k_points_sha256"],
            "reference_run_id": record["reference_run_id"],
            "optical_chi2": "UNRESOLVED; electronic structure only"}

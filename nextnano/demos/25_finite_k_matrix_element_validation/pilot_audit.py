"""Audit what a Demo 25 pilot variant actually wrote to disk.

The gate is deliberately filesystem-based. A zero exit status from nextnano++
does not prove that finite-k states were produced - Demo 23 exited cleanly and
still emitted only ``k00000`` - so every claim here is made by counting files
and reading their contents, never by trusting the solver's return code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


K_INDEX = re.compile(r"_k(\d{5})", re.IGNORECASE)
K_DIR = re.compile(r"^k(\d{3,5})$", re.IGNORECASE)


class FiniteKDataUnavailable(RuntimeError):
    """Raised when the pilot proves finite-k reconstruction is not possible."""


@dataclass(frozen=True)
class KPointEvidence:
    k_index: int
    energies: bool
    envelopes: bool
    spinor: bool
    character: bool
    probabilities: bool
    oscillator: bool
    momentum: bool
    dipole: bool
    transition: bool
    envelope_files: int
    sample_path: str

    @property
    def usable_for_equation2(self) -> bool:
        """Equation 2 needs envelopes at this k; everything else is corroboration."""
        return self.energies and self.envelopes

    def as_row(self, variant: str) -> dict[str, object]:
        def mark(flag: bool) -> str:
            return "YES" if flag else "no"
        return {
            "variant": variant, "k": self.k_index,
            "energy output?": mark(self.energies),
            "wavefunction output?": mark(self.envelopes),
            "spinor output?": mark(self.spinor),
            "CB/HH/LH/SO character?": mark(self.character),
            "probability density?": mark(self.probabilities),
            "oscillator strength?": mark(self.oscillator),
            "momentum matrix?": mark(self.momentum),
            "dipole matrix?": mark(self.dipole),
            "transition energies?": mark(self.transition),
            "envelope files": self.envelope_files,
            "file path": self.sample_path,
            "parser tested?": mark(self.envelopes),
            "usable for Equation 2?": mark(self.usable_for_equation2),
        }


def _k_indices_from_names(paths: Iterable[Path]) -> dict[int, list[Path]]:
    found: dict[int, list[Path]] = {}
    for path in paths:
        match = K_INDEX.search(path.name)
        if match:
            found.setdefault(int(match.group(1)), []).append(path)
            continue
        for part in path.parts:
            sub = K_DIR.match(part)
            if sub:
                found.setdefault(int(sub.group(1)), []).append(path)
                break
    return found


def audit_case(case_dir: Path, variant: str) -> tuple[list[KPointEvidence], dict[str, Any]]:
    """Enumerate every k point that left evidence on disk under ``case_dir``."""
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        raise FileNotFoundError(f"pilot output directory is missing: {case_dir}")
    files = [p for p in case_dir.rglob("*") if p.is_file()]
    by_k = _k_indices_from_names(files)
    evidence: list[KPointEvidence] = []
    for index in sorted(by_k):
        names = [p.name.lower() for p in by_k[index]]
        joined = " ".join(names)
        envelope_files = sum(1 for n in names if n.startswith("envelope"))
        sample = next((str(p) for p in by_k[index] if p.name.lower().startswith("envelope")),
                      str(by_k[index][0]))
        evidence.append(KPointEvidence(
            k_index=index,
            energies=any("energy_spectrum" in n or "dispersion" in n for n in names),
            envelopes=envelope_files > 0,
            spinor=any("spinor" in n for n in names),
            character=any("cb_hh_lh_so" in n or "_cb" in n or "spinor_composition" in n for n in names),
            probabilities=any("probabilit" in n for n in names),
            oscillator="oscillator" in joined,
            momentum="momentum" in joined,
            dipole="dipole" in joined,
            transition="transition_energies" in joined,
            envelope_files=envelope_files,
            sample_path=sample,
        ))
    summary = {
        "variant": variant,
        "case_dir": str(case_dir),
        "total_files": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
        "k_points_with_evidence": len(evidence),
        "k_points_usable": sum(1 for e in evidence if e.usable_for_equation2),
        "finite_k_state_output": bool(sum(1 for e in evidence if e.usable_for_equation2) > 1),
        "k_indices": sorted(by_k),
    }
    return evidence, summary


def k_vectors_for_case(case_dir: Path) -> np.ndarray | None:
    """Recover the explicit k vectors, without which per-k data cannot be placed.

    Returns ``None`` when no k-vector file exists; the caller must then treat
    the finite-k data as unusable rather than guessing a k grid.
    """
    for pattern in ("**/kVectors*.dat", "**/k_vectors*.dat", "**/kvectors*.dat"):
        for path in sorted(Path(case_dir).glob(pattern)):
            try:
                data = np.loadtxt(path, skiprows=1)
            except (OSError, ValueError):
                continue
            if data.size:
                return np.atleast_2d(data)
    return None


def gate(summaries: Iterable[Mapping[str, Any]], *,
         require_k_vectors: bool = True) -> dict[str, Any]:
    """Decide whether the production run may launch.

    PASS requires at least one variant that produced usable state output at
    more than one k point. Anything else is a documented FAIL with the reason.
    """
    rows = list(summaries)
    passing = [r for r in rows
               if bool(r.get("finite_k_state_output"))
               and (not require_k_vectors or bool(r.get("k_vectors_found")))]
    if not passing:
        multi = [r for r in rows if int(r.get("k_points_usable", 0)) > 1]
        if multi and require_k_vectors:
            reason = ("finite-k state output was produced, but no k-vector file was found, "
                      "so per-k data cannot be associated with a k value")
        else:
            reason = ("no pilot variant produced usable state output at more than one k point; "
                      "every variant behaved like Demo 23 and wrote only k00000")
        return {"status": "FAIL", "reason": reason, "recommended_variant": None,
                "variants": rows}
    best = max(passing, key=lambda r: (int(r["k_points_usable"]), -int(r["total_bytes"])))
    return {
        "status": "PASS",
        "reason": (f"variant {best['variant']} produced usable state output at "
                   f"{best['k_points_usable']} k points with identifiable k vectors"),
        "recommended_variant": best["variant"],
        "variants": rows,
    }


def cost_model(summary: Mapping[str, Any], seconds: float) -> dict[str, float]:
    """Per-k cost measured from the pilot, used to size the production run."""
    usable = max(int(summary.get("k_points_usable", 0)), 1)
    return {
        "measured_seconds": float(seconds),
        "k_points_usable": float(usable),
        "seconds_per_k": float(seconds) / usable,
        "bytes_per_k": float(summary.get("total_bytes", 0)) / usable,
        "files_per_k": float(summary.get("total_files", 0)) / usable,
    }


def project(cost: Mapping[str, float], k_points: int) -> dict[str, float]:
    """Project a production run of ``k_points`` from the measured pilot cost."""
    points = int(k_points)
    return {
        "k_points": float(points),
        "projected_seconds": cost["seconds_per_k"] * points,
        "projected_hours": cost["seconds_per_k"] * points / 3600.0,
        "projected_bytes": cost["bytes_per_k"] * points,
        "projected_gb": cost["bytes_per_k"] * points / 1e9,
        "projected_files": cost["files_per_k"] * points,
    }


def recommend_k_points(cost: Mapping[str, float], *, requested: int,
                       max_hours: float, max_gb: float) -> dict[str, Any]:
    """Largest k count within the time and disk budget, and why."""
    full = project(cost, requested)
    if full["projected_hours"] <= max_hours and full["projected_gb"] <= max_gb:
        return {"recommended_k_points": int(requested), "within_budget": True,
                "reason": "the requested grid fits the configured time and disk budget",
                **{f"requested_{k}": v for k, v in full.items()}}
    by_time = int(max_hours * 3600.0 / cost["seconds_per_k"]) if cost["seconds_per_k"] > 0 else requested
    by_disk = int(max_gb * 1e9 / cost["bytes_per_k"]) if cost["bytes_per_k"] > 0 else requested
    limit = max(5, min(requested, by_time, by_disk))
    binding = "time" if by_time <= by_disk else "disk"
    return {
        "recommended_k_points": limit, "within_budget": False,
        "reason": (f"the requested {requested}-point grid would need "
                   f"{full['projected_hours']:.1f} h and {full['projected_gb']:.1f} GB; "
                   f"{binding} is the binding budget, so the matrix-element grid is "
                   f"reduced to {limit} points and interpolated onto the energy grid"),
        **{f"requested_{k}": v for k, v in full.items()},
    }

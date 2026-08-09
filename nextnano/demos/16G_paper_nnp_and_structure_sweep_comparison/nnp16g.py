"""Handling for the two supplied ``.nnp`` files. The originals are never edited.

Two things this module refuses to do:

* modify a source file in place -- a verbatim copy is made inside the run
  directory and both the source and the copy are SHA256-hashed, so a later
  reader can prove what was solved;
* guess what the file contains -- its variables, its quantum models and its
  output requests are read out and recorded, and anything unrecognised is
  reported rather than assumed.

Reading them turned up two facts the comparison depends on:

**Grading.** ``$GRADE_WIDTH = 0.7`` produces
``ternary_linear{ alloy_x = [0.55, 0.0]  x = [$QW1_min - 0.7, $QW1_min] }`` --
a *full* 0.7 nm ramp sitting *outside* the well. Demo 16E's "0.70 nm grade" is a
10-90 width whose full ramp is 0.875 nm and straddles the interface. See
:mod:`grading16g`.

**Hole model.** Both files solve holes with ``kp_6band{ num_ev = 10 }``, not the
one-band heavy-hole model Demos 16E and 16F use. That is a genuine physics
difference, not a formatting one, and it is recorded on every Group 1 case so no
chi2 comparison silently spans two hole models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
import shutil
from typing import Any, Mapping

#: ``$NAME = value`` at the start of a line, value up to the first comment.
_VARIABLE = re.compile(r"^\s*\$(\w+)\s*=\s*([^#\n]+)", re.MULTILINE)
_TERNARY_LINEAR = re.compile(r"ternary_linear\s*\{", re.IGNORECASE)
_TERNARY_IMPORT = re.compile(r"ternary_import\s*\{", re.IGNORECASE)
_TERNARY_CONSTANT = re.compile(r"ternary_constant\s*\{", re.IGNORECASE)

#: Blocks whose presence changes what the file computes.
_FEATURES = {
    "kp_6band": re.compile(r"^\s*kp_6band\s*\{", re.MULTILINE),
    "kp_8band": re.compile(r"^\s*kp_8band\s*\{", re.MULTILINE),
    "bulk_dispersion": re.compile(r"^\s*bulk_dispersion\s*\{", re.MULTILINE),
    "output_states": re.compile(r"^\s*output_states\s*\{", re.MULTILINE),
    "envelopes_requested": re.compile(r"envelopes\s*=\s*yes"),
    "probabilities_requested": re.compile(r"probabilities\s*=\s*yes"),
    "poisson": re.compile(r"^\s*poisson\s*\{", re.MULTILINE),
}

#: Structural variables the comparison reports. Absent ones are recorded as
#: absent rather than defaulted.
STRUCTURE_VARIABLES = (
    "QW_WIDTH1", "QW_WIDTH2", "QW_SEPARATION", "GRADE_WIDTH", "middle",
)


class Nnp16GError(RuntimeError):
    """A supplied ``.nnp`` file that cannot be used as given."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class NnpInspection:
    """Everything read out of a supplied file, without changing it."""

    source_path: Path
    sha256_source: str
    bytes_source: int
    variables: dict[str, str]
    numeric_variables: dict[str, float]
    features: dict[str, bool]
    representation_counts: dict[str, int]
    hole_model: str
    computes_chi2: bool
    warnings: list[str] = field(default_factory=list)

    def as_record(self) -> dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "sha256_source": self.sha256_source,
            "bytes_source": self.bytes_source,
            "variables": dict(self.variables),
            "numeric_variables": dict(self.numeric_variables),
            "features": dict(self.features),
            "representation_counts": dict(self.representation_counts),
            "hole_model": self.hole_model,
            "computes_chi2": self.computes_chi2,
            "warnings": list(self.warnings),
        }


def inspect(path: Path) -> NnpInspection:
    """Read a supplied file and report what it is. Never writes."""

    path = Path(path)
    if not path.is_file():
        raise Nnp16GError(f"supplied .nnp file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")

    variables = {
        name: value.strip() for name, value in _VARIABLE.findall(text)
    }
    numeric: dict[str, float] = {}
    for name, value in variables.items():
        try:
            numeric[name] = float(value)
        except ValueError:
            # Derived expressions such as "$middle - $QW_SEPARATION / 2" are
            # kept as text; nextnano++ evaluates them, this demo does not.
            continue

    features = {name: bool(pattern.search(text)) for name, pattern in _FEATURES.items()}
    counts = {
        "ternary_linear": len(_TERNARY_LINEAR.findall(text)),
        "ternary_import": len(_TERNARY_IMPORT.findall(text)),
        "ternary_constant": len(_TERNARY_CONSTANT.findall(text)),
    }
    if features["kp_8band"]:
        hole_model = "kp_8band"
    elif features["kp_6band"]:
        hole_model = "kp_6band"
    else:
        hole_model = "single_band_or_unspecified"

    warnings: list[str] = []
    if hole_model != "single_band_or_unspecified":
        warnings.append(
            f"holes are solved with {hole_model}; Demos 16E/16F use a one-band "
            "heavy-hole model. Any chi2 comparison across these groups spans two "
            "hole models and must say so."
        )
    if not features["envelopes_requested"]:
        warnings.append(
            "output_states does not request envelopes = yes; the chi2 evaluator "
            "needs signed envelopes and will have nothing to read"
        )
    missing = [name for name in STRUCTURE_VARIABLES if name not in variables]
    if missing:
        warnings.append(f"structural variables not found in the file: {missing}")

    return NnpInspection(
        source_path=path,
        sha256_source=sha256(path),
        bytes_source=path.stat().st_size,
        variables=variables,
        numeric_variables=numeric,
        features=features,
        representation_counts=counts,
        hole_model=hole_model,
        # Neither supplied file contains an optical/chi2 block; states are fed
        # into the Demo 16F evaluator instead, so all groups share one optical
        # calculation. Detected rather than assumed.
        computes_chi2=bool(re.search(r"\bchi2\b|\bsecond_harmonic\b", text, re.I)),
        warnings=warnings,
    )


def structure_summary(inspection: NnpInspection) -> dict[str, Any]:
    """The layer widths the file declares, in this demo's column names.

    Grading is reported through :mod:`grading16g` so a Group 1 row and a Group 2
    row mean the same thing by "grade".
    """

    import grading16g

    numeric = inspection.numeric_variables
    thick = numeric.get("QW_WIDTH1")
    thin = numeric.get("QW_WIDTH2")
    barrier = numeric.get("QW_SEPARATION")
    grade = numeric.get("GRADE_WIDTH")
    record: dict[str, Any] = {
        "thick_well_nm": thick,
        "thin_well_nm": thin,
        "barrier_nm": barrier,
        "left_grade_nm": grade,
        "right_grade_nm": grade,
        "total_well_nm": None if thick is None or thin is None else thick + thin,
        "asymmetry_s": (
            None if thick is None or thin is None or (thick + thin) == 0
            else (thick - thin) / (thick + thin)
        ),
        "representation": (
            "native_ternary_linear"
            if inspection.representation_counts["ternary_linear"]
            else "abrupt_or_constant"
        ),
        "hole_model": inspection.hole_model,
    }
    if grade is not None:
        widths = grading16g.describe(
            grade, definition="full_linear_ramp_outside_well"
        )
        record.update(widths.as_record("left"))
        record.update(widths.as_record("right"))
        record["grading_definition"] = widths.definition
    return record


def stage_copy(inspection: NnpInspection, case_input_dir: Path) -> dict[str, Any]:
    """Copy the source into the run directory verbatim and hash both ends.

    A copy rather than a symlink so the run directory is self-contained, and
    verbatim so ``modifications`` is genuinely empty. nextnano++ takes its output
    directory on the command line, so no edit is needed to control where results
    land -- which is why this demo can honestly claim the file was run as given.
    """

    case_input_dir = Path(case_input_dir)
    case_input_dir.mkdir(parents=True, exist_ok=True)
    destination = case_input_dir / inspection.source_path.name
    shutil.copy2(inspection.source_path, destination)
    digest = sha256(destination)
    identical = digest == inspection.sha256_source
    if not identical:  # pragma: no cover - a copy that changed bytes is a defect
        raise Nnp16GError(
            f"the staged copy of {inspection.source_path} does not match its "
            f"source hash ({digest} != {inspection.sha256_source})"
        )
    return {
        "source_path": str(inspection.source_path),
        "staged_path": str(destination),
        "sha256_source": inspection.sha256_source,
        "sha256_staged": digest,
        "byte_identical": identical,
        "modifications": [],
        "modification_note": (
            "none. The file is solved exactly as supplied; the output directory "
            "is set by the solver command line, not by editing the deck."
        ),
    }

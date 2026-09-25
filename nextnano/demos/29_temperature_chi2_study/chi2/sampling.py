"""Five-point sampling diagnostics for the 29A2 spinor-derived matrices."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator


BLOCKS = (("e1", "e2"), ("hh1", "hh2"), ("e1", "hh1"), ("e1", "hh2"),
          ("e2", "hh1"), ("e2", "hh2"))


def block_strength(matrix: np.ndarray, left: list[int], right: list[int]) -> float:
    """Basis-rotation invariant Frobenius magnitude per two-state block, in nm."""
    return float(np.linalg.norm(matrix[np.ix_(np.asarray(left)-1, np.asarray(right)-1)]) / 2)


def interpolation_diagnostics(k: np.ndarray, values: np.ndarray) -> dict:
    """Interior leave-one-out errors; endpoints are not extrapolation tests."""
    if len(k) < 5 or np.any(np.diff(k) <= 0) or not np.isfinite(values).all():
        raise ValueError("Need at least five finite, increasing sample points")
    residuals = []
    for i in range(1, len(k)-1):
        kept = np.arange(len(k)) != i
        linear = float(np.interp(k[i], k[kept], values[kept]))
        pchip = float(PchipInterpolator(k[kept], values[kept])(k[i]))
        scale = max(abs(float(values[i])), 0.05 * float(np.max(abs(values))), 1e-9)
        residuals.append({"held_out_k_per_nm": float(k[i]), "actual_nm": float(values[i]),
                          "linear_nm": linear, "pchip_nm": pchip,
                          "linear_abs_error_nm": abs(linear - float(values[i])),
                          "pchip_abs_error_nm": abs(pchip - float(values[i])),
                          "linear_relative_error": abs(linear - float(values[i])) / scale,
                          "pchip_relative_error": abs(pchip - float(values[i])) / scale})
    steps = np.diff(values)
    return {"values_nm": list(map(float, values)), "nonmonotonic": bool(np.any(steps > 0) and np.any(steps < 0)),
            "max_linear_relative_error": max(item["linear_relative_error"] for item in residuals),
            "max_pchip_relative_error": max(item["pchip_relative_error"] for item in residuals),
            "leave_one_out": residuals}


def analyze(analysis: Path, output: Path) -> dict:
    report = json.loads((analysis / "pilot_analysis.json").read_text(encoding="utf-8"))
    frames = report["frames"]
    k = np.asarray([f["ky_per_nm"] for f in frames], float)
    strengths = {"-".join(pair): [] for pair in BLOCKS}
    raw_phases = {"-".join(pair): [] for pair in BLOCKS}
    for frame in frames:
        with np.load(analysis / "matrix_blocks" / f"{frame['id']}.npz") as data:
            z = data["z_matrix_nm"]
        for left, right in BLOCKS:
            name = f"{left}-{right}"
            l = frame["labels"][left]["solver_states"]
            r = frame["labels"][right]["solver_states"]
            strengths[name].append(block_strength(z, l, r))
            element = z[l[0]-1, r[0]-1]
            raw_phases[name].append(None if abs(element) < 1e-6 else float(np.angle(element)))
    blocks = {name: interpolation_diagnostics(k, np.asarray(series)) for name, series in strengths.items()}
    for name, series in raw_phases.items():
        blocks[name]["representative_raw_phase_rad"] = series
    reasons = []
    if len(frames) < 8:
        reasons.append("Only five on-path spinor frames for a 301-point dispersion")
    if any(frame["labels"][label]["flag"] for frame in frames for label in ("e1", "e2", "hh1", "hh2")):
        reasons.append("At least one selected state has weak adjacent-k subspace overlap")
    if any(blocks[name]["max_linear_relative_error"] > .1 or
           blocks[name]["max_pchip_relative_error"] > .1 for name in ("e1-e2", "hh1-hh2")):
        reasons.append("Same-band matrix interpolation has >10% interior leave-one-out error")
    result = {"k_per_nm": list(map(float, k)), "blocks": blocks,
              "phase_note": "Raw complex-element phases are gauge dependent; do not interpolate them without phase/subspace alignment.",
              "interband_note": "Growth-position e-h blocks are not the unresolved interband Bloch optical operator.",
              "five_point_interpolation_accepted": not reasons,
              "reasons_for_dense_validation": reasons}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

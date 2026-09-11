"""Assemble Equation 2 inputs from a raw nextnano results root, per calculation mode.

Results-root layout (written by 01_run_nextnano.py, mirrored by cached_raw/):
    kp8/                         8-band k.p run (production; always required)
    singleband_case04_graded/    single-band Gamma/HH, 1 nm grading (historical modes)
    singleband_case00_abrupt/    single-band Gamma/HH, abrupt (historical cutoff mode)
    supplied/case00_abrupt_matrix_elements.json   processed fallback, if case00 raw absent

Modes
    kp8               PRODUCTION. Everything from the kp8 run (see kp8_states.py).
    demo26-baseline   Historical Demo 26 / Demo 23D chain, reproduced exactly: kp8 dispersion
                      shape, each band shifted to single-band case04 k=0 energies,
                      single-band case04 overlaps and z. Kept to validate the engine
                      against the saved historical spectrum.
    demo26-cutoff     Historical cutoff DIAGNOSTIC: anchored parabolas E0 + A k^2 fitted to
                      the baseline dispersion, extrapolated in Python beyond the solved k
                      range, with case00 (abrupt) matrices. Explicitly not production.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import numpy as np

from . import nextnano_io as io
from .kp8_states import load_kp8_inputs

MODES = ("kp8", "demo26-baseline", "demo26-cutoff")


def _single_band_matrices(root: Path) -> dict:
    sb = io.read_single_band(root)
    z, e, h = sb["z_nm"], sb["electron_env"], sb["hole_env"]
    if np.any(np.diff(sb["electron_eV"]) <= 0) or np.any(np.diff(sb["hole_eV"]) >= 0):
        raise io.RawDataError("expected electron energies ascending, valence energies descending")
    m = lambda a, b, pos=False: np.array([[np.trapezoid(a[:, i] * b[:, j] * (z if pos else 1), z)
                                           for j in range(2)] for i in range(2)])
    gram = max(float(np.max(np.abs(m(p, p) - np.eye(2)))) for p in (e, h))
    return {"anchors_eV": np.r_[sb["electron_eV"], sb["hole_eV"]], "overlap": m(e, h),
            "ze_nm": m(e, e, True), "zh_nm": m(h, h, True), "gram_error": gram,
            "envelope_grid_points": len(z)}


def _historical_dispersion(kp8_root: Path, anchors: np.ndarray) -> dict:
    """Original Demo 26 pair selection and alignment, operation order preserved."""
    spectrum = io.find_one(kp8_root, "kp8/energy_spectrum_k00000.dat")
    energy = io.read_energy_spectrum(spectrum)
    comp = io.read_composition(io.find_one(spectrum.parent, "spinor_composition_k00000_CbHhLhSo.dat"))
    k, disp, meta = io.read_dispersion(kp8_root)
    if len(energy) % 2 or not np.allclose(energy, disp[0], atol=1e-9, rtol=0):
        raise io.RawDataError("k=0 energies disagree with dispersion or do not form pairs")
    spin = np.column_stack([comp[c] for c in io.KP8_COMPONENTS])
    spin = spin / np.abs(spin).sum(axis=1)[:, None]
    pairs = np.arange(len(energy)).reshape(-1, 2)
    pair_energy = energy[pairs].mean(axis=1)
    character = spin[:, :2].sum(axis=1)[pairs].mean(axis=1)
    expected = anchors[:2, None] - anchors[None, 2:]
    best = None
    for e in itertools.combinations(np.flatnonzero(character >= .8), 2):
        e = sorted(e, key=lambda i: pair_energy[i])
        for h in itertools.combinations(np.flatnonzero(character <= .2), 2):
            h = sorted(h, key=lambda i: pair_energy[i], reverse=True)
            score = np.sqrt(np.mean((pair_energy[e, None] - pair_energy[None, h] - expected) ** 2))
            if best is None or score < best[0]:
                best = (score, e + h)
    if best is None:
        raise io.RawDataError("cannot classify electron and valence Kramers pairs")
    chosen = pairs[best[1]]
    raw = np.array([disp[:, pair].mean(axis=1) for pair in chosen])
    aligned = anchors[:, None] + raw - raw[:, 0, None]
    x = k * k
    curvature = np.array([np.dot(x, b - b[0]) / np.dot(x, x) for b in aligned])
    return {"k_per_nm": k, "electron_eV": aligned[:2], "valence_eV": aligned[2:],
            "energy_eV": aligned[:, 0], "curvature_eV_nm2": curvature,
            "kp8_pair_ids": (chosen + 1).tolist(), "dispersion": meta}


def available_modes(root: Path) -> dict[str, str]:
    root = Path(root)
    status = {m: "" for m in MODES}
    has_kp8 = io.find_optional(root / "kp8", "energy_spectrum_k00000.dat") is not None
    has_04 = (root / "singleband_case04_graded").is_dir()
    has_00 = (root / "singleband_case00_abrupt").is_dir() or (root / "supplied/case00_abrupt_matrix_elements.json").is_file()
    status["kp8"] = "available" if has_kp8 else "missing kp8/"
    status["demo26-baseline"] = "available" if has_kp8 and has_04 else "needs kp8/ and singleband_case04_graded/"
    status["demo26-cutoff"] = "available" if has_kp8 and has_04 and has_00 else "needs kp8/, case04 and case00 inputs"
    return status


def load_inputs(root: Path, mode: str) -> dict:
    root = Path(root)
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if mode == "kp8":
        return load_kp8_inputs(root / "kp8")
    base = _single_band_matrices(root / "singleband_case04_graded")
    result = _historical_dispersion(root / "kp8", base["anchors_eV"])
    matrices, supplied = base, []
    if mode == "demo26-cutoff":
        raw00 = root / "singleband_case00_abrupt"
        if raw00.is_dir():
            matrices = _single_band_matrices(raw00)
        else:
            path = root / "supplied/case00_abrupt_matrix_elements.json"
            matrices = json.loads(path.read_text())
            supplied.append({"file": path.relative_to(root).as_posix(), "reason": matrices.get("reason", "")})
    for key in ("overlap", "ze_nm", "zh_nm"):
        result[key] = np.asarray(matrices[key], float)
    result.update(model=mode, supplied_inputs=supplied,
                  state_ids={"electron": [1, 2], "valence": [1, 2], "kp8_pairs_for_dispersion": result["kp8_pair_ids"]},
                  single_band_gram_error=base["gram_error"], envelope_grid_points=base["envelope_grid_points"],
                  limitations=["Historical mixed-model chain (single-band matrices, kp8 dispersion shape)",
                               "Valence pair (3,4) selected by energy match is light-hole dominated",
                               "M(k)=M(0)"] + (["Parabolas extrapolated beyond the solved k range; case00 matrices with case04 energies"]
                                               if mode == "demo26-cutoff" else []))
    return result

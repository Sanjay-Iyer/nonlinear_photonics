"""One optical calculation for all three groups: Demo 16F's validated evaluator.

The supplied ``.nnp`` files solve quantum states and stop; the sweep and the
benchmark go through Demo 16E's production pipeline. If each group used its own
chi2 route the comparison would measure the routes, not the structures. So every
group's solved envelopes are fed into the *same* evaluator -- Demo 16F's
``variants16f.chi2_at``, under the conventions 16F was able to justify from a
cited source:

* ``N_z`` counted per quantum well, not per period (Methods Sec. 5.1);
* the zincblende Gamma->X zone edge at ``2 pi/a`` (X = (1,0,0) in units of
  ``2 pi/a`` for an FCC lattice);
* the disc k domain, integrated to one-tenth of that boundary.

Both k implementations are run -- the radial reduction and the independent
Cartesian quadrature -- because their agreement is the standing check that no
``2 pi``, spin factor or area normalisation has gone missing.

There is no scale factor here and none may be added. 16F's two unresolved
published ambiguities (the factor of 3 between Eq. 1 and Eq. 2 as printed, and
the unstated heavy-hole ``m_j`` multiplicity) are reported alongside every
result and are never applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMOS = Path(__file__).resolve().parents[1]
for _relative in ("16F_paper_absolute_chi2_reproduction_audit",):
    _path = str(DEMOS / _relative)
    if _path not in sys.path:
        sys.path.insert(0, _path)

import conventions16f as conv16f  # noqa: E402
import demo16f  # noqa: E402
import eq16f  # noqa: E402
import variants16f as variants16f  # noqa: E402


class Optics16GError(RuntimeError):
    """An optical evaluation that cannot be performed as asked."""


def conventions_from(cfg: Mapping[str, Any], method: str) -> conv16f.Convention:
    """Build a 16F ``Convention`` from this demo's config, refusing unknowns."""

    optics = cfg["optics"]
    convention = conv16f.Convention(
        nz=str(optics["nz_definition"]),
        zone_edge=str(optics["zone_edge"]),
        k_domain=str(optics["k_domain"]),
        k_method=str(method),
    )
    if not convention.fully_faithful:
        raise Optics16GError(
            "Demo 16G may only use conventions every one of whose choices a "
            f"cited source requires; {convention.as_record()['justification']} "
            "contains an unsourced choice"
        )
    return convention


def wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    start, end = (float(v) for v in cfg["optics"]["scan_wavelength_nm"])
    return np.linspace(start, end, int(cfg["optics"]["scan_points"]))


@dataclass
class OpticalResult:
    """One case's optical response, on one k implementation."""

    method: str
    wavelength_nm: np.ndarray
    magnitude_pm_per_V: np.ndarray
    chi2_at_target: float
    peak_chi2: float
    peak_wavelength_nm: float
    detuning_nm: float

    def as_record(self) -> dict[str, Any]:
        return {
            "k_method": self.method,
            "chi2_1550_pm_per_V": self.chi2_at_target,
            "peak_chi2_pm_per_V": self.peak_chi2,
            "peak_wavelength_nm": self.peak_wavelength_nm,
            "detuning_nm": self.detuning_nm,
            "scan_points": int(self.wavelength_nm.size),
            "scan_window_nm": [
                float(self.wavelength_nm[0]), float(self.wavelength_nm[-1])
            ],
        }


def evaluate(
    states: eq16f.StateSet, cfg: Mapping[str, Any], *, method: str = "radial",
) -> OpticalResult:
    """|chi2_xzx|(lambda) for one state set, in pm/V. Computes; never scales."""

    optics = cfg["optics"]
    convention = conventions_from(cfg, method)
    grid = wavelength_grid(cfg)
    broadening = float(optics["broadening_meV"]) * 1.0e-3
    magnitude = variants16f.spectrum(
        states, convention, grid, broadening_eV=broadening
    )
    target = float(optics["target_wavelength_nm"])
    at_target = float(np.interp(target, grid, magnitude))
    peak_index = int(np.argmax(magnitude))
    return OpticalResult(
        method=method,
        wavelength_nm=grid,
        magnitude_pm_per_V=magnitude,
        chi2_at_target=at_target,
        peak_chi2=float(magnitude[peak_index]),
        peak_wavelength_nm=float(grid[peak_index]),
        detuning_nm=float(grid[peak_index] - target),
    )


def evaluate_all_methods(
    states: eq16f.StateSet, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Both k implementations, plus their agreement.

    The primary reported number is the radial one, because that is the
    implementation Demo 16F's regression anchors were measured on. The Cartesian
    result is a control: a disagreement beyond the quadrature tolerance means a
    normalisation problem, not a physics one, and the case says so.
    """

    results = {
        method: evaluate(states, cfg, method=method)
        for method in cfg["optics"]["k_methods"]
    }
    primary = results.get("radial") or next(iter(results.values()))
    control = results.get("cartesian")
    ratio = (
        None if control is None or not primary.chi2_at_target
        else control.chi2_at_target / primary.chi2_at_target
    )
    return {
        "primary_method": primary.method,
        "results": results,
        "by_method": {name: result.as_record() for name, result in results.items()},
        "chi2_1550_pm_per_V": primary.chi2_at_target,
        "peak_chi2_pm_per_V": primary.peak_chi2,
        "peak_wavelength_nm": primary.peak_wavelength_nm,
        "detuning_nm": primary.detuning_nm,
        "cartesian_over_radial": ratio,
        "k_implementations_agree": (
            None if ratio is None
            else bool(abs(ratio - 1.0) <= 2.0e-2)
        ),
        "tensor": cfg["optics"]["tensor"],
        "conventions": conventions_from(cfg, primary.method).as_record(),
        "scale_factor_applied": None,
        "unresolved_published_ambiguities": [
            {"name": "eq1_eq2_prefactor", "size": 3.0, "applied": False},
            {"name": "heavy_hole_mj_multiplicity", "size": 2.0, "applied": False},
        ],
    }


def state_set_from_parsed(
    parsed_dir: Path,
    *,
    electron_energies_eV: Sequence[float],
    hole_energies_eV: Sequence[float],
    r_e_hh_nm: float = 0.751,
) -> tuple[eq16f.StateSet, dict[str, Any]]:
    """Rebuild Eq. 2's inputs from an ``envelopes.csv``, via Demo 16F.

    Reused rather than reimplemented so a Group 1 case and a Group 2 case are
    guaranteed to have their overlaps and position matrix elements computed by
    the same integrals.
    """

    return demo16f.state_set_from_run(
        Path(parsed_dir),
        electron_energies_eV=electron_energies_eV,
        hole_energies_eV=hole_energies_eV,
        r_e_hh_nm=float(r_e_hh_nm),
    )


def matrix_element_record(states: eq16f.StateSet) -> dict[str, Any]:
    """Energies, separations, overlaps and position matrix elements, named."""

    overlap = np.asarray(states.overlap_eh, dtype=float)
    z_e = np.asarray(states.z_e_nm, dtype=float)
    z_h = np.asarray(states.z_h_nm, dtype=float)
    e1, e2 = (float(v) for v in states.electron_energies_eV[:2])
    h1, h2 = (float(v) for v in states.hole_energies_eV[:2])
    return {
        "E1_eV": e1, "E2_eV": e2, "HH1_eV": h1, "HH2_eV": h2,
        "E2_minus_E1_meV": (e2 - e1) * 1000.0,
        "HH1_minus_HH2_meV": (h1 - h2) * 1000.0,
        "E1_minus_HH1_eV": e1 - h1,
        "E2_minus_HH2_eV": e2 - h2,
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
        "electron_diagonal_difference_nm": float(z_e[1, 1] - z_e[0, 0]),
        "hole_diagonal_difference_nm": float(z_h[1, 1] - z_h[0, 0]),
        "electron_hole_centroid_separation_nm": float(z_e[0, 0] - z_h[0, 0]),
    }


def bound_state_gate(parsed_dir: Path) -> dict[str, Any]:
    """Demo 16F's strict per-state gate, unchanged. Fails closed."""

    return demo16f.bound_state_gate(Path(parsed_dir))

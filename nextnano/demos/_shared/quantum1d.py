"""Parse and analyse one 1D one-band nextnano++ run.

Demos 4, 5, 6, and 9 all solve the Gamma-electron Schroedinger equation on a
layered 1D stack and then ask the same questions of the result: where is each
state, is it really bound, how do the states pair up between sweep points, and
what are the intersubband position matrix elements.  That common work lives
here so the four demos differ only in the physics they enable and the
conclusions they draw.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import outputs
from outputs import ParserError, ParserProfile, ResolvedOutputs


@dataclass
class OneBandRun:
    """Everything parsed from a single one-band 1D solver run."""

    position_nm: np.ndarray
    conduction_eV: np.ndarray
    band_edges: dict[str, np.ndarray]
    state_position_nm: np.ndarray
    energies_eV: np.ndarray
    densities: np.ndarray
    envelopes: np.ndarray | None
    potential_V: tuple[np.ndarray, np.ndarray] | None = None
    electric_field_kV_cm: tuple[np.ndarray, np.ndarray] | None = None
    dipole_matrix_nm: dict[str, np.ndarray] = field(default_factory=dict)
    resolved: ResolvedOutputs | None = None

    @property
    def state_count(self) -> int:
        return int(self.energies_eV.size)


def parse_one_band_run(
    raw_dir: Path,
    *,
    profile: ParserProfile,
    region_name: str,
    bandedge_columns: Mapping[str, int],
    want_potential: bool = False,
    want_envelopes: bool = True,
    dipole_polarizations: Sequence[str] = (),
) -> OneBandRun:
    """Locate and read every artifact a one-band demo consumes."""

    keys = ["bandedges", "energy_spectrum_gamma", "probabilities_gamma"]
    if want_envelopes:
        keys.append("envelopes_gamma")
    if want_potential:
        keys.extend(["potential", "electric_field"])
    resolved = outputs.resolve_outputs(
        profile, raw_dir, keys, substitutions={"region": region_name}
    )

    band_table = outputs.read_table(resolved.one("bandedges"))
    band_edges = band_table.select(dict(bandedge_columns))
    position = band_edges["position_nm"]
    conduction = band_edges["conduction_eV"]

    _, energies = outputs.read_state_table(resolved.one("energy_spectrum_gamma"))
    state_x, densities = outputs.read_profile_table(resolved.one("probabilities_gamma"))
    envelopes: np.ndarray | None = None
    if want_envelopes and resolved.many("envelopes_gamma"):
        envelope_x, envelope_values = outputs.read_profile_table(
            resolved.one("envelopes_gamma")
        )
        if envelope_x.shape != state_x.shape or not np.allclose(envelope_x, state_x):
            raise ParserError(
                "envelope and probability outputs are on different grids; refusing "
                "to combine them."
            )
        envelopes = envelope_values

    if densities.shape[1] < energies.size:
        # More eigenvalues than density columns means output_states{ max_num }
        # is smaller than num_ev. Trim the energies rather than inventing data.
        energies = energies[: densities.shape[1]]
    elif densities.shape[1] > energies.size:
        densities = densities[:, : energies.size]
        if envelopes is not None:
            envelopes = envelopes[:, : energies.size]

    potential = None
    field_profile = None
    if want_potential:
        potential_table = outputs.read_table(resolved.one("potential"))
        potential = (potential_table.column(0), potential_table.column(1))
        field_table = outputs.read_table(resolved.one("electric_field"))
        field_profile = (field_table.column(0), field_table.column(1))

    dipoles: dict[str, np.ndarray] = {}
    for polarization in dipole_polarizations:
        found = outputs.resolve_outputs(
            profile,
            raw_dir,
            ["dipole_matrix_elements_gamma"],
            substitutions={"region": region_name, "polarization": polarization},
        )
        paths = found.many("dipole_matrix_elements_gamma")
        if not paths:
            continue
        elements = outputs.read_matrix_elements(paths[0])
        # Selected by the header-declared unit, so the squared column (e^2*nm^2)
        # can never be mistaken for a length.
        column = outputs.magnitude_column(paths[0], unit="e*nm")
        size = int(energies.size)
        matrix = np.full((size, size), np.nan, dtype=float)
        for (i, j), values in elements.items():
            if 1 <= i <= size and 1 <= j <= size:
                matrix[i - 1, j - 1] = float(values[column])
        dipoles[polarization] = matrix

    return OneBandRun(
        position_nm=position,
        conduction_eV=conduction,
        band_edges=band_edges,
        state_position_nm=state_x,
        energies_eV=energies,
        densities=densities,
        envelopes=envelopes,
        potential_V=potential,
        electric_field_kV_cm=field_profile,
        dipole_matrix_nm=dipoles,
        resolved=resolved,
    )


def local_barrier_edge_eV(
    position_nm: np.ndarray,
    conduction_eV: np.ndarray,
    centroid_nm: float,
    *,
    window_nm: tuple[float, float] | None = None,
) -> float | None:
    """Lowest conduction-band maximum that still confines a state at ``centroid``.

    For a flat structure this is just the barrier height.  Under an applied
    tilt the two sides differ, and a state only stays bound if it is below the
    *smaller* of the two enclosing maxima -- which is what a naive "compare to
    the barrier material" test gets wrong.
    """

    x = np.asarray(position_nm, dtype=float)
    ec = np.asarray(conduction_eV, dtype=float)
    if x.size == 0 or ec.size != x.size:
        return None
    low, high = (float(x[0]), float(x[-1])) if window_nm is None else window_nm
    inside = (x >= low) & (x <= high)
    if not inside.any():
        return None
    left = inside & (x <= centroid_nm)
    right = inside & (x >= centroid_nm)
    if not left.any() or not right.any():
        return None
    return float(min(np.max(ec[left]), np.max(ec[right])))


def state_table(
    run: OneBandRun,
    *,
    regions: Mapping[str, tuple[float, float]],
    minimum_confined_probability: float = 0.5,
    normalisation_tolerance: float = 1e-3,
    boundary_edge_fraction: float = 0.05,
    symmetry_centre_nm: float | None = None,
    quantum_window_nm: tuple[float, float] | None = None,
) -> list[analysis.StateObservables]:
    """Per-state observables with a position-aware bound-state test."""

    states = analysis.analyse_states(
        run.state_position_nm,
        run.energies_eV,
        run.densities,
        regions=regions,
        envelopes=run.envelopes,
        barrier_edge_eV=None,
        minimum_bound_probability=minimum_confined_probability,
        normalisation_tolerance=normalisation_tolerance,
        boundary_edge_fraction=boundary_edge_fraction,
        symmetry_centre_nm=symmetry_centre_nm,
    )
    for state in states:
        barrier = local_barrier_edge_eV(
            run.position_nm,
            run.conduction_eV,
            state.centroid_nm,
            window_nm=quantum_window_nm,
        )
        confining = [name for name in regions if "well" in name]
        confined = sum(state.region_probabilities.get(name, 0.0) for name in confining)
        reasons: list[str] = []
        energy_ok = True
        if barrier is None:
            reasons.append("no enclosing barrier maximum found; energy test skipped")
        else:
            energy_ok = state.energy_eV < barrier
            if not energy_ok:
                reasons.append(
                    f"energy {state.energy_eV:.5f} eV is above the enclosing barrier "
                    f"maximum {barrier:.5f} eV"
                )
        probability_ok = confined >= minimum_confined_probability
        if not probability_ok:
            reasons.append(
                f"confined probability {confined:.4f} < {minimum_confined_probability}"
            )
        state.bound = bool(energy_ok and probability_ok)
        state.bound_reason = "; ".join(reasons) or (
            "energy below the enclosing barrier maximum and probability confined"
        )
    return states


def envelope_matrices(run: OneBandRun) -> dict[str, np.ndarray]:
    """Overlap and position-matrix-element matrices derived from envelopes."""

    if run.envelopes is None or run.envelopes.size == 0:
        return {}
    x = run.state_position_nm
    count = min(run.state_count, run.envelopes.shape[1])
    normalised = np.column_stack(
        [analysis.normalise_envelope(x, run.envelopes[:, index])[0] for index in range(count)]
    )
    overlap = np.zeros((count, count), dtype=float)
    position = np.zeros((count, count), dtype=float)
    for i in range(count):
        for j in range(count):
            overlap[i, j] = analysis.overlap(x, normalised[:, i], normalised[:, j])
            position[i, j] = analysis.position_matrix_element_nm(
                x, normalised[:, i], normalised[:, j]
            )
    return {"overlap": overlap, "position_matrix_nm": position}


def compare_dipole_sources(
    run: OneBandRun, envelope_position_nm: np.ndarray, polarization: str
) -> dict[str, Any]:
    """Cross-check the solver's dipole output against the envelope integral.

    nextnano++ reports |<i|eps.d|j>| in e*nm, i.e. the magnitude of z_ij, so
    only magnitudes are compared.  A disagreement means one of the two is being
    read wrongly and must be resolved before any matrix element is used.
    """

    solver = run.dipole_matrix_nm.get(polarization)
    if solver is None or envelope_position_nm.size == 0:
        return {
            "compared": False,
            "reason": "solver dipole output or envelopes unavailable",
        }
    size = min(solver.shape[0], envelope_position_nm.shape[0])
    solver_block = np.abs(solver[:size, :size])
    envelope_block = np.abs(envelope_position_nm[:size, :size])
    offdiag = ~np.eye(size, dtype=bool)
    finite = np.isfinite(solver_block) & np.isfinite(envelope_block) & offdiag
    if not finite.any():
        return {"compared": False, "reason": "no comparable off-diagonal elements"}
    difference = np.abs(solver_block[finite] - envelope_block[finite])
    return {
        "compared": True,
        "polarization": polarization,
        "max_absolute_difference_nm": float(np.max(difference)),
        "mean_absolute_difference_nm": float(np.mean(difference)),
        "compared_elements": int(finite.sum()),
    }


def kv_per_cm_to_volts_per_metre(field_kV_cm: float) -> float:
    """Convert kV/cm to the V/m that ``poisson{ electric_field{ strength } }`` takes.

    Measured on nextnano++ 3.0.0 (Free edition, home laptop, 2026-07-30):
    ``strength = 1.0e7`` produced exactly 100 kV/cm in ``electric_field.dat``
    and a 0.4 V drop across a 40 nm domain.  1 kV/cm = 1e5 V/m.
    """

    value = float(field_kV_cm)
    if not math.isfinite(value):
        raise ValueError("electric field must be finite.")
    return value * 1.0e5


def measured_field_kV_cm(run: OneBandRun) -> float | None:
    """Median field actually written by the solver, for the unit cross-check."""

    if run.electric_field_kV_cm is None:
        return None
    _, values = run.electric_field_kV_cm
    if values.size == 0:
        return None
    return float(np.median(values))


def potential_slope_kV_cm(run: OneBandRun) -> float | None:
    """Field implied by the potential profile, in kV/cm.

    E = -dphi/dx.  phi is in V and x in nm, so dphi/dx in V/nm becomes kV/cm by
    multiplying by 1e7 nm/cm and dividing by 1e3 V/kV, i.e. by 1e4.
    """

    if run.potential_V is None:
        return None
    x, phi = run.potential_V
    if x.size < 2:
        return None
    slope_V_per_nm = float(np.polyfit(x, phi, 1)[0])
    return -slope_V_per_nm * 1.0e4


def region_map(intervals: Mapping[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    """Copy of a layer stack's intervals, with float coordinates."""

    return {name: (float(low), float(high)) for name, (low, high) in intervals.items()}

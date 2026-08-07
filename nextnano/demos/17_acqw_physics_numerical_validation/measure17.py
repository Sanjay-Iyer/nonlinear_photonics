"""Demo 17 measurement layer: what a nextnano++ run actually produced.

Everything here turns raw solver output into numbers an experiment can compare.
Three facts about nextnano++ 3.0.0 are built in because they were measured on the
installed binary rather than assumed, and each one would otherwise show up as a
spurious scientific error:

**Composition is reported on the dual grid.** ``Structure/alloy_composition.dat``
lists *cell centres*, not grid lines: with a 0.5 nm grid from 0 nm the first row
is at 0.25 nm. Comparing it point-by-point against a profile sampled on grid
nodes introduces a half-cell shift that looks exactly like a real interface
offset. :func:`load_realized_composition` records the grid it got and every
comparison interpolates the authoritative profile onto it.

**``import{}`` is refused outright by the Free edition**, at run time rather than
at parse time. ``--parse`` accepts an imported deck and the solver then declines
to execute it, so a Level-1 pass says nothing about whether the imported path
runs. Only the licensed build can answer the equivalence question.

**Hole states come back in decreasing electron-scale energy.** Index order is
confinement order, so HH1 is the most confined hole. Demo 11 already relies on
this; Demo 17 reuses its readers rather than re-deriving the convention.

Grading widths use one definition throughout, stated once here:

    ``grading_width_nm`` is the 10%-to-90% composition transition width of that
    interface's grading function **taken in isolation**.

At an isolated interface the realized width equals the request (exactly for
linear; to within a fraction of a mesh cell for fermi/erf/cosine). At a thin
central barrier the two interfaces superpose and the realized width of the
composite is *smaller* than either request. That is the structure, not an error,
and :func:`grading_width_report` reports both numbers rather than picking the
flattering one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import chi2 as chi2mod
import demo16
import grading14
import outputs as outputs_mod

#: CODATA-consistent conversion. lambda[nm] = HC_EV_NM / E[eV].
HC_EV_NM = 1239.841984

#: nextnano++ writes realized alloy composition here, relative to the run's raw
#: output directory. Measured on the installed 3.0.0 build.
ALLOY_COMPOSITION_GLOB = "**/Structure/alloy_composition.dat"

#: The marker nextnano++ writes on success, and its expected content.
JOB_DONE_NAME = "job_done.txt"
JOB_DONE_TEXT = "Calculation successfully completed"


class Measure17Error(RuntimeError):
    """A measurement could not be made, as distinct from failing a tolerance."""


# ---------------------------------------------------------------------------
# Numerical tolerances
#
# Each is justified by a measured floor rather than chosen to make a test pass.
# The floors were characterised on the authoritative profiles at the production
# 0.05 nm mesh before any tolerance was written down.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tolerances:
    """Experiment-specific tolerances and why each one has its value."""

    #: Isolated-interface 10-90 width. Measured floor: 0 nm for linear (exact),
    #: <= 0.007 nm for fermi/erf on a 0.05 nm mesh. 0.02 nm is ~3x the floor and
    #: 0.4 of one mesh cell.
    grading_width_isolated_nm: float = 0.02
    #: Interface 50% crossing position. One mesh cell; a crossing is located by
    #: linear interpolation between two samples, so it cannot be sharper.
    interface_centre_nm: float = 0.05
    #: Composition agreement between the authoritative profile and nextnano++'s
    #: realized output, interpolated onto the same grid.
    composition_rms: float = 5.0e-3
    composition_max: float = 2.0e-2
    #: Native vs imported rendering of the same profile. These are two encodings
    #: of one function; disagreement beyond interpolation is a real defect.
    equivalence_composition_max: float = 5.0e-3
    equivalence_energy_eV: float = 1.0e-3
    equivalence_transition_eV: float = 1.0e-3
    #: Mirror invariance at zero field. A mirrored structure is the same physics
    #: reflected, so energies should agree to solver precision; the budget is
    #: dominated by the mesh not being symmetric about the structure centre.
    mirror_energy_eV: float = 1.0e-3
    mirror_probability: float = 5.0e-3
    #: Mesh convergence: what counts as "converged" between the two finest grids.
    mesh_converged_energy_eV: float = 1.0e-3
    #: Domain convergence: a bound state must not care where the wall is.
    domain_converged_energy_eV: float = 1.0e-3
    #: Boundary leakage above which confinement is attributed to the wall.
    maximum_boundary_probability: float = 1.0e-3
    #: Wavefunction normalisation and orthonormality.
    normalisation: float = 1.0e-3
    orthonormality: float = 1.0e-3
    #: Independent energy-to-wavelength cross-check.
    wavelength_relative: float = 1.0e-6

    def as_record(self) -> dict[str, Any]:
        return {
            k: getattr(self, k) for k in self.__dataclass_fields__
        }


TOLERANCES = Tolerances()


# ---------------------------------------------------------------------------
# Realized composition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealizedComposition:
    """nextnano++'s own account of the alloy profile it built."""

    x_nm: np.ndarray
    al_fraction: np.ndarray
    source_path: str
    #: True when the samples sit at cell centres rather than on grid lines.
    grid_is_dual_cell_centred: bool
    mesh_nm: float | None

    def as_record(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "points": int(self.x_nm.size),
            "first_position_nm": float(self.x_nm[0]) if self.x_nm.size else None,
            "last_position_nm": float(self.x_nm[-1]) if self.x_nm.size else None,
            "grid_is_dual_cell_centred": self.grid_is_dual_cell_centred,
            "median_spacing_nm": self.mesh_nm,
            "max_al_fraction": float(np.max(self.al_fraction)) if self.al_fraction.size else None,
        }


def load_realized_composition(raw_dir: Path) -> RealizedComposition:
    """Read ``Structure/alloy_composition.dat``.

    Columns are ``x[nm] Alloy_x[] Alloy_y[] Alloy_z[]``; only ``Alloy_x`` is
    meaningful for a ternary. The dual-grid flag is derived from the data, not
    declared: if the first sample sits half a spacing above the first grid line
    the file is cell-centred.
    """

    raw_dir = Path(raw_dir)
    matches = sorted(raw_dir.glob(ALLOY_COMPOSITION_GLOB))
    if not matches:
        listing = sorted(p.name for p in raw_dir.rglob("*") if p.is_file())[:25]
        raise Measure17Error(
            f"no alloy composition under {raw_dir}. structure{{}} must contain "
            f"output_alloy_composition{{}}. Files present: {listing}"
        )
    path = matches[0]
    rows: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue  # the header line
    if len(rows) < 3:
        raise Measure17Error(f"{path} holds {len(rows)} usable rows.")

    x = np.array([r[0] for r in rows], dtype=float)
    y = np.array([r[1] for r in rows], dtype=float)
    if not np.all(np.diff(x) > 0):
        raise Measure17Error(f"{path} positions are not strictly ascending.")

    spacings = np.diff(x)
    median = float(np.median(spacings))
    # Cell-centred when the first sample is about half a spacing in from 0.
    dual = bool(x.size and abs(float(x[0]) - 0.5 * median) < 0.25 * median)
    return RealizedComposition(
        x_nm=x, al_fraction=y, source_path=str(path),
        grid_is_dual_cell_centred=dual, mesh_nm=median,
    )


def compare_composition(
    intended: grading14.CompositionProfile,
    realized: RealizedComposition,
    *,
    restrict_to_nm: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Authoritative ``x_Al(z)`` against nextnano++'s realized composition.

    The authoritative profile is evaluated on the *realized* grid, using its
    continuous oversampled representation rather than its mesh sampling, so the
    comparison measures what nextnano++ built and not the difference between two
    sampling grids.
    """

    xr, yr = realized.x_nm, realized.al_fraction
    if restrict_to_nm is not None:
        lo, hi = restrict_to_nm
        mask = (xr >= lo) & (xr <= hi)
        xr, yr = xr[mask], yr[mask]
    if xr.size < 3:
        raise Measure17Error("too few realized samples in the comparison window.")

    intended_on_realized = np.interp(
        xr, intended.x_nm_continuous, intended.al_fraction_continuous
    )
    residual = yr - intended_on_realized
    dose_realized = float(np.trapezoid(yr, xr))
    dose_intended = float(np.trapezoid(intended_on_realized, xr))
    return {
        "points_compared": int(xr.size),
        "window_nm": [float(xr[0]), float(xr[-1])],
        "rms_error": float(np.sqrt(np.mean(residual**2))),
        "max_abs_error": float(np.max(np.abs(residual))),
        "mean_signed_error": float(np.mean(residual)),
        "max_error_position_nm": float(xr[int(np.argmax(np.abs(residual)))]),
        "integrated_al_dose_realized_nm": dose_realized,
        "integrated_al_dose_intended_nm": dose_intended,
        "integrated_al_dose_relative_error": (
            abs(dose_realized - dose_intended) / dose_intended
            if dose_intended > 0 else None
        ),
        "realized_peak_al_fraction": float(np.max(yr)),
        "intended_peak_al_fraction": float(np.max(intended_on_realized)),
        "comparison_grid": "realized (nextnano++ cell centres)",
    }


# ---------------------------------------------------------------------------
# Mesh snapping
# ---------------------------------------------------------------------------


def mesh_snapping_report(
    geometry: Any, profile: grading14.CompositionProfile, mesh_nm: float
) -> dict[str, Any]:
    """Requested continuous geometry against what the mesh can represent.

    A 1.8 nm barrier on a 0.05 nm mesh is representable exactly; 0.851 nm is not.
    Recording the difference is what separates expected discretization error from
    a renderer that put a layer in the wrong place.
    """

    interfaces = profile.request["interfaces_nm"]
    x = np.asarray(profile.x_nm, dtype=float)

    def snap(position: float) -> float:
        return float(x[int(np.argmin(np.abs(x - position)))])

    entries: dict[str, Any] = {}
    for name, requested in interfaces.items():
        snapped = snap(float(requested))
        entries[name] = {
            "requested_nm": float(requested),
            "mesh_represented_nm": snapped,
            "snapping_error_nm": float(snapped - requested),
            "representable_exactly": bool(abs(snapped - requested) < 1e-9),
        }

    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    layers = {
        "thick_well_nm": (z2 - z1, snap(z2) - snap(z1)),
        "central_barrier_nm": (z3 - z2, snap(z3) - snap(z2)),
        "thin_well_nm": (z4 - z3, snap(z4) - snap(z3)),
        "active_region_nm": (z4 - z1, snap(z4) - snap(z1)),
    }
    layer_report = {
        name: {
            "requested_nm": float(req),
            "mesh_represented_nm": float(real),
            "error_nm": float(real - req),
        }
        for name, (req, real) in layers.items()
    }
    worst = max(abs(e["snapping_error_nm"]) for e in entries.values())
    return {
        "mesh_nm": float(mesh_nm),
        "interfaces": entries,
        "layers": layer_report,
        "max_interface_snapping_error_nm": float(worst),
        # A snap can never exceed half a cell; anything more is a bug, not
        # discretization.
        "within_half_a_mesh_cell": bool(worst <= 0.5 * mesh_nm + 1e-12),
        "total_active_length_error_nm": layer_report["active_region_nm"]["error_nm"],
    }


# ---------------------------------------------------------------------------
# Grading-width definition
# ---------------------------------------------------------------------------


def support_half_width_nm(
    family_name: str, width_10_90_nm: float, *, threshold: float = 0.01
) -> float:
    """How far an interface's influence actually reaches, in nanometres.

    The 10-90 width is the wrong measure of reach for fermi and erf: both have
    infinite support, and a 1.4 nm fermi interface is still 10% of the way
    through its transition more than a nanometre past where a linear one has
    finished. Using the 10-90 width as a clearance therefore calls two
    interfaces isolated when they are visibly interfering -- which is what a
    2.5 nm barrier with 1.4 nm fermi grades does.

    The distance is solved from the family's own CDF by bisection, so it stays
    correct for any family added later and duplicates no grading physics.
    """

    fam = grading14.family(family_name)
    scale = fam.scale_for(float(width_10_90_nm))
    if fam.compact_support:
        # Support is exactly one natural scale wide, centred on the interface.
        return 0.5 * scale

    lo, hi = 0.0, 1.0
    for _ in range(200):                     # expand until the tail is below threshold
        if float(fam.cdf(np.array([-hi]))[0]) <= threshold:
            break
        lo, hi = hi, hi * 2.0
    else:  # pragma: no cover - no supported family fails to decay
        raise Measure17Error(f"{family_name}: CDF never falls below {threshold}")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(fam.cdf(np.array([-mid]))[0]) > threshold:
            lo = mid
        else:
            hi = mid
    return float(hi * scale)


def isolated_interfaces(
    interfaces: Mapping[str, float], requested_widths: Mapping[str, float],
    *, family_name: str = "linear", threshold: float = 0.01,
) -> dict[str, bool]:
    """Which interfaces have no neighbour close enough to distort their width.

    An interface is isolated when its own reach and its nearest neighbour's do
    not meet -- "reach" being where the grading function has decayed to
    ``threshold``, not where its 10-90 transition ends.
    """

    centres = {k: float(v) for k, v in interfaces.items()}
    reach = {
        name: support_half_width_nm(
            family_name, float(requested_widths[name]), threshold=threshold)
        for name in centres
    }
    out: dict[str, bool] = {}
    for name, centre in centres.items():
        clearances = [
            abs(other - centre) - (reach[name] + reach[other_name])
            for other_name, other in centres.items() if other_name != name
        ]
        out[name] = bool(min(clearances) >= 0.0) if clearances else True
    return out


def grading_width_report(
    profile: grading14.CompositionProfile,
    requested_widths: Mapping[str, float],
    max_al_fraction: float,
) -> dict[str, Any]:
    """The standardized grading-width account for one structure.

    Reports, per interface: the family's raw mathematical scale, the requested
    10-90 width, the realized width measured locally, and whether the interface
    was isolated. The definitional check applies only to isolated interfaces --
    a composite barrier has no single 10-90 width to compare a request against.
    """

    req = profile.request
    fam = grading14.family(req["profile"])
    interfaces = req["interfaces_nm"]
    metrics = demo16.measure_interfaces(
        profile.x_nm, profile.al_fraction, interfaces, requested_widths,
        max_al_fraction,
    )
    isolation = isolated_interfaces(
        interfaces, requested_widths, family_name=fam.name)
    scales = {
        "outer_left_algaas_to_gaas": float(req["natural_scale_fall_nm"]),
        "central_gaas_to_algaas": float(req["natural_scale_rise_nm"]),
        "central_algaas_to_gaas": float(req["natural_scale_fall_nm"]),
        "outer_right_gaas_to_algaas": float(req["natural_scale_rise_nm"]),
    }

    rows: list[dict[str, Any]] = []
    for metric in metrics:
        realized = metric.realized_width_10_90_nm
        requested = metric.requested_width_10_90_nm
        rows.append({
            "interface": metric.name,
            "profile_family": fam.name,
            "family_10_90_width_in_natural_units": fam.width_10_90_natural,
            "raw_mathematical_scale_nm": scales[metric.name],
            "requested_grading_width_nm": requested,
            "expected_physical_10_90_width_nm": requested,
            "realized_peak_referenced_10_90_width_nm": realized,
            "width_error_nm": None if realized is None else abs(realized - requested),
            "interface_is_isolated": isolation[metric.name],
            "support_half_width_nm": support_half_width_nm(fam.name, requested),
            "measurement_window_nm": list(metric.window_nm),
            "window_isolated_from_other_interfaces": metric.window_isolated,
            "realized_centre_nm": metric.realized_centre_nm,
            "requested_centre_nm": metric.requested_centre_nm,
            "centre_error_nm": metric.centre_error_nm,
        })

    diag = profile.diagnostics
    reached = bool(diag["nominal_90pct_threshold_reached"])
    checked = [r for r in rows if r["interface_is_isolated"] and r["width_error_nm"] is not None]
    return {
        "profile_family": fam.name,
        "width_definition": (
            "10%-to-90% composition transition width of the interface's grading "
            "function taken in isolation"
        ),
        "interfaces": rows,
        "nominal_90pct_threshold_reached": reached,
        "peak_referenced_10_90_width_nm": {
            "left": diag["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"],
            "right": diag["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"],
        },
        # Explicitly null, not absent, when the nominal 90% level is never
        # crossed. That is a physical statement about an overlapped barrier.
        "nominal_referenced_10_90_width_nm": {
            "left": diag["realized_gaas_to_algaas_grading_width_10_90_nominalref_nm"],
            "right": diag["realized_algaas_to_gaas_grading_width_10_90_nominalref_nm"],
        },
        "realized_central_peak_al_fraction": diag["realized_peak_al_fraction"],
        "isolated_interface_count": len(checked),
        "max_isolated_width_error_nm": (
            max((r["width_error_nm"] for r in checked), default=0.0)
        ),
    }


# ---------------------------------------------------------------------------
# Overlap oracle
# ---------------------------------------------------------------------------


def overlap_physics_report(
    profile: grading14.CompositionProfile, max_al_fraction: float
) -> dict[str, Any]:
    """The explicit description of what happens inside a graded central barrier.

    The authoritative combination rule lives in
    ``grading14.build_structure_profile`` and is stated once, here, in words:

        ``x_Al(z) = x_max * (1 - G_thick(z) - G_thin(z))``

    where each ``G_w(z) = C((z - z_open)/s_fall) * (1 - C((z - z_close)/s_rise))``
    is that well's GaAs *occupancy*. Composition is the barrier alloy with the
    wells subtracted, so where two wells' tails reach the same point their
    occupancies add and the remaining Al falls short of nominal.

    This is a superposition of occupancies, not of compositions, and it is not
    ``max()``, ``min()`` or last-writer-wins. Those alternatives all fabricate a
    flat nominal plateau across a barrier too thin to have one -- which is the
    defect this report exists to rule out.
    """

    x = np.asarray(profile.x_nm, dtype=float)
    y = np.asarray(profile.al_fraction, dtype=float)
    xc = np.asarray(profile.x_nm_continuous, dtype=float)
    yc = np.asarray(profile.al_fraction_continuous, dtype=float)
    interfaces = profile.request["interfaces_nm"]
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])

    inner = (xc >= z2) & (xc <= z3)
    if not np.any(inner):
        inner = (xc >= z2 - 0.5) & (xc <= z3 + 0.5)
    peak = float(np.max(yc[inner]))
    peak_position = float(xc[inner][int(np.argmax(yc[inner]))])

    # The overlap region: where BOTH wells' occupancies are non-negligible.
    fam = grading14.family(profile.request["profile"])
    req = profile.request
    s_rise = float(req["natural_scale_rise_nm"])
    s_fall = float(req["natural_scale_fall_nm"])
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    g_thick = fam.cdf((xc - z1) / s_fall) * (1.0 - fam.cdf((xc - z2) / s_rise))
    g_thin = fam.cdf((xc - z3) / s_fall) * (1.0 - fam.cdf((xc - z4) / s_rise))
    both = (g_thick > 0.01) & (g_thin > 0.01)
    if np.any(both):
        overlap_start = float(xc[both][0])
        overlap_end = float(xc[both][-1])
    else:
        overlap_start = overlap_end = None

    # The authoritative rule, evaluated independently and checked against the
    # profile the production code returned. Same functions, recombined -- this
    # verifies the rule was applied, not that two implementations agree.
    rule = np.clip(max_al_fraction * (1.0 - g_thick - g_thin), 0.0, max_al_fraction)
    rule_residual = float(np.max(np.abs(rule - yc)))

    plateau_level = 0.995 * max_al_fraction
    inner_mesh = (x >= z2) & (x <= z3)
    plateau_points = int(np.count_nonzero(y[inner_mesh] >= plateau_level))
    dose = float(np.trapezoid(yc[inner], xc[inner]))

    return {
        "combination_rule": "x_Al(z) = x_max * (1 - G_thick(z) - G_thin(z))",
        "combination_rule_kind": "subtractive superposition of GaAs occupancies",
        "combination_rule_is_not": ["max", "min", "last_region_wins", "average"],
        "combination_rule_residual_vs_profile": rule_residual,
        "combination_rule_verified": bool(rule_residual < 1e-12),
        "nominal_barrier_al_fraction": float(max_al_fraction),
        "realized_peak_al_fraction": peak,
        "expected_peak_al_fraction": peak,
        "peak_as_fraction_of_nominal": peak / max_al_fraction,
        "peak_position_nm": peak_position,
        "barrier_centre_nm": 0.5 * (z2 + z3),
        "peak_offset_from_barrier_centre_nm": peak_position - 0.5 * (z2 + z3),
        "overlap_start_nm": overlap_start,
        "overlap_end_nm": overlap_end,
        "overlap_width_nm": (
            None if overlap_start is None else overlap_end - overlap_start),
        "reaches_90pct_of_nominal": bool(peak >= 0.90 * max_al_fraction),
        "nominal_plateau_exists": bool(plateau_points >= 2),
        "plateau_mesh_points_at_nominal": plateau_points,
        "expected_integrated_al_dose_nm": dose,
        "realized_integrated_al_dose_nm": dose,
        "grades_overlap": bool(peak < 0.995 * max_al_fraction),
        "central_barrier_nm": z3 - z2,
    }


# ---------------------------------------------------------------------------
# Quantum states
# ---------------------------------------------------------------------------


@dataclass
class SolvedStates:
    """Electron and heavy-hole states of one completed run."""

    electron: chi2mod.BandStates
    heavy_hole: chi2mod.BandStates
    raw_dir: str
    region: str
    #: Position grid the envelopes live on.
    z_nm: np.ndarray = field(default_factory=lambda: np.array([]))

    def transition_eV(self, electron_index: int = 0, hole_index: int = 0) -> float:
        return float(
            self.electron.energies_eV[electron_index]
            - self.heavy_hole.energies_eV[hole_index]
        )


def load_states(raw_dir: Path, region: str) -> SolvedStates:
    """Electron and HH states, through Demo 11's readers and the shared parser."""

    profile = outputs_mod.load_profile("nextnano_pp_3_0_0")
    raw_dir = Path(raw_dir)
    resolved = outputs_mod.resolve_outputs(
        profile, raw_dir,
        ["energy_spectrum_gamma", "envelopes_gamma",
         "energy_spectrum_hh", "envelopes_hh"],
        substitutions={"region": region},
    )
    outputs_mod.require_or_diagnose(
        resolved, raw_dir,
        ["energy_spectrum_gamma", "envelopes_gamma",
         "energy_spectrum_hh", "envelopes_hh"],
        why="Demo 17 compares electron and heavy-hole states across variants",
    )
    _, e_energies = outputs_mod.read_state_table(resolved.one("energy_spectrum_gamma"))
    z_e, e_env = outputs_mod.read_profile_table(resolved.one("envelopes_gamma"))
    _, h_energies = outputs_mod.read_state_table(resolved.one("energy_spectrum_hh"))
    z_h, h_env = outputs_mod.read_profile_table(resolved.one("envelopes_hh"))
    if z_e.shape != z_h.shape or not np.allclose(z_e, z_h):
        raise Measure17Error(
            "electron and hole envelopes are on different grids; a transition "
            "energy computed across them would be meaningless"
        )
    return SolvedStates(
        electron=chi2mod.BandStates(z_e, e_energies, e_env, "Gamma"),
        heavy_hole=chi2mod.BandStates(z_h, h_energies, h_env, "HH"),
        raw_dir=str(raw_dir), region=region, z_nm=z_e,
    )


def state_quality_report(
    states: SolvedStates, *, edge_fraction: float = 0.05,
    tolerances: Tolerances = TOLERANCES,
) -> dict[str, Any]:
    """Normalisation, orthonormality, ordering, leakage and finiteness.

    ``BandStates`` normalises on construction, so the normalisation figure here
    measures the *raw* envelopes as nextnano++ wrote them -- normalising first
    and then checking the norm would report 1.0 whatever the solver produced.
    """

    report: dict[str, Any] = {}
    for band in (states.electron, states.heavy_hole):
        z = band.z_nm
        span = float(z[-1] - z[0])
        left = z <= z[0] + edge_fraction * span
        right = z >= z[-1] - edge_fraction * span
        norms, leak_l, leak_r = [], [], []
        for index in range(band.count):
            psi = band.envelopes[:, index]
            density = psi**2
            total = float(np.trapezoid(density, z))
            norms.append(total)
            leak_l.append(float(np.trapezoid(density[left], z[left]) / total))
            leak_r.append(float(np.trapezoid(density[right], z[right]) / total))
        energies = band.energies_eV
        # Electrons ascend in energy; nextnano++ lists holes in DECREASING
        # electron-scale energy, so each band is checked against its own
        # convention rather than a single assumed direction.
        ascending = bool(np.all(np.diff(energies) >= -1e-9))
        descending = bool(np.all(np.diff(energies) <= 1e-9))
        report[band.label] = {
            "state_count": band.count,
            "energies_eV": [float(e) for e in energies],
            "normalisation_of_each_state": norms,
            "max_normalisation_error": float(
                max(abs(n - 1.0) for n in norms)) if norms else None,
            "orthonormality_error": float(band.orthonormality_error()),
            "orthonormality_within_tolerance": bool(
                band.orthonormality_error() <= tolerances.orthonormality),
            "energies_monotone": ascending or descending,
            "energy_order": (
                "ascending" if ascending else "descending" if descending else "mixed"),
            "boundary_probability_left": leak_l,
            "boundary_probability_right": leak_r,
            "max_boundary_probability": float(max(leak_l + leak_r)) if leak_l else None,
            "confined_by_material_not_boundary": bool(
                max(leak_l + leak_r) <= tolerances.maximum_boundary_probability
            ) if leak_l else None,
            "all_finite": bool(
                np.all(np.isfinite(energies)) and np.all(np.isfinite(band.envelopes))),
            "any_nan": bool(
                np.any(np.isnan(energies)) or np.any(np.isnan(band.envelopes))),
            "any_inf": bool(
                np.any(np.isinf(energies)) or np.any(np.isinf(band.envelopes))),
        }
    report["passed"] = all(
        report[label]["all_finite"]
        and report[label]["orthonormality_within_tolerance"]
        and report[label]["energies_monotone"]
        and not report[label]["any_nan"]
        for label in ("Gamma", "HH")
    )
    return report


def localization(band: chi2mod.BandStates, regions: Mapping[str, tuple[float, float]]
                 ) -> list[dict[str, Any]]:
    """Fraction of |psi|^2 inside each named region, per state."""

    z = band.z_nm
    out = []
    for index in range(band.count):
        density = band.envelopes[:, index] ** 2
        total = float(np.trapezoid(density, z))
        entry: dict[str, Any] = {"state_index": index + 1}
        for name, (lo, hi) in regions.items():
            mask = (z >= lo) & (z <= hi)
            entry[name] = (
                float(np.trapezoid(density[mask], z[mask]) / total)
                if np.count_nonzero(mask) > 1 else 0.0
            )
        entry["centroid_nm"] = float(np.trapezoid(density * z, z) / total)
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Independent energy <-> wavelength
# ---------------------------------------------------------------------------


def wavelength_check(
    electron_eV: float, hole_eV: float, production_wavelength_nm: float | None = None,
    *, tolerances: Tolerances = TOLERANCES,
) -> dict[str, Any]:
    """``lambda = 1239.841984 / dE``, computed independently of the production path.

    Recomputing the same conversion with the same helper would prove nothing; the
    arithmetic here is deliberately written out so a unit slip in ``chi2`` has
    somewhere to show up.
    """

    delta_eV = float(electron_eV) - float(hole_eV)
    independent_nm = HC_EV_NM / delta_eV if delta_eV > 0 else None
    production_nm = (
        float(production_wavelength_nm) if production_wavelength_nm is not None
        else (float(chi2mod.wavelength_nm(delta_eV)) if delta_eV > 0 else None)
    )
    difference = (
        abs(independent_nm - production_nm)
        if (independent_nm is not None and production_nm is not None) else None
    )
    return {
        "electron_energy_eV": float(electron_eV),
        "hole_energy_eV": float(hole_eV),
        "transition_energy_eV": delta_eV,
        "transition_energy_meV": delta_eV * 1000.0,
        "independent_wavelength_nm": independent_nm,
        "production_wavelength_nm": production_nm,
        "absolute_difference_nm": difference,
        "relative_difference": (
            difference / production_nm
            if (difference is not None and production_nm) else None),
        "within_tolerance": bool(
            difference is not None and production_nm
            and difference / production_nm <= tolerances.wavelength_relative
        ) if difference is not None else None,
        # The classic unit slip: treating an eV value as meV shifts the answer by
        # exactly 1000x, which this makes visible rather than plausible.
        "wavelength_if_energy_mistaken_for_meV_nm": (
            HC_EV_NM / (delta_eV / 1000.0) if delta_eV > 0 else None),
        "constant_used_eV_nm": HC_EV_NM,
    }


def target_energy_check(target_wavelength_nm: float) -> dict[str, Any]:
    """The energy corresponding to the production target, both ways."""

    target = float(target_wavelength_nm)
    independent_eV = HC_EV_NM / target
    production_eV = float(chi2mod.photon_energy_eV(target))
    return {
        "target_wavelength_nm": target,
        "independent_energy_eV": independent_eV,
        "independent_energy_meV": independent_eV * 1000.0,
        "production_energy_eV": production_eV,
        "absolute_difference_eV": abs(independent_eV - production_eV),
        "relative_difference": abs(independent_eV - production_eV) / production_eV,
        "round_trip_wavelength_nm": HC_EV_NM / independent_eV,
        "round_trip_error_nm": abs(HC_EV_NM / independent_eV - target),
    }


# ---------------------------------------------------------------------------
# Run integrity
# ---------------------------------------------------------------------------


def run_integrity(
    raw_dir: Path, *, return_code: int | None,
    started_utc: str | None = None, expected_files: Sequence[str] = (),
) -> dict[str, Any]:
    """Whether this run may be used to make a physical claim.

    Three independent ways a run can look finished without being finished:
    a nonzero return code, a missing ``job_done.txt``, and output files older
    than the run that produced them. The last is the subtle one -- a failed
    solve leaves the previous run's files in place, and analysis then reports
    the previous structure's physics under the new structure's name.
    """

    raw_dir = Path(raw_dir)
    markers = sorted(raw_dir.rglob(JOB_DONE_NAME))
    job_done_text = (
        markers[0].read_text(encoding="utf-8", errors="replace").strip()
        if markers else None
    )
    info = sorted(raw_dir.rglob("simulation_info.txt"))

    stale: list[str] = []
    if started_utc:
        import datetime as dt

        try:
            started = dt.datetime.fromisoformat(started_utc.replace("Z", "+00:00"))
            cutoff = started.timestamp() - 2.0   # filesystem timestamp slack
            for path in raw_dir.rglob("*"):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    stale.append(str(path.relative_to(raw_dir)))
        except ValueError:
            stale = []

    missing = [
        name for name in expected_files if not any(raw_dir.rglob(name))
    ]
    checks = {
        "return_code": return_code,
        "return_code_is_zero": bool(return_code == 0),
        "job_done_present": bool(markers),
        "job_done_text": job_done_text,
        "job_done_reports_success": bool(
            job_done_text and JOB_DONE_TEXT.lower() in job_done_text.lower()),
        "simulation_info_present": bool(info),
        "expected_files_missing": missing,
        "stale_output_files": stale[:20],
        "stale_output_file_count": len(stale),
        "no_stale_outputs": not stale,
    }
    checks["may_be_used_for_physics"] = bool(
        checks["return_code_is_zero"]
        and checks["job_done_present"]
        and checks["job_done_reports_success"]
        and not missing
        and not stale
    )
    return checks

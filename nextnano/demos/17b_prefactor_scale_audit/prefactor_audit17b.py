"""Demo 17b engine: decompose the residual absolute-chi(2) gap into exact factors.

Demo 17 established that the envelope side is converged: matrix elements moved
by <=2.4 % and transition energies by <=0.22 % when the Dirichlet box went from
2 nm to 30 nm padding, origin independence held at 2.7e-13, and two independently
written Eq. 2 evaluators agreed to 0.8 %. So the residual 27.6x against the
paper's 2340 pm/V is **not** in the wavefunctions. Demo 17b takes the prefactor
apart instead, and it runs no solver at all.

WHY THIS CAN BE PURE PYTHON, AND WHY IT IS EXACT
================================================
Every quantity swept here -- N_z, the permutation/degeneracy count, the spin
weight, and r_e,hh -- multiplies the WHOLE Eq. 2 triple sum. None of them enters
a denominator, a matrix element, or the k dependence, so none of them can change
the lineshape or the relative weight of any term. Each sweep is therefore an
exact rational or closed-form multiplier on chi(2), and it stays exact even when
the sum itself is only available as a recorded number.

That is a real property of the equation, not a convenience. It is asserted in
code: :func:`verify_multiplicative` re-evaluates the sum with and without a
factor whenever the states are available and refuses to report a multiplier that
does not come out at the analytic value.

The one sweep that is NOT merely a multiplier is C. "Is the heavy-hole Kramers
doublet already counted?" is a question about the existing code, and it is
answered by inspecting where ``spin_degeneracy`` is applied and by measuring the
g_s = 1 vs g_s = 2 ratio -- not by assuming an answer.

THREE LOADING TIERS
===================
``envelopes``
    ``envelopes.csv`` present: the overlap and position matrices are rebuilt
    from the amplitudes, and the Eq. 2 sum is recomputed here.
``matrix_elements``
    ``matrix_elements.json`` present: the sum is recomputed from the stored
    matrices. Still an independent evaluation -- this module implements Eq. 2 in
    ANGULAR FREQUENCY with hbar^2 left in the prefactor, where ``_shared/chi2.py``
    uses energy denominators and cancels it. Agreement is a genuine cross-check
    of both.
``summary``
    Only ``physics_summary.json``: the sum cannot be rebuilt, because the summary
    records the diagonal overlaps but not <psi_e1|psi_hh2> or <psi_e2|psi_hh1>.
    The baseline is then the recorded value and ``sum_recomputed`` is False in
    every artifact. The multipliers are unaffected, for the reason above.

NOTHING IS FITTED. No factor is promoted because it makes the number larger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

# --- physical constants (CODATA 2018), SI unless the name says otherwise -----
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
HC_EV_NM = 1239.841984

#: Curated hand-off directories, newest naming first. Both spellings are
#: accepted because both have been created by hand; see .gitignore.
RESULTS_DIR_NAMES = ("demo_17", "demo17")


class Audit17bError(RuntimeError):
    """An audit that would report a number it cannot stand behind."""


# ---------------------------------------------------------------------------
# Sweep D -- the Kane unit-cell dipole length
# ---------------------------------------------------------------------------


def kane_r_e_hh_nm(*, kane_energy_eV: float, band_gap_eV: float) -> float:
    """``r_e,hh = (hbar / E_g) * sqrt(E_p / (2 m_0))``, in nm.

    The two-band Kane relation. ``E_p = 2 p_cv^2 / m_0`` defines the momentum
    matrix element, and ``r_cv = hbar p_cv / (m_0 E_g)`` converts it to a length
    at the band edge, which is where the interband dipole is evaluated.

    For GaAs (E_p = 28.8 eV, E_g = 1.424 eV at 300 K) this returns **0.736 nm**,
    not the ~1.28 nm sometimes assumed. That is the audit's finding, not a
    tuning knob: 0.736 nm sits 2 % from the published VASP/HSE06 value of
    0.751 nm, so the Kane cross-check CONFIRMS the legacy constant rather than
    boosting it. See :func:`kane_required_inputs_for` for what E_p or E_g would
    have to be for a larger r, and why neither is GaAs.
    """

    for name, value in (("kane_energy_eV", kane_energy_eV),
                        ("band_gap_eV", band_gap_eV)):
        if not math.isfinite(float(value)) or float(value) <= 0:
            raise Audit17bError(f"{name} must be finite and > 0, got {value!r}.")
    e_p_J = float(kane_energy_eV) * ELEMENTARY_CHARGE_C
    e_g_J = float(band_gap_eV) * ELEMENTARY_CHARGE_C
    r_m = (REDUCED_PLANCK_J_S / e_g_J) * math.sqrt(e_p_J / (2.0 * ELECTRON_MASS_KG))
    return r_m * 1.0e9


def kane_momentum_p_cv(kane_energy_eV: float) -> float:
    """``p_cv = sqrt(m_0 E_p / 2)`` in kg m/s, reported alongside r."""

    return math.sqrt(
        ELECTRON_MASS_KG * float(kane_energy_eV) * ELEMENTARY_CHARGE_C / 2.0
    )


def kane_required_inputs_for(
    target_r_nm: float, *, kane_energy_eV: float, band_gap_eV: float
) -> dict[str, float]:
    """What E_p or E_g would have to be to make the Kane formula give ``target_r``.

    Reported so a mismatch between an expected r and the formula's r is
    attributable rather than mysterious. r scales as ``sqrt(E_p) / E_g``.
    """

    target_m = float(target_r_nm) * 1.0e-9
    e_g_J = float(band_gap_eV) * ELEMENTARY_CHARGE_C
    required_e_p_J = ((target_m * e_g_J / REDUCED_PLANCK_J_S) ** 2) * 2.0 * ELECTRON_MASS_KG
    required_e_g_J = (REDUCED_PLANCK_J_S / target_m) * math.sqrt(
        float(kane_energy_eV) * ELEMENTARY_CHARGE_C / (2.0 * ELECTRON_MASS_KG)
    )
    return {
        "target_r_nm": float(target_r_nm),
        "required_kane_energy_eV_at_given_gap": required_e_p_J / ELEMENTARY_CHARGE_C,
        "required_band_gap_eV_at_given_kane_energy": (
            required_e_g_J / ELEMENTARY_CHARGE_C
        ),
        "given_kane_energy_eV": float(kane_energy_eV),
        "given_band_gap_eV": float(band_gap_eV),
    }


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseArtifacts:
    """Everything Demo 17 recorded for one case, plus what tier supplied it."""

    case_id: str
    tier: str
    recorded_chi2_pm_per_V: float
    recorded_peak_pm_per_V: float | None
    recorded_peak_nm: float | None
    electron_energies_eV: np.ndarray
    heavy_hole_energies_eV: np.ndarray
    settings: Mapping[str, Any]
    overlap_eh: np.ndarray | None = None
    z_e_nm: np.ndarray | None = None
    z_h_nm: np.ndarray | None = None
    source_paths: tuple[str, ...] = ()

    @property
    def can_recompute_sum(self) -> bool:
        return (
            self.overlap_eh is not None
            and self.z_e_nm is not None
            and self.z_h_nm is not None
        )


def resolve_results_dir(explicit: Path | None = None) -> Path:
    """Find Demo 17's curated hand-off directory, either spelling."""

    if explicit is not None:
        path = Path(explicit)
        if not path.is_dir():
            raise Audit17bError(f"results directory not found: {path}")
        return path
    root = Path(__file__).resolve().parents[3] / "demo_results"
    for name in RESULTS_DIR_NAMES:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise Audit17bError(
        f"no Demo 17 results under {root}; looked for "
        + " and ".join(RESULTS_DIR_NAMES)
        + ". Copy the run's physics_summary.json (and, for a recomputed sum, "
        "matrix_elements.json or envelopes.csv) from the work laptop."
    )


def _find_case_artifact(results_dir: Path, case_id: str, filename: str) -> Path | None:
    """Locate a per-case artifact wherever the hand-off happened to put it.

    Every candidate names the case, and a bare ``<results_dir>/<filename>`` is
    deliberately NOT one of them. A top-level ``matrix_elements.json`` would
    otherwise be picked up for whichever case was asked for, so a hand-off that
    copied only case_02's matrices would silently report them as case_01's --
    and the audit would compare a graded structure against abrupt matrices with
    nothing in the output saying so.
    """

    candidates = (
        results_dir / f"paper_target_{case_id}" / filename,
        results_dir / case_id / filename,
        results_dir / f"{case_id}_{filename}",
        results_dir / "cases" / case_id / "physics" / "optical" / "parsed" / filename,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = sorted(results_dir.glob(f"**/{case_id}/**/{filename}"))
    return matches[0] if matches else None


def _matrices_from_envelopes(path: Path, n_e: int, n_h: int):
    """Rebuild the three matrices from signed amplitudes, by trapezoid."""

    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    z = np.asarray(data[:, 0], dtype=float)
    e_cols = [i for i, name in enumerate(header) if name.strip().startswith("psi_e")][:n_e]
    h_cols = [i for i, name in enumerate(header) if name.strip().startswith("psi_hh")][:n_h]
    if len(e_cols) < n_e or len(h_cols) < n_h:
        raise Audit17bError(
            f"{path.name} has {len(e_cols)}/{len(h_cols)} envelope columns, "
            f"fewer than the {n_e}/{n_h} states Eq. 2 uses."
        )
    psi_e = data[:, e_cols]
    psi_h = data[:, h_cols]
    for label, block in (("electron", psi_e), ("heavy hole", psi_h)):
        for index in range(block.shape[1]):
            norm = float(np.trapezoid(block[:, index] ** 2, z))
            if norm <= 0:
                raise Audit17bError(f"{label} state {index + 1} has zero norm.")
            block[:, index] /= math.sqrt(norm)
    overlap = np.array([[float(np.trapezoid(psi_e[:, i] * psi_h[:, j], z))
                         for j in range(n_h)] for i in range(n_e)])
    z_e = np.array([[float(np.trapezoid(psi_e[:, i] * z * psi_e[:, j], z))
                     for j in range(n_e)] for i in range(n_e)])
    z_h = np.array([[float(np.trapezoid(psi_h[:, i] * z * psi_h[:, j], z))
                     for j in range(n_h)] for i in range(n_h)])
    return overlap, z_e, z_h


def load_case(
    results_dir: Path, case_id: str, *, max_states: int = 2
) -> CaseArtifacts:
    """Load one Demo 17 case at the best tier the hand-off supports."""

    summary_path = Path(results_dir) / "physics_summary.json"
    if not summary_path.is_file():
        raise Audit17bError(f"{summary_path} not found; Demo 17b needs it.")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    record = next(
        (row for row in payload.get("cases", []) if row.get("case_id") == case_id), None
    )
    if record is None:
        available = [row.get("case_id") for row in payload.get("cases", [])]
        raise Audit17bError(f"{case_id} not in {summary_path.name}; have {available}.")
    optical = record.get("optical") or {}
    metrics = optical.get("production_metrics") or {}
    if optical.get("chi2_at_1550") is None:
        raise Audit17bError(f"{case_id} has no recorded chi2; it did not complete.")

    e_energies = np.asarray(metrics["electron_energies_eV"], dtype=float)[:max_states]
    h_energies = np.asarray(metrics["heavy_hole_energies_eV"], dtype=float)[:max_states]
    settings = dict((payload.get("corrections") or {}).get("production_settings") or {})

    sources: list[str] = [str(summary_path)]
    overlap = z_e = z_h = None
    tier = "summary"

    envelopes = _find_case_artifact(Path(results_dir), case_id, "envelopes.csv")
    if envelopes is not None:
        overlap, z_e, z_h = _matrices_from_envelopes(
            envelopes, e_energies.size, h_energies.size
        )
        tier = "envelopes"
        sources.append(str(envelopes))
    else:
        elements = _find_case_artifact(
            Path(results_dir), case_id, "matrix_elements.json"
        )
        if elements is not None:
            blob = json.loads(elements.read_text(encoding="utf-8"))
            overlap = np.asarray(blob["overlap_electron_hole"], dtype=float)
            z_e = np.asarray(blob["position_matrix_electron_nm"], dtype=float)
            z_h = np.asarray(blob["position_matrix_heavy_hole_nm"], dtype=float)
            overlap = overlap[:e_energies.size, :h_energies.size]
            z_e = z_e[:e_energies.size, :e_energies.size]
            z_h = z_h[:h_energies.size, :h_energies.size]
            tier = "matrix_elements"
            sources.append(str(elements))

    return CaseArtifacts(
        case_id=case_id,
        tier=tier,
        recorded_chi2_pm_per_V=float(optical["chi2_at_1550"]),
        recorded_peak_pm_per_V=optical.get("spectral_peak_chi2"),
        recorded_peak_nm=optical.get("spectral_peak_wavelength_nm"),
        electron_energies_eV=e_energies,
        heavy_hole_energies_eV=h_energies,
        settings=settings,
        overlap_eh=overlap,
        z_e_nm=z_e,
        z_h_nm=z_h,
        source_paths=tuple(sources),
    )


# ---------------------------------------------------------------------------
# An independent Eq. 2, in angular frequency
# ---------------------------------------------------------------------------


def chi2_from_matrices(
    case: CaseArtifacts,
    wavelength_nm: float,
    *,
    n_wells_per_metre: float,
    r_e_hh_nm: float,
    k_max_per_nm: float,
    k_points: int,
    spin_degeneracy: int,
    broadening_meV: float,
    electron_mass_m0: float,
    heavy_hole_inplane_mass_m0: float,
    extra_prefactor: float = 1.0,
) -> complex:
    """Eq. 2 for SHG, written in ANGULAR FREQUENCY with hbar^2 in the prefactor.

    ``_shared/chi2.py`` writes the denominators in energy, which cancels the
    hbar^2 that the published Eq. 3 carries explicitly. That is a legitimate
    rewriting and exactly the kind of step that can hide a factor, so this
    module deliberately does it the other way: Gamma is converted to rad/s and
    the hbar^2 stays put. Agreement between the two is then evidence about both.

    Dimensions close on m/V:

        N_z e^3 r^2 / (6 eps0 hbar^2)   ->  C m^2 J^-1 s^-2
        sum (z in m, 1/omega^2, k in m^-2) ->  s^2 m^-1
        product                             ->  C m J^-1  ==  m/V
    """

    if not case.can_recompute_sum:  # pragma: no cover - guarded by callers
        raise Audit17bError(
            f"{case.case_id} was loaded at tier '{case.tier}', which has no "
            "overlap or position matrices, so the sum cannot be recomputed."
        )
    overlap = np.asarray(case.overlap_eh, dtype=float)
    z_e_m = np.asarray(case.z_e_nm, dtype=float) * 1.0e-9
    z_h_m = np.asarray(case.z_h_nm, dtype=float) * 1.0e-9
    n_e, n_h = overlap.shape

    omega = (HC_EV_NM / float(wavelength_nm)) * ELEMENTARY_CHARGE_C / REDUCED_PLANCK_J_S
    gamma_rad = float(broadening_meV) * 1.0e-3 * ELEMENTARY_CHARGE_C / REDUCED_PLANCK_J_S

    k = np.linspace(0.0, float(k_max_per_nm) * 1.0e9, int(k_points))
    reduced = ELECTRON_MASS_KG / (
        1.0 / float(electron_mass_m0) + 1.0 / float(heavy_hole_inplane_mass_m0)
    )
    kinetic_J = (REDUCED_PLANCK_J_S**2) * k**2 / (2.0 * reduced)
    # (1/A) sum_k -> int d^2k/(2 pi)^2 = (1/2 pi) int k dk, times spin.
    weights = np.gradient(k) * k / (2.0 * math.pi) * float(spin_degeneracy)
    weights[0] *= 0.5
    weights[-1] *= 0.5

    transitions = (
        case.electron_energies_eV[:n_e, None] - case.heavy_hole_energies_eV[None, :n_h]
    ) * ELEMENTARY_CHARGE_C
    omega_nm = (transitions[:, :, None] + kinetic_J[None, None, :]) / REDUCED_PLANCK_J_S

    two_photon = omega_nm - 2.0 * omega + 1j * gamma_rad
    one_photon = omega_nm - omega + 1j * gamma_rad

    accumulated = np.zeros(k.size, dtype=complex)
    for m in range(n_h):
        for n in range(n_e):
            for l in range(n_e):
                numerator = overlap[n, m] * z_e_m[n, l] * overlap[l, m]
                if numerator:
                    accumulated += numerator / (two_photon[n, m] * one_photon[l, m])
            for l in range(n_h):
                numerator = overlap[n, m] * z_h_m[m, l] * overlap[n, l]
                if numerator:
                    accumulated -= numerator / (two_photon[n, m] * one_photon[n, l])

    r_m = float(r_e_hh_nm) * 1.0e-9
    prefactor = (
        float(n_wells_per_metre)
        * ELEMENTARY_CHARGE_C**3
        * r_m**2
        / (6.0 * VACUUM_PERMITTIVITY_F_PER_M * REDUCED_PLANCK_J_S**2)
    )
    return complex(prefactor * float(extra_prefactor) * np.dot(weights, accumulated) * 1.0e12)


def production_prefactor_pm_per_V(
    *, n_wells_per_metre: float, r_e_hh_nm: float
) -> float:
    """``N_z e^3 r^2 / (6 eps0)`` in the units ``_shared/chi2.py`` uses.

    Recomputed here from CODATA so the two prefactor assemblies can be compared
    directly. Demo 18 records this as ``production_prefactor``; agreement is a
    cross-check that needs no wavefunctions and therefore works at every tier.
    """

    r_m = float(r_e_hh_nm) * 1.0e-9
    raw = (
        float(n_wells_per_metre)
        * ELEMENTARY_CHARGE_C**3
        * r_m**2
        / (6.0 * VACUUM_PERMITTIVITY_F_PER_M)
    )
    # nm -> m on z, nm^-2 -> m^-2 on the k weights, eV^-2 -> J^-2 on the
    # denominators, then m/V -> pm/V.
    return raw * (1.0e-9 * 1.0e18 / ELEMENTARY_CHARGE_C**2) * 1.0e12


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Multiplier:
    """One candidate factor: what it is, how big, and whether it is defensible."""

    sweep: str
    variant: str
    multiplier: float
    exact: bool
    #: True only when a cited source REQUIRES the change. Reported-only factors
    #: are never folded into the defensible cumulative.
    promotable: bool
    rationale: str
    detail: Mapping[str, Any] = field(default_factory=dict)
    verified_numerically: bool | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "sweep": self.sweep,
            "variant": self.variant,
            "multiplier": self.multiplier,
            "exact": self.exact,
            "promotable": self.promotable,
            "verified_numerically": self.verified_numerically,
            "rationale": self.rationale,
            **{f"detail_{k}": v for k, v in self.detail.items()},
        }


def verify_multiplicative(
    case: CaseArtifacts, base_kwargs: Mapping[str, Any], changed: Mapping[str, Any],
    expected: float, *, wavelength_nm: float, tolerance: float = 1e-9,
) -> bool | None:
    """Re-evaluate the sum with a factor changed and confirm the analytic ratio.

    Returns ``None`` when the tier cannot recompute the sum -- "not checked" is
    a different answer from "checked and correct", and the artifacts say which.
    """

    if not case.can_recompute_sum:
        return None
    base = abs(chi2_from_matrices(case, wavelength_nm, **base_kwargs))
    probe = abs(chi2_from_matrices(case, wavelength_nm, **{**base_kwargs, **changed}))
    if base == 0.0:
        return None
    return abs(probe / base - expected) <= tolerance * max(1.0, expected)


def sweep_a_nz(
    case: CaseArtifacts, cfg: Mapping[str, Any], base_kwargs: Mapping[str, Any],
    wavelength_nm: float,
) -> list[Multiplier]:
    """A -- what length does N_z count wells per?

    chi(2) is linear in N_z, so every entry here is exact by construction and the
    numerical verification is a check that the plumbing agrees, not a discovery.
    """

    block = cfg["sweeps"]["A_nz"]
    baseline = float(base_kwargs["n_wells_per_metre"])
    out: list[Multiplier] = []
    for variant in block["variants"]:
        wells = float(variant["wells"])
        length_nm = float(variant["length_nm"])
        n_z = wells / (length_nm * 1.0e-9)
        ratio = n_z / baseline
        out.append(Multiplier(
            sweep="A_nz",
            variant=str(variant["id"]),
            multiplier=ratio,
            exact=True,
            promotable=bool(variant.get("promotable", False)),
            rationale=str(variant["rationale"]),
            detail={
                "wells": wells, "length_nm": length_nm,
                "n_wells_per_metre": n_z, "baseline_n_wells_per_metre": baseline,
            },
            verified_numerically=verify_multiplicative(
                case, base_kwargs, {"n_wells_per_metre": n_z}, ratio,
                wavelength_nm=wavelength_nm,
            ),
        ))
    return out


def sweep_b_permutation(
    case: CaseArtifacts, cfg: Mapping[str, Any], base_kwargs: Mapping[str, Any],
    wavelength_nm: float,
) -> list[Multiplier]:
    """B -- permutation and degeneracy counting.

    Two candidates, and the important thing about them is that they are probably
    NOT independent. The Bloembergen/Boyd degeneracy factor for SHG is what a
    permutation sum over the two input photons produces, and Demo 16F measured
    Eq. 1 / Eq. 2 = 3.000000 using ``identity_only`` permutations -- i.e. with no
    permutation sum applied at all. Multiplying both would very likely count the
    same physics twice, so each is reported separately, neither is promotable,
    and :func:`cumulative` refuses to combine them without being told which
    reading is intended.
    """

    block = cfg["sweeps"]["B_permutation"]
    out: list[Multiplier] = []
    for variant in block["variants"]:
        factor = float(variant["factor"])
        out.append(Multiplier(
            sweep="B_permutation",
            variant=str(variant["id"]),
            multiplier=factor,
            exact=True,
            promotable=bool(variant.get("promotable", False)),
            rationale=str(variant["rationale"]),
            detail={"factor": factor,
                    "mutually_exclusive_with": variant.get("mutually_exclusive_with")},
            verified_numerically=verify_multiplicative(
                case, base_kwargs, {"extra_prefactor": factor}, factor,
                wavelength_nm=wavelength_nm,
            ),
        ))
    return out


def spin_degeneracy_site() -> dict[str, Any]:
    """Where ``spin_degeneracy`` is actually applied in the shared evaluator.

    A static check, because "is g_s counted once, twice, or not at all?" is a
    question about code rather than about physics. Reading the source is the
    direct answer; the g_s = 1 vs 2 ratio in :func:`sweep_c_spin` is the
    independent confirmation.
    """

    try:
        import chi2 as chi2mod  # noqa: PLC0415 - shared module, may be absent
    except ImportError:
        return {"inspected": False, "reason": "shared chi2 module not importable"}
    sites: dict[str, int] = {}
    for name in ("_k_grid", "chi2_spectrum", "_transition_energies_eV"):
        function = getattr(chi2mod, name, None)
        if function is None:
            continue
        try:
            source = inspect.getsource(function)
        except OSError:  # pragma: no cover - source unavailable
            continue
        sites[name] = source.count("spin_degeneracy")
    total = sum(sites.values())
    return {
        "inspected": True,
        "occurrences_by_function": sites,
        "applied_in_k_weights": bool(sites.get("_k_grid", 0)),
        "applied_again_in_state_sum": bool(sites.get("chi2_spectrum", 0)),
        "total_occurrences": total,
    }


def sweep_c_spin(
    case: CaseArtifacts, cfg: Mapping[str, Any], base_kwargs: Mapping[str, Any],
    wavelength_nm: float,
) -> list[Multiplier]:
    """C -- is the heavy-hole Kramers doublet already counted?

    The one-band HH solver returns orbital envelopes; it does not resolve
    m_j = +-3/2. The +-3/2 doublet is therefore exactly what a spin weight of 2
    represents, and the audit's job is to find out whether that weight is already
    applied. If it is, an additional m_j factor of 2 would be double counting and
    the honest multiplier is 1.0.
    """

    site = spin_degeneracy_site()
    baseline_g = int(base_kwargs["spin_degeneracy"])
    ratio_measured = verify_multiplicative(
        case, base_kwargs, {"spin_degeneracy": 1}, 1.0 / baseline_g,
        wavelength_nm=wavelength_nm,
    )
    already = bool(baseline_g == 2) and (
        site.get("applied_in_k_weights", False) if site.get("inspected") else True
    )
    doubled = bool(
        site.get("inspected")
        and site.get("applied_in_k_weights")
        and site.get("applied_again_in_state_sum")
    )
    if doubled:
        verdict = "double_counted"
        multiplier, rationale = 0.5, (
            "spin_degeneracy is applied in BOTH the k weights and the state sum; "
            "chi(2) is a factor of 2 too large and must be halved."
        )
    elif already:
        verdict = "already_included_once"
        multiplier, rationale = 1.0, (
            "g_s = 2 is applied exactly once, in the k-space weight vector, and "
            "the one-band HH solver does not resolve m_j = +-3/2 separately. The "
            "Kramers doublet is therefore ALREADY counted, and an additional "
            "m_j factor of 2 would be double counting. Multiplier is 1.0."
        )
    else:
        verdict = "missing"
        multiplier, rationale = 2.0, (
            f"the spin weight is {baseline_g}, so the m_j = +-3/2 doublet is not "
            "counted and a factor of 2 is owed."
        )
    return [Multiplier(
        sweep="C_spin_degeneracy",
        variant=verdict,
        multiplier=multiplier,
        exact=True,
        promotable=bool(multiplier != 1.0),
        rationale=rationale,
        detail={
            "baseline_spin_degeneracy": baseline_g,
            "source_inspection": site,
            "g1_over_g2_ratio_matches_analytic": ratio_measured,
        },
        verified_numerically=ratio_measured,
    )]


def sweep_d_kane(
    case: CaseArtifacts, cfg: Mapping[str, Any], base_kwargs: Mapping[str, Any],
    wavelength_nm: float,
) -> list[Multiplier]:
    """D -- r_e,hh from the Kane parameter, against the published 0.751 nm.

    chi(2) goes as r^2, so the multiplier is ``(r_new / r_legacy)^2``.
    """

    block = cfg["sweeps"]["D_kane_dipole"]
    legacy = float(base_kwargs["r_e_hh_nm"])
    out: list[Multiplier] = []
    for variant in block["variants"]:
        e_p = float(variant["kane_energy_eV"])
        e_g = float(variant["band_gap_eV"])
        r_nm = kane_r_e_hh_nm(kane_energy_eV=e_p, band_gap_eV=e_g)
        ratio = (r_nm / legacy) ** 2
        out.append(Multiplier(
            sweep="D_kane_dipole",
            variant=str(variant["id"]),
            multiplier=ratio,
            exact=True,
            promotable=bool(variant.get("promotable", False)),
            rationale=str(variant["rationale"]),
            detail={
                "kane_energy_eV": e_p,
                "band_gap_eV": e_g,
                "r_kane_nm": r_nm,
                "r_legacy_nm": legacy,
                "r_ratio": r_nm / legacy,
                "p_cv_kg_m_per_s": kane_momentum_p_cv(e_p),
                "percent_from_legacy": 100.0 * (r_nm - legacy) / legacy,
            },
            verified_numerically=verify_multiplicative(
                case, base_kwargs, {"r_e_hh_nm": r_nm}, ratio,
                wavelength_nm=wavelength_nm,
            ),
        ))
    expected = block.get("expected_r_nm")
    if expected:
        reference = out[0].detail if out else {}
        out.append(Multiplier(
            sweep="D_kane_dipole",
            variant="expectation_check",
            multiplier=(float(expected) / legacy) ** 2,
            exact=True,
            promotable=False,
            rationale=(
                f"REPORTED ONLY. An r of {expected} nm was expected, but the Kane "
                f"formula gives {reference.get('r_kane_nm', float('nan')):.4f} nm "
                "for GaAs. The inputs that WOULD produce the expected value are "
                "recorded beside this row; neither is GaAs."
            ),
            detail=kane_required_inputs_for(
                float(expected),
                kane_energy_eV=float(block["variants"][0]["kane_energy_eV"]),
                band_gap_eV=float(block["variants"][0]["band_gap_eV"]),
            ),
            verified_numerically=None,
        ))
    return out


# ---------------------------------------------------------------------------
# The budget
# ---------------------------------------------------------------------------


def base_kwargs_from(case: CaseArtifacts, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Demo 17's production settings, as keyword arguments for the evaluator."""

    settings = dict(case.settings)
    defaults = cfg.get("baseline") or {}

    def pick(key: str, fallback_key: str | None = None) -> Any:
        value = settings.get(key)
        if value is None:
            value = defaults.get(fallback_key or key)
        if value is None:
            raise Audit17bError(
                f"neither Demo 17's recorded settings nor demo17b.yaml supply "
                f"{key!r}; the audit will not guess it."
            )
        return value

    return {
        "n_wells_per_metre": float(pick("n_wells_per_metre")),
        "r_e_hh_nm": float(pick("r_e_hh_nm")),
        "k_max_per_nm": float(pick("k_max_per_nm")),
        "k_points": int(pick("k_parallel_points")),
        "spin_degeneracy": int(pick("spin_degeneracy")),
        "broadening_meV": float(pick("broadening_meV")),
        "electron_mass_m0": float(pick("electron_mass_m0")),
        "heavy_hole_inplane_mass_m0": float(pick("heavy_hole_inplane_mass_m0")),
    }


def cumulative(multipliers: Sequence[Multiplier]) -> dict[str, Any]:
    """Two products: what the sources require, and the maximal reading.

    The defensible product takes the largest promotable multiplier from each
    sweep. The maximal product takes the largest of any kind, and is labelled as
    an upper bound rather than a result, because it knowingly includes factors
    that are reported-only and, in sweep B, factors that may double-count each
    other.
    """

    by_sweep: dict[str, list[Multiplier]] = {}
    for entry in multipliers:
        by_sweep.setdefault(entry.sweep, []).append(entry)

    defensible, maximal = 1.0, 1.0
    chosen_defensible, chosen_maximal = {}, {}
    for sweep, entries in sorted(by_sweep.items()):
        promotable = [e for e in entries if e.promotable]
        if promotable:
            best = max(promotable, key=lambda e: e.multiplier)
            defensible *= best.multiplier
            chosen_defensible[sweep] = {"variant": best.variant,
                                        "multiplier": best.multiplier}
        else:
            chosen_defensible[sweep] = {"variant": "none promotable",
                                        "multiplier": 1.0}
        reportable = [e for e in entries if e.variant != "expectation_check"]
        if reportable:
            best = max(reportable, key=lambda e: e.multiplier)
            maximal *= best.multiplier
            chosen_maximal[sweep] = {"variant": best.variant,
                                     "multiplier": best.multiplier}
    return {
        "defensible_product": defensible,
        "defensible_choices": chosen_defensible,
        "maximal_product": maximal,
        "maximal_choices": chosen_maximal,
        "maximal_warning": (
            "UPPER BOUND, not a result. It includes reported-only factors, and "
            "in sweep B it multiplies a permutation factor by an Eq.1/Eq.2 "
            "factor that very likely describe the same counting."
        ),
    }


def audit_case(
    case: CaseArtifacts, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Run all four sweeps for one case and assemble the budget."""

    wavelength = float(cfg["baseline"]["target_wavelength_nm"])
    base_kwargs = base_kwargs_from(case, cfg)

    recomputed = None
    agreement = None
    if case.can_recompute_sum:
        recomputed = abs(chi2_from_matrices(case, wavelength, **base_kwargs))
        agreement = (
            abs(recomputed - case.recorded_chi2_pm_per_V)
            / case.recorded_chi2_pm_per_V
        )
    baseline_value = recomputed if recomputed is not None else case.recorded_chi2_pm_per_V

    multipliers: list[Multiplier] = []
    for sweep in (sweep_a_nz, sweep_b_permutation, sweep_c_spin, sweep_d_kane):
        multipliers.extend(sweep(case, cfg, base_kwargs, wavelength))

    totals = cumulative(multipliers)
    target = float(cfg["target"]["chi2_pm_per_V"])
    prefactor = production_prefactor_pm_per_V(
        n_wells_per_metre=base_kwargs["n_wells_per_metre"],
        r_e_hh_nm=base_kwargs["r_e_hh_nm"],
    )
    return {
        "case_id": case.case_id,
        "loading_tier": case.tier,
        "sum_recomputed": case.can_recompute_sum,
        "sum_recomputed_note": (
            "the Eq. 2 triple sum was rebuilt here from the stored states"
            if case.can_recompute_sum else
            "the recorded chi(2) is used as the baseline; the sum was NOT "
            "rebuilt. Every multiplier below is still exact, because all four "
            "sweeps are prefactors that multiply the whole sum."
        ),
        "source_paths": list(case.source_paths),
        "baseline_pm_per_V": baseline_value,
        "recorded_pm_per_V": case.recorded_chi2_pm_per_V,
        "independent_recompute_pm_per_V": recomputed,
        "independent_recompute_relative_difference": agreement,
        "production_prefactor_pm_per_V_per_summand": prefactor,
        "baseline_settings": base_kwargs,
        "multipliers": [entry.as_record() for entry in multipliers],
        "cumulative": totals,
        "target_pm_per_V": target,
        "defensible_total_pm_per_V": baseline_value * totals["defensible_product"],
        "maximal_total_pm_per_V": baseline_value * totals["maximal_product"],
        "remaining_factor_before": target / baseline_value,
        "remaining_factor_after_defensible": (
            target / (baseline_value * totals["defensible_product"])
        ),
        "remaining_factor_after_maximal": (
            target / (baseline_value * totals["maximal_product"])
        ),
        "no_scale_factor_was_fitted": True,
    }

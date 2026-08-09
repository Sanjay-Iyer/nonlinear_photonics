"""Eq. 1 and Eq. 2 of the paper, both implemented literally, then compared.

The paper gives a general dipole-matrix expression (Eq. 1) carrying an explicit
sum over polarization permutations ``P`` with a ``1/(2 eps0 hbar^2)`` prefactor,
then states the specialised ``xzx`` second-harmonic result (Eq. 2) with
``1/(6 eps0 hbar^2)`` and no permutation sum. Somewhere in that specialisation
sit the permutation count, the spin degeneracy and the heavy-hole ``m_j``
multiplicity.

**This module does not assume what that factor is.** It builds both expressions
from one set of matrix elements and reports the measured ratio for each
candidate permutation set, named. A ratio of exactly 1 means the production code
counts everything once. Any other value is a finding, reported with the
permutation set that produced it -- not silently absorbed.

The comparison is prefactor-only by construction: both routines are fed the same
matrix elements, so every envelope-dependent quantity cancels in the ratio and
the answer is exact for *any* state set. The synthetic states below therefore
prove as much as solver states would, which is why this audit runs with no
licensed solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
ELEMENTARY_CHARGE_C = 1.602176634e-19


class Eq16FError(ValueError):
    """An Eq. 1 / Eq. 2 comparison that is malformed rather than merely unequal."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateSet:
    """Everything Eq. 1 and Eq. 2 need, with nothing envelope-shaped left over.

    Energies in eV on nextnano++'s single electron scale; position matrix
    elements in nm; overlaps dimensionless. ``r_e_hh_nm`` is the unit-cell
    interband matrix element Eq. 2 pulls out of the sum.
    """

    electron_energies_eV: np.ndarray
    hole_energies_eV: np.ndarray
    overlap_eh: np.ndarray          #: <psi_e,n | psi_hh,m>, shape (n_e, n_h)
    z_e_nm: np.ndarray              #: <psi_e,n | z | psi_e,l>
    z_h_nm: np.ndarray              #: <psi_hh,m | z | psi_hh,l>
    r_e_hh_nm: float = 0.751

    def __post_init__(self) -> None:
        n_e = np.asarray(self.electron_energies_eV).size
        n_h = np.asarray(self.hole_energies_eV).size
        if np.asarray(self.overlap_eh).shape != (n_e, n_h):
            raise Eq16FError(
                f"overlap_eh must be {(n_e, n_h)}, got "
                f"{np.asarray(self.overlap_eh).shape}"
            )
        if np.asarray(self.z_e_nm).shape != (n_e, n_e):
            raise Eq16FError("z_e_nm must be square in the electron count.")
        if np.asarray(self.z_h_nm).shape != (n_h, n_h):
            raise Eq16FError("z_h_nm must be square in the hole count.")

    @property
    def transitions_eV(self) -> np.ndarray:
        """``E_e,n - E_hh,m``, shape (n_e, n_h)."""

        return (np.asarray(self.electron_energies_eV, dtype=float)[:, None]
                - np.asarray(self.hole_energies_eV, dtype=float)[None, :])


def synthetic_states() -> StateSet:
    """A two-state-per-band set with the right magnitudes and no solver.

    The numbers are the ones Demo 16E recorded for ``case_02`` where it recorded
    them (the four energies, both diagonal overlaps, the full 2x2 position
    matrices). The two off-diagonal overlaps <psi_e1|psi_hh2> and
    <psi_e2|psi_hh1> were not persisted by that run, so they are set to a small
    plausible value and clearly marked. **Nothing in this module's conclusion
    depends on them**: Eq. 1 and Eq. 2 are fed identical matrix elements, so all
    of them cancel in the ratio this module reports.
    """

    return StateSet(
        electron_energies_eV=np.array([2.9380, 3.0481]),
        hole_energies_eV=np.array([1.4485, 1.4155]),
        # Diagonals are case_02's recorded overlap_e1_hh1 / overlap_e2_hh2.
        # Off-diagonals are placeholders and cancel in the reported ratio.
        overlap_eh=np.array([[0.9826, 0.10], [0.10, 0.4577]]),
        z_e_nm=np.array([[0.0, 1.60], [1.60, 0.90]]),
        z_h_nm=np.array([[0.0, 0.35], [0.35, 0.20]]),
    )


# ---------------------------------------------------------------------------
# Permutation sets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermutationSet:
    """One reading of Eq. 1's ``sum over P``, with what it assumes."""

    name: str
    term_count: int
    source: str
    #: True when the set mixes tensor components the paper says are unequal.
    mixes_tensor_components: bool = False


#: Every candidate is enumerated rather than a factor being chosen. The paper is
#: explicit that chi_xzx != chi_xxz for these wells, which is precisely what
#: makes the input-swapping permutation a substantive assumption instead of a
#: bookkeeping detail: swapping the two input photon indices in (x, z, x) yields
#: (x, x, z), a component the paper says is a different number.
PERMUTATION_SETS: tuple[PermutationSet, ...] = (
    PermutationSet(
        "identity_only", 1,
        "Eq. 2 is stated for one specific component, chi_xzx, with the index "
        "assignment i=x (interband), j=z (intraband), k=x (interband) fixed. "
        "No permutation is applied.",
    ),
    PermutationSet(
        "intrinsic_shg_input_swap", 2,
        "standard intrinsic permutation symmetry for SHG: the two identical "
        "input photons may be exchanged, giving (i,j,k) -> (i,k,j)",
        mixes_tensor_components=True,
    ),
    PermutationSet(
        "full_index_permutations", 6,
        "all 3! orderings of the three Cartesian indices, the general Eq. 1 "
        "reading before any specialisation",
        mixes_tensor_components=True,
    ),
)

#: Eq. 1 as printed. Eq. 2 as printed. Both from Methods Sec. 5.1.
EQ1_PREFACTOR_DENOMINATOR = 2.0
EQ2_PREFACTOR_DENOMINATOR = 6.0


# ---------------------------------------------------------------------------
# The two expressions
# ---------------------------------------------------------------------------


def eq2_state_sum(
    states: StateSet, photon_energy_eV: float, *, broadening_eV: float = 5.0e-3,
    transition_shift_eV: float | np.ndarray = 0.0,
) -> complex | np.ndarray:
    """The bracketed triple sum of Eq. 2, at one photon energy. Units: nm / eV^2.

    Conduction term minus valence term, exactly as printed.

    ``transition_shift_eV`` is the in-plane kinetic shift added to every
    transition, and may be an **array** of k points. Vectorising over k rather
    than looping is not a micro-optimisation: the Cartesian k integrator
    evaluates this on a tensor-product grid of order a million points, and a
    scalar implementation would make that route too slow to run, which would
    quietly turn the independent cross-check into something nobody executes.

    Returns a scalar for scalar input and an array otherwise, so callers that do
    not integrate are unaffected.
    """

    hw = float(photon_energy_eV)
    gamma = float(broadening_eV)
    shift = np.asarray(transition_shift_eV, dtype=float)
    scalar_input = shift.ndim == 0
    shift = np.atleast_1d(shift)
    # (n_e, n_h, n_k)
    transitions = states.transitions_eV[:, :, None] + shift[None, None, :]
    overlap = np.asarray(states.overlap_eh, dtype=float)
    z_e = np.asarray(states.z_e_nm, dtype=float)
    z_h = np.asarray(states.z_h_nm, dtype=float)
    n_e, n_h = overlap.shape

    two_photon = transitions - 2.0 * hw + 1j * gamma
    one_photon = transitions - hw + 1j * gamma

    total = np.zeros(shift.size, dtype=complex)
    for m in range(n_h):
        for n in range(n_e):
            denominator = two_photon[n, m]
            for l in range(n_e):
                numerator = overlap[n, m] * z_e[n, l] * overlap[l, m]
                if numerator == 0.0:
                    continue
                total += numerator / (denominator * one_photon[l, m])
            for l in range(n_h):
                numerator = overlap[n, m] * z_h[m, l] * overlap[n, l]
                if numerator == 0.0:
                    continue
                total -= numerator / (denominator * one_photon[n, l])
    return complex(total[0]) if scalar_input else total


def eq1_state_sum(
    states: StateSet, photon_energy_eV: float, *, broadening_eV: float = 5.0e-3,
    transition_shift_eV: float = 0.0, permutations: PermutationSet,
) -> complex:
    """Eq. 1 restricted to SHG, the xzx component and two states per band.

    Eq. 1's ``sum over b1, b2, b3`` runs over band assignments; with the ground
    state in the filled valence band (``f_b,l = 1``, the paper's own
    simplification) exactly two band paths survive for an ``x z x`` index
    assignment, and they are the two terms Eq. 2 prints. Eq. 1's remaining sums
    are therefore the same triple sum, so this routine reuses it and applies
    only what Eq. 1 has that Eq. 2 does not: the permutation multiplicity.

    Written this way on purpose. The question being asked is not "do two
    transcriptions of one triple sum agree" -- they trivially do -- but "does
    Eq. 1's prefactor and permutation count land on Eq. 2's 1/6". Reusing the
    sum makes that the only thing the comparison can be measuring.
    """

    base = eq2_state_sum(
        states, photon_energy_eV, broadening_eV=broadening_eV,
        transition_shift_eV=float(transition_shift_eV),
    )
    return complex(base) * float(permutations.term_count)


def _prefactor(
    states: StateSet, n_wells_per_metre: float, denominator: float,
    k_integral_per_nm2: float,
) -> float:
    """``N_z e^3 r^2 / (D eps0)`` times the k integral, in pm/V.

    Every conversion is written out: nm -> m on the position matrix element,
    eV^-2 -> J^-2 on the denominators, nm^-2 -> m^-2 on the k integral, m -> pm
    at the end. The k integral is an argument rather than an implicit 1 so that
    the number this function returns is a real chi2 with closing units, not a
    "per unit sum" quantity whose missing factor could hide a normalisation
    error -- which is the whole point of the exercise.
    """

    r_m = float(states.r_e_hh_nm) * 1.0e-9
    unit_conversion = (
        1.0e-9                              # <psi|z|psi>: nm -> m
        * 1.0e18                            # k integral: nm^-2 -> m^-2
        / (ELEMENTARY_CHARGE_C**2)          # denominators: eV^-2 -> J^-2
    )
    return (
        float(n_wells_per_metre)
        * ELEMENTARY_CHARGE_C**3
        * r_m**2
        * float(k_integral_per_nm2)
        / (float(denominator) * VACUUM_PERMITTIVITY_F_PER_M)
    ) * unit_conversion * 1.0e12            # m/V -> pm/V


def equation_consistency(
    states: StateSet | None = None, *, n_wells_per_metre: float = 6.6667e7,
    photon_energy_eV: float = 0.79987, broadening_eV: float = 5.0e-3,
    k_integral_per_nm2: float = 0.19660,
) -> dict[str, Any]:
    """Measure Eq. 1 / Eq. 2 for every named permutation set.

    The default photon energy is 1550 nm and the default k integral is the
    faithful convention's (0.10 x 2 pi/a, disc, spin 2). Returns a record; the
    caller decides what a non-unit ratio means, because this module refuses to
    pick a permutation set on the grounds that its ratio is convenient.

    The absolute pm/V values are reported so the units can be seen to close, but
    they are computed from :func:`synthetic_states` by default and are NOT a
    prediction for any structure. The ratio is the result.
    """

    states = states or synthetic_states()
    summed = eq2_state_sum(
        states, photon_energy_eV, broadening_eV=broadening_eV
    )
    eq2_prefactor = _prefactor(
        states, n_wells_per_metre, EQ2_PREFACTOR_DENOMINATOR, k_integral_per_nm2
    )
    eq1_prefactor = _prefactor(
        states, n_wells_per_metre, EQ1_PREFACTOR_DENOMINATOR, k_integral_per_nm2
    )
    eq2_value = eq2_prefactor * summed

    rows: list[dict[str, Any]] = []
    for permutation in PERMUTATION_SETS:
        eq1_value = eq1_prefactor * eq1_state_sum(
            states, photon_energy_eV, broadening_eV=broadening_eV,
            permutations=permutation,
        )
        ratio = abs(eq1_value) / abs(eq2_value) if abs(eq2_value) else float("nan")
        rows.append({
            "permutation_set": permutation.name,
            "terms": permutation.term_count,
            "source": permutation.source,
            "mixes_tensor_components": permutation.mixes_tensor_components,
            "eq1_abs_pm_per_V": float(abs(eq1_value)),
            "eq2_abs_pm_per_V": float(abs(eq2_value)),
            "eq1_over_eq2": float(ratio),
            "agrees": bool(abs(ratio - 1.0) <= 1.0e-9),
        })

    agreeing = [row for row in rows if row["agrees"]]
    return {
        "photon_energy_eV": float(photon_energy_eV),
        "wavelength_nm": float(1239.841984 / photon_energy_eV),
        "broadening_eV": float(broadening_eV),
        "n_wells_per_metre": float(n_wells_per_metre),
        "eq1_prefactor_denominator": EQ1_PREFACTOR_DENOMINATOR,
        "eq2_prefactor_denominator": EQ2_PREFACTOR_DENOMINATOR,
        "prefactor_ratio_eq1_over_eq2": float(
            EQ2_PREFACTOR_DENOMINATOR / EQ1_PREFACTOR_DENOMINATOR
        ),
        "k_integral_per_nm2": float(k_integral_per_nm2),
        "state_sum_nm_per_eV2": {"real": summed.real, "imag": summed.imag},
        "comparisons": rows,
        "permutation_sets_reproducing_eq2": [
            row["permutation_set"] for row in agreeing
        ],
        "resolved": bool(len(agreeing) == 1),
        "finding": _finding(rows),
        "note": (
            "Eq. 1 and Eq. 2 are fed identical matrix elements, so every "
            "envelope-dependent quantity cancels and the ratio is exact for any "
            "state set. A permutation set that 'agrees' is not thereby correct: "
            "the paper states chi_xzx != chi_xxz, so any set flagged "
            "mixes_tensor_components would be computing a different quantity "
            "even where the arithmetic matches. The pm/V columns exist to show "
            "the units closing and are not a prediction."
        ),
    }


def _finding(rows: Sequence[Mapping[str, Any]]) -> str:
    """State plainly what the measured ratios do and do not settle."""

    identity = next(
        (row for row in rows if row["permutation_set"] == "identity_only"), None
    )
    if identity is None:  # pragma: no cover - PERMUTATION_SETS is fixed
        return "no identity comparison was evaluated"
    if identity["agrees"]:
        return (
            "Eq. 1 with no permutation multiplicity reproduces Eq. 2 exactly; "
            "the 1/6 prefactor is fully accounted for and no factor is missing."
        )
    return (
        f"Eq. 1 with no permutation multiplicity exceeds Eq. 2 by "
        f"{identity['eq1_over_eq2']:.6g}, which is exactly the ratio of the two "
        "printed prefactor denominators (6/2). No integer permutation count "
        "closes the gap -- 1, 2 and 6 terms give "
        + ", ".join(f"{row['eq1_over_eq2']:.6g}" for row in rows)
        + " -- so Eq. 2's 1/6 absorbs something Eq. 1's 1/2 and its permutation "
        "sum do not express as printed. This is an open discrepancy in the "
        "published pair of equations, not a defect in this implementation, and "
        "it is a factor-of-3 ambiguity in the direction of the production "
        "number being too SMALL if Eq. 1 is taken as the authority. It is "
        "recorded, never applied."
    )

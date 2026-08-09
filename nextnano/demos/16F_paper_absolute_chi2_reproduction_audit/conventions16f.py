"""Every convention the absolute chi2 scale depends on, named with its source.

Demo 16E reproduced the paper's *shape* -- transition energies to 0.2%, the
two-photon resonance position to ~15 nm, the graded/abrupt ratio to 1.2% -- and
missed its absolute magnitude by a case-independent factor of roughly 75-85.
A case-independent factor is a prefactor problem, not a physics problem, so this
demo takes the prefactor apart.

The rule this module exists to enforce: **a convention may only change when a
cited equation, crystallographic fact or published sentence requires it.** Every
entry therefore carries a ``source`` and a ``changes_the_number`` note, and the
audit refuses to promote a variant that has no source. There is deliberately no
free scale factor anywhere in Demo 16F -- fitting one would answer the question
by assuming it.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

DEMO_ID = "16F_paper_absolute_chi2_reproduction_audit"
DEMO_VERSION = "demo16f-1.0.0"

#: The paper. Every ``source`` string below cites a section of it.
PAPER = (
    "Ramesh et al., 'Enhanced Interband Optical Nonlinearities from Coupled "
    "Quantum Wells', arXiv:2602.23246v1 (26 Feb 2026)"
)

#: The paper's own layer definition (Sec. 2.2 and Fig. 1a). One period is the
#: two coupled GaAs wells, the tunnelling barrier and the period barrier.
PAPER_PERIOD_NM = 30.0
PAPER_PERIOD_BARRIER_NM = 18.2
PAPER_TUNNEL_BARRIER_NM = 1.8
PAPER_THICK_WELL_NM = 7.1
PAPER_THIN_WELL_NM = 2.9
PAPER_TOTAL_WELL_NM = PAPER_THICK_WELL_NM + PAPER_THIN_WELL_NM
PAPER_AL_FRACTION = 0.55
PAPER_WELLS_PER_PERIOD = 2

#: GaAs zincblende lattice constant, nm.
GAAS_LATTICE_CONSTANT_NM = 0.565325

TARGET_WAVELENGTH_NM = 1550.0


class Conventions16FError(ValueError):
    """A convention was requested that this demo does not define."""


# ---------------------------------------------------------------------------
# Regression targets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """One number the paper states in words, with the sentence that states it."""

    name: str
    value_pm_per_V: float
    wavelength_nm: float
    interfaces: str
    source: str


#: The three explicitly quoted simulation numbers. Fig. 2d's ~4000 pm/V peak is
#: deliberately NOT here: it is read off a figure, the repo's own digitisation
#: carries a +/-15% caveat, and it is inconsistent with the 2340 pm/V the same
#: paper quotes for the *abrupt* case at 1550 nm -- the abrupt case should be the
#: larger of the two. Reproducing three stated numbers with one implementation is
#: a far stronger claim than matching one curve by eye.
TARGETS: tuple[Target, ...] = (
    Target(
        "ideal_abrupt", 2340.0, 1550.0, "abrupt",
        "Sec. 3.1: simulation prediction of 2340 pm/V for abrupt interfaces",
    ),
    Target(
        "eds_al_profile", 1200.0, 1550.0, "measured Al profile",
        "Sec. 3.1: chi(2) = 1200 pm/V from the measured Al profile",
    ),
    Target(
        "eds_ga_profile", 1363.0, 1550.0, "measured Ga profile",
        "Sec. 3.1: chi(2) = 1363 pm/V from the measured Ga profile",
    ),
)

PRIMARY_TARGET = TARGETS[0]


# ---------------------------------------------------------------------------
# N_z -- the number of quantum wells per unit length
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NzDefinition:
    """One reading of "number of quantum wells per unit length"."""

    name: str
    wells_counted_per_period: int
    source: str
    faithful: bool

    def value_per_metre(self, period_nm: float = PAPER_PERIOD_NM) -> float:
        return float(self.wells_counted_per_period) / (float(period_nm) * 1.0e-9)


#: Demo 14/16E production counted one *period*, not the wells inside it. The
#: paper's Methods sentence is unambiguous -- "Nz is the number of quantum wells
#: per unit length" -- and Fig. 1a puts two GaAs wells in every 30 nm period. The
#: well count is therefore the faithful reading and period_density is retained
#: only so the change is visible rather than silent.
NZ_DEFINITIONS: Mapping[str, NzDefinition] = {
    "period_density": NzDefinition(
        "period_density", 1,
        "Demo 14 demo.yaml nz_mode; counts coupled-QW periods, not wells",
        faithful=False,
    ),
    "well_density": NzDefinition(
        "well_density", PAPER_WELLS_PER_PERIOD,
        "Methods Sec. 5.1: 'Nz is the number of quantum wells per unit length'; "
        "Fig. 1a and Sec. 2.2 put two GaAs wells in each 30 nm period",
        faithful=True,
    ),
}


# ---------------------------------------------------------------------------
# Brillouin-zone edge
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoneEdge:
    """Where the Brillouin-zone boundary sits, in reciprocal nm."""

    name: str
    multiplier: float          #: k_edge = multiplier * pi / a
    source: str
    faithful: bool

    def edge_per_nm(self, lattice_nm: float = GAAS_LATTICE_CONSTANT_NM) -> float:
        return self.multiplier * math.pi / float(lattice_nm)


#: The paper says only "one-tenth of the Brillouin zone away from zone center".
#: Which boundary that is, is a crystallographic question, not a preference.
#: GaAs is zincblende (FCC), whose zone is a truncated octahedron with X along
#: <100> at (1,0,0) in units of 2*pi/a -- so Gamma->X is 2*pi/a, not pi/a. The
#: pi/a value inherited from Demo 14 is the *simple cubic* edge and does not
#: describe this lattice. This correction doubles k_max and is made because the
#: crystallography requires it, not because it raises chi2.
ZONE_EDGES: Mapping[str, ZoneEdge] = {
    "legacy_pi_over_a": ZoneEdge(
        "legacy_pi_over_a", 1.0,
        "Demo 14 chi2.py Chi2Settings.k_max_per_nm; the simple-cubic edge, "
        "inherited and never re-derived for zincblende",
        faithful=False,
    ),
    "gamma_to_x_2pi_over_a": ZoneEdge(
        "gamma_to_x_2pi_over_a", 2.0,
        "zincblende (FCC) Brillouin zone: X = (1,0,0) in units of 2*pi/a along "
        "<100>, so the Gamma->X zone boundary is at 2*pi/a",
        faithful=True,
    ),
}

#: Kept at the paper's stated value. Only the *boundary* is under investigation.
BZ_FRACTION = 0.10


# ---------------------------------------------------------------------------
# In-plane integration domain and method
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KDomain:
    """The shape of the region "one-tenth of the Brillouin zone" describes."""

    name: str
    source: str
    faithful: bool


#: "From zone center to one-tenth of the Brillouin zone" reads most naturally as
#: a radius, and the paper's justification -- that the contribution *saturates*
#: there -- is a statement about distance from Gamma, which is isotropic. The
#: square is carried as an explicit alternative because a Cartesian (kx, ky)
#: implementation over independent limits produces it by accident, and its area
#: is 4/pi = 1.273 times the disc's.
K_DOMAINS: Mapping[str, KDomain] = {
    "disc": KDomain(
        "disc",
        "Methods Sec. 5.1: integrated 'from zone center to one-tenth of the "
        "Brillouin zone', i.e. a radius; saturation with |k| is isotropic",
        faithful=True,
    ),
    "square": KDomain(
        "square",
        "the domain a naive independent-limits (kx, ky) integration produces; "
        "area 4/pi times the disc",
        faithful=False,
    ),
}

#: Both must give the same answer on the same domain. They are separate code
#: paths on purpose: agreement is the test that no 2*pi, radial measure, spin
#: factor or area normalisation has been dropped or double counted.
K_METHODS = ("radial", "cartesian")


# ---------------------------------------------------------------------------
# Degeneracy and permutation bookkeeping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DegeneracyFactor:
    """One multiplicity, and the reason it is or is not already counted."""

    name: str
    value: float
    applied: bool
    source: str


#: Every multiplicity that could plausibly be missing or double counted, stated
#: once. ``applied`` records what the production code actually does; the Eq.1 vs
#: Eq.2 test in :mod:`eq16f` is what proves the bookkeeping is right, rather
#: than this table asserting it.
DEGENERACY_LEDGER: tuple[DegeneracyFactor, ...] = (
    DegeneracyFactor(
        "electron_spin", 2.0, True,
        "folded into the k-space weights as spin_degeneracy=2; each in-plane k "
        "state holds two spin orientations",
    ),
    DegeneracyFactor(
        "heavy_hole_mj", 2.0, False,
        "the hh band is doubly degenerate (m_j = +/-3/2) at k=0. Eq. 2's "
        "interband matrix element r_e,hh already refers to one conduction/hh "
        "pair; whether the paper's Nz-normalised sum runs over both m_j "
        "branches is NOT stated. Carried as an explicit open factor, never "
        "applied silently.",
    ),
    DegeneracyFactor(
        "shg_permutation", 1.0, True,
        "Eq. 1 carries an explicit sum over polarization permutations P with a "
        "1/(2 eps0 hbar^2) prefactor; Eq. 2 states the specialised xzx result "
        "with 1/(6 eps0 hbar^2). The 1/6 already absorbs the permutation count, "
        "so no further factor is applied. Verified by eq16f.",
    ),
)


# ---------------------------------------------------------------------------
# Tensor component
# ---------------------------------------------------------------------------

#: The paper is explicit that it computes chi2_xzx, and equally explicit that
#: for these wells chi2_xzx != chi2_xxz, so the usual Kleinman-style factor of
#: two between chi and d does not apply in the normal way. Recorded as a string
#: that every artifact carries, so an absolute number can never be compared
#: against a d-coefficient or an effective SHG coefficient by accident.
TENSOR_QUANTITY = "chi2_xzx"
TENSOR_DECLARATION = (
    "The reported quantity is chi^(2)_xzx(omega, omega) for second-harmonic "
    "generation, in pm/V. It is NOT d_xzx (= chi/2), NOT 2*d_xzx, NOT "
    "chi_xzx + chi_xxz, and NOT an effective SHG coefficient d_eff. The paper "
    "states chi_xzx != chi_xxz for these coupled wells, so the usual factor-of-2 "
    "chi/d relation must not be assumed in either direction."
)
FORBIDDEN_TENSOR_COMPARISONS = (
    "d_xzx", "2*d_xzx", "chi_xzx + chi_xxz", "d_eff", "chi_xxz",
)


# ---------------------------------------------------------------------------
# Held fixed
# ---------------------------------------------------------------------------

#: Parameters this demo must NOT touch, with the sentence that fixes each. They
#: are listed so a reviewer can see that the audit had the opportunity to tune
#: them and declined.
HELD_FIXED: Mapping[str, str] = {
    "broadening_meV=5.0":
        "Methods Sec. 5.1: 'Gamma is the line broadening and is assumed to be "
        "5 meV'",
    "max_states_per_band=2":
        "Methods Sec. 5.1: 'The first two bound states in the heavy hole and "
        "conduction bands are the only states considered'",
    "k_parallel_fraction_of_bz=0.10":
        "Methods Sec. 5.1: integrated 'to one-tenth of the Brillouin zone'; "
        "only which boundary that fraction is taken of is under investigation",
    "r_e_hh_nm=0.751":
        "Ramesh et al., Appl. Phys. Lett. 123, 251111 (2023), VASP/HSE06. "
        "Independently consistent with the GaAs Kane-model value "
        "r_cv = hbar*p_cv/(m0*Eg) = 0.738 nm for E_P = 28.8 eV, E_g = 1.42 eV.",
    "absolute_scale_factor":
        "does not exist and must not be added: fitting a scale answers the "
        "question by assuming it",
}


# ---------------------------------------------------------------------------
# Variant assembly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Convention:
    """One fully specified set of scale conventions."""

    nz: str
    zone_edge: str
    k_domain: str
    k_method: str
    heavy_hole_mj_applied: bool = False
    lattice_constant_nm: float = GAAS_LATTICE_CONSTANT_NM
    period_nm: float = PAPER_PERIOD_NM
    bz_fraction: float = BZ_FRACTION

    def __post_init__(self) -> None:
        for value, table, what in (
            (self.nz, NZ_DEFINITIONS, "N_z definition"),
            (self.zone_edge, ZONE_EDGES, "zone edge"),
            (self.k_domain, K_DOMAINS, "k domain"),
        ):
            if value not in table:
                raise Conventions16FError(
                    f"unknown {what} {value!r}; known: {sorted(table)}"
                )
        if self.k_method not in K_METHODS:
            raise Conventions16FError(
                f"unknown k method {self.k_method!r}; known: {list(K_METHODS)}"
            )

    @property
    def n_wells_per_metre(self) -> float:
        return NZ_DEFINITIONS[self.nz].value_per_metre(self.period_nm)

    @property
    def k_max_per_nm(self) -> float:
        return self.bz_fraction * ZONE_EDGES[self.zone_edge].edge_per_nm(
            self.lattice_constant_nm
        )

    @property
    def heavy_hole_mj_factor(self) -> float:
        return 2.0 if self.heavy_hole_mj_applied else 1.0

    @property
    def fully_faithful(self) -> bool:
        """True when every choice is the one a cited source requires."""

        return (
            NZ_DEFINITIONS[self.nz].faithful
            and ZONE_EDGES[self.zone_edge].faithful
            and K_DOMAINS[self.k_domain].faithful
        )

    def justification(self) -> dict[str, str]:
        return {
            "N_z": NZ_DEFINITIONS[self.nz].source,
            "zone_edge": ZONE_EDGES[self.zone_edge].source,
            "k_domain": K_DOMAINS[self.k_domain].source,
            "k_method": (
                "radial and cartesian are independent implementations of one "
                "integral; they must agree"
            ),
            "heavy_hole_mj": (
                "applied as an explicit open factor of 2"
                if self.heavy_hole_mj_applied
                else "not applied; the paper does not state it"
            ),
        }

    def as_record(self) -> dict[str, Any]:
        return {
            "nz_definition": self.nz,
            "n_wells_per_metre": self.n_wells_per_metre,
            "zone_edge": self.zone_edge,
            "zone_edge_per_nm": ZONE_EDGES[self.zone_edge].edge_per_nm(
                self.lattice_constant_nm
            ),
            "bz_fraction": self.bz_fraction,
            "k_max_per_nm": self.k_max_per_nm,
            "k_domain": self.k_domain,
            "k_method": self.k_method,
            "heavy_hole_mj_factor": self.heavy_hole_mj_factor,
            "lattice_constant_nm": self.lattice_constant_nm,
            "period_nm": self.period_nm,
            "tensor_quantity": TENSOR_QUANTITY,
            "fully_faithful": self.fully_faithful,
            "justification": self.justification(),
        }


#: Ladder values measured on Demo 16E's licensed ``case_02`` envelopes. These are
#: regression anchors, not targets: the licensed solves added later must not move
#: them unless the newly solved wavefunctions genuinely differ, and if they do,
#: the difference must be attributable to the wavefunctions rather than to a
#: convention having been edited.
#:
#: ``legacy`` reproducing Demo 16E's recorded 31.0 pm/V is the load-bearing one.
#: Two independently written evaluators -- production ``chi2.py`` and this demo's
#: :func:`variants16f.chi2_at` -- landing on the same number is what licenses
#: every other row in the table.
LADDER_REGRESSION_PM_PER_V: Mapping[str, float] = {
    "legacy": 30.99,
    "paper_Nz": 61.99,
    "paper_Nz_and_zone": 84.04,
    "independent_cartesian": 84.14,
}

#: Fractional budget for the regression check. Loose enough to absorb quadrature
#: and the two-decimal transcription above, tight enough that any convention
#: change would blow straight through it.
LADDER_REGRESSION_TOLERANCE = 0.02

#: Demo 16E's own recorded chi2(1550) for case_02, from
#: ``demo16e_master_summary.csv``. The ``legacy`` rung must reproduce it.
DEMO16E_CASE02_CHI2_AT_1550 = 30.99419558736484


def check_ladder_regression(
    rows: Sequence[Mapping[str, Any]], *,
    tolerance: float = LADDER_REGRESSION_TOLERANCE,
) -> dict[str, Any]:
    """Do the ladder's rungs still land where the validated run put them?

    A drift here is not automatically an error -- newly solved wavefunctions may
    genuinely differ from Demo 16E's -- but it is never allowed to pass silently,
    because the other thing that moves these numbers is somebody editing a
    convention, and the whole demo rests on that not having happened.
    """

    by_name = {row["variant"]: row for row in rows}
    comparisons = []
    for name, expected in LADDER_REGRESSION_PM_PER_V.items():
        row = by_name.get(name)
        if row is None:
            comparisons.append({"variant": name, "expected": expected,
                                "observed": None, "agrees": None})
            continue
        observed = float(row["chi2_at_1550_pm_per_V"])
        relative = abs(observed - expected) / expected
        comparisons.append({
            "variant": name, "expected": expected, "observed": observed,
            "relative_difference": relative,
            "agrees": bool(relative <= tolerance),
        })
    checked = [row for row in comparisons if row["agrees"] is not None]
    return {
        "tolerance": tolerance,
        "reference": (
            "Demo 16E licensed case_02 envelopes; legacy anchors to "
            f"{DEMO16E_CASE02_CHI2_AT_1550:.5f} pm/V from 16E's master summary"
        ),
        "comparisons": comparisons,
        "variants_checked": len(checked),
        "all_agree": (
            all(row["agrees"] for row in checked) if checked else None
        ),
        "interpretation": (
            "a drift means either the newly solved wavefunctions differ from "
            "Demo 16E's -- legitimate, and attributable to the solve -- or a "
            "convention was edited, which is not"
        ),
    }


#: What Demo 14/16E production actually did. Reproduced here so the audit's
#: first row is the number already on record rather than a re-derivation of it.
LEGACY = Convention(
    nz="period_density", zone_edge="legacy_pi_over_a",
    k_domain="disc", k_method="radial",
)

#: Every choice made because a source requires it, and nothing else.
FAITHFUL = Convention(
    nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
    k_domain="disc", k_method="radial",
)

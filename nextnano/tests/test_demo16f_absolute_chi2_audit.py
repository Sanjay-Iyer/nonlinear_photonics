"""Tests for Demo 16F's absolute-chi2 reproduction audit.

Everything here runs without a solver and without a licence: the audit's whole
point is that the k-space normalisation, the dimensional closure and the
Eq. 1 / Eq. 2 relation are settled by arithmetic, not by a simulation.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for relative in ("16F_paper_absolute_chi2_reproduction_audit",):
    path = str(DEMOS / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import conventions16f as conv  # noqa: E402
import demo16f  # noqa: E402
import eq16f  # noqa: E402
import kspace16f as kspace  # noqa: E402
import run_demo16f  # noqa: E402
import variants16f as variants  # noqa: E402


# ---------------------------------------------------------------------------
# Conventions carry their sources
# ---------------------------------------------------------------------------


def test_every_convention_names_a_source():
    """A convention with no citation cannot be audited, so none may exist."""

    for table in (conv.NZ_DEFINITIONS, conv.ZONE_EDGES, conv.K_DOMAINS):
        for name, entry in table.items():
            assert entry.source.strip(), f"{name} has no source"


def test_faithful_convention_is_well_density_and_zincblende_zone():
    assert conv.FAITHFUL.nz == "well_density"
    assert conv.FAITHFUL.zone_edge == "gamma_to_x_2pi_over_a"
    assert conv.FAITHFUL.fully_faithful
    assert not conv.LEGACY.fully_faithful


def test_well_density_is_exactly_twice_period_density():
    """The paper counts wells; Fig. 1a puts two in every 30 nm period."""

    assert conv.FAITHFUL.n_wells_per_metre == pytest.approx(
        2.0 * conv.LEGACY.n_wells_per_metre
    )


def test_zincblende_zone_edge_is_exactly_twice_the_legacy_edge():
    assert conv.FAITHFUL.k_max_per_nm == pytest.approx(
        2.0 * conv.LEGACY.k_max_per_nm
    )
    assert conv.FAITHFUL.k_max_per_nm == pytest.approx(
        0.10 * 2.0 * math.pi / conv.GAAS_LATTICE_CONSTANT_NM
    )


def test_bz_fraction_is_not_touched():
    """The paper states one-tenth; only the boundary is under investigation."""

    assert conv.BZ_FRACTION == 0.10
    assert conv.LEGACY.bz_fraction == conv.FAITHFUL.bz_fraction == 0.10


def test_no_free_scale_factor_exists_anywhere():
    for module in (conv, kspace, eq16f, variants, demo16f):
        for name in dir(module):
            assert "scale_factor" not in name.lower(), (
                f"{module.__name__}.{name} looks like a fitted scale"
            )


def test_fig2d_peak_is_not_a_target():
    """Only numbers the paper states in words are regression targets."""

    values = {target.value_pm_per_V for target in conv.TARGETS}
    assert values == {2340.0, 1200.0, 1363.0}
    assert 4000.0 not in values


# ---------------------------------------------------------------------------
# k-space: the two implementations, and the closed form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("convention", [conv.LEGACY, conv.FAITHFUL])
def test_two_k_implementations_agree(convention):
    report = kspace.k_normalisation_audit(convention.k_max_per_nm)
    assert report["all_methods_agree"], report["comparisons"]
    assert report["closed_form_reproduced"], report["comparisons"]


def test_radial_disc_reproduces_the_closed_form_exactly():
    """On the disc the angular integral is the exact 2*pi, so this is exact."""

    k_max = conv.FAITHFUL.k_max_per_nm
    numeric = kspace.radial_integral(
        lambda k: np.ones_like(np.asarray(k, dtype=float)),
        k_max_per_nm=k_max, points=2001, domain="disc",
    )
    assert numeric.real == pytest.approx(
        kspace.analytic_disc_constant(k_max), rel=1e-12
    )


def test_square_over_disc_is_the_area_ratio():
    """Catches the pi vs pi**2 slip this audit found in its own first draft."""

    k_max = conv.FAITHFUL.k_max_per_nm
    ratio = (kspace.analytic_square_constant(k_max)
             / kspace.analytic_disc_constant(k_max))
    assert ratio == pytest.approx(4.0 / math.pi, rel=1e-12)


def test_spin_degeneracy_scales_the_integral_linearly():
    k_max = conv.FAITHFUL.k_max_per_nm
    one = kspace.radial_integral(
        lambda k: np.ones_like(np.asarray(k, dtype=float)),
        k_max_per_nm=k_max, spin_degeneracy=1,
    )
    two = kspace.radial_integral(
        lambda k: np.ones_like(np.asarray(k, dtype=float)),
        k_max_per_nm=k_max, spin_degeneracy=2,
    )
    assert two.real == pytest.approx(2.0 * one.real, rel=1e-12)


def test_unknown_domain_and_method_are_refused():
    with pytest.raises(kspace.KSpace16FError):
        kspace.radial_integral(lambda k: k, k_max_per_nm=1.0, domain="hexagon")
    with pytest.raises(kspace.KSpace16FError):
        kspace.k_integral(lambda k: k, k_max_per_nm=1.0, method="montecarlo")


# ---------------------------------------------------------------------------
# The dimensional ledger
# ---------------------------------------------------------------------------


def test_ledger_closes_on_metres_per_volt():
    ledger = kspace.dimensional_ledger(
        n_wells_per_metre=conv.FAITHFUL.n_wells_per_metre,
        r_e_hh_nm=0.751,
        k_integral_per_nm2=kspace.analytic_disc_constant(
            conv.FAITHFUL.k_max_per_nm
        ),
        position_matrix_nm=1.0,
        denominator_product_eV2=1.0,
    )
    assert ledger.closes_on(kspace.CHI2_UNIT)
    assert str(ledger.unit) == "m^1 C^1 J^-1"


def test_every_ledger_row_declares_a_unit_or_is_genuinely_dimensionless():
    ledger = kspace.dimensional_ledger(
        n_wells_per_metre=1.0, r_e_hh_nm=1.0, k_integral_per_nm2=1.0,
        position_matrix_nm=1.0, denominator_product_eV2=1.0,
        heavy_hole_mj_factor=2.0,
    )
    dimensionless = [
        row.label for row in ledger.rows if row.unit == kspace.DIMENSIONLESS
    ]
    # The only dimensionless factor permitted is an explicit multiplicity.
    assert dimensionless == ["hh m_j = +/-3/2"]


def test_ledger_unit_algebra_is_not_accidentally_commutative_nonsense():
    assert kspace.Unit(m=1.0) * kspace.Unit(m=-1.0) == kspace.DIMENSIONLESS
    assert kspace.Unit(J=1.0) * kspace.Unit(J=-2.0) == kspace.Unit(J=-1.0)


# ---------------------------------------------------------------------------
# Eq. 1 vs Eq. 2
# ---------------------------------------------------------------------------


def test_eq1_over_eq2_is_the_printed_prefactor_ratio_for_the_identity():
    report = eq16f.equation_consistency()
    identity = next(
        row for row in report["comparisons"]
        if row["permutation_set"] == "identity_only"
    )
    assert identity["eq1_over_eq2"] == pytest.approx(3.0, rel=1e-12)
    assert report["prefactor_ratio_eq1_over_eq2"] == pytest.approx(3.0)


def test_no_permutation_count_reconciles_the_printed_equations():
    """The open finding, pinned so a later change cannot erase it silently."""

    report = eq16f.equation_consistency()
    assert report["permutation_sets_reproducing_eq2"] == []
    assert report["resolved"] is False
    assert "factor-of-3" in report["finding"] or "3" in report["finding"]


def test_swap_based_permutation_sets_are_flagged_as_mixing_tensor_components():
    """chi_xzx != chi_xxz, so swapping input indices changes the quantity."""

    for row in eq16f.equation_consistency()["comparisons"]:
        if row["permutation_set"] != "identity_only":
            assert row["mixes_tensor_components"]


def test_eq1_eq2_ratio_is_independent_of_the_state_set():
    """Both are fed identical matrix elements, so the ratio must be exact."""

    other = eq16f.StateSet(
        electron_energies_eV=np.array([2.80, 3.20]),
        hole_energies_eV=np.array([1.30, 1.20]),
        overlap_eh=np.array([[0.5, 0.2], [0.3, 0.7]]),
        z_e_nm=np.array([[0.4, 2.5], [2.5, 1.1]]),
        z_h_nm=np.array([[0.2, 0.8], [0.8, 0.5]]),
    )
    default = eq16f.equation_consistency()["comparisons"][0]["eq1_over_eq2"]
    varied = eq16f.equation_consistency(states=other)["comparisons"][0]
    assert varied["eq1_over_eq2"] == pytest.approx(default, rel=1e-12)


def test_state_set_rejects_mismatched_matrix_shapes():
    with pytest.raises(eq16f.Eq16FError):
        eq16f.StateSet(
            electron_energies_eV=np.array([1.0, 2.0]),
            hole_energies_eV=np.array([0.1, 0.2]),
            overlap_eh=np.array([[1.0]]),
            z_e_nm=np.eye(2), z_h_nm=np.eye(2),
        )


# ---------------------------------------------------------------------------
# The variant ladder
# ---------------------------------------------------------------------------


def test_ladder_is_cumulative_and_starts_from_legacy():
    rungs = variants.ladder()
    assert rungs[0].name == "legacy"
    assert rungs[0].convention == conv.LEGACY
    assert [rung.name for rung in rungs][:3] == [
        "legacy", "paper_Nz", "paper_Nz_and_zone",
    ]


def test_only_fully_sourced_variants_are_promotable():
    by_name = {rung.name: rung for rung in variants.ladder()}
    assert variants.promotable(by_name["paper_Nz_and_zone"])
    assert not variants.promotable(by_name["legacy"])
    assert not variants.promotable(by_name["square_domain"])
    assert not variants.promotable(by_name["open_hh_mj_factor"])


def test_nz_change_scales_chi2_exactly_by_two():
    """N_z enters linearly, so this must be exact rather than approximate."""

    states = eq16f.synthetic_states()
    legacy = abs(variants.chi2_at(states, conv.LEGACY, 1550.0))
    paper_nz = abs(variants.chi2_at(
        states,
        conv.Convention(nz="well_density", zone_edge="legacy_pi_over_a",
                        k_domain="disc", k_method="radial"),
        1550.0,
    ))
    assert paper_nz == pytest.approx(2.0 * legacy, rel=1e-10)


def test_heavy_hole_mj_factor_is_opt_in_and_exactly_two():
    states = eq16f.synthetic_states()
    without = abs(variants.chi2_at(states, conv.FAITHFUL, 1550.0))
    with_mj = abs(variants.chi2_at(
        states,
        conv.Convention(nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
                        k_domain="disc", k_method="radial",
                        heavy_hole_mj_applied=True),
        1550.0,
    ))
    assert conv.FAITHFUL.heavy_hole_mj_factor == 1.0
    assert with_mj == pytest.approx(2.0 * without, rel=1e-10)


def test_independent_k_implementations_give_the_same_chi2():
    """The control rung: swapping the integrator must change nothing."""

    states = eq16f.synthetic_states()
    radial = abs(variants.chi2_at(states, conv.FAITHFUL, 1550.0))
    cartesian = abs(variants.chi2_at(
        states,
        conv.Convention(nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
                        k_domain="disc", k_method="cartesian"),
        1550.0, k_points=401,
    ))
    assert cartesian == pytest.approx(
        radial, rel=kspace.K_METHOD_AGREEMENT_TOLERANCE
    )


def test_ladder_report_records_the_target_and_what_is_held_fixed():
    report = variants.evaluate_ladder(eq16f.synthetic_states())
    assert report["target"]["value_pm_per_V"] == 2340.0
    assert report["tensor_quantity"] == "chi2_xzx"
    assert "absolute_scale_factor" in report["held_fixed"]


# ---------------------------------------------------------------------------
# Structure and gates
# ---------------------------------------------------------------------------


def test_paper_structure_sums_to_the_thirty_nanometre_period():
    structure = demo16f.PAPER_STRUCTURE
    structure.validate()
    assert structure.period_nm == pytest.approx(conv.PAPER_PERIOD_NM)
    assert structure.total_well_nm == pytest.approx(10.0)
    assert structure.asymmetry_s == pytest.approx(0.42, abs=5e-3)
    assert structure.interfaces == "abrupt"


def test_a_structure_that_is_not_the_paper_period_is_refused():
    """N_z is derived from the period, so the period is not a free choice."""

    with pytest.raises(demo16f.Demo16FError):
        demo16f.PaperStructure(period_barrier_nm=12.0).validate()


def test_domain_sweep_includes_the_papers_own_period_barrier():
    assert conv.PAPER_PERIOD_BARRIER_NM in demo16f.DOMAIN_SWEEP_NM
    assert demo16f.DOMAIN_SWEEP_NM == tuple(sorted(demo16f.DOMAIN_SWEEP_NM))


def test_bound_state_gate_reports_unavailable_rather_than_passing(tmp_path):
    """A missing table must never read as a pass."""

    report = demo16f.bound_state_gate(tmp_path)
    assert report["available"] is False
    assert report["passed"] is None


def test_bound_state_gate_names_the_failing_state(tmp_path):
    import json

    (tmp_path / "quasi_bound_states.json").write_text(json.dumps({
        "policy": "warn",
        "records": [
            {"state": "E1", "in_chi2_sum": True, "bound": True,
             "boundary_probability": 1e-5},
            {"state": "E2", "in_chi2_sum": True, "bound": False,
             "boundary_probability": 3.6e-2,
             "left_boundary_probability": 3.6e-2,
             "right_boundary_probability": 2.4e-2,
             "reason": "boundary probability above 1e-3"},
        ],
    }), encoding="utf-8")
    report = demo16f.bound_state_gate(tmp_path)
    assert report["passed"] is False
    assert report["failing_count"] == 1
    assert report["failing_states"][0]["state"] == "E2"
    assert report["policy_required"] == "fail_case"


def test_domain_convergence_separates_energies_from_dipoles():
    """Converged energies with drifting dipoles must not read as converged."""

    def states(z_e12: float, energy_shift: float = 0.0) -> eq16f.StateSet:
        return eq16f.StateSet(
            electron_energies_eV=np.array([2.94 + energy_shift, 3.06]),
            hole_energies_eV=np.array([1.448, 1.413]),
            overlap_eh=np.array([[0.98, 0.1], [0.1, 0.46]]),
            z_e_nm=np.array([[0.0, z_e12], [z_e12, 0.9]]),
            z_h_nm=np.array([[0.0, 0.35], [0.35, 0.2]]),
        )

    report = demo16f.domain_convergence([
        {"outer_barrier_nm": 18.2, "states": states(1.40)},
        {"outer_barrier_nm": 25.0, "states": states(1.58)},
        {"outer_barrier_nm": 35.0, "states": states(1.60)},
    ])
    assert report["paper_domain_energies_converged"] is True
    assert report["paper_domain_dipoles_converged"] is False
    assert report["converged"] is False
    assert "amplitude" in report["diagnostic"]


def test_matrix_elements_recomputation_matches_a_known_analytic_case():
    """Two orthonormal box states: <1|z|1> = L/2 and <1|2> = 0 by symmetry."""

    length = 10.0
    z = np.linspace(0.0, length, 4001)
    first = np.sqrt(2.0 / length) * np.sin(np.pi * z / length)
    second = np.sqrt(2.0 / length) * np.sin(2.0 * np.pi * z / length)
    band = np.column_stack([first, second])
    elements = demo16f.matrix_elements(z, band, band)
    assert elements["z_e_nm"][0, 0] == pytest.approx(length / 2.0, rel=1e-6)
    assert elements["gram_electron"][0, 1] == pytest.approx(0.0, abs=1e-9)
    assert demo16f.orthonormality_error(elements["gram_electron"]) < 1e-6


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_audit_entry_point_runs_with_no_solver(capsys):
    status, payload = run_demo16f.run_audit()
    assert status == 0
    assert payload["k_space_implementation_verified"] is True
    assert payload["dimensional_ledger"]["closes"] is True
    # The open finding must survive into the artifact rather than be smoothed.
    assert payload["equations_consistent"] is False
    output = capsys.readouterr().out
    assert "chi2_xzx" in output
    assert "2340" in output


def test_plan_lists_the_licensed_work(capsys):
    assert run_demo16f.run_plan() == 0
    output = capsys.readouterr().out
    assert "fail_case" in output
    assert "18.2" in output
    assert "--from-run" in output


def test_from_run_refuses_a_directory_with_no_parsed_optical_output(tmp_path):
    with pytest.raises(demo16f.Demo16FError):
        run_demo16f.run_from_run(tmp_path, "case_02", None)

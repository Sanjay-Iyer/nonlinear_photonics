"""Tests for Demo 11 and the paper's chi(2) equation.

The physics tests are the point. Eq. 2 has three properties that must hold
regardless of the structure, and each of them catches a different class of
error:

* a symmetric structure gives **identically** zero, by parity;
* the result is independent of where the z origin is placed, but only for an
  orthonormal envelope basis;
* the resonances sit at ``2*hbar*omega = E`` and ``hbar*omega = E``.

The reproduction tests then run the real paper structure through the whole
pipeline using genuine nextnano++ 3.0.0 output committed as a fixture.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

import chi2 as chi2mod
import demo_workflow as workflow
import sweeps

import demo11
import report11
import tracking11

DEMOS = Path(__file__).resolve().parents[1] / "demos"
DEMO11 = DEMOS / "11_paper_validation_interband_chi2_acqw"
FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "nextnano_pp_3_0_0"
    / "demo11_acqw_paper"
)

#: The reduced-grid settings the committed fixture was produced with.
FIXTURE_NUMERICS = {
    "active_region_grid_spacing_nm": 0.4,
    "exterior_grid_spacing_nm": 0.6,
    "number_of_electron_states": 2,
    "number_of_hole_states": 2,
    "quantum_region_padding_nm": 6.0,
}


def _fixture_cfg() -> dict:
    cfg = workflow.load_demo_config(DEMO11)
    cfg["numerical"].update(FIXTURE_NUMERICS)
    return cfg


def _machine_yaml(path: Path, results_root: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "portable_root": None,
                "executable": None,
                "database": None,
                "license": None,
                "threads": 2,
                "run_solver": False,
                "results_root": str(results_root),
            }
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Eq. 2: properties that must hold for any structure
# ---------------------------------------------------------------------------


def _well_states(z, centre, width, energies):
    columns = []
    for index in range(1, len(energies) + 1):
        psi = np.zeros_like(z)
        inside = (z >= centre - width / 2) & (z <= centre + width / 2)
        psi[inside] = np.sin(
            index * np.pi * (z[inside] - (centre - width / 2)) / width
        )
        columns.append(psi)
    return chi2mod.BandStates(z, np.asarray(energies), np.column_stack(columns))


def test_symmetric_structure_gives_identically_zero_chi2():
    """Parity forbids a second-order response in a symmetric structure.

    This is the paper's own stated limit at both ends of the asymmetry sweep,
    and it must come out as a hard zero rather than merely a small number.
    """

    z = np.linspace(-25.0, 25.0, 2001)
    electron = _well_states(z, 0.0, 10.0, [1.50, 1.56])
    hole = _well_states(z, 0.0, 10.0, [0.01, 0.04])
    spectrum = chi2mod.chi2_spectrum(
        electron, hole, np.linspace(0.6, 0.95, 51)
    )
    assert float(np.max(np.abs(spectrum.chi2))) < 1e-15


def test_asymmetric_structure_gives_a_nonzero_response():
    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    spectrum = chi2mod.chi2_spectrum(electron, hole, np.linspace(0.6, 0.95, 51))
    assert float(np.max(np.abs(spectrum.chi2))) > 0.0


def test_chi2_is_independent_of_the_z_origin():
    """Eq. 2 contains diagonal dipoles, which individually are origin dependent.

    The dependence cancels between the two terms -- but only for orthonormal
    envelopes. Verifying it end to end confirms both the reading of Eq. 2 and
    the implementation.
    """

    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    error = chi2mod.origin_independence_error(
        electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=137.0
    )
    assert error < 1e-9


# ---------------------------------------------------------------------------
# origin independence near chi2 = 0
# ---------------------------------------------------------------------------
#
# The 2026-07-31 licensed run reported a FAIL for the symmetric structure at
# s = 0. Its chi(2) was 5.7e-14 -- zero, by parity -- and the check divided the
# origin-shift residual by that, turning ~1e-14 of rounding noise into a
# "relative error" of 0.139. These tests pin down both regimes and the boundary
# between them, so the fix cannot regress into either a false failure or a free
# pass.


def _asymmetric_pair(z=None):
    """Two bands with genuinely asymmetric, orthonormal envelopes."""

    z = np.linspace(-25.0, 25.0, 2001) if z is None else z
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    return electron, hole


def _symmetric_pair():
    """An exactly symmetric structure: chi(2) is identically zero by parity."""

    z = np.linspace(-25.0, 25.0, 2001)
    return (
        _well_states(z, 0.0, 10.0, [1.50, 1.56]),
        _well_states(z, 0.0, 10.0, [0.01, 0.04]),
    )


def _near_zero_pair(jitter=1.0e-12):
    """Symmetric to within rounding: what a real solver actually returns.

    The exactly symmetric case above cancels to a hard 0.0 and so never
    exercises the noise path. A real nextnano++ symmetric structure does not:
    the 2026-07-31 run gave |chi(2)| = 5.7e-14 with an origin-shift residual of
    about 1e-14, which is the regime that produced the false failure. A tiny
    linear tilt on the envelopes reproduces exactly that regime.
    """

    z = np.linspace(-25.0, 25.0, 2001)
    electron = _well_states(z, 0.0, 10.0, [1.50, 1.56])
    tilted = chi2mod.BandStates(
        z, electron.energies_eV, electron.envelopes * (1.0 + jitter * z[:, None]), "e"
    )
    return tilted, _well_states(z, 0.0, 10.0, [0.01, 0.04])


def test_origin_check_uses_the_relative_residual_when_chi2_is_nonzero():
    """Case 1: real magnitude, small residual -> relative comparison, PASS."""

    electron, hole = _asymmetric_pair()
    check = chi2mod.origin_independence(
        electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=137.0
    )
    assert check.comparison_mode == chi2mod.ORIGIN_MODE_RELATIVE
    assert check.scale > check.scale_floor
    assert check.relative_residual is not None
    assert check.relative_residual < 1e-9
    assert check.passed


def test_origin_check_fails_a_nonzero_chi2_with_an_excessive_residual():
    """Case 2: real magnitude, residual too large -> FAIL, not explained away.

    A non-orthonormal basis is what actually produces origin dependence, so the
    tolerance is tightened against a genuine spectrum instead of hand-feeding a
    fake residual: the point is that the relative branch can still fail.
    """

    electron, hole = _asymmetric_pair()
    check = chi2mod.origin_independence(
        electron,
        hole,
        np.linspace(0.6, 0.95, 51),
        shift_nm=137.0,
        relative_tolerance=1e-30,
    )
    assert check.comparison_mode == chi2mod.ORIGIN_MODE_RELATIVE
    assert not check.passed
    assert "above" in check.reason


def test_origin_check_switches_to_absolute_when_chi2_vanishes_by_parity():
    """Case 3: chi(2) = 0, residual under the absolute tolerance -> PASS.

    This is the exact case the licensed run got wrong. The residual is real
    rounding noise of order 1e-14; what must not happen is dividing it by an
    equally tiny scale.
    """

    electron, hole = _near_zero_pair()
    check = chi2mod.origin_independence(
        electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=100.0
    )
    assert check.comparison_mode == chi2mod.ORIGIN_MODE_ABSOLUTE_NEAR_ZERO
    assert check.scale <= check.scale_floor
    assert check.relative_residual is None
    # The residual is real rounding noise, not zero -- this is the case the old
    # code divided by the scale and reported as a 14% relative error.
    assert 0.0 < check.absolute_residual < 1e-12
    assert check.absolute_residual / check.scale > 1e-4
    assert check.passed

    # And the exactly symmetric limit, which cancels to a hard zero, passes too.
    exact = chi2mod.origin_independence(
        *_symmetric_pair(), np.linspace(0.6, 0.95, 51), shift_nm=100.0
    )
    assert exact.comparison_mode == chi2mod.ORIGIN_MODE_ABSOLUTE_NEAR_ZERO
    assert exact.absolute_residual == 0.0
    assert exact.passed


def test_origin_check_still_fails_a_near_zero_chi2_with_a_large_residual():
    """Case 4: chi(2) = 0 but the residual is too big -> FAIL.

    Near-zero must not become a free pass. With the absolute tolerance driven
    below the actual rounding noise, the same symmetric structure has to fail.
    """

    electron, hole = _near_zero_pair()
    check = chi2mod.origin_independence(
        electron,
        hole,
        np.linspace(0.6, 0.95, 51),
        shift_nm=100.0,
        absolute_tolerance=1e-30,
    )
    assert check.comparison_mode == chi2mod.ORIGIN_MODE_ABSOLUTE_NEAR_ZERO
    assert check.absolute_residual > check.absolute_tolerance
    assert not check.passed
    assert check.relative_residual is None


def test_origin_check_never_produces_nan_or_inf_near_zero():
    """Case 5: nothing in the record is NaN or infinite at the parity zero.

    A NaN here would propagate into the sweep summary and the scorecard as a
    silently missing value rather than as a failure.
    """

    for electron, hole in (_symmetric_pair(), _near_zero_pair()):
        check = chi2mod.origin_independence(
            electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=100.0
        )
        assert math.isfinite(check.absolute_residual)
        assert math.isfinite(check.scale)
        for key, value in check.as_record().items():
            if isinstance(value, float):
                assert math.isfinite(value), key
        # The convenience wrapper must be finite too.
        error = chi2mod.origin_independence_error(
            electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=100.0
        )
        assert math.isfinite(error)


def test_origin_check_records_which_comparison_it_used():
    """The mode is part of the result, not something to be inferred later."""

    modes = {
        chi2mod.origin_independence(
            *pair, np.linspace(0.6, 0.95, 31)
        ).comparison_mode
        for pair in (_asymmetric_pair(), _symmetric_pair())
    }
    assert modes == {
        chi2mod.ORIGIN_MODE_RELATIVE,
        chi2mod.ORIGIN_MODE_ABSOLUTE_NEAR_ZERO,
    }


def test_origin_tolerances_come_from_the_demo_yaml():
    """The thresholds are configuration, not constants buried in the code."""

    analysis_cfg = workflow.load_demo_config(DEMO11)["analysis"]
    for key in (
        "maximum_origin_dependence",
        "origin_independence_absolute_tolerance",
        "origin_independence_scale_floor",
        "origin_independence_shift_nm",
    ):
        assert key in analysis_cfg, key
    # The floor has to separate the paper structure (order 1) from a parity
    # zero (order 1e-14) with room to spare on both sides.
    floor = float(analysis_cfg["origin_independence_scale_floor"])
    assert 1e-12 < floor < 1e-3


def test_non_orthonormal_envelopes_are_refused():
    z = np.linspace(-25.0, 25.0, 1001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    # Deliberately non-orthogonal: both columns overlap heavily.
    bad = chi2mod.BandStates(z, np.array([1.50, 1.56]),
                             np.column_stack([left, left + 0.5 * right]), "e")
    good = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left, right]), "hh")
    )
    with pytest.raises(chi2mod.Chi2Error, match="not orthonormal"):
        chi2mod.chi2_spectrum(bad, good, [0.8])


def test_resonances_sit_at_the_two_photon_and_one_photon_energies():
    resonances = chi2mod.resonance_wavelengths_nm([1.49, 1.62])
    assert resonances["two_photon_resonance_nm"][1] == pytest.approx(1530.7, abs=1.0)
    assert resonances["one_photon_resonance_nm"][1] == pytest.approx(765.3, abs=1.0)
    # A peak of |chi2| really lands at the two-photon resonance.
    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = np.linspace(1450.0, 1750.0, 1201)
    spectrum = chi2mod.chi2_spectrum(
        electron, hole, chi2mod.photon_energy_eV(grid)
    )
    transitions = (electron.energies_eV[:, None] - hole.energies_eV[None, :]).ravel()
    expected = [2.0 * chi2mod.HC_EV_NM / value for value in transitions]
    assert min(abs(spectrum.peak()["wavelength_nm"] - e) for e in expected) < 6.0


def test_narrower_broadening_sharpens_the_resonance():
    z = np.linspace(-25.0, 25.0, 1501)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = chi2mod.photon_energy_eV(np.linspace(1450.0, 1750.0, 1501))
    broad = chi2mod.chi2_spectrum(
        electron, hole, grid, chi2mod.Chi2Settings(broadening_meV=20.0)
    )
    narrow = chi2mod.chi2_spectrum(
        electron, hole, grid, chi2mod.Chi2Settings(broadening_meV=2.0)
    )
    assert narrow.peak()["magnitude"] > broad.peak()["magnitude"]


# ---------------------------------------------------------------------------
# how many states Eq. 2 actually sums over
# ---------------------------------------------------------------------------
#
# The 2026-07-31 run swept 3, 4 and 6 solver states and got chi(2) agreeing to
# ~1e-13, which read as convergence. It was not: chi2_spectrum caps the sum at
# max_states_per_band, so all three cases summed identical terms. These tests
# make the truncation explicit and prove that widening it really does change
# both the term count and the answer.


def _three_state_pair():
    """Three states per band, the third with deliberately nonzero couplings."""

    z = np.linspace(-25.0, 25.0, 1501)
    a = np.exp(-((z + 4.0) / 2.0) ** 2)
    b = np.exp(-((z - 3.0) / 1.4) ** 2)
    c = np.exp(-((z - 8.0) / 2.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(
            z,
            np.array([1.50, 1.56, 1.63]),
            np.column_stack([a + 0.3 * b, b - 0.3 * a + 0.2 * c, c + 0.25 * b]),
            "e",
        )
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(
            z,
            np.array([0.01, 0.04, 0.08]),
            np.column_stack([a + 0.15 * b, b - 0.15 * a + 0.1 * c, c + 0.2 * a]),
            "hh",
        )
    )
    return electron, hole


def test_supplying_more_states_does_not_by_itself_widen_the_sum():
    """Extra solver states are truncated, and the diagnostics say so.

    This is the defect behind the apparent state-count convergence: the number
    of states handed in is not the number used, and nothing used to record the
    difference.
    """

    electron, hole = _three_state_pair()
    result = chi2mod.chi2_spectrum(electron, hole, [0.8])
    assert result.diagnostics["electron_states_supplied"] == 3
    assert result.diagnostics["electron_states_used"] == 2
    assert result.diagnostics["electron_states_discarded_by_truncation"] == 1
    assert result.diagnostics["max_states_per_band"] == 2
    # 2 holes x 2 electrons x (2 conduction + 2 valence partners).
    assert result.diagnostics["triple_sum_terms_evaluated"] == 16


def test_widening_the_state_window_changes_the_term_count_and_the_answer():
    """The synthetic proof the audit asks for.

    If the extra states carry nonzero matrix elements, then raising
    max_states_per_band must change both how many terms are evaluated and the
    value of chi(2). Anything else means the knob is not connected.
    """

    electron, hole = _three_state_pair()
    two = chi2mod.chi2_spectrum(
        electron, hole, [0.8], chi2mod.Chi2Settings(max_states_per_band=2)
    )
    three = chi2mod.chi2_spectrum(
        electron, hole, [0.8], chi2mod.Chi2Settings(max_states_per_band=3)
    )
    assert two.diagnostics["triple_sum_terms_evaluated"] == 16
    assert three.diagnostics["triple_sum_terms_evaluated"] == 54
    assert three.diagnostics["triple_sum_terms_significant"] > (
        two.diagnostics["triple_sum_terms_significant"]
    )
    # And the numbers genuinely differ -- not at the 1e-13 level that a
    # disconnected knob produces.
    relative_change = abs(three.chi2[0] - two.chi2[0]) / abs(two.chi2[0])
    assert relative_change > 1e-6


def test_state_window_is_configuration_not_a_hidden_keyword():
    cfg = workflow.load_demo_config(DEMO11)
    assert cfg["metric"]["max_states_per_band"] == 2
    settings = demo11.chi2_settings(cfg)
    assert settings.max_states_per_band == 2
    assert settings.as_record()["max_states_per_band"] == 2
    # And it is swept as its own convergence axis, separately from the number
    # of states the solver is asked for.
    assert cfg["analysis"]["convergence"]["chi2_max_states_per_band"] == [2, 3, 4]
    stage2 = [
        case
        for case in demo11.build_cases(cfg)
        if case.metadata["stage"] == "stage2"
        and "max_states_per_band" in case.swept
    ]
    assert [case.config["metric"]["max_states_per_band"] for case in stage2] == [2, 3, 4]
    # Each such case must request at least as many solver states as the sum uses,
    # or the widened window would have nothing to widen onto.
    for case in stage2:
        assert (
            case.config["numerical"]["number_of_electron_states"]
            >= case.config["metric"]["max_states_per_band"]
        )


def test_a_window_below_two_states_is_refused():
    with pytest.raises(chi2mod.Chi2Error, match="at least 2"):
        chi2mod.Chi2Settings(max_states_per_band=1)


# ---------------------------------------------------------------------------
# physical-state tracking
# ---------------------------------------------------------------------------


def _crossing_sweep(n_points=9):
    """A synthetic avoided crossing: two states swap character across the sweep.

    Built so that energy ordering and physical identity genuinely disagree past
    the midpoint, which is what the refined Stage 3 sweep is being run to test
    for.
    """

    z = np.linspace(-20.0, 20.0, 801)
    left = np.exp(-((z + 5.0) / 2.5) ** 2)
    right = np.exp(-((z - 5.0) / 2.5) ** 2)
    points = []
    for index in range(n_points):
        # mix runs 0 -> 1: state A starts left-localised and ends right-localised.
        mix = index / (n_points - 1)
        angle = mix * np.pi / 2
        a = np.cos(angle) * left + np.sin(angle) * right
        b = -np.sin(angle) * left + np.cos(angle) * right
        # An arbitrary global sign, as a real solver is free to produce.
        if index % 2:
            b = -b
        energies = np.array([1.50 + 0.001 * index, 1.52 - 0.001 * index])
        points.append(
            tracking11.SweepPoint(
                case_id=f"p{index:02d}",
                sweep_value=0.36 + 0.02 * index,
                z_nm=z,
                energies_eV=energies,
                envelopes=np.column_stack([a, b]),
            )
        )
    return points


def test_tracking_follows_a_branch_through_a_crossing():
    tracked, diagnostics = tracking11.track_band(_crossing_sweep(), band="electron")
    assert diagnostics["method"] == "envelope_overlap"
    assert len(tracked) == 18
    # Every state keeps a label, and each sweep point carries both identities.
    for state in tracked:
        assert state.tracked_label in (1, 2)
        assert state.raw_index in (1, 2)
    # Confidences and margins are recorded from the second point onward.
    later = [s for s in tracked if s.overlap_with_previous is not None]
    assert later
    for state in later:
        assert 0.0 <= state.overlap_with_previous <= 1.0
        assert state.second_best_overlap is not None
        assert state.assignment_margin == pytest.approx(
            state.overlap_with_previous - state.second_best_overlap
        )


def test_tracking_aligns_the_arbitrary_global_sign():
    """A solver may flip an eigenvector's sign between runs; a branch must not."""

    tracked, _ = tracking11.track_band(_crossing_sweep(), band="electron")
    assert any(state.sign_flip_applied for state in tracked)


def test_tracking_reports_ambiguity_instead_of_guessing():
    """At a genuine 50/50 crossing the tracker must say so, not pick silently."""

    z = np.linspace(-20.0, 20.0, 801)
    left = np.exp(-((z + 5.0) / 2.5) ** 2)
    right = np.exp(-((z - 5.0) / 2.5) ** 2)
    equal_a = (left + right) / np.sqrt(2.0)
    equal_b = (left - right) / np.sqrt(2.0)
    points = [
        tracking11.SweepPoint("p0", 0.40, z, np.array([1.50, 1.52]),
                              np.column_stack([left, right])),
        tracking11.SweepPoint("p1", 0.41, z, np.array([1.505, 1.515]),
                              np.column_stack([equal_a, equal_b])),
    ]
    tracked, diagnostics = tracking11.track_band(
        points, band="electron", minimum_confidence=0.9, minimum_margin=0.3
    )
    assert diagnostics["ambiguous_steps"] == ["p1"]
    ambiguous = [s for s in tracked if s.ambiguous]
    assert ambiguous
    assert all(state.ambiguity_reason != "unambiguous" for state in ambiguous)


def test_tracking_interpolates_between_different_grids():
    """Sweep points whose geometry changed the mesh must still be comparable."""

    coarse = np.linspace(-20.0, 20.0, 401)
    fine = np.linspace(-20.0, 20.0, 811)
    envelope = np.exp(-((fine) / 3.0) ** 2)
    resampled = tracking11.interpolate_onto(
        coarse, fine, np.column_stack([envelope])
    )
    assert resampled.shape == (coarse.size, 1)
    assert float(np.trapezoid(resampled[:, 0] ** 2, coarse)) == pytest.approx(1.0, abs=1e-6)


def test_tracked_reordering_changes_which_states_eq2_sums():
    """Reordering to tracked labels really does hand Eq. 2 different states."""

    z = np.linspace(-25.0, 25.0, 1201)
    left = np.exp(-((z + 4.0) / 2.0) ** 2)
    right = np.exp(-((z - 4.0) / 1.5) ** 2)
    band = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left, right]), "e")
    )
    swapped = [
        tracking11.TrackedState(0.42, "c", "electron", 1, 2, 1.50, None, None, None,
                                False, False, ""),
        tracking11.TrackedState(0.42, "c", "electron", 2, 1, 1.56, None, None, None,
                                False, False, ""),
    ]
    reordered = tracking11.reorder_to_tracked_labels(band, swapped)
    assert reordered.energies_eV[0] == pytest.approx(1.56)
    assert np.allclose(reordered.envelopes[:, 0], band.envelopes[:, 1])


# ---------------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------------


def test_absolute_mode_refuses_without_the_unpublished_inputs():
    with pytest.raises(chi2mod.Chi2Error, match="r_e_hh_nm"):
        chi2mod.Chi2Settings(mode="absolute")
    with pytest.raises(chi2mod.Chi2Error, match="n_wells_per_metre"):
        chi2mod.Chi2Settings(mode="absolute", r_e_hh_nm=0.3)
    # Supplying both is what unlocks it.
    settings = chi2mod.Chi2Settings(
        mode="absolute", r_e_hh_nm=0.3, n_wells_per_metre=3.33e7
    )
    assert settings.units == chi2mod.ABSOLUTE_UNITS


def test_relative_mode_never_claims_pm_per_V():
    settings = chi2mod.Chi2Settings(mode="relative")
    assert "pm/V" not in settings.units
    assert "arbitrary" in settings.units


def test_calibrated_mode_needs_a_named_source_and_fits_one_factor():
    z = np.linspace(-25.0, 25.0, 1501)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = chi2mod.photon_energy_eV(np.linspace(1400.0, 1800.0, 401))
    relative = chi2mod.chi2_spectrum(electron, hole, grid)
    with pytest.raises(chi2mod.Chi2Error, match="source"):
        chi2mod.calibrate(relative, target_pm_per_V=2340.0,
                          wavelength_nm_value=1550.0, source="")
    calibrated = chi2mod.calibrate(
        relative, target_pm_per_V=2340.0, wavelength_nm_value=1550.0,
        source="paper Section 3.1",
    )
    # It hits the target exactly, by construction -- which is why the label says so.
    assert abs(calibrated.at_wavelength(1550.0)) == pytest.approx(2340.0, rel=1e-9)
    assert "calibrated" in calibrated.units
    assert "not an independent prediction" in calibrated.diagnostics["calibration_warning"]
    # Only ONE factor is fitted: the shape is untouched.
    ratio = np.abs(calibrated.chi2) / np.abs(relative.chi2)
    assert float(np.std(ratio)) < 1e-9


def test_absolute_scale_is_linear_in_Nz_and_quadratic_in_r():
    z = np.linspace(-25.0, 25.0, 1001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = [0.8]

    def magnitude(r_nm, n_z):
        settings = chi2mod.Chi2Settings(
            mode="absolute", r_e_hh_nm=r_nm, n_wells_per_metre=n_z
        )
        return abs(chi2mod.chi2_spectrum(electron, hole, grid, settings).chi2[0])

    base = magnitude(0.3, 3.33e7)
    assert magnitude(0.3, 6.66e7) == pytest.approx(2.0 * base, rel=1e-9)
    assert magnitude(0.6, 3.33e7) == pytest.approx(4.0 * base, rel=1e-9)


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_asymmetry_round_trips_and_matches_the_paper():
    assert chi2mod.structural_asymmetry(7.1, 2.9) == pytest.approx(0.42)
    thick, thin = chi2mod.well_widths_from_asymmetry(0.42, 10.0)
    assert thick == pytest.approx(7.1)
    assert thin == pytest.approx(2.9)
    # The symmetric limits the paper names.
    assert chi2mod.well_widths_from_asymmetry(0.0, 10.0) == (5.0, 5.0)
    assert chi2mod.well_widths_from_asymmetry(1.0, 10.0) == (10.0, 0.0)


def test_demo11_geometry_matches_the_published_structure():
    cfg = workflow.load_demo_config(DEMO11)
    stack = demo11.build_stack(cfg)
    intervals = stack.intervals()
    assert intervals["left_well"][1] - intervals["left_well"][0] == pytest.approx(7.1)
    assert intervals["right_well"][1] - intervals["right_well"][0] == pytest.approx(2.9)
    assert (
        intervals["centre_barrier"][1] - intervals["centre_barrier"][0]
    ) == pytest.approx(1.8)
    # One period is exactly 30 nm: 10 nm of well, 1.8 nm tunnel, 18.2 nm barrier.
    assert stack.total_thickness_nm == pytest.approx(30.0)


def test_paper_targets_file_is_complete_and_sourced():
    targets = demo11.paper_targets(DEMO11)
    published = targets["targets"]
    for name in (
        "thick_well_nm", "thin_well_nm", "tunnel_barrier_nm", "aluminium_fraction",
        "ground_interband_transition_eV", "excited_interband_transition_eV",
        "simulated_resonance_nm", "chi2_ideal_abrupt_pm_per_V",
    ):
        assert name in published, name
        assert published[name].get("source"), f"{name} has no source"
        assert published[name].get("kind") in {
            "structural", "spectral", "simulated", "measured", "qualitative", "reference"
        }
    # The unpublished inputs must be recorded as such.
    missing = targets["missing_for_absolute_scale"]
    assert "r_e_hh_nm" in missing and "n_wells_per_metre" in missing


def test_demo11_deck_is_complete_and_deterministic():
    cfg = workflow.load_demo_config(DEMO11)
    template = (DEMO11 / cfg["template"]).read_text(encoding="utf-8")
    first = workflow.render_template(template, demo11.render_values(cfg))
    second = workflow.render_template(template, demo11.render_values(cfg))
    assert first == second
    assert "{{" not in first
    for expected in ("simulate1D{}", "Gamma{ num_ev", "HH{    num_ev",
                     "transition_energies{ Gamma_HH{} }",
                     "overlap_integrals{ Gamma_HH{} }",
                     "dipole_moment_matrix_elements{"):
        assert expected in first, expected


def test_graded_model_adds_linear_ramps_at_every_interface():
    cfg = workflow.load_demo_config(DEMO11)
    cfg["scientific"]["interface_grading_nm"] = 1.0
    template = (DEMO11 / cfg["template"]).read_text(encoding="utf-8")
    graded = workflow.render_template(template, demo11.render_values(cfg))
    # Count inside the structure block only; the deck header mentions the
    # keyword in a comment.
    structure = graded.split("structure{", 1)[1].split("\nclassical{", 1)[0]
    assert structure.count("ternary_linear{") == 4
    assert "alloy_x = [0.55, 0]" in structure
    assert "alloy_x = [0, 0.55]" in structure
    # The abrupt model has none.
    cfg["scientific"]["interface_grading_nm"] = 0.0
    abrupt = workflow.render_template(template, demo11.render_values(cfg))
    abrupt_structure = abrupt.split("structure{", 1)[1].split("\nclassical{", 1)[0]
    assert "ternary_linear{" not in abrupt_structure


def test_demo11_requires_two_bound_states_per_band():
    cfg = workflow.load_demo_config(DEMO11)
    cfg["numerical"]["number_of_electron_states"] = 1
    with pytest.raises(workflow.DemoError, match="two bound states"):
        demo11.render_values(cfg)


# ---------------------------------------------------------------------------
# reproduction, against real nextnano++ output for the published structure
# ---------------------------------------------------------------------------


def test_reproduces_the_published_transition_energies(tmp_path):
    """The headline physics check, on genuine solver output.

    No material parameter was adjusted to obtain this.
    """

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo11.analyse_case(
        _fixture_cfg(), FIXTURE, extracted, plots
    )
    # Paper: ground states separated by 1.49 eV, excited states by 1.62 eV.
    assert observables["transition_e1_hh1_eV"] == pytest.approx(1.49, abs=0.010)
    assert observables["transition_e2_hh2_eV"] == pytest.approx(1.62, abs=0.020)
    assert observables["asymmetry"] == pytest.approx(0.42)
    assert validation["envelopes_orthonormal"] is True
    assert validation["chi2_origin_independent"] is True
    assert validation["two_bound_electron_states"] is True


def test_reproduces_the_published_resonance_wavelengths(tmp_path):
    """The paper's "peaks around 760 nm and 1520 nm" are one statement."""

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, _ = demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    two_photon = observables["predicted_two_photon_resonances_nm"]
    one_photon = observables["predicted_one_photon_resonances_nm"]
    assert min(abs(value - 1520.0) for value in two_photon) < 15.0
    assert min(abs(value - 760.0) for value in one_photon) < 10.0
    # And the end-to-end Eq. 2 scan peaks there too, not just the bare energies.
    assert observables["chi2_peak_wavelength_nm"] == pytest.approx(1520.0, abs=25.0)


def test_states_localise_in_opposite_wells(tmp_path):
    """The coupled-well character the paper's Fig. 1c shows."""

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, _ = demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    assert observables["electron1_thick_well_probability"] > 0.8
    assert observables["electron2_thin_well_probability"] > 0.6
    # e1 in the thick well, e2 in the thin one -- the asymmetry is real.
    assert (
        observables["electron1_thick_well_probability"]
        > observables["electron1_thin_well_probability"]
    )
    assert (
        observables["electron2_thin_well_probability"]
        > observables["electron2_thick_well_probability"]
    )


def test_analysis_writes_the_artifacts_stage5_needs(tmp_path):
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    for name in ("envelopes.csv", "matrix_elements.json", "chi2_settings.json",
                 "chi2_focused.csv", "electron_states.csv"):
        assert (extracted / name).is_file(), name
    settings = json.loads((extracted / "chi2_settings.json").read_text(encoding="utf-8"))
    assert settings["mode"] == "relative"
    assert settings["r_e_hh_nm"] is None
    assert settings["assumptions"]


# ---------------------------------------------------------------------------
# stage plumbing and the report
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# the two metrics, and the status vocabulary
# ---------------------------------------------------------------------------


def _fake_case(case_id, stage, **observables):
    spec = sweeps.CaseSpec(
        case_id=case_id, label=case_id, swept={}, config={},
        metadata={"stage": stage, "sweep_kind": stage},
    )
    return sweeps.CaseResult(
        spec=spec, run_dir=Path("."), status="completed",
        observables=dict(observables),
        validation={"envelopes_orthonormal": True, "chi2_origin_independent": True},
    )


def _detuned_sweep():
    """A sweep where the two metrics genuinely disagree about the optimum.

    Modelled on what the licensed run produced: the intrinsic peak grows past
    s = 0.42, but the resonance blue-shifts away from the fixed reference
    wavelength fast enough that the fixed-wavelength value falls. Any report
    that scores the optimum at one wavelength picks the wrong structure.
    """

    return [
        _fake_case("a1", "stage3", asymmetry=0.38,
                   chi2_peak_magnitude=0.13, chi2_relative_at_reference=0.08),
        _fake_case("a2", "stage3", asymmetry=0.42,
                   chi2_peak_magnitude=1.09, chi2_relative_at_reference=0.55),
        _fake_case("a3", "stage3", asymmetry=0.50,
                   chi2_peak_magnitude=1.29, chi2_relative_at_reference=0.54),
        _fake_case("a4", "stage3", asymmetry=0.55,
                   chi2_peak_magnitude=1.28, chi2_relative_at_reference=0.53),
    ]


def test_the_two_metrics_can_disagree_and_both_are_reported():
    results = _detuned_sweep()
    peak = report11._optimum(results, "asymmetry", "chi2_peak_magnitude")
    reference = report11._optimum(results, "asymmetry", "chi2_relative_at_reference")
    assert peak["value"] == pytest.approx(0.50)
    assert reference["value"] == pytest.approx(0.42)
    # And the margin is carried, because an optimum that leads by less than the
    # sweep's own scatter is a ranking rather than a maximum.
    assert peak["runner_up"] == pytest.approx(0.55)
    assert peak["runner_up_margin_fraction"] < 0.02


def test_the_primary_metric_is_the_detuning_independent_one():
    assert report11.PRIMARY_METRIC == "peak_chi2_magnitude"
    assert (
        report11.METRICS[report11.PRIMARY_METRIC]["observable"] == "chi2_peak_magnitude"
    )
    # The secondary metric must never be described as the intrinsic maximum.
    secondary = report11.METRICS["chi2_at_reference_wavelength"]["meaning"]
    assert "application-specific" in secondary
    assert "confounded" in secondary


def test_smoothness_flags_the_cliff_but_not_the_parity_zero():
    """The s = 0 zero is required physics; the 8.5x step next to it is not."""

    results = _detuned_sweep() + [
        _fake_case("a0", "stage3", asymmetry=0.0,
                   chi2_peak_magnitude=7.4e-14, chi2_relative_at_reference=5.7e-14)
    ]
    smoothness = report11._monotone_break(results, "asymmetry", "chi2_peak_magnitude")
    # The pair straddling the parity zero is skipped, and said to be skipped.
    assert smoothness["skipped_pairs"] == ["a0->a1"]
    # What survives is the real discontinuity, not a 1e13 artifact.
    assert smoothness["factor"] == pytest.approx(1.09 / 0.13, rel=1e-6)
    assert smoothness["between"] == [0.38, 0.42]


def test_a_value_exactly_on_its_tolerance_is_neither_pass_nor_fail():
    """s = 0.50 against a paper value of 0.42 lands exactly on the +/-0.08 line.

    Whether that reads as PASS or FAIL is then decided by how 0.42 rounds in
    binary, which is not a physics result. It has to be reported as sitting on
    the boundary.
    """

    entry = report11._entry(
        "asymmetry_optimum_peak_metric", 0.42, 0.50, report11.QUALITATIVE, "",
        "", tolerance=0.08, provisional=True,
    )
    assert entry["at_tolerance_boundary"] is True
    assert entry["outcome"] == "at_tolerance_boundary"
    # Clearly inside or clearly outside must still resolve normally.
    inside = report11._entry("x", 0.42, 0.44, report11.QUALITATIVE, "", "", tolerance=0.08)
    outside = report11._entry("x", 0.42, 0.70, report11.QUALITATIVE, "", "", tolerance=0.08)
    assert inside["outcome"] == "within_tolerance"
    assert not inside["at_tolerance_boundary"]
    assert outside["outcome"] == "outside_tolerance"
    assert not outside["at_tolerance_boundary"]


def test_status_vocabulary_keeps_independent_claims_independent():
    """An unresolved asymmetry optimum must not drag down the resonance claim."""

    cfg = workflow.load_demo_config(DEMO11)
    targets = demo11.paper_targets(DEMO11)
    reference = _fake_case(
        "s1_ref", "stage1",
        transition_e1_hh1_eV=1.48906,
        transition_e2_hh2_eV=1.62967,
        chi2_peak_magnitude=1.09,
        chi2_relative_at_reference=0.5524,
        predicted_two_photon_resonances_nm=[1665.3, 1521.6],
    )
    results = [reference] + _detuned_sweep() + [
        _fake_case("b1", "stage4", tunnel_barrier_nm=1.0,
                   chi2_peak_magnitude=1.86, chi2_relative_at_reference=1.08),
        _fake_case("b2", "stage4", tunnel_barrier_nm=1.8,
                   chi2_peak_magnitude=1.09, chi2_relative_at_reference=0.55),
    ]
    comparison = report11.build(
        cfg=cfg, targets=targets, results=results, reference=reference,
        stage5={"modes": {}},
        stage6={"focused_peak": {"wavelength_nm": 1519.0, "magnitude": 1.09}},
        parent=Path("."), stage3b={"available": False, "reason": "not run"},
    )
    status = {c["claim"]: c["status"] for c in comparison["status"]["claims"]}
    assert status["transition energies (E1-HH1, E2-HH2)"] == report11.REPRODUCED
    assert (
        status["resonance wavelength near 1520 nm, reference structure"]
        == report11.REPRODUCED
    )
    assert status["tunnelling-barrier optimum near 1 nm"] == report11.REPRODUCED
    # The unresolved ones, which must NOT read as reproduced.
    assert status["asymmetry optimum near s = 0.42"] == report11.PROVISIONAL
    assert status["smoothness of chi(2) versus asymmetry"] == report11.FAILED
    assert status["state-count convergence of Eq. 2"] == report11.UNRESOLVED
    assert (
        status["physical-state tracking across the refined sweep"]
        == report11.UNRESOLVED
    )
    assert status["run completed mechanically"] == report11.MECHANICAL


def test_the_asymmetry_optimum_is_never_called_reproduced():
    """The whole point of the status split, asserted directly."""

    cfg = workflow.load_demo_config(DEMO11)
    targets = demo11.paper_targets(DEMO11)
    # Hand it a sweep whose optimum lands exactly on the paper value, so the
    # only thing that can stop it reading as reproduced is the provisional flag.
    results = [
        _fake_case("a1", "stage3", asymmetry=0.42, chi2_peak_magnitude=1.0,
                   chi2_relative_at_reference=1.0),
        _fake_case("a2", "stage3", asymmetry=0.50, chi2_peak_magnitude=0.5,
                   chi2_relative_at_reference=0.5),
    ]
    comparison = report11.build(
        cfg=cfg, targets=targets, results=results, reference=None,
        stage5={"modes": {}}, stage6={}, parent=Path("."),
        stage3b={"available": False, "reason": "not run"},
    )
    entry = next(
        e for e in comparison["entries"]
        if e["quantity"] == "asymmetry_optimum_peak_metric"
    )
    assert entry["within_tolerance"] is True
    assert entry["provisional"] is True
    assert entry["provisional_reason"]
    status = {c["claim"]: c["status"] for c in comparison["status"]["claims"]}
    assert status["asymmetry optimum near s = 0.42"] != report11.REPRODUCED


def test_stage3b_figures_render_from_tracking_rows(tmp_path):
    """The tracking figures only see real data on the licensed laptop.

    Without this they would be exercised for the first time in the middle of a
    long licensed run, which is exactly where a plotting bug is most expensive.
    """

    tracked, _ = tracking11.track_band(_crossing_sweep(), band="electron")
    rows = [state.row() for state in tracked]
    for row in rows:
        row["probability_left_well"] = 0.5
        row["boundary_probability"] = 1e-5
    stage3b = {
        "available": True,
        "rows": rows,
        "comparison": [
            {
                "case_id": state.case_id,
                "asymmetry": state.sweep_value,
                "chi2_peak_magnitude_raw_index": 1.0 + state.sweep_value,
                "chi2_peak_magnitude_tracked": 1.0 + 2 * state.sweep_value,
            }
            for state in tracked
            if state.raw_index == 1
        ],
    }
    report11._tracking_plots(tmp_path, [], stage3b, None)
    for name in (
        "refined_raw_index_branches.png",
        "refined_tracked_branches.png",
        "refined_localization.png",
        "refined_assignment_overlap.png",
        "refined_boundary_probability.png",
        "refined_chi2_raw_vs_tracked.png",
    ):
        assert (tmp_path / name).is_file(), name


def test_every_declared_figure_is_produced_by_a_dry_run(tmp_path):
    """A missing figure must always mean a bug, never "no licence here"."""

    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    assert demo11.main(DEMO11, machine) == 0
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    for name, _ in demo11.PLOT_SET:
        assert (parent / "plots" / name).is_file(), name


def test_case_construction_covers_every_solver_stage():
    cfg = workflow.load_demo_config(DEMO11)
    cases = demo11.build_cases(cfg)
    stages = {case.metadata["stage"] for case in cases}
    assert {"stage1", "stage2", "stage3", "stage4", "stage7"} <= stages
    assert len({case.case_id for case in cases}) == len(cases)
    analysis_cfg = cfg["analysis"]
    assert sum(1 for c in cases if c.metadata["stage"] == "stage3") == len(
        analysis_cfg["asymmetry_sweep"]
    )
    assert sum(1 for c in cases if c.metadata["stage"] == "stage4") == len(
        analysis_cfg["barrier_sweep_nm"]
    )


def test_refined_sweep_covers_the_discontinuity_without_replacing_the_coarse_one():
    """The coarse sweep is context; the refined one resolves the cliff in it.

    Deleting the coarse sweep would destroy the comparison that motivated the
    refinement in the first place, so both must be present and separate.
    """

    cfg = workflow.load_demo_config(DEMO11)
    cases = demo11.build_cases(cfg)
    coarse = [c for c in cases if c.metadata["stage"] == "stage3"]
    refined = [c for c in cases if c.metadata["stage"] == "stage3_refined"]
    assert len(coarse) == len(cfg["analysis"]["asymmetry_sweep"])
    values = sorted(
        demo11.chi2mod.structural_asymmetry(
            float(c.config["scientific"]["thick_well_nm"]),
            float(c.config["scientific"]["thin_well_nm"]),
        )
        for c in refined
    )
    assert values[0] == pytest.approx(0.36)
    assert values[-1] == pytest.approx(0.52)
    assert len(values) == 17
    for lower, upper in zip(values, values[1:]):
        assert upper - lower == pytest.approx(0.01, abs=1e-9)


def test_padding_convergence_is_probed_away_from_the_design_point():
    """A padding scan only at s = 0.42 proves nothing about the rest of the sweep."""

    cfg = workflow.load_demo_config(DEMO11)
    cases = [
        c for c in demo11.build_cases(cfg) if c.metadata["stage"] == "stage2_padding"
    ]
    probe = cfg["analysis"]["convergence"]["padding_at_asymmetry"]
    assert len(cases) == len(probe["asymmetry_values"]) * len(
        probe["quantum_region_padding_nm"]
    )
    probed = {
        round(
            demo11.chi2mod.structural_asymmetry(
                float(c.config["scientific"]["thick_well_nm"]),
                float(c.config["scientific"]["thin_well_nm"]),
            ),
            2,
        )
        for c in cases
    }
    assert probed == set(probe["asymmetry_values"])


def test_asymmetry_sweep_holds_the_total_well_thickness_fixed():
    cfg = workflow.load_demo_config(DEMO11)
    total = float(cfg["scientific"]["thick_well_nm"]) + float(
        cfg["scientific"]["thin_well_nm"]
    )
    for case in demo11.build_cases(cfg):
        if case.metadata["stage"] not in demo11.ASYMMETRY_STAGES:
            continue
        scientific = case.config["scientific"]
        assert (
            float(scientific["thick_well_nm"]) + float(scientific["thin_well_nm"])
        ) == pytest.approx(total)


def test_case_ids_fit_the_windows_path_budget():
    cfg = workflow.load_demo_config(DEMO11)
    work_root = Path(
        r"C:\Code\optics\nextnano\nonlinear_photonics\nextnano\results\demo_runs"
    )
    for case in demo11.build_cases(cfg):
        run_dir = (
            work_root / cfg["demo_id"] / "20260731T000000Z_deadbeef" / "runs" / case.case_id
        )
        assert sweeps.check_path_budget(run_dir) is None, case.case_id


def test_dry_run_produces_the_paper_comparison_artifacts(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    assert demo11.main(DEMO11, machine) == 0
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    for name in (
        "paper_comparison_report.md",
        "assumptions_and_unknowns.yaml",
        "comparison.json",
        "sweep_manifest.json",
        "validation_report.md",
    ):
        assert (parent / name).is_file(), name
    for name in ("paper_targets.csv", "our_results.csv", "comparison_metrics.csv"):
        assert (parent / "tables" / name).is_file(), name

    report = (parent / "paper_comparison_report.md").read_text(encoding="utf-8")
    # The honest headline must lead, not be buried.
    assert "not independently reproducible" in report
    assert "r_e_hh" in report
    # Nothing may be claimed as physically validated on a dry run.
    validation = (parent / "validation_report.md").read_text(encoding="utf-8")
    assert "Physically validated: **False**" in validation

    produced = {path.name for path in (parent / "plots").glob("*.png")}
    for filename, _ in demo11.PLOT_SET:
        assert filename in produced, filename


def test_report_classifies_measured_values_as_out_of_scope(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    comparison = json.loads((parent / "comparison.json").read_text(encoding="utf-8"))
    by_name = {entry["quantity"]: entry for entry in comparison["entries"]}
    # Measured multi-period values depend on band bending, standing waves, and a
    # fitted extraction parameter. They are not electronic-structure predictions.
    for name in (
        "chi2_4_period_pm_per_V",
        "chi2_80_period_pm_per_V",
        "chi2_12_and_16_period_pm_per_V",
        "chi2_growth_interrupted_pm_per_V",
    ):
        assert by_name[name]["classification"] == report11.OUT_OF_SCOPE
        assert by_name[name]["our_value"] is None
    # And the unpublished matrix element is flagged as needing the authors.
    assert (
        by_name["r_e_hh_unit_cell_matrix_element"]["classification"]
        == report11.NEEDS_AUTHORS
    )


def test_absolute_chi2_is_not_reproducible_without_the_missing_inputs(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    manifest = json.loads((parent / "sweep_manifest.json").read_text(encoding="utf-8"))
    absolute = manifest["stage5_chi2_modes"]["modes"].get("absolute", {})
    # demo.yaml leaves r_e_hh_nm and n_wells_per_metre null, so absolute mode
    # must decline rather than invent a scale.
    assert absolute.get("available") is False
    assert "r_e_hh_nm" in absolute.get("reason", "")
    assert "not independently reproducible" in manifest["absolute_scale_disclaimer"].lower() or (
        "cannot be reproduced independently" in manifest["absolute_scale_disclaimer"]
    )


def test_assumptions_file_records_every_unknown(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    data = yaml.safe_load(
        (parent / "assumptions_and_unknowns.yaml").read_text(encoding="utf-8")
    )
    unknowns = data["not_published_by_the_paper"]
    for name in ("r_e_hh_nm", "n_wells_per_metre", "k_parallel_quadrature"):
        assert name in unknowns
    assert any("k" in text and "2" in text for text in data["assumptions"])


def test_a_dry_run_never_reads_as_a_successful_reproduction(tmp_path):
    """`classification` is the kind of comparison; `outcome` is whether it ran.

    Without that split a dry run -- which computes nothing -- would report every
    structural and spectral entry as `directly_reproduced`.
    """

    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    comparison = json.loads((parent / "comparison.json").read_text(encoding="utf-8"))
    by_name = {entry["quantity"]: entry for entry in comparison["entries"]}

    # Nothing was solved, so every physics comparison must be pending.
    for name in (
        "ground_interband_transition",
        "excited_interband_transition",
        "focused_scan_peak_wavelength",
        "asymmetry_optimum_peak_metric",
        "asymmetry_optimum_at_reference_wavelength",
    ):
        assert by_name[name]["outcome"] == "pending", name
        assert by_name[name]["evaluated"] is False
        assert by_name[name]["our_value"] is None

    # Structural transcription IS checkable without a solver, so it evaluates.
    assert by_name["thick_well_nm"]["outcome"] == "within_tolerance"
    assert by_name["thick_well_nm"]["evaluated"] is True

    # The summary counts only evaluated comparisons.
    summary = comparison["summary"]
    assert summary["evaluated"] == sum(
        1 for e in comparison["entries"] if e["evaluated"]
    )
    assert summary["pending"] > 0
    report = (parent / "paper_comparison_report.md").read_text(encoding="utf-8")
    assert "Pending (nothing computed yet)" in report

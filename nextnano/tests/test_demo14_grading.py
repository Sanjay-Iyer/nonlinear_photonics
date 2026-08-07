"""Demo 14 grading renderer: bounds, 10-90 fidelity, and overlap behaviour.

These are the solver-free checks required before any licensed Demo 14 run
(spec 10E part 1, 13A, 33). The central claim under test is that the Demo 14
parameterization is **feasible by construction**: there is no draw from the beta
search space that produces an unbuildable or out-of-bounds composition profile,
so a Demo 13 style ``subresolution_grade`` refusal cannot recur.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

# conftest puts every demos/NN_* directory on sys.path, so the uniquely-named
# demo modules import directly.
import grading14

XMAX = grading14.NOMINAL_AL_FRACTION
MESH = 0.05
DOMAIN = (0.0, 40.0)
CENTRE = 20.0


def build(profile, barrier, wl, wr, *, mesh=MESH, domain=DOMAIN):
    return grading14.build_profile(
        profile=profile,
        barrier_thickness_nm=barrier,
        gaas_to_algaas_width_10_90_nm=wl,
        algaas_to_gaas_width_10_90_nm=wr,
        barrier_centre_nm=CENTRE,
        domain_nm=domain,
        mesh_nm=mesh,
    )


# --- the 10-90 definition is common across families ------------------------


@pytest.mark.parametrize("profile", grading14.PROFILE_FAMILIES)
@pytest.mark.parametrize("width", [0.4, 0.7, 1.0, 1.4])
def test_isolated_interface_realizes_the_requested_10_90_width(profile, width):
    """A thick barrier isolates the interfaces, so realized == requested.

    This is the property that makes the optimizer-facing width comparable
    between families: 1.0 nm must mean the same physical interface for linear,
    fermi, erf and cosine alike.
    """

    built = build(profile, 8.0, width, width)
    d = built.diagnostics
    for key in (
        "realized_gaas_to_algaas_grading_width_10_90_peakref_nm",
        "realized_algaas_to_gaas_grading_width_10_90_peakref_nm",
    ):
        assert d[key] == pytest.approx(width, abs=2 * MESH), (
            f"{profile} {key}: realized {d[key]} vs requested {width}"
        )


@pytest.mark.parametrize("profile", grading14.PROFILE_FAMILIES)
def test_families_agree_with_each_other_at_equal_requested_width(profile):
    """Equal requested widths give equal realized widths across families."""

    reference = build("linear", 8.0, 1.0, 1.0).diagnostics[
        "realized_gaas_to_algaas_grading_width_10_90_peakref_nm"
    ]
    got = build(profile, 8.0, 1.0, 1.0).diagnostics[
        "realized_gaas_to_algaas_grading_width_10_90_peakref_nm"
    ]
    assert got == pytest.approx(reference, abs=2 * MESH)


def test_the_two_interfaces_are_independent_and_correctly_oriented():
    """A narrow left and wide right interface must not be swapped."""

    d = build("erf", 8.0, 0.4, 1.4).diagnostics
    left = d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"]
    right = d["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"]
    assert left == pytest.approx(0.4, abs=2 * MESH)
    assert right == pytest.approx(1.4, abs=2 * MESH)
    assert left < right
    assert d["grading_slope_max_left_per_nm"] > d["grading_slope_max_right_per_nm"]


# --- bounded by construction ----------------------------------------------


def test_thousands_of_samples_stay_bounded_and_buildable():
    """13A's success criterion: 100% of valid draws build a bounded profile."""

    rng = np.random.default_rng(20260807)
    failures: list[str] = []
    for case in grading14.sample_search_space(rng, 4000):
        built = build(
            case["profile"],
            case["barrier_thickness_nm"],
            case["gaas_to_algaas_width_10_90_nm"],
            case["algaas_to_gaas_width_10_90_nm"],
        )
        y = built.al_fraction
        d = built.diagnostics
        if not np.all(np.isfinite(y)):
            failures.append(f"non-finite: {case}")
        if y.min() < -1e-12 or y.max() > XMAX + 1e-12:
            failures.append(f"out of [0, {XMAX}]: {y.min()}..{y.max()} {case}")
        if not d["profile_within_bounds"]:
            failures.append(f"profile_within_bounds false: {case}")
        if not d["profile_monotone_coordinates"]:
            failures.append(f"non-monotone coordinates: {case}")
        if d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"] is None:
            failures.append(f"peak-referenced left width undefined: {case}")
        if d["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"] is None:
            failures.append(f"peak-referenced right width undefined: {case}")
    assert not failures, "\n".join(failures[:20])


def test_peak_referenced_width_is_always_defined_including_extreme_overlap():
    """The thinnest barrier with the widest interfaces is still measurable."""

    for profile in grading14.PROFILE_FAMILIES:
        d = build(profile, 0.85, 1.4, 1.4).diagnostics
        assert d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"] is not None
        assert d["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"] is not None
        assert d["profile_within_bounds"]


def test_profile_is_continuous_on_the_mesh():
    """No step larger than the steepest analytic slope can produce."""

    for profile in grading14.PROFILE_FAMILIES:
        built = build(profile, 1.0, 0.4, 0.4)
        jumps = np.abs(np.diff(built.al_fraction))
        # 0.4 nm 10-90 width cannot move more than the full range in one mesh cell.
        assert jumps.max() < XMAX * 0.5, f"{profile} discontinuity {jumps.max()}"


# --- the nullable nominal reference ----------------------------------------


def test_overlapping_thin_barrier_reports_null_nominal_width_and_does_not_fail():
    """The approved behaviour: record the null, never reject the trial."""

    d = build("erf", 0.85, 1.4, 1.4).diagnostics
    assert d["nominal_90pct_threshold_reached"] is False
    assert d["realized_gaas_to_algaas_grading_width_10_90_nominalref_nm"] is None
    assert d["realized_algaas_to_gaas_grading_width_10_90_nominalref_nm"] is None
    # ... while the peak-referenced pair stays fully defined.
    assert d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"] is not None
    assert d["grading_interfaces_overlap"] is True
    assert d["realized_peak_al_fraction"] < 0.90 * XMAX


def test_thick_barrier_reaches_nominal_composition_and_reports_both_widths():
    d = build("erf", 2.5, 0.4, 0.4).diagnostics
    assert d["nominal_90pct_threshold_reached"] is True
    assert d["realized_gaas_to_algaas_grading_width_10_90_nominalref_nm"] is not None
    assert d["grading_interfaces_overlap"] is False
    assert d["realized_peak_al_fraction"] == pytest.approx(XMAX, abs=1e-3)


def test_the_null_rate_matches_the_audited_fraction_of_the_search_space():
    """~19% of the beta space never reaches 0.495; that must not drift silently."""

    rng = np.random.default_rng(11)
    null = 0
    total = 1500
    for case in grading14.sample_search_space(rng, total):
        d = build(
            case["profile"],
            case["barrier_thickness_nm"],
            case["gaas_to_algaas_width_10_90_nm"],
            case["algaas_to_gaas_width_10_90_nm"],
        ).diagnostics
        if not d["nominal_90pct_threshold_reached"]:
            null += 1
    fraction = null / total
    assert 0.05 < fraction < 0.40, f"null nominal-width fraction {fraction:.3f}"


# --- overlap diagnostics ---------------------------------------------------


def test_overlap_flag_tracks_peak_composition():
    thin = build("fermi", 0.85, 1.2, 1.2).diagnostics
    thick = build("fermi", 2.5, 0.4, 0.4).diagnostics
    assert thin["grading_interfaces_overlap"] is True
    assert thick["grading_interfaces_overlap"] is False
    assert thin["realized_peak_al_fraction"] < thick["realized_peak_al_fraction"]


def test_al_dose_increases_with_barrier_thickness():
    doses = [
        build("erf", t, 0.8, 0.8).diagnostics["integrated_al_dose_nm_equivalent"]
        for t in (0.85, 1.5, 2.5)
    ]
    assert doses == sorted(doses)
    # The dose is an equivalent thickness, so it should track the barrier itself.
    assert doses[-1] == pytest.approx(2.5, abs=0.25)


def test_fwhm_is_defined_and_ordered():
    narrow = build("erf", 1.0, 0.4, 0.4).diagnostics["realized_barrier_fwhm_nm"]
    wide = build("erf", 2.5, 0.4, 0.4).diagnostics["realized_barrier_fwhm_nm"]
    assert narrow is not None and wide is not None
    assert wide > narrow


# --- imported profile payload ----------------------------------------------


def test_import_datafile_is_well_formed():
    built = build("erf", 1.8, 1.0, 1.0)
    text = grading14.import_datafile(built)
    rows = [line.split() for line in text.strip().splitlines()]
    assert len(rows) == len(built.x_nm)
    xs = [float(r[0]) for r in rows]
    ys = [float(r[1]) for r in rows]
    assert all(b > a for a, b in zip(xs, xs[1:])), "coordinates must strictly ascend"
    assert len(set(xs)) == len(xs), "duplicate coordinates"
    assert all(0.0 <= y <= XMAX + 1e-9 for y in ys)
    assert all(math.isfinite(y) for y in ys)


def test_import_datafile_refuses_malformed_input():
    built = build("erf", 1.8, 1.0, 1.0)
    broken = grading14.CompositionProfile(
        x_nm=np.array([0.0, 0.0, 1.0]),
        al_fraction=np.array([0.0, 0.1, 0.2]),
        x_nm_continuous=built.x_nm_continuous,
        al_fraction_continuous=built.al_fraction_continuous,
        request=built.request,
    )
    with pytest.raises(grading14.Grading14Error, match="ascending"):
        grading14.import_datafile(broken)

    empty = grading14.CompositionProfile(
        x_nm=np.array([]),
        al_fraction=np.array([]),
        x_nm_continuous=built.x_nm_continuous,
        al_fraction_continuous=built.al_fraction_continuous,
        request=built.request,
    )
    with pytest.raises(grading14.Grading14Error, match="zero-length"):
        grading14.import_datafile(empty)


# --- rendering -------------------------------------------------------------


def test_linear_renders_natively_and_the_rest_import():
    assert grading14.RENDER_METHOD["linear"] == "ternary_linear"
    for profile in ("fermi", "erf", "cosine"):
        assert grading14.RENDER_METHOD[profile] == "ternary_import"

    linear = grading14.render_structure_blocks(build("linear", 1.8, 1.0, 1.0))
    assert "ternary_linear{" in linear["structure_block"]
    assert linear["import_block"] == ""
    assert linear["datafile"] == ""

    erf = grading14.render_structure_blocks(build("erf", 1.8, 1.0, 1.0))
    assert "ternary_import{" in erf["structure_block"]
    assert "import{" in erf["import_block"]
    assert "format = DAT" in erf["import_block"]
    assert erf["datafile"].strip()


def test_no_staircase_renderer_is_reachable():
    """Demo 13's 16-sublayer staircase must not be the Demo 14 production path."""

    for profile in grading14.PROFILE_FAMILIES:
        blocks = grading14.render_structure_blocks(build(profile, 1.8, 1.0, 1.0))
        assert blocks["structure_block"].count("ternary_constant{") <= 1


def test_growth_coordinate_is_x():
    """Confirmed against keywords_nnp.xml and the validated Demo 13 deck."""

    blocks = grading14.render_structure_blocks(build("linear", 1.8, 1.0, 1.0))
    assert " x = [" in blocks["structure_block"]
    for axis in (" y = [", " z = ["):
        assert axis not in blocks["structure_block"]


# --- mesh fidelity ---------------------------------------------------------


def test_finer_mesh_reduces_realization_error():
    coarse = build("erf", 1.8, 0.4, 0.4, mesh=0.10).diagnostics
    fine = build("erf", 1.8, 0.4, 0.4, mesh=0.025).diagnostics
    assert fine["grading_profile_realization_rms_error"] <= coarse[
        "grading_profile_realization_rms_error"
    ]


def test_production_mesh_realization_error_is_small():
    """0.05 nm must represent the narrowest allowed interface faithfully."""

    for profile in grading14.PROFILE_FAMILIES:
        d = build(profile, 1.8, 0.40, 0.40).diagnostics
        assert d["grading_profile_realization_max_error"] < 0.02 * XMAX, profile


# --- input validation ------------------------------------------------------


def test_unknown_profile_is_refused_and_names_the_supported_set():
    with pytest.raises(grading14.Grading14Error, match="abrupt"):
        build("abrupt", 1.8, 1.0, 1.0)
    with pytest.raises(grading14.Grading14Error, match="unknown grading profile"):
        build("gaussian", 1.8, 1.0, 1.0)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_widths_and_thicknesses_are_refused(bad):
    with pytest.raises(grading14.Grading14Error):
        build("erf", 1.8, bad, 1.0)
    with pytest.raises(grading14.Grading14Error):
        build("erf", bad, 1.0, 1.0)


# --- one material per region (the licensed-run failure) --------------------


def _regions_in(deck: str) -> list[str]:
    """Split a rendered deck's structure{} into individual region{} bodies."""

    import re

    start = deck.index("structure{")
    depth, i = 0, start
    for i in range(start, len(deck)):
        if deck[i] == "{":
            depth += 1
        elif deck[i] == "}":
            depth -= 1
            if depth == 0:
                break
    body = deck[start:i]
    return re.findall(r"region\{(.*?)\n    \}", body, flags=re.S)


@pytest.mark.parametrize("profile", grading14.PROFILE_FAMILIES)
def test_each_region_declares_exactly_one_material(profile):
    """nextnano++ rejects a region carrying several material specifications.

    The first licensed gate died on exactly this: the linear renderer emitted
    ternary_linear + ternary_constant + ternary_linear into one region and the
    solver answered "Too many instances of 'ternary_linear'" and terminated
    before solving anything.
    """

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "demos" / "_shared"))
    import demo14

    cfg = demo14.load_config()
    params = {
        "asymmetry_s": 0.42, "nominal_central_barrier_thickness_nm": 1.8,
        "gaas_to_algaas_grading_width_10_90_nm": 1.0,
        "algaas_to_gaas_grading_width_10_90_nm": 1.0,
        "grading_profile": profile,
    }
    geometry = demo14.geometry_for(cfg, params)
    built = demo14.build_grading(cfg, params, geometry)
    blocks = grading14.render_structure_blocks(built)
    deck = demo14.render_deck(cfg, geometry, built, blocks)

    materials = ("binary{", "ternary_constant{", "ternary_linear{",
                 "ternary_import{")
    bodies = _regions_in(deck)
    assert bodies, "the deck declares no regions at all"
    for body in bodies:
        count = sum(body.count(m) for m in materials)
        # At most one: nextnano++ rejects a region carrying several. Zero is
        # legal -- a region may exist solely to attach a contact.
        assert count <= 1, (
            f"{profile}: a region declares {count} materials, nextnano++ allows "
            f"at most one:\n{body}"
        )
    assert sum(
        sum(b.count(m) for m in materials) for b in bodies
    ) >= 2, f"{profile}: deck declares too few materials to be a real structure"


def test_render_blocks_expose_one_material_per_region_entry():
    for profile in grading14.PROFILE_FAMILIES:
        blocks = grading14.render_structure_blocks(build(profile, 1.8, 1.0, 1.0))
        assert blocks["regions"], f"{profile} produced no regions"
        for entry in blocks["regions"]:
            assert entry["material"].count("{") >= 1
            declared = sum(
                entry["material"].count(m)
                for m in ("ternary_constant{", "ternary_linear{", "ternary_import{")
            )
            assert declared == 1, entry


def test_degenerate_barrier_drops_the_empty_plateau_region():
    """Ramps wider than the barrier leave no plateau; a zero-width region is
    invalid, so it must not be emitted at all."""

    blocks = grading14.render_structure_blocks(build("linear", 0.85, 1.4, 1.4))
    for entry in blocks["regions"]:
        lo, hi = entry["x"]
        assert hi - lo > 0.0, f"zero or negative width region {entry}"


def test_structure_profile_has_outer_barriers():
    """A well needs something to confine it.

    The first Demo 14 renderer put the central barrier in a GaAs background, so
    outside it there was no barrier material at all: the wells were unbounded
    and any computed state would have belonged to the quantum region's Dirichlet
    walls rather than to a quantum well. --parse cannot catch that; only looking
    at the composition can.
    """

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "demos" / "_shared"))
    import demo14

    cfg = demo14.load_config()
    for profile in grading14.PROFILE_FAMILIES:
        params = {
            "asymmetry_s": 0.42, "nominal_central_barrier_thickness_nm": 1.8,
            "gaas_to_algaas_grading_width_10_90_nm": 1.0,
            "algaas_to_gaas_grading_width_10_90_nm": 1.0,
            "grading_profile": profile,
        }
        geometry = demo14.geometry_for(cfg, params)
        built = demo14.build_grading(cfg, params, geometry)
        y = built.al_fraction
        assert y[0] == pytest.approx(XMAX, abs=1e-3), f"{profile}: no left outer barrier"
        assert y[-1] == pytest.approx(XMAX, abs=1e-3), f"{profile}: no right outer barrier"
        assert built.diagnostics["outer_barrier_present"] is True, profile
        # And the wells must actually be GaAs.
        z1 = built.request["interfaces_nm"]["outer_left_algaas_to_gaas"]
        z2 = built.request["interfaces_nm"]["central_gaas_to_algaas"]
        centre = 0.5 * (z1 + z2)
        well = float(np.interp(centre, built.x_nm, y))
        assert well < 0.02, f"{profile}: thick well is not GaAs (x_Al={well})"


def test_structure_profile_realizes_the_requested_interface_widths():
    """Measured on the central barrier only, between the two well floors."""

    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "demos" / "_shared"))
    import demo14

    cfg = demo14.load_config()
    for profile in ("linear", "cosine"):   # compact support -> exact
        params = {
            "asymmetry_s": 0.42, "nominal_central_barrier_thickness_nm": 1.8,
            "gaas_to_algaas_grading_width_10_90_nm": 0.4,
            "algaas_to_gaas_grading_width_10_90_nm": 1.4,
            "grading_profile": profile,
        }
        geometry = demo14.geometry_for(cfg, params)
        d = demo14.build_grading(cfg, params, geometry).diagnostics
        left = d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"]
        right = d["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"]
        assert left == pytest.approx(0.4, abs=2 * MESH), f"{profile} left {left}"
        assert right == pytest.approx(1.4, abs=2 * MESH), f"{profile} right {right}"
        # A well width must never be mistaken for an interface width.
        assert left < 2.0 and right < 3.0, (profile, left, right)

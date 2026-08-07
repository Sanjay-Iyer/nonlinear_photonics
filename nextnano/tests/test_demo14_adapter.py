"""Demo 14 -> Demo 11 analysis adapter: the integration boundary that broke.

The first licensed Demo 14 startup gate spent a real solver call and then died
in ``demo11.build_stack`` on ``cfg["scientific"]``. The 897-test suite did not
catch it because nothing ever exercised the Demo 14 -> Demo 11 boundary; the
mock path produced metrics directly and never went near Demo 11.

These tests run the real boundary, and one of them statically audits *every*
config key Demo 11's analysis call graph reads, so the next missing field is
found here rather than by a second paid run.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest

import adapter14
import demo11
import demo14

DEMO11_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "demos" / "11_paper_validation_interband_chi2_acqw" / "demo11.py"
)

REPRESENTATIVE_TRIAL = {
    "asymmetry_s": 0.42,
    "nominal_central_barrier_thickness_nm": 1.8,
    "gaas_to_algaas_grading_width_10_90_nm": 1.0,
    "algaas_to_gaas_grading_width_10_90_nm": 1.0,
    "grading_profile": "erf",
}


@pytest.fixture()
def cfg():
    return demo14.load_config()


@pytest.fixture()
def derived(cfg):
    geometry = demo14.geometry_for(cfg, REPRESENTATIVE_TRIAL)
    profile = demo14.build_grading(cfg, REPRESENTATIVE_TRIAL, geometry)
    return adapter14.build_demo11_analysis_config_from_demo14(cfg, geometry, profile)


# --- the exact failure that cost a licensed run ----------------------------


def test_build_stack_accepts_the_adapter_output(derived):
    """The precise call that raised KeyError: 'scientific'."""

    stack = demo11.build_stack(derived)
    intervals = stack.intervals()
    for region in ("left_well", "centre_barrier", "right_well"):
        assert region in intervals


def test_scientific_section_is_present_and_complete(derived):
    """A missing 'scientific' must fail loudly here, never in the analyser."""

    assert "scientific" in derived
    for field in adapter14.REQUIRED_DEMO11_FIELDS["scientific"]:
        assert field in derived["scientific"], field


def test_adapter_refuses_an_incomplete_config():
    broken = {"scientific": {}, "numerical": {}, "outputs": {},
              "validation": {}, "analysis": {}, "metric": {}}
    with pytest.raises(adapter14.Adapter14Error, match="missing field"):
        adapter14.validate_demo11_config(broken)
    with pytest.raises(adapter14.Adapter14Error, match="missing section"):
        adapter14.validate_demo11_config({"scientific": {}})


def test_adapter_refuses_a_demo14_config_missing_a_section(cfg):
    import copy

    broken = copy.deepcopy(cfg)
    del broken["materials"]
    geometry = demo14.geometry_for(cfg, REPRESENTATIVE_TRIAL)
    with pytest.raises(adapter14.Adapter14Error, match="materials"):
        adapter14.build_demo11_analysis_config_from_demo14(broken, geometry)


# --- the field names that read as synonyms but are not ---------------------


def test_field_names_match_demo11_exactly(derived):
    """These are the specific names the broken inline projection got wrong."""

    scientific = derived["scientific"]
    assert "tunnel_barrier_nm" in scientific
    assert "central_barrier_thickness_nm" not in scientific
    # American spelling; the inline version used the British one.
    assert "aluminum_fraction" in scientific
    assert "aluminium_fraction" not in scientific
    # The old projection put everything under 'structure'.
    assert "structure" not in derived


def test_geometry_travels_from_the_trial_not_from_defaults(cfg):
    """A different trial must produce a different analysed structure."""

    a = {**REPRESENTATIVE_TRIAL, "asymmetry_s": 0.35,
         "nominal_central_barrier_thickness_nm": 1.0}
    b = {**REPRESENTATIVE_TRIAL, "asymmetry_s": 0.50,
         "nominal_central_barrier_thickness_nm": 2.4}
    out = []
    for params in (a, b):
        geometry = demo14.geometry_for(cfg, params)
        profile = demo14.build_grading(cfg, params, geometry)
        out.append(adapter14.build_demo11_analysis_config_from_demo14(
            cfg, geometry, profile)["scientific"])
    assert out[0]["thick_well_nm"] != out[1]["thick_well_nm"]
    assert out[0]["tunnel_barrier_nm"] == pytest.approx(1.0)
    assert out[1]["tunnel_barrier_nm"] == pytest.approx(2.4)


def test_the_analysed_stack_is_the_structure_demo14_renders(cfg):
    """If these disagree, region probabilities describe an unsolved structure."""

    for barrier in (0.85, 1.8, 2.5):
        params = {**REPRESENTATIVE_TRIAL,
                  "nominal_central_barrier_thickness_nm": barrier}
        geometry = demo14.geometry_for(cfg, params)
        profile = demo14.build_grading(cfg, params, geometry)
        derived = adapter14.build_demo11_analysis_config_from_demo14(
            cfg, geometry, profile)
        stack = demo11.build_stack(derived)
        rendered = geometry.domain_nm[1] - geometry.domain_nm[0]
        assert float(stack.total_thickness_nm) == pytest.approx(rendered, abs=1e-6)


def test_padding_derivation_is_refused_when_it_cannot_reproduce_the_deck(cfg):
    import copy

    broken = copy.deepcopy(cfg)
    broken["geometry"]["domain_padding_nm"] = 1.0   # < half the 18.2 nm period
    geometry = demo14.geometry_for(broken, REPRESENTATIVE_TRIAL)
    with pytest.raises(adapter14.Adapter14Error, match="period barrier"):
        adapter14.build_demo11_analysis_config_from_demo14(broken, geometry)


# --- the absolute mode reaches Demo 11 -------------------------------------


def test_absolute_constants_reach_demo11_chi2_settings(derived):
    settings = demo11.chi2_settings(derived)
    assert settings.mode == "absolute"
    assert settings.r_e_hh_nm == pytest.approx(0.751)
    assert settings.n_wells_per_metre == pytest.approx(3.3333333e7, rel=1e-6)
    assert settings.spin_degeneracy == 2
    assert settings.broadening_meV == pytest.approx(5.0)


def test_absolute_mode_without_constants_is_refused_before_the_solver():
    broken = {
        "scientific": {k: 1.0 for k in adapter14.REQUIRED_DEMO11_FIELDS["scientific"]},
        "numerical": {k: 1.0 for k in adapter14.REQUIRED_DEMO11_FIELDS["numerical"]},
        "outputs": {k: {} for k in adapter14.REQUIRED_DEMO11_FIELDS["outputs"]},
        "validation": {k: 1.0 for k in adapter14.REQUIRED_DEMO11_FIELDS["validation"]},
        "analysis": {k: 1.0 for k in adapter14.REQUIRED_DEMO11_FIELDS["analysis"]},
        "metric": {"mode": "absolute", "broadening_meV": 5.0,
                   "max_states_per_band": 2, "r_e_hh_nm": None,
                   "n_wells_per_metre": None},
    }
    with pytest.raises(adapter14.Adapter14Error, match="absolute mode requires"):
        adapter14.validate_demo11_config(broken)


# --- the audit that stops "fix key -> paid run -> next key" ----------------


def _config_keys_demo11_reads() -> dict[str, set[str]]:
    """Statically collect ``cfg[...]`` / local-alias accesses from demo11.py.

    Covers both ``cfg["a"]["b"]`` and the ``a = cfg["a"]`` then ``a["b"]``
    pattern that ``build_stack`` uses -- the latter is exactly what a naive
    regex misses, and ``exterior_grid_spacing_nm`` is read that way.
    """

    source = DEMO11_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sections: dict[str, set[str]] = {}

    def record(section: str, field: str | None) -> None:
        sections.setdefault(section, set())
        if field:
            sections[section].add(field)

    for node in ast.walk(tree):
        # cfg["section"]["field"]
        if (isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Subscript)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "cfg"
                and isinstance(node.value.slice, ast.Constant)
                and isinstance(node.slice, ast.Constant)):
            record(str(node.value.slice.value), str(node.slice.value))

    # alias = cfg["section"]  ->  alias["field"]
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Subscript)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "cfg"
                and isinstance(node.value.slice, ast.Constant)):
            aliases[node.targets[0].id] = str(node.value.slice.value)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in aliases
                and isinstance(node.slice, ast.Constant)):
            record(aliases[node.value.id], str(node.slice.value))
    return sections


def test_adapter_supplies_every_required_key_demo11_reads(derived):
    """Structural audit, so the next missing field is found without a paid run.

    Only mandatory ``[...]`` subscripts count. Demo 11 uses ``.get(name,
    default)`` wherever a value is genuinely optional, and those cannot raise.
    """

    reads = _config_keys_demo11_reads()
    missing: list[str] = []
    for section, fields in sorted(reads.items()):
        if section not in derived:
            # Sections only touched by Demo 11's own sweep drivers, never by the
            # analysis path Demo 14 calls.
            continue
        for field in sorted(fields):
            if field not in (derived.get(section) or {}):
                missing.append(f"{section}.{field}")
    assert not missing, (
        "the adapter does not supply config key(s) Demo 11 reads with a "
        f"mandatory subscript: {missing}"
    )


def test_the_audit_itself_detects_the_sections_that_mattered():
    """Guard the guard: the audit must actually see 'scientific'."""

    reads = _config_keys_demo11_reads()
    assert "scientific" in reads
    assert "thick_well_nm" in reads["scientific"]
    assert "tunnel_barrier_nm" in reads["scientific"]
    assert "aluminum_fraction" in reads["scientific"]
    # The alias pattern build_stack uses must be picked up too.
    assert "exterior_grid_spacing_nm" in reads.get("numerical", set())


# --- path duplication ------------------------------------------------------


def test_results_root_has_no_duplicated_demo_runs_component():
    """The first gate wrote to results/demo_runs/demo_runs/14_...

    machine.results_root already ends in demo_runs, so appending another one
    produced a second, wrong tree. A duplicated component anywhere in the
    resolved path is the symptom to catch.
    """

    import run_demo14

    root, _ = run_demo14._results_root()
    parts = [p for p in Path(root).parts]
    duplicates = [
        a for a, b in zip(parts, parts[1:]) if a == b
    ]
    assert not duplicates, f"duplicated path component(s) {duplicates} in {root}"
    assert parts[-1] == "demo_runs", f"results root should end in demo_runs: {root}"
    assert parts.count("demo_runs") == 1, f"demo_runs appears twice in {root}"


def test_gate_directory_sits_under_the_demo_id():
    import gate14
    import run_demo14

    root, _ = run_demo14._results_root()
    directory = Path(root) / demo14.DEMO_DIR.name / gate14.GATE_DIR_NAME
    parts = list(directory.parts)
    assert not [a for a, b in zip(parts, parts[1:]) if a == b], directory
    assert parts[-1] == gate14.GATE_DIR_NAME
    assert parts[-2] == "14_absolute_chi2_graded_acqw_bo"

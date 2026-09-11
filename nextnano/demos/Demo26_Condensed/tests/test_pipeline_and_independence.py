"""End-to-end Script 2 on cached Professional output, validation semantics, and the self-containment audit."""
import ast
import csv
import json
import sys
from pathlib import Path

import pytest

from src import analysis, validation

PKG = Path(__file__).resolve().parents[1]
RUNTIME = [PKG / "01_run_nextnano.py", PKG / "02_calculate_chi2.py", *sorted((PKG / "src").glob("*.py"))]
MODE_DIRS = {"kp8": "kp8", "demo26-baseline": "demo26_baseline", "demo26-cutoff": "demo26_cutoff"}


@pytest.fixture(scope="module")
def run(root, tmp_path_factory):
    out = tmp_path_factory.mktemp("analysis")
    code = analysis.main(["--input", str(root / "cached_raw"), "--output", str(out), "--check-reference"])
    return code, out


@pytest.fixture(scope="module")
def summaries(run):
    return {mode: json.loads((run[1] / d / "summary.json").read_text()) for mode, d in MODE_DIRS.items()}


def test_script2_passes_every_applicable_check(run, root):
    code, out = run
    report = json.loads((out / "validation.json").read_text())
    reference = json.loads((root / "validation/reference_demo26.json").read_text())
    expected = sum(len(v) for v in reference["modes"].values())
    assert code == 0
    assert report["totals"] == {"PASS": expected, "FAIL": 0, "NOT APPLICABLE": 0, "NOT RUN": 0}
    assert set(report["by_category"]) == {"reference", "independent_rederivation", "consistency"}
    assert all(report["dataset_conditions"].values())


def test_different_dataset_makes_dataset_checks_not_applicable(summaries, root):
    conditions = {"kp8_deck_matches_reference": False, "case04_deck_matches_reference": True, "config_matches_reference": True}
    report = validation.validate(summaries, root / "validation/reference_demo26.json", conditions)
    for r in report["checks"]:
        expected = "PASS" if r["category"] == "consistency" else "NOT APPLICABLE"
        assert r["status"] == expected, (r["mode"], r["id"], r["status"])


@pytest.mark.parametrize("mode", list(MODE_DIRS.values()))
def test_required_outputs_and_csv_columns(run, mode):
    out = run[1] / mode
    for name in ("01_chi2_real.png", "02_chi2_imag.png", "03_chi2_abs_real.png", "04_chi2_magnitude.png",
                 "05_paper_vs_absreal_vs_magnitude.png", "06_real_and_imag.png", "07_k_cutoff_dependence.png",
                 "chi2_spectrum.csv", "pathways.csv", "summary.json", "SUMMARY.md", "derived_inputs.json"):
        assert (out / name).is_file(), name
    header = next(csv.reader((out / "chi2_spectrum.csv").open()))
    for col in ("wavelength_nm", "photon_energy_eV", "chi2_real_pm_per_V", "chi2_imag_pm_per_V",
                "chi2_abs_real_pm_per_V", "chi2_abs_pm_per_V"):
        assert col in header


def test_finding_separates_mechanism_from_shape_comparison(summaries):
    for s in summaries.values():
        mech, shape = s["finding"]["mechanism"], s["finding"]["shape_comparison"]
        assert mech["re_zero_count"] == len(mech["at_re_zeros"])
        for z in mech["at_re_zeros"]:  # at a refined Re zero, |chi| is exactly |Im|
            assert z["abs_over_max_abs"] == pytest.approx(z["abs_imag_over_max_abs"], rel=1e-9)
        m = s["paper_metrics"]
        assert shape["comparison_informative"] == (m["abs_real"]["informative"] or m["abs"]["informative"])
        for name in ("abs_real", "abs"):
            assert m[name]["informative"] == (m[name]["nRMSE"] < m["null_best_constant"]["nRMSE"] and m[name]["correlation"] >= 0.5)


def test_kp8_production_is_branch_resolved_with_sensitivity(summaries):
    s = summaries["kp8"]
    assert s["pathway_count"] == 16 and s["modulus_identity_max_error"] < 1e-9
    assert s["energy_treatment"].startswith("branch-resolved")
    assert set(s["sensitivity"]) == {"doublet_averaged_energies", "overlap_weighted_by_conduction_block_amplitude"}
    assert s["origin_invariance_max_abs_change"] < 1e-8 < 1e-3 < s["origin_sensitivity_without_lowdin_max_abs_change"]


def test_runtime_imports_are_self_contained():
    allowed = {"numpy", "scipy", "matplotlib", "src", *sys.stdlib_module_names}
    for path in RUNTIME:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert name.split(".")[0] in allowed, f"{path.name} imports {name}"


def test_runtime_code_has_no_repository_or_personal_paths():
    forbidden = ["demo_results", "demos/2", "26_real_chi2", "23_k_resolved", "27_physics",
                 r"c:\code", "c:/code", "nn_results", "mccoysa", "iyer95"]
    for path in RUNTIME:
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token!r}"

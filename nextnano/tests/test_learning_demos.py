"""Solver-free tests for the YAML-driven nextnano++ learning demos."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

import demo_workflow as workflow

DEMO_ROOT = Path(__file__).resolve().parents[1] / "demos"
DEMO1 = DEMO_ROOT / "01_classical_single_quantum_well"
DEMO2 = DEMO_ROOT / "02_one_band_finite_quantum_well"
DEMO3 = DEMO_ROOT / "03_quantum_well_convergence"


def _machine_yaml(path: Path, **overrides) -> Path:
    data = {
        "portable_root": None,
        "executable": None,
        "database": None,
        "license": None,
        "threads": 2,
        "run_solver": False,
        "results_root": str(path.parent / "results"),
    }
    data.update(overrides)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_repository_root_discovery_is_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert workflow.repository_root(DEMO1 / "run.py") == workflow.REPOSITORY_ROOT


def test_sibling_portable_root_resolution(tmp_path):
    repo = tmp_path / "nonlinear_photonics"
    repo.mkdir()
    sibling = tmp_path / "2026_07_03"
    sibling.mkdir()
    assert workflow.sibling_portable_root(repo) == sibling.resolve()


def test_explicit_machine_paths_override_discovery(tmp_path):
    portable = tmp_path / "portable"
    portable.mkdir()
    exe = tmp_path / "custom_solver.exe"
    database = tmp_path / "custom_database.xml"
    license_file = tmp_path / "private.lic"
    for path in (exe, database, license_file):
        path.write_text("fixture", encoding="utf-8")
    config = _machine_yaml(
        tmp_path / "machine.yaml",
        portable_root=str(portable),
        executable=str(exe),
        database=str(database),
        license=str(license_file),
        run_solver=True,
    )
    machine = workflow.load_machine_config(config)
    assert machine.executable == exe.resolve()
    assert machine.database == database.resolve()
    assert machine.license == license_file.resolve()


def test_missing_portable_is_actionable_when_execution_enabled(tmp_path):
    config = _machine_yaml(
        tmp_path / "machine.yaml",
        portable_root=str(tmp_path / "missing"),
        run_solver=True,
    )
    with pytest.raises(workflow.DemoError, match="portable_root is missing"):
        workflow.load_machine_config(config)


def test_auto_mode_executes_when_portable_installation_is_complete(tmp_path):
    portable = tmp_path / "2026_07_03"
    portable.mkdir()
    exe = portable / "nextnano++.exe"
    database = portable / "database_nnp.xml"
    license_file = portable / "License_nnp.lic"
    for path in (exe, database, license_file):
        path.write_text("fixture", encoding="utf-8")
    config = _machine_yaml(
        tmp_path / "machine.yaml",
        portable_root=str(portable),
        run_solver="auto",
    )
    machine = workflow.load_machine_config(config)
    assert machine.run_solver is True
    assert machine.executable == exe.resolve()
    assert machine.database == database.resolve()
    assert machine.license == license_file.resolve()


def test_existing_legacy_machine_config_is_reused_automatically(
    tmp_path, monkeypatch
):
    exe = tmp_path / "configured_solver.exe"
    database = tmp_path / "configured_database.xml"
    license_file = tmp_path / "configured_license.lic"
    for path in (exe, database, license_file):
        path.write_text("fixture", encoding="utf-8")
    legacy = tmp_path / "paths.local.yaml"
    legacy.write_text(
        yaml.safe_dump(
            {
                "nextnano++": {
                    "exe": str(exe),
                    "database": str(database),
                    "license": str(license_file),
                    "outputdirectory": str(tmp_path / "old_output"),
                    "threads": 7,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(workflow, "LEGACY_MACHINE_CONFIG", legacy)
    monkeypatch.setattr(workflow, "MACHINE_CONFIG", tmp_path / "missing_local.yaml")
    machine = workflow.load_machine_config()
    assert machine.run_solver is True
    assert machine.executable == exe.resolve()
    assert machine.database == database.resolve()
    assert machine.license == license_file.resolve()
    assert machine.threads == 7
    assert machine.source_path == legacy


def test_machine_yaml_rejects_unknown_keys(tmp_path):
    config = _machine_yaml(tmp_path / "machine.yaml")
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["mystery"] = 1
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(workflow.DemoError, match="unsupported key"):
        workflow.load_machine_config(config)


def test_all_demo_yamls_are_strictly_valid():
    assert workflow.load_demo_config(DEMO1)["demo_id"].startswith("01")
    assert workflow.load_demo_config(DEMO2)["demo_id"].startswith("02")
    cfg3 = workflow.load_demo_config(DEMO3)
    assert set(cfg3["sweeps"]) == workflow.SWEEP_KEYS


def test_demo_yaml_rejects_unknown_nested_key(tmp_path):
    demo = tmp_path / "01_bad_demo"
    demo.mkdir()
    data = workflow.load_demo_config(DEMO1)
    data["scientific"]["unsupported_physics"] = True
    (demo / "demo.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(workflow.DemoError, match="unsupported key"):
        workflow.load_demo_config(demo)


def test_demo_yaml_rejects_nonfinite_numeric_value(tmp_path):
    demo = tmp_path / "01_bad_numeric"
    demo.mkdir()
    data = workflow.load_demo_config(DEMO1)
    data["scientific"]["well_width_nm"] = ".nan"
    (demo / "demo.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(workflow.DemoError, match="finite"):
        workflow.load_demo_config(demo)


def test_template_substitution_is_complete_and_reproducible():
    cfg = workflow.load_demo_config(DEMO2)
    template = (DEMO2 / cfg["template"]).read_text(encoding="utf-8")
    values = workflow._parameters(cfg)
    first = workflow.render_template(template, values)
    second = workflow.render_template(template, values)
    assert first == second
    assert "{{" not in first and "}}" not in first
    assert hashlib_sha(first) == hashlib_sha(second)


def test_demo1_has_required_neutral_contact_without_forbidden_physics():
    cfg = workflow.load_demo_config(DEMO1)
    rendered = workflow.render_template(
        (DEMO1 / cfg["template"]).read_text(encoding="utf-8"),
        workflow._parameters(cfg),
    )
    assert "contacts{" in rendered
    assert "fermi{ name = qw_contact  bias = 0.0 }" in rendered
    assert "contact{ name = qw_contact }" in rendered
    assert "poisson{" not in rendered
    assert "quantum{" not in rendered


@pytest.mark.parametrize("demo_dir", [DEMO1, DEMO2, DEMO3])
def test_rendered_inputs_load_as_nextnanopp(tmp_path, demo_dir):
    nn = pytest.importorskip("nextnanopy")
    cfg = workflow.load_demo_config(demo_dir)
    rendered = workflow.render_template(
        (demo_dir / cfg["template"]).read_text(encoding="utf-8"),
        workflow._parameters(cfg),
    )
    deck = tmp_path / f"{cfg['demo_id']}.in"
    deck.write_text(rendered, encoding="utf-8")
    assert nn.InputFile(str(deck)).product == "nextnano++"


def hashlib_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_undefined_template_variable_fails():
    with pytest.raises(workflow.DemoError, match="undefined"):
        workflow.render_template("temperature={{missing}}", {})


def test_run_ids_are_unique_and_sortable():
    first = workflow.make_run_id()
    second = workflow.make_run_id()
    assert first != second
    assert first[:8].isdigit() and second[:8].isdigit()


def test_machine_summary_redacts_license_path_and_contents(tmp_path):
    license_file = tmp_path / "secret" / "licensed_asset.lic"
    license_file.parent.mkdir()
    license_file.write_text("TOP SECRET LICENSE CONTENT", encoding="utf-8")
    executable = tmp_path / "solver.exe"
    database = tmp_path / "database.xml"
    executable.write_text("x", encoding="utf-8")
    database.write_text("x", encoding="utf-8")
    config = _machine_yaml(
        tmp_path / "machine.yaml",
        executable=str(executable),
        database=str(database),
        license=str(license_file),
        run_solver=True,
    )
    encoded = json.dumps(
        workflow.machine_summary(workflow.load_machine_config(config))
    )
    assert "licensed_asset.lic" in encoded
    assert str(license_file.parent) not in encoded
    assert "TOP SECRET" not in encoded


def test_solver_log_sanitizer_redacts_identity_and_key(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    log = raw / "solver.log"
    log.write_text(
        "Licensed to: Example Person, example@example.invalid\n"
        "License key: private-key-value\n"
        "DONE.\n",
        encoding="utf-8",
    )
    assert workflow._sanitize_solver_logs(raw) == 1
    sanitized = log.read_text(encoding="utf-8")
    assert "Example Person" not in sanitized
    assert "example@example.invalid" not in sanitized
    assert "private-key-value" not in sanitized
    assert sanitized.count("<redacted>") == 2
    assert "DONE." in sanitized


def test_numeric_output_parser_fixture(tmp_path):
    path = tmp_path / "bandedges.dat"
    path.write_text(
        "x[nm] Gamma[eV] HH[eV] LH[eV] SO[eV] electron_Fermi_level[eV] "
        "hole_Fermi_level[eV]\n"
        "0 1.65 0.0 -0.01 -0.34 0 0\n"
        "1 1.42 0.0 -0.02 -0.35 0 0\n",
        encoding="utf-8",
    )
    parsed = workflow.parse_numeric_table(
        path, {"position_nm": 0, "conduction_eV": 1, "split_off_eV": 4}
    )
    assert parsed["position_nm"].tolist() == [0.0, 1.0]
    assert parsed["conduction_eV"].tolist() == [1.65, 1.42]
    assert np.isfinite(parsed["split_off_eV"]).all()


def test_quantum_output_parser_and_plots_with_small_fixture(tmp_path):
    raw = tmp_path / "raw"
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    raw.mkdir()
    extracted.mkdir()
    plots.mkdir()
    x = np.linspace(0.0, 50.0, 201)
    inside = (x >= 20.0) & (x <= 30.0)
    ec = np.where(inside, 1.42, 1.65)
    bandedges = np.column_stack(
        [x, ec, np.full_like(x, 1.8), np.full_like(x, 1.9),
         np.zeros_like(x), np.full_like(x, -0.01), np.full_like(x, -0.34)]
    )
    np.savetxt(raw / "bandedges.dat", bandedges)
    np.savetxt(
        raw / "energy_spectrum_k00000.dat",
        np.asarray([[1, 1.46], [2, 1.55]]),
    )
    densities = []
    for center in (25.0, 23.5):
        density = np.exp(-((x - center) / 2.0) ** 2)
        density /= np.trapezoid(density, x)
        densities.append(density)
    np.savetxt(
        raw / "probabilities_k00000.dat",
        np.column_stack([x, *densities]),
    )
    cfg = workflow.load_demo_config(DEMO2)
    observables, validation = workflow._analyse_quantum(
        cfg, raw, extracted, plots
    )
    assert observables["E1_eV"] == pytest.approx(1.46)
    assert observables["well_probability"] > 0.9
    assert validation["passed"] is True
    assert (extracted / "composition_profile.csv").is_file()
    assert (plots / "band_edge_with_probability_offsets.png").is_file()


def test_convergence_selects_coarsest_passing_grid():
    rows = [
        {
            "value": 1.0,
            "solver_success": True,
            "E1_eV": 1.451,
            "boundary_probability": 1e-7,
            "well_probability": 0.8,
        },
        {
            "value": 0.5,
            "solver_success": True,
            "E1_eV": 1.45005,
            "boundary_probability": 1e-7,
            "well_probability": 0.8,
        },
        {
            "value": 0.25,
            "solver_success": True,
            "E1_eV": 1.45001,
            "boundary_probability": 1e-7,
            "well_probability": 0.8,
        },
        {
            "value": 0.125,
            "solver_success": True,
            "E1_eV": 1.45,
            "boundary_probability": 1e-7,
            "well_probability": 0.8,
        },
    ]
    chosen = workflow.select_coarsest_converged(
        rows,
        reference_e1_eV=1.45,
        absolute_tolerance_meV=0.1,
        relative_tolerance=1e-4,
        maximum_boundary_probability=1e-4,
        minimum_well_probability=0.5,
    )
    assert chosen is not None
    assert chosen["value"] == 0.5


def test_failed_solver_run_is_preserved(tmp_path, monkeypatch):
    cfg = workflow.load_demo_config(DEMO2)
    fake = tmp_path / "asset"
    fake.write_text("x", encoding="utf-8")
    machine = workflow.MachineConfig(
        portable_root=tmp_path,
        executable=fake,
        database=fake,
        license=fake,
        threads=1,
        run_solver=True,
        results_root=tmp_path,
        source_path=tmp_path / "machine.yaml",
        discovery_notes=(),
    )

    def fail(*_args, **_kwargs):
        raise RuntimeError("simulated solver failure")

    monkeypatch.setattr(workflow, "_execute_solver", fail)
    run_dir = tmp_path / "failed_run"
    outcome = workflow.run_case(DEMO2, cfg, machine, run_dir)
    assert outcome.solver_status == "failed"
    assert (run_dir / "generated_input").is_dir()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["completion_status"] == "failed"
    assert "simulated solver failure" in manifest["failure_reason"]


@pytest.mark.parametrize("demo_dir", [DEMO1, DEMO2])
def test_home_dry_run_creates_complete_provenance(tmp_path, demo_dir):
    cfg = workflow.load_demo_config(demo_dir)
    machine_path = _machine_yaml(tmp_path / "machine.yaml")
    machine = workflow.load_machine_config(machine_path)
    run_dir = tmp_path / cfg["demo_id"] / workflow.make_run_id()
    outcome = workflow.run_case(demo_dir, cfg, machine, run_dir)
    assert outcome.solver_status == "skipped_no_solver"
    for name in (
        "console.log",
        "demo_resolved.yaml",
        "machine_summary.json",
        "run_manifest.json",
    ):
        assert (run_dir / name).is_file()
    generated = next((run_dir / "generated_input").glob("*.in"))
    assert "{{" not in generated.read_text(encoding="utf-8")
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["generated_input_sha256"] == workflow._sha256(generated)


def test_demo3_home_run_preserves_all_sweep_points(tmp_path):
    machine_path = _machine_yaml(tmp_path / "machine.yaml")
    assert workflow.run_demo(DEMO3, machine_path) == 0
    parent = next((tmp_path / "results" / "03_quantum_well_convergence").iterdir())
    generated = list((parent / "cases").glob("**/generated_input/case.in"))
    assert len(generated) == 16
    summary = json.loads(
        (parent / "extracted" / "convergence_summary.json").read_text(encoding="utf-8")
    )
    assert len(summary) == 16
    assert all(row["status"] == "skipped_no_solver" for row in summary)
    assert (parent / "extracted" / "convergence_table.md").is_file()
    assert len(list((parent / "plots").glob("*.png"))) == 5

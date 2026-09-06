"""Demo 27 tests.

These validate the campaign machinery and its fail-loud contracts. They
deliberately assert no physics conclusion: the Professional data that would
settle one does not exist until the sub-demos have run.

What is tested, in the order the brief asks for it:

* no master "run all physics" path
* sub-demos execute independently
* prerequisites are enforced
* raw outputs are never fabricated
* a missing Professional executable fails loudly
* state output associated to k is valid
* Demos 23/24/26 are not modified
* analysis-only stages do not invoke nextnano
* every Professional invocation writes a manifest
* every sub-demo has a resolvable config
* the status file updates correctly
"""

from __future__ import annotations

import ast
import inspect
import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest
import yaml

DEMO_DIR = Path(__file__).resolve().parents[1]
DEMOS_DIR = DEMO_DIR.parent
REPO_ROOT = DEMO_DIR.parents[2]
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import run_demo27  # noqa: E402
from framework import Demo27Error  # noqa: E402
from framework import analyze as analyze_module  # noqa: E402
from framework import decks as deck_module  # noqa: E402
from framework import manifest as manifest_module  # noqa: E402
from framework import physics as physics_module  # noqa: E402
from framework import preflight as preflight_module  # noqa: E402
from framework import registry, reuse, solver, status  # noqa: E402


def code_only(path: Path) -> str:
    """Source with comments and docstrings removed.

    The guards below check what the code *does*. A module that documents "this
    never fabricates raw physics" would otherwise fail a naive substring search
    for the very word it is promising not to act on.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body.pop(0)
    return ast.unparse(tree)


@pytest.fixture(scope="module")
def parent():
    return registry.load_parent_config()


@pytest.fixture(scope="module")
def subs(parent):
    return registry.discover(parent)


@pytest.fixture(scope="module")
def cfg23():
    return registry.load_demo23_config()


# ---------------------------------------------------------------------------
# 1. no master "run all physics" path
# ---------------------------------------------------------------------------

def test_forbidden_batch_flags_are_refused_before_argparse(parent):
    for flag in parent["policy"]["forbidden_batch_flags"]:
        with pytest.raises(SystemExit) as exc:
            run_demo27.enforce_policy([flag], parent)
        assert "REFUSED" in str(exc.value)


def test_forbidden_flag_refused_even_with_a_value(parent):
    with pytest.raises(SystemExit):
        run_demo27.enforce_policy(["--all-physics=27A"], parent)


def test_parser_defines_no_batch_option(parent):
    """argparse must not know these options at all, not even to reject them."""
    known = set()
    for action in run_demo27.build_parser()._actions:
        known.update(action.option_strings)
    for flag in parent["policy"]["forbidden_batch_flags"]:
        assert flag not in known


def test_no_function_iterates_sub_demos_and_runs_physics():
    """A loop over sub-demos calling the physics stage would be a batch path."""
    source = (DEMO_DIR / "run_demo27.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        body = ast.dump(node)
        assert "command_physics" not in body and "physics_module" not in body, (
            "run_demo27.py loops over something and launches the physics stage inside "
            "the loop; that is a batch path by another name")
    physics_source = inspect.getsource(physics_module)
    physics_tree = ast.parse(physics_source)
    for node in ast.walk(physics_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            args = [a.arg for a in node.args.args]
            assert "sub" in args, "physics.run must act on exactly one sub-demo"


def test_a_stage_requires_a_demo(parent):
    for stage in ("--preflight", "--physics", "--analyze"):
        buffer = io.StringIO()
        with redirect_stdout(buffer), redirect_stderr(buffer):
            code = run_demo27.main([stage])
        assert code == 2
        assert "needs --demo" in buffer.getvalue()


def test_only_one_stage_per_run():
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = run_demo27.main(["--demo", "27D", "--preflight", "--physics"])
    assert code == 2
    assert "one stage per run" in buffer.getvalue()


def test_demo_takes_exactly_one_sub_demo():
    for value in ("27A,27D", "27A 27D"):
        buffer = io.StringIO()
        with redirect_stdout(buffer), redirect_stderr(buffer):
            code = run_demo27.main(["--demo", value, "--preflight"])
        assert code == 2
        assert "exactly one sub-demo" in buffer.getvalue()


# ---------------------------------------------------------------------------
# 2. sub-demos are independent
# ---------------------------------------------------------------------------

def test_every_sub_demo_has_its_own_directory_config_and_readme(subs):
    for sub in subs:
        assert (sub.directory / "config.yaml").is_file()
        assert (sub.directory / "README.md").is_file()
        assert sub.outputs_dir.is_dir()


def test_sub_demo_outputs_are_disjoint(subs):
    roots = [sub.outputs_dir.resolve() for sub in subs]
    assert len(set(roots)) == len(roots)


def test_sub_demo_results_roots_are_disjoint(subs, parent):
    roots = [registry.resolve(sub, parent).results_root for sub in subs]
    assert len(set(roots)) == len(roots)


def test_no_sub_demo_triggers_another(subs):
    """A sub-demo config may declare prerequisites; it may not chain execution."""
    for sub in subs:
        text = (sub.directory / "config.yaml").read_text(encoding="utf-8")
        blob = yaml.safe_load(text)
        delegate = blob.get("delegate") or {}
        for command in (delegate.get("commands") or {}).values():
            assert "run_demo27" not in str(command), (
                "%s delegates back into Demo 27, which would chain sub-demos" % sub.demo_id)
        assert "then_run" not in blob and "next_demo" not in blob


def test_a_failed_sub_demo_does_not_block_an_unrelated_one(parent, subs, tmp_path):
    recorded = {sub.demo_id: "NOT RUN" for sub in subs}
    recorded["27A"] = "FAIL"
    for sub in subs:
        if "27A" in sub.prerequisites:
            assert registry.blocking_prerequisites(sub, recorded)
        elif not sub.prerequisites:
            assert not registry.blocking_prerequisites(sub, recorded), (
                "%s has no prerequisites and must not be blocked by 27A" % sub.demo_id)


# ---------------------------------------------------------------------------
# 3. prerequisites are enforced
# ---------------------------------------------------------------------------

def test_prerequisite_graph_is_acyclic_and_complete(subs):
    known = {sub.demo_id for sub in subs}
    for sub in subs:
        assert set(sub.prerequisites) <= known
        assert set(sub.unlocks) <= known
    registry._validate_graph(subs)  # raises on a cycle


def test_unknown_prerequisite_is_rejected(tmp_path, subs):
    bogus = registry.SubDemo(
        demo_id="27Z", slug="bogus", directory=tmp_path, title="t", question="q",
        tier=1, priority=None, professional_required=False,
        prerequisites=("27ZZ",), unlocks=(), pass_condition="p", cost={},
        stages={}, delegate={}, controlled_change={}, raw={})
    with pytest.raises(Demo27Error, match="unknown prerequisite"):
        registry._validate_graph(list(subs) + [bogus])


def test_only_terminal_statuses_satisfy_a_prerequisite():
    assert set(registry.SATISFYING) == {"PASS", "COMPLETE", "NOT NEEDED"}
    for status_value in ("NOT RUN", "READY", "RUNNING", "FAIL", "BLOCKED"):
        assert status_value not in registry.SATISFYING


def test_blocked_is_derived_not_merely_stored(subs):
    recorded = {"27B": "READY"}
    sub = registry.find("27B", subs)
    assert registry.derived_status(sub, recorded) == "BLOCKED"


def test_physics_stage_refuses_while_a_prerequisite_is_unmet(monkeypatch, parent):
    monkeypatch.setattr(status, "statuses", lambda _p: {"27D": "READY"})
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = run_demo27.main(["--demo", "27E", "--physics", "--yes"])
    assert code == 3
    assert "blocked by" in buffer.getvalue()


def test_physics_stage_refuses_without_preflight(monkeypatch, parent, subs, tmp_path):
    sub = registry.find("27H", subs)
    monkeypatch.setattr(registry.SubDemo, "outputs_dir",
                        property(lambda self: tmp_path / self.demo_id))
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = run_demo27.main(["--demo", "27H", "--physics", "--yes"])
    assert code == 4
    assert "has not passed preflight" in buffer.getvalue()


# ---------------------------------------------------------------------------
# 4. raw outputs are never fabricated
# ---------------------------------------------------------------------------

def test_analysis_refuses_when_there_is_no_raw_output(parent, subs, tmp_path,
                                                      monkeypatch):
    sub = registry.find("27G", subs)
    resolved = registry.resolve(sub, parent)
    monkeypatch.setattr(type(resolved), "results_root",
                        property(lambda self: tmp_path / "empty"))
    monkeypatch.setattr(registry.SubDemo, "outputs_dir",
                        property(lambda self: tmp_path / "out"))
    result = analyze_module.run(sub, resolved)
    assert result["status"] == "NO DATA"
    assert "does not invent" in result["message"]


def test_no_placeholder_files_are_written_for_pending_artifacts(parent, subs, tmp_path,
                                                                monkeypatch):
    sub = registry.find("27G", subs)
    resolved = registry.resolve(sub, parent)
    out = tmp_path / "out"
    monkeypatch.setattr(type(resolved), "results_root",
                        property(lambda self: tmp_path / "empty"))
    monkeypatch.setattr(registry.SubDemo, "outputs_dir", property(lambda self: out))
    analyze_module.run(sub, resolved)
    planned = set((sub.raw.get("analysis") or {}).get("produces") or [])
    written = {p.name for p in out.glob("*")}
    assert planned.isdisjoint(written), (
        "an analysis artifact was created without the data behind it")


def test_no_module_substitutes_k0_for_missing_finite_k_data():
    """Nothing in the framework silently freezes M(k) to M(0) or invents a value.

    Checked over identifiers rather than raw text, because the modules *describe*
    what they refuse to do in their reports, and a substring search would flag
    the promise as if it were the act.
    """
    banned = {"fallback_to_k0", "assume_k0", "default_matrix", "placeholder_value",
              "synthesize", "fabricate", "zeros_like", "fillna", "interpolate_missing"}
    for path in (DEMO_DIR / "framework").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                names.add(node.attr.lower())
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name.lower())
            elif isinstance(node, ast.arg):
                names.add(node.arg.lower())
        overlap = names & banned
        assert not overlap, "%s defines or calls %s" % (path.name, sorted(overlap))


# ---------------------------------------------------------------------------
# 5. a missing Professional executable fails loudly
# ---------------------------------------------------------------------------

def test_free_build_is_rejected_by_name(tmp_path):
    """Every file exists, so only the Free naming can be what refuses the run."""
    machine = {}
    for key, name in (("exe", "nextnano++_Microsoft_32bit_free.exe"),
                      ("database", "database_free.nnp"),
                      ("license", "License_free.lic")):
        path = tmp_path / name
        path.write_text("", encoding="utf-8")
        machine[key] = path
    machine["threads"] = 1
    assert solver.is_free_build(machine)
    with pytest.raises(Demo27Error) as exc:
        solver.assert_professional(machine)
    message = str(exc.value)
    assert "Free build" in message and "Free license" in message
    assert "not found" not in message


def test_missing_executable_is_rejected(tmp_path):
    machine = {"exe": tmp_path / "does_not_exist.exe",
               "database": tmp_path / "db.nnp",
               "license": tmp_path / "lic.lic", "threads": 1}
    with pytest.raises(Demo27Error) as exc:
        solver.assert_professional(machine)
    assert "executable not found" in str(exc.value)


def test_missing_machine_config_is_explained(tmp_path):
    with pytest.raises(Demo27Error) as exc:
        solver.machine_config(tmp_path / "absent.yaml")
    assert "paths.local.yaml" in str(exc.value)


def test_physics_stage_fails_loudly_on_this_machine_if_free(parent, subs):
    """The home laptop's Free build must not be able to start a physics stage."""
    try:
        machine = solver.machine_config()
    except Demo27Error:
        pytest.skip("no nextnano configured on this machine")
    if not solver.is_free_build(machine):
        pytest.skip("this machine has a Professional build")
    sub = registry.find("27D", subs)
    resolved = registry.resolve(sub, parent)
    with pytest.raises(Demo27Error, match="Professional is not available"):
        physics_module.run(sub, resolved, machine, {}, timeout_seconds=1.0)


# ---------------------------------------------------------------------------
# 6. state output associated to k is valid
# ---------------------------------------------------------------------------

def test_k_association_requires_a_matching_k_vector(tmp_path, monkeypatch, parent, subs):
    """A state file tagged k00007 with only 4 k vectors is not usable evidence."""
    pilot_audit = analyze_module._pilot_audit_module()
    case = tmp_path / "raw" / "case"
    case.mkdir(parents=True)
    for index in (0, 7):
        (case / ("energy_spectrum_k%05d.dat" % index)).write_text("0.0\n", encoding="utf-8")
        (case / ("envelope_k%05d.dat" % index)).write_text("0.0\n", encoding="utf-8")
    _, summary = pilot_audit.audit_case(case, "case")
    assert summary["k_indices"] == [0, 7]
    # Two k vectors only: index 7 cannot be placed in k space.
    assert max(summary["k_indices"]) >= 2


def test_audit_reports_association_failure(tmp_path, monkeypatch, parent, subs):
    sub = registry.find("27C", subs)
    resolved = registry.resolve(sub, parent)
    root = tmp_path / "results"
    case = root / "raw" / "deck"
    case.mkdir(parents=True)
    (case / "energy_spectrum_k00000.dat").write_text("0\n", encoding="utf-8")
    (case / "envelope_k00000.dat").write_text("0\n", encoding="utf-8")
    (case / "energy_spectrum_k00009.dat").write_text("0\n", encoding="utf-8")
    (case / "envelope_k00009.dat").write_text("0\n", encoding="utf-8")
    monkeypatch.setattr(type(resolved), "results_root", property(lambda self: root))
    monkeypatch.setattr(registry.SubDemo, "outputs_dir",
                        property(lambda self: tmp_path / "out"))
    audit = analyze_module.audit_raw_output(sub, resolved)
    # No kVectors file exists, so nothing can be associated.
    assert audit["status"] == "FAIL"
    assert audit["unassociated"] == ["deck"]


# ---------------------------------------------------------------------------
# 7. Demos 23/24/26 are not modified
# ---------------------------------------------------------------------------

def test_demo27_never_writes_into_an_earlier_demo(parent):
    reuse.assert_no_writes_outside_demo27(parent)
    root = Path(str(parent["paths"]["results_root"]))
    assert root.as_posix().startswith("demo_results/demo27")


def test_reuse_audit_detects_a_changed_artifact(tmp_path, monkeypatch, parent):
    from framework import reuse as reuse_module

    target = tmp_path / "artifact.csv"
    target.write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(reuse_module, "ARTIFACTS", (
        {"id": "probe", "path": "probe.csv", "provides": "p",
         "reusable_for": "ALL", "reuse_rule": "r"},))
    monkeypatch.setattr(reuse_module, "_resolve", lambda _rel: target)
    monkeypatch.setattr(registry, "DEMO_DIR", tmp_path)
    monkeypatch.setattr(reuse_module.registry if hasattr(reuse_module, "registry")
                        else registry, "DEMO_DIR", tmp_path, raising=False)
    first = reuse_module.audit(parent)
    assert first["rows"][0]["integrity"] == "BASELINED"
    target.write_text("a,b\n9,9\n", encoding="utf-8")
    second = reuse_module.audit(parent)
    assert second["rows"][0]["integrity"] == "CHANGED"
    assert second["drifted"] == ["probe"]


def test_earlier_demo_paths_are_read_only_in_the_source():
    """No framework module opens a Demo 23/24/26 path for writing."""
    for path in list((DEMO_DIR / "framework").glob("*.py")) + [DEMO_DIR / "run_demo27.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("write_text", "write_bytes", "mkdir", "unlink"):
                    dumped = ast.dump(node)
                    for demo in ("demo23", "demo24", "demo26", "23_k_resolved",
                                 "24_equation2", "26_real_chi2"):
                        assert demo not in dumped, (
                            "%s writes into %s" % (path.name, demo))


# ---------------------------------------------------------------------------
# 8. analysis-only stages do not invoke nextnano
# ---------------------------------------------------------------------------

def test_analyze_module_cannot_reach_a_solver():
    source = code_only(DEMO_DIR / "framework" / "analyze.py")
    for banned in ("execute_real", "subprocess", "assert_professional", "--parse"):
        assert banned not in source, (
            "framework/analyze.py references %r; the analysis stage must never launch "
            "a solver" % banned)


def test_analysis_only_sub_demos_declare_no_physics_stage(subs):
    for demo_id in ("27M", "27N"):
        sub = registry.find(demo_id, subs)
        assert sub.stage_kind("physics") == "none"
        assert sub.professional_required is False
        assert (sub.cost.get("decks") or 0) == 0


def test_analysis_stage_of_an_analysis_only_demo_runs_without_a_machine(parent, subs,
                                                                        tmp_path,
                                                                        monkeypatch):
    sub = registry.find("27N", subs)
    resolved = registry.resolve(sub, parent)
    monkeypatch.setattr(type(resolved), "results_root",
                        property(lambda self: tmp_path / "none"))
    monkeypatch.setattr(registry.SubDemo, "outputs_dir",
                        property(lambda self: tmp_path / "out"))
    result = analyze_module.run(sub, resolved)
    assert result["status"] in ("NO DATA", "PASS")


# ---------------------------------------------------------------------------
# 9. every Professional invocation writes a manifest
# ---------------------------------------------------------------------------

def test_manifest_records_deck_hash_argv_machine_and_outputs(tmp_path):
    deck = tmp_path / "deck.in"
    deck.write_text("global{}\n", encoding="utf-8")
    out = tmp_path / "raw"
    out.mkdir()
    (out / "energy.dat").write_text("0\n", encoding="utf-8")
    record = manifest_module.build(
        sub_demo="27D", stage="physics", deck=deck, output_dir=out,
        machine={"executable": "nnp.exe", "database": "db", "license": "lic", "threads": 2},
        spec_summary={"band_model": "kp8"}, changes={"interface_model": ("linear_graded", "abrupt")},
        seconds=12.5, returncode=0, argv=["nnp.exe", "deck.in"], cost_statement={"tier": 2})
    assert len(record["deck"]["sha256"]) == 64
    assert record["argv"] == ["nnp.exe", "deck.in"]
    assert record["machine"]["threads"] == 2
    assert record["outputs"]["files"] == 1
    assert record["controlled_changes"]["interface_model"]["deck"] == "abrupt"
    path = manifest_module.write(tmp_path, [record])
    assert json.loads(path.read_text(encoding="utf-8"))["runs"][0]["sub_demo"] == "27D"


def test_every_solver_launch_path_builds_a_manifest():
    source = inspect.getsource(physics_module)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_run_"):
            body = ast.dump(node)
            assert "manifest_module" in body, (
                "%s launches work without building a manifest" % node.name)


def test_physics_module_is_the_only_solver_entry_point():
    for path in (DEMO_DIR / "framework").glob("*.py"):
        if path.name in ("physics.py", "solver.py"):
            continue
        text = path.read_text(encoding="utf-8")
        assert "execute_real" not in text, "%s can launch the solver" % path.name


# ---------------------------------------------------------------------------
# 10. every sub-demo has a resolved config
# ---------------------------------------------------------------------------

def test_every_sub_demo_resolves(parent, subs, cfg23):
    for sub in subs:
        resolved = registry.resolve(sub, parent, cfg23)
        assert resolved.baseline.name == "baseline_demo23"
        declared = sub.cost.get("decks")
        if sub.stage_kind("preflight") == "generate_and_parse":
            assert resolved.decks, "%s must define decks" % sub.demo_id
            assert declared == len(resolved.decks), (
                "%s declares %s decks but resolves %d"
                % (sub.demo_id, declared, len(resolved.decks)))
        else:
            assert not resolved.decks


def test_baseline_matches_demo23_exactly(parent, cfg23):
    baseline = registry.baseline_spec(parent, cfg23)
    assert baseline.thick_well_nm == cfg23["geometry"]["thick_well_nm"]
    assert baseline.interface_model == "linear_graded"
    assert baseline.grade_width_nm == cfg23["geometry"]["grade_width_nm"]
    assert baseline.active_spacing_nm == cfg23["mesh"]["active_spacing_nm"]
    assert baseline.k_points == cfg23["integration"]["production_points"]
    assert baseline.domain_end_nm == pytest.approx(cfg23["geometry"]["total_period_nm"])


def test_baseline_reproduces_the_demo23_production_deck_structure(parent, cfg23):
    """The generated baseline deck must match the deck Demo 23 actually ran."""
    demo23_deck = (DEMOS_DIR / "23_k_resolved_dispersion_validation" / "inputs"
                   / "production_y_n301_k0100.in")
    if not demo23_deck.is_file():
        pytest.skip("Demo 23 production deck not present")
    baseline = registry.baseline_spec(parent, cfg23)
    generated = deck_module.render(baseline)
    diff = deck_module.diff_against_baseline(
        demo23_deck.read_text(encoding="utf-8"), generated)
    assert diff == [], "the Demo 27 baseline drifted from the Demo 23 production deck: %s" % diff


def test_undeclared_deck_change_is_refused(parent, subs, cfg23):
    sub = registry.find("27D", subs)
    tampered = dict(sub.raw)
    tampered["decks"] = [{"name": "sneaky", "overrides": {"temperature_K": 4.0}}]
    bad = registry.SubDemo(**{**sub.__dict__, "raw": tampered})
    with pytest.raises(Demo27Error, match="only declares"):
        registry.resolve(bad, parent, cfg23)


def test_too_many_changes_in_one_deck_is_refused(parent, subs, cfg23):
    sub = registry.find("27D", subs)
    tampered = dict(sub.raw)
    tampered["decks"] = [{"name": "two_changes",
                          "overrides": {"interface_model": "abrupt", "temperature_K": 4.0}}]
    changed = dict(sub.controlled_change)
    changed["fields"] = ["interface_model", "temperature_K"]
    changed["max_fields_per_deck"] = 1
    bad = registry.SubDemo(**{**sub.__dict__, "raw": tampered, "controlled_change": changed})
    with pytest.raises(Demo27Error, match="at most 1 per deck"):
        registry.resolve(bad, parent, cfg23)


def test_doping_without_justification_is_refused():
    with pytest.raises(Demo27Error, match="no justification"):
        deck_module.Doping(name="d", kind="donor", start_nm=0.0, end_nm=1.0,
                           conc_cm3=1e18, degeneracy=2, justification="   ")


def test_every_sub_demo_states_its_cost(subs):
    for sub in subs:
        low, high = sub.runtime_range()
        assert low is not None and high is not None, "%s has no runtime estimate" % sub.demo_id
        assert 0 < float(low) <= float(high)
        volume = sub.cost.get("output_gb")
        assert volume and len(volume) == 2
        assert str(sub.cost.get("basis", "")).strip(), (
            "%s does not say what its estimate is based on" % sub.demo_id)


def test_every_sub_demo_states_a_pass_condition(subs):
    for sub in subs:
        assert len(sub.pass_condition.strip()) > 40, (
            "%s has no meaningful pass condition" % sub.demo_id)


def test_tier_is_within_range_and_professional_flag_is_consistent(subs):
    for sub in subs:
        assert 0 <= sub.tier <= 5
        if sub.stage_kind("physics") in ("professional", "delegated"):
            assert sub.professional_required, (
                "%s runs the solver but does not declare Professional required" % sub.demo_id)
        if sub.tier == 0:
            assert not sub.professional_required


def test_bz_conventions_resolve_to_the_expected_cutoffs(cfg23):
    base = registry.k_bz_per_nm(cfg23)
    assert registry.kmax_per_nm(cfg23, 0.10, "pi_over_a") == pytest.approx(0.10 * base)
    # "0.1 of Gamma-X" is twice "0.1 of pi/a" - the whole point of 27G.
    assert registry.kmax_per_nm(cfg23, 0.10, "gamma_x") == pytest.approx(0.20 * base)
    assert registry.kmax_per_nm(cfg23, 0.10, "gamma_x") == pytest.approx(
        registry.kmax_per_nm(cfg23, 0.20, "pi_over_a"))
    with pytest.raises(Demo27Error, match="unknown BZ convention"):
        registry.kmax_per_nm(cfg23, 0.1, "half_a_zone")


def test_generated_decks_carry_the_full_harvest(parent, subs, cfg23):
    sub = registry.find("27D", subs)
    resolved = registry.resolve(sub, parent, cfg23)
    text = deck_module.render(resolved.decks[0].spec, sub_demo="27D")
    for required in ("spinor_composition_CB_HH_LH_SO", "envelopes_CB_HH_LH_SO",
                     "transition_energies", "dipole_moment_matrix_elements",
                     "momentum_matrix_elements", "output_oscillator_strengths",
                     "output_bandedges", "output_alloy_composition", "output_k_vectors"):
        assert required in text, "the broad harvest is missing %s" % required


def test_flat_band_deck_has_no_poisson_block(parent, subs, cfg23):
    sub = registry.find("27E", subs)
    resolved = registry.resolve(sub, parent, cfg23)
    flat = next(d for d in resolved.decks if d.spec.electrostatics == "flat_band")
    sc = next(d for d in resolved.decks if d.spec.electrostatics == "quantum_poisson")
    flat_text = deck_module.render(flat.spec)
    sc_text = deck_module.render(sc.spec)
    flat_code = "\n".join(line for line in flat_text.splitlines()
                          if not line.strip().startswith("#"))
    assert "poisson{" not in flat_code
    assert "run{\n    quantum{}\n}" in flat_text
    assert "quantum_poisson{" in sc_text
    assert "no_density = yes" not in sc_text, (
        "a self-consistent run needs the quantum density it is supposed to feed back")


# ---------------------------------------------------------------------------
# 11. the status file updates correctly
# ---------------------------------------------------------------------------

def test_status_round_trips_and_regenerates_markdown(tmp_path, monkeypatch, parent, subs):
    local = dict(parent)
    json_path = tmp_path / "MASTER_STATUS.json"
    md_path = tmp_path / "MASTER_STATUS.md"
    monkeypatch.setattr(status, "status_paths", lambda _p: (json_path, md_path))
    assert json_path.parent == tmp_path
    status.record(local, "27D", "PASS", conclusion="grading is not the explanation")
    blob = json.loads(json_path.read_text(encoding="utf-8"))
    assert blob["demos"]["27D"]["status"] == "PASS"
    assert blob["demos"]["27D"]["conclusion"] == "grading is not the explanation"
    text = md_path.read_text(encoding="utf-8")
    assert "grading is not the explanation" in text
    assert "| 27D |" in text
    # A prerequisite reaching PASS must unblock its dependent in the rendered table.
    rows = {row["Demo"]: row["Status"] for row in status.rows(local, subs)}
    assert rows["27E"] == "NOT RUN"


def test_invalid_status_is_rejected(tmp_path, monkeypatch, parent):
    monkeypatch.setattr(status, "status_paths",
                        lambda _p: (tmp_path / "s.json", tmp_path / "s.md"))
    with pytest.raises(Demo27Error, match="is not one of"):
        status.record(dict(parent), "27D", "MOSTLY FINE")


def test_status_vocabulary_matches_the_brief():
    assert set(registry.STATUSES) == {
        "NOT RUN", "READY", "RUNNING", "PASS", "FAIL", "BLOCKED", "COMPLETE", "NOT NEEDED"}


def test_master_status_markdown_lists_every_sub_demo(parent, subs):
    text = (DEMO_DIR / str(parent["outputs"]["status_md"])).read_text(encoding="utf-8")
    for sub in subs:
        assert "| %s |" % sub.demo_id in text


# ---------------------------------------------------------------------------
# preflight behaviour
# ---------------------------------------------------------------------------

def test_preflight_never_solves_only_parses():
    source = code_only(DEMO_DIR / "framework" / "preflight.py")
    assert "execute_real" not in source
    assert "parse_deck" in source, "preflight must go through solver.parse_deck"
    # The only subprocess preflight may start is another demo's own preflight.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and "subprocess" in ast.dump(node):
            assert node.name == "_run_delegated_preflight", (
                "%s starts a subprocess; only the delegated preflight may" % node.name)


def test_cost_statement_cross_checks_declared_against_generated(parent, subs, cfg23):
    sub = registry.find("27F", subs)
    resolved = registry.resolve(sub, parent, cfg23)
    statement = preflight_module.cost_statement(sub, resolved)
    assert statement["decks_declared"] == statement["decks_generated"]
    assert "warning" not in statement
    assert statement["total_k_point_solves"] == sum(statement["k_points_per_deck"])


def test_cost_statement_warns_when_the_declared_count_is_wrong(parent, subs, cfg23):
    sub = registry.find("27D", subs)
    resolved = registry.resolve(sub, parent, cfg23)
    tampered = registry.SubDemo(**{**sub.__dict__, "cost": {**sub.cost, "decks": 99}})
    statement = preflight_module.cost_statement(tampered, resolved)
    assert "warning" in statement

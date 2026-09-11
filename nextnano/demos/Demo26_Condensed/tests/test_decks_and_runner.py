"""Script 1: deck reproduction and launcher behaviour. Nothing here launches nextnano."""
import json
import subprocess

import pytest

from src import decks, runner


def test_default_render_matches_demo26_dataset_deck(root):
    assert decks.same_deck(decks.render_kp8(), decks.read(root / "validation/decks/demo23_production_y_n301_k0100.in"))


def test_shipped_deck_is_the_current_render(root):
    assert decks.same_deck(decks.read(root / "decks/kp8_dispersion.in"), decks.render_kp8())


def test_config_defaults_equal_renderer_defaults(root):
    cfg = json.loads((root / "config/runner.json").read_text())["kp8"]
    params = {k: v for k, v in cfg.items() if k not in ("job", "purpose")}
    assert decks.same_deck(decks.render_kp8(params), decks.render_kp8())


def test_k_override_matches_demo27G_deck(root):
    text = decks.render_kp8({"k_max_per_nm": 1.11142887846, "k_points": 601})
    assert decks.same_deck(text, decks.read(root / "validation/decks/demo27G_bz_0p10_gamma_x.in"))


def test_abrupt_override_matches_demo27D_deck(root):
    text = decks.render_kp8({"interface_model": "abrupt"})
    assert decks.same_deck(text, decks.read(root / "validation/decks/demo27D_abrupt_paper_geometry.in"))


def test_legacy_decks_byte_identical_to_sources(root):
    for name in ("singleband_case04_graded.in", "singleband_case00_abrupt.in"):
        assert (root / "decks" / name).read_bytes() == (root / "validation/decks" / name).read_bytes()


def test_static_checks(root):
    assert decks.static_check(decks.render_kp8(), "kp8") == []
    assert decks.static_check(decks.read(root / "decks/singleband_case00_abrupt.in"), "singleband") == []
    assert decks.static_check("global{", "kp8")


def test_command_order():
    assert runner.command("C:/Program Files/nn.exe", "db.nnp", "l.lic", "deck.in", "out dir", 3) == [
        "C:/Program Files/nn.exe", "-d", "db.nnp", "-l", "l.lic", "--threads", "3", "-o", "out dir", "deck.in"]


@pytest.fixture
def isolated(monkeypatch):
    for key in ("NEXTNANO_EXE", "NEXTNANO_DATABASE", "NEXTNANO_LICENSE", "NEXTNANO_MACHINE",
                "NEXTNANO_PARSER_EXE", "NEXTNANO_PARSER_DATABASE", "DEMO26_RAW_OUTPUT"):
        monkeypatch.delenv(key, raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("a nextnano process was launched")
    monkeypatch.setattr(runner.subprocess, "run", forbidden)


def fake_professional(tmp_path):
    exe, db, lic = tmp_path / "nextnano++_pro.exe", tmp_path / "db.nnp", tmp_path / "l.lic"
    for p in (exe, db, lic):
        p.write_text("x")
    return ["--exe", str(exe), "--database", str(db), "--license", str(lic)]


def test_preflight_launches_nothing(tmp_path, isolated):
    assert runner.main(["--preflight", "--no-parse", "--output", str(tmp_path)]) == 0
    m = json.loads((tmp_path / "preflight_manifest.json").read_text())
    assert m["professional_execution_performed"] is False
    assert [j["job"] for j in m["jobs"]] == ["kp8", "singleband_case04_graded", "singleband_case00_abrupt"]
    assert m["script2_parser_self_test_on_shipped_cached_raw"]["modes"]["kp8"] == "available"
    assert not (tmp_path / "decks").exists()


def test_dry_run_writes_decks_but_no_results(tmp_path, isolated):
    assert runner.main(["--dry-run", "--jobs", "kp8", "--no-parse", "--output", str(tmp_path)]) == 0
    assert decks.same_deck((tmp_path / "decks/kp8.in").read_text(), decks.render_kp8())
    assert not (tmp_path / "kp8").exists()


def test_run_refuses_without_professional(tmp_path, isolated):
    assert runner.main(["--run", "--no-parse", "--output", str(tmp_path / "o")]) == 2
    assert not (tmp_path / "o").exists()


def test_run_refuses_free_build(tmp_path, isolated):
    exe, db, lic = tmp_path / "nextnano++_free.exe", tmp_path / "db.nnp", tmp_path / "l.lic"
    for p in (exe, db, lic):
        p.write_text("x")
    argv = ["--run", "--no-parse", "--exe", str(exe), "--database", str(db), "--license", str(lic), "--output", str(tmp_path / "o")]
    assert runner.main(argv) == 2


def test_run_refuses_to_overwrite_existing_results_without_touching_them(tmp_path, isolated):
    out = tmp_path / "o"
    (out / "kp8").mkdir(parents=True)
    (out / "kp8" / "previous_result.dat").write_text("old")
    (out / runner.METADATA).write_text("previous metadata")
    assert runner.main(["--run", "--no-parse", *fake_professional(tmp_path), "--output", str(out)]) == 2
    assert (out / runner.METADATA).read_text() == "previous metadata"
    assert not (out / "decks").exists()


def test_timeout_marks_the_job_failed(tmp_path, isolated, monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(runner.subprocess, "run", slow)
    out = tmp_path / "o"
    assert runner.main(["--run", "--no-parse", "--jobs", "kp8", *fake_professional(tmp_path), "--output", str(out)]) == 1
    job = json.loads((out / runner.METADATA).read_text())["jobs"][0]
    assert job["status"] == "FAIL" and "timeout" in job["error"]


def test_machine_file_and_invalid_threads(tmp_path, isolated):
    f = tmp_path / "m.yaml"
    f.write_text('# comment\nexecutable: "C:/nn/x.exe"\ndatabase: C:/nn/db.nnp\nlicense: C:/nn/l.lic\nthreads: 4\n')
    assert runner.read_machine(f) == {"exe": "C:/nn/x.exe", "database": "C:/nn/db.nnp", "license": "C:/nn/l.lic", "threads": "4"}
    assert runner.main(["--threads", "0", "--no-parse", "--output", str(tmp_path / "o")]) == 2

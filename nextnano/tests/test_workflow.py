"""Non-licensed tests for the portable nextnano++ workflow.

Everything here runs on a machine with no license and (mostly) no solver:
config parsing/validation, path portability, wildcard handling, and the
runner's control flow are exercised directly, while licensed *execution* is
mocked. These tests never run the nextnano++ solver, so a green run here does
NOT prove the decks are valid nextnano++ syntax -- that is verified on the
work laptop.

Test index (maps to the task's required test list):
     1 repo-relative path resolution      9 unmatched wildcard failure
     2 missing local config error        10 multiple-input ordering + dedup
     3 missing YAML section              11 output-dir assignment per input
     4 missing required keys             12 nonzero exit on validation failure
     5 Standard profile missing license  13 --check-config performs no execution
     6 valid temp configuration          14 --dry-run performs no execution
     7 env-var + ~ expansion             15 repo-relative works when repo copied
     8 wildcard expansion                16 git ignores config + outputs
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import nn_config
import run_input
from nn_config import ConfigError, NextnanoConfig, resolve_config


# --- helpers ----------------------------------------------------------------


def _write_config(
    tmp_path: Path,
    *,
    exe="exe.exe",
    database="db.nnp",
    outputdirectory="out",
    license_="lic.lic",
    threads=4,
    profile=None,
    make_files=True,
    section_name="nextnano++",
) -> Path:
    """Write a paths.local.yaml under tmp_path and (optionally) create the
    exe/database/license files and output dir it points at. Returns the yaml."""
    if make_files:
        if exe:
            (tmp_path / exe).write_text("", encoding="utf-8")
        if database:
            (tmp_path / database).write_text("", encoding="utf-8")
        if license_:
            (tmp_path / license_).write_text("", encoding="utf-8")

    def _p(name):
        return str((tmp_path / name).as_posix()) if name else ""

    lines = [f"{section_name}:"]
    lines.append(f'  exe: "{_p(exe)}"')
    lines.append(f'  database: "{_p(database)}"')
    lines.append(f'  license: "{_p(license_)}"')
    lines.append(f'  outputdirectory: "{_p(outputdirectory)}"')
    lines.append(f"  threads: {threads}")
    if profile is not None:
        lines.append(f'  profile: "{profile}"')
    cfg = tmp_path / "paths.local.yaml"
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cfg


REAL_DECK = nn_config.INPUT_DIR / "hello_01_bulk_gaas.in"


# --- 1. repo-relative path resolution ---------------------------------------


def test_paths_are_repo_relative_to_module():
    # NEXTNANO_ROOT is the nextnano/ dir, derived from the module file, not cwd.
    assert nn_config.NEXTNANO_ROOT == Path(nn_config.__file__).resolve().parents[1]
    assert nn_config.CONFIG_PATH == nn_config.NEXTNANO_ROOT / "config" / "paths.local.yaml"
    assert nn_config.INPUT_DIR == nn_config.NEXTNANO_ROOT / "inputs"
    assert nn_config.DEFAULT_OUTPUT_DIR == nn_config.NEXTNANO_ROOT / "output"


def test_no_hardcoded_drive_paths_in_scripts():
    # Guard against absolute Windows paths creeping into tracked code.
    for mod in (nn_config, run_input):
        text = Path(mod.__file__).read_text(encoding="utf-8")
        assert "C:\\" not in text and "C:/" not in text


# --- 2. missing local config error ------------------------------------------


def test_missing_config_raises_with_copy_hint(tmp_path):
    with pytest.raises(ConfigError) as exc:
        resolve_config(tmp_path / "does_not_exist.yaml")
    msg = str(exc.value)
    assert "not found" in msg
    assert "copy" in msg.lower()  # actionable instruction present


# --- 3. missing YAML section ------------------------------------------------


def test_missing_section_raises(tmp_path):
    cfg = tmp_path / "paths.local.yaml"
    cfg.write_text("some_other_section:\n  foo: bar\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="nextnano\\+\\+"):
        resolve_config(cfg)


# --- 4. missing required keys -----------------------------------------------


def test_missing_required_keys_raises(tmp_path):
    cfg = tmp_path / "paths.local.yaml"
    cfg.write_text('nextnano++:\n  exe: "x"\n', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        resolve_config(cfg)
    assert "database" in str(exc.value)
    assert "outputdirectory" in str(exc.value)


# --- 5. Standard profile missing license ------------------------------------


def test_standard_profile_requires_license(tmp_path):
    cfg = _write_config(tmp_path, license_="", profile="standard", make_files=True)
    with pytest.raises(ConfigError, match="license"):
        resolve_config(cfg)


def test_empty_license_defaults_to_free(tmp_path):
    cfg = _write_config(tmp_path, license_="", profile=None)
    resolved = resolve_config(cfg)
    assert resolved.profile == nn_config.PROFILE_FREE
    assert resolved.license is None


# --- 6. valid temporary configuration ---------------------------------------


def test_valid_config_resolves(tmp_path):
    cfg = _write_config(tmp_path, threads=8)
    resolved = resolve_config(cfg)
    assert isinstance(resolved, NextnanoConfig)
    assert resolved.profile == nn_config.PROFILE_STANDARD
    assert resolved.exe == (tmp_path / "exe.exe").resolve()
    assert resolved.database == (tmp_path / "db.nnp").resolve()
    assert resolved.license == (tmp_path / "lic.lic").resolve()
    assert resolved.outputdirectory == (tmp_path / "out").resolve()
    assert resolved.threads == 8
    # execute_kwargs carries everything and supports a per-input override.
    kw = resolved.execute_kwargs(outputdirectory=tmp_path / "out" / "deckA")
    assert kw["exe"] == str(resolved.exe)
    assert kw["outputdirectory"] == str(tmp_path / "out" / "deckA")
    assert kw["threads"] == 8
    assert kw["license"] == str(resolved.license)


def test_bad_threads_raises(tmp_path):
    cfg = _write_config(tmp_path, threads="not-an-int")
    with pytest.raises(ConfigError, match="threads"):
        resolve_config(cfg)


# --- 7. env-var + ~ expansion -----------------------------------------------


def test_env_and_home_expansion(tmp_path, monkeypatch):
    (tmp_path / "exe.exe").write_text("", encoding="utf-8")
    (tmp_path / "db.nnp").write_text("", encoding="utf-8")
    (tmp_path / "lic.lic").write_text("", encoding="utf-8")
    monkeypatch.setenv("NN_TESTROOT", str(tmp_path))
    # USERPROFILE (Windows) / HOME drive expanduser for the leading ~.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = tmp_path / "paths.local.yaml"
    cfg.write_text(
        "nextnano++:\n"
        '  exe: "${NN_TESTROOT}/exe.exe"\n'
        '  database: "~/db.nnp"\n'
        '  license: "${NN_TESTROOT}/lic.lic"\n'
        '  outputdirectory: "${NN_TESTROOT}/out"\n'
        "  threads: 2\n",
        encoding="utf-8",
    )
    resolved = resolve_config(cfg)
    assert resolved.exe == (tmp_path / "exe.exe").resolve()
    assert resolved.database == (tmp_path / "db.nnp").resolve()
    assert resolved.outputdirectory == (tmp_path / "out").resolve()


# --- 8. wildcard expansion --------------------------------------------------


def test_wildcard_expansion(tmp_path):
    for name in ("hello_02.in", "hello_01.in"):  # created out of order
        (tmp_path / name).write_text("", encoding="utf-8")
    result = run_input.expand_inputs([str(tmp_path / "hello_*.in")])
    assert [p.name for p in result] == ["hello_01.in", "hello_02.in"]  # sorted


# --- 9. unmatched wildcard / path failure -----------------------------------


def test_unmatched_wildcard_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no files match"):
        run_input.expand_inputs([str(tmp_path / "zzz_*.in")])


def test_missing_plain_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        run_input.expand_inputs([str(tmp_path / "nope.in")])


# --- 10. multiple-input ordering + dedup ------------------------------------


def test_ordering_and_dedup(tmp_path):
    a = tmp_path / "a.in"
    b = tmp_path / "b.in"
    a.write_text("", encoding="utf-8")
    b.write_text("", encoding="utf-8")
    result = run_input.expand_inputs([str(b), str(a), str(b)])
    assert [p.name for p in result] == ["b.in", "a.in"]  # order kept, dup dropped


# --- 11. output-directory assignment per input ------------------------------


def test_output_dir_assignment_is_per_input(tmp_path):
    cfg = resolve_config(_write_config(tmp_path))
    deck_a = tmp_path / "hello_01.in"
    deck_b = tmp_path / "hello_02.in"
    plan = run_input.build_plan(cfg, [deck_a, deck_b])
    outs = [out for _deck, out in plan]
    assert outs[0] == cfg.outputdirectory / "hello_01"
    assert outs[1] == cfg.outputdirectory / "hello_02"
    assert outs[0] != outs[1]  # cannot overwrite each other


# --- 12. nonzero exit on validation failure ---------------------------------


def test_main_check_config_bad_config_returns_nonzero(tmp_path):
    bad = tmp_path / "paths.local.yaml"
    bad.write_text("nope:\n  x: 1\n", encoding="utf-8")
    assert run_input.main(["--check-config", "--config", str(bad)]) == 1


def test_main_unmatched_input_returns_2(tmp_path):
    good = _write_config(tmp_path)
    rc = run_input.main(["--config", str(good), str(tmp_path / "missing_*.in")])
    assert rc == 2


def test_main_no_inputs_returns_2(tmp_path):
    good = _write_config(tmp_path)
    assert run_input.main(["--config", str(good)]) == 2


# --- 13/14. --check-config and --dry-run perform no execution ---------------


@pytest.fixture
def no_execute(monkeypatch):
    """Replace InputFile.execute with a recorder that fails the test if run."""
    nn = pytest.importorskip("nextnanopy")
    calls = []

    def _forbidden(self, *a, **k):  # pragma: no cover - must never be hit
        calls.append((a, k))
        raise AssertionError("solver execute() must not be called")

    monkeypatch.setattr(nn.InputFile, "execute", _forbidden)
    return calls


def test_check_config_does_not_execute(tmp_path, no_execute):
    good = _write_config(tmp_path)
    rc = run_input.main(["--check-config", "--config", str(good), str(REAL_DECK)])
    assert rc == 0  # temp exe/db/license exist, output writable, deck exists
    assert no_execute == []


def test_dry_run_does_not_execute(tmp_path, no_execute):
    good = _write_config(tmp_path)
    rc = run_input.main(["--dry-run", "--config", str(good), str(REAL_DECK)])
    assert rc == 0
    assert no_execute == []


# --- 15. repo-relative paths work when the repo is copied elsewhere ----------


def test_repo_relative_when_copied(tmp_path):
    # Recreate a minimal nextnano/ tree under an arbitrary parent and import the
    # copied nn_config.py from there; its NEXTNANO_ROOT must point at the copy.
    fake_root = tmp_path / "somewhere" / "else" / "nextnano"
    (fake_root / "scripts").mkdir(parents=True)
    (fake_root / "config").mkdir()
    (fake_root / "inputs").mkdir()
    (fake_root / "output").mkdir()
    shutil.copy(nn_config.__file__, fake_root / "scripts" / "nn_config.py")

    spec = importlib.util.spec_from_file_location(
        "nn_config_copy", fake_root / "scripts" / "nn_config.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: dataclasses with `from __future__ import annotations`
    # resolve field types via sys.modules[cls.__module__] at class-creation time.
    sys.modules["nn_config_copy"] = mod
    try:
        spec.loader.exec_module(mod)
        assert mod.NEXTNANO_ROOT == fake_root.resolve()
        assert mod.CONFIG_PATH == fake_root.resolve() / "config" / "paths.local.yaml"
    finally:
        sys.modules.pop("nn_config_copy", None)


# --- 16. git ignores config + outputs, tracks decks + example ---------------


def _check_ignore(repo_root: Path, rel: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", rel],
        capture_output=True,
    )
    return result.returncode == 0  # 0 => ignored, 1 => not ignored


def test_gitignore_rules():
    repo_root = Path(nn_config.__file__).resolve().parents[2]
    if not (repo_root / ".git").exists():  # pragma: no cover - non-git checkout
        pytest.skip("not a git checkout")
    # Ignored:
    assert _check_ignore(repo_root, "nextnano/config/paths.local.yaml")
    assert _check_ignore(repo_root, "nextnano/output/run_result.vtr")
    assert _check_ignore(repo_root, "nextnano/output/hello_01/bandedges.dat")
    assert _check_ignore(repo_root, "nextnano/inputs/some.lic")
    # Tracked (NOT ignored):
    assert not _check_ignore(repo_root, "nextnano/config/paths.local.yaml.example")
    assert not _check_ignore(repo_root, "nextnano/inputs/hello_01_bulk_gaas.in")
    assert not _check_ignore(repo_root, "nextnano/output/.gitkeep")


# --- bonus: real decks load without execution (home-laptop non-licensed) ----


def test_real_decks_load_without_execution():
    nn = pytest.importorskip("nextnanopy")
    for deck in ("hello_01_bulk_gaas.in", "hello_02_algaas_qw.in"):
        path = nn_config.INPUT_DIR / deck
        inp = nn.InputFile(str(path))  # loads/parses; does not execute
        assert inp.product == "nextnano++"

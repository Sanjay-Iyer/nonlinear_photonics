"""nextnano/scripts/raw_data.py: register copies byte-identically, verify catches changes."""
import json

import pytest

import raw_data


def _source(tmp_path):
    src = tmp_path / "solver_output"
    (src / "run" / "bias_00000").mkdir(parents=True)
    (src / "run" / "deck.in").write_text("global{ temperature = 300 }\n")
    (src / "run" / "bias_00000" / "energy_spectrum_k00000.dat").write_text("no. Energy[eV]\n1 1.5\n")
    return src


def _record(date="2026-01-02"):
    return {"date": date, "machine": "WORK", "licensed": True, "solver": {"version": "test"},
            "deck": {"path": "data/run/deck.in"}, "physics": {"model": "test", "temperature_K": 300},
            "structure": "none", "status": "valid", "provenance": "unit test"}


def test_register_then_verify_passes_and_source_is_untouched(tmp_path):
    src = _source(tmp_path)
    before = raw_data.tree_hashes(src)
    folder = raw_data.register(5, "D005_2026-01-02_unit-test", src, _record(), tmp_path / "store")
    assert folder == tmp_path / "store" / "demo_005" / "D005_2026-01-02_unit-test"
    assert raw_data.tree_hashes(src) == before
    report = raw_data.verify(folder)
    assert report["result"] == "PASS" and report["files"] == 2
    record = json.loads((folder / "RUN_RECORD.json").read_text())
    assert record["deck"]["sha256"] == raw_data.sha256(folder / "data" / "run" / "deck.in")
    assert record["originating_demo"] == 5 and record["files"]["count"] == 2


def test_verify_reports_changed_missing_and_unlisted_files(tmp_path):
    folder = raw_data.register(5, "D005_2026-01-02_unit-test", _source(tmp_path), _record(), tmp_path / "store")
    (folder / "data" / "run" / "deck.in").write_text("edited\n")
    (folder / "data" / "run" / "bias_00000" / "energy_spectrum_k00000.dat").unlink()
    (folder / "data" / "extra.dat").write_text("x")
    problems = raw_data.verify(folder)["problems"]
    assert "changed: data/run/deck.in" in problems
    assert "missing: data/run/bias_00000/energy_spectrum_k00000.dat" in problems
    assert "unlisted: data/extra.dat" in problems


def test_register_refuses_overwrite_bad_ids_and_date_mismatch(tmp_path):
    src, store = _source(tmp_path), tmp_path / "store"
    raw_data.register(5, "D005_2026-01-02_unit-test", src, _record(), store)
    with pytest.raises(raw_data.RawDataError, match="overwrite"):
        raw_data.register(5, "D005_2026-01-02_unit-test", src, _record(), store)
    with pytest.raises(raw_data.RawDataError, match="must start with D006_"):
        raw_data.register(6, "D005_2026-01-02_other", src, _record(), store)
    with pytest.raises(raw_data.RawDataError, match="date"):
        raw_data.register(5, "D005_2026-01-03_other", src, _record(), store)
    with pytest.raises(raw_data.RawDataError, match="does not match"):
        raw_data.run_folder(store, "D5_2026-01-02_x")

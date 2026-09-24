"""Small software fixtures; none is a nextnano production result."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

from chi2.acquisition import config, check_decks, job_decks
from chi2 import decks
from chi2.full8 import matrix_data, pair_score, choose_k0, contract_interband, optical_gate, prepare, compare_k0_to_reference
from chi2.mixed_control import calculate
from chi2.transfer import validate, unpack, packed_frames


def _write(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def synthetic_bundle(root: Path) -> Path:
    """301 complete but tiny spinor frames and matching synthetic mixed raw tables."""
    c = config()
    bundle = root / "300K"
    (bundle / "full8/frames").mkdir(parents=True)
    k = np.linspace(0, c["k_max_per_nm"], 301)
    bases = np.array([1.30, 1.40, 1.45, 1.50, 2.80, 2.90, 3.00])
    energies = np.repeat(bases, 2)[None, :] + k[:, None]**2 * .01
    z = np.array([10., 19.])
    psi = np.zeros((14, 8, 2), complex)
    slots = [(2,0),(3,0),(4,0),(5,0),(2,1),(3,1),(6,0),(7,0),
             (6,1),(7,1),(0,0),(1,0),(0,1),(1,1)]
    for state, (component, point) in enumerate(slots):
        psi[state, component, point] = 1 / np.sqrt(4.5)
    comp = (abs(psi)**2).sum(axis=2) * 4.5
    for i, ki in enumerate(k):
        np.savez_compressed(bundle / "full8/frames" / f"k{i:05d}.npz",
                            k_index=np.int64(i), k_per_nm=np.float64(ki), energy_eV=energies[i],
                            z_nm=z, psi=psi, composition=comp, solver_state=np.arange(1,15),
                            components=np.array(("cb1","cb2","hh1","hh2","lh1","lh2","so1","so2")))
    np.savez_compressed(bundle / "full8/dispersion.npz", k_per_nm=k, energy_eV=energies,
                        direction=np.array([0,1,0]))
    for name, body in job_decks(300, c).items():
        _write(bundle / "decks" / f"{name}.in", body)
    _write(bundle / "run_metadata.json", json.dumps({"temperature_K": 300, "pilot": False,
        "professional_execution_performed": True, "source_config": c,
        "jobs": {name: {"status": "PASS"} for name in ("kp8", "singleband_case04_graded")}}))
    _write(bundle / "bundle.json", json.dumps({"format": "demo29-full8-numeric-v1",
        "temperature_K": 300, "k_points": 301, "candidate_states": 14}))
    _write(bundle / "source_checksums.json", "{}")
    kp = bundle / "mixed/kp8/bias_00000"
    _write(kp / "QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat",
           "k " + " ".join(f"e{s}" for s in range(14)) + "\n" +
           "\n".join(" ".join([f"{ki:.16g}"] + [f"{e:.16g}" for e in row]) for ki, row in zip(k, energies)) + "\n")
    _write(kp / "QuantumDispersions/acqw/kp8/kVectors_Gamma_to_y.dat",
           "no kx ky kz\n" + "\n".join(f"{i} 0 {ki:.16g} 0" for i, ki in enumerate(k)) + "\n")
    _write(kp / "Quantum/acqw/kp8/energy_spectrum_k00000.dat",
           "no Energy\n" + "\n".join(f"{i+1} {e:.16g}" for i,e in enumerate(energies[0])) + "\n")
    _write(kp / "Quantum/acqw/kp8/spinor_composition_k00000_CbHhLhSo.dat",
           "no cb1 cb2 hh1 hh2 lh1 lh2 so1 so2\n" +
           "\n".join(" ".join([str(i+1)] + [str(int(v)) for v in row]) for i,row in enumerate(comp)) + "\n")
    sb = bundle / "mixed/singleband_case04_graded/bias_00000/Quantum/acqw"
    for band, levels in (("Gamma", (2.9,3.0)), ("HH", (1.45,1.40))):
        _write(sb / band / "energy_spectrum_k00000.dat", "no Energy\n1 %s\n2 %s\n" % levels)
        _write(sb / band / "envelopes_k00000.dat", "z p1 p2\n10 1 0\n14.5 0.5 0.5\n19 0 1\n")
    rows = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            rows.append({"file": path.relative_to(bundle).as_posix(),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    _write(bundle / "checksums.json", json.dumps(rows))
    return bundle


def test_decks_temperature_is_only_sweep_change():
    c = config()
    assert check_decks(c)["status"] == "PASS"
    for kind in ("kp8", "singleband_case04_graded"):
        decks_by_t = {t: job_decks(t, c)[kind] for t in (100,300,500)}
        assert all(decks.without_temperature(body) == decks.without_temperature(decks_by_t[300])
                   for body in decks_by_t.values())
        assert all(f"temperature = {t}" in decks_by_t[t] for t in (100,300,500))


def test_spinor_matrices_and_optical_gate(tmp_path):
    z = np.array([10., 19.])
    psi = np.zeros((4, 8, 2), complex)
    for i, (component, point) in enumerate(((0,0),(1,0),(2,0),(3,0))):
        psi[i, component, point] = 1/np.sqrt(4.5)
    _, tensor, zm, norms = matrix_data(z, psi)
    assert np.allclose(norms, 1)
    assert np.allclose(zm, zm.conj().T)
    rotated = psi.copy()
    rotated[0], rotated[1] = (psi[0]+psi[1])/np.sqrt(2), (psi[0]-psi[1])/np.sqrt(2)
    assert pair_score(psi, rotated, np.array([4.5,4.5]))[0,0] == pytest.approx(1)
    with pytest.raises(ValueError, match="non-identity"):
        contract_interband(tensor, np.eye(8))
    with pytest.raises(ValueError, match="UNRESOLVED"):
        optical_gate(Path(__file__).resolve().parents[1] / "config/optical_operator.json")
    operator = {"status":"APPROVED", "basis":list(("cb1","cb2","hh1","hh2","lh1","lh2","so1","so2")),
                "operator_matrix":(np.ones((8,8))-np.eye(8)).tolist(),
                "operator_units":"dimensionless_relative_to_r_e_hh", "operator_source":"test only",
                "relationship_to_r_e_hh":"retain_r_e_hh_squared_once",
                "spin_reduction":"explicit_two_channels_plus_historical_factor_two"}
    path = tmp_path / "bad_spin.json"
    path.write_text(json.dumps(operator), encoding="utf-8")
    with pytest.raises(ValueError, match="double-counted spin"):
        optical_gate(path)


def test_transfer_and_both_300k_preparations(tmp_path):
    bundle = synthetic_bundle(tmp_path)
    assert validate(bundle)["status"] == "PASS"
    full = prepare(bundle, tmp_path / "full")
    assert full["k0_selection"]["selected"] == {"e1":5,"e2":6,"hh1":2,"hh2":0}
    assert full["ambiguous_pair_assignments"] == 0
    _, _, energy, z, psi, _, _ = next(packed_frames(bundle))
    same_temperature = compare_k0_to_reference(bundle, energy, z, psi, full["k0_selection"])
    assert all(record["consistent"] for record in same_temperature.values())
    mixed = calculate(bundle, tmp_path / "mixed")
    assert mixed["finite"] and mixed["temperature_K"] == 300
    archive = tmp_path / "demo29_300K_raw.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in bundle.rglob("*"):
            if path.is_file():
                z.write(path, (Path("300K") / path.relative_to(bundle)).as_posix())
    assert unpack(archive, tmp_path / "returned")["status"] == "PASS"
    with (bundle / "full8/frames/k00001.npz").open("ab") as f:
        f.write(b"altered")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        validate(bundle)


def test_actual_packer_lossless_three_point_fixture(tmp_path, monkeypatch):
    """Exercise the work-run packer without pretending the fixture is physics."""
    from chi2 import transfer
    c = {**config(), "k_points": 3}
    monkeypatch.setattr(transfer, "config", lambda: c)
    work = tmp_path / "work"
    k = np.linspace(0, c["k_max_per_nm"], 3)
    base = np.repeat(np.array([1.30,1.40,1.45,1.50,2.80,2.90,3.00]), 2)
    energy = base[None,:] + k[:,None]**2 * .01
    root = work / "kp8/bias_00000"
    _write(root / "QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat",
           "k " + " ".join(f"e{s}" for s in range(14)) + "\n" +
           "\n".join(" ".join([f"{ki:.16g}"] + [f"{v:.16g}" for v in row]) for ki,row in zip(k,energy)) + "\n")
    _write(root / "QuantumDispersions/acqw/kp8/kVectors_Gamma_to_y.dat",
           "no kx ky kz\n" + "\n".join(f"{i} 0 {ki:.16g} 0" for i,ki in enumerate(k)) + "\n")
    slots = [(2,0),(3,0),(4,0),(5,0),(2,1),(3,1),(6,0),(7,0),
             (6,1),(7,1),(0,0),(1,0),(0,1),(1,1)]
    names = ("cb1","cb2","hh1","hh2","lh1","lh2","so1","so2")
    for i in range(3):
        _write(root / f"Quantum/acqw/kp8/energy_spectrum_k{i:05d}.dat",
               "no Energy\n" + "\n".join(f"{s+1} {v:.16g}" for s,v in enumerate(energy[i])) + "\n")
        _write(root / f"Quantum/acqw/kp8/spinor_composition_k{i:05d}_CbHhLhSo.dat",
               "no " + " ".join(names) + "\n" +
               "\n".join(" ".join([str(s+1)] + [str(int(j == component)) for j in range(8)])
                         for s,(component,_) in enumerate(slots)) + "\n")
        for s,(component,point) in enumerate(slots, 1):
            for j,name in enumerate(names):
                values = [1/np.sqrt(4.5) if j == component and p == point else 0 for p in (0,1)]
                _write(root / f"Quantum/acqw/kp8/envelope_k{i:05d}_{s:04d}_{name}.dat",
                       f"z real imag\n10 {values[0]:.17g} 0\n19 {values[1]:.17g} 0\n")
    sb = work / "singleband_case04_graded/bias_00000/Quantum/acqw"
    for band, levels in (("Gamma",(2.9,3.0)),("HH",(1.45,1.40))):
        _write(sb / band / "energy_spectrum_k00000.dat", "no Energy\n1 %s\n2 %s\n" % levels)
        _write(sb / band / "envelopes_k00000.dat", "z p1 p2\n10 1 0\n14.5 0.5 0.5\n19 0 1\n")
    for name, body in job_decks(300, c).items():
        _write(work / "decks" / f"{name}.in", body)
        _write(work / f"{name}.log", "synthetic test only\n")
        _write(work / f"{name}_parse.log", "synthetic test only\n")
    _write(work / "run_metadata.json", json.dumps({"temperature_K":300,"pilot":False,
        "professional_execution_performed":True,"source_config":c,
        "jobs":{name:{"status":"PASS"} for name in ("kp8","singleband_case04_graded")}}))
    folder, archive = tmp_path / "transfer/300K", tmp_path / "demo29_300K_raw.zip"
    result = transfer.pack(work, folder, archive)
    assert result["status"] == "PASS" and archive.is_file()
    assert transfer.unpack(archive, tmp_path / "returned")["status"] == "PASS"
    with np.load(folder / "full8/frames/k00002.npz", allow_pickle=False) as d:
        assert d["psi"].dtype == np.complex128
        assert d["energy_eV"].shape == (14,)

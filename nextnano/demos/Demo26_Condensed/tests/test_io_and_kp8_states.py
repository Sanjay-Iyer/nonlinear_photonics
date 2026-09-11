"""Raw-file parsing and the 8-band k.p state/matrix-element reduction, on cached Professional output."""
import numpy as np
import pytest

from src import nextnano_io as io
from src.kp8_states import ORIGIN_SHIFT_NM, group_doublets, load_kp8_inputs, lowdin
from src.raw_inputs import available_modes, load_inputs


@pytest.fixture(scope="module")
def kp8(root):
    return load_kp8_inputs(root / "cached_raw/kp8")


def test_trapezoid_weights_exact_for_linear():
    x = np.sort(np.r_[0, np.random.default_rng(3).uniform(0, 1, 50), 1])
    w = io.trapezoid_weights(x)
    assert w.sum() == pytest.approx(1.0) and (w * x).sum() == pytest.approx(0.5)


def test_read_table_fixed_width_fallback(tmp_path):
    p = tmp_path / "t.dat"
    p.write_text("a         b         c         \n1.0000000002.0000000003.000000000\n")
    assert io.read_table(p)[1].tolist() == [[1.0, 2.0, 3.0]]


def test_dispersion_parser(root):
    k, energies, meta = io.read_dispersion(root / "cached_raw/kp8")
    assert energies.shape == (301, 14) and k[0] == 0 and k[-1] == pytest.approx(0.555714439232)
    assert meta["direction"] == pytest.approx([0, 1, 0])


def test_composition_is_mapped_by_header_not_position(root):
    comp = io.read_composition(io.find_one(root / "cached_raw/kp8", "spinor_composition_k00000_CbHhLhSo.dat"))
    hh, lh = comp["hh1"] + comp["hh2"], comp["lh1"] + comp["lh2"]
    assert hh[0] == pytest.approx(1.0) and lh[2] > 0.97  # state 1 pure HH, state 3 light hole


def test_doublet_grouping():
    assert group_doublets(np.array([1.0, 1.0, 1.1, 1.1 + 1e-12, 1.2, 1.2 + 3e-5])) == [(1, 2), (3, 4), (5,), (6,)]


def test_state_selection_by_band_character(kp8):
    assert kp8["state_ids"] == {"e1": [11, 12], "e2": [13, 14], "hh1": [5, 6], "hh2": [1, 2]}
    light_hole = next(r for r in kp8["doublet_table"] if r["states"] == [3, 4])
    assert light_hole["lh"] > 0.97 and light_hole["role"] == ""
    mixed = next(r for r in kp8["doublet_table"] if r["states"] == [7, 8])
    assert mixed["cb"] < 0.8 and mixed["role"] == ""


def test_scalar_envelopes_exact_and_orthonormal(kp8):
    assert max(d["second_singular_fraction"] for d in kp8["envelope_reduction"].values()) < 1e-12
    assert max(d["imaginary_residue"] for d in kp8["envelope_reduction"].values()) < 1e-12
    assert kp8["checks"]["orthonormality_error_after_lowdin"] < 1e-12
    assert kp8["checks"]["composition_file_max_abs_difference"] < 1e-6


def test_matrix_element_shapes_and_hermiticity(kp8):
    for key in ("overlap", "ze_nm", "zh_nm"):
        assert np.asarray(kp8[key]).shape == (2, 2)
    assert np.allclose(kp8["ze_nm"], np.asarray(kp8["ze_nm"]).T) and np.allclose(kp8["zh_nm"], np.asarray(kp8["zh_nm"]).T)
    assert kp8["electron_eV"].shape == kp8["valence_eV"].shape == (2, 301)


def test_branch_energies_exposed_and_degenerate_at_zone_centre(kp8):
    eb, vb = kp8["electron_branches_eV"], kp8["valence_branches_eV"]
    assert eb.shape == vb.shape == (2, 2, 301)
    assert np.allclose(eb[:, 0, 0], eb[:, 1, 0], atol=1e-9) and np.allclose(vb[:, 0, 0], vb[:, 1, 0], atol=1e-9)
    assert np.allclose(eb.mean(axis=1), kp8["electron_eV"]) and np.allclose(vb.mean(axis=1), kp8["valence_eV"])
    assert max(kp8["checks"]["max_doublet_splitting_eV"].values()) > 1e-3  # splitting is real and reported
    assert eb.min() > vb.max()  # every electron branch lies above every hole branch at every k


def test_origin_check_is_not_a_tautology(kp8):
    """Shifting z inside the integrals changes Ze by c*Gram: zero off-diagonal only after Loewdin."""
    c = ORIGIN_SHIFT_NM
    final, final_s = kp8, kp8["matrices_origin_shifted"]
    pre, pre_s = kp8["matrices_pre_lowdin"], kp8["matrices_pre_lowdin_origin_shifted"]
    assert np.allclose(np.asarray(final_s["ze_nm"]) - final["ze_nm"], c * np.eye(2), atol=1e-9)
    gram_e = np.asarray(kp8["checks"]["gram_before_lowdin_electron"])
    assert abs(gram_e[0, 1]) > 1e-3
    assert np.allclose(np.asarray(pre_s["ze_nm"]) - pre["ze_nm"], c * gram_e, atol=1e-9)


def test_z_agrees_with_nextnano_own_dipole_output(kp8):
    c = kp8["checks"]
    assert c["package_abs_zh12_nm"] == pytest.approx(c["nextnano_dipole_hh1_hh2_nm"], rel=1e-4)
    assert c["package_abs_ze12_nm"] == pytest.approx(c["nextnano_dipole_e1_e2_nm"], rel=0.01)


def test_selected_branches_stay_at_least_gamma_from_other_columns(kp8):
    assert min(kp8["checks"]["min_member_gap_to_other_columns_eV"].values()) > 0.005


def test_full_spinor_overlap_vanishes(root):
    """Why Eq. 2 uses block envelopes: kp8 eigenstates are mutually orthogonal."""
    kp8_dir = io.find_one(root / "cached_raw/kp8", "energy_spectrum_k00000.dat").parent
    z, psi = io.read_kp8_envelopes(kp8_dir, [5, 11])
    assert abs(np.sum(np.conj(psi[11]) * psi[5] * io.trapezoid_weights(z))) < 1e-10


def test_lowdin_restores_orthonormality():
    z = np.linspace(0, 1, 201)
    w = io.trapezoid_weights(z)
    F = np.column_stack([np.sin(np.pi * z), np.sin(np.pi * z) + 0.3 * np.sin(2 * np.pi * z)])
    G, _ = lowdin(F, w)
    assert np.allclose(G.T @ (G * w[:, None]), np.eye(2), atol=1e-12)


def test_all_modes_available_on_cached_raw(root):
    assert set(available_modes(root / "cached_raw").values()) == {"available"}


def test_historical_modes_keep_their_documented_inputs(root):
    base = load_inputs(root / "cached_raw", "demo26-baseline")
    assert base["kp8_pair_ids"] == [[11, 12], [13, 14], [5, 6], [3, 4]] and base["supplied_inputs"] == []
    cut = load_inputs(root / "cached_raw", "demo26-cutoff")
    assert [s["file"] for s in cut["supplied_inputs"]] == ["supplied/case00_abrupt_matrix_elements.json"]


def test_missing_raw_file_names_the_file(tmp_path):
    with pytest.raises(io.RawDataError, match="energy_spectrum"):
        load_kp8_inputs(tmp_path)

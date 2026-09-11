"""Eight-band k.p states -> the scalar inputs of Equation 2 (production path).

Everything here comes from ONE nextnano++ kp_8band calculation:

* Kramers doublets are grouped from the k=0 energy spectrum.
* Band character (CB/HH/LH/SO fractions) is computed from the spinor envelopes
  and cross-checked against nextnano's own spinor_composition file.
* e1, e2 = the two lowest doublets with CB fraction >= 0.8. (The doublets at
  2.339 eV in the shipped run are 56% CB mid-gap mixed states; the filter excludes them.)
  hh1, hh2 = the two highest valence doublets with HH fraction >= 0.8.
  (Selecting holes by energy alone picks the light-hole doublet as "hh2" in this
  structure; its envelope is not orthogonal to hh1 and nextnano's own
  <hh1|z|lh1> vanishes, so it is not a valid Eq. 2 heavy-hole state.)
* Each doublet's dominant-block envelope (CB block for electrons, HH block for
  holes) is reduced to ONE real function by SVD over both Kramers members. This
  is invariant to the arbitrary unitary mixing LAPACK returns inside a doublet,
  and is exact when the second singular value and the imaginary residue vanish
  (both checked).
* Envelopes are unit-normalized and Loewdin-orthonormalized within each band, so
  diagonal z terms are origin-independent. Eq. 2 factors the Bloch part into
  r_e,hh, so the full spinor inner product <e|h> (which is zero by orthogonality)
  is NOT the Eq. 2 overlap.
* Energies: at k != 0 each doublet splits into two branches (structure inversion
  asymmetry). Both energy-sorted columns are returned; the analysis averages chi2
  over the four lower/upper electron-hole branch pairings. Doublet-mean energies
  are also returned for the sensitivity comparison.
* M(k) = M(0): the deck exports spinors at k=0 only.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

from . import nextnano_io as io

CB_MIN, HH_MIN, SVD_MAX_RESIDUAL, IMAG_MAX_RESIDUE = 0.8, 0.8, 1e-6, 1e-6
ORIGIN_SHIFT_NM = 20.0


def group_doublets(energies: np.ndarray, tol_eV: float = 1e-6) -> list[tuple[int, ...]]:
    groups, start = [], 0
    for i in range(1, len(energies) + 1):
        if i == len(energies) or energies[i] - energies[start] > tol_eV:
            groups.append(tuple(range(start + 1, i + 1)))
            start = i
    return groups


def block_fractions(psi: np.ndarray, w: np.ndarray) -> dict[str, float]:
    dens = (np.abs(psi) ** 2 * w).sum(axis=1)
    idx = {c: i for i, c in enumerate(io.KP8_COMPONENTS)}
    total = dens.sum()
    return {b: float(sum(dens[idx[c]] for c in comps) / total) for b, comps in io.BLOCKS.items()}


def scalar_envelope(psi: dict, members: tuple[int, ...], block: str, w: np.ndarray):
    idx = [io.KP8_COMPONENTS.index(c) for c in io.BLOCKS[block]]
    M = np.array([psi[s][i] for s in members for i in idx]).T * np.sqrt(w)[:, None]
    U, S, _ = np.linalg.svd(M, full_matrices=False)
    u = U[:, 0] / np.sqrt(w)
    f = u * np.exp(-1j * np.angle(np.sum(u * u * w)) / 2)
    imag = float(np.sum(f.imag ** 2 * w) / np.sum(np.abs(f) ** 2 * w))
    f = f.real / np.sqrt(np.sum(f.real ** 2 * w))
    if f[np.argmax(np.abs(f))] < 0:
        f = -f
    diag = {"block": block, "block_weight": float((S ** 2).sum() / len(members)),
            "second_singular_fraction": float((S[1:] ** 2).sum() / (S ** 2).sum()),
            "imaginary_residue": imag}
    return f, diag


def lowdin(F: np.ndarray, w: np.ndarray):
    S = F.T @ (F * w[:, None])
    vals, vecs = np.linalg.eigh(S)
    return F @ (vecs @ np.diag(vals ** -0.5) @ vecs.T), S


def matrix_elements(Fe, Fh, z, w):
    ip = lambda A, B, x=1: (A * x).T @ (B * w[:, None])
    return ip(Fe, Fh), ip(Fe, Fe, z[:, None]), ip(Fh, Fh, z[:, None])


def _as_dict(triple, **extra):
    return {"overlap": triple[0], "ze_nm": triple[1], "zh_nm": triple[2], **extra}


def kramers_invariant(dipole: dict, A: tuple, B: tuple) -> float:
    """sqrt(sum |<a|z|b>|^2 / 2) over doublet members: U(2)-invariant |z| per member."""
    return float(np.sqrt(sum(abs(dipole[(a, b)]) ** 2 for a in A for b in B) / 2))


def load_kp8_inputs(root: Path) -> dict:
    root = Path(root)
    spectrum = io.find_one(root, "kp8/energy_spectrum_k00000.dat")
    kp8_dir = spectrum.parent
    energies = io.read_energy_spectrum(spectrum)
    doublets = group_doublets(energies)
    z, psi = io.read_kp8_envelopes(kp8_dir, list(range(1, len(energies) + 1)))
    w = io.trapezoid_weights(z)

    comp_path = io.find_optional(kp8_dir, "spinor_composition_k00000_CbHhLhSo.dat")
    comp = io.read_composition(comp_path) if comp_path else None
    table, comp_err = [], 0.0
    for d in doublets:
        fr = {b: float(np.mean([block_fractions(psi[s], w)[b] for s in d])) for b in io.BLOCKS}
        if comp:
            for s in d:
                own = block_fractions(psi[s], w)
                for b, cs in io.BLOCKS.items():
                    comp_err = max(comp_err, abs(own[b] - sum(comp[c][s - 1] for c in cs)))
        table.append({"states": list(d), "energy_eV": float(energies[d[0] - 1]), **fr})

    electrons = sorted([r for r in table if r["cb"] >= CB_MIN], key=lambda r: r["energy_eV"])
    if len(electrons) < 2:
        raise io.RawDataError("fewer than two conduction doublets with CB >= 0.8; raise num_electrons")
    valence = [r for r in table if r["energy_eV"] < electrons[0]["energy_eV"] and r["hh"] >= HH_MIN]
    holes = sorted(valence, key=lambda r: -r["energy_eV"])
    if len(holes) < 2:
        raise io.RawDataError("fewer than two heavy-hole doublets with HH >= 0.8; raise num_holes")
    roles = {"e1": electrons[0], "e2": electrons[1], "hh1": holes[0], "hh2": holes[1]}
    for r in table:
        r["role"] = next((k for k, v in roles.items() if v is r), "")
    for role, row in roles.items():
        if len(row["states"]) != 2:
            raise io.RawDataError(f"{role} is not a Kramers doublet: states {row['states']}")

    env, env_diag = {}, {}
    for role, row in roles.items():
        env[role], env_diag[role] = scalar_envelope(psi, tuple(row["states"]), "cb" if role[0] == "e" else "hh", w)
        d = env_diag[role]
        if d["second_singular_fraction"] > SVD_MAX_RESIDUAL or d["imaginary_residue"] > IMAG_MAX_RESIDUE:
            raise io.RawDataError(f"{role} block envelope is not a single real function "
                                  f"(singular {d['second_singular_fraction']:.2e}, imaginary {d['imaginary_residue']:.2e})")
    raw_e = np.column_stack([env["e1"], env["e2"]])
    raw_h = np.column_stack([env["hh1"], env["hh2"]])
    Fe, gram_e = lowdin(raw_e, w)
    Fh, gram_h = lowdin(raw_h, w)
    O, Ze, Zh = matrix_elements(Fe, Fh, z, w)

    k, disp, disp_meta = io.read_dispersion(root)
    if not np.allclose(disp[0], energies, atol=1e-9, rtol=0):
        raise io.RawDataError("dispersion k=0 energies disagree with energy_spectrum_k00000")
    cols = {role: [s - 1 for s in roles[role]["states"]] for role in roles}
    branches = {role: disp[:, cols[role]].T for role in roles}  # (2 branches, nk)
    gap, split = {}, {}
    for role in roles:
        others = [c for c in range(disp.shape[1]) if c not in cols[role]]
        gap[role] = float(min(np.min(np.abs(disp[:, others] - disp[:, c][:, None])) for c in cols[role]))
        split[role] = float(np.max(np.abs(branches[role][1] - branches[role][0])))

    checks = {"composition_file_max_abs_difference": comp_err if comp else None,
              "gram_before_lowdin_electron": gram_e.tolist(), "gram_before_lowdin_hole": gram_h.tolist(),
              "orthonormality_error_after_lowdin": float(max(
                  np.abs(Fe.T @ (Fe * w[:, None]) - np.eye(2)).max(),
                  np.abs(Fh.T @ (Fh * w[:, None]) - np.eye(2)).max())),
              "min_member_gap_to_other_columns_eV": gap, "max_doublet_splitting_eV": split}
    dip_path = io.find_optional(root, "dipole_moment_matrix_elements_k00000_growth_z.txt")
    if dip_path:
        dip = io.read_kp8_dipole(dip_path)
        s = {r: tuple(roles[r]["states"]) for r in roles}
        checks["nextnano_dipole_hh1_hh2_nm"] = kramers_invariant(dip, s["hh1"], s["hh2"])
        checks["nextnano_dipole_e1_e2_nm"] = kramers_invariant(dip, s["e1"], s["e2"])
        checks["package_abs_zh12_nm"] = float(abs(Zh[0, 1]))
        checks["package_abs_ze12_nm"] = float(abs(Ze[0, 1]))

    return {"model": "kp8", "k_per_nm": k,
            "electron_eV": np.vstack([branches["e1"].mean(axis=0), branches["e2"].mean(axis=0)]),
            "valence_eV": np.vstack([branches["hh1"].mean(axis=0), branches["hh2"].mean(axis=0)]),
            "electron_branches_eV": np.stack([branches["e1"], branches["e2"]]),
            "valence_branches_eV": np.stack([branches["hh1"], branches["hh2"]]),
            "overlap": O, "ze_nm": Ze, "zh_nm": Zh,
            "matrices_origin_shifted": _as_dict(matrix_elements(Fe, Fh, z + ORIGIN_SHIFT_NM, w), shift_nm=ORIGIN_SHIFT_NM),
            "matrices_pre_lowdin": _as_dict(matrix_elements(raw_e, raw_h, z, w)),
            "matrices_pre_lowdin_origin_shifted": _as_dict(matrix_elements(raw_e, raw_h, z + ORIGIN_SHIFT_NM, w)),
            "block_weights": {r: env_diag[r]["block_weight"] for r in roles},
            "state_ids": {r: roles[r]["states"] for r in roles},
            "doublet_table": table, "envelope_reduction": env_diag,
            "envelope_grid_points": int(len(z)), "dispersion": disp_meta, "checks": checks,
            "limitations": ["M(k)=M(0): kp8 spinors exported at k=0 only",
                            "Energy-sorted dispersion columns (no finite-k spinor tracking); see min member gap",
                            "Spin branches at k != 0 cannot be assigned without finite-k spinors; chi2 is averaged "
                            "over the four lower/upper electron-hole branch pairings (splitting up to "
                            f"{1e3 * max(split.values()):.1f} meV)",
                            "Dominant-block scalar envelopes renormalized to unit norm (Eq. 2 envelope-function factorization)"]}

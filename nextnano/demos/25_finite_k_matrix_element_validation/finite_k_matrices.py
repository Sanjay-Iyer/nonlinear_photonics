"""Finite-k pathway numerators and the Demo 25 Equation 2 recompute.

The Equation 2 engine is NOT reimplemented. ``chi2_22.chi2_from_k_inputs``
already accepts either a constant ``(2,2)`` matrix or a k-dependent
``(2,2,nk)`` one, so Demo 25 supplies k-dependent matrices to exactly the same
validated algebra Demo 23 and Demo 24 used. Nothing else changes: broadening,
Nz, spin degeneracy, radial weighting, the 16 pathways, the sign convention
and the wavelength grid all come from the Demo 23 settings.

The one substantive Demo 25 addition is the pathway numerator ratio

    M_p(k) / M_p(0)

which is the quantity Demo 24 could not test because Demo 23 froze it at 1.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from config25 import DEMO22, DEMO23, DEMO24

# Demo 23 and Demo 24 both ship generically named `plotting.py`/`reporting.py`.
# Demo 24 is APPENDED rather than inserted so that a Demo 23 module importing
# `plotting` in the same interpreter still resolves to its own file; putting
# Demo 24 first silently shadows Demo 23 and breaks its tests.
for module_dir in (DEMO22, DEMO23):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
if str(DEMO24) not in sys.path:
    sys.path.append(str(DEMO24))

import chi2_22  # noqa: E402
import causal_sensitivity as cs  # noqa: E402  - reuse Demo 24's pathway bookkeeping


PATHWAYS = cs.PATHWAYS


@dataclass(frozen=True)
class FiniteKMatrices:
    """O, z_e, z_hh as functions of k, on the Equation 2 index convention."""

    k_per_nm: np.ndarray
    overlap: np.ndarray        # (2, 2, nk) indexed [electron, hole]
    z_e_nm: np.ndarray         # (2, 2, nk)
    z_hh_nm: np.ndarray        # (2, 2, nk)
    electron_purity: np.ndarray | None = None   # (2, nk) CB fraction
    hole_purity: np.ndarray | None = None       # (2, nk) HH fraction

    def at_zero(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.overlap[:, :, 0], self.z_e_nm[:, :, 0], self.z_hh_nm[:, :, 0]


def assemble(tables: Sequence[Mapping[str, Any]], k_per_nm: Sequence[float]) -> FiniteKMatrices:
    """Stack per-k matrix-element tables into (2,2,nk) arrays.

    Each table is a ``kp8_finite_k_io.matrix_element_table`` result restricted
    to the two electron and two hole states Equation 2 uses.
    """
    if len(tables) != len(k_per_nm):
        raise ValueError("one matrix-element table is required per k point")
    nk = len(tables)
    o = np.zeros((2, 2, nk), dtype=complex)
    ze = np.zeros((2, 2, nk), dtype=complex)
    zh = np.zeros((2, 2, nk), dtype=complex)
    ep = np.zeros((2, nk))
    hp = np.zeros((2, nk))
    for index, table in enumerate(tables):
        for array, key in ((o, "O"), (ze, "z_e_nm"), (zh, "z_hh_nm")):
            block = np.asarray(table[key], dtype=complex)
            if block.shape != (2, 2):
                raise ValueError(
                    f"Equation 2 needs a 2x2 {key} block; got {block.shape} at k index {index}")
            array[:, :, index] = block
        ep[:, index] = np.asarray(table["electron_CB_purity"], dtype=float)[:2]
        hp[:, index] = np.asarray(table["hole_HH_purity"], dtype=float)[:2]
    return FiniteKMatrices(np.asarray(k_per_nm, dtype=float), o, ze, zh, ep, hp)


def interpolate_onto(matrices: FiniteKMatrices, k_target: Sequence[float]) -> FiniteKMatrices:
    """Resample M(k) onto a finer energy grid.

    Matrix elements vary slowly with k while the energies set the resonance
    positions, so a coarser matrix grid interpolated onto the fine energy grid
    is far cheaper than solving envelopes at every energy k point. Real and
    imaginary parts are interpolated separately; extrapolation is refused.
    """
    target = np.asarray(k_target, dtype=float)
    source = matrices.k_per_nm
    if target.min() < source.min() - 1e-12 or target.max() > source.max() + 1e-12:
        raise ValueError(
            f"refusing to extrapolate M(k): target k range [{target.min():.4g},{target.max():.4g}] "
            f"exceeds the computed range [{source.min():.4g},{source.max():.4g}]")

    def resample(block: np.ndarray) -> np.ndarray:
        out = np.zeros((*block.shape[:2], len(target)), dtype=complex)
        for i in range(block.shape[0]):
            for j in range(block.shape[1]):
                out[i, j] = (np.interp(target, source, block[i, j].real)
                             + 1j * np.interp(target, source, block[i, j].imag))
        return out

    def resample_real(block: np.ndarray | None) -> np.ndarray | None:
        if block is None:
            return None
        return np.vstack([np.interp(target, source, row) for row in block])

    return FiniteKMatrices(target, resample(matrices.overlap), resample(matrices.z_e_nm),
                           resample(matrices.z_hh_nm), resample_real(matrices.electron_purity),
                           resample_real(matrices.hole_purity))


def pathway_numerators(matrices: FiniteKMatrices) -> np.ndarray:
    """M_p(k) for all 16 pathways, in the production emission order.

    The expressions mirror ``chi2_22.chi2_from_k_inputs`` exactly:
        electron side  C:  +O[n,m] z_e[n,l] O[l,m]
        hole side      V:  -O[n,m] z_hh[m,l] O[n,l]
    """
    o, ze, zh = matrices.overlap, matrices.z_e_nm, matrices.z_hh_nm
    out = np.zeros((len(PATHWAYS), o.shape[2]), dtype=complex)
    for item in PATHWAYS:
        m, n, ell = item.m - 1, item.n - 1, item.ell - 1
        if item.side == "electron_side":
            out[item.index] = o[n, m] * ze[n, ell] * o[ell, m]
        else:
            out[item.index] = -o[n, m] * zh[m, ell] * o[n, ell]
    return out


def numerator_ratios(matrices: FiniteKMatrices, *,
                     flag_fractions: Sequence[float] = (0.05, 0.10)) -> list[dict[str, Any]]:
    """M_p(k)/M_p(0) per pathway, with sign changes and variation flags.

    A pathway whose k=0 numerator is negligible has no meaningful ratio, so it
    is reported as such rather than dividing by something close to zero.
    """
    numerators = pathway_numerators(matrices)
    reference = numerators[:, 0]
    scale = float(np.max(np.abs(reference))) if numerators.size else 0.0
    rows: list[dict[str, Any]] = []
    for item in PATHWAYS:
        values = numerators[item.index]
        base = reference[item.index]
        negligible = abs(base) <= 1e-6 * max(scale, 1e-300)
        ratio = np.full(len(values), np.nan, dtype=complex) if negligible else values / base
        magnitude = np.abs(ratio)
        finite = magnitude[np.isfinite(magnitude)]
        sign_change = bool(not negligible and np.any(np.real(ratio) < 0))
        max_dev = float(np.max(np.abs(finite - 1.0))) if finite.size else float("nan")
        row: dict[str, Any] = {
            "pathway": item.label, "side": item.side,
            "numerator_expression": item.numerator_expression,
            "M_p_at_k0": complex(base).real if abs(complex(base).imag) < 1e-12 else complex(base),
            "abs_M_p_at_k0": float(abs(base)),
            "negligible_at_k0": negligible,
            "max_abs_ratio": float(np.max(finite)) if finite.size else float("nan"),
            "min_abs_ratio": float(np.min(finite)) if finite.size else float("nan"),
            "max_fractional_deviation": max_dev,
            "sign_change_vs_k": sign_change,
            "crosses_zero": bool(not negligible and np.any(np.abs(values) <= 1e-3 * abs(base))),
        }
        for fraction in flag_fractions:
            row[f"varies_more_than_{int(round(100 * fraction))}pct"] = bool(
                np.isfinite(max_dev) and max_dev > float(fraction))
        rows.append(row)
    return rows


def spectrum_with_finite_k(wavelength_nm: np.ndarray, k_per_nm: np.ndarray,
                           electron_energies_eV: np.ndarray, hole_energies_eV: np.ndarray,
                           matrices: FiniteKMatrices, *, settings: Any,
                           broadening_meV: float):
    """Equation 2 with full E(k) and finite-k M(k), through the validated engine."""
    return chi2_22.chi2_from_k_inputs(
        wavelength_nm, k_per_nm, electron_energies_eV, hole_energies_eV,
        matrices.overlap, matrices.z_e_nm, matrices.z_hh_nm,
        broadening_meV=float(broadening_meV), settings=settings)


def spectrum_with_frozen_matrices(wavelength_nm: np.ndarray, k_per_nm: np.ndarray,
                                  electron_energies_eV: np.ndarray, hole_energies_eV: np.ndarray,
                                  matrices: FiniteKMatrices, *, settings: Any,
                                  broadening_meV: float):
    """The M(k)=M(0) control, using the same k=0 matrices Demo 25 measured.

    This is the honest comparison partner: it isolates the effect of finite-k
    M(k) alone, because every other input is identical.
    """
    o0, ze0, zh0 = matrices.at_zero()
    return chi2_22.chi2_from_k_inputs(
        wavelength_nm, k_per_nm, electron_energies_eV, hole_energies_eV,
        o0, ze0, zh0, broadening_meV=float(broadening_meV), settings=settings)


def cancellation_at(wavelength_nm: np.ndarray, spectrum, target_nm: float) -> dict[str, float]:
    """Electron/hole subtotals and cancellation ratio at one wavelength."""
    index = int(np.argmin(np.abs(np.asarray(wavelength_nm) - float(target_nm))))
    values = spectrum.terms[:, index]
    electron = complex(np.sum([v for v, p in zip(values, PATHWAYS) if p.side == "electron_side"]))
    hole = complex(np.sum([v for v, p in zip(values, PATHWAYS) if p.side != "electron_side"]))
    total = complex(spectrum.chi2[index])
    denominator = abs(electron) + abs(hole)
    return {
        "wavelength_nm": float(np.asarray(wavelength_nm)[index]),
        "chi_e_abs": abs(electron), "chi_hh_abs": abs(hole), "total_abs": abs(total),
        "cancellation_ratio": abs(total) / denominator if denominator else float("nan"),
        "phase_difference_deg": float(np.degrees(np.angle(electron) - np.angle(hole)
                                                 + np.pi) % 360.0 - 180.0),
        "coherent_over_incoherent": float(abs(np.sum(values)) / np.sum(np.abs(values))),
    }

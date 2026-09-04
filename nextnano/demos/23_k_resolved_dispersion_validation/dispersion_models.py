"""Four interchangeable subband-dispersion backends for Demo 23."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

import numpy as np
from scipy.interpolate import PchipInterpolator


ELEMENTARY_CHARGE_C = 1.602176634e-19
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
SUBBANDS = ("e1", "e2", "hh1", "hh2")


class SubbandDispersion(Protocol):
    """Backend contract consumed by Equation 2."""

    name: str

    def evaluate(self, k_per_nm: np.ndarray) -> dict[str, np.ndarray]: ...


@dataclass(frozen=True)
class ParabolicFit:
    state: str
    e0_eV: float
    coefficient_eV_nm2: float
    effective_mass_m0: float
    rmse_meV: float
    max_abs_residual_meV: float
    k_at_max_residual_per_nm: float
    fit_kmin_per_nm: float
    fit_kmax_per_nm: float
    point_count: int
    residuals_eV: np.ndarray

    def evaluate(self, k_per_nm: np.ndarray) -> np.ndarray:
        k = np.asarray(k_per_nm, dtype=float)
        return self.e0_eV + self.coefficient_eV_nm2 * k * k

    def as_record(self) -> dict[str, float | int | str]:
        return {
            "state": self.state,
            "E0_eV": self.e0_eV,
            "A_eV_nm2": self.coefficient_eV_nm2,
            "effective_mass_m0": self.effective_mass_m0,
            "RMSE_meV": self.rmse_meV,
            "max_abs_residual_meV": self.max_abs_residual_meV,
            "k_at_max_residual_per_nm": self.k_at_max_residual_per_nm,
            "fit_kmin_per_nm": self.fit_kmin_per_nm,
            "fit_kmax_per_nm": self.fit_kmax_per_nm,
            "point_count": self.point_count,
            "residual_pattern": "systematic" if _systematic(self.residuals_eV) else "not_detected",
        }


def _systematic(residual: np.ndarray) -> bool:
    values = np.asarray(residual, dtype=float)
    if len(values) < 6 or np.allclose(values, 0.0):
        return False
    thirds = np.array_split(values, 3)
    signs = [np.sign(np.mean(part)) for part in thirds]
    return len(set(signs)) > 1 and max(abs(np.mean(part)) for part in thirds) > 0.2 * np.std(values)


def coefficient_to_effective_mass_m0(coefficient_eV_nm2: float) -> float:
    coefficient = float(coefficient_eV_nm2)
    if coefficient == 0.0:
        return float("inf")
    coefficient_joule_m2 = coefficient * ELEMENTARY_CHARGE_C * 1.0e-18
    mass_kg = REDUCED_PLANCK_J_S ** 2 / (2.0 * coefficient_joule_m2)
    return mass_kg / ELECTRON_MASS_KG


def fit_anchored_parabola(
    state: str,
    k_per_nm: np.ndarray,
    energy_eV: np.ndarray,
    *,
    fit_kmax_per_nm: float | None = None,
) -> ParabolicFit:
    """Least-squares fit E(k)=E(0)+A k^2 with E(0) held fixed."""

    k = np.asarray(k_per_nm, dtype=float)
    energy = np.asarray(energy_eV, dtype=float)
    if k.ndim != 1 or energy.shape != k.shape or len(k) < 3 or np.any(np.diff(k) <= 0):
        raise ValueError("fit requires matching, strictly increasing 1D k and energy arrays")
    if abs(k[0]) > 1e-12:
        raise ValueError("anchored parabolic fit requires an explicit k=0 point")
    limit = float(k[-1] if fit_kmax_per_nm is None else fit_kmax_per_nm)
    use = k <= limit + 1e-14
    if np.count_nonzero(use) < 3:
        raise ValueError("parabolic fit range contains fewer than three points")
    x = k[use] ** 2
    y = energy[use] - energy[0]
    denominator = float(np.dot(x, x))
    if denominator == 0:
        raise ValueError("parabolic fit has zero k^2 variation")
    coefficient = float(np.dot(x, y) / denominator)
    fitted = energy[0] + coefficient * k[use] ** 2
    residual = energy[use] - fitted
    imax = int(np.argmax(np.abs(residual)))
    return ParabolicFit(
        state=state,
        e0_eV=float(energy[0]),
        coefficient_eV_nm2=coefficient,
        effective_mass_m0=coefficient_to_effective_mass_m0(coefficient),
        rmse_meV=1000.0 * float(np.sqrt(np.mean(residual ** 2))),
        max_abs_residual_meV=1000.0 * float(abs(residual[imax])),
        k_at_max_residual_per_nm=float(k[use][imax]),
        fit_kmin_per_nm=float(k[use][0]),
        fit_kmax_per_nm=float(k[use][-1]),
        point_count=int(np.count_nonzero(use)),
        residuals_eV=residual,
    )


class _PchipBand:
    def __init__(self, k: np.ndarray, energy: np.ndarray):
        self.k = np.asarray(k, dtype=float)
        self.energy = np.asarray(energy, dtype=float)
        if self.k.ndim != 1 or self.energy.shape != self.k.shape:
            raise ValueError("PCHIP input arrays disagree")
        if len(self.k) < 2 or np.any(np.diff(self.k) <= 0):
            raise ValueError("PCHIP k grid must be strictly increasing")
        self._interpolator = PchipInterpolator(self.k, self.energy, extrapolate=False)

    def __call__(self, k: np.ndarray) -> np.ndarray:
        points = np.asarray(k, dtype=float)
        tolerance = 1e-12 * max(1.0, abs(float(self.k[-1])))
        if np.any(points < self.k[0] - tolerance) or np.any(points > self.k[-1] + tolerance):
            raise ValueError(
                f"refusing dispersion extrapolation beyond [{self.k[0]:.9g}, {self.k[-1]:.9g}] nm^-1"
            )
        clipped = np.clip(points, self.k[0], self.k[-1])
        values = np.asarray(self._interpolator(clipped), dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("non-finite PCHIP interpolation result")
        return values


@dataclass(frozen=True)
class BaselineSharedParabola:
    name: str
    electron_k0_eV: np.ndarray
    heavy_hole_k0_eV: np.ndarray
    reduced_mass_kg: float

    def evaluate(self, k_per_nm: np.ndarray) -> dict[str, np.ndarray]:
        k = np.asarray(k_per_nm, dtype=float)
        kinetic_eV = (
            REDUCED_PLANCK_J_S ** 2 * (k * 1.0e9) ** 2
            / (2.0 * float(self.reduced_mass_kg) * ELEMENTARY_CHARGE_C)
        )
        return {
            "e1": float(self.electron_k0_eV[0]) + kinetic_eV,
            "e2": float(self.electron_k0_eV[1]) + kinetic_eV,
            "hh1": np.full_like(k, float(self.heavy_hole_k0_eV[0])),
            "hh2": np.full_like(k, float(self.heavy_hole_k0_eV[1])),
        }


@dataclass(frozen=True)
class SeparateParabolic:
    name: str
    fits: Mapping[str, ParabolicFit]

    def evaluate(self, k_per_nm: np.ndarray) -> dict[str, np.ndarray]:
        return {state: self.fits[state].evaluate(k_per_nm) for state in SUBBANDS}


class BossHybrid:
    name = "23C"

    def __init__(self, fits: Mapping[str, ParabolicFit], raw_k: np.ndarray,
                 raw_energies: Mapping[str, np.ndarray]):
        self._fits = fits
        self._hh = {state: _PchipBand(raw_k, raw_energies[state]) for state in ("hh1", "hh2")}

    def evaluate(self, k_per_nm: np.ndarray) -> dict[str, np.ndarray]:
        return {
            "e1": self._fits["e1"].evaluate(k_per_nm),
            "e2": self._fits["e2"].evaluate(k_per_nm),
            "hh1": self._hh["hh1"](k_per_nm),
            "hh2": self._hh["hh2"](k_per_nm),
        }


class RawKp8:
    name = "23D"

    def __init__(self, raw_k: np.ndarray, raw_energies: Mapping[str, np.ndarray]):
        self._bands = {state: _PchipBand(raw_k, raw_energies[state]) for state in SUBBANDS}

    def evaluate(self, k_per_nm: np.ndarray) -> dict[str, np.ndarray]:
        return {state: self._bands[state](k_per_nm) for state in SUBBANDS}


def build_models(
    *,
    raw_k_per_nm: np.ndarray,
    raw_energies_eV: Mapping[str, np.ndarray],
    electron_k0_eV: np.ndarray,
    heavy_hole_k0_eV: np.ndarray,
    reduced_mass_kg: float,
) -> tuple[dict[str, SubbandDispersion], dict[str, ParabolicFit]]:
    fits = {
        state: fit_anchored_parabola(state, raw_k_per_nm, raw_energies_eV[state])
        for state in SUBBANDS
    }
    models: dict[str, SubbandDispersion] = {
        "23A": BaselineSharedParabola(
            "23A", np.asarray(electron_k0_eV), np.asarray(heavy_hole_k0_eV), reduced_mass_kg
        ),
        "23B": SeparateParabolic("23B", fits),
        "23C": BossHybrid(fits, raw_k_per_nm, raw_energies_eV),
        "23D": RawKp8(raw_k_per_nm, raw_energies_eV),
    }
    return models, fits


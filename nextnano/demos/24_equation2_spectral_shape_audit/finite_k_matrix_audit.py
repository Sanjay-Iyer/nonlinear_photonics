"""Evidence-only inventory for finite-k matrix data; never synthesizes missing data."""

from __future__ import annotations

from pathlib import Path


class ProfessionalDataRequired(RuntimeError):
    pass


def inventory(raw_case: Path) -> list[dict[str, object]]:
    def matches(pattern: str) -> list[Path]:
        return sorted(raw_case.rglob(pattern))
    dispersions = matches("dispersion_*.dat")
    k0_envelopes = matches("envelope_k00000_*.dat")
    finite_envelopes = [p for p in matches("envelope_k*.dat") if "k00000" not in p.name]
    spinor_k0 = matches("spinor_composition_k00000_CbHhLhSo.dat")
    finite_spinor = [p for p in matches("spinor_composition_k*.dat") if "k00000" not in p.name]
    direct_matrix = matches("*matrix*.dat") + matches("*dipole*.dat") + matches("*momentum*.dat")
    def row(quantity: str, needed: bool, files: list[Path], direct: bool, conversion: str, missing: bool) -> dict[str, object]:
        return {
            "Quantity": quantity, "Needed for Equation 2?": needed,
            "Available in copied Demo 23 raw output?": bool(files),
            "Exact file/path": "; ".join(str(p) for p in files[:4]) + ("; ..." if len(files) > 4 else ""),
            "Can be used directly?": direct, "Needs conversion?": conversion, "Missing?": missing,
        }
    return [
        row("tracked transition energies E(k)", True, dispersions, True, "no", not dispersions),
        row("k=0 envelope components", True, k0_envelopes, False, "integration and state pairing", not k0_envelopes),
        row("finite-k envelope components", True, finite_envelopes, False, "integration and state pairing", not finite_envelopes),
        row("k=0 Cb/HH/LH/SO composition", False, spinor_k0, True, "pair averaging", not spinor_k0),
        row("finite-k Cb/HH/LH/SO composition", False, finite_spinor, True, "pair averaging", not finite_spinor),
        row("finite-k overlap O_nm(k)", True, direct_matrix, False, "quantity-specific parser", not direct_matrix),
        row("finite-k electron z matrix z_e(k)", True, direct_matrix, False, "quantity-specific parser", not direct_matrix),
        row("finite-k heavy-hole z matrix z_hh(k)", True, direct_matrix, False, "quantity-specific parser", not direct_matrix),
    ]


def require_finite_k_matrices(rows: list[dict[str, object]]) -> None:
    missing = [r["Quantity"] for r in rows if r["Needed for Equation 2?"] and r["Missing?"]]
    if missing:
        raise ProfessionalDataRequired("REQUIRES_NEW_PROFESSIONAL_DATA: " + ", ".join(map(str, missing)))

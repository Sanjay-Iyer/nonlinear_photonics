"""Literal 16-pathway reference for the paper's two-state chi(2) equation.

The assignments are intentionally explicit so an ordering/sign error can be
located at the first named term.  Inputs are a single wavelength and the
already-constructed transition cube and radial weights.
"""

from __future__ import annotations

import numpy as np


def literal_terms(hw, gamma, transitions, weights, overlap, z_e, z_h, prefactor):
    def C(m, n, ell):
        d2 = transitions[n, m] - 2.0 * hw + 1j * gamma
        d1 = transitions[ell, m] - hw + 1j * gamma
        numerator = overlap[n, m] * z_e[n, ell] * overlap[ell, m]
        return prefactor * np.dot(weights, numerator / (d2 * d1))

    def V(m, n, ell):
        d2 = transitions[n, m] - 2.0 * hw + 1j * gamma
        d1 = transitions[n, ell] - hw + 1j * gamma
        numerator = -overlap[n, m] * z_h[m, ell] * overlap[n, ell]
        return prefactor * np.dot(weights, numerator / (d2 * d1))

    term01 = C(0, 0, 0)
    term02 = C(0, 0, 1)
    term03 = V(0, 0, 0)
    term04 = V(0, 0, 1)
    term05 = C(0, 1, 0)
    term06 = C(0, 1, 1)
    term07 = V(0, 1, 0)
    term08 = V(0, 1, 1)
    term09 = C(1, 0, 0)
    term10 = C(1, 0, 1)
    term11 = V(1, 0, 0)
    term12 = V(1, 0, 1)
    term13 = C(1, 1, 0)
    term14 = C(1, 1, 1)
    term15 = V(1, 1, 0)
    term16 = V(1, 1, 1)
    terms = [term01, term02, term03, term04, term05, term06, term07, term08,
             term09, term10, term11, term12, term13, term14, term15, term16]
    chi_reference = sum(terms)
    return np.asarray(terms, dtype=complex), chi_reference


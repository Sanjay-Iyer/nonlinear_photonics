"""Render the smallest defensible Professional rerun recommendation."""

from __future__ import annotations


def recommendation() -> str:
    return """# Professional rerun recommendation

## B. TARGETED PRO RUN RECOMMENDED

The existing solver output is sufficient to establish the Demo 23D energy-only spectrum, to
*exclude* several hypotheses outright, and to localise the failure. It is not sufficient to test
the one remaining hypothesis that could produce the missing structure, because it contains no
finite-k wavefunctions, spinor composition, overlaps, or z matrices. A full campaign is not
justified.

## What Demo 24N changed about this recommendation

The causal sensitivity study narrowed the question in three ways, and the deck below reflects
all three.

- **The paper's P1/P3 pair is out of reach of the current model space.** P1 (540 nm) and P3
  (1080 nm) are an exact one-photon/two-photon pair of a single 2.296 eV transition. The largest
  transition energy any pair of bound subbands in this structure attains - extrapolated to the k
  where the electron reaches the 2.145 eV Al0.55Ga0.45As barrier edge and stops being confined -
  is 1.966 eV. So the run must retain enough states, and enough energy range, to reveal whatever
  carries oscillator strength near 2.3 eV, rather than assuming the four-state truncation.
- **Extending kmax alone is not a fix.** The model peak near 1318 nm marches 1502 -> 1431 ->
  1376 -> 1318 nm as kmax goes 0.05 -> 0.125 pi/a and matches 2hc/DeltaE(kmax) to a 9 nm mean
  error: it is the edge of a truncated k sum, not a resonance. With a frozen numerator the
  integrand never decays, so a longer k range would relocate the artifact instead of removing it.
  Finite-k M(k) is what supplies the high-k damping.
- **The missing nodes are within reach of a few-percent numerator change.** Electron and signed
  heavy-hole subtotals are antiphase to within 0.1 degree and cancel to 4.3% (605 nm) and 4.9%
  (1330 nm), a 21-24x amplification. Scaling one dominant pathway numerator by 0.90 opens genuine
  complex nodes at 573 nm (normalized 0.0001) and 1282 nm (0.0018). That is exactly the size of
  effect a real finite-k M(k) would introduce, which makes it the highest-value measurement.

1. **Scientific question:** Does finite-k envelope mixing and matrix-element amplitude variation
   (a) open the deep minima near 605 and 1330 nm, and (b) damp the high-k tail enough to remove
   the truncation edge - and does any transition in this structure reach 2.296 eV?
2. **Missing quantity:** `O_nm(k)`, `z_e,nl(k)`, and `z_hh,ml(k)` (or equivalent complex
   dipole/momentum data) for e1/e2/hh1/hh2, with enough character data to track each Kramers
   pair, plus the energies and oscillator strengths of the states above the current four.
3. **Required output:** energies, explicit k vectors, complex envelope/spinor coefficients or
   directly exported complex matrix elements at every k point, CB/HH/LH/SO fractions per state
   per k, state identities/tracking diagnostics, and solver metadata. Demo 23 requested
   `all_k_state_output` but received only `k00000` state and matrix files, so validate the output
   syntax on a small pilot grid before launching the production job.
4. **Structure:** first run the exact ideal abrupt Fig. 2d structure: GaAs wells 7.1 and 2.9 nm,
   Al0.55Ga0.45As 1.8 nm tunnel barrier, 18.2 nm period barrier, 30 nm total period, 300 K,
   growth direction [100]. Keep the current 1-nm-linear structure as a second deck if time
   permits, so geometry and M(k) effects stay separable.
5. **k path/grid:** Gamma to 0.20 pi/a along [010], 301 points minimum. The extent is set by
   Demo 24N: 0.125 pi/a still leaves the integrand peaking at the cutoff, and the resonance that
   the paper's Z2 needs sits at about 0.116 pi/a, so the grid must comfortably pass it. Include
   the [011]-type 45-degree path only as an optional second-direction diagnostic.
6. **Minimum decks:** one production deck for the ideal abrupt geometry; two decks if the current
   graded structure is included as the controlled comparison.
7. **Does 1D radial data suffice?** Yes for this first test, provided an isotropy check shows the
   matrix elements and energies are acceptably isotropic. The decisive quantities here - band
   edges, node depth, and the high-k tail - are all radial.
8. **Is full 2D k necessary?** Not for the first targeted run. It becomes necessary only if
   direction-dependent spectra remain material after M(k) is included.
9. **Expected runtime:** approximately one 301-point Demo 23 production deck per geometry, plus
   matrix-output overhead and the longer k range; still far smaller than a seven-deck campaign.
10. **Copy back:** complete raw output, exact input deck, solver stdout/stderr, resolved
    database/material version, all per-k energies/vectors, all per-k spinor/envelope or matrix
    files, `bandedges.dat`, and `job_done.txt`.

## What would make this a category C

If the returned finite-k matrices leave P1/P3 unexplained *and* no state in the extended solve
carries oscillator strength near 2.296 eV, then the compared curve is not this structure and the
question becomes a geometry search rather than a numerator correction. Only then is a broader
campaign warranted.

No Professional executable is invoked by Demo 24 on this laptop.
"""

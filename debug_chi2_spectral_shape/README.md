# χ² spectral-shape debugging study

This directory is a controlled, solver-free investigation of why the calculated
χ² spectrum does not reproduce the nodes and resonance shape digitized from the
paper.

## Fixed provenance

- Structure/state source: cached licensed Demo 21 Case 04 (`Linear 1.0 nm`).
- Energies: `docs/demo21/trace_linear_1nm/05_subband_energies.csv`.
- Matrix elements: `docs/demo21/trace_linear_1nm/07_matrix_elements.csv`.
- Trusted parabolic evaluator: Demo 20/21 production `s06_chi2.py`, imported
  read-only.
- Hybrid evaluator: the polynomial dispersions from
  `docs/8_band_non_parabolic_v2.py`, applied to the same Demo 21 states and the
  same Eq. 2 normalization.
- Paper comparison: the digitized points already embedded in the hybrid script.
- Wavelength grid: 400–1850 nm in 1 nm increments.

The runner fails if the cached licensed inputs are missing. It contains no
synthetic-wavefunction fallback and never invokes nextnano++.

## Status

| Experiment | Status | Main finding |
|---|---|---|
| `00_baseline` | complete | Neither calculated magnitude reproduces the paper's two zeros. |
| `01_complex_components` | complete | Hybrid Re(χ²) crosses zero, but Im(χ²) fills both magnitude nodes. |
| `02_abs_order` onward | not yet executed | Run only as later controlled phases. |

Run the completed phase with:

```powershell
python debug_chi2_spectral_shape/run_phase1.py
```

`MASTER_DEBUG_SUMMARY.csv` is the machine-readable experiment index.


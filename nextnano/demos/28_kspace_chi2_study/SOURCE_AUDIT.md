# Source and runtime audit

Historical directories were read as source/reference material, not edited for this work. Existing unrelated working-tree changes were preserved.

| Source inspected | Finding | Demo 28 decision |
|---|---|---|
| `26_real_chi2_paper_comparison/run_demo26_real.py` | Loads historical 23D complex spectrum; mainly a comparison/plot layer | Keep numerical CSV as a local regression fixture, not a runtime dependency |
| Demo 26 `extended_implementation_audit.py::independent_eq2` | Independent complex-conjugation/sign audit | Preserve the audited product conventions and phase-invariance test |
| `Demo26_Condensed/src/equation2.py` | Self-contained 16-pathway complex discrete engine, explicit units/prefactor | Consolidate in one `chi2/equation2.py`; both wavelength and signed-energy audit entry points share its loop |
| Condensed `raw_inputs.py` and `nextnano_io.py` | Historical mixed-model reconstruction and raw fixed-width parsing | Local parser and explicit input builder; no imports from Condensed |
| Condensed cached Professional kp8 and Case04 single-band data | True raw energies/envelopes and saved decks | Copy intact as package-local raw inputs, hash each file |
| Condensed newer kp8/matrix alternatives | Change state selection and matrix physics | Do not silently substitute into historical 28A/B |
| Demo 26 cutoff diagnostic | Parabolic extrapolation, enlarged cutoff, different frozen-matrix source; early raw diagnostic did not apply absolute prefactor | Historical explanation only, not the authoritative native-data baseline |
| Earlier raw independent grids / extended run | Genuine solver output, not fitted parabolas | Copy separately with provenance; labeled 28H/28C diagnostics |

## Preserved conventions and limitations

- Two electron and two valence levels, 8 electron-intermediate plus 8 valence-intermediate terms.
- Gamma = 5 meV, plus-iGamma convention; 400–1850 nm fundamental wavelength, 1 nm step.
- Baseline selected one-based solver pairs: e1=[11,12], e2=[13,14], h1=[5,6], h2=[3,4]. Last pair is LH-dominated despite historical HH naming.
- Pair-average E(k)-E(0) shifts are added to single-band anchors. Matrices remain at k=0.
- Spin degeneracy 2; isotropic radial measure g_s k dk/(2pi); Nz=1/(30 nm); r=0.751 nm; prefactor retains 1/6.
- r is a fixed published HSE06/VASP result (7.51 angstrom in the 2023 reference), not a DFT calculation performed here. See `PAPER_AUDIT.md`.
- Paper's Schrödinger–Poisson description is not identical to this quantum-only 8-band dispersion plus single-band-matrix construction. The decks do not solve Poisson or propagate photoexcited populations.

The parser, runner and deck generator were retained because they represent separate workflow stages. Duplicated historical Eq2 engines, legacy imports, analytic extrapolation alternatives and old ad-hoc plotting scripts were not copied into production.

## Numerical continuity versus scientific validity

28A compares every complex wavelength sample against the **local** reference CSV. Max difference is 6.9711344e-10 pm/V, below 1e-8. This is a regression test, not a validation against experiment or a proof that the state truncation is physically adequate.

The tests also preserve numerator gauge invariance, complex signs, units, endpoint weights and pathway summation. `outputs/dependency_audit/metadata.json` records isolated execution with historical data/code directories blocked. Production imports are local modules and NumPy/SciPy/Matplotlib; pytest is test-only. Regression/reference fixtures remain explicitly historical.

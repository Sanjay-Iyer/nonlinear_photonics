# Demo 23 paper-comparison provenance

`paper_figure2d_digitized_simulation.csv` is the repository's existing
45-point **eye digitization** of the dashed simulated susceptibility curve in
Ramesh et al., *Enhanced Interband Optical Nonlinearities from Coupled Quantum
Wells*, Fig. 2d. The values were previously embedded as `PAPER_DIGITIZED` in
`docs/demo21/compare_demo21_hybrid_spectra.py`; this CSV is a direct,
unchanged transcription so Demo 23 can load it without importing unrelated
plotting code.

The curve is labeled **"Digitized from Ramesh et al. Fig. 2d"** everywhere.
It is not raw or tabulated author data. Linear interpolation is used only on
the overlap of the digitized and Demo 23 wavelength ranges. Errors inherit
unquantified visual-reading and interpolation uncertainty and are diagnostic,
not an exact validation gate.

The following separate reference values come directly from the paper text:

- simulated resonance near 1520 nm fundamental wavelength;
- measured resonance near 1560 nm fundamental wavelength;
- ideal abrupt-interface simulated susceptibility about 2340 pm/V at 1550 nm
  in the growth-interruption discussion.

Measured SHG intensity is not placed on a susceptibility axis. Demo 23's
linear-1-nm geometry is also not claimed to be identical to the ideal-abrupt
2340-pm/V reference.

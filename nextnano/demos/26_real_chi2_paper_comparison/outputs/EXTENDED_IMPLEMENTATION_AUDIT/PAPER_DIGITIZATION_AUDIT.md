# Paper digitization audit

- 45 points are strictly wavelength ordered: **True**.
- x spans 400-1850 nm and y is nonnegative: **True**.
- The columns are explicitly `wavelength_nm` and `digitized_simulated_chi2_pm_per_V`; no swap is present.
- Points 605 and 1330 nm are stored as zero, consistent with the nonnegative simulated magnitude trace.
- Linear interpolation is only used to form a common comparison grid; metrics use the unchanged 45-point eye digitization as the source.
- The source is Figure 2d's simulated curve, not the experimental points. This remains an eye digitization and is not author-supplied numerical data.

`plots/paper_digitization_overlay.png` overlays all 45 points on the rendered Figure 2d panel; registration is approximate because the trace was eye-digitized.

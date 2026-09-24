# Fig. 2d digitization (30A)

`scripts/digitize_fig2d_measured.py` regenerates everything here. It takes no manual input.

## Source

- **Raster.** The embedded Fig. 2d image of arXiv:2602.23246v1: page 7, `Im1.png`,
  4441 × 1122 px. It is extracted from the PDF with `pypdf`. The SHA-256
  `865de452…` is checked on every run.
- **Resolution.** This raster is about 6× finer than the page renders used by earlier demos:
  - 2.574 px per nm on the wavelength axis;
  - 3.473 px per unit on the SH-intensity axis (0–200 scale).

## Method

1. **Axes.**
   - The plot frame is found as the two long dark rows and the two long dark columns.
   - All tick marks along the bottom, right and left spines are detected automatically.
   - The only human-read facts are the printed tick labels:
     - x: ticks every 50 nm, with 400 nm on the left spine;
     - SH axis: long ticks are 0, 50, …, 200, with short ticks between;
     - χ(2) axis: 0.00 is on the bottom spine, and long ticks are 1000 … 4000 pm/V.
   - Linear fits give maximum tick residuals of 0.48 px (x), 0.44 px (SH) and 0.00 px (χ(2)).
2. **Markers.** Each series is picked out by its legend fill color:
   - 80 pd sample: (247, 66, 66);
   - AlGaAs control: (206, 156, 0);
   - GaAs control: (24, 107, 222).

   Points inside the legend box are ignored.
   - **Wavelengths.** The 11 red markers are complete, isolated 27 × 27 px squares. Their
     centres define the measured wavelengths.
   - **Control values.** Each control value is read in a narrow central column band at
     those wavelengths. A marker row must be ≥ 80% filled, which rejects the thin
     connecting lines.
   - **Partly covered markers.** Two control markers are partly covered by a marker drawn
     on top: AlGaAs at 1400 nm (covered by red) and GaAs at 1800 nm (covered by gold). Their
     centres are taken from the visible edge plus the known marker size (`hidden_edge` column).
3. **Wavelength grid.** Every digitized wavelength lies within 0.18 nm of a multiple of
   10 nm. The column `nominal_wavelength_nm` holds that multiple, and the analysis uses it:
   1400, 1500, 1530, 1540, 1550, 1560, 1570, 1580, 1600, 1700 and 1800 nm.
4. **Simulated curve.** As an extra check, the dashed "Simulation" line (gray level 82)
   is traced column by column. The result is `paper_fig2d_simulated_traced.csv`: 2669
   columns, with no points in dash gaps or under markers.

## Uncertainty

| Quantity | Estimate |
|---|---|
| Wavelength of a marker | ±0.3 nm (tick fit 0.2 nm plus centring 0.2 nm) |
| SH value of a complete marker | ±0.3 arb. u. (±0.15% of the 0–200 scale) |
| SH value of the two partly hidden control markers | ±0.5 arb. u. |
| Simulated trace | about ±1 nm and about ±10 pm/V where the dashes are present |

The paper gives no experimental error bars, so the digitization error is negligible
next to any plausible measurement error.

**The older 45-point eye digitization is less accurate.** That is the Demo 26/28 file
`paper_fig2d_simulated.csv`. Compared with the trace at 34 of its 45 wavelengths, it
deviates by 92 pm/V RMS, with a maximum of 304 pm/V at 1580 nm, on a steep flank. Demo 30
keeps the eye file for **comparison A**, so the Demo 28J numbers can be reproduced
exactly. The trace is used where precision matters: the paper-simulation peak
wavelengths.

Traced paper-simulation features:

- peaks at 538.7, 760.2, 1079.5 and **1519.8 nm**;
- near-zero minima at 613.3 and 1329.8 nm.

## What the measured values mean

The right axis of Fig. 2d is **"Normalized SH Intensity (arb. u.)"**, measured on the
**80-period** sample. It is an SH intensity, not χ(2). The paper does not say how it was
normalized (for example by the fundamental power squared). So only its wavelength
dependence and relative values are used, never its absolute scale.

The two control series (GaAs and AlGaAs) are digitized for context only.

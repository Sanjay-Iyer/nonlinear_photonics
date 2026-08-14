# Demo 19 — Interface Grading Showcase

## What was changed

The same 7.1 / 1.8 / 2.9 nm coupled-QW structure was used in every case. Only interface grading was varied.

## How grading was specified

The Al fraction x_Al changes from 0 to 0.55 across a controlled full transition width centered on each nominal interface. A 0.7 nm linear grade ramps between GaAs and Al0.55Ga0.45As over exactly 0.7 nm.

## What Nextnano calculated

Band edges, wavefunctions, electron and heavy-hole energy levels, overlaps, dipoles and centroids.

## What Python calculated afterward

The 1400–1800 nm χ² spectrum, |χ²| at 1550 nm, peak wavelength, and normalized comparisons with abrupt.

## Key results

- The 13 requested grading definitions and all four named interfaces passed solver-free realization checks.
- No requested grading intervals overlap.
- Licensed band-structure and susceptibility results are pending; no synthetic physics is substituted.

## Main takeaway

The controlled input workflow is ready. Quantitative conclusions require the 13 licensed solves.

# Demo 23 plotting/reporting audit

This audit was completed before the reporting expansion. “Changed” means the
existing calculation was retained and its presentation was extended; no
Equation 2 physics was altered.

| Plot / table | Previously implemented? | File / function | Data source | Change made? |
|---|---|---|---|---|
| Fig. 1 raw kp8 dispersions | Yes | `plotting.raw_dispersions` | tracked Professional kp8 states | Yes: point markers, k=0/kmax/range, electron and hole zooms |
| Figs. 2–5 parabolic fits/residuals | Yes | `fit_plot`, `residual_plot` | tracked points + anchored fits | Yes: fit annotations, extrema, optional curvature diagnostic |
| Figs. 6–7 transition energies | Yes | transition plotters | A–D same-k transitions | Yes: 1550-nm two-photon resonance marker |
| Fig. 8 full A–D spectrum | Yes | `spectra` | validated 16-pathway Equation 2 | Yes: 1550, peak, FWHM annotations |
| Fig. 9 difference from 23D | Yes | `differences` | A–D spectra | Yes: absolute + relative panels, extrema, 1% gate |
| Fig. 10 k-integrand | Partial | `k_integrand` | retained complex summed integrand | Yes: real, imaginary, magnitude |
| Fig. 11 cumulative k contribution | No | `cumulative_k` | retained complex integrand and production weights | Added |
| Fig. 12 pathway decomposition | Table summary only | `pathway_contributions` | 16 complex pathway spectra | Added at 1550 and each mode peak |
| Fig. 13 pathway change A–D | No | `major_pathway_changes` | largest integrated pathways | Added |
| Figs. 14–15 convergence | Minimal plots | `convergence` | configured grid/cutoff decks | Changed: χ1550, peak, peak λ, PASS/FAIL |
| Fig. 16 isotropy | Yes | `isotropy` | matched y and yz45 kp8 paths | Changed: tolerance and PASS/FAIL |
| P1–P5 paper comparison | No | paper plotters + `paper_comparison.py` | 45-point eye digitization and paper-reported points | Added with explicit provenance |
| Master mode table | Partial | `mode_summary.csv` | A–D spectra | Added consolidated CSV with FWHM and paper errors |
| Validation table | No | `demo23_validation_table.csv` | regression/tracking/fits/convergence/isotropy audits | Added |
| 21-section final report | Partial | `reporting.write_final_report` | all preceding tables | Expanded |

The paper curve is labeled “Digitized from Ramesh et al. Fig. 2d” and is never
represented as raw or tabulated author data.

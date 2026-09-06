# Demo 26_real - signed Re[chi2] paper comparison

This analysis-only demo tests whether the digitized Ramesh et al. Figure 2d
simulation agrees better with signed `Re[chi^(2)]` than with `|chi^(2)|`.

It does not invoke nextnano++ Professional and does not alter Demo 23 or Demo
24. The shortest reproducible route is used: the existing Demo 23D complex
spectrum exported by Demo 23 is read from the Demo 24 reanalysis products. The
real, imaginary, and magnitude columns in that file are the same complex
Equation-2 result on the same 1-nm wavelength grid.

Run from the repository root:

```powershell
python nextnano/demos/26_real_chi2_paper_comparison/run_demo26_real.py
```

Results are written to `outputs/`, with the primary plot at
`outputs/plots/figure01_paper_vs_signed_real_vs_magnitude.png`.


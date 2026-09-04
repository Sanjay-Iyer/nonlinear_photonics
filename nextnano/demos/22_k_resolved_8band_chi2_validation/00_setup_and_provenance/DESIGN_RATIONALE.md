# Demo 22 design rationale

## Primary geometry

The primary run is ideal-abrupt because the repository's paper record describes
the quoted 2340 pm/V result as the paper's **simulated ideal-abrupt-interface**
χ² (`demos/11.../demo.yaml`), while the independent physics-source audit states
that the listed 18.2/7.1/1.8/2.9 nm period totals 30.0 nm. The 9.1 nm of outer
barrier on each side merely centers that period.

The 1 nm linearly graded Case 04 structure remains a secondary control because
it is the geometry used by Demo 21's cached licensed scalar states. Running it
separately tests geometry sensitivity without mixing its matrices or energies
into the abrupt paper comparison.

## Observable

The paper-target metadata identifies Fig. 2d's left axis as simulated
`|chi(2)|`. Therefore `|chi2|` remains the primary claimed paper observable.
`Re(chi2)`, `Im(chi2)`, and `|Re(chi2)|` are retained as independently scored
diagnostics because the home-laptop study found much better shape agreement for
`|Re(chi2)|`; that numerical resemblance alone is not authority to relabel the
paper.

## k grids

The explicit dispersion path requests 301 points from Gamma to 1.2 nm^-1 for
visual state tracking. The separate kp8 integration uses 48/72/96 points at
0.10 reciprocal-cell relative size. The upper point count is 96 because the
nextnano++ 3.0.0 grammar restricts `k_integration/num_points` to 2–100. The
final integration cutoff must be reduced if actual state tracking, neighboring
states, or localization show that the two-state description fails earlier; it
must not be selected by paper RMSE.

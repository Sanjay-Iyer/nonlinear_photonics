# 27E preflight

**Schroedinger versus self-consistent Schroedinger-Poisson**

Question: Does self-consistent electrostatics materially change the QW states or the chi2 spectrum?

Pass condition: Both arms converge (a quantum_poisson run that exits DONE without converging is a FAIL, not a result - the evidence is the convergence warning in summary.log and the residuals in iteration_quantum_poisson.dat, both of which are checked), and the Hartree potential, charge density, band edges, state energies, localization and matrix elements are compared arm to arm. PASS means the size of the electrostatic effect is quantified, whatever that size is.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| A_flat_band_control.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | none | 0 |
| B_self_consistent.in | kp8 | dispersion | 301 | 0.555714 | 14 | quantum_poisson | linear_graded | electrostatics | 6 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| A_flat_band_control.in | True | parsed |
| B_self_consistent.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27E cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 3 |
| nextnano++ Professional required | yes |
| Decks | 2 |
| k points per deck | [301, 301] |
| Total k-point solves | 602 |
| States solved/output per deck | [14, 14] |
| Estimated wall time | 2 h - 8 h |
| Estimated output volume | 0.6 - 2 GB |

**Basis for the estimate.** The flat-band arm costs one Demo 23 production run (10 min 20 s measured). The self-consistent arm repeats the quantum solve once per Poisson iteration, so it is the iteration count times that, and Demo 6 needed tens of iterations on a much smaller problem. 2-8 h is the honest range; the run is capped by --timeout and by the iteration limit in the deck.

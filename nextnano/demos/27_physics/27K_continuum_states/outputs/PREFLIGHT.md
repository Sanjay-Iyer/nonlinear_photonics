# 27K preflight

**Continuum and quasi-bound state contributions**

Question: Do physically meaningful continuum or quasi-bound states contribute to the high-energy features?

Pass condition: Every state above the Al0.55Ga0.45As barrier edge is classified by evidence, not by index: confinement fraction inside the wells, sensitivity to the domain size and to the boundary condition, and oscillator strength to the states Equation 2 uses. PASS means each such state is labelled REAL QUASI-BOUND (its energy and localization survive the domain change) or DIRICHLET BOX STATE (it moves with the walls). A box state may not be entered into Equation 2 under any circumstances, and 27K produces no chi2 contribution from unlabelled states.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| continuum_pad2_outer18.in | kp8 | dispersion | 301 | 0.555714 | 64 | flat_band | linear_graded | num_electrons;num_holes;output_state_count | 0 |
| continuum_pad8_outer18.in | kp8 | dispersion | 301 | 0.555714 | 64 | flat_band | linear_graded | num_electrons;num_holes;output_state_count;quantum_region_padding_nm | 0 |
| continuum_pad2_outer34.in | kp8 | dispersion | 301 | 0.555714 | 64 | flat_band | linear_graded | num_electrons;num_holes;output_state_count;period_barrier_nm | 24 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| continuum_pad2_outer18.in | True | parsed |
| continuum_pad8_outer18.in | True | parsed |
| continuum_pad2_outer34.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27K cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 3 |
| nextnano++ Professional required | yes |
| Decks | 3 |
| k points per deck | [301, 301, 301] |
| Total k-point solves | 903 |
| States solved/output per deck | [64, 64, 64] |
| Estimated wall time | 4 h - 12 h |
| Estimated output volume | 3 - 9 GB |

**Basis for the estimate.** 64 states is more than four times the Demo 23 production count of 14, and the eigenvalue cost grows faster than linearly in the state count, so each deck is taken as 1-3 h against the measured 10 min 20 s baseline. Three decks are needed because a continuum claim is only meaningful if the domain is varied underneath it - one deck could not distinguish a resonance from a box level.

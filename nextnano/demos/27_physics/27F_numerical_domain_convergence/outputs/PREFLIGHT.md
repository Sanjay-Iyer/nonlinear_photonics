# 27F preflight

**Numerical domain and boundary convergence**

Question: Could numerical-domain choices be creating or moving the higher states?

Pass condition: Every state energy is reported against each numerical knob, and each state is labelled converged or not-converged under an explicit tolerance. A physical state must not depend strongly on the outer boundary; any state that moves with the padding, the outer barrier width or the boundary condition is recorded as a numerical artifact of the Dirichlet box, not as physics. PASS is reached when every state carries that label.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| mesh_fine_0p025nm.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | active_spacing_nm | 8 |
| mesh_coarse_0p100nm.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | active_spacing_nm | 8 |
| padding_4nm.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | quantum_region_padding_nm | 0 |
| padding_8nm.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | quantum_region_padding_nm | 0 |
| outer_barrier_28p2nm.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | period_barrier_nm | 24 |
| states_24.in | kp8 | dispersion | 301 | 0.555714 | 24 | flat_band | linear_graded | num_electrons;num_holes;output_state_count | 0 |
| boundary_neumann.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | boundary | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| mesh_fine_0p025nm.in | True | parsed |
| mesh_coarse_0p100nm.in | True | parsed |
| padding_4nm.in | True | parsed |
| padding_8nm.in | True | parsed |
| outer_barrier_28p2nm.in | True | parsed |
| states_24.in | True | parsed |
| boundary_neumann.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27F cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 7 |
| k points per deck | [301, 301, 301, 301, 301, 301, 301] |
| Total k-point solves | 2107 |
| States solved/output per deck | [14, 14, 14, 14, 14, 24, 14] |
| Estimated wall time | 2.5 h - 6 h |
| Estimated output volume | 1.5 - 4 GB |

**Basis for the estimate.** Seven decks at roughly the Demo 23 production cost (10 min 20 s each), except the 0.025 nm mesh, which doubles the grid and therefore costs several times more. The 0.05 nm / 2 nm-padding / 18.2 nm-outer-barrier / Dirichlet control is NOT rerun: demo_results/demo23/raw/production_y_n301_k0100 is that exact case. Demo 23 also already holds 101 and 201 k-point grids, so k-grid convergence is reused rather than recomputed.

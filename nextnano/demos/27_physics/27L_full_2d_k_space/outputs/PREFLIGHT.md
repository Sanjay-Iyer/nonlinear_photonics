# 27L preflight

**Full 2D in-plane (kx, ky) validation**

Question: Does full 2D in-plane physics materially change chi2 compared with radial integration?

Pass condition: chi2 is computed by genuine 2D integration over the in-plane zone and compared directly against the radial model on the same structure and the same cutoff. PASS means the difference is quantified. A difference below the 27H tolerance is a successful result that validates every radial calculation this project has done.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| k2d_integration_n61.in | kp8 | integration | 61 | 0.555714 | 14 | flat_band | linear_graded | k_mode;k_points | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| k2d_integration_n61.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27L cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 4 |
| nextnano++ Professional required | yes |
| Decks | 1 |
| k points per deck | [61] |
| Total k-point solves | 61 |
| States solved/output per deck | [14] |
| Estimated wall time | 8 h - 24 h |
| Estimated output volume | 4 - 20 GB |

**Basis for the estimate.** k_integration builds a two-dimensional in-plane grid, so num_points = 61 with symmetry = none is of order 61^2 = 3700 k-point solves against the 301 of a dispersion path - roughly twelve times the Demo 23 production run before the per-k output volume is counted. This is a planning estimate with wide bounds and it should be re-derived from the 27A pilot's measured seconds-per-k and bytes-per-k before the run is launched.

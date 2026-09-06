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

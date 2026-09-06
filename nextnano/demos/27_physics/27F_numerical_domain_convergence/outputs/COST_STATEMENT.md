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

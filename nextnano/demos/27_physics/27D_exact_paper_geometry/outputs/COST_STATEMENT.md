# 27D cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 1 |
| k points per deck | [301] |
| Total k-point solves | 301 |
| States solved/output per deck | [14] |
| Estimated wall time | 9 min - 30 min |
| Estimated output volume | 0.3 - 1 GB |

**Basis for the estimate.** One deck identical in cost to the Demo 23 production run (301 k points, 14 states, 10 min 20 s measured on the work laptop), plus margin. Only one deck is needed because the graded arm ALREADY EXISTS: demo_results/demo23/raw/ production_y_n301_k0100 is this exact structure and solver configuration, so rerunning it would buy nothing. See REUSE_AUDIT.md.

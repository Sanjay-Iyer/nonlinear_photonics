# 27I cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 1 |
| nextnano++ Professional required | yes |
| Decks | 2 |
| k points per deck | [301, 0] |
| Total k-point solves | 301 |
| States solved/output per deck | [14, 14] |
| Estimated wall time | 6 min - 30 min |
| Estimated output volume | 0.1 - 0.5 GB |

**Basis for the estimate.** The single-band arm is an ordinary 1D Schroedinger solve on 600 grid points and takes seconds. The kp6 arm is the Demo 23 production cost scaled by roughly (6/8), i.e. minutes. The kp8 arm is not rerun: it is demo_results/demo23/raw/production_y_n301_k0100 on this exact structure.

# 27G cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 3 |
| k points per deck | [451, 601, 901] |
| Total k-point solves | 1953 |
| States solved/output per deck | [14, 14, 14] |
| Estimated wall time | 1 h - 3 h |
| Estimated output volume | 0.8 - 2.5 GB |

**Basis for the estimate.** Demo 23 measured 301 k points x 14 states at 10 min 20 s, i.e. about 2 s per k point. The k spacing is held at the Demo 23 value, so widening the range widens the point count proportionally: 451, 601 and 901 points for 0.15, 0.20 and 0.30 pi/a. That is roughly 2000 k-point solves, or 1-3 h with margin. Only three decks are new: 0.10 pi/a is demo_results/demo23/raw/ production_y_n301_k0100 and 0.125 pi/a is kmax_y_n301_k0125, both already computed on this exact structure.

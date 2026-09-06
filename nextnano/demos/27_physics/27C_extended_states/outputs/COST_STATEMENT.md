# 27C cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 1 |
| k points per deck | [301] |
| Total k-point solves | 301 |
| States solved/output per deck | [48] |
| Estimated wall time | 30 min - 2 h |
| Estimated output volume | 1 - 3 GB |

**Basis for the estimate.** Demo 23 solved 301 k points for 14 states in 10 min 20 s. The eigenvalue cost grows faster than linearly in the state count, so 48 states is taken as 3-10x that. Envelopes are written at k=0 only unless 27A unlocks per-k output, which is why 27C is cheap compared with 27B.

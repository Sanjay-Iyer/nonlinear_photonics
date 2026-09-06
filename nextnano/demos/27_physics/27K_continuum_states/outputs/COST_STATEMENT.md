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

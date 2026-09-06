# 27E cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 3 |
| nextnano++ Professional required | yes |
| Decks | 2 |
| k points per deck | [301, 301] |
| Total k-point solves | 602 |
| States solved/output per deck | [14, 14] |
| Estimated wall time | 2 h - 8 h |
| Estimated output volume | 0.6 - 2 GB |

**Basis for the estimate.** The flat-band arm costs one Demo 23 production run (10 min 20 s measured). The self-consistent arm repeats the quantum solve once per Poisson iteration, so it is the iteration count times that, and Demo 6 needed tens of iterations on a much smaller problem. 2-8 h is the honest range; the run is capped by --timeout and by the iteration limit in the deck.
